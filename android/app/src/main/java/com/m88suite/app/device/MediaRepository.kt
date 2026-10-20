package com.m88suite.app.device

import android.content.ContentUris
import android.content.ContentValues
import android.content.Context
import android.content.Intent
import android.net.Network
import android.net.Uri
import android.provider.MediaStore
import androidx.documentfile.provider.DocumentFile
import org.apache.commons.net.ftp.FTP
import org.apache.commons.net.ftp.FTPClient
import java.io.File
import java.io.OutputStream

/** Arquivo no cartao do oculos. */
data class RemoteMedia(val name: String, val size: Long, val timeMs: Long) {
    val isVideo: Boolean get() = MediaTypes.isVideo(name)
}

/** Arquivo ja baixado no celular. */
data class LocalMedia(val name: String, val uri: Uri, val isVideo: Boolean, val timeMs: Long)

/** Para onde os arquivos vao: um album da galeria (MediaStore) ou uma pasta escolhida (SAF). */
sealed interface Destination {
    val label: String

    data class Album(val name: String) : Destination {
        override val label get() = "Galeria › Imagens/$name e Filmes/$name"
    }

    data class Folder(val tree: Uri, val displayName: String) : Destination {
        override val label get() = "Pasta › $displayName"
    }
}

object MediaTypes {
    private val photo = setOf("jpg", "jpeg", "png", "bmp")
    private val video = setOf("mp4", "avi", "mov", "3gp")
    fun ext(name: String) = name.substringAfterLast('.', "").lowercase()
    fun isMedia(name: String) = ext(name) in photo || ext(name) in video
    fun isVideo(name: String) = ext(name) in video
    fun mime(name: String) = when (ext(name)) {
        "jpg", "jpeg" -> "image/jpeg"
        "png" -> "image/png"
        "bmp" -> "image/bmp"
        "mp4" -> "video/mp4"
        "mov" -> "video/quicktime"
        "3gp" -> "video/3gpp"
        else -> "video/x-msvideo"
    }
}

/**
 * Midia do oculos via FTP (bk7258/123456) e do celular (MediaStore ou pasta escolhida).
 * O firmware de fabrica aceita DELE; so apagamos depois de conferir o tamanho do arquivo baixado.
 */
class MediaRepository(private val context: Context) {
    private val prefs = context.getSharedPreferences("m88_media", Context.MODE_PRIVATE)
    private val resolver = context.contentResolver

    data class Result(val downloaded: Int, val failed: Int, val deleted: Int)

    // ------------------------------------------------------------------ preferencias
    var deleteAfterDownload: Boolean
        get() = prefs.getBoolean("delete_after", false)
        set(value) = prefs.edit().putBoolean("delete_after", value).apply()

    fun destination(): Destination {
        val tree = prefs.getString("tree_uri", null)
        if (tree != null) {
            val uri = Uri.parse(tree)
            val doc = DocumentFile.fromTreeUri(context, uri)
            if (doc != null && doc.canWrite()) return Destination.Folder(uri, doc.name ?: "pasta escolhida")
        }
        return Destination.Album(prefs.getString("album", "M88") ?: "M88")
    }

    fun useAlbum(name: String) {
        val clean = name.trim().replace(Regex("[\\\\/:*?\"<>|]"), "").ifEmpty { "M88" }
        prefs.edit().putString("album", clean).remove("tree_uri").apply()
    }

    fun useFolder(tree: Uri) {
        resolver.takePersistableUriPermission(tree, Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_GRANT_WRITE_URI_PERMISSION)
        prefs.edit().putString("tree_uri", tree.toString()).apply()
    }

    // ------------------------------------------------------------------ oculos (FTP)
    private fun <T> ftp(network: Network, block: (FTPClient) -> T): T {
        val client = FTPClient().apply {
            setSocketFactory(network.socketFactory)
            connectTimeout = 5_000
            defaultTimeout = 10_000
        }
        try {
            client.connect(WifiLink.DEVICE_IP, 21)
            check(client.login("bk7258", "123456")) { "login FTP recusado" }
            client.enterLocalPassiveMode()
            client.setFileType(FTP.BINARY_FILE_TYPE)
            return block(client)
        } finally {
            runCatching { client.logout() }
            runCatching { client.disconnect() }
        }
    }

    fun listRemote(network: Network): List<RemoteMedia> = ftp(network) { c ->
        c.listFiles("/").filter { it.isFile && MediaTypes.isMedia(it.name) }
            .map { RemoteMedia(it.name, it.size, it.timestamp?.timeInMillis ?: 0L) }
            .sortedByDescending { it.name } // nomes do oculos sao a data/hora (AAAAMMDDhhmmss)
    }

