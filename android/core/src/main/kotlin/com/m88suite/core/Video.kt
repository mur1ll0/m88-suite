package com.m88suite.core

/** Junta pacotes {id, eof, cnt, total} em quadros; descarta quadros incompletos (perda UDP). */
class FrameAssembler(private val maxPending: Int = 3) {
    private val parts = LinkedHashMap<Int, MutableMap<Int, ByteArray>>()
    var dropped = 0
        private set

    fun push(payload: ByteArray): ByteArray? {
        if (payload.size < 4) return null
        val fid = payload[0].toInt() and 0xFF
        val eof = payload[1].toInt() != 0
        val cnt = payload[2].toInt() and 0xFF
        val total = payload[3].toInt() and 0xFF
        while (parts.size >= maxPending && fid !in parts) {
            parts.remove(parts.keys.first())
            dropped++
        }
        parts.getOrPut(fid) { HashMap() }[cnt] = payload.copyOfRange(4, payload.size)
        if (!eof) return null
        val chunks = parts.remove(fid)!!
        if (total != 0 && chunks.size < total) {
            dropped++
            return null
        }
        return chunks.toSortedMap().values.fold(ByteArray(0)) { acc, c -> acc + c }
    }
}

object H264 {
    const val SPS = 7
    const val PPS = 8
    const val IDR = 5
    private val START = byteArrayOf(0, 0, 0, 1)

    fun nalTypes(unit: ByteArray): List<Int> = startCodes(unit).mapNotNull { i ->
        if (i + 4 < unit.size) unit[i + 4].toInt() and 0x1F else null
    }

    fun startCodes(unit: ByteArray): List<Int> {
        val out = mutableListOf<Int>()
        var i = 0
        while (i + 3 < unit.size) {
            if (unit[i] == START[0] && unit[i + 1] == START[1] && unit[i + 2] == START[2] && unit[i + 3] == START[3]) {
                out += i
                i += 4
            } else {
                i++
            }
        }
        return out
    }

    fun findNal(unit: ByteArray, type: Int): Int =
        startCodes(unit).firstOrNull { it + 4 < unit.size && unit[it + 4].toInt() and 0x1F == type } ?: -1
}

/** Guarda SPS/PPS e reinjeta antes de IDRs que chegarem sem eles. */
class H264ParamCache {
    var params: ByteArray = ByteArray(0)
        private set

    fun fix(unit: ByteArray): ByteArray {
        val types = H264.nalTypes(unit)
        if (H264.SPS in types) {
            val idr = H264.findNal(unit, H264.IDR)
            params = if (idr >= 0) unit.copyOfRange(0, idr) else unit
            return unit
        }
        return if (H264.IDR in types && params.isNotEmpty()) params + unit else unit
    }
}

class Backoff(private val initial: Double = 1.0, private val maximum: Double = 20.0, private val factor: Double = 2.0) {
    var attempts = 0
        private set

    fun nextDelay(): Double = minOf(initial * Math.pow(factor, attempts.toDouble()), maximum).also { attempts++ }

    fun reset() {
        attempts = 0
    }
}
