"""Paradigma funcional: funciones puras (sin efectos secundarios, mismas entradas -> mismas
salidas). Trabajan con tuplas inmutables y se componen entre sí."""
from functools import reduce
from typing import Iterable

Linea = tuple[float, int]  # (precio_unitario, cantidad)


def redondear(valor: float) -> float:
    return round(valor, 2)


def subtotal_linea(linea: Linea) -> float:
    precio, cantidad = linea
    return precio * cantidad


def subtotal(lineas: Iterable[Linea]) -> float:
    return redondear(reduce(lambda acc, l: acc + subtotal_linea(l), lineas, 0.0))


def total_descuentos(descuentos: Iterable[tuple[str, float]]) -> float:
    return redondear(sum(map(lambda d: d[1], descuentos)))


def aplicar_descuento(monto: float, porcentaje: float) -> float:
    """Devuelve el monto con el porcentaje (0..1) de descuento aplicado."""
    return redondear(monto * (1 - max(0.0, min(porcentaje, 1.0))))


def valor_descuento(monto: float, porcentaje: float) -> float:
    return redondear(monto - aplicar_descuento(monto, porcentaje))


def calcular_impuesto(base: float, tasa: float) -> float:
    return redondear(max(base, 0.0) * tasa)


def calcular_propina(base: float, porcentaje: float = 0.10) -> float:
    return redondear(max(base, 0.0) * porcentaje)


def total_factura(lineas: tuple[Linea, ...], descuentos: tuple[tuple[str, float], ...],
                  tasa_impuesto: float, porcentaje_propina: float) -> dict:
    """Composición de funciones puras: devuelve un dict nuevo con todos los totales."""
    sub = subtotal(lineas)
    desc = min(total_descuentos(descuentos), sub)
    base = redondear(sub - desc)
    imp = calcular_impuesto(base, tasa_impuesto)
    prop = calcular_propina(base, porcentaje_propina)
    return {"subtotal": sub, "descuentos": desc, "base": base, "impuesto": imp,
            "propina": prop, "total": redondear(base + imp + prop)}


def cambio(recibido: float, total: float) -> float:
    return redondear(recibido - total)


def formato_moneda(valor: float) -> str:
    return f"${valor:,.0f}".replace(",", ".")
