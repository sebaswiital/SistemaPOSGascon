from datetime import date

from src.domain.entities import Empleado, EstadoMesa, EstadoPedido, Factura, Mesa, Pedido, Producto
from src.infraestructure.database.repositorios.base import RepositorioBase


class RepositorioProductos(RepositorioBase[Producto]):
    def por_categoria(self, categoria: str) -> list[Producto]:
        return self.buscar(categoria=categoria, orden=lambda p: p.nombre)

    def categorias(self) -> list[str]:
        return sorted({p.categoria for p in self.todos()})

    def con_stock_bajo(self) -> list[Producto]:
        return self.buscar(filtro=lambda p: p.stock_bajo, orden=lambda p: p.stock)


class RepositorioMesas(RepositorioBase[Mesa]):
    def libres(self) -> list[Mesa]:
        return self.buscar(estado=EstadoMesa.LIBRE)

    def ocupadas(self) -> list[Mesa]:
        return self.buscar(filtro=lambda m: m.estado != EstadoMesa.LIBRE, orden=lambda m: m.numero)


class RepositorioPedidos(RepositorioBase[Pedido]):
    def abiertos(self) -> list[Pedido]:
        return self.buscar(estado=EstadoPedido.ABIERTO)


class RepositorioFacturas(RepositorioBase[Factura]):
    def del_dia(self, dia: date | None = None) -> list[Factura]:
        dia = dia or date.today()
        return self.buscar(filtro=lambda f: f.fecha.date() == dia, orden=lambda f: f.numero)

    def desde(self, momento) -> list[Factura]:
        return self.buscar(filtro=lambda f: f.fecha >= momento, orden=lambda f: f.numero)


class RepositorioEmpleados(RepositorioBase[Empleado]):
    def por_usuario(self, usuario: str) -> Empleado | None:
        return self.primero(usuario=usuario)
