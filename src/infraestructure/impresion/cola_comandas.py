"""Paradigma concurrente: productor/consumidor.

La UI (productor) deja comandas en una cola por área; un hilo trabajador por área
(cocina y bar) las consume y las "imprime" (archivo .txt) sin bloquear la interfaz."""
import logging
import queue
import threading
import time
from datetime import datetime

from src.config import settings
from src.infraestructure.eventos import bus_eventos as ev

log = logging.getLogger("comandas")
_FIN = object()  # centinela para detener los hilos


class ColaComandas:
    AREAS = ("cocina", "bar")

    def __init__(self, bus, demora_impresion: float = 1.0):
        self.bus = bus
        self.demora = demora_impresion
        self._colas = {area: queue.Queue() for area in self.AREAS}
        self._hilos: list[threading.Thread] = []
        self._consecutivo = 0
        self._lock = threading.Lock()

    def iniciar(self) -> None:
        settings.DIR_COMANDAS.mkdir(parents=True, exist_ok=True)
        for area in self.AREAS:
            hilo = threading.Thread(target=self._trabajador, args=(area,), name=f"impresora-{area}", daemon=True)
            hilo.start()
            self._hilos.append(hilo)
        log.info("Cola de comandas iniciada (%s)", ", ".join(self.AREAS))

    def detener(self) -> None:
        for cola in self._colas.values():
            cola.put(_FIN)
        for hilo in self._hilos:
            hilo.join(timeout=3)
        self._hilos.clear()

    def enviar(self, pedido, items) -> None:
        """Divide los items por área de preparación (polimorfismo de Producto) y encola."""
        por_area: dict[str, list] = {}
        for item in items:
            por_area.setdefault(item.producto.area_preparacion(), []).append(
                (item.cantidad, item.producto.nombre, item.nota))
        for area, lineas in por_area.items():
            with self._lock:
                self._consecutivo += 1
                numero = self._consecutivo
            self._colas[area].put({"numero": numero, "area": area, "mesa": pedido.mesa_numero,
                                   "mesero": pedido.mesero, "lineas": lineas, "hora": datetime.now()})

    def pendientes(self) -> dict[str, int]:
        return {area: c.qsize() for area, c in self._colas.items()}

    def _trabajador(self, area: str) -> None:
        cola = self._colas[area]
        while True:
            comanda = cola.get()
            if comanda is _FIN:
                cola.task_done()
                break
            try:
                time.sleep(self.demora)  # simula el tiempo de impresión
                ruta = self._imprimir(comanda)
                self.bus.publicar(ev.COMANDA_IMPRESA, {**comanda, "archivo": str(ruta)})
            except Exception:
                log.exception("Error imprimiendo comanda")
            finally:
                cola.task_done()

    @staticmethod
    def _imprimir(c: dict):
        texto = [f"===== COMANDA {c['area'].upper()} #{c['numero']} =====",
                 f"Mesa: {c['mesa']}   Mesero: {c['mesero']}",
                 f"Hora: {c['hora']:%H:%M:%S}", "-" * 34]
        for cantidad, nombre, nota in c["lineas"]:
            texto.append(f"{cantidad:>2} x {nombre}")
            if nota:
                texto.append(f"     * {nota}")
        texto.append("=" * 34)
        ruta = settings.DIR_COMANDAS / f"{c['hora']:%H%M%S}_{c['area']}_{c['numero']:04d}.txt"
        ruta.write_text("\n".join(texto), encoding="utf-8")
        log.info("Comanda %s #%d impresa (mesa %s)", c["area"], c["numero"], c["mesa"])
        return ruta
