"""Regras de midia sem o oculos: so apaga depois de conferir o tamanho baixado."""
from ftplib import error_perm

from m88suite.core.media import MediaClient, RemoteMedia, pretty_name, pretty_size


class FakeFTP:
    """FTP em memoria; `truncate` simula um download que veio incompleto."""

    def __init__(self, files: dict[str, bytes], truncate: set[str] = frozenset()):
        self.files, self.truncate, self.deleted = dict(files), truncate, []

    def mlsd(self, path):
        return [(n, {"type": "file", "size": str(len(d))}) for n, d in self.files.items()]

    def retrbinary(self, cmd, callback, blocksize=8192):
        name = cmd.split("/", 1)[1]
        data = self.files[name]
        callback(data[: len(data) // 2] if name in self.truncate else data)

    def delete(self, path):
        name = path.lstrip("/")
        if name not in self.files:
            raise error_perm("550 not found")
        del self.files[name]
        self.deleted.append(name)
        return "250 File deleted successfully."

    def quit(self):
        pass

    close = quit


def make(fake):
    return MediaClient(session=lambda: fake)


def test_list_only_media_newest_first():
    fake = FakeFTP({"20261020024529.mp4": b"v" * 10, "20260505163326.jpeg": b"f", "notes.txt": b"x"})
    names = [m.name for m in make(fake).list_remote()]
    assert names == ["20261020024529.mp4", "20260505163326.jpeg"]


def test_download_verifies_size_before_deleting(tmp_path):
    fake = FakeFTP({"a.jpeg": b"1" * 100, "b.jpeg": b"2" * 100}, truncate={"b.jpeg"})
    items = [RemoteMedia("a.jpeg", 100), RemoteMedia("b.jpeg", 100)]
    result = make(fake).download(items, tmp_path, delete_after=True)
    assert (result.downloaded, result.failed, result.deleted) == (1, 1, 1)
    assert fake.deleted == ["a.jpeg"]  # o incompleto continua no oculos
    assert (tmp_path / "a.jpeg").read_bytes() == b"1" * 100
    assert not (tmp_path / "b.jpeg").exists() and not list(tmp_path.glob("*.part"))


def test_download_keeps_files_when_delete_disabled(tmp_path):
    fake = FakeFTP({"a.jpeg": b"1" * 10})
    make(fake).download([RemoteMedia("a.jpeg", 10)], tmp_path, delete_after=False)
    assert fake.deleted == [] and "a.jpeg" in fake.files


def test_delete_remote_counts_successes():
    fake = FakeFTP({"a.jpeg": b"1"})
    assert make(fake).delete_remote(["a.jpeg", "missing.jpeg"]) == 1


def test_pretty_helpers():
    assert pretty_name("20261020024748.jpeg") == "20/10/2026 02:47:48"
    assert pretty_name("foto.jpg") == "foto.jpg"
    assert pretty_size(4_103_723) == "4.1 MB" and pretty_size(298_458) == "298 KB"
