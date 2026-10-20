package com.m88suite.app.device

import android.net.Network
import com.m88suite.core.Doorbell
import com.m88suite.core.FrameAssembler
import com.m88suite.core.H264ParamCache
import com.m88suite.core.StreamConfig
import java.io.InputStream
import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.InetAddress
import java.net.InetSocketAddress
import java.net.Socket
import java.net.SocketTimeoutException
import java.util.concurrent.atomic.AtomicBoolean

/**
 * Sessao de video do servico doorbell (firmware de fabrica). Liga a camera via TCP 7100 e entrega
 * cada quadro (JPEG ou unidade H.264) em `onFrame`. Roda numa thread propria.
 */
class VideoClient(
    private val network: Network,
    private val config: StreamConfig,
    private val onFrame: (ByteArray) -> Unit,
) {
    @Volatile var frames = 0L; private set
    @Volatile var bytes = 0L; private set
    @Volatile var dropped = 0; private set
    @Volatile var lastFrameAt = 0L; private set
    @Volatile var startedAt = 0L; private set
    @Volatile var error: String? = null; private set

    private val running = AtomicBoolean(false)
    private var thread: Thread? = null

    val stalled: Boolean
        get() {
            val ref = if (lastFrameAt > 0) lastFrameAt else startedAt
            return ref > 0 && System.currentTimeMillis() - ref > STALL_MS
        }

    fun start() {
        running.set(true)
        thread = Thread({ runCatching { loop() }.onFailure { error = it.message ?: it.toString() } }, "m88-video")
            .apply { isDaemon = true; start() }
    }

    fun stop() {
        running.set(false)
        thread?.join(3_000)
    }

    private fun loop() {
        val device = InetAddress.getByName(WifiLink.DEVICE_IP)
        val packer = Doorbell.Packer()
        val cmd = network.socketFactory.createSocket().apply { connect(InetSocketAddress(device, Doorbell.CMD_PORT), 3_000) }
        val udp = config.transport == "udp"
        var datagram: DatagramSocket? = null
        var tcpImage: Socket? = null
        var tcpIn: InputStream? = null
        if (udp) {
            datagram = DatagramSocket(null).apply {
                reuseAddress = true
                receiveBufferSize = 4 shl 20
                bind(InetSocketAddress(Doorbell.UDP_IMG_PORT))
                soTimeout = 500
            }
            network.bindSocket(datagram)
        } else {
            tcpImage = network.socketFactory.createSocket().apply {
                connect(InetSocketAddress(device, Doorbell.IMG_PORT), 3_000)
                soTimeout = 1_000
            }
            tcpIn = tcpImage.getInputStream()
        }
        val hello = packer.pack(byteArrayOf(0))
        fun sendHello() = datagram?.send(DatagramPacket(hello, hello.size, device, Doorbell.UDP_IMG_PORT))
        val assembler = FrameAssembler()
        val params = H264ParamCache()
        var unpacker = Doorbell.Unpacker()
        val buf = ByteArray(65536)
        try {
            sendHello()
            cmd.getOutputStream().write(packer.pack(Doorbell.command(
                Doorbell.CMD_CAMERA_ON, Doorbell.CAMERA_ID_DVP,
                Doorbell.cameraOnPayload(config.width, config.height, config.format))))
            startedAt = System.currentTimeMillis()
            var lastHello = startedAt
            while (running.get()) {
                if (udp && System.currentTimeMillis() - lastHello > HELLO_MS) {
                    sendHello()
                    lastHello = System.currentTimeMillis()
                }
                val data = try {
                    if (udp) {
                        val p = DatagramPacket(buf, buf.size)
                        datagram!!.receive(p)
                        unpacker = Doorbell.Unpacker() // cada datagrama e um pacote completo
                        buf.copyOf(p.length)
                    } else {
                        val n = tcpIn!!.read(buf)
                        if (n < 0) throw IllegalStateException("conexao de imagem fechada pelo oculos")
                        buf.copyOf(n)
                    }
                } catch (e: SocketTimeoutException) {
                    continue
                }
                bytes += data.size
                for (packet in unpacker.feed(data)) {
                    val unit = assembler.push(packet.payload) ?: continue
                    dropped = assembler.dropped
                    if (config.codec == "jpeg" && !(unit.size > 2 && unit[0] == 0xFF.toByte() && unit[1] == 0xD8.toByte())) continue
                    frames++
                    lastFrameAt = System.currentTimeMillis()
                    onFrame(if (config.codec == "h264") params.fix(unit) else unit)
                }
                dropped = assembler.dropped
            }
        } finally {
            runCatching { cmd.getOutputStream().write(packer.pack(Doorbell.command(Doorbell.CMD_CAMERA_OFF, Doorbell.CAMERA_ID_DVP))) }
            runCatching { cmd.close() }
            runCatching { datagram?.close() }
            runCatching { tcpImage?.close() }
        }
    }

    companion object {
        const val STALL_MS = 4_000L
        const val HELLO_MS = 2_000L
    }
}
