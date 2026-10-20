"""Conexao do Wi-Fi do PC ao AP do M88 via netsh (Windows)."""
import socket
import subprocess
import tempfile
import time
from pathlib import Path

from .eventlog import event

SSID = "M88-522B"
PASSWORD = "12345678"
TARGET_IP = "192.168.48.1"

PROFILE_XML = """<?xml version="1.0"?>
<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
  <name>{ssid}</name>
  <SSIDConfig><SSID><name>{ssid}</name></SSID><nonBroadcast>true</nonBroadcast></SSIDConfig>
  <connectionType>ESS</connectionType>
  <connectionMode>manual</connectionMode>
  <MSM><security>
    <authEncryption><authentication>WPA2PSK</authentication><encryption>AES</encryption><useOneX>false</useOneX></authEncryption>
    <sharedKey><keyType>passPhrase</keyType><protected>false</protected><keyMaterial>{password}</keyMaterial></sharedKey>
  </security></MSM>
</WLANProfile>
"""


def _netsh(*args: str) -> str:
    out = subprocess.run(["netsh", "wlan", *args], capture_output=True, text=True, encoding="oem", errors="replace")
    return (out.stdout + out.stderr).strip()


def interface_status() -> dict:
    text = _netsh("show", "interfaces")
    info = {}
    for line in text.splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            info.setdefault(key.strip().lower(), value.strip())
    radio_off = "software off" in text.lower()
    return {"raw": text, "radio_off": radio_off, "name": info.get("name", "Wi-Fi"),
            "state": info.get("state"), "ssid": info.get("ssid")}


def local_ip_toward(target: str = TARGET_IP) -> str | None:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect((target, 9))
            return s.getsockname()[0]
    except OSError:
        return None


def on_m88_subnet() -> bool:
    ip = local_ip_toward()
    return bool(ip and ip.startswith("192.168.48."))


def connect(timeout: float = 30.0, ssid: str = SSID, password: str = PASSWORD) -> bool:
    status = interface_status()
    if status["radio_off"]:
        event("WIFI", "o radio Wi-Fi do PC esta DESLIGADO (Software Off). Ligue o Wi-Fi no Windows e repita.")
        return False
    if on_m88_subnet():
        event("WIFI", f"ja na rede do M88 (IP local {local_ip_toward()})")
        return True

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / f"{ssid}.xml"
        path.write_text(PROFILE_XML.format(ssid=ssid, password=password), encoding="utf-8")
        event("WIFI", "perfil: " + _netsh("add", "profile", f"filename={path}", f"interface={status['name']}", "user=current"))
    event("WIFI", "connect: " + _netsh("connect", f"name={ssid}", f"ssid={ssid}", f"interface={status['name']}"))

    deadline = time.time() + timeout
    while time.time() < deadline:
        if on_m88_subnet():
            event("WIFI", f"conectado ao {ssid}; IP local {local_ip_toward()}")
            return True
        time.sleep(1.0)
    st = interface_status()
    event("WIFI", f"sem IP 192.168.48.x apos {timeout:.0f}s (estado={st['state']} ssid={st['ssid']}). "
                  "O AP do oculos so sobe apos o comando BLE ap-on.")
    return False


def disconnect():
    status = interface_status()
    event("WIFI", "disconnect: " + _netsh("disconnect", f"interface={status['name']}"))
