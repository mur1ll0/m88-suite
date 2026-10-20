package com.m88suite.app.ui

import android.graphics.Bitmap
import android.view.SurfaceHolder
import android.view.SurfaceView
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.PlayArrow
import androidx.compose.material.icons.rounded.Stop
import androidx.compose.material3.Button
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.viewinterop.AndroidView
import androidx.compose.ui.unit.dp
import com.m88suite.app.device.VideoUnit
import com.m88suite.core.StreamConfig
import com.m88suite.core.StreamState
import com.m88suite.core.Telemetry
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.withContext

private data class Mode(val label: String, val config: StreamConfig)

private val MODES = listOf(
    Mode("Fluido · H.264/UDP", StreamConfig("h264", transport = "udp")),
    Mode("Estável · H.264/TCP", StreamConfig("h264", transport = "tcp")),
    Mode("Fotos · JPEG/UDP", StreamConfig("jpeg", transport = "udp")),
)

@Composable
fun CameraScreen(t: Telemetry, video: SharedFlow<VideoUnit>, onStart: (StreamConfig) -> Unit, onStop: () -> Unit) {
    var mode by remember { mutableStateOf(0) }
    val live = t.stream != StreamState.OFF
    Column(Modifier.verticalScroll(rememberScrollState()).padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        ScreenTitle("Câmera", "Vídeo ao vivo do óculos (640 × 480)")
        Box(Modifier.fillMaxWidth().aspectRatio(4f / 3f).clip(RoundedCornerShape(18.dp)).background(Color(0xFF05060C)),
            contentAlignment = Alignment.Center) {
            if (live) VideoView(video, MODES[mode].config.codec) else Text("Vídeo desligado", color = Palette.Muted)
        }
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            Button(onClick = { if (live) onStop() else onStart(MODES[mode].config) }) {
                Icon(if (live) Icons.Rounded.Stop else Icons.Rounded.PlayArrow, null)
                Text(if (live) "  Parar" else "  Iniciar")
            }
            Pill(t.stream.label, streamColor(t.stream))
        }
        if (t.stream == StreamState.LIVE) Text("%.1f fps · %.0f kbit/s · descartados %d".format(t.fps, t.kbps, t.dropped), color = Palette.Muted)
        if (t.stream == StreamState.RECOVERING) Text("Recuperando… tentativa ${t.recoveries}", color = Palette.Warn)
        Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
            MODES.forEachIndexed { i, m -> FilterChip(selected = mode == i, onClick = { mode = i }, enabled = !live, label = { Text(m.label) }) }
        }
        Notice("Fique a até ~3 m. Se o vídeo congelar, o app reinicia o óculos e retoma sozinho (até 3 tentativas). " +
            "Com o cabo USB conectado a câmera não transmite.")
    }
}

@Composable
private fun VideoView(video: SharedFlow<VideoUnit>, codec: String) {
    if (codec == "jpeg") {
        var bitmap by remember { mutableStateOf<Bitmap?>(null) }
        LaunchedEffect(video) { video.collect { u -> JpegDecoder.decode(u.data)?.let { bitmap = it } } }
        bitmap?.let { Image(it.asImageBitmap(), null, Modifier.fillMaxSize()) }
        return
    }
    var renderer by remember { mutableStateOf<H264Renderer?>(null) }
    AndroidView(factory = { ctx ->
        SurfaceView(ctx).apply {
            holder.addCallback(object : SurfaceHolder.Callback {
                override fun surfaceCreated(h: SurfaceHolder) { renderer = H264Renderer(h.surface) }
                override fun surfaceChanged(h: SurfaceHolder, f: Int, w: Int, hh: Int) = Unit
                override fun surfaceDestroyed(h: SurfaceHolder) { renderer?.release(); renderer = null }
            })
        }
    }, modifier = Modifier.fillMaxSize())
    LaunchedEffect(video, renderer) {
        val r = renderer ?: return@LaunchedEffect
        withContext(Dispatchers.Default) { video.collect { r.submit(it.data) } } // MediaCodec fora da thread da UI
    }
    DisposableEffect(Unit) { onDispose { renderer?.release() } }
}
