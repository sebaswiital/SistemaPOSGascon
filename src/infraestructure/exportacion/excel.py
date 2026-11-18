"""Rutinas procedurales de exportación a Excel (openpyxl)."""
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

_ENCABEZADO = PatternFill("solid", fgColor="2B1D0E")
_FUENTE_ENC = Font(bold=True, color="F5B041")


def _escribir_encabezado(hoja, columnas: list[str]) -> None:
    hoja.append(columnas)
    for celda in hoja[hoja.max_row]:
        celda.fill = _ENCABEZADO
        celda.font = _FUENTE_ENC
        celda.alignment = Alignment(horizontal="center")


def _ajustar_anchos(hoja) -> None:
    for columna in hoja.columns:
        ancho = max(len(str(c.value or "")) for c in columna) + 2
        hoja.column_dimensions[columna[0].column_letter].width = min(ancho, 45)


def _hoja_resumen(libro, resumen: dict) -> None:
    hoja = libro.active
    hoja.title = "Resumen"
    hoja.append([f"Cierre de caja - {resumen['negocio']}"])
    hoja["A1"].font = Font(bold=True, size=14)
    hoja.append([])
    filas = [
        ("Cajero", resumen["cajero"]),
        ("Apertura", resumen["apertura"].strftime("%Y-%m-%d %H:%M")),
        ("Cierre", resumen["cierre"].strftime("%Y-%m-%d %H:%M")),
        ("Monto inicial", resumen["monto_inicial"]),
        ("Facturas emitidas", resumen["num_facturas"]),
        ("Total ventas", resumen["total_ventas"]),
        ("Impuesto al consumo", resumen["total_impuesto"]),
        ("Propinas", resumen["total_propinas"]),
        ("Descuentos aplicados", resumen["total_descuentos"]),
        ("Ingresos manuales", resumen["ingresos"]),
        ("Egresos manuales", resumen["egresos"]),
        ("Efectivo esperado", resumen["efectivo_esperado"]),
        ("Efectivo contado", resumen["efectivo_contado"]),
        ("Diferencia", resumen["diferencia"]),
    ]
    for fila in filas:
        hoja.append(list(fila))
    hoja.append([])
    _escribir_encabezado(hoja, ["Método de pago", "Total"])
    for metodo, total in resumen["por_metodo"].items():
        hoja.append([metodo, total])
    hoja.append([])
    _escribir_encabezado(hoja, ["Top productos", "Unidades"])
    for nombre, unidades in resumen["top_productos"]:
        hoja.append([nombre, unidades])
    for fila in hoja.iter_rows(min_col=2, max_col=2):
        for celda in fila:
            if isinstance(celda.value, float):
                celda.number_format = '"$"#,##0'
    _ajustar_anchos(hoja)


def _hoja_facturas(libro, facturas: list) -> None:
    hoja = libro.create_sheet("Facturas")
    _escribir_encabezado(hoja, ["N°", "Fecha", "Mesa", "Cajero", "Subtotal", "Descuentos", "Impuesto",
                                "Propina", "Total", "Método"])
    for f in facturas:
        hoja.append([f.numero, f.fecha.strftime("%Y-%m-%d %H:%M"), f.mesa_numero, f.cajero, f.subtotal,
                     f.total_descuentos, f.impuesto, f.propina, f.total, f.metodo_pago])
    _ajustar_anchos(hoja)


def _hoja_detalle(libro, facturas: list) -> None:
    hoja = libro.create_sheet("Detalle")
    _escribir_encabezado(hoja, ["Factura", "Producto", "Cantidad", "Precio", "Subtotal"])
    for f in facturas:
        for l in f.lineas:
            hoja.append([f.numero, l["producto"], l["cantidad"], l["precio"], l["subtotal"]])
    _ajustar_anchos(hoja)


def exportar_cierre_excel(resumen: dict, facturas: list, ruta: Path) -> Path:
    libro = Workbook()
    _hoja_resumen(libro, resumen)
    _hoja_facturas(libro, facturas)
    _hoja_detalle(libro, facturas)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    libro.save(ruta)
    return ruta


def exportar_ventas_excel(facturas: list, ruta: Path) -> Path:
    libro = Workbook()
    libro.remove(libro.active)
    _hoja_facturas(libro, facturas)
    _hoja_detalle(libro, facturas)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    libro.save(ruta)
    return ruta
