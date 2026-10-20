package com.m88suite.app.ui

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp

// Mesma paleta do app Windows (desktop/src/m88suite/ui/theme.py).
object Palette {
    val Accent = Color(0xFF4F8CFF)
    val Ok = Color(0xFF3DDC97)
    val Warn = Color(0xFFFFB547)
    val Bad = Color(0xFFFF5C6C)
    val Bg = Color(0xFF0F1220)
    val Surface = Color(0xFF171B2E)
    val Surface2 = Color(0xFF1F2440)
    val Text = Color(0xFFE8EAF6)
    val Muted = Color(0xFF9AA3C7)
}

private val colors = darkColorScheme(
    primary = Palette.Accent, background = Palette.Bg, surface = Palette.Surface,
    surfaceVariant = Palette.Surface2, onBackground = Palette.Text, onSurface = Palette.Text,
    onSurfaceVariant = Palette.Muted, error = Palette.Bad,
)

private val typography = Typography(
    headlineMedium = TextStyle(fontSize = 28.sp, fontWeight = FontWeight.SemiBold),
    titleMedium = TextStyle(fontSize = 18.sp, fontWeight = FontWeight.SemiBold),
    bodyLarge = TextStyle(fontSize = 17.sp),
    bodyMedium = TextStyle(fontSize = 15.sp),
    labelLarge = TextStyle(fontSize = 16.sp, fontWeight = FontWeight.SemiBold),
)

@Composable
fun M88Theme(content: @Composable () -> Unit) = MaterialTheme(colorScheme = colors, typography = typography, content = content)
