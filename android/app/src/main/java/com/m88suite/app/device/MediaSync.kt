package com.m88suite.app.device

import android.content.ContentValues
import android.content.Context
import android.net.Network
import android.provider.MediaStore
import org.apache.commons.net.ftp.FTP
import org.apache.commons.net.ftp.FTPClient

/** Copia fotos e videos novos do cartao do oculos (FTP) para a galeria do celular. */
class MediaSync(private val context: Context) {
    private val prefs = context.getSharedPreferences("m88_media", Context.MODE_PRIVATE)
    private val photoExt = setOf("jpg", "jpeg", "png", "bmp")
    private val videoExt = setOf("mp4", "avi", "mov", "3gp")

    data class Result(val downloaded: Int, val total: Int)

    fun sync(network: Network, onProgress: (String) -> Unit): Result {
        val ftp = FTPClient().apply {
            setSocketFactory(network.socketFactory)
            connectTimeout = 5_000
            defaultTimeout = 8_000
        }
        try {
            ftp.connect(WifiLink.DEVICE_IP, 21)
            check(ftp.login("bk7258", "123456")) { "login FTP recusado" }
            ftp.enterLocalPassiveMode()
            ftp.setFileType(FTP.BINARY_FILE_TYPE)
            val media = ftp.listFiles("/").filter { it.isFile && ext(it.name) in photoExt + videoExt }
            val pending = media.filter { !prefs.getBoolean(it.name, false) }
            pending.forEachIndexed { i, file ->
                onProgress("Baixando ${i + 1}/${pending.size}: ${file.name}")
                if (download(ftp, file.name)) prefs.edit().putBoolean(file.name, true).apply()
            }
            onProgress("Sincronizado: ${pending.size} novo(s), ${media.size} no óculos")
            return Result(pending.size, media.size)
        } finally {
            runCatching { ftp.logout() }
            runCatching { ftp.disconnect() }
        }
    }

    private fun download(ftp: FTPClient, name: String): Boolean {
        val isVideo = ext(name) in videoExt
        val collection = if (isVideo) MediaStore.Video.Media.EXTERNAL_CONTENT_URI else MediaStore.Images.Media.EXTERNAL_CONTENT_URI
        val values = ContentValues().apply {
            put(MediaStore.MediaColumns.DISPLAY_NAME, name)
            put(MediaStore.MediaColumns.MIME_TYPE, mime(name))
            put(MediaStore.MediaColumns.RELATIVE_PATH, if (isVideo) "Movies/M88" else "Pictures/M88")
        }
        val uri = context.contentResolver.insert(collection, values) ?: return false
        val ok = context.contentResolver.openOutputStream(uri)?.use { out ->
            ftp.retrieveFile("/$name", out)
        } ?: false
        if (!ok) context.contentResolver.delete(uri, null, null)
        return ok
    }

    private fun ext(name: String) = name.substringAfterLast('.', "").lowercase()

    private fun mime(name: String) = when (ext(name)) {
        "jpg", "jpeg" -> "image/jpeg"
        "png" -> "image/png"
        "bmp" -> "image/bmp"
        "mp4" -> "video/mp4"
        "mov" -> "video/quicktime"
        "3gp" -> "video/3gpp"
        else -> "video/x-msvideo"
    }
}
