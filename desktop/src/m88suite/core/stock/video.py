"""Recepcao de video do servico doorbell (firmware de fabrica): TCP 7150 ou UDP 7180."""
from __future__ import annotations

import socket
import threading
import time
from dataclasses import dataclass
from typing import Callable

from . import doorbell as db

START_CODE = b"\x00\x00\x00\x01"
NAL_SPS, NAL_PPS, NAL_IDR = 7, 8, 5


@dataclass
class StreamConfig:
    codec: str = "h264"  # "h264" ou "jpeg"
    width: int = 864  # 640x480 nao gera quadros no firmware de fabrica; 864x480 chega como 640x480
    height: int = 480
    transport: str = "udp"  # "udp" (melhor com perda) ou "tcp"

    @property
    def fmt(self) -> int:
        return 1 if self.codec == "h264" else 0


@dataclass
class StreamStats:
    frames: int = 0
    dropped: int = 0
    bytes: int = 0
    started: float = 0.0
    last_frame: float = 0.0

    def fps(self, window_start: float | None = None) -> float:
        elapsed = time.time() - (window_start or self.started)
        return self.frames / elapsed if self.started and elapsed > 0 else 0.0


class FrameAssembler:
    """Junta pacotes {id, eof, cnt, total} em quadros; descarta quadros incompletos."""

    MAX_PENDING = 3

    def __init__(self):
        self._parts: dict[int, dict[int, bytes]] = {}
        self.dropped = 0

    def push(self, payload: bytes) -> bytes | None:
        if len(payload) < 4:
            return None
        fid, eof, cnt, total = payload[0], payload[1], payload[2], payload[3]
        while len(self._parts) >= self.MAX_PENDING and fid not in self._parts:
            self._parts.pop(next(iter(self._parts)))
            self.dropped += 1
        self._parts.setdefault(fid, {})[cnt] = payload[4:]
        if not eof:
            return None
        chunks = self._parts.pop(fid)
        if total and len(chunks) < total:
            self.dropped += 1
            return None
        return b"".join(chunks[k] for k in sorted(chunks))


def nal_types(unit: bytes) -> list[int]:
    types, i = [], unit.find(START_CODE)
    while i >= 0 and i + 4 < len(unit):
        types.append(unit[i + 4] & 0x1F)
        i = unit.find(START_CODE, i + 4)
    return types


class H264ParamCache:
    """Guarda SPS/PPS e os reinjeta antes de IDRs que chegarem sem eles (perda de pacote UDP)."""

    def __init__(self):
        self.params = b""

    def fix(self, unit: bytes) -> bytes:
        types = nal_types(unit)
        if NAL_SPS in types:
            idr = _find_nal(unit, NAL_IDR)
            self.params = unit[:idr] if idr >= 0 else unit
            return unit
        if NAL_IDR in types and self.params:
            return self.params + unit
        return unit


def _find_nal(unit: bytes, nal_type: int) -> int:
    i = unit.find(START_CODE)
    while i >= 0:
        if i + 4 < len(unit) and unit[i + 4] & 0x1F == nal_type:
            return i
        i = unit.find(START_CODE, i + 4)
    return -1


class VideoSession:
    """Liga a camera via TCP 7100 e entrega cada quadro (JPEG ou unidade H.264) em on_frame.

    Roda em thread propria. `stalled` fica True quando nao chega quadro por STALL_SECONDS.
    """

    STALL_SECONDS = 4.0
    HELLO_INTERVAL = 2.0

    def __init__(self, ip: str, config: StreamConfig, on_frame: Callable[[bytes], None]):
        self.ip, self.config, self.on_frame = ip, config, on_frame
        self.stats = StreamStats()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.error: str | None = None

    @property
    def stalled(self) -> bool:
        ref = self.stats.last_frame or self.stats.started
        return bool(ref) and time.time() - ref > self.STALL_SECONDS

    def start(self):
        self._thread = threading.Thread(target=self._run, name="m88-video", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 3.0):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout)

    def _run(self):
        try:
            self._loop()
        except OSError as e:
            self.error = str(e)

    def _open_image_socket(self, packer: db.Packer) -> socket.socket:
        if self.config.transport == "udp":
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4 << 20)
            s.bind(("", db.UDP_IMG_PORT))
            s.settimeout(0.5)
            s.sendto(packer.pack(b"\x00"), (self.ip, db.UDP_IMG_PORT))
            return s
        s = socket.create_connection((self.ip, db.IMG_PORT), timeout=3)
        s.settimeout(1.0)
        return s

    def _loop(self):
        packer = db.Packer()
        cmd = socket.create_connection((self.ip, db.CMD_PORT), timeout=3)
        img = self._open_image_socket(packer)
        assembler, h264 = FrameAssembler(), H264ParamCache()
        unpacker = db.Unpacker()
        try:
            cmd.sendall(packer.pack(db.command(
                db.DBCMD_SET_CAMERA_TURN_ON, db.CAMERA_ID_DVP,
                db.camera_on_payload(self.config.width, self.config.height, self.config.fmt, 0, 0))))
            self.stats.started = last_hello = time.time()
            udp = self.config.transport == "udp"
            while not self._stop.is_set():
                if udp and time.time() - last_hello > self.HELLO_INTERVAL:
                    img.sendto(packer.pack(b"\x00"), (self.ip, db.UDP_IMG_PORT))
                    last_hello = time.time()
                try:
                    data = img.recv(65536)
                except (socket.timeout, ConnectionResetError):
                    continue
                if not data:
                    if not udp:
                        raise OSError("conexao de imagem fechada pelo oculos")
                    continue
                self.stats.bytes += len(data)
                if udp:
                    unpacker = db.Unpacker()  # cada datagrama e um pacote completo
                for packet in unpacker.feed(data):
                    unit = assembler.push(packet["payload"])
                    self.stats.dropped = assembler.dropped
                    if unit is None:
                        continue
                    if self.config.codec == "jpeg" and unit[:2] != b"\xff\xd8":
                        continue
                    if self.config.codec == "h264":
                        unit = h264.fix(unit)
                    self.stats.frames += 1
                    self.stats.last_frame = time.time()
                    self.on_frame(unit)
        finally:
            try:
                cmd.sendall(packer.pack(db.command(db.DBCMD_SET_CAMERA_TURN_OFF, db.CAMERA_ID_DVP)))
            except OSError:
                pass
            cmd.close()
            img.close()
