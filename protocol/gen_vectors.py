"""Gera protocol/vectors.json a partir da implementacao de referencia em Python.

Uso: desktop/.venv/Scripts/python protocol/gen_vectors.py
Os testes em C (firmware) e Kotlin (android) verificam contra este arquivo.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "desktop" / "src"))

from m88suite.core import m88p  # noqa: E402
from m88suite.core.stock import doorbell  # noqa: E402

T, C = m88p.Tag, m88p.Cmd
CASES = [
    ("get_status_req", m88p.FrameType.REQ, 1, C.GET_STATUS, []),
    ("status_rsp", m88p.FrameType.RSP, 1, C.GET_STATUS,
     [(T.BATTERY, m88p.u8(72)), (T.CHARGING, m88p.u8(0)), (T.WIFI, m88p.u8(1)), (T.CAMERA, m88p.u8(1))]),
    ("camera_start_req", m88p.FrameType.REQ, 7, C.CAMERA_START,
     [(T.CODEC, m88p.u8(1)), (T.WIDTH, m88p.u16(1280)), (T.HEIGHT, m88p.u16(720)), (T.FPS, m88p.u8(25)),
      (T.BITRATE_KBPS, m88p.u16(2500)), (T.TRANSPORT, m88p.u8(0))]),
    ("button_evt", m88p.FrameType.EVT, 300, C.EVT_BUTTON, [(T.GESTURE, m88p.u8(2)), (T.ACTION, m88p.u8(5))]),
    ("info_rsp", m88p.FrameType.RSP, 65535, C.GET_INFO, [(T.FW_VERSION, b"m88suite-0.1.0")]),
]


def main():
    vectors = {"m88p": [], "doorbell_crc8": []}
    for name, ftype, seq, cmd, tlv in CASES:
        frame = m88p.Frame(ftype, seq, cmd, tlv)
        vectors["m88p"].append({"name": name, "type": int(ftype), "seq": seq, "cmd": int(cmd),
                                "tlv": [{"tag": int(t), "value": v.hex()} for t, v in tlv],
                                "hex": frame.encode().hex()})
    for data in (b"", b"\x03\x00\x00\x00\x00\x00\x00\x00\x00\x00", bytes(range(32))):
        vectors["doorbell_crc8"].append({"data": data.hex(), "crc": doorbell.crc8(data)})
    out = ROOT / "protocol" / "vectors.json"
    out.write_text(json.dumps(vectors, indent=2) + "\n", encoding="utf-8")
    print(f"{out}: {len(vectors['m88p'])} frames M88P, {len(vectors['doorbell_crc8'])} CRC8")


if __name__ == "__main__":
    main()