    fun download(network: Network, items: List<RemoteMedia>, deleteAfter: Boolean, onProgress: (String) -> Unit): Result =
        ftp(network) { c ->
            val dest = destination()
            var ok = 0
            var failed = 0
            var deleted = 0
            items.forEachIndexed { i, item ->
                onProgress("Baixando ${i + 1}/${items.size}: ${item.name}")
                val written = runCatching { save(c, dest, item) }.getOrDefault(-1L)
                if (written == item.size) {
                    ok++
                    if (deleteAfter && c.deleteFile("/${item.name}")) deleted++
                } else {
                    failed++
                }
            }
            Result(ok, failed, deleted)
        }

    fun deleteRemote(network: Network, names: List<String>): Int = ftp(network) { c -> names.count { c.deleteFile("/$it") } }

    /** Baixa uma foto para o cache so para pre-visualizar (nao vai para a galeria). */
    fun preview(network: Network, item: RemoteMedia): File = ftp(network) { c ->
        File(context.cacheDir, "preview_${item.name}").also { f ->
            if (f.length() != item.size) f.outputStream().use { out -> check(c.retrieveFile("/${item.name}", out)) { "falha ao baixar" } }
        }
    }

    /** Copia o arquivo para o destino e devolve quantos bytes foram gravados (-1 em falha). */
    private fun save(c: FTPClient, dest: Destination, item: RemoteMedia): Long {
        val (uri, out) = createOutput(dest, item.name) ?: return -1
        val counting = CountingStream(out)
        val ok = counting.use { c.retrieveFile("/${item.name}", it) }
        if (!ok || counting.count != item.size) {
            runCatching { if (dest is Destination.Folder) DocumentFile.fromSingleUri(context, uri)?.delete() else resolver.delete(uri, null, null) }
            return -1
        }
        if (dest is Destination.Album) {
            resolver.update(uri, ContentValues().apply { put(MediaStore.MediaColumns.IS_PENDING, 0) }, null, null)
        }
        return counting.count
    }

    private fun createOutput(dest: Destination, name: String): Pair<Uri, OutputStream>? = when (dest) {
        is Destination.Album -> {
            val video = MediaTypes.isVideo(name)
            val values = ContentValues().apply {
                put(MediaStore.MediaColumns.DISPLAY_NAME, name)
                put(MediaStore.MediaColumns.MIME_TYPE, MediaTypes.mime(name))
                put(MediaStore.MediaColumns.RELATIVE_PATH, albumPath(dest.name, video))
                put(MediaStore.MediaColumns.IS_PENDING, 1) // invisivel na galeria ate terminar
            }
            val collection = if (video) MediaStore.Video.Media.EXTERNAL_CONTENT_URI else MediaStore.Images.Media.EXTERNAL_CONTENT_URI
            resolver.insert(collection, values)?.let { uri -> resolver.openOutputStream(uri)?.let { uri to it } }
        }
        is Destination.Folder -> {
            val dir = DocumentFile.fromTreeUri(context, dest.tree)
            dir?.findFile(name)?.delete()
            dir?.createFile(MediaTypes.mime(name), name)?.let { f -> resolver.openOutputStream(f.uri)?.let { f.uri to it } }
        }
    }

    // ------------------------------------------------------------------ celular
    fun listLocal(): List<LocalMedia> = when (val dest = destination()) {
        is Destination.Album -> queryAlbum(dest.name, video = false) + queryAlbum(dest.name, video = true)
        is Destination.Folder -> DocumentFile.fromTreeUri(context, dest.tree)?.listFiles().orEmpty()
            .filter { it.isFile && MediaTypes.isMedia(it.name ?: "") }
            .map { LocalMedia(it.name!!, it.uri, MediaTypes.isVideo(it.name!!), it.lastModified()) }
    }.sortedByDescending { it.name }

    private fun queryAlbum(album: String, video: Boolean): List<LocalMedia> {
        val collection = if (video) MediaStore.Video.Media.EXTERNAL_CONTENT_URI else MediaStore.Images.Media.EXTERNAL_CONTENT_URI
        val projection = arrayOf(MediaStore.MediaColumns._ID, MediaStore.MediaColumns.DISPLAY_NAME, MediaStore.MediaColumns.DATE_MODIFIED)
        val out = mutableListOf<LocalMedia>()
        resolver.query(collection, projection, "${MediaStore.MediaColumns.RELATIVE_PATH} = ?", arrayOf(albumPath(album, video) + "/"), null)
            ?.use { cur ->
                while (cur.moveToNext()) {
                    val uri = ContentUris.withAppendedId(collection, cur.getLong(0))
                    out += LocalMedia(cur.getString(1), uri, video, cur.getLong(2) * 1000)
                }
            }
        return out
    }

    private fun albumPath(album: String, video: Boolean) = if (video) "Movies/$album" else "Pictures/$album"

    private class CountingStream(private val inner: OutputStream) : OutputStream() {
        var count = 0L
            private set
        override fun write(b: Int) { inner.write(b); count++ }
        override fun write(b: ByteArray, off: Int, len: Int) { inner.write(b, off, len); count += len }
        override fun flush() = inner.flush()
        override fun close() = inner.close()
    }
}
