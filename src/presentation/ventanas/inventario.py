from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QDoubleSpinBox, QFormLayout, QGroupBox, QHBoxLayout,
                               QHeaderView, QLabel, QLineEdit, QListWidget, QMessageBox, QPushButton, QSpinBox,
                               QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from src.application.contexto import ctx
from src.application.services import inventario_service as inv
from src.domain.entities import Rol
from src.domain.reglas.reglas_negocio import nivel_alerta
from src.infraestructure.eventos import bus_eventos as ev
from src.presentation.utilidades import ejecutar, formato_moneda

COLOR_ALERTA = {"AGOTADO": "#E0533B", "CRÍTICO": "#F07A64", "BAJO": "#F0A35B"}


class Inventario(QWidget):
    def __init__(self, puente):
        super().__init__()
        es_admin = ctx.usuario.tiene_rol(Rol.ADMIN)
        titulo = QLabel("Inventario")
        titulo.setObjectName("titulo")

        self.tabla = QTableWidget(0, 7)
        self.tabla.setHorizontalHeaderLabels(["ID", "Producto", "Tipo", "Categoría", "Precio", "Stock", "Alerta"])
        self.tabla.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.setSortingEnabled(True)

        # reponer
        grupo_rep = QGroupBox("Reponer stock")
        f_rep = QFormLayout(grupo_rep)
        self.lbl_sel = QLabel("Seleccione un producto")
        self.cant_rep = QSpinBox(minimum=1, maximum=1000, value=24)
        self.btn_reponer = QPushButton("Reponer")
        self.btn_reponer.setObjectName("primario")
        f_rep.addRow(self.lbl_sel)
        f_rep.addRow("Cantidad", self.cant_rep)
        f_rep.addRow(self.btn_reponer)

        # nuevo producto (validado con Pydantic)
        grupo_nuevo = QGroupBox("Nuevo producto")
        f_nuevo = QFormLayout(grupo_nuevo)
        self.n_tipo = QComboBox()
        self.n_tipo.addItems(["Plato", "Bebida", "Coctel"])
        self.n_nombre = QLineEdit()
        self.n_categoria = QLineEdit(placeholderText="(opcional)")
        self.n_precio = QDoubleSpinBox()
        self.n_precio.setRange(0, 1_000_000)
        self.n_precio.setDecimals(0)
        self.n_precio.setSingleStep(1000)
        self.n_stock = QSpinBox(minimum=0, maximum=10_000, value=30)
        btn_crear = QPushButton("Crear producto")
        f_nuevo.addRow("Tipo", self.n_tipo)
        f_nuevo.addRow("Nombre", self.n_nombre)
        f_nuevo.addRow("Categoría", self.n_categoria)
        f_nuevo.addRow("Precio", self.n_precio)
        f_nuevo.addRow("Stock", self.n_stock)
        f_nuevo.addRow(btn_crear)

        grupo_alertas = QGroupBox("Alertas de inventario (en vivo)")
        ca = QVBoxLayout(grupo_alertas)
        self.alertas = QListWidget()
        ca.addWidget(self.alertas)

        derecha = QVBoxLayout()
        derecha.addWidget(grupo_rep)
        derecha.addWidget(grupo_nuevo)
        derecha.addWidget(grupo_alertas, 1)
        grupo_rep.setEnabled(es_admin)
        grupo_nuevo.setEnabled(es_admin)
        if not es_admin:
            grupo_rep.setTitle("Reponer stock (solo administrador)")
            grupo_nuevo.setTitle("Nuevo producto (solo administrador)")

        cuerpo = QHBoxLayout()
        cuerpo.addWidget(self.tabla, 3)
        cuerpo.addLayout(derecha, 2)
        capa = QVBoxLayout(self)
        capa.addWidget(titulo)
        capa.addLayout(cuerpo, 1)

        # eventos
        self.tabla.itemSelectionChanged.connect(self._seleccion)
        self.btn_reponer.clicked.connect(self._reponer)
        btn_crear.clicked.connect(self._crear)
        puente.escuchar(self._al_evento)
        self.refrescar()
        for p in ctx.repos.productos.todos():
            if nivel := nivel_alerta(p):
                self._agregar_alerta(p, nivel)

    def _al_evento(self, nombre: str, datos) -> None:
        if nombre == ev.INVENTARIO_ACTUALIZADO:
            self.refrescar()
        elif nombre == ev.STOCK_BAJO:
            self._agregar_alerta(*datos)

    def _agregar_alerta(self, producto, nivel: str) -> None:
        self.alertas.insertItem(0, f"{datetime.now():%H:%M:%S}  [{nivel}] {producto.nombre}: quedan {producto.stock}")
        self.alertas.item(0).setForeground(QColor(COLOR_ALERTA[nivel]))
        while self.alertas.count() > 100:
            self.alertas.takeItem(self.alertas.count() - 1)

    def _id_seleccionado(self):
        fila = self.tabla.currentRow()
        return int(self.tabla.item(fila, 0).text()) if fila >= 0 and self.tabla.item(fila, 0) else None

    def _seleccion(self) -> None:
        pid = self._id_seleccionado()
        if pid:
            p = ctx.repos.productos.obtener(pid)
            self.lbl_sel.setText(f"{p.nombre} (stock actual {p.stock})")

    def _reponer(self) -> None:
        pid = self._id_seleccionado()
        if pid is None:
            QMessageBox.information(self, "Inventario", "Seleccione un producto de la tabla")
            return
        ejecutar(self, inv.reponer, pid, self.cant_rep.value())
        self._seleccion()

    def _crear(self) -> None:
        p = ejecutar(self, inv.crear_producto, tipo=self.n_tipo.currentText(), nombre=self.n_nombre.text().strip(),
                     precio=self.n_precio.value(), stock=self.n_stock.value(),
                     categoria=self.n_categoria.text().strip() or None)
        if p:
            QMessageBox.information(self, "Inventario", f"Producto creado: {p.descripcion()}")
            self.n_nombre.clear()
            self.n_categoria.clear()

    def refrescar(self) -> None:
        productos = sorted(ctx.repos.productos.todos(), key=lambda p: (p.categoria, p.nombre))
        self.tabla.setSortingEnabled(False)
        self.tabla.setRowCount(len(productos))
        for fila, p in enumerate(productos):
            nivel = nivel_alerta(p) or "OK"
            valores = [p.id, p.nombre, p.tipo, p.categoria, formato_moneda(p.precio), p.stock, nivel]
            for col, v in enumerate(valores):
                celda = QTableWidgetItem()
                celda.setData(Qt.ItemDataRole.DisplayRole, v)
                if nivel != "OK":
                    celda.setForeground(QColor(COLOR_ALERTA[nivel]))
                self.tabla.setItem(fila, col, celda)
        self.tabla.setSortingEnabled(True)
