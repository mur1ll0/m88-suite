"""M88P v1: protocolo de controle do firmware M88 Suite (ver docs/PROTOCOL.md).

Implementacao de referencia; gera protocol/vectors.json usado pelos testes em C e Kotlin.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field
from enum import IntEnum

MAGIC = b"M8"
VERSION = 1
HEADER = struct.Struct("<2sBBHHH")  # magic, version, type, seq, cmd, len
HEADER_SIZE = HEADER.size  # 10
CRC_SIZE = 2


class FrameType(IntEnum):
    REQ = 0
    RSP = 1
    EVT = 2


class Cmd(IntEnum):
    GET_INFO = 0x0001
    GET_STATUS = 0x0002
    SET_CONFIG = 0x0003
    CAMERA_START = 0x0010
    CAMERA_STOP = 0x0011
    CAMERA_KEYFRAME = 0x0012
    PHOTO = 0x0020
    RECORD_START = 0x0021
    RECORD_STOP = 0x0022
    BUTTONS_GET = 0x0030
    BUTTONS_SET = 0x0031
    FILE_LIST = 0x0040
    FILE_READ = 0x0041
    FILE_DELETE = 0x0042
    OTA_BEGIN = 0x0050
    OTA_DATA = 0x0051
    OTA_END = 0x0052
    AUDIO_ROUTE = 0x0060
    REBOOT = 0x00F0
    EVT_STATUS_CHANGED = 0x8001
    EVT_BUTTON = 0x8002
    EVT_MEDIA_ADDED = 0x8003
    EVT_STREAM_STATS = 0x8004
    EVT_ERROR = 0x80FF


class Tag(IntEnum):
    BATTERY = 0x01
    CHARGING = 0x02
    LED = 0x03
    FLASHLIGHT = 0x04
    WIFI = 0x05
    BT = 0x06
    CAMERA = 0x07
    CODEC = 0x10
    WIDTH = 0x11
    HEIGHT = 0x12
    FPS = 0x13
    BITRATE_KBPS = 0x14
    TRANSPORT = 0x15
    STATUS = 0x20
    FW_VERSION = 0x21
    GESTURE = 0x30
    ACTION = 0x31


class ProtocolError(ValueError):
    pass


def crc16_ccitt(data: bytes, crc: int = 0xFFFF) -> int:
    """CRC-16/CCITT-FALSE (poly 0x1021, init 0xFFFF, sem reflexao)."""
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if crc & 0x8000 else (crc << 1)
            crc &= 0xFFFF
    return crc


def tlv_encode(items: list[tuple[int, bytes]]) -> bytes:
    out = bytearray()
    for tag, value in items:
        if len(value) > 255:
            raise ProtocolError(f"TLV {tag:#x} maior que 255 bytes")
        out += bytes([tag, len(value)]) + value
    return bytes(out)


def tlv_decode(data: bytes) -> list[tuple[int, bytes]]:
    items, i = [], 0
    while i < len(data):
        if i + 2 > len(data):
            raise ProtocolError("TLV truncado")
        tag, length = data[i], data[i + 1]
        if i + 2 + length > len(data):
            raise ProtocolError(f"TLV {tag:#x} truncado")
        items.append((tag, data[i + 2:i + 2 + length]))
        i += 2 + length
    return items


def u8(v: int) -> bytes:
    return struct.pack("<B", v)


def u16(v: int) -> bytes:
    return struct.pack("<H", v)


@dataclass
class Frame:
    type: FrameType
    seq: int
    cmd: int
    tlv: list[tuple[int, bytes]] = field(default_factory=list)

    def encode(self) -> bytes:
        payload = tlv_encode(self.tlv)
        head = HEADER.pack(MAGIC, VERSION, int(self.type), self.seq & 0xFFFF, self.cmd & 0xFFFF, len(payload))
        body = head + payload
        return body + struct.pack("<H", crc16_ccitt(body))

    def get(self, tag: int, default: bytes | None = None) -> bytes | None:
        return next((v for t, v in self.tlv if t == tag), default)

    @classmethod
    def decode(cls, data: bytes) -> "Frame":
        if len(data) < HEADER_SIZE + CRC_SIZE:
            raise ProtocolError("frame curto")
        magic, version, ftype, seq, cmd, length = HEADER.unpack_from(data)
        if magic != MAGIC:
            raise ProtocolError("magic invalido")
        if version != VERSION:
            raise ProtocolError(f"versao {version} nao suportada")
        end = HEADER_SIZE + length
        if len(data) < end + CRC_SIZE:
            raise ProtocolError("frame incompleto")
        (crc,) = struct.unpack_from("<H", data, end)
        if crc != crc16_ccitt(data[:end]):
            raise ProtocolError("CRC invalido")
        return cls(FrameType(ftype), seq, cmd, tlv_decode(data[HEADER_SIZE:end]))


class StreamDecoder:
    """Remonta frames M88P de um fluxo (TCP, USB CDC ou fragmentos BLE)."""

    def __init__(self):
        self._buf = bytearray()

    def feed(self, data: bytes) -> list[Frame]:
        self._buf += data
        frames = []
        while True:
            start = self._buf.find(MAGIC)
            if start < 0:
                keep = self._buf[-1:] if self._buf[-1:] == MAGIC[:1] else b""
                self._buf[:] = keep  # o ultimo byte pode ser o inicio de um magic cortado
                break
            del self._buf[:start]
            if len(self._buf) < HEADER_SIZE:
                break
            length = struct.unpack_from("<H", self._buf, 8)[0]
            total = HEADER_SIZE + length + CRC_SIZE
            if len(self._buf) < total:
                break
            raw = bytes(self._buf[:total])
            try:
                frames.append(Frame.decode(raw))
                del self._buf[:total]
            except ProtocolError:
                del self._buf[:2]  # ressincroniza a partir do proximo magic
        return frames
