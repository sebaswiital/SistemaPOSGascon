from datetime import datetime

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QMainWindow, QPushButton, QTabWidget, QVBoxLayout, QWidget

from src.application.contexto import ctx
from src.application.services import auth_service
from src.config import settings
from src.domain.entities import Rol
from src.domain.reglas.motor_promociones import es_happy_hour
from src.infraestructure.eventos import bus_eventos as ev
from src.presentation.ventanas.caja import Caja
from src.presentation.ventanas.dashboard import Dashboard
from src.presentation.ventanas.inventario import Inventario
from src.presentation.ventanas.mapa_mesas import MapaMesas
from src.presentation.ventanas.toma_pedido import TomaPedido

MENSAJES_BARRA = {
    ev.COMANDA_IMPRESA: lambda d: f"🖨 Comanda {d['area']} #{d['numero']} impresa (mesa {d['mesa']})",
    ev.TICKET_IMPRESO: lambda d: f"🧾 Ticket factura {d['numero']} impreso → {d['archivo']}",
    ev.RESPALDO_REALIZADO: lambda d: f"💾 Respaldo automático: {d}",
}


class VentanaPrincipal(QMainWindow):
    def __init__(self, puente, al_cerrar_sesion):
        super().__init__()
        self._al_cerrar_sesion = al_cerrar_sesion
        self._cerrando_sesion = False
        u = ctx.usuario
        self.setWindowTitle(f"{settings.NOMBRE_NEGOCIO} · POS")
        self.resize(1360, 820)

        # ---------- encabezado ----------
        encabezado = QFrame()
        encabezado.setObjectName("encabezado")
        ch = QHBoxLayout(encabezado)
        marca = QLabel(f"🍺 {settings.NOMBRE_NEGOCIO}")
        marca.setObjectName("marca")
        self.happy = QLabel("HAPPY HOUR")
        self.happy.setObjectName("happyHour")
        usuario = QLabel(f"{u.nombre} · {u.rol.value}")
        usuario.setObjectName("usuario")
        self.reloj = QLabel()
        self.reloj.setObjectName("reloj")
        btn_salir = QPushButton("Cerrar sesión")
        ch.addWidget(marca)
        ch.addSpacing(12)
        ch.addWidget(self.happy)
        ch.addStretch()
        ch.addWidget(usuario)
        ch.addSpacing(16)
        ch.addWidget(self.reloj)
        ch.addSpacing(16)
        ch.addWidget(btn_salir)

        # ---------- pestañas según rol ----------
        self.tabs = QTabWidget()
        self.mapa = MapaMesas(puente)
        self.pedido = TomaPedido(puente)
        self.tabs.addTab(self.mapa, "Mesas")
        self.tabs.addTab(self.pedido, "Pedido")
        if u.tiene_rol(Rol.CAJERO):  # cajero y admin (en inventario el cajero solo consulta)
            self.tabs.addTab(Caja(puente), "Caja")
            self.tabs.addTab(Inventario(puente), "Inventario")
            self.tabs.addTab(Dashboard(puente), "Dashboard")

        central = QWidget()
        central.setObjectName("fondo")
        capa = QVBoxLayout(central)
        capa.setContentsMargins(0, 0, 0, 0)
        capa.addWidget(encabezado)
        contenido = QVBoxLayout()
        contenido.setContentsMargins(14, 10, 14, 10)
        contenido.addWidget(self.tabs)
        capa.addLayout(contenido, 1)
        self.setCentralWidget(central)
        self.statusBar().showMessage("Listo")

        # ---------- eventos ----------
        btn_salir.clicked.connect(self._cerrar_sesion)
        puente.escuchar(self._al_evento)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tic)
        self._timer.start(1000)
        self._tic()

    def _al_evento(self, nombre: str, datos) -> None:
        if nombre == ev.MESA_SELECCIONADA:
            self.pedido.seleccionar_mesa(datos)
            self.tabs.setCurrentWidget(self.pedido)
        elif nombre in MENSAJES_BARRA:
            self.statusBar().showMessage(MENSAJES_BARRA[nombre](datos), 6000)
        elif nombre == ev.PEDIDO_ACTUALIZADO:
            self._tic()

    def _tic(self) -> None:
        ahora = datetime.now()
        self.reloj.setText(f"{ahora:%H:%M:%S}")
        self.happy.setVisible(bool(es_happy_hour({"hora": ahora.hour, "forzar_happy_hour": ctx.forzar_happy_hour})))

    def _cerrar_sesion(self) -> None:
        self._cerrando_sesion = True
        auth_service.cerrar_sesion()
        self.close()
        QTimer.singleShot(0, self._al_cerrar_sesion)

    def closeEvent(self, evento) -> None:
        self._timer.stop()
        super().closeEvent(evento)
        self.deleteLater()
        if not self._cerrando_sesion:
            from PySide6.QtWidgets import QApplication
            QApplication.instance().quit()
