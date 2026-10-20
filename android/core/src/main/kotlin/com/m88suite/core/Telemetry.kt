package com.m88suite.core

enum class LinkState(val label: String) {
    DISCONNECTED("Desconectado"), CONNECTING("Conectando"), CONNECTED("Conectado"), RECONNECTING("Reconectando")
}

enum class StreamState(val label: String) {
    OFF("Desligado"), STARTING("Iniciando"), LIVE("Ao vivo"), RECOVERING("Recuperando")
}

data class Telemetry(
    val link: LinkState = LinkState.DISCONNECTED,
    val battery: Int? = null,
    val systemState: Int? = null,
    val wifiAp: String? = null,
    val wifiPhone: Boolean = false,
    val mediaCount: Int? = null,
    val stream: StreamState = StreamState.OFF,
    val fps: Double = 0.0,
    val kbps: Double = 0.0,
    val dropped: Int = 0,
    val recoveries: Int = 0,
    val message: String = "",
) {
    val systemFlags: List<String>
        get() = systemState?.let { s -> StockBle.SYSTEM_STATE_BITS.filterKeys { s and it != 0 }.values.toList() }.orEmpty()

    fun apply(note: StockBle.Notification): Telemetry = when (note) {
        is StockBle.Notification.Battery -> copy(battery = note.percent)
        is StockBle.Notification.SystemState -> copy(systemState = note.bits)
        is StockBle.Notification.ApState -> copy(wifiAp = note.state)
        is StockBle.Notification.MediaCount -> copy(mediaCount = note.count)
        is StockBle.Notification.DeviceIp -> this
    }
}

/** Configuracao de stream. 864x480 e o pedido que funciona no firmware de fabrica (chega 640x480). */
data class StreamConfig(val codec: String = "h264", val width: Int = 864, val height: Int = 480, val transport: String = "udp") {
    val format: Int get() = if (codec == "h264") 1 else 0
}
