from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QFrame, QLabel, QLineEdit, QPushButton, QVBoxLayout)

from src.application.esquemas import mensaje_error
from src.application.services import auth_service
from src.config import settings


class VentanaLogin(QDialog):
    def __init__(self):
        super().__init__()
        self.setObjectName("login")
        self.setWindowTitle(f"{settings.NOMBRE_NEGOCIO} - Ingreso")
        self.setFixedSize(420, 520)

        panel = QFrame()
        panel.setObjectName("panelLogin")
        capa_panel = QVBoxLayout(panel)
        capa_panel.setContentsMargins(30, 30, 30, 30)
        capa_panel.setSpacing(12)

        marca = QLabel(settings.NOMBRE_NEGOCIO)
        marca.setObjectName("marca")
        marca.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub = QLabel("Sistema POS")
        sub.setObjectName("subtitulo")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.usuario = QLineEdit(placeholderText="Usuario")
        self.pin = QLineEdit(placeholderText="PIN (4 dígitos)")
        self.pin.setEchoMode(QLineEdit.EchoMode.Password)
        self.pin.setMaxLength(4)
        self.error = QLabel("")
        self.error.setStyleSheet("color:#F07A64;")
        self.error.setWordWrap(True)
        boton = QPushButton("Ingresar")
        boton.setObjectName("primario")
        boton.setDefault(True)

        ayuda = QLabel("Usuarios de prueba:\nadmin / 1234   ·   mesero / 1111   ·   cajero / 2222")
        ayuda.setObjectName("subtitulo")
        ayuda.setAlignment(Qt.AlignmentFlag.AlignCenter)

        for w in (marca, sub, self.usuario, self.pin, self.error, boton, ayuda):
            capa_panel.addWidget(w)

        capa = QVBoxLayout(self)
        capa.setContentsMargins(24, 24, 24, 24)
        capa.addWidget(panel)

        # --- eventos ---
        boton.clicked.connect(self._ingresar)
        self.usuario.returnPressed.connect(self.pin.setFocus)
        self.pin.returnPressed.connect(self._ingresar)
        self.usuario.setFocus()

    def _ingresar(self) -> None:
        try:
            auth_service.iniciar_sesion(self.usuario.text(), self.pin.text())
            self.accept()
        except Exception as e:
            self.error.setText(mensaje_error(e))
            self.pin.clear()
            self.pin.setFocus()
