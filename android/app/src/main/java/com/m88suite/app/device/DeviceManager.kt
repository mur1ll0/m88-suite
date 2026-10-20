package com.m88suite.app.device

import android.content.Context
import com.m88suite.core.Backoff
import com.m88suite.core.Doorbell
import com.m88suite.core.LinkState
import com.m88suite.core.StockBle
import com.m88suite.core.StreamConfig
import com.m88suite.core.StreamState
import com.m88suite.core.Telemetry
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.channels.BufferOverflow
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import java.net.InetSocketAddress

/** Unidade de video entregue a UI. */
class VideoUnit(val data: ByteArray, val codec: String)

/**
 * Conexao, telemetria, video e midia do M88 com o firmware de fabrica.
 * Espelho de desktop/src/m88suite/core/manager.py.
 */
class DeviceManager(context: Context, var address: String = StockBle.DEFAULT_ADDRESS) {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private val gatt = GattLink(context)
    private val wifi = WifiLink(context)
    private val media = MediaSync(context)
    private val ops = Mutex() // uma operacao de alto nivel por vez (video, midia, reinicio)

    private val _telemetry = MutableStateFlow(Telemetry())
    val telemetry: StateFlow<Telemetry> = _telemetry
    private val _video = MutableSharedFlow<VideoUnit>(extraBufferCapacity = 16, onBufferOverflow = BufferOverflow.DROP_OLDEST)
    val video: SharedFlow<VideoUnit> = _video
    private val _log = MutableSharedFlow<String>(extraBufferCapacity = 64, onBufferOverflow = BufferOverflow.DROP_OLDEST)
    val log: SharedFlow<String> = _log

    private var wantLink = false
    private var linkJob: Job? = null
    private var watchdogJob: Job? = null
    private var client: VideoClient? = null
    private var streamConfig: StreamConfig? = null
    private var videoUsedThisBoot = false

    init {
        scope.launch {
            gatt.notifications.collect { (_, data) ->
                StockBle.parse(data)?.let { note -> _telemetry.update { it.apply(note) } }
            }
        }
    }

    private fun say(message: String) {
        android.util.Log.i(TAG, message)
        _log.tryEmit(message)
        _telemetry.update { it.copy(message = message) }
    }

    // ------------------------------------------------------------------ link BLE
    fun connect() {
        wantLink = true
        if (linkJob?.isActive == true) return
        linkJob = scope.launch { linkLoop() }
    }

    fun disconnect() {
        wantLink = false
        scope.launch {
            stopStreamInternal()
            linkJob?.cancel()
            gatt.close()
            wifi.release()
            _telemetry.update { it.copy(link = LinkState.DISCONNECTED, wifiPhone = false) }
        }
    }

    private suspend fun linkLoop() {
        val backoff = Backoff(1.0, 20.0)
        while (scope.isActive && wantLink) {
            if (!gatt.isConnected) {
                val first = _telemetry.value.link == LinkState.DISCONNECTED
                _telemetry.update { it.copy(link = if (first) LinkState.CONNECTING else LinkState.RECONNECTING) }
                try {
                    gatt.connect(address)
                    gatt.send(StockBle.frame(StockBle.CMD_SYSTEM_STATE))
                    gatt.send(StockBle.frame(StockBle.CMD_MEDIA_COUNT))
                    backoff.reset()
                    _telemetry.update { it.copy(link = LinkState.CONNECTED) }
                    say("Bluetooth conectado")
                } catch (e: Exception) {
                    val wait = backoff.nextDelay()
                    if (e is GattLink.BluetoothSlotsFull) {
                        // apps comuns nao podem listar quem ocupa as vagas; via adb: dumpsys bluetooth_manager
                        say("Não foi possível usar o Bluetooth: ${e.message}")
                    } else {
                        say("Bluetooth indisponível (${e.message}); nova tentativa em ${wait.toInt()}s")
                    }
                    delay((wait * 1000).toLong())
                    continue
                }
            }
            runCatching { gatt.send(StockBle.frame(StockBle.CMD_WIFI_STATE, 0x01)) }
            delay(KEEPALIVE_MS)
        }
    }

    private suspend fun waitLink(timeoutMs: Long = 30_000) {
        connect()
        val until = System.currentTimeMillis() + timeoutMs
        while (!gatt.isConnected) {
            check(System.currentTimeMillis() < until) { "óculos não conectou pelo Bluetooth" }
            delay(500)
        }
    }

    // ------------------------------------------------------------------ Wi-Fi
    private suspend fun ensureWifi(): android.net.Network {
        waitLink()
        wifi.network?.let { return it }
        gatt.send(StockBle.frame(StockBle.CMD_AP_MODE, 0x01))
        delay(1_000)
        val net = wifi.connect()
        gatt.send(StockBle.frame(StockBle.CMD_SYSTEM_STATE))
        _telemetry.update { it.copy(wifiPhone = true) }
        return net
    }

    // ------------------------------------------------------------------ reinicio
    fun restartDevice() = scope.launch { ops.withLock { restartInternal() } }

