"""Decodificacao de video (JPEG/H.264) para QImage e saida opcional para webcam virtual."""
from __future__ import annotations

import logging
import queue
import threading

import numpy as np
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QImage

log = logging.getLogger(__name__)


class VideoDecoder(QObject):
    """Recebe unidades de video (qualquer thread) e emite `image` com o quadro decodificado.

    A decodificacao roda numa thread propria; a fila guarda so os quadros mais recentes para que
    a tela nunca acumule atraso.
    """

    image = Signal(QImage)

    def __init__(self):
        super().__init__()
        self._queue: queue.Queue[tuple[bytes, str]] = queue.Queue(maxsize=8)
        self._codec = None
        self.webcam: VirtualWebcam | None = None
        threading.Thread(target=self._run, name="m88-decoder", daemon=True).start()

    def submit(self, unit: bytes, codec: str):
        try:
            self._queue.put_nowait((unit, codec))
        except queue.Full:
            if codec == "jpeg":  # em H.264 descartar quebraria a referencia dos quadros P
                return
            self._queue.get_nowait()
            self._queue.put_nowait((unit, codec))

    def _run(self):
        while True:
            unit, codec = self._queue.get()
            try:
                for rgb in self._decode(unit, codec):
                    h, w, _ = rgb.shape
                    img = QImage(rgb.data, w, h, 3 * w, QImage.Format_RGB888).copy()
                    self.image.emit(img)
                    if self.webcam:
                        self.webcam.send(rgb)
            except Exception as e:  # quadro corrompido por perda de pacote
                log.debug("quadro descartado: %s", e)

    def _decode(self, unit: bytes, codec: str):
        if codec == "jpeg":
            img = QImage.fromData(unit, "JPG").convertToFormat(QImage.Format_RGB888)
            if img.isNull():
                return
            ptr = img.constBits()
            arr = np.frombuffer(ptr, np.uint8, img.sizeInBytes()).reshape(img.height(), img.bytesPerLine())
            yield np.ascontiguousarray(arr[:, : img.width() * 3].reshape(img.height(), img.width(), 3))
            return
        if self._codec is None:
            import av
            self._codec = av.CodecContext.create("h264", "r")
        for packet in self._codec.parse(unit):
            for frame in self._codec.decode(packet):
                yield frame.to_ndarray(format="rgb24")


class VirtualWebcam:
    """Envia quadros para a camera virtual do OBS (aparece como webcam no Meet/Zoom/Teams)."""

    def __init__(self, width: int = 640, height: int = 480, fps: int = 15):
        import pyvirtualcam
        self.width, self.height = width, height
        self._cam = pyvirtualcam.Camera(width=width, height=height, fps=fps, backend="obs")
        self.device = self._cam.device

    def send(self, rgb: np.ndarray):
        if rgb.shape[1] != self.width or rgb.shape[0] != self.height:
            img = QImage(rgb.data, rgb.shape[1], rgb.shape[0], 3 * rgb.shape[1], QImage.Format_RGB888)
            img = img.scaled(self.width, self.height).convertToFormat(QImage.Format_RGB888)
            arr = np.frombuffer(img.constBits(), np.uint8, img.sizeInBytes())
            rgb = arr.reshape(self.height, img.bytesPerLine())[:, : self.width * 3].reshape(self.height, self.width, 3)
        self._cam.send(np.ascontiguousarray(rgb))

    def close(self):
        self._cam.close()
