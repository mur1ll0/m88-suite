"""Leva eventos do DeviceManager (thread propria) para a UI via sinais Qt."""
from PySide6.QtCore import QObject, Signal

from ..core.manager import Listener


class DeviceBridge(QObject):
    telemetry = Signal(object)
    frame = Signal(bytes, str)
    log = Signal(str)

    def listener(self) -> Listener:
        # emit() e seguro entre threads: o Qt entrega na thread da UI (conexao enfileirada).
        return Listener(on_telemetry=self.telemetry.emit, on_frame=self.frame.emit, on_log=self.log.emit)
