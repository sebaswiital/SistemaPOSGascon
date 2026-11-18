"""Paradigma funcional: estadísticas de ventas a partir de composición de funciones puras
(map / filter / reduce / sorted / groupby). Ninguna función modifica sus entradas."""
from collections import Counter
from functools import reduce
from itertools import groupby
from operator import itemgetter
from typing import Callable, Iterable

from src.domain.entities import Factura


def componer(*funciones: Callable) -> Callable:
    return lambda x: reduce(lambda acc, f: f(acc), funciones, x)


def total_vendido(facturas: Iterable[Factura]) -> float:
    return round(sum(map(lambda f: f.total, facturas)), 2)


def ticket_promedio(facturas: list[Factura]) -> float:
    return round(total_vendido(facturas) / len(facturas), 2) if facturas else 0.0


def ventas_por_metodo(facturas: Iterable[Factura]) -> dict[str, float]:
    ordenadas = sorted(facturas, key=lambda f: f.metodo_pago)
    return {metodo: round(sum(f.total for f in grupo), 2)
            for metodo, grupo in groupby(ordenadas, key=lambda f: f.metodo_pago)}


def ventas_por_hora(facturas: Iterable[Factura]) -> dict[int, float]:
    ordenadas = sorted(facturas, key=lambda f: f.fecha.hour)
    return {h: round(sum(f.total for f in g), 2) for h, g in groupby(ordenadas, key=lambda f: f.fecha.hour)}


def ventas_por_dia(facturas: Iterable[Factura]) -> dict[str, float]:
    ordenadas = sorted(facturas, key=lambda f: f.fecha.date())
    return {str(d): round(sum(f.total for f in g), 2) for d, g in groupby(ordenadas, key=lambda f: f.fecha.date())}


def _lineas(facturas: Iterable[Factura]):
    return (l for f in facturas for l in f.lineas)


def unidades_por_producto(facturas: Iterable[Factura]) -> Counter:
    return reduce(lambda c, l: c + Counter({l["producto"]: l["cantidad"]}), _lineas(facturas), Counter())


def top_productos(facturas: Iterable[Factura], n: int = 5) -> list[tuple[str, int]]:
    return componer(unidades_por_producto, lambda c: c.most_common(n))(list(facturas))


def ingresos_por_producto(facturas: Iterable[Factura]) -> list[tuple[str, float]]:
    pares = sorted(((l["producto"], l["subtotal"]) for l in _lineas(facturas)), key=itemgetter(0))
    totales = ((p, round(sum(map(itemgetter(1), g)), 2)) for p, g in groupby(pares, key=itemgetter(0)))
    return sorted(totales, key=itemgetter(1), reverse=True)


def facturas_mayores_a(monto: float) -> Callable[[Iterable[Factura]], list[Factura]]:
    """Currificación: devuelve un filtro configurado."""
    return lambda facturas: list(filter(lambda f: f.total > monto, facturas))


def resumen(facturas: list[Factura]) -> dict:
    return {"total": total_vendido(facturas), "num_facturas": len(facturas),
            "ticket_promedio": ticket_promedio(facturas), "por_metodo": ventas_por_metodo(facturas),
            "por_hora": ventas_por_hora(facturas), "top": top_productos(facturas, 5),
            "propinas": round(sum(f.propina for f in facturas), 2),
            "descuentos": round(sum(f.total_descuentos for f in facturas), 2)}
