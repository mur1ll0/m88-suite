package com.m88suite.app.device

import android.annotation.SuppressLint
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothGatt
import android.bluetooth.BluetoothGattCallback
import android.bluetooth.BluetoothGattCharacteristic
import android.bluetooth.BluetoothGattDescriptor
import android.bluetooth.BluetoothManager
import android.bluetooth.BluetoothProfile
import android.bluetooth.BluetoothStatusCodes
import android.content.Context
import com.m88suite.core.StockBle
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.channels.BufferOverflow
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withTimeout
import java.util.UUID

/**
 * Conexao GATT com o M88. O Android so aceita uma operacao GATT por vez: todas passam pelo `mutex`
 * e esperam o callback correspondente.
 */
@SuppressLint("MissingPermission") // permissoes pedidas pela MainActivity antes de conectar
class GattLink(private val context: Context) {
    private val _connected = MutableStateFlow(false)
    val connected: StateFlow<Boolean> = _connected
    private val _notifications = MutableSharedFlow<Pair<UUID, ByteArray>>(
        extraBufferCapacity = 64, onBufferOverflow = BufferOverflow.DROP_OLDEST)
    val notifications: SharedFlow<Pair<UUID, ByteArray>> = _notifications

    private var gatt: BluetoothGatt? = null
    private val mutex = Mutex()
    private var pendingConnect: CompletableDeferred<Unit>? = null
    private var pendingOp: CompletableDeferred<Int>? = null

    private val callback = object : BluetoothGattCallback() {
        override fun onConnectionStateChange(g: BluetoothGatt, status: Int, newState: Int) {
            if (newState == BluetoothProfile.STATE_CONNECTED) {
                g.discoverServices()
            } else {
                _connected.value = false
                pendingConnect?.completeExceptionally(IllegalStateException("conexao recusada ($status)"))
                pendingOp?.complete(-1)
                g.close()
                if (gatt === g) gatt = null
            }
        }

        override fun onServicesDiscovered(g: BluetoothGatt, status: Int) {
            if (status == BluetoothGatt.GATT_SUCCESS) pendingConnect?.complete(Unit)
            else pendingConnect?.completeExceptionally(IllegalStateException("servicos nao encontrados ($status)"))
        }

        override fun onCharacteristicWrite(g: BluetoothGatt, ch: BluetoothGattCharacteristic, status: Int) {
            pendingOp?.complete(status)
        }

        override fun onDescriptorWrite(g: BluetoothGatt, d: BluetoothGattDescriptor, status: Int) {
            pendingOp?.complete(status)
        }

        override fun onCharacteristicChanged(g: BluetoothGatt, ch: BluetoothGattCharacteristic, value: ByteArray) {
            _notifications.tryEmit(ch.uuid to value)
        }
    }

    val isConnected: Boolean get() = _connected.value

    suspend fun connect(address: String, timeoutMs: Long = 20_000) = mutex.withLock {
        close()
        val adapter = context.getSystemService(BluetoothManager::class.java).adapter
            ?: error("Bluetooth indisponivel")
        check(adapter.isEnabled) { "Bluetooth desligado" }
        val wait = CompletableDeferred<Unit>().also { pendingConnect = it }
        gatt = adapter.getRemoteDevice(address).connectGatt(context, false, callback, BluetoothDevice.TRANSPORT_LE)
        try {
            withTimeout(timeoutMs) { wait.await() }
        } catch (e: Exception) {
            close()
            throw e
        } finally {
            pendingConnect = null
        }
        enableNotify(StockBle.SERVICE, StockBle.RX)
        enableNotify(StockBle.BOARDING_SERVICE, StockBle.BOARDING_NTF)
        _connected.value = true
    }

    private suspend fun enableNotify(service: UUID, uuid: UUID) {
        val g = gatt ?: return
        val ch = g.getService(service)?.getCharacteristic(uuid) ?: return
        g.setCharacteristicNotification(ch, true)
        val d = ch.getDescriptor(StockBle.CCCD) ?: return
        op { g.writeDescriptor(d, BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE) }
    }

    /** Escreve em `uuid` (servico `service`). Retorna quando o oculos confirma a escrita. */
    suspend fun write(service: UUID, uuid: UUID, data: ByteArray) = mutex.withLock {
        val g = gatt ?: error("Bluetooth desconectado")
        val ch = g.getService(service)?.getCharacteristic(uuid) ?: error("caracteristica $uuid ausente")
        val type = if (ch.properties and BluetoothGattCharacteristic.PROPERTY_WRITE != 0)
            BluetoothGattCharacteristic.WRITE_TYPE_DEFAULT else BluetoothGattCharacteristic.WRITE_TYPE_NO_RESPONSE
        val status = op { g.writeCharacteristic(ch, data, type) }
        check(status == BluetoothGatt.GATT_SUCCESS) { "escrita falhou ($status)" }
    }

    suspend fun send(frame: ByteArray) = write(StockBle.SERVICE, StockBle.TX, frame)

    private suspend fun op(start: () -> Int): Int {
        val wait = CompletableDeferred<Int>().also { pendingOp = it }
        try {
            var code = start()
            var retries = 0
            while (code == BluetoothStatusCodes.ERROR_GATT_WRITE_REQUEST_BUSY && retries++ < 5) {
                kotlinx.coroutines.delay(80)
                code = start()
            }
            if (code != BluetoothStatusCodes.SUCCESS) return code
            return withTimeout(5_000) { wait.await() }
        } finally {
            pendingOp = null
        }
    }

    fun close() {
        gatt?.let {
            it.disconnect()
            it.close()
        }
        gatt = null
        _connected.value = false
    }
}
