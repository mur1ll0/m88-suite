package com.m88suite.app.ui

import android.content.Intent
import android.provider.Settings
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.Bluetooth
import androidx.compose.material.icons.rounded.Sync
import androidx.compose.material3.Button
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp

@Composable
fun MediaScreen(mediaCount: Int?, status: String, syncing: Boolean, onSync: () -> Unit) {
    Column(Modifier.verticalScroll(rememberScrollState()).padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        ScreenTitle("Fotos e vídeos", "Copia os arquivos novos do óculos para a galeria (Imagens/M88 e Filmes/M88)")
        Button(onClick = onSync, enabled = !syncing) {
            Icon(Icons.Rounded.Sync, null)
            Text(if (syncing) "  Sincronizando…" else "  Sincronizar agora")
        }
        Text("Arquivos no óculos: ${mediaCount ?: "—"}", style = MaterialTheme.typography.bodyLarge)
        if (status.isNotEmpty()) Text(status, color = Palette.Muted)
        Notice("A sincronização liga o Wi‑Fi do óculos; o Android pode pedir para confirmar a rede M88-522B na primeira vez.")
    }
}

private val STOCK_EVENTS = listOf(
    "BTN0 BSP_LONG_PRESS" to "toque longo no botão 0",
    "BTN1 BSP_LONG_PRESS" to "toque longo no botão 1",
    "BTN1 BSP_TRIPLE_CLICK" to "toque triplo no botão 1",
    "BTN Start / stop recording" to "iniciar / parar gravação",
    "BTN Shutdown system" to "desligar",
    "BTN factory restore" to "restauração de fábrica (gesto não identificado)",
)

@Composable
fun MoreScreen() {
    val context = LocalContext.current
    Column(Modifier.verticalScroll(rememberScrollState()).padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        ScreenTitle("Áudio", "Fone de ouvido e microfone")
        Notice("O óculos é um headset Bluetooth (A2DP + HFP). Pareie pelo Android e ele vira saída de áudio e microfone " +
            "para música e chamadas, sem este app. Microfone por Wi‑Fi/USB chega com o firmware M88 Suite.")
        OutlinedButton(onClick = { context.startActivity(Intent(Settings.ACTION_BLUETOOTH_SETTINGS)) }) {
            Icon(Icons.Rounded.Bluetooth, null)
            Text("  Configurações de Bluetooth")
        }

        ScreenTitle("Botões", "Atalhos do óculos")
        Notice("O firmware de fábrica não permite mudar os atalhos; isso chega com o firmware M88 Suite. " +
            "Eventos encontrados no firmware atual:")
        STOCK_EVENTS.forEach { (event, meaning) ->
            Row(Modifier.fillMaxWidth()) {
                Text(event, Modifier.weight(1f))
                Text(meaning, Modifier.weight(1f), color = Palette.Muted)
            }
        }

        ScreenTitle("Firmware", "Versão e atualizações")
        Text("Instalada: 0039000B V191 (fábrica)")
        Text("Servidor do fabricante: V189 (mais antiga)", color = Palette.Muted)
        Text("Chip: Beken BK7258QN6868 · placa JY_5BG_V4", color = Palette.Muted)
        Notice("A atualização pelo Bluetooth fica desativada até existir uma cópia de segurança do firmware atual " +
            "(requer conexão serial). Ver docs/FIRMWARE_UPDATE.md.")
    }
}
