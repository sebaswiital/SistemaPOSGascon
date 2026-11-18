"""Jerarquía de productos de la carta (POO: herencia, abstracción, polimorfismo)."""
from abc import ABC, abstractmethod
from itertools import count

_ids = count(1)


class Producto(ABC):
    def __init__(self, nombre: str, precio: float, stock: int = 50, stock_minimo: int = 5,
                 categoria: str = ""):
        self._id = next(_ids)
        self._nombre = nombre
        self._precio = float(precio)
        self._stock = int(stock)
        self.stock_minimo = int(stock_minimo)
        self.categoria = categoria

    # --- encapsulación ---
    @property
    def id(self) -> int:
        return self._id

    @property
    def nombre(self) -> str:
        return self._nombre

    @property
    def precio(self) -> float:
        return self._precio

    @precio.setter
    def precio(self, valor: float) -> None:
        if valor <= 0:
            raise ValueError("El precio debe ser positivo")
        self._precio = float(valor)

    @property
    def stock(self) -> int:
        return self._stock

    def descontar_stock(self, cantidad: int) -> None:
        if cantidad > self._stock:
            raise ValueError(f"Stock insuficiente de {self._nombre} (quedan {self._stock})")
        self._stock -= cantidad

    def reponer_stock(self, cantidad: int) -> None:
        self._stock += cantidad

    @property
    def stock_bajo(self) -> bool:
        return self._stock <= self.stock_minimo

    # --- polimorfismo ---
    @property
    @abstractmethod
    def tipo(self) -> str: ...

    @abstractmethod
    def area_preparacion(self) -> str:
        """'cocina' o 'bar': define a qué impresora va la comanda."""

    def descripcion(self) -> str:
        return f"{self.nombre} - ${self.precio:,.0f}"

    def a_dict(self) -> dict:
        return {"id": self.id, "tipo": self.tipo, "nombre": self.nombre, "precio": self.precio,
                "stock": self.stock, "categoria": self.categoria}

    def __repr__(self) -> str:
        return f"<{self.tipo} {self.nombre}>"


class Plato(Producto):
    def __init__(self, nombre, precio, tiempo_preparacion_min: int = 15, **kw):
        super().__init__(nombre, precio, categoria=kw.pop("categoria", "Comida"), **kw)
        self.tiempo_preparacion_min = tiempo_preparacion_min

    @property
    def tipo(self) -> str:
        return "Plato"

    def area_preparacion(self) -> str:
        return "cocina"

    def descripcion(self) -> str:
        return f"{super().descripcion()} ({self.tiempo_preparacion_min} min)"


class Bebida(Producto):
    def __init__(self, nombre, precio, mililitros: int = 330, alcoholica: bool = False, **kw):
        super().__init__(nombre, precio, categoria=kw.pop("categoria", "Bebidas"), **kw)
        self.mililitros = mililitros
        self.alcoholica = alcoholica

    @property
    def tipo(self) -> str:
        return "Bebida"

    def area_preparacion(self) -> str:
        return "bar"

    def descripcion(self) -> str:
        return f"{super().descripcion()} {self.mililitros}ml"


class Coctel(Bebida):
    def __init__(self, nombre, precio, ingredientes: list[str] | None = None, **kw):
        kw.setdefault("categoria", "Cócteles")
        super().__init__(nombre, precio, alcoholica=True, **kw)
        self.ingredientes = ingredientes or []

    @property
    def tipo(self) -> str:
        return "Coctel"

    def descripcion(self) -> str:
        return f"{self.nombre} - ${self.precio:,.0f} [{', '.join(self.ingredientes)}]"
