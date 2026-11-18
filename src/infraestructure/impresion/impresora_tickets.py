"""Paradigma concurrente: impresión de tickets en segundo plano con un pool de hilos.
`imprimir` retorna un Future inmediatamente; al terminar se publica TICKET_IMPRESO."""
import logging
import time
from concurrent.futures import Future, ThreadPoolExecutor

from src.config import settings
from src.infraestructure.eventos import bus_eventos as ev

log = logging.getLogger("tickets")


def _m(v: float) -> str:
    return f"${v:,.0f}".replace(",", ".")


def formatear_ticket(f) -> str:
    ancho = 40
    lineas = [settings.NOMBRE_NEGOCIO.center(ancho), f"NIT {settings.NIT}".center(ancho), "=" * ancho,
              f"Factura N° {f.numero}", f"Fecha: {f.fecha:%Y-%m-%d %H:%M}",
              f"Mesa: {f.mesa_numero}   Cajero: {f.cajero}", "-" * ancho]
    for l in f.lineas:
        izq = f"{l['cantidad']} x {l['producto']}"[:28]
        lineas.append(f"{izq:<28}{_m(l['subtotal']):>12}")
    lineas.append("-" * ancho)
    lineas.append(f"{'Subtotal':<28}{_m(f.subtotal):>12}")
    for nombre, valor in f.descuentos:
        lineas.append(f"{nombre[:27]:<28}{'-' + _m(valor):>12}")
    lineas.append(f"{'Impoconsumo 8%':<28}{_m(f.impuesto):>12}")
    lineas.append(f"{'Propina':<28}{_m(f.propina):>12}")
    lineas.append(f"{'TOTAL':<28}{_m(f.total):>12}")
    lineas.append("-" * ancho)
    lineas.append(f"Pago: {f.metodo_pago}")
    for k, v in f.detalle_pago.items():
        lineas.append(f"  {k}: {_m(v) if isinstance(v, float) else v}")
    lineas += ["=" * ancho, "¡Gracias por su visita!".center(ancho)]
    return "\n".join(lineas)


class ImpresoraTickets:
    def __init__(self, bus, demora: float = 1.5, hilos: int = 2):
        self.bus = bus
        self.demora = demora
        self._pool = ThreadPoolExecutor(max_workers=hilos, thread_name_prefix="ticket")

    def imprimir(self, factura) -> Future:
        futuro = self._pool.submit(self._tarea, factura)
        futuro.add_done_callback(self._al_terminar)
        return futuro

    def _tarea(self, factura):
        time.sleep(self.demora)  # simula la impresora térmica
        settings.DIR_TICKETS.mkdir(parents=True, exist_ok=True)
        ruta = settings.DIR_TICKETS / f"factura_{factura.numero}.txt"
        ruta.write_text(formatear_ticket(factura), encoding="utf-8")
        return factura, ruta

    def _al_terminar(self, futuro: Future) -> None:
        if futuro.exception():
            log.error("Fallo al imprimir ticket: %s", futuro.exception())
            return
        factura, ruta = futuro.result()
        log.info("Ticket de factura %s impreso", factura.numero)
        self.bus.publicar(ev.TICKET_IMPRESO, {"numero": factura.numero, "archivo": str(ruta)})

    def detener(self) -> None:
        self._pool.shutdown(wait=True)
