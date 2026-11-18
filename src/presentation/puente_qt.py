"""Puente entre el bus de eventos (hilos cualquiera) y la interfaz Qt (hilo principal).

Los eventos publicados desde hilos de impresión o del sincronizador se re-emiten como una
señal Qt; al conectarse con QueuedConnection a métodos de widgets, se ejecutan en el hilo
de la interfaz de forma segura."""
from PySide6.QtCore import QObject, Qt, Signal


class PuenteEventos(QObject):
    evento = Signal(str, object)

    def __init__(self, bus):
        super().__init__()
        bus.suscribir("*", self._reenviar)

    def _reenviar(self, nombre: str, datos) -> None:
        self.evento.emit(nombre, datos)

    def escuchar(self, receptor) -> None:
        """`receptor` debe ser un método ligado de un QObject: receptor(nombre, datos)."""
        self.evento.connect(receptor, Qt.ConnectionType.QueuedConnection)
