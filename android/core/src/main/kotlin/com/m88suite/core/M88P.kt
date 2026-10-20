package com.m88suite.core

/** M88P v1 — protocolo do firmware M88 Suite (docs/PROTOCOL.md). Espelho de m88suite.core.m88p. */
object M88P {
    const val VERSION = 1
    const val HEADER_SIZE = 10
    const val CRC_SIZE = 2
    private val MAGIC = byteArrayOf('M'.code.toByte(), '8'.code.toByte())

    enum class Type(val code: Int) { REQ(0), RSP(1), EVT(2) }

    class ProtocolError(message: String) : IllegalArgumentException(message)

    data class Tlv(val tag: Int, val value: ByteArray) {
        override fun equals(other: Any?) = other is Tlv && tag == other.tag && value.contentEquals(other.value)
        override fun hashCode() = 31 * tag + value.contentHashCode()
    }

    data class Frame(val type: Type, val seq: Int, val cmd: Int, val tlv: List<Tlv> = emptyList()) {
        fun get(tag: Int): ByteArray? = tlv.firstOrNull { it.tag == tag }?.value

        fun encode(): ByteArray {
            val payload = encodeTlv(tlv)
            val out = ByteArray(HEADER_SIZE + payload.size + CRC_SIZE)
            MAGIC.copyInto(out, 0)
            out[2] = VERSION.toByte()
            out[3] = type.code.toByte()
            putU16(out, 4, seq)
            putU16(out, 6, cmd)
            putU16(out, 8, payload.size)
            payload.copyInto(out, HEADER_SIZE)
            putU16(out, HEADER_SIZE + payload.size, crc16(out, 0, HEADER_SIZE + payload.size))
            return out
        }
    }

    fun decode(data: ByteArray): Frame {
        if (data.size < HEADER_SIZE + CRC_SIZE) throw ProtocolError("frame curto")
        if (data[0] != MAGIC[0] || data[1] != MAGIC[1]) throw ProtocolError("magic invalido")
        if (data[2].toInt() != VERSION) throw ProtocolError("versao ${data[2]} nao suportada")
        val length = u16(data, 8)
        val end = HEADER_SIZE + length
        if (data.size < end + CRC_SIZE) throw ProtocolError("frame incompleto")
        if (u16(data, end) != crc16(data, 0, end)) throw ProtocolError("CRC invalido")
        val type = Type.entries.firstOrNull { it.code == data[3].toInt() } ?: throw ProtocolError("tipo invalido")
        return Frame(type, u16(data, 4), u16(data, 6), decodeTlv(data.copyOfRange(HEADER_SIZE, end)))
    }

    fun encodeTlv(items: List<Tlv>): ByteArray {
        val out = java.io.ByteArrayOutputStream()
        for (item in items) {
            if (item.value.size > 255) throw ProtocolError("TLV ${item.tag} maior que 255 bytes")
            out.write(item.tag)
            out.write(item.value.size)
            out.write(item.value)
        }
        return out.toByteArray()
    }

    fun decodeTlv(data: ByteArray): List<Tlv> {
        val items = mutableListOf<Tlv>()
        var i = 0
        while (i < data.size) {
            if (i + 2 > data.size) throw ProtocolError("TLV truncado")
            val tag = data[i].toInt() and 0xFF
            val len = data[i + 1].toInt() and 0xFF
            if (i + 2 + len > data.size) throw ProtocolError("TLV $tag truncado")
            items += Tlv(tag, data.copyOfRange(i + 2, i + 2 + len))
            i += 2 + len
        }
        return items
    }

    /** CRC-16/CCITT-FALSE (poly 0x1021, init 0xFFFF). */
    fun crc16(data: ByteArray, from: Int = 0, to: Int = data.size): Int {
        var crc = 0xFFFF
        for (i in from until to) {
            crc = crc xor ((data[i].toInt() and 0xFF) shl 8)
            repeat(8) { crc = if (crc and 0x8000 != 0) (crc shl 1) xor 0x1021 else crc shl 1 }
            crc = crc and 0xFFFF
        }
        return crc
    }

    /** Remonta frames de um fluxo (TCP, USB ou fragmentos BLE). */
    class StreamDecoder {
        private var buf = ByteArray(0)

        fun feed(data: ByteArray): List<Frame> {
            buf += data
            val frames = mutableListOf<Frame>()
            while (true) {
                val start = indexOfMagic(buf)
                if (start < 0) {
                    buf = if (buf.isNotEmpty() && buf.last() == MAGIC[0]) byteArrayOf(MAGIC[0]) else ByteArray(0)
                    break
                }
                buf = buf.copyOfRange(start, buf.size)
                if (buf.size < HEADER_SIZE) break
                val total = HEADER_SIZE + u16(buf, 8) + CRC_SIZE
                if (buf.size < total) break
                try {
                    frames += decode(buf.copyOfRange(0, total))
                    buf = buf.copyOfRange(total, buf.size)
                } catch (e: ProtocolError) {
                    buf = buf.copyOfRange(2, buf.size)
                }
            }
            return frames
        }

        private fun indexOfMagic(b: ByteArray): Int {
            for (i in 0 until b.size - 1) if (b[i] == MAGIC[0] && b[i + 1] == MAGIC[1]) return i
            return -1
        }
    }

    internal fun u16(b: ByteArray, off: Int) = (b[off].toInt() and 0xFF) or ((b[off + 1].toInt() and 0xFF) shl 8)

    internal fun putU16(b: ByteArray, off: Int, v: Int) {
        b[off] = (v and 0xFF).toByte()
        b[off + 1] = ((v shr 8) and 0xFF).toByte()
    }
}
