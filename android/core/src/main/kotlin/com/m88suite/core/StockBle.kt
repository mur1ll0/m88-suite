package com.m88suite.core

import java.util.UUID

/** BLE do firmware de fabrica (keepfit/WheatAI + boarding Beken). Espelho de stock/ble_proto.py. */
object StockBle {
    val SERVICE: UUID = UUID.fromString("000056ff-0000-1000-8000-00805f9b34fb")
    val TX: UUID = UUID.fromString("000033f3-0000-1000-8000-00805f9b34fb")
    val RX: UUID = UUID.fromString("000033f4-0000-1000-8000-00805f9b34fb")
    val BOARDING_SERVICE: UUID = UUID.fromString("0000fa00-0000-1000-8000-00805f9b34fb")
    val BOARDING_OP: UUID = UUID.fromString("0000ea02-0000-1000-8000-00805f9b34fb")
    val BOARDING_NTF: UUID = UUID.fromString("0000ea01-0000-1000-8000-00805f9b34fb")
    val CCCD: UUID = UUID.fromString("00002902-0000-1000-8000-00805f9b34fb")

    const val DEFAULT_ADDRESS = "C8:47:8C:FD:52:2B"
    const val CMD_WIFI_STATE = 0x04
    const val CMD_MEDIA_COUNT = 0x05
    const val CMD_SYSTEM_STATE = 0x11
    const val CMD_AP_MODE = 0x13
    const val BOARDING_UDP_SERVICE = 3
    const val BOARDING_TCP_SERVICE = 4

    /** setDeviceMode(3) = "Reiniciar" do WheatAI. Modos 1 (OTA) e 4 (reset de fabrica) nunca. */
    val RESTART_FRAME: ByteArray = hex("0E123456789ABCDEF0").copyOf(20)

    val SYSTEM_STATE_BITS = mapOf(1 to "gravando vídeo", 2 to "gravando áudio", 4 to "chat IA", 8 to "transferência")

    fun frame(cmd: Int, arg: Int = 0): ByteArray =
        ByteArray(20).also { it[0] = 0x54; it[1] = cmd.toByte(); it[2] = arg.toByte() }

    fun boarding(opcode: Int, data: ByteArray = ByteArray(0)): ByteArray {
        // 1/2 mudam a config de Wi-Fi, 5-9 CS2/P2P, 10 desliga o BLE ate o proximo boot
        require(opcode == BOARDING_UDP_SERVICE || opcode == BOARDING_TCP_SERVICE) { "opcode $opcode nao permitido" }
        return byteArrayOf(opcode.toByte(), 0, data.size.toByte(), (data.size shr 8).toByte()) + data
    }

    sealed interface Notification {
        data class Battery(val percent: Int) : Notification
        data class SystemState(val bits: Int) : Notification
        data class ApState(val state: String) : Notification
        data class DeviceIp(val ip: String) : Notification
        data class MediaCount(val count: Int) : Notification
    }

    fun parse(data: ByteArray): Notification? {
        if (data.isEmpty()) return null
        val b = { i: Int -> data[i].toInt() and 0xFF }
        if (b(0) == 0x0B && data.size >= 2) return if (b(1) <= 100) Notification.Battery(b(1)) else null
        if (b(0) != 0x54 || data.size < 3) return null
        return when (b(1)) {
            0x12 -> Notification.SystemState(b(2))
            0x13 -> Notification.ApState(if (b(2) == 2) "client" else if (b(2) == 1) "on" else b(2).toString())
            0x04 -> if (b(2) == 2 && data.size >= 7) Notification.DeviceIp((3..6).joinToString(".") { b(it).toString() }) else null
            0x06 -> Notification.MediaCount(b(2))
            else -> null
        }
    }

    fun hex(s: String): ByteArray = ByteArray(s.length / 2) { s.substring(it * 2, it * 2 + 2).toInt(16).toByte() }
}
