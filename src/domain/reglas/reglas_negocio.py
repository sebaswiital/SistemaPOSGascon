"""Paradigma lógico: validaciones de negocio y alertas de inventario como base de reglas.

Cada regla declara *cuándo se viola* y el mensaje. `verificar` consulta todas las reglas
de una acción y devuelve las violaciones; no hay if/else repartidos por el código."""
from dataclasses import dataclass
from typing import Callable

from src.domain.entities.mesa import EstadoMesa
from src.domain.entities.pedido import EstadoPedido


class ReglaNegocioViolada(Exception):
    pass


@dataclass(frozen=True)
class Restriccion:
    accion: str
    violada: Callable[[dict], bool]
    mensaje: str


RESTRICCIONES: list[Restriccion] = [
    Restriccion("facturar", lambda c: not c["caja_abierta"], "No se puede facturar: la caja está cerrada"),
    Restriccion("facturar", lambda c: c["pedido"] is None or c["pedido"].vacio, "El pedido no tiene productos"),
    Restriccion("facturar", lambda c: c["pedido"] is not None and c["pedido"].estado != EstadoPedido.ABIERTO,
                "El pedido ya fue facturado"),
    Restriccion("facturar", lambda c: c["pedido"] is not None and bool(c["pedido"].items_pendientes()),
                "Hay productos sin enviar a cocina/bar"),
    Restriccion("liberar_mesa", lambda c: c["mesa"].pedido_actual is not None
                and c["mesa"].pedido_actual.estado == EstadoPedido.ABIERTO
                and not c["mesa"].pedido_actual.vacio, "La mesa tiene un pedido sin pagar"),
    Restriccion("agregar_item", lambda c: c["cantidad"] > c["producto"].stock,
                "Stock insuficiente para el producto"),
    Restriccion("agregar_item", lambda c: c["mesa"].estado == EstadoMesa.POR_COBRAR,
                "La mesa ya pidió la cuenta"),
    Restriccion("abrir_caja", lambda c: c["caja_abierta"], "La caja ya está abierta"),
    Restriccion("cerrar_caja", lambda c: not c["caja_abierta"], "La caja no está abierta"),
    Restriccion("cerrar_caja", lambda c: c["mesas_con_pedido"] > 0,
                "Hay mesas con pedidos abiertos; cóbrelas o cancélelas antes de cerrar"),
]


def verificar(accion: str, contexto: dict) -> list[str]:
    return [r.mensaje for r in RESTRICCIONES if r.accion == accion and r.violada(contexto)]


def exigir(accion: str, contexto: dict) -> None:
    violaciones = verificar(accion, contexto)
    if violaciones:
        raise ReglaNegocioViolada("\n".join(violaciones))


# ---------------- alertas de inventario ----------------
@dataclass(frozen=True)
class ReglaAlerta:
    nivel: str
    condicion: Callable[[object], bool]


REGLAS_INVENTARIO = [
    ReglaAlerta("AGOTADO", lambda p: p.stock == 0),
    ReglaAlerta("CRÍTICO", lambda p: 0 < p.stock <= p.stock_minimo // 2),
    ReglaAlerta("BAJO", lambda p: p.stock_minimo // 2 < p.stock <= p.stock_minimo),
]


def nivel_alerta(producto) -> str | None:
    return next((r.nivel for r in REGLAS_INVENTARIO if r.condicion(producto)), None)


def alertas_inventario(productos) -> list[tuple[object, str]]:
    return [(p, n) for p in productos if (n := nivel_alerta(p))]
