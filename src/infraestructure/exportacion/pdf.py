"""Rutinas procedurales de exportación a PDF (fpdf2)."""
from pathlib import Path

from fpdf import FPDF


def _moneda(v: float) -> str:
    return f"${v:,.0f}".replace(",", ".")


def _titulo(doc: FPDF, texto: str) -> None:
    doc.set_font("Helvetica", "B", 16)
    doc.set_text_color(120, 70, 10)
    doc.cell(0, 10, texto, new_x="LMARGIN", new_y="NEXT", align="C")
    doc.set_text_color(0, 0, 0)


def _seccion(doc: FPDF, texto: str) -> None:
    doc.ln(3)
    doc.set_font("Helvetica", "B", 12)
    doc.set_fill_color(43, 29, 14)
    doc.set_text_color(245, 176, 65)
    doc.cell(0, 8, f"  {texto}", new_x="LMARGIN", new_y="NEXT", fill=True)
    doc.set_text_color(0, 0, 0)
    doc.set_font("Helvetica", "", 10)


def _fila(doc: FPDF, etiqueta: str, valor: str) -> None:
    doc.cell(95, 7, etiqueta, border="B")
    doc.cell(0, 7, valor, border="B", new_x="LMARGIN", new_y="NEXT", align="R")


def _tabla(doc: FPDF, columnas: list[tuple[str, int]], filas: list[list[str]]) -> None:
    doc.set_font("Helvetica", "B", 9)
    for nombre, ancho in columnas:
        doc.cell(ancho, 7, nombre, border=1, align="C")
    doc.ln()
    doc.set_font("Helvetica", "", 9)
    for fila in filas:
        for (_, ancho), valor in zip(columnas, fila):
            doc.cell(ancho, 6, str(valor), border=1)
        doc.ln()


def exportar_cierre_pdf(resumen: dict, facturas: list, ruta: Path) -> Path:
    doc = FPDF()
    doc.add_page()
    _titulo(doc, f"{resumen['negocio']} - Cierre de caja")
    doc.set_font("Helvetica", "", 10)
    doc.cell(0, 6, f"Cajero: {resumen['cajero']}   |   "
                   f"{resumen['apertura']:%Y-%m-%d %H:%M} a {resumen['cierre']:%H:%M}",
             new_x="LMARGIN", new_y="NEXT", align="C")

    _seccion(doc, "Totales")
    _fila(doc, "Facturas emitidas", str(resumen["num_facturas"]))
    _fila(doc, "Total ventas", _moneda(resumen["total_ventas"]))
    _fila(doc, "Impuesto al consumo", _moneda(resumen["total_impuesto"]))
    _fila(doc, "Propinas", _moneda(resumen["total_propinas"]))
    _fila(doc, "Descuentos aplicados", _moneda(resumen["total_descuentos"]))

    _seccion(doc, "Por método de pago")
    for metodo, total in resumen["por_metodo"].items():
        _fila(doc, metodo, _moneda(total))

    _seccion(doc, "Cuadre de efectivo")
    _fila(doc, "Monto inicial", _moneda(resumen["monto_inicial"]))
    _fila(doc, "Ingresos / egresos manuales", f"{_moneda(resumen['ingresos'])} / {_moneda(resumen['egresos'])}")
    _fila(doc, "Efectivo esperado", _moneda(resumen["efectivo_esperado"]))
    _fila(doc, "Efectivo contado", _moneda(resumen["efectivo_contado"]))
    _fila(doc, "Diferencia", _moneda(resumen["diferencia"]))

    if resumen["top_productos"]:
        _seccion(doc, "Productos más vendidos")
        for nombre, unidades in resumen["top_productos"]:
            _fila(doc, nombre, f"{unidades} und")

    if facturas:
        _seccion(doc, "Facturas")
        _tabla(doc, [("N°", 18), ("Hora", 22), ("Mesa", 16), ("Método", 30), ("Propina", 40), ("Total", 64)],
               [[f.numero, f"{f.fecha:%H:%M}", f.mesa_numero, f.metodo_pago, _moneda(f.propina),
                 _moneda(f.total)] for f in facturas])

    ruta.parent.mkdir(parents=True, exist_ok=True)
    doc.output(str(ruta))
    return ruta
