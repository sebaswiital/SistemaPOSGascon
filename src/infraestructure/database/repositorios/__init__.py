from dataclasses import dataclass, field

from src.infraestructure.database.repositorios.base import RepositorioBase
from src.infraestructure.database.repositorios.repositorios import (
    RepositorioEmpleados, RepositorioFacturas, RepositorioMesas, RepositorioPedidos, RepositorioProductos)


@dataclass
class Repositorios:
    """Agrupa todos los repositorios en memoria de la sesión de la aplicación."""
    productos: RepositorioProductos = field(default_factory=RepositorioProductos)
    mesas: RepositorioMesas = field(default_factory=RepositorioMesas)
    pedidos: RepositorioPedidos = field(default_factory=RepositorioPedidos)
    facturas: RepositorioFacturas = field(default_factory=RepositorioFacturas)
    empleados: RepositorioEmpleados = field(default_factory=RepositorioEmpleados)

    def snapshot(self) -> dict:
        return {"productos": [p.a_dict() for p in self.productos.todos()],
                "mesas": [m.a_dict() for m in self.mesas.todos()],
                "pedidos": [p.a_dict() for p in self.pedidos.todos()],
                "facturas": [f.a_dict() for f in self.facturas.todos()],
                "empleados": [e.a_dict() for e in self.empleados.todos()]}


__all__ = ["Repositorios", "RepositorioBase", "RepositorioProductos", "RepositorioMesas",
           "RepositorioPedidos", "RepositorioFacturas", "RepositorioEmpleados"]
