"""Protocolo BLE do firmware de fabrica (SDK keepfit do WheatAI + boarding Beken).

Validado no dispositivo em 2026-10-20. Ver docs/PROTOCOL.md, secao 1.
"""
from __future__ import annotations

from dataclasses import dataclass

SERVICE_UUID = "000056ff-0000-1000-8000-00805f9b34fb"
TX_UUID = "000033f3-0000-1000-8000-00805f9b34fb"
RX_UUID = "000033f4-0000-1000-8000-00805f9b34fb"
BOARDING_OP_UUID = "0000ea02-0000-1000-8000-00805f9b34fb"
BOARDING_NTF_UUID = "0000ea01-0000-1000-8000-00805f9b34fb"

HEADER = 0x54
CMD_WIFI_STATE = 0x04
CMD_MEDIA_COUNT = 0x05
CMD_SYSTEM_STATE = 0x11
CMD_AP_MODE = 0x13

RSP_WIFI_STATE = 0x04
RSP_MEDIA_COUNT = 0x06
RSP_SYSTEM_STATE = 0x12
RSP_AP_MODE = 0x13
NTF_BATTERY = 0x0B

BOARDING_UDP_SERVICE = 3
BOARDING_TCP_SERVICE = 4

# setDeviceMode(3) = botao "Reiniciar" do WheatAI. Modos 1 (OTA) e 4 (reset de fabrica) nunca.
RESTART_FRAME = bytes.fromhex("0E123456789ABCDEF0").ljust(20, b"\x00")


def frame(cmd: int, arg: int = 0x00) -> bytes:
    return bytes([HEADER, cmd & 0xFF, arg & 0xFF]).ljust(20, b"\x00")


def boarding(opcode: int, data: bytes = b"") -> bytes:
    if opcode not in (BOARDING_UDP_SERVICE, BOARDING_TCP_SERVICE):
        # 1/2 mudam a configuracao Wi-Fi, 5-9 CS2/P2P, 10 desliga o BLE ate o proximo boot.
        raise ValueError(f"opcode de boarding {opcode} nao permitido")
    return opcode.to_bytes(2, "little") + len(data).to_bytes(2, "little") + data


SYSTEM_STATE_BITS = {1: "gravando vídeo", 2: "gravando áudio", 4: "chat IA", 8: "transferência"}


@dataclass
class Notification:
    kind: str
    value: object = None


def parse(data: bytes) -> Notification | None:
    """Interpreta uma notificacao de RX_UUID. Retorna None para frames sem significado conhecido."""
    if not data:
        return None
    if data[0] == NTF_BATTERY and len(data) >= 2:
        return Notification("battery", data[1]) if data[1] <= 100 else None
    if data[0] != HEADER or len(data) < 3:
        return None
    cmd, arg = data[1], data[2]
    if cmd == RSP_SYSTEM_STATE:
        return Notification("system_state", arg)
    if cmd == RSP_AP_MODE:
        return Notification("ap_state", "client" if arg == 2 else "on" if arg == 1 else arg)
    if cmd == RSP_WIFI_STATE and arg == 2 and len(data) >= 7:
        return Notification("device_ip", ".".join(str(b) for b in data[3:7]))
    if cmd == RSP_MEDIA_COUNT:
        return Notification("media_count", arg)
    return None
