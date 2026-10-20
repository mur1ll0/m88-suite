package com.m88suite.app.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.unit.dp
import com.m88suite.core.LinkState
import com.m88suite.core.StreamState

@Composable
fun StatusCard(icon: ImageVector, title: String, value: String, detail: String, color: Color, modifier: Modifier = Modifier) {
    Card(modifier, shape = RoundedCornerShape(18.dp), colors = CardDefaults.cardColors(containerColor = Palette.Surface)) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(icon, null, tint = color, modifier = Modifier.size(22.dp))
                Spacer(Modifier.width(8.dp))
                Text(title, color = Palette.Muted, style = MaterialTheme.typography.bodyMedium)
            }
            Text(value, style = MaterialTheme.typography.headlineMedium)
            if (detail.isNotEmpty()) Text(detail, color = Palette.Muted, style = MaterialTheme.typography.bodyMedium)
        }
    }
}

@Composable
fun Pill(text: String, color: Color) {
    Text(text, color = color, style = MaterialTheme.typography.labelLarge,
        modifier = Modifier.background(color.copy(alpha = 0.18f), RoundedCornerShape(50)).padding(horizontal = 14.dp, vertical = 6.dp))
}

@Composable
fun Notice(text: String) {
    Text(text, color = Palette.Muted, style = MaterialTheme.typography.bodyMedium,
        modifier = Modifier.fillMaxWidth().background(Palette.Surface, RoundedCornerShape(14.dp)).padding(14.dp))
}

@Composable
fun ScreenTitle(title: String, subtitle: String) {
    Column(Modifier.padding(bottom = 8.dp)) {
        Text(title, style = MaterialTheme.typography.headlineMedium)
        Text(subtitle, color = Palette.Muted, style = MaterialTheme.typography.bodyMedium)
    }
}

fun linkColor(state: LinkState) = when (state) {
    LinkState.CONNECTED -> Palette.Ok
    LinkState.DISCONNECTED -> Palette.Bad
    else -> Palette.Warn
}

fun streamColor(state: StreamState) = when (state) {
    StreamState.LIVE -> Palette.Ok
    StreamState.OFF -> Palette.Muted
    else -> Palette.Warn
}
