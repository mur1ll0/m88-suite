package com.m88suite.app.ui

import android.content.Intent
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.util.Size
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.CheckCircle
import androidx.compose.material.icons.rounded.Delete
import androidx.compose.material.icons.rounded.Download
import androidx.compose.material.icons.rounded.Folder
import androidx.compose.material.icons.rounded.Image
import androidx.compose.material.icons.rounded.PhotoLibrary
import androidx.compose.material.icons.rounded.PlayCircle
import androidx.compose.material.icons.rounded.Refresh
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Checkbox
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Switch
import androidx.compose.material3.Tab
import androidx.compose.material3.TabRow
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.produceState
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.m88suite.app.device.DeviceManager
import com.m88suite.app.device.Destination
import com.m88suite.app.device.LocalMedia
import com.m88suite.app.device.MediaState
import com.m88suite.app.device.RemoteMedia
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File
import java.util.Locale

@Composable
fun MediaScreen(manager: DeviceManager, state: MediaState) {
    val context = LocalContext.current
    val repo = manager.media
    var destination by remember { mutableStateOf(repo.destination()) }
    var deleteAfter by remember { mutableStateOf(repo.deleteAfterDownload) }
    var tab by remember { mutableStateOf(0) }
    var editAlbum by remember { mutableStateOf(false) }
    var confirmDelete by remember { mutableStateOf<List<RemoteMedia>?>(null) }
    var preview by remember { mutableStateOf<Pair<RemoteMedia, File>?>(null) }
    val selected = remember { mutableStateListOf<String>() }

    val local by produceState(emptyList<LocalMedia>(), destination, state.localVersion) {
        value = withContext(Dispatchers.IO) { runCatching { repo.listLocal() }.getOrDefault(emptyList()) }
    }
    val localNames = remember(local) { local.map { it.name }.toSet() }

    val pickFolder = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocumentTree()) { uri ->
        if (uri != null) {
            repo.useFolder(uri)
            destination = repo.destination()
        }
    }

    LaunchedEffect(Unit) { if (!state.remoteLoaded) manager.refreshRemote() }

    Column(Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
        ScreenTitle("Fotos e vídeos", "O que está no óculos e o que já está no celular")

        Card(shape = RoundedCornerShape(16.dp), colors = CardDefaults.cardColors(containerColor = Palette.Surface)) {
            Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("Salvar em", color = Palette.Muted)
                Text(destination.label, style = MaterialTheme.typography.bodyLarge)
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedButton(onClick = { editAlbum = true }) { Icon(Icons.Rounded.PhotoLibrary, null); Text("  Álbum") }
                    OutlinedButton(onClick = { pickFolder.launch(null) }) { Icon(Icons.Rounded.Folder, null); Text("  Pasta…") }
                }
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text("Apagar do óculos depois de baixar", Modifier.weight(1f))
                    Switch(checked = deleteAfter, onCheckedChange = { deleteAfter = it; repo.deleteAfterDownload = it })
                }
            }
        }

        if (state.busy) LinearProgressIndicator(Modifier.fillMaxWidth())
        if (state.status.isNotEmpty()) Text(state.status, color = Palette.Muted)

        TabRow(selectedTabIndex = tab, containerColor = Palette.Bg) {
            Tab(tab == 0, { tab = 0 }, text = { Text("No óculos (${state.remote.size})") })
            Tab(tab == 1, { tab = 1 }, text = { Text("Baixadas (${local.size})") })
        }

        if (tab == 0) {
            val chosen = state.remote.filter { it.name in selected }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                Button(onClick = { manager.download(chosen.ifEmpty { state.remote.filter { it.name !in localNames } }, deleteAfter); selected.clear() },
                    enabled = !state.busy && state.remote.isNotEmpty()) {
                    Icon(Icons.Rounded.Download, null)
                    Text(if (chosen.isEmpty()) "  Baixar novos" else "  Baixar (${chosen.size})")
                }
                OutlinedButton(onClick = { confirmDelete = chosen }, enabled = !state.busy && chosen.isNotEmpty(),
                    colors = ButtonDefaults.outlinedButtonColors(contentColor = Palette.Bad)) {
                    Icon(Icons.Rounded.Delete, null)
                }
                OutlinedButton(onClick = { manager.refreshRemote() }, enabled = !state.busy) { Icon(Icons.Rounded.Refresh, null) }
            }
            TextButton(onClick = { if (selected.size == state.remote.size) selected.clear() else { selected.clear(); selected += state.remote.map { it.name } } }) {
                Text(if (selected.size == state.remote.size && selected.isNotEmpty()) "Limpar seleção" else "Selecionar tudo")
            }
            LazyColumn(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                items(state.remote, key = { it.name }) { item ->
                    RemoteRow(item, item.name in selected, item.name in localNames,
                        onToggle = { if (item.name in selected) selected.remove(item.name) else selected.add(item.name) },
                        onOpen = { if (!item.isVideo) manager.preview(item) { f -> preview = item to f } })
                }
            }
        } else {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(onClick = { local.firstOrNull()?.let { openMedia(context, it) } }, enabled = local.isNotEmpty()) {
                    Icon(Icons.Rounded.PhotoLibrary, null); Text("  Abrir na galeria")
                }
            }
            LazyVerticalGrid(GridCells.Adaptive(110.dp), Modifier.weight(1f), horizontalArrangement = Arrangement.spacedBy(6.dp),
                verticalArrangement = Arrangement.spacedBy(6.dp)) {
                items(local, key = { it.uri.toString() }) { item -> LocalTile(item) { openMedia(context, item) } }
            }
        }
    }

    if (editAlbum) AlbumDialog((destination as? Destination.Album)?.name ?: "M88", onDismiss = { editAlbum = false }) {
        repo.useAlbum(it)
        destination = repo.destination()
        editAlbum = false
    }
    confirmDelete?.let { items ->
        AlertDialog(onDismissRequest = { confirmDelete = null },
            title = { Text("Apagar do óculos?") },
            text = { Text("${items.size} arquivo(s) serão apagados do cartão do óculos. Arquivos que ainda não foram baixados serão perdidos.") },
            confirmButton = { TextButton(onClick = { manager.deleteRemote(items); selected.clear(); confirmDelete = null }) { Text("Apagar", color = Palette.Bad) } },
            dismissButton = { TextButton(onClick = { confirmDelete = null }) { Text("Cancelar") } })
    }
    preview?.let { (item, file) ->
        val bitmap = remember(file) { BitmapFactory.decodeFile(file.path) }
        AlertDialog(onDismissRequest = { preview = null },
            title = { Text(prettyName(item.name)) },
            text = { bitmap?.let { Image(it.asImageBitmap(), null, Modifier.fillMaxWidth(), contentScale = ContentScale.Fit) } ?: Text("Não foi possível abrir a foto") },
            confirmButton = { TextButton(onClick = { manager.download(listOf(item), deleteAfter); preview = null }) { Text("Baixar") } },
            dismissButton = { TextButton(onClick = { preview = null }) { Text("Fechar") } })
    }
}