    private suspend fun restartInternal() {
        waitLink()
        say("Reiniciando o óculos…")
        runCatching { gatt.send(StockBle.RESTART_FRAME) }
        videoUsedThisBoot = false
        wifi.release()
        _telemetry.update { it.copy(wifiPhone = false) }
        delay(3_000)
        gatt.close()
        waitLink(60_000)
        say("Óculos reiniciado")
    }

    // ------------------------------------------------------------------ video
    fun startStream(config: StreamConfig) = scope.launch {
        ops.withLock {
            stopStreamInternal()
            streamConfig = config
            _telemetry.update { it.copy(stream = StreamState.STARTING, recoveries = 0) }
            try {
                openVideo(config)
            } catch (e: Exception) {
                streamConfig = null
                _telemetry.update { it.copy(stream = StreamState.OFF) }
                say("Falha ao iniciar vídeo: ${e.message}")
                return@withLock
            }
            watchdogJob = scope.launch { watchdog() }
        }
    }

    fun stopStream() = scope.launch { ops.withLock { stopStreamInternal() } }

    private suspend fun openVideo(config: StreamConfig) {
        if (videoUsedThisBoot) restartInternal() // o servico de video so abre uma vez por boot
        val net = ensureWifi()
        val op = if (config.transport == "udp") StockBle.BOARDING_UDP_SERVICE else StockBle.BOARDING_TCP_SERVICE
        gatt.write(StockBle.BOARDING_SERVICE, StockBle.BOARDING_OP, StockBle.boarding(op))
        videoUsedThisBoot = true
        check(waitPort(net, Doorbell.CMD_PORT, 15_000)) { "serviço de vídeo não respondeu" }
        delay(1_000)
        client = VideoClient(net, config) { _video.tryEmit(VideoUnit(it, config.codec)) }.also { it.start() }
        _telemetry.update { it.copy(stream = StreamState.LIVE) }
        say("Vídeo ao vivo (${config.codec.uppercase()} ${config.transport.uppercase()})")
    }

    private suspend fun waitPort(net: android.net.Network, port: Int, timeoutMs: Long): Boolean = withContext(Dispatchers.IO) {
        val until = System.currentTimeMillis() + timeoutMs
        while (System.currentTimeMillis() < until) {
            val ok = runCatching {
                net.socketFactory.createSocket().use { it.connect(InetSocketAddress(WifiLink.DEVICE_IP, port), 500) }
            }.isSuccess
            if (ok) return@withContext true
            delay(300)
        }
        false
    }

    private suspend fun closeVideo() = withContext(Dispatchers.IO) {
        client?.stop()
        client = null
    }

    private suspend fun stopStreamInternal() {
        watchdogJob?.cancel()
        watchdogJob = null
        streamConfig = null
        closeVideo()
        if (_telemetry.value.stream != StreamState.OFF) {
            _telemetry.update { it.copy(stream = StreamState.OFF, fps = 0.0, kbps = 0.0) }
        }
    }

    private suspend fun watchdog() {
        var lastFrames = 0L
        var lastBytes = 0L
        while (scope.isActive && streamConfig != null) {
            delay(WATCHDOG_MS)
            val c = client ?: continue
            val seconds = WATCHDOG_MS / 1000.0
            _telemetry.update {
                it.copy(fps = (c.frames - lastFrames) / seconds, kbps = (c.bytes - lastBytes) * 8 / 1000.0 / seconds, dropped = c.dropped)
            }
            lastFrames = c.frames
            lastBytes = c.bytes
            if (c.stalled || c.error != null) {
                recover()
                lastFrames = 0
                lastBytes = 0
            }
        }
    }

    private suspend fun recover() = ops.withLock {
        val config = streamConfig ?: return@withLock
        val attempt = _telemetry.value.recoveries + 1
        if (attempt > MAX_RECOVERIES) {
            say("Vídeo não recuperou; aproxime o óculos e inicie de novo")
            watchdogJob = null
            stopStreamInternal()
            return@withLock
        }
        _telemetry.update { it.copy(stream = StreamState.RECOVERING, recoveries = attempt) }
        say("Vídeo parado; recuperando ($attempt/$MAX_RECOVERIES)")
        closeVideo()
        runCatching { openVideo(config) }.onFailure { say("Recuperação falhou: ${it.message}") }
    }

    // ------------------------------------------------------------------ midia
    fun syncMedia(onProgress: (String) -> Unit) = scope.launch {
        ops.withLock {
            try {
                val net = ensureWifi()
                val result = withContext(Dispatchers.IO) { media.sync(net, onProgress) }
                _telemetry.update { it.copy(mediaCount = result.total) }
            } catch (e: Exception) {
                onProgress("Falha na sincronização: ${e.message}")
            }
        }
    }

    fun close() {
        wantLink = false
        client?.stop()
        gatt.close()
        wifi.release()
        scope.coroutineContext[Job]?.cancel()
    }

    companion object {
        const val TAG = "M88Suite"
        const val KEEPALIVE_MS = 4_000L
        const val WATCHDOG_MS = 1_000L
        const val MAX_RECOVERIES = 3
    }
}
