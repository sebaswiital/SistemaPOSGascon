from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from src.application.contexto import ctx
from src.application.services import pedido_service
from src.infraestructure.eventos import bus_eventos as ev
from src.presentation.utilidades import formato_moneda, refrescar_estilo

ETIQUETA_ESTADO = {"libre": "Libre", "ocupada": "Ocupada", "por_cobrar": "Por cobrar"}


class MapaMesas(QWidget):
    COLUMNAS = 4

    def __init__(self, puente):
        super().__init__()
        self._botones: dict[int, QPushButton] = {}

        titulo = QLabel("Mapa de mesas")
        titulo.setObjectName("titulo")
        leyenda = QHBoxLayout()
        for texto, nombre in (("● Libre", "leyendaLibre"), ("● Ocupada", "leyendaOcupada"),
                              ("● Por cobrar", "leyendaCobrar")):
            l = QLabel(texto)
            l.setObjectName(nombre)
            leyenda.addWidget(l)
        leyenda.addStretch()
        self.resumen = QLabel()
        self.resumen.setObjectName("subtitulo")
        leyenda.addWidget(self.resumen)

        rejilla = QGridLayout()
        rejilla.setSpacing(14)
        for i, mesa in enumerate(sorted(ctx.repos.mesas.todos(), key=lambda m: m.numero)):
            boton = QPushButton()
            boton.setProperty("mesa", True)
            boton.clicked.connect(lambda _=False, n=mesa.numero: self._seleccionar(n))
            rejilla.addWidget(boton, i // self.COLUMNAS, i % self.COLUMNAS)
            self._botones[mesa.numero] = boton

        capa = QVBoxLayout(self)
        capa.addWidget(titulo)
        capa.addLayout(leyenda)
        capa.addLayout(rejilla)
        capa.addStretch()

        puente.escuchar(self._al_evento)
        self.refrescar()

    def _al_evento(self, nombre: str, _datos) -> None:
        if nombre in (ev.MESA_CAMBIADA, ev.PEDIDO_ACTUALIZADO, ev.FACTURA_EMITIDA):
            self.refrescar()

    def _seleccionar(self, numero: int) -> None:
        ctx.bus.publicar(ev.MESA_SELECCIONADA, numero)

    def refrescar(self) -> None:
        for numero, boton in self._botones.items():
            mesa = ctx.repos.mesas.obtener(numero)
            texto = f"Mesa {numero}\n{ETIQUETA_ESTADO[mesa.estado.value]} · {mesa.capacidad} pers."
            if mesa.pedido_actual and not mesa.pedido_actual.vacio:
                cuenta = pedido_service.calcular_cuenta(mesa.pedido_actual, incluir_propina=False)
                texto += f"\n{formato_moneda(cuenta['total'])}"
            boton.setText(texto)
            boton.setProperty("estado", mesa.estado.value)
            refrescar_estilo(boton)
        ocupadas = len(ctx.repos.mesas.ocupadas())
        self.resumen.setText(f"{ocupadas} de {len(self._botones)} mesas ocupadas")