@Composable
private fun RemoteRow(item: RemoteMedia, checked: Boolean, downloaded: Boolean, onToggle: () -> Unit, onOpen: () -> Unit) {
    Row(Modifier.fillMaxWidth().clip(RoundedCornerShape(12.dp)).background(Palette.Surface).clickable(onClick = onOpen).padding(8.dp),
        verticalAlignment = Alignment.CenterVertically) {
        Checkbox(checked, { onToggle() })
        Icon(if (item.isVideo) Icons.Rounded.PlayCircle else Icons.Rounded.Image, null, tint = Palette.Accent)
        Column(Modifier.weight(1f).padding(start = 10.dp)) {
            Text(prettyName(item.name), maxLines = 1, overflow = TextOverflow.Ellipsis)
            Text("${if (item.isVideo) "Vídeo" else "Foto"} · ${prettySize(item.size)}", color = Palette.Muted, style = MaterialTheme.typography.bodyMedium)
        }
        if (downloaded) Icon(Icons.Rounded.CheckCircle, "já baixado", tint = Palette.Ok)
    }
}

@Composable
private fun LocalTile(item: LocalMedia, onClick: () -> Unit) {
    val context = LocalContext.current
    val thumb by produceState<Bitmap?>(null, item.uri) {
        value = withContext(Dispatchers.IO) { runCatching { context.contentResolver.loadThumbnail(item.uri, Size(256, 256), null) }.getOrNull() }
    }
    Box(Modifier.aspectRatio(1f).clip(RoundedCornerShape(12.dp)).background(Palette.Surface).clickable(onClick = onClick),
        contentAlignment = Alignment.Center) {
        thumb?.let { Image(it.asImageBitmap(), item.name, Modifier.fillMaxSize(), contentScale = ContentScale.Crop) }
            ?: Icon(Icons.Rounded.Image, null, tint = Palette.Muted)
        if (item.isVideo) Icon(Icons.Rounded.PlayCircle, null, tint = Color.White, modifier = Modifier.size(36.dp))
    }
}

@Composable
private fun AlbumDialog(current: String, onDismiss: () -> Unit, onSave: (String) -> Unit) {
    var name by remember { mutableStateOf(current) }
    AlertDialog(onDismissRequest = onDismiss,
        title = { Text("Álbum da galeria") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("Fotos em Imagens/<nome> e vídeos em Filmes/<nome>; aparece como álbum na galeria.", color = Palette.Muted)
                OutlinedTextField(name, { name = it }, singleLine = true, label = { Text("Nome do álbum") })
            }
        },
        confirmButton = { TextButton(onClick = { onSave(name) }) { Text("Salvar") } },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Cancelar") } })
}

private fun openMedia(context: android.content.Context, item: LocalMedia) {
    val intent = Intent(Intent.ACTION_VIEW).setDataAndType(item.uri, if (item.isVideo) "video/*" else "image/*")
        .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_ACTIVITY_NEW_TASK)
    runCatching { context.startActivity(intent) }
}

/** "20261020024748.jpeg" -> "20/10/2026 02:47:48" (o oculos nomeia pela data/hora, em UTC). */
fun prettyName(name: String): String {
    val d = name.substringBefore('.')
    if (d.length != 14 || !d.all { it.isDigit() }) return name
    return "${d.substring(6, 8)}/${d.substring(4, 6)}/${d.substring(0, 4)} ${d.substring(8, 10)}:${d.substring(10, 12)}:${d.substring(12, 14)}"
}

fun prettySize(bytes: Long): String = when {
    bytes >= 1_000_000 -> String.format(Locale.ROOT, "%.1f MB", bytes / 1_000_000.0)
    else -> "${bytes / 1000} KB"
}
