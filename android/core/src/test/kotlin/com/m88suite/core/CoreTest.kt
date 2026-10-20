package com.m88suite.core

import org.json.JSONObject
import java.io.File
import kotlin.test.Test
import kotlin.test.assertContentEquals
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertNull
import kotlin.test.assertTrue

class CoreTest {
    private val vectors = JSONObject(File(System.getProperty("m88.vectors")).readText())

    @Test
    fun m88pMatchesSharedVectors() {
        val list = vectors.getJSONArray("m88p")
        for (i in 0 until list.length()) {
            val v = list.getJSONObject(i)
            val tlv = v.getJSONArray("tlv").let { a ->
                (0 until a.length()).map { M88P.Tlv(a.getJSONObject(it).getInt("tag"), StockBle.hex(a.getJSONObject(it).getString("value"))) }
            }
            val frame = M88P.Frame(M88P.Type.entries[v.getInt("type")], v.getInt("seq"), v.getInt("cmd"), tlv)
            val hex = frame.encode().joinToString("") { "%02x".format(it) }
            assertEquals(v.getString("hex"), hex, v.getString("name"))
            assertEquals(frame, M88P.decode(StockBle.hex(hex)))
        }
    }

    @Test
    fun streamDecoderHandlesFragmentsAndJunk() {
        val list = vectors.getJSONArray("m88p")
        val stream = byteArrayOf(0, 1, 2) + (0 until list.length()).fold(ByteArray(0)) { acc, i ->
            acc + StockBle.hex(list.getJSONObject(i).getString("hex"))
        }
        val dec = M88P.StreamDecoder()
        val frames = stream.toList().chunked(3).flatMap { dec.feed(it.toByteArray()) }
        assertEquals(list.length(), frames.size)
    }

    @Test
    fun badCrcIsRejected() {
        val raw = StockBle.hex(vectors.getJSONArray("m88p").getJSONObject(0).getString("hex"))
        raw[raw.size - 1] = (raw.last().toInt() xor 0xFF).toByte()
        assertFailsWith<M88P.ProtocolError> { M88P.decode(raw) }
    }

    @Test
    fun crcVectors() {
        assertEquals(0x29B1, M88P.crc16("123456789".toByteArray()))
        val list = vectors.getJSONArray("doorbell_crc8")
        for (i in 0 until list.length()) {
            val v = list.getJSONObject(i)
            assertEquals(v.getInt("crc"), Doorbell.crc8(StockBle.hex(v.getString("data"))))
        }
    }

    @Test
    fun stockNotifications() {
        assertEquals(StockBle.Notification.Battery(38), StockBle.parse(StockBle.hex("0B26").copyOf(20)))
        assertEquals(StockBle.Notification.DeviceIp("192.168.48.1"), StockBle.parse(StockBle.hex("540402C0A83001").copyOf(20)))
        assertEquals(listOf("gravando vídeo", "transferência"),
            Telemetry().apply(StockBle.parse(StockBle.hex("541209").copyOf(20))!!).systemFlags)
        assertNull(StockBle.parse(byteArrayOf(0xF6.toByte(), 1)))
    }

    @Test
    fun boardingAndRestartAreRestricted() {
        assertContentEquals(StockBle.hex("04000000"), StockBle.boarding(4))
        assertFailsWith<IllegalArgumentException> { StockBle.boarding(10) }
        assertContentEquals(StockBle.hex("0E123456789ABCDEF0"), StockBle.RESTART_FRAME.copyOf(9))
    }

    @Test
    fun doorbellPackUnpack() {
        val cmd = Doorbell.command(Doorbell.CMD_CAMERA_ON, 1, Doorbell.cameraOnPayload(864, 480, 1))
        val pkt = Doorbell.Unpacker().feed(Doorbell.Packer().pack(cmd)).single()
        assertTrue(pkt.crcOk)
        assertContentEquals(cmd, pkt.payload)
    }

    @Test
    fun assemblerAndParamCache() {
        val asm = FrameAssembler()
        fun packets(fid: Int, data: ByteArray) = data.toList().chunked(30).let { cs ->
            cs.mapIndexed { i, c -> byteArrayOf(fid.toByte(), if (i == cs.size - 1) 1 else 0, (i + 1).toByte(), cs.size.toByte()) + c.toByteArray() }
        }
        assertContentEquals(ByteArray(100) { 7 }, packets(1, ByteArray(100) { 7 }).map { asm.push(it) }.last())
        packets(2, ByteArray(100)).filterIndexed { i, _ -> i != 1 }.forEach { assertNull(asm.push(it)) }
        assertEquals(1, asm.dropped)

        val cache = H264ParamCache()
        val spsPps = StockBle.hex("0000000167420000000168ce")
        val idr = StockBle.hex("000000016588")
        cache.fix(spsPps + idr)
        assertEquals(listOf(7, 8, 5), H264.nalTypes(cache.fix(idr)))
    }

    @Test
    fun backoff() {
        val b = Backoff(1.0, 8.0)
        assertEquals(listOf(1.0, 2.0, 4.0, 8.0, 8.0), List(5) { b.nextDelay() })
    }
}
