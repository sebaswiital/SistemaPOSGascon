from datetime import datetime
from enum import Enum
from itertools import count

from src.domain.entities.producto import Producto

_ids = count(1)


class EstadoPedido(str, Enum):
    ABIERTO = "abierto"
    FACTURADO = "facturado"
    CANCELADO = "cancelado"


class ItemPedido:
    def __init__(self, producto: Producto, cantidad: int = 1, nota: str = ""):
        self.producto = producto
        self.cantidad = cantidad
        self.nota = nota
        self.enviado = False  # ya salió en comanda

    @property
    def precio_unitario(self) -> float:
        return self.producto.precio

    @property
    def subtotal(self) -> float:
        return self.precio_unitario * self.cantidad

    def a_dict(self) -> dict:
        return {"producto": self.producto.nombre, "cantidad": self.cantidad,
                "precio": self.precio_unitario, "nota": self.nota}

    def __repr__(self) -> str:
        return f"{self.cantidad}x {self.producto.nombre}"


class Pedido:
    def __init__(self, mesa_numero: int, mesero: str):
        self.id = next(_ids)
        self.mesa_numero = mesa_numero
        self.mesero = mesero
        self.items: list[ItemPedido] = []
        self.estado = EstadoPedido.ABIERTO
        self.creado = datetime.now()
        self.descuentos: list[tuple[str, float]] = []  # (nombre promoción, valor)

    def agregar(self, producto: Producto, cantidad: int = 1, nota: str = "") -> ItemPedido:
        if self.estado != EstadoPedido.ABIERTO:
            raise ValueError("El pedido ya no está abierto")
        producto.descontar_stock(cantidad)
        # agrupa con un item existente no enviado del mismo producto y nota
        for item in self.items:
            if item.producto is producto and item.nota == nota and not item.enviado:
                item.cantidad += cantidad
                return item
        item = ItemPedido(producto, cantidad, nota)
        self.items.append(item)
        return item

    def quitar(self, item: ItemPedido) -> None:
        if item.enviado:
            raise ValueError("No se puede quitar un item que ya fue enviado a preparación")
        item.producto.reponer_stock(item.cantidad)
        self.items.remove(item)

    def items_pendientes(self) -> list[ItemPedido]:
        return [i for i in self.items if not i.enviado]

    @property
    def vacio(self) -> bool:
        return not self.items

    def a_dict(self) -> dict:
        return {"id": self.id, "mesa": self.mesa_numero, "mesero": self.mesero,
                "estado": self.estado.value, "creado": self.creado.isoformat(),
                "items": [i.a_dict() for i in self.items]}

    def __repr__(self) -> str:
        return f"<Pedido {self.id} mesa {self.mesa_numero}: {self.items}>"
