"""Testes do nucleo (sem hardware): protocolos, montagem de quadros e reconexao."""
import json
from pathlib import Path

import pytest

from m88suite.core import m88p
from m88suite.core.backoff import Backoff
from m88suite.core.device import Telemetry, apply_notification
from m88suite.core.stock import ble_proto, doorbell
from m88suite.core.stock.video import FrameAssembler, H264ParamCache, nal_types

VECTORS = json.loads((Path(__file__).parents[2] / "protocol" / "vectors.json").read_text(encoding="utf-8"))


def test_m88p_vectors_roundtrip():
    for v in VECTORS["m88p"]:
        frame = m88p.Frame(m88p.FrameType(v["type"]), v["seq"], v["cmd"],
                           [(t["tag"], bytes.fromhex(t["value"])) for t in v["tlv"]])
        assert frame.encode().hex() == v["hex"], v["name"]
        assert m88p.Frame.decode(bytes.fromhex(v["hex"])) == frame


def test_m88p_rejects_bad_crc():
    raw = bytearray(bytes.fromhex(VECTORS["m88p"][0]["hex"]))
    raw[-1] ^= 0xFF
    with pytest.raises(m88p.ProtocolError):
        m88p.Frame.decode(bytes(raw))


def test_m88p_stream_decoder_resyncs_across_chunks():
    frames = [bytes.fromhex(v["hex"]) for v in VECTORS["m88p"]]
    stream = b"\x00junk" + b"".join(frames)
    dec = m88p.StreamDecoder()
    out = []
    for i in range(0, len(stream), 3):  # fragmentado como em BLE
        out += dec.feed(stream[i:i + 3])
    assert [f.cmd for f in out] == [v["cmd"] for v in VECTORS["m88p"]]


def test_crc_vectors():
    assert m88p.crc16_ccitt(b"123456789") == 0x29B1
    for v in VECTORS["doorbell_crc8"]:
        assert doorbell.crc8(bytes.fromhex(v["data"])) == v["crc"]


def test_ble_parse_known_notifications():
    assert ble_proto.parse(bytes.fromhex("0B26" + "00" * 18)).value == 38
    assert ble_proto.parse(bytes.fromhex("541208" + "00" * 17)).value == 8
    assert ble_proto.parse(bytes.fromhex("540402C0A83001" + "00" * 13)).value == "192.168.48.1"
    assert ble_proto.parse(bytes.fromhex("540607" + "00" * 17)).value == 7
    assert ble_proto.parse(b"\xF6\x01") is None


def test_boarding_only_allows_video_services():
    assert ble_proto.boarding(4) == bytes.fromhex("04000000")
    for forbidden in (1, 2, 9, 10):
        with pytest.raises(ValueError):
            ble_proto.boarding(forbidden)


def test_restart_frame_is_mode_3_only():
    assert ble_proto.RESTART_FRAME[:9] == bytes.fromhex("0E123456789ABCDEF0")
    assert ble_proto.RESTART_FRAME != bytes.fromhex("0E1234123412341234").ljust(20, b"\x00")


def test_doorbell_pack_unpack():
    pk = doorbell.Packer()
    cmd = doorbell.command(doorbell.DBCMD_SET_CAMERA_TURN_ON, 1, doorbell.camera_on_payload(864, 480, 1, 0, 0))
    frames = doorbell.Unpacker().feed(pk.pack(cmd))
    assert frames[0]["crc_ok"] and frames[0]["payload"] == cmd


def _packets(fid: int, data: bytes, size: int):
    chunks = [data[i:i + size] for i in range(0, len(data), size)]
    return [bytes([fid, int(i == len(chunks) - 1), i + 1, len(chunks)]) + c for i, c in enumerate(chunks)]


def test_frame_assembler_complete_and_lost_packet():
    asm = FrameAssembler()
    pkts = _packets(1, b"A" * 100, 30)
    assert [asm.push(p) for p in pkts][-1] == b"A" * 100
    lost = _packets(2, b"B" * 100, 30)
    del lost[1]
    assert all(asm.push(p) is None for p in lost)
    assert asm.dropped == 1


def test_h264_param_cache_reinjects_sps_pps():
    sps_pps = b"\x00\x00\x00\x01\x67\x42" + b"\x00\x00\x00\x01\x68\xce"
    idr = b"\x00\x00\x00\x01\x65\x88"
    cache = H264ParamCache()
    assert cache.fix(sps_pps + idr) == sps_pps + idr
    assert nal_types(cache.fix(idr)) == [7, 8, 5]
    p_frame = b"\x00\x00\x00\x01\x41\x9a"
    assert cache.fix(p_frame) == p_frame


def test_backoff_grows_and_caps():
    b = Backoff(1, 8)
    assert [b.next_delay() for _ in range(5)] == [1, 2, 4, 8, 8]
    b.reset()
    assert b.next_delay() == 1


def test_telemetry_from_notifications():
    t = apply_notification(Telemetry(), ble_proto.parse(bytes.fromhex("541209" + "00" * 17)))
    assert t.system_flags == ["gravando vídeo", "transferência"]
