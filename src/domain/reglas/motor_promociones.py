"""Paradigma lógico (basado en reglas).

Cada Regla es un par  condicion(hechos) -> bool  /  conclusion(hechos) -> descuento.
El motor hace *encadenamiento hacia adelante*: evalúa las reglas por prioridad y cada
conclusión agrega nuevos hechos a la base (p. ej. 'descuento_acumulado'), que las reglas
posteriores pueden usar en sus condiciones.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from src.config import settings

Hechos = dict


@dataclass(frozen=True)
class Regla:
    nombre: str
    condicion: Callable[[Hechos], bool]
    conclusion: Callable[[Hechos], float]
    prioridad: int = 0


# ---------------- predicados (hechos derivados) ----------------
def es_happy_hour(h: Hechos) -> bool:
    return h.get("forzar_happy_hour") or settings.HAPPY_HOUR_INICIO <= h["hora"] < settings.HAPPY_HOUR_FIN


def lineas_de(h: Hechos, predicado) -> list[dict]:
    return [l for l in h["lineas"] if predicado(l)]


def es_coctel(l):
    return l["tipo"] == "Coctel"


def es_cerveza(l):
    return l["categoria"] == "Cervezas"


def es_hamburguesa(l):
    return "hamburguesa" in l["nombre"].lower()


def unidades(lineas: list[dict]) -> int:
    return sum(l["cantidad"] for l in lineas)


def precio_minimo(lineas: list[dict]) -> float:
    return min(l["precio"] for l in lineas)


# ---------------- base de reglas ----------------
REGLAS: list[Regla] = [
    Regla(
        "Happy Hour: 30% en cócteles",
        condicion=lambda h: es_happy_hour(h) and bool(lineas_de(h, es_coctel)),
        conclusion=lambda h: sum(l["precio"] * l["cantidad"] for l in lineas_de(h, es_coctel))
        * settings.DESCUENTO_HAPPY_HOUR,
        prioridad=1,
    ),
    Regla(
        "Happy Hour: 2x1 en cervezas",
        condicion=lambda h: es_happy_hour(h) and unidades(lineas_de(h, es_cerveza)) >= 2,
        conclusion=lambda h: sum((l["cantidad"] // 2) * l["precio"] for l in lineas_de(h, es_cerveza)),
        prioridad=1,
    ),
    Regla(
        "Combo hamburguesa + cerveza (15%)",
        # el combo no se acumula con el 2x1 de happy hour
        condicion=lambda h: not es_happy_hour(h) and bool(lineas_de(h, es_hamburguesa))
        and bool(lineas_de(h, es_cerveza)),
        conclusion=lambda h: min(unidades(lineas_de(h, es_hamburguesa)), unidades(lineas_de(h, es_cerveza)))
        * (precio_minimo(lineas_de(h, es_hamburguesa)) + precio_minimo(lineas_de(h, es_cerveza)))
        * settings.DESCUENTO_COMBO,
        prioridad=2,
    ),
    Regla(
        "Cliente frecuente: 5% por consumo alto",
        # usa el hecho derivado 'descuento_acumulado' producido por reglas anteriores
        condicion=lambda h: h["subtotal"] - h["descuento_acumulado"] >= settings.MONTO_DESCUENTO_ALTO,
        conclusion=lambda h: (h["subtotal"] - h["descuento_acumulado"]) * settings.DESCUENTO_MONTO_ALTO,
        prioridad=9,
    ),
]


class MotorPromociones:
    def __init__(self, reglas: list[Regla] | None = None):
        self.reglas = sorted(reglas if reglas is not None else REGLAS, key=lambda r: r.prioridad)

    @staticmethod
    def construir_hechos(pedido, ahora: datetime | None = None, forzar_happy_hour: bool = False) -> Hechos:
        ahora = ahora or datetime.now()
        lineas = [{"nombre": i.producto.nombre, "tipo": i.producto.tipo, "categoria": i.producto.categoria,
                   "precio": i.precio_unitario, "cantidad": i.cantidad} for i in pedido.items]
        return {"hora": ahora.hour, "lineas": lineas, "forzar_happy_hour": forzar_happy_hour,
                "subtotal": sum(l["precio"] * l["cantidad"] for l in lineas), "descuento_acumulado": 0.0}

    def inferir(self, hechos: Hechos) -> list[tuple[str, float]]:
        aplicadas = []
        for regla in self.reglas:
            if regla.condicion(hechos):
                valor = round(regla.conclusion(hechos), 2)
                if valor > 0:
                    aplicadas.append((regla.nombre, valor))
                    hechos["descuento_acumulado"] += valor  # nuevo hecho
        return aplicadas

    def evaluar(self, pedido, ahora: datetime | None = None, forzar_happy_hour: bool = False):
        return self.inferir(self.construir_hechos(pedido, ahora, forzar_happy_hour))
