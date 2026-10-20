"""Registro de eventos: console + arquivo JSONL em captures/desktop/ para analise posterior."""
import json
import threading
import time
from datetime import datetime
from pathlib import Path

CAPTURE_DIR = Path.home() / "M88Suite" / "logs"

_lock = threading.Lock()
_listeners = []
_session_file: Path | None = None


def session_file() -> Path:
    global _session_file
    if _session_file is None:
        CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
        _session_file = CAPTURE_DIR / f"m88_{datetime.now():%Y%m%d_%H%M%S}.jsonl"
    return _session_file


def add_listener(fn):
    """fn(line: str) recebe cada linha formatada (usado pela GUI)."""
    _listeners.append(fn)


def event(tag: str, message: str, **data):
    ts = time.time()
    line = f"{datetime.fromtimestamp(ts):%H:%M:%S.%f}"[:-3] + f" [{tag}] {message}"
    record = {"ts": ts, "tag": tag, "msg": message, **data}
    with _lock:
        print(line, flush=True)
        with session_file().open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    for fn in list(_listeners):
        try:
            fn(line)
        except Exception:
            pass
