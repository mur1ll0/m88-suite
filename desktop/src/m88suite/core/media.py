"""Midia do cartao do oculos (FTP): listar, baixar com verificacao, apagar e pre-visualizar.

Mesmas regras do app Android (MediaRepository.kt): so apaga do oculos depois de conferir que o
arquivo baixado tem o mesmo tamanho do original. O firmware de fabrica aceita DELE (validado).
"""
from __future__ import annotations

import io
from dataclasses import dataclass
from ftplib import FTP, error_perm
from pathlib import Path
from typing import Callable

from .stock import ftp_media

PHOTO_EXT = {".jpg", ".jpeg", ".png", ".bmp"}
VIDEO_EXT = {".mp4", ".avi", ".mov", ".3gp"}


@dataclass(frozen=True)
class RemoteMedia:
    name: str
    size: int

    @property
    def is_video(self) -> bool:
        return Path(self.name).suffix.lower() in VIDEO_EXT


@dataclass
class DownloadResult:
    downloaded: int = 0
    failed: int = 0
    deleted: int = 0


def is_media(name: str) -> bool:
    return Path(name).suffix.lower() in PHOTO_EXT | VIDEO_EXT


def pretty_name(name: str) -> str:
    """'20261020024748.jpeg' -> '20/10/2026 02:47:48' (o oculos nomeia pela data/hora, em UTC)."""
    stem = Path(name).stem
    if len(stem) != 14 or not stem.isdigit():
        return name
    return f"{stem[6:8]}/{stem[4:6]}/{stem[0:4]} {stem[8:10]}:{stem[10:12]}:{stem[12:14]}"


def pretty_size(size: int) -> str:
    return f"{size / 1e6:.1f} MB" if size >= 1_000_000 else f"{size // 1000} KB"


class MediaClient:
    """Operacoes de midia sobre uma sessao FTP nova a cada chamada (o servidor do oculos e simples)."""

    def __init__(self, session: Callable[[], FTP] = ftp_media.ftp_session):
        self._session = session

    def _run(self, fn):
        ftp = self._session()
        try:
            return fn(ftp)
        finally:
            try:
                ftp.quit()
            except Exception:  # noqa: BLE001 - conexao ja encerrada pelo oculos
                ftp.close()

    def list_remote(self) -> list[RemoteMedia]:
        def run(ftp: FTP):
            files = []
            for name, facts in ftp.mlsd("/"):
                if facts.get("type") == "file" and is_media(name):
                    files.append(RemoteMedia(name, int(facts.get("size", 0) or 0)))
            return sorted(files, key=lambda m: m.name, reverse=True)
        try:
            return self._run(run)
        except error_perm:  # servidor sem MLSD: cai para LIST
            return sorted((RemoteMedia(Path(p).name, s) for p, s in ftp_media.ftp_list() if is_media(p)),
                          key=lambda m: m.name, reverse=True)

    def download(self, items: list[RemoteMedia], dest: Path, delete_after: bool,
                 on_progress: Callable[[str], None] = lambda s: None) -> DownloadResult:
        dest.mkdir(parents=True, exist_ok=True)

        def run(ftp: FTP):
            result = DownloadResult()
            for i, item in enumerate(items, 1):
                on_progress(f"Baixando {i}/{len(items)}: {pretty_name(item.name)}")
                target = dest / item.name
                partial = target.with_name(target.name + ".part")
                try:
                    with partial.open("wb") as f:
                        ftp.retrbinary(f"RETR /{item.name}", f.write, blocksize=32768)
                except Exception:  # noqa: BLE001 - falha de rede: conta e segue
                    partial.unlink(missing_ok=True)
                    result.failed += 1
                    continue
                if partial.stat().st_size != item.size:
                    partial.unlink(missing_ok=True)
                    result.failed += 1
                    continue
                partial.replace(target)
                result.downloaded += 1
                if delete_after and _delete(ftp, item.name):
                    result.deleted += 1
            return result
        return self._run(run)

    def delete_remote(self, names: list[str]) -> int:
        return self._run(lambda ftp: sum(_delete(ftp, n) for n in names))

    def preview(self, item: RemoteMedia) -> bytes:
        def run(ftp: FTP):
            buf = io.BytesIO()
            ftp.retrbinary(f"RETR /{item.name}", buf.write, blocksize=32768)
            return buf.getvalue()
        return self._run(run)


def _delete(ftp: FTP, name: str) -> bool:
    try:
        return ftp.delete(f"/{name}").startswith("250")
    except error_perm:
        return False


def local_files(folder: Path) -> list[Path]:
    if not folder.exists():
        return []
    return sorted((p for p in folder.iterdir() if p.is_file() and is_media(p.name)), key=lambda p: p.name, reverse=True)
