"""Protocolo BLE do M88 (SDK keepfit do app OEM WheatAI).

Fonte: out/jadx_wheatai/sources/com/sxr/sdk/ble/keepfit/service/BluetoothLeService.java
e .../service/bean/SampleGattAttributes.java.
"""

SERVICE_UUID = "000056ff-0000-1000-8000-00805f9b34fb"
TX_UUID = "000033f3-0000-1000-8000-00805f9b34fb"   # escrita (app -> oculos)
RX_UUID = "000033f4-0000-1000-8000-00805f9b34fb"   # notify (oculos -> app)
RAW_TX_UUID = "000033f5-0000-1000-8000-00805f9b34fb"
RAW_RX_UUID = "000033f6-0000-1000-8000-00805f9b34fb"

HEADER = 0x54

# Comandos confirmados no SDK OEM (byte[1] do frame 0x54).
CMD_SET_WIFI_INFO = 0x01      # setWifiHotSpotInfo: SSID/senha em pedacos de 17 bytes
CMD_WIFI_STATE = 0x04         # usado pelo app Android; resposta 5404 02 <ip>
CMD_MEDIA_FILE_STATE = 0x05   # getMediaFileState
CMD_SCAN_WIFI = 0x08          # scanWifi (oculos escaneia e devolve SSIDs)
CMD_FTP_DOWNLOAD_DONE = 0x07  # notifyDownloadFtpFileCompleted (encerra o sync)
CMD_AI_CHAT_STATE = 0x0F      # setAiChatState(bool)
CMD_SYSTEM_STATE = 0x11       # getDeviceSystemStateInfo -> resposta 5412 <estado>
CMD_WIFI_AP_MODE = 0x13       # openWifiApMode -> 54 13 01
CMD_AI_CONN_METHOD = 0x14     # setAiConnectionMethod(int)

# Atalhos nomeados para a CLI/GUI.
NAMED = {
    "ap-on": (CMD_WIFI_AP_MODE, 0x01),
    "wifi-state": (CMD_WIFI_STATE, 0x01),
    "media-state": (CMD_MEDIA_FILE_STATE, 0x00),
    "scan-wifi": (CMD_SCAN_WIFI, 0x00),
    "system-state": (CMD_SYSTEM_STATE, 0x00),
    "ftp-done": (CMD_FTP_DOWNLOAD_DONE, 0x00),
}


def frame(cmd: int, mode: int = 0x01, payload: bytes = b"") -> bytes:
    data = bytes([HEADER, cmd & 0xFF, mode & 0xFF]) + payload
    if len(data) > 20:
        raise ValueError("frame M88 tem no maximo 20 bytes")
    return data.ljust(20, b"\x00")


def check_safe(data: bytes) -> None:
    """Recusa frames que podem reiniciar, resetar ou entrar em OTA.

    No SDK OEM, setDeviceMode (1=OTA, 3=restart, 4=factory reset) usa frames com
    byte[0]=0x0E. So frames 0x54 sao permitidos.
    """
    if not data:
        raise ValueError("frame vazio")
    if data[0] != HEADER:
        raise ValueError(
            f"frame com cabecalho 0x{data[0]:02X} bloqueado: apenas frames 0x54 sao permitidos "
            "(0x0E = modo do dispositivo: OTA/reinicio/reset de fabrica)"
        )


def parse_hex(text: str) -> bytes:
    clean = text.replace(" ", "").replace(":", "")
    data = bytes.fromhex(clean)
    if data and data[0] == HEADER and len(data) < 20:
        data = data.ljust(20, b"\x00")
    return data


def decode(data: bytes) -> str:
    """Interpretacao das notificacoes conhecidas. Marcadas como hipotese quando nao confirmadas."""
    if len(data) < 2 or data[0] != HEADER:
        return "frame fora do padrao 0x54"
    cmd, arg = data[1], data[2] if len(data) > 2 else None
    if cmd == CMD_WIFI_STATE and arg == 0x02 and len(data) >= 7:
        ip = ".".join(str(b) for b in data[3:7])
        return f"estado Wi-Fi: IP do oculos={ip}"
    if cmd == CMD_WIFI_AP_MODE:
        return f"modo AP: valor={arg} (2 observado como 'AP ativo')"
    if cmd == 0x12:
        return f"estado do sistema={arg} (8 observado com oculos conectado; bitmask OEM 1=video 2=audio 4=IA 8=transferencia)"
    if cmd == CMD_MEDIA_FILE_STATE:
        return f"estado de midia: bytes={data[2:8].hex()} (formato nao confirmado)"
    if cmd == CMD_SCAN_WIFI:
        text = bytes(b for b in data[3:] if 32 <= b < 127).decode("ascii", "ignore")
        return f"scan Wi-Fi: parte={arg} texto='{text}' (formato nao confirmado)"
    return f"cmd=0x{cmd:02X} arg={arg}"


# setDeviceMode(3) = "Reiniciar" no app OEM (FragmentSetting.OnClicktvRestart).
# Unico frame 0x0E liberado; o modo 4 (reset de fabrica) e o 1 (OTA) continuam bloqueados.
RESTART_FRAME = bytes.fromhex("0E123456789ABCDEF0").ljust(20, b"\x00")
