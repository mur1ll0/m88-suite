"""DeviceManager: conexao, telemetria, video e midia do M88 (firmware de fabrica).

Toda a I/O roda num loop asyncio em thread propria; os metodos publicos sao thread-safe e
retornam `concurrent.futures.Future`. A UI recebe dados pelos callbacks do `Listener`.
"""
from __future__ import annotations

import asyncio
import logging
import threading
from concurrent.futures import Future
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Callable

from . import wifi
from .backoff import Backoff
from .ble_client import M88Ble
from .device import LinkState, StreamState, Telemetry, apply_notification
from .stock import ble_proto, ftp_media
from .stock.doorbell import CMD_PORT
from .stock.video import StreamConfig, VideoSession

log = logging.getLogger(__name__)

DEFAULT_ADDRESS = "C8:47:8C:FD:52:2B"


@dataclass
class Listener:
    on_telemetry: Callable[[Telemetry], None] = lambda t: None
    on_frame: Callable[[bytes, str], None] = lambda unit, codec: None
    on_log: Callable[[str], None] = lambda line: None


class DeviceManager:
    KEEPALIVE_S = 4.0
    WATCHDOG_S = 1.0
    MAX_RECOVERIES = 3

    def __init__(self, listener: Listener, address: str = DEFAULT_ADDRESS):
        self.listener, self.address = listener, address
        self.telemetry = Telemetry()
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, name="m88-manager", daemon=True)
        self._thread.start()
        self._ble: M88Ble | None = None
        self._want_link = False
        self._link_task: asyncio.Task | None = None
        self._video: VideoSession | None = None
        self._stream_cfg: StreamConfig | None = None
        self._watchdog: asyncio.Task | None = None
        self._video_used_this_boot = False

    # ------------------------------------------------------------------ API publica
    def connect(self) -> Future:
        return self._submit(self._start_link())

    def disconnect(self) -> Future:
        return self._submit(self._stop_link())

    def start_stream(self, config: StreamConfig) -> Future:
        return self._submit(self._start_stream(config))

    def stop_stream(self) -> Future:
        return self._submit(self._stop_stream())

    def restart_device(self) -> Future:
        return self._submit(self._restart_device())

    def sync_media(self, dest: Path, on_progress: Callable[[str], None] = lambda s: None) -> Future:
        return self._submit(self._sync_media(dest, on_progress))

    def shutdown(self, timeout: float = 5.0):
        try:
            self._submit(self._stop_link()).result(timeout)
        except Exception:
            pass
        self._loop.call_soon_threadsafe(self._loop.stop)

    # ------------------------------------------------------------------ internos
    def _submit(self, coro) -> Future:
        return asyncio.run_coroutine_threadsafe(coro, self._loop)

    def _update(self, **changes):
        self.telemetry = replace(self.telemetry, **changes)
        self.listener.on_telemetry(self.telemetry)

    def _say(self, message: str):
        log.info(message)
        self.listener.on_log(message)
        self._update(message=message)

    def _on_notify(self, _uuid: str, data: bytes):
        note = ble_proto.parse(data)
        if note:
            self.telemetry = apply_notification(self.telemetry, note)
            self.listener.on_telemetry(self.telemetry)

    @property
    def _ble_ok(self) -> bool:
        return bool(self._ble and self._ble.connected)

    # ---- link BLE
    async def _start_link(self):
        self._want_link = True
        if not self._link_task or self._link_task.done():
            self._link_task = asyncio.create_task(self._link_loop())

    async def _stop_link(self):
        self._want_link = False
        await self._stop_stream()
        if self._link_task:
            self._link_task.cancel()
        if self._ble:
            try:
                await self._ble.disconnect()
            except Exception:
                pass
        self._ble = None
        self._update(link=LinkState.DISCONNECTED)

    async def _link_loop(self):
        backoff = Backoff(1.0, 20.0)
        while self._want_link:
            if not self._ble_ok:
                first = self.telemetry.link == LinkState.DISCONNECTED
                self._update(link=LinkState.CONNECTING if first else LinkState.RECONNECTING)
                try:
                    await self._open_ble()
                    backoff.reset()
                    self._update(link=LinkState.CONNECTED)
                    self._say("Bluetooth conectado")
                except Exception as e:
                    delay = backoff.next_delay()
                    self._say(f"Bluetooth indisponivel ({e}); nova tentativa em {delay:.0f}s")
                    await asyncio.sleep(delay)
                    continue
            try:
                await self._ble.send(ble_proto.frame(ble_proto.CMD_WIFI_STATE, 0x01), "keepalive")
            except Exception:
                pass  # a queda e detectada por _ble_ok na proxima volta
            await asyncio.sleep(self.KEEPALIVE_S)

    async def _open_ble(self):
        ble = M88Ble(self.address)
        ble.on_notify = self._on_notify
        await ble.connect(scan_timeout=8)
        self._ble = ble
        await ble.send(ble_proto.frame(ble_proto.CMD_SYSTEM_STATE), "system-state")
        await ble.send(ble_proto.frame(ble_proto.CMD_MEDIA_COUNT), "media-count")

    async def _wait_ble(self, timeout: float = 30.0):
        await self._start_link()
        for _ in range(int(timeout * 2)):
            if self._ble_ok:
                return
            await asyncio.sleep(0.5)
        raise RuntimeError("oculos nao conectou pelo Bluetooth")

    # ---- Wi-Fi do PC no AP do oculos
    async def _ensure_wifi(self):
        await self._wait_ble()
        if wifi.on_m88_subnet():
            self._update(wifi_pc=True)
            return
        await self._ble.send(ble_proto.frame(ble_proto.CMD_AP_MODE, 0x01), "ap-on")
        await asyncio.sleep(1.0)
        if not await asyncio.to_thread(wifi.connect, 40):
            self._update(wifi_pc=False)
            raise RuntimeError("PC nao entrou na rede Wi-Fi do oculos")
        await self._ble.send(ble_proto.frame(ble_proto.CMD_SYSTEM_STATE), "system-state")
        self._update(wifi_pc=True)

    # ---- reinicio
    async def _restart_device(self):
        await self._wait_ble()
        self._say("Reiniciando o oculos...")
        await self._ble.restart_device()
        self._video_used_this_boot = False
        self._update(wifi_pc=False)
        await asyncio.sleep(3.0)
        await self._wait_ble(60)
        self._say("Oculos reiniciado")

    # ---- video
    async def _start_stream(self, config: StreamConfig):
        await self._stop_stream()
        self._stream_cfg = config
        self._update(stream=StreamState.STARTING, recoveries=0)
        try:
            await self._open_video(config)
        except Exception as e:
            self._update(stream=StreamState.OFF)
            self._say(f"Falha ao iniciar video: {e}")
            raise
        self._watchdog = asyncio.create_task(self._video_watchdog())

    async def _open_video(self, config: StreamConfig):
        if self._video_used_this_boot:
            await self._restart_device()  # o servico de video so abre uma vez por boot
        await self._ensure_wifi()
        opcode = ble_proto.BOARDING_UDP_SERVICE if config.transport == "udp" else ble_proto.BOARDING_TCP_SERVICE
        await self._ble.client.write_gatt_char(ble_proto.BOARDING_OP_UUID, ble_proto.boarding(opcode), response=True)
        self._video_used_this_boot = True
        if await asyncio.to_thread(ftp_media.wait_port, CMD_PORT, 15) is None:
            raise RuntimeError("servico de video nao respondeu")
        await asyncio.sleep(1.0)
        self._video = VideoSession(wifi.TARGET_IP, config, lambda unit: self.listener.on_frame(unit, config.codec))
        self._video.start()
        self._update(stream=StreamState.LIVE)
        self._say(f"Video ao vivo ({config.codec.upper()} {config.transport.upper()})")

    async def _close_video(self):
        if self._video:
            await asyncio.to_thread(self._video.stop)
            self._video = None

    async def _stop_stream(self):
        if self._watchdog:
            self._watchdog.cancel()
            self._watchdog = None
        self._stream_cfg = None
        await self._close_video()
        if self.telemetry.stream != StreamState.OFF:
            self._update(stream=StreamState.OFF, fps=0.0, kbps=0.0)

    async def _video_watchdog(self):
        last_frames = last_bytes = 0
        while self._stream_cfg:
            await asyncio.sleep(self.WATCHDOG_S)
            video = self._video
            if not video:
                continue
            st = video.stats
            self._update(fps=(st.frames - last_frames) / self.WATCHDOG_S,
                         kbps=(st.bytes - last_bytes) * 8 / 1000 / self.WATCHDOG_S, dropped=st.dropped)
            last_frames, last_bytes = st.frames, st.bytes
            if video.stalled or video.error:
                await self._recover_video()
                last_frames = last_bytes = 0

    async def _recover_video(self):
        attempt = self.telemetry.recoveries + 1
        if attempt > self.MAX_RECOVERIES:
            self._say("Video nao recuperou; aproxime o oculos e inicie de novo")
            await self._stop_stream()
            return
        self._update(stream=StreamState.RECOVERING, recoveries=attempt)
        self._say(f"Video parado; recuperando ({attempt}/{self.MAX_RECOVERIES})")
        await self._close_video()
        try:
            await self._open_video(self._stream_cfg)
        except Exception as e:
            self._say(f"Recuperacao falhou: {e}")

    # ---- midia
    async def _sync_media(self, dest: Path, on_progress: Callable[[str], None]) -> int:
        await self._ensure_wifi()
        dest.mkdir(parents=True, exist_ok=True)
        files = await asyncio.to_thread(ftp_media.ftp_list)
        media = [(p, size) for p, size in files if Path(p).suffix.lower() in ftp_media.MEDIA_EXT]
        new = [(p, size) for p, size in media if not (dest / Path(p).name).exists()]
        self._update(media_count=len(media))
        for i, (remote, _size) in enumerate(new, 1):
            on_progress(f"Baixando {i}/{len(new)}: {Path(remote).name}")
            await asyncio.to_thread(ftp_media.ftp_get, remote, dest)
        on_progress(f"Sincronizado: {len(new)} novo(s), {len(media)} no oculos")
        return len(new)
