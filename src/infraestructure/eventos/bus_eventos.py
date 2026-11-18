"""Paradigma orientado a eventos: bus de publicación/suscripción (thread-safe).

Los publicadores no conocen a los suscriptores. La interfaz Qt se suscribe a través de
`src/presentation/puente_qt.py`, que re-emite los eventos como señales al hilo de la UI."""
import logging
import threading
from collections import defaultdict
from typing import Any, Callable

log = logging.getLogger("eventos")

# Catálogo de eventos del sistema
MESA_CAMBIADA = "mesa_cambiada"
MESA_SELECCIONADA = "mesa_seleccionada"
PEDIDO_ACTUALIZADO = "pedido_actualizado"
COMANDA_ENVIADA = "comanda_enviada"
COMANDA_IMPRESA = "comanda_impresa"
FACTURA_EMITIDA = "factura_emitida"
TICKET_IMPRESO = "ticket_impreso"
STOCK_BAJO = "stock_bajo"
INVENTARIO_ACTUALIZADO = "inventario_actualizado"
CAJA_ABIERTA = "caja_abierta"
CAJA_CERRADA = "caja_cerrada"
RESPALDO_REALIZADO = "respaldo_realizado"
DASHBOARD_TICK = "dashboard_tick"
SESION_INICIADA = "sesion_iniciada"


class BusEventos:
    _instancia = None
    _lock_instancia = threading.Lock()

    def __new__(cls):  # Singleton
        with cls._lock_instancia:
            if cls._instancia is None:
                cls._instancia = super().__new__(cls)
                cls._instancia._suscriptores = defaultdict(list)
                cls._instancia._lock = threading.RLock()
        return cls._instancia

    def suscribir(self, evento: str, manejador: Callable[[Any], None]) -> None:
        with self._lock:
            if manejador not in self._suscriptores[evento]:
                self._suscriptores[evento].append(manejador)

    def desuscribir(self, evento: str, manejador: Callable[[Any], None]) -> None:
        with self._lock:
            if manejador in self._suscriptores[evento]:
                self._suscriptores[evento].remove(manejador)

    def publicar(self, evento: str, datos: Any = None) -> None:
        """Los suscriptores a un evento reciben (datos); los suscritos a '*' reciben (evento, datos)."""
        with self._lock:
            llamadas = [(m, (datos,)) for m in self._suscriptores[evento]]
            llamadas += [(m, (evento, datos)) for m in self._suscriptores["*"]]
        if evento != DASHBOARD_TICK:
            log.debug("evento %s -> %d suscriptores", evento, len(llamadas))
        for manejador, args in llamadas:
            try:
                manejador(*args)
            except Exception:  # un suscriptor con error no debe tumbar a los demás
                log.exception("Error en manejador de %s", evento)

    def limpiar(self) -> None:
        with self._lock:
            self._suscriptores.clear()


bus = BusEventos()
