package com.m88suite.app.ui

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.media.MediaCodec
import android.media.MediaFormat
import android.view.Surface
import com.m88suite.core.H264

/**
 * Decodifica H.264 com o MediaCodec (hardware) direto numa Surface. Espera a primeira unidade com
 * SPS para configurar; o SPS/PPS seguinte segue em banda.
 */
class H264Renderer(private val surface: Surface, private val width: Int = 640, private val height: Int = 480) {
    private var codec: MediaCodec? = null
    private val info = MediaCodec.BufferInfo()
    private var ptsUs = 0L

    @Synchronized
    fun submit(unit: ByteArray) {
        val c = codec ?: if (H264.SPS in H264.nalTypes(unit)) start() else return
        val index = c.dequeueInputBuffer(10_000)
        if (index >= 0) {
            val buf = c.getInputBuffer(index) ?: return
            buf.clear()
            if (unit.size > buf.capacity()) {
                c.queueInputBuffer(index, 0, 0, ptsUs, 0)
                return
            }
            buf.put(unit)
            c.queueInputBuffer(index, 0, unit.size, ptsUs, 0)
            ptsUs += 66_000
        }
        drain(c)
    }

    private fun start(): MediaCodec {
        val format = MediaFormat.createVideoFormat(MediaFormat.MIMETYPE_VIDEO_AVC, width, height)
        format.setInteger(MediaFormat.KEY_LOW_LATENCY, 1)
        return MediaCodec.createDecoderByType(MediaFormat.MIMETYPE_VIDEO_AVC).also {
            it.configure(format, surface, null, 0)
            it.start()
            codec = it
        }
    }

    private fun drain(c: MediaCodec) {
        while (true) {
            val out = c.dequeueOutputBuffer(info, 0)
            if (out < 0) return
            c.releaseOutputBuffer(out, true)
        }
    }

    @Synchronized
    fun release() {
        runCatching { codec?.stop() }
        runCatching { codec?.release() }
        codec = null
    }
}

object JpegDecoder {
    fun decode(unit: ByteArray): Bitmap? = BitmapFactory.decodeByteArray(unit, 0, unit.size)
}
