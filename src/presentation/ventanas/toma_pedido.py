from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QHBoxLayout, QHeaderView, QLabel,
                               QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPushButton, QSpinBox,
                               QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget, QGroupBox)

from src.application.contexto import ctx
from src.application.services import pedido_service as ps
from src.domain.entities import EstadoMesa, Rol
from src.infraestructure.eventos import bus_eventos as ev
from src.presentation.utilidades import ejecutar, formato_moneda


class TomaPedido(QWidget):
    def __init__(self, puente):
        super().__init__()

        # ---------- encabezado ----------
        titulo = QLabel("Toma de pedido")
        titulo.setObjectName("titulo")
        self.combo_mesa = QComboBox()
        for m in sorted(ctx.repos.mesas.todos(), key=lambda m: m.numero):
            self.combo_mesa.addItem(f"Mesa {m.numero}", m.numero)
        self.chk_happy = QCheckBox("Simular Happy Hour")
        self.chk_happy.setVisible(ctx.usuario.tiene_rol(Rol.ADMIN))
        self.chk_happy.setChecked(ctx.forzar_happy_hour)
        self.estado_mesa = QLabel()
        self.estado_mesa.setObjectName("subtitulo")
        cabecera = QHBoxLayout()
        cabecera.addWidget(titulo)
        cabecera.addSpacing(20)
        cabecera.addWidget(self.combo_mesa)
        cabecera.addWidget(self.estado_mesa)
        cabecera.addStretch()
        cabecera.addWidget(self.chk_happy)

        # ---------- carta ----------
        self.lista_categorias = QListWidget()
        self.lista_categorias.setMaximumWidth(170)
        self.lista_categorias.addItems(ctx.repos.productos.categorias())
        self.lista_productos = QListWidget()
        self.lista_productos.setMinimumWidth(360)
        self.cantidad = QSpinBox(minimum=1, maximum=50)
        self.nota = QLineEdit(placeholderText="Nota (sin hielo, término medio...)")
        btn_agregar = QPushButton("Agregar ➜")
        btn_agregar.setObjectName("primario")
        fila_agregar = QHBoxLayout()
        fila_agregar.addWidget(QLabel("Cant."))
        fila_agregar.addWidget(self.cantidad)
        fila_agregar.addWidget(self.nota, 1)
        fila_agregar.addWidget(btn_agregar)

        carta = QGroupBox("Carta")
        capa_carta = QVBoxLayout(carta)
        listas = QHBoxLayout()
        listas.addWidget(self.lista_categorias)
        listas.addWidget(self.lista_productos, 1)
        capa_carta.addLayout(listas)
        capa_carta.addLayout(fila_agregar)

        # ---------- pedido ----------
        self.tabla = QTableWidget(0, 5)
        self.tabla.setHorizontalHeaderLabels(["Producto", "Cant.", "Precio", "Subtotal", "Estado"])
        self.tabla.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setAlternatingRowColors(True)
        self.promos = QLabel()
        self.promos.setWordWrap(True)
        self.promos.setStyleSheet("color:#6FCB86;")
        self.totales = QLabel()
        self.totales.setObjectName("totales")
        self.total = QLabel()
        self.total.setObjectName("totalGrande")
        self.total.setAlignment(Qt.AlignmentFlag.AlignRight)

        self.btn_quitar = QPushButton("Quitar item")
        self.btn_enviar = QPushButton("Enviar a cocina / bar")
        self.btn_enviar.setObjectName("primario")
        self.btn_cuenta = QPushButton("Pedir cuenta")
        self.btn_cancelar = QPushButton("Anular pedido")
        self.btn_cancelar.setObjectName("peligro")
        botones = QHBoxLayout()
        for b in (self.btn_quitar, self.btn_cancelar):
            botones.addWidget(b)
        botones.addStretch()
        for b in (self.btn_enviar, self.btn_cuenta):
            botones.addWidget(b)

        pedido = QGroupBox("Pedido de la mesa")
        capa_pedido = QVBoxLayout(pedido)
        capa_pedido.addWidget(self.tabla, 1)
        capa_pedido.addWidget(self.promos)
        fila_tot = QHBoxLayout()
        fila_tot.addWidget(self.totales, 1)
        fila_tot.addWidget(self.total)
        capa_pedido.addLayout(fila_tot)
        capa_pedido.addLayout(botones)

        cuerpo = QHBoxLayout()
        cuerpo.addWidget(carta, 5)
        cuerpo.addWidget(pedido, 6)
        capa = QVBoxLayout(self)
        capa.addLayout(cabecera)
        capa.addLayout(cuerpo, 1)

        # ---------- eventos de la interfaz ----------
        self.lista_categorias.currentTextChanged.connect(self._mostrar_categoria)
        self.lista_productos.itemDoubleClicked.connect(lambda _: self._agregar())
        btn_agregar.clicked.connect(self._agregar)
        self.combo_mesa.currentIndexChanged.connect(lambda _: self.refrescar())
        self.btn_quitar.clicked.connect(self._quitar)
        self.btn_enviar.clicked.connect(self._enviar)
        self.btn_cuenta.clicked.connect(self._pedir_cuenta)
        self.btn_cancelar.clicked.connect(self._cancelar)
        self.chk_happy.toggled.connect(self._toggle_happy)
        puente.escuchar(self._al_evento)

        self.lista_categorias.setCurrentRow(0)
        self.refrescar()

    # ---------- helpers ----------
    @property
    def mesa(self) -> int:
        return self.combo_mesa.currentData()

    def seleccionar_mesa(self, numero: int) -> None:
        self.combo_mesa.setCurrentIndex(self.combo_mesa.findData(numero))
        self.refrescar()

    def _mostrar_categoria(self, categoria: str) -> None:
        self.lista_productos.clear()
        for p in ctx.repos.productos.por_categoria(categoria):
            item = QListWidgetItem(f"{p.descripcion()}    (stock {p.stock})")
            item.setData(Qt.ItemDataRole.UserRole, p.id)
            if p.stock == 0:
                item.setFlags(Qt.ItemFlag.NoItemFlags)
            elif p.stock_bajo:
                item.setForeground(QColor("#F0A35B"))
            self.lista_productos.addItem(item)

    def _al_evento(self, nombre: str, _datos) -> None:
        if nombre in (ev.PEDIDO_ACTUALIZADO, ev.MESA_CAMBIADA, ev.FACTURA_EMITIDA):
            self.refrescar()
        if nombre == ev.INVENTARIO_ACTUALIZADO and self.lista_categorias.currentItem():
            self._mostrar_categoria(self.lista_categorias.currentItem().text())

    # ---------- acciones ----------
    def _agregar(self) -> None:
        item = self.lista_productos.currentItem()
        if item is None:
            QMessageBox.information(self, "Pedido", "Seleccione un producto de la carta")
            return
        if ejecutar(self, ps.agregar_item, self.mesa, item.data(Qt.ItemDataRole.UserRole),
                    self.cantidad.value(), self.nota.text().strip()):
            self.cantidad.setValue(1)
            self.nota.clear()

    def _quitar(self) -> None:
        fila = self.tabla.currentRow()
        if fila < 0:
            return
        ejecutar(self, ps.quitar_item, self.mesa, fila)

    def _enviar(self) -> None:
        enviados = ejecutar(self, ps.enviar_comanda, self.mesa)
        if enviados == 0:
            QMessageBox.information(self, "Comanda", "No hay productos pendientes por enviar")

    def _pedir_cuenta(self) -> None:
        ejecutar(self, ps.pedir_cuenta, self.mesa)

    def _cancelar(self) -> None:
        if ps.pedido_de_mesa(self.mesa) is None:
            return
        if QMessageBox.question(self, "Anular", f"¿Anular el pedido de la mesa {self.mesa}?") \
                == QMessageBox.StandardButton.Yes:
            ejecutar(self, ps.cancelar_pedido, self.mesa)

    def _toggle_happy(self, activo: bool) -> None:
        ctx.forzar_happy_hour = activo
        ctx.bus.publicar(ev.PEDIDO_ACTUALIZADO, None)

    # ---------- vista ----------
    def refrescar(self) -> None:
        mesa = ctx.repos.mesas.obtener(self.mesa)
        pedido = mesa.pedido_actual
        self.estado_mesa.setText(f"Estado: {mesa.estado.value.replace('_', ' ')}"
                                 + (f" · Mesero: {pedido.mesero}" if pedido else ""))
        items = pedido.items if pedido else []
        self.tabla.setRowCount(len(items))
        for fila, it in enumerate(items):
            valores = [it.producto.nombre + (f"  ({it.nota})" if it.nota else ""), str(it.cantidad),
                       formato_moneda(it.precio_unitario), formato_moneda(it.subtotal),
                       "Enviado" if it.enviado else "Pendiente"]
            for col, v in enumerate(valores):
                celda = QTableWidgetItem(v)
                if col == 4:
                    celda.setForeground(QColor("#6FCB86" if it.enviado else "#E0A23B"))
                self.tabla.setItem(fila, col, celda)

        if pedido and not pedido.vacio:
            c = ps.calcular_cuenta(pedido)
            self.promos.setText("\n".join(f"✔ {n}: -{formato_moneda(v)}" for n, v in c["promociones"]))
            self.totales.setText(f"Subtotal {formato_moneda(c['subtotal'])}   ·   Desc. -{formato_moneda(c['descuentos'])}"
                                 f"   ·   Impoconsumo {formato_moneda(c['impuesto'])}"
                                 f"   ·   Propina sug. {formato_moneda(c['propina'])}")
            self.total.setText(formato_moneda(c["total"]))
        else:
            self.promos.setText("")
            self.totales.setText("Mesa sin pedido. Elija productos de la carta.")
            self.total.setText(formato_moneda(0))

        por_cobrar = mesa.estado == EstadoMesa.POR_COBRAR
        tiene = bool(pedido and not pedido.vacio)
        self.btn_quitar.setEnabled(tiene and not por_cobrar)
        self.btn_enviar.setEnabled(tiene and bool(pedido.items_pendientes()))
        self.btn_cuenta.setEnabled(tiene and not por_cobrar)
        self.btn_cancelar.setEnabled(tiene)
