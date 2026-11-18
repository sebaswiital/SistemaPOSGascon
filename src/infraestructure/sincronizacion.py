"""Paradigma asíncrono: un event loop de asyncio en un hilo aparte ejecuta tareas periódicas
concurrentes (corutinas): respaldo de datos en memoria y refresco del dashboard."""
import asyncio
import json
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from src.config import settings
from src.infraestructure.eventos import bus_eventos as ev

log = logging.getLogger("sincronizacion")


class Sincronizador:
    def __init__(self, repos, bus, intervalo_respaldo: float = settings.INTERVALO_RESPALDO_SEG,
                 intervalo_dashboard: float = settings.INTERVALO_DASHBOARD_SEG):
        self.repos = repos
        self.bus = bus
        self.intervalo_respaldo = intervalo_respaldo
        self.intervalo_dashboard = intervalo_dashboard
        self._loop: asyncio.AbstractEventLoop | None = None
        self._hilo: threading.Thread | None = None
        self._parar: asyncio.Event | None = None
        self._pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="respaldo")

    # ---- ciclo de vida ----
    def iniciar(self) -> None:
        self._hilo = threading.Thread(target=self._ejecutar, name="sincronizador", daemon=True)
        self._hilo.start()

    def detener(self) -> None:
        if self._loop and self._parar:
            self._loop.call_soon_threadsafe(self._parar.set)
        if self._hilo:
            self._hilo.join(timeout=5)
        self._pool.shutdown(wait=True)

    def _ejecutar(self) -> None:
        asyncio.run(self._principal())

    async def _principal(self) -> None:
        self._loop = asyncio.get_running_loop()
        self._parar = asyncio.Event()
        log.info("Sincronizador iniciado")
        tareas = [asyncio.create_task(self._periodica(self.intervalo_respaldo, self.respaldar)),
                  asyncio.create_task(self._periodica(self.intervalo_dashboard, self._tick_dashboard))]
        await self._parar.wait()
        for t in tareas:
            t.cancel()
        await asyncio.gather(*tareas, return_exceptions=True)
        await self.respaldar()  # respaldo final al salir
        log.info("Sincronizador detenido")

    async def _periodica(self, intervalo: float, corutina) -> None:
        while True:
            await asyncio.sleep(intervalo)
            try:
                await corutina()
            except Exception:
                log.exception("Error en tarea periódica")

    async def _en_hilo(self, funcion, *args):
        """Equivalente a asyncio.to_thread. Se usa un pool propio porque, con PySide6 cargado en
        Python 3.15, los imports diferidos de asyncio rompen run_in_executor/wrap_future."""
        futuro = self._pool.submit(funcion, *args)
        while not futuro.done():
            await asyncio.sleep(0.02)
        return futuro.result()

    # ---- tareas ----
    async def respaldar(self) -> None:
        datos = self.repos.snapshot()
        settings.DIR_RESPALDOS.mkdir(parents=True, exist_ok=True)
        ruta = settings.DIR_RESPALDOS / f"respaldo_{datetime.now():%Y%m%d_%H%M%S}.json"
        texto = json.dumps(datos, ensure_ascii=False, indent=2, default=str)
        await self._en_hilo(ruta.write_text, texto, "utf-8")  # E/S sin bloquear el loop
        self._rotar_respaldos()
        self.bus.publicar(ev.RESPALDO_REALIZADO, str(ruta))

    @staticmethod
    def _rotar_respaldos(maximo: int = 10) -> None:
        archivos = sorted(settings.DIR_RESPALDOS.glob("respaldo_*.json"))
        for viejo in archivos[:-maximo]:
            viejo.unlink(missing_ok=True)

    async def _tick_dashboard(self) -> None:
        self.bus.publicar(ev.DASHBOARD_TICK, datetime.now())
