import os

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QGroupBox,
                               QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMessageBox, QPlainTextEdit,
                               QPushButton, QStackedWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from src.application.calculos.funciones_puras import cambio
from src.application.contexto import ctx
from src.application.esquemas import PagoIn
from src.application.services import caja_service as cs
from src.application.services import pedido_service as ps
from src.config import settings
from src.domain.entities import EstadoMesa
from src.infraestructure.eventos import bus_eventos as ev
from src.presentation.utilidades import ejecutar, formato_moneda


def _spin_dinero(maximo: float = 10_000_000) -> QDoubleSpinBox:
    s = QDoubleSpinBox()
    s.setRange(0, maximo)
    s.setDecimals(0)
    s.setSingleStep(1000)
    s.setPrefix("$ ")
    s.setGroupSeparatorShown(True)
    return s


class Caja(QWidget):
    def __init__(self, puente):
        super().__init__()
        titulo = QLabel("Caja")
        titulo.setObjectName("titulo")
        self.estado = QLabel()
        self.estado.setObjectName("subtitulo")
        cab = QHBoxLayout()
        cab.addWidget(titulo)
        cab.addSpacing(16)
        cab.addWidget(self.estado)
        cab.addStretch()

        # ---------- apertura / cierre ----------
        grupo_turno = QGroupBox("Turno")
        f_turno = QFormLayout(grupo_turno)
        self.monto_inicial = _spin_dinero()
        self.monto_inicial.setValue(200_000)
        self.btn_abrir = QPushButton("Abrir caja")
        self.btn_abrir.setObjectName("primario")
        self.efectivo_contado = _spin_dinero(100_000_000)
        self.btn_cerrar = QPushButton("Cerrar caja y exportar")
        self.btn_cerrar.setObjectName("peligro")
        f_turno.addRow("Base inicial", self.monto_inicial)
        f_turno.addRow(self.btn_abrir)
        self.efectivo_contado.setSpecialValueText("(sin contar)")
        f_turno.addRow("Efectivo contado", self.efectivo_contado)
        f_turno.addRow(self.btn_cerrar)

        grupo_mov = QGroupBox("Movimientos de caja")
        f_mov = QFormLayout(grupo_mov)
        self.tipo_mov = QComboBox()
        self.tipo_mov.addItems(["egreso", "ingreso"])
        self.monto_mov = _spin_dinero()
        self.concepto_mov = QLineEdit(placeholderText="Ej: compra de hielo")
        btn_mov = QPushButton("Registrar movimiento")
        f_mov.addRow("Tipo", self.tipo_mov)
        f_mov.addRow("Monto", self.monto_mov)
        f_mov.addRow("Concepto", self.concepto_mov)
        f_mov.addRow(btn_mov)

        izquierda = QVBoxLayout()
        izquierda.addWidget(grupo_turno)
        izquierda.addWidget(grupo_mov)
        izquierda.addStretch()

        # ---------- cobro ----------
        grupo_cobro = QGroupBox("Cobrar mesa")
        c = QVBoxLayout(grupo_cobro)
        self.combo_mesa = QComboBox()
        self.detalle = QPlainTextEdit()
        self.detalle.setReadOnly(True)
        self.detalle.setMinimumHeight(220)
        self.chk_propina = QCheckBox(f"Incluir propina sugerida ({settings.PROPINA_SUGERIDA:.0%})")
        self.chk_propina.setChecked(True)
        self.total = QLabel()
        self.total.setObjectName("totalGrande")

        self.metodo = QComboBox()
        self.metodo.addItems(["Efectivo", "Tarjeta", "Nequi"])
        self.pila = QStackedWidget()
        # efectivo
        p_ef = QWidget()
        f_ef = QFormLayout(p_ef)
        self.recibido = _spin_dinero()
        self.lbl_cambio = QLabel("Cambio: $0")
        f_ef.addRow("Recibido", self.recibido)
        f_ef.addRow(self.lbl_cambio)
        # tarjeta
        p_tj = QWidget()
        f_tj = QFormLayout(p_tj)
        self.num_tarjeta = QLineEdit(placeholderText="Número de tarjeta")
        self.franquicia = QComboBox()
        self.franquicia.addItems(["Visa", "Mastercard", "American Express"])
        f_tj.addRow("Tarjeta", self.num_tarjeta)
        f_tj.addRow("Franquicia", self.franquicia)
        # nequi
        p_nq = QWidget()
        f_nq = QFormLayout(p_nq)
        self.celular = QLineEdit(placeholderText="3001234567")
        f_nq.addRow("Celular", self.celular)
        for p in (p_ef, p_tj, p_nq):
            self.pila.addWidget(p)
        self.btn_cobrar = QPushButton("Cobrar e imprimir ticket")
        self.btn_cobrar.setObjectName("primario")

        fila_m = QHBoxLayout()
        fila_m.addWidget(QLabel("Mesa"))
        fila_m.addWidget(self.combo_mesa, 1)
        c.addLayout(fila_m)
        c.addWidget(self.detalle)
        c.addWidget(self.chk_propina)
        c.addWidget(self.total)
        fila_met = QHBoxLayout()
        fila_met.addWidget(QLabel("Método de pago"))
        fila_met.addWidget(self.metodo, 1)
        c.addLayout(fila_met)
        c.addWidget(self.pila)
        c.addWidget(self.btn_cobrar)

        # ---------- facturas ----------
        grupo_fact = QGroupBox("Facturas del turno")
        cf = QVBoxLayout(grupo_fact)
        self.tabla = QTableWidget(0, 5)
        self.tabla.setHorizontalHeaderLabels(["N°", "Hora", "Mesa", "Método", "Total"])
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setAlternatingRowColors(True)
        self.btn_carpeta = QPushButton("Abrir carpeta de salidas")
        cf.addWidget(self.tabla)
        cf.addWidget(self.btn_carpeta)

        cuerpo = QHBoxLayout()
        cuerpo.addLayout(izquierda, 3)
        cuerpo.addWidget(grupo_cobro, 4)
        cuerpo.addWidget(grupo_fact, 4)
        capa = QVBoxLayout(self)
        capa.addLayout(cab)
        capa.addLayout(cuerpo, 1)

        # ---------- eventos ----------
        self.btn_abrir.clicked.connect(self._abrir)
        self.btn_cerrar.clicked.connect(self._cerrar)
        btn_mov.clicked.connect(self._movimiento)
        self.combo_mesa.currentIndexChanged.connect(lambda _: self._mostrar_cuenta())
        self.chk_propina.toggled.connect(lambda _: self._mostrar_cuenta())
        self.metodo.currentIndexChanged.connect(self.pila.setCurrentIndex)
        self.recibido.valueChanged.connect(lambda _: self._actualizar_cambio())
        self.btn_cobrar.clicked.connect(self._cobrar)
        self.btn_carpeta.clicked.connect(self._abrir_carpeta)
        puente.escuchar(self._al_evento)
        self.refrescar()

    # ---------- reacciones a eventos ----------
    def _al_evento(self, nombre: str, datos) -> None:
        if nombre in (ev.MESA_CAMBIADA, ev.PEDIDO_ACTUALIZADO, ev.FACTURA_EMITIDA, ev.CAJA_ABIERTA,
                      ev.CAJA_CERRADA):
            self.refrescar()

    # ---------- acciones ----------
    def _abrir(self) -> None:
        ejecutar(self, cs.abrir_caja, self.monto_inicial.value())

    def _movimiento(self) -> None:
        if ejecutar(self, cs.registrar_movimiento, self.tipo_mov.currentText(), self.monto_mov.value(),
                    self.concepto_mov.text().strip() or "sin concepto"):
            self.monto_mov.setValue(0)
            self.concepto_mov.clear()
            self.refrescar()

    def _cuenta_actual(self):
        numero = self.combo_mesa.currentData()
        if numero is None:
            return None, None
        pedido = ps.pedido_de_mesa(numero)
        if pedido is None or pedido.vacio:
            return numero, None
        return numero, ps.calcular_cuenta(pedido, self.chk_propina.isChecked())

    def _mostrar_cuenta(self) -> None:
        numero, cuenta = self._cuenta_actual()
        if cuenta is None:
            self.detalle.setPlainText("Seleccione una mesa con pedido.")
            self.total.setText(formato_moneda(0))
            self._actualizar_cambio()
            return
        pedido = ps.pedido_de_mesa(numero)
        lineas = [f"{i.cantidad:>2} x {i.producto.nombre:<26}{formato_moneda(i.subtotal):>12}" for i in pedido.items]
        lineas.append("-" * 42)
        lineas.append(f"{'Subtotal':<31}{formato_moneda(cuenta['subtotal']):>11}")
        lineas += [f"{n[:30]:<31}{'-' + formato_moneda(v):>11}" for n, v in cuenta["promociones"]]
        lineas.append(f"{'Impoconsumo 8%':<31}{formato_moneda(cuenta['impuesto']):>11}")
        lineas.append(f"{'Propina':<31}{formato_moneda(cuenta['propina']):>11}")
        if pedido.items_pendientes():
            lineas.append("\n⚠ Hay productos sin enviar a preparación")
        self.detalle.setPlainText("\n".join(lineas))
        self.total.setText(f"Total {formato_moneda(cuenta['total'])}")
        self._actualizar_cambio()

    def _actualizar_cambio(self) -> None:
        _, cuenta = self._cuenta_actual()
        total = cuenta["total"] if cuenta else 0
        dif = cambio(self.recibido.value(), total)
        self.lbl_cambio.setText(f"Cambio: {formato_moneda(dif)}" if dif >= 0 else f"Faltan {formato_moneda(-dif)}")

    def _cobrar(self) -> None:
        numero, cuenta = self._cuenta_actual()
        if cuenta is None:
            QMessageBox.information(self, "Cobro", "Seleccione una mesa con pedido")
            return
        metodo = self.metodo.currentText()
        datos = {"metodo": metodo, "incluir_propina": self.chk_propina.isChecked()}
        if metodo == "Efectivo":
            datos["recibido"] = self.recibido.value()
        elif metodo == "Tarjeta":
            datos["numero_tarjeta"] = self.num_tarjeta.text()
            datos["franquicia"] = self.franquicia.currentText()
        else:
            datos["celular"] = self.celular.text()
        try:
            pago = PagoIn(**datos)
        except Exception as e:
            from src.application.esquemas import mensaje_error
            QMessageBox.warning(self, "Datos de pago", mensaje_error(e))
            return
        factura = ejecutar(self, cs.cobrar_mesa, numero, pago)
        if factura:
            extra = "\n".join(f"{k}: {formato_moneda(v) if isinstance(v, float) else v}"
                              for k, v in factura.detalle_pago.items())
            QMessageBox.information(self, "Factura emitida",
                                    f"Factura N° {factura.numero}\nTotal: {formato_moneda(factura.total)}\n"
                                    f"{factura.metodo_pago}\n{extra}\n\nEl ticket se imprime en segundo plano.")
            self.recibido.setValue(0)
            self.num_tarjeta.clear()
            self.celular.clear()

    def _cerrar(self) -> None:
        if not cs.caja_abierta():
            QMessageBox.information(self, "Caja", "La caja no está abierta")
            return
        if QMessageBox.question(self, "Cierre de caja", "¿Cerrar la caja del turno actual?") \
                != QMessageBox.StandardButton.Yes:
            return
        contado = self.efectivo_contado.value() or None  # 0 = no se contó: se asume lo esperado
        r = ejecutar(self, cs.cerrar_caja, contado)
        if r:
            metodos = "\n".join(f"   {m}: {formato_moneda(v)}" for m, v in r["por_metodo"].items())
            QMessageBox.information(
                self, "Caja cerrada",
                f"Facturas: {r['num_facturas']}\nVentas: {formato_moneda(r['total_ventas'])}\n{metodos}\n"
                f"Efectivo esperado: {formato_moneda(r['efectivo_esperado'])}\n"
                f"Diferencia: {formato_moneda(r['diferencia'])}\n\n"
                f"Excel: {r['archivo_excel']}\nPDF: {r['archivo_pdf']}")

    def _abrir_carpeta(self) -> None:
        settings.DIR_SALIDAS.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(os.fspath(settings.DIR_SALIDAS)))

    # ---------- vista ----------
    def refrescar(self) -> None:
        abierta = cs.caja_abierta()
        estado = cs.estado_caja()
        if abierta:
            self.estado.setText(f"● Abierta desde {estado['apertura']:%H:%M} por {estado['cajero']} · "
                                f"base {formato_moneda(estado['monto_inicial'])} · "
                                f"{len(estado['movimientos'])} movimientos")
            self.estado.setStyleSheet("color:#6FCB86;")
        else:
            self.estado.setText("● Caja cerrada")
            self.estado.setStyleSheet("color:#F07A64;")
        self.btn_abrir.setEnabled(not abierta)
        self.monto_inicial.setEnabled(not abierta)
        self.btn_cerrar.setEnabled(abierta)
        self.btn_cobrar.setEnabled(abierta)

        actual = self.combo_mesa.currentData()
        self.combo_mesa.blockSignals(True)
        self.combo_mesa.clear()
        mesas = sorted(ctx.repos.mesas.ocupadas(), key=lambda m: (m.estado != EstadoMesa.POR_COBRAR, m.numero))
        for m in mesas:
            if m.pedido_actual and not m.pedido_actual.vacio:
                etiqueta = "  (pidió la cuenta)" if m.estado == EstadoMesa.POR_COBRAR else ""
                self.combo_mesa.addItem(f"Mesa {m.numero}{etiqueta}", m.numero)
        idx = self.combo_mesa.findData(actual)
        self.combo_mesa.setCurrentIndex(idx if idx >= 0 else 0)
        self.combo_mesa.blockSignals(False)
        self._mostrar_cuenta()

        facturas = ctx.repos.facturas.desde(estado["apertura"]) if abierta else []
        self.tabla.setRowCount(len(facturas))
        for fila, f in enumerate(reversed(facturas)):
            for col, v in enumerate([str(f.numero), f"{f.fecha:%H:%M}", str(f.mesa_numero), f.metodo_pago,
                                     formato_moneda(f.total)]):
                self.tabla.setItem(fila, col, QTableWidgetItem(v))
