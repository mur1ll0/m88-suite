"""Testes de rede no M88: FTP (banner, PASV, listagem, download) e portas de streaming candidatas."""
import re
import socket
import time
from ftplib import FTP, error_perm
from pathlib import Path

from ..eventlog import event
from ..wifi import TARGET_IP

FTP_USER, FTP_PASS = "bk7258", "123456"

# Portas dos demos de video da Beken (armino/components/demos/media/doorbell/include/doorbell.h,
# armino/components/app/video_work/video_transfer_config.h) + portas comuns de stream.
TCP_CANDIDATES = [1114, 7150, 8050, 80, 554, 8080, 8554, 5000, 7000, 8899, 9000, 34567]
UDP_CMD_TO_IMG = [(7190, 7180), (8090, 8080), (10000, 52110)]

MEDIA_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".mp4", ".avi", ".mov", ".mkv", ".3gp", ".wav", ".mp3"}


class RecordingFTP(FTP):
    """FTP que guarda cada porta de dados anunciada na resposta 227 (PASV)."""

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.pasv_ports: list[int] = []
        self.pasv_replies: list[str] = []

    def makepasv(self):
        resp = self.sendcmd("PASV")
        self.pasv_replies.append(resp)
        nums = re.search(r"(\d+),(\d+),(\d+),(\d+),(\d+),(\d+)", resp)
        if not nums:
            raise error_perm(f"resposta PASV inesperada: {resp}")
        port = int(nums.group(5)) * 256 + int(nums.group(6))
        self.pasv_ports.append(port)
        # Usa o IP do controle (o oculos pode anunciar outro IP).
        return self.host, port


def ftp_session(timeout: float = 8.0) -> RecordingFTP:
    ftp = RecordingFTP()
    ftp.set_debuglevel(0)
    ftp.connect(TARGET_IP, 21, timeout=timeout)
    event("FTP", f"banner: {ftp.getwelcome()}")
    ftp.login(FTP_USER, FTP_PASS)
    ftp.set_pasv(True)
    return ftp


def walk(ftp: FTP, path: str = "/", depth: int = 0, out=None):
    out = [] if out is None else out
    if depth > 4 or len(out) > 2000:
        return out
    try:
        entries = list(ftp.mlsd(path))
        for name, facts in entries:
            if name in (".", ".."):
                continue
            full = path.rstrip("/") + "/" + name
            if facts.get("type") == "dir":
                walk(ftp, full, depth + 1, out)
            else:
                out.append((full, int(facts.get("size", 0) or 0)))
        return out
    except error_perm:
        pass
    lines: list[str] = []
    ftp.retrlines(f"LIST {path}", lines.append)
    for line in lines:
        parts = line.split(None, 8)
        if len(parts) < 9 or parts[8] in (".", ".."):
            continue
        full = path.rstrip("/") + "/" + parts[8]
        if line.startswith("d"):
            walk(ftp, full, depth + 1, out)
        else:
            size = int(parts[4]) if parts[4].isdigit() else 0
            out.append((full, size))
    return out


def ftp_pasv_test(rounds: int = 4) -> dict:
    ftp = ftp_session()
    try:
        for _ in range(rounds):
            ftp.nlst("/")
        ports = ftp.pasv_ports
        explains = 1114 in ports
        event("PASV", f"portas de dados anunciadas: {ports}" +
              (" -> 1114 E A PORTA DE DADOS DO FTP (nao e live)" if explains else ""), ports=ports)
        for r in ftp.pasv_replies[:2]:
            event("PASV", f"resposta: {r}")
        return {"ports": ports, "explains_1114": explains}
    finally:
        _close(ftp)


def ftp_list() -> list[tuple[str, int]]:
    ftp = ftp_session()
    try:
        files = walk(ftp, "/")
        media = [f for f in files if Path(f[0]).suffix.lower() in MEDIA_EXT]
        event("FTP", f"{len(files)} arquivos, {len(media)} de midia", count=len(files))
        for path, size in media[-30:]:
            event("FTP", f"  {path} ({size // 1024} KB)")
        return files
    finally:
        _close(ftp)


def ftp_get(remote: str, dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / Path(remote).name
    ftp = ftp_session(timeout=15)
    try:
        started = time.time()
        with dest.open("wb") as f:
            ftp.retrbinary(f"RETR {remote}", f.write, blocksize=32768)
        size = dest.stat().st_size
        secs = max(time.time() - started, 0.001)
        event("FTP", f"baixado {remote} -> {dest} ({size // 1024} KB, {size / secs / 1024:.0f} KB/s)",
              throughput_kbps=size / secs / 1024)
        return dest
    finally:
        _close(ftp)


def _close(ftp: FTP):
    try:
        ftp.quit()
    except Exception:
        ftp.close()


def tcp_probe(port: int, timeout: float = 0.6) -> tuple[bool, str | None]:
    try:
        with socket.create_connection((TARGET_IP, port), timeout=timeout) as s:
            s.settimeout(0.5)
            try:
                banner = s.recv(128)
                return True, banner.decode("ascii", "replace").strip() or banner.hex()
            except socket.timeout:
                return True, None
    except OSError:
        return False, None


def udp_probe(cmd_port: int, img_port: int, timeout: float = 1.5) -> int:
    payloads = [bytes.fromhex("5412010000000000000000000000000000000000"), b"start"]
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        try:
            s.bind(("", img_port))  # demos Beken enviam imagem para a porta de imagem do cliente
        except OSError:
            s.bind(("", 0))
        s.settimeout(timeout)
        for p in payloads:
            s.sendto(p, (TARGET_IP, cmd_port))
        data, addr = s.recvfrom(4096)
        return len(data)
    except OSError:
        return 0
    finally:
        s.close()


def port_sweep() -> dict:
    open_tcp = {}
    for port in TCP_CANDIDATES:
        ok, banner = tcp_probe(port)
        if ok:
            open_tcp[port] = banner
    udp = {}
    for cmd_port, img_port in UDP_CMD_TO_IMG:
        n = udp_probe(cmd_port, img_port)
        if n:
            udp[cmd_port] = n
    event("PORTS", f"TCP abertas: {open_tcp or 'nenhuma'} | UDP respostas: {udp or 'nenhuma'}",
          tcp=list(open_tcp), udp=list(udp))
    return {"tcp": open_tcp, "udp": udp}


def wait_port(port: int, seconds: float) -> float | None:
    """Espera a porta abrir; retorna os segundos ate abrir ou None."""
    started = time.time()
    while time.time() - started < seconds:
        if tcp_probe(port, timeout=0.5)[0]:
            took = round(time.time() - started, 1)
            event("PORTS", f"porta {port} abriu apos {took}s")
            return took
        time.sleep(0.3)
    event("PORTS", f"porta {port} nao abriu em {seconds:.0f}s")
    return None


def watch_ports(seconds: float, interval: float = 0.3) -> set[int]:
    """Varre as portas TCP candidatas repetidamente e registra qualquer porta que abrir."""
    event("WATCH", f"monitorando portas {TCP_CANDIDATES} por {seconds:.0f}s - use os botoes do oculos agora")
    seen: set[int] = set()
    deadline = time.time() + seconds
    while time.time() < deadline:
        for port in TCP_CANDIDATES:
            ok, banner = tcp_probe(port, timeout=0.15)
            if ok and port not in seen:
                seen.add(port)
                event("WATCH", f"PORTA {port} ABRIU banner={banner}", port=port)
        time.sleep(interval)
    event("WATCH", f"fim; portas que abriram: {sorted(seen) or 'nenhuma'}")
    return seen
