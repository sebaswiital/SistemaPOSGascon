from datetime import datetime

from PySide6.QtWidgets import (QGridLayout, QGroupBox, QHBoxLayout, QHeaderView, QLabel, QListWidget,
                               QMessageBox, QProgressBar, QPushButton, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QWidget, QAbstractItemView)

from src.application.contexto import ctx
from src.application.services import reporte_service as rs
from src.config import settings
from src.infraestructure.eventos import bus_eventos as ev
from src.infraestructure.exportacion import excel
from src.presentation.utilidades import Tarjeta, ejecutar, formato_moneda

TEXTO_EVENTO = {
    ev.COMANDA_IMPRESA: lambda d: f"Comanda {d['area']} #{d['numero']} impresa (mesa {d['mesa']})",
    ev.TICKET_IMPRESO: lambda d: f"Ticket de factura {d['numero']} impreso",
    ev.FACTURA_EMITIDA: lambda f: f"Factura {f.numero} emitida: {formato_moneda(f.total)} ({f.metodo_pago})",
    ev.COMANDA_ENVIADA: lambda p: f"Comanda enviada desde mesa {p.mesa_numero}",
    ev.CAJA_ABIERTA: lambda d: f"Caja abierta por {d['cajero']}",
    ev.CAJA_CERRADA: lambda d: f"Caja cerrada: {formato_moneda(d['total_ventas'])}",
    ev.STOCK_BAJO: lambda d: f"Stock {d[1].lower()}: {d[0].nombre} ({d[0].stock})",
    ev.RESPALDO_REALIZADO: lambda d: "Respaldo automático guardado",
}


class Dashboard(QWidget):
    def __init__(self, puente):
        super().__init__()
        titulo = QLabel("Dashboard de ventas del día")
        titulo.setObjectName("titulo")
        self.actualizado = QLabel()
        self.actualizado.setObjectName("subtitulo")
        btn_exportar = QPushButton("Exportar ventas a Excel")
        cab = QHBoxLayout()
        cab.addWidget(titulo)
        cab.addStretch()
        cab.addWidget(self.actualizado)
        cab.addWidget(btn_exportar)

        self.k_ventas = Tarjeta("Ventas del día")
        self.k_facturas = Tarjeta("Facturas")
        self.k_ticket = Tarjeta("Ticket promedio")
        self.k_mesas = Tarjeta("Mesas ocupadas")
        self.k_propinas = Tarjeta("Propinas")
        self.k_cola = Tarjeta("Comandas en cola")
        kpis = QGridLayout()
        for i, t in enumerate((self.k_ventas, self.k_facturas, self.k_ticket, self.k_mesas, self.k_propinas,
                               self.k_cola)):
            kpis.addWidget(t, 0, i)

        g_top = QGroupBox("Productos más vendidos")
        self.tabla_top = QTableWidget(0, 2)
        self.tabla_top.setHorizontalHeaderLabels(["Producto", "Unidades"])
        self.tabla_top.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tabla_top.verticalHeader().setVisible(False)
        self.tabla_top.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        QVBoxLayout(g_top).addWidget(self.tabla_top)

        g_met = QGroupBox("Ventas por método de pago")
        cm = QVBoxLayout(g_met)
        self.barras = {}
        for metodo in ("Efectivo", "Tarjeta", "Nequi"):
            fila = QHBoxLayout()
            etiqueta = QLabel(metodo)
            etiqueta.setMinimumWidth(70)
            barra = QProgressBar()
            barra.setRange(0, 100)
            fila.addWidget(etiqueta)
            fila.addWidget(barra, 1)
            cm.addLayout(fila)
            self.barras[metodo] = barra
        cm.addStretch()

        g_act = QGroupBox("Actividad en tiempo real")
        self.actividad = QListWidget()
        QVBoxLayout(g_act).addWidget(self.actividad)

        fila = QHBoxLayout()
        fila.addWidget(g_top, 3)
        fila.addWidget(g_met, 3)
        fila.addWidget(g_act, 4)

        capa = QVBoxLayout(self)
        capa.addLayout(cab)
        capa.addLayout(kpis)
        capa.addLayout(fila, 1)

        btn_exportar.clicked.connect(self._exportar)
        puente.escuchar(self._al_evento)
        self.refrescar()

    def _al_evento(self, nombre: str, datos) -> None:
        if nombre in TEXTO_EVENTO:
            try:
                texto = TEXTO_EVENTO[nombre](datos)
            except Exception:
                texto = nombre
            self.actividad.insertItem(0, f"{datetime.now():%H:%M:%S}  {texto}")
            while self.actividad.count() > 200:
                self.actividad.takeItem(self.actividad.count() - 1)
        if nombre in (ev.DASHBOARD_TICK, ev.FACTURA_EMITIDA, ev.MESA_CAMBIADA, ev.COMANDA_IMPRESA,
                      ev.COMANDA_ENVIADA):
            self.refrescar()

    def _exportar(self) -> None:
        facturas = ctx.repos.facturas.del_dia()
        ruta = settings.DIR_REPORTES / f"ventas_{datetime.now():%Y%m%d_%H%M%S}.xlsx"
        if ejecutar(self, excel.exportar_ventas_excel, facturas, ruta):
            QMessageBox.information(self, "Exportación", f"Archivo generado:\n{ruta}")

    def refrescar(self) -> None:
        facturas = ctx.repos.facturas.del_dia()
        r = rs.resumen(facturas)
        self.k_ventas.poner(formato_moneda(r["total"]))
        self.k_facturas.poner(str(r["num_facturas"]))
        self.k_ticket.poner(formato_moneda(r["ticket_promedio"]))
        self.k_mesas.poner(f"{len(ctx.repos.mesas.ocupadas())}/{len(ctx.repos.mesas)}")
        self.k_propinas.poner(formato_moneda(r["propinas"]))
        pend = ctx.cola_comandas.pendientes() if ctx.cola_comandas else {}
        self.k_cola.poner(" · ".join(f"{a} {n}" for a, n in pend.items()) or "0")

        self.tabla_top.setRowCount(len(r["top"]))
        for fila, (nombre, unidades) in enumerate(r["top"]):
            self.tabla_top.setItem(fila, 0, QTableWidgetItem(nombre))
            self.tabla_top.setItem(fila, 1, QTableWidgetItem(str(unidades)))

        total = r["total"] or 1
        for metodo, barra in self.barras.items():
            valor = r["por_metodo"].get(metodo, 0)
            barra.setValue(int(valor * 100 / total))
            barra.setFormat(f"{formato_moneda(valor)}  ({valor * 100 / total:.0f}%)")
        self.actualizado.setText(f"Actualizado {datetime.now():%H:%M:%S}")
