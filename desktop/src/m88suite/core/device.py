"""Tipos de estado e telemetria do oculos M88 (firmware de fabrica).

Roda um loop asyncio proprio numa thread. A UI chama os metodos publicos (thread-safe) e recebe
eventos pelos callbacks de `Listener`. Cuida de:
  - conexao BLE com reconexao (backoff exponencial);
  - Wi-Fi do PC no AP do oculos (sob demanda: video e midia);
  - sessao de video com watchdog: quadro parado -> reinicia o oculos e retoma o stream
    (o firmware de fabrica so abre o servico de video uma vez por boot).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field, replace
from enum import Enum

from .stock import ble_proto

DEFAULT_ADDRESS = "C8:47:8C:FD:52:2B"


class LinkState(str, Enum):
    DISCONNECTED = "Desconectado"
    CONNECTING = "Conectando"
    CONNECTED = "Conectado"
    RECONNECTING = "Reconectando"


class StreamState(str, Enum):
    OFF = "Desligado"
    STARTING = "Iniciando"
    LIVE = "Ao vivo"
    RECOVERING = "Recuperando"


@dataclass
class Telemetry:
    link: LinkState = LinkState.DISCONNECTED
    battery: int | None = None
    system_state: int | None = None
    wifi_ap: str | None = None
    wifi_pc: bool = False
    media_count: int | None = None
    stream: StreamState = StreamState.OFF
    fps: float = 0.0
    kbps: float = 0.0
    dropped: int = 0
    recoveries: int = 0
    message: str = ""
    updated: float = field(default_factory=time.time)

    @property
    def system_flags(self) -> list[str]:
        if not self.system_state:
            return []
        return [name for bit, name in ble_proto.SYSTEM_STATE_BITS.items() if self.system_state & bit]


def apply_notification(t: Telemetry, note: ble_proto.Notification) -> Telemetry:
    """Atualiza a telemetria a partir de uma notificacao BLE ja interpretada."""
    changes = {"updated": time.time()}
    if note.kind == "battery":
        changes["battery"] = note.value
    elif note.kind == "system_state":
        changes["system_state"] = note.value
    elif note.kind == "ap_state":
        changes["wifi_ap"] = str(note.value)
    elif note.kind == "media_count":
        changes["media_count"] = note.value
    return replace(t, **changes)