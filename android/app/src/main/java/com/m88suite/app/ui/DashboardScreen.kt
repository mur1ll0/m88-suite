package com.m88suite.app.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.BatteryStd
import androidx.compose.material.icons.rounded.Bluetooth
import androidx.compose.material.icons.rounded.PhotoLibrary
import androidx.compose.material.icons.rounded.PowerSettingsNew
import androidx.compose.material.icons.rounded.Videocam
import androidx.compose.material.icons.rounded.Visibility
import androidx.compose.material.icons.rounded.Wifi
import androidx.compose.material3.Button
import androidx.compose.material3.Icon
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.m88suite.core.LinkState
import com.m88suite.core.StreamState
import com.m88suite.core.Telemetry

@Composable
fun DashboardScreen(t: Telemetry, log: List<String>, onConnectToggle: () -> Unit, onRestart: () -> Unit) {
    Column(Modifier.verticalScroll(rememberScrollState()).padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        ScreenTitle("Painel", "Estado do óculos M88 em tempo real")
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            Button(onClick = onConnectToggle) {
                Icon(Icons.Rounded.Bluetooth, null)
                Text(if (t.link == LinkState.DISCONNECTED) "  Conectar" else "  Desconectar")
            }
            OutlinedButton(onClick = onRestart, enabled = t.link == LinkState.CONNECTED) {
                Icon(Icons.Rounded.PowerSettingsNew, null)
                Text("  Reiniciar")
            }
        }
        val battery = t.battery
        val cards = listOf(
            CardData(Icons.Rounded.Bluetooth, "Bluetooth", t.link.label,
                if (t.link != LinkState.DISCONNECTED) "Reconexão automática ativa" else "", linkColor(t.link)),
            CardData(Icons.Rounded.BatteryStd, "Bateria", battery?.let { "$it%" } ?: "—", if (battery == null) "aguardando o óculos" else "",
                when { battery == null -> Palette.Muted; battery > 40 -> Palette.Ok; battery > 15 -> Palette.Warn; else -> Palette.Bad }),
            CardData(Icons.Rounded.Wifi, "Wi‑Fi", if (t.wifiPhone) "Conectado" else "Sob demanda",
                if (t.wifiPhone) "Rede M88-522B" else "liga para vídeo e mídia", if (t.wifiPhone) Palette.Ok else Palette.Muted),
            CardData(Icons.Rounded.Videocam, "Câmera", t.stream.label,
                if (t.stream == StreamState.LIVE) "%.1f fps · %.0f kbit/s".format(t.fps, t.kbps) else "", streamColor(t.stream)),
            CardData(Icons.Rounded.PhotoLibrary, "Fotos e vídeos", t.mediaCount?.toString() ?: "—", "arquivos no cartão",
                if ((t.mediaCount ?: 0) > 0) Palette.Accent else Palette.Muted),
            CardData(Icons.Rounded.Visibility, "Óculos", if (t.link == LinkState.CONNECTED) "Online" else "—",
                t.systemFlags.joinToString().ifEmpty { "em espera" }, if (t.link == LinkState.CONNECTED) Palette.Ok else Palette.Muted),
        )
        cards.chunked(2).forEach { row ->
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                row.forEach { StatusCard(it.icon, it.title, it.value, it.detail, it.color, Modifier.weight(1f)) }
            }
        }
        Notice("LED e lanterna não são informados pelo firmware de fábrica. Esses indicadores chegam com o firmware M88 Suite.")
        log.takeLast(8).reversed().forEach { Text(it, color = Palette.Muted, modifier = Modifier.fillMaxWidth()) }
    }
}

private data class CardData(val icon: androidx.compose.ui.graphics.vector.ImageVector, val title: String, val value: String,
                            val detail: String, val color: androidx.compose.ui.graphics.Color)
