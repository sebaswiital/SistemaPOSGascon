"""Punto de entrada del POS Bar Gascón.

Paradigma imperativo/procedural: el arranque es una secuencia ordenada de procedimientos.
No hay base de datos: todo vive en memoria mientras la aplicación está abierta.

    python main.py
"""
import logging
import sys

from src.application.contexto import ctx
from src.config import settings

_servicios = {}


def configurar_logging() -> None:
    settings.DIR_SALIDAS.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(threadName)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout),
                  logging.FileHandler(settings.DIR_SALIDAS / "pos.log", encoding="utf-8")],
    )


def cargar_datos_iniciales() -> None:
    from scripts.seed_db import seed
    seed(ctx.repos)


def iniciar_servicios() -> None:
    from src.application.services.inventario_service import revisar_alertas
    from src.infraestructure.impresion.cola_comandas import ColaComandas
    from src.infraestructure.impresion.impresora_tickets import ImpresoraTickets
    from src.infraestructure.sincronizacion import Sincronizador

    ctx.cola_comandas = ColaComandas(ctx.bus)
    ctx.cola_comandas.iniciar()
    ctx.impresora = ImpresoraTickets(ctx.bus)
    sincronizador = Sincronizador(ctx.repos, ctx.bus)
    sincronizador.iniciar()
    _servicios["sincronizador"] = sincronizador
    revisar_alertas()


def lanzar_interfaz() -> int:
    from PySide6.QtWidgets import QApplication, QDialog

    from src.presentation.puente_qt import PuenteEventos
    from src.presentation.ventanas.login import VentanaLogin
    from src.presentation.ventanas.ventana_principal import VentanaPrincipal

    app = QApplication(sys.argv)
    app.setApplicationName(settings.NOMBRE_NEGOCIO)
    app.setQuitOnLastWindowClosed(False)
    app.setStyleSheet(settings.ARCHIVO_QSS.read_text(encoding="utf-8"))
    puente = PuenteEventos(ctx.bus)
    estado = {}

    def iniciar_sesion() -> bool:
        if VentanaLogin().exec() != QDialog.DialogCode.Accepted:
            app.quit()
            return False
        estado["ventana"] = VentanaPrincipal(puente, al_cerrar_sesion=iniciar_sesion)
        estado["ventana"].show()
        return True

    if not iniciar_sesion():
        return 0
    return app.exec()


def apagar_servicios() -> None:
    logging.info("Apagando servicios...")
    if "sincronizador" in _servicios:
        _servicios["sincronizador"].detener()
    if ctx.cola_comandas:
        ctx.cola_comandas.detener()
    if ctx.impresora:
        ctx.impresora.detener()
    logging.info("Aplicación cerrada. Los datos en memoria se descartan.")


def main() -> int:
    configurar_logging()
    cargar_datos_iniciales()
    iniciar_servicios()
    try:
        codigo = lanzar_interfaz()
    finally:
        apagar_servicios()
    return codigo


if __name__ == "__main__":
    sys.exit(main())
