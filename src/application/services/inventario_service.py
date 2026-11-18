from src.application.contexto import ctx
from src.application.decoradores import registrar, requiere_rol
from src.application.esquemas import AjusteStockIn, ProductoIn
from src.domain.entities import Bebida, Coctel, Plato, Producto, Rol
from src.domain.reglas.reglas_negocio import nivel_alerta
from src.infraestructure.eventos import bus_eventos as ev

_FABRICA = {"Plato": Plato, "Bebida": Bebida, "Coctel": Coctel}


@registrar
@requiere_rol(Rol.ADMIN)
def reponer(producto_id: int, cantidad: int) -> Producto:
    datos = AjusteStockIn(producto_id=producto_id, cantidad=cantidad)
    producto = ctx.repos.productos.obtener(datos.producto_id)
    if producto is None:
        raise ValueError("Producto inexistente")
    producto.reponer_stock(datos.cantidad)
    ctx.bus.publicar(ev.INVENTARIO_ACTUALIZADO, producto)
    return producto


@registrar
@requiere_rol(Rol.ADMIN)
def crear_producto(**campos) -> Producto:
    datos = ProductoIn(**campos)
    extra = {"categoria": datos.categoria} if datos.categoria else {}
    producto = _FABRICA[datos.tipo](datos.nombre, datos.precio, stock=datos.stock,
                                    stock_minimo=datos.stock_minimo, **extra)
    ctx.repos.productos.agregar(producto)
    ctx.bus.publicar(ev.INVENTARIO_ACTUALIZADO, producto)
    return producto


def revisar_alertas() -> None:
    """Publica un evento por cada producto que dispara una regla de alerta."""
    for p in ctx.repos.productos.todos():
        if nivel := nivel_alerta(p):
            ctx.bus.publicar(ev.STOCK_BAJO, (p, nivel))
