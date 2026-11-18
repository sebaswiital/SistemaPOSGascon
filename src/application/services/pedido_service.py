"""Casos de uso de mesas y pedidos."""
from src.application.calculos import funciones_puras as fp
from src.application.contexto import ctx
from src.application.decoradores import PermisoDenegado, registrar, requiere_rol
from src.application.esquemas import ItemPedidoIn
from src.config import settings
from src.domain.entities import EstadoMesa, EstadoPedido, Mesa, Pedido, Rol
from src.domain.reglas.motor_promociones import MotorPromociones
from src.domain.reglas.reglas_negocio import alertas_inventario, exigir, nivel_alerta
from src.infraestructure.eventos import bus_eventos as ev

motor = MotorPromociones()


def _mesa(numero: int) -> Mesa:
    mesa = ctx.repos.mesas.obtener(numero)
    if mesa is None:
        raise ValueError(f"La mesa {numero} no existe")
    return mesa


def pedido_de_mesa(numero: int) -> Pedido | None:
    return _mesa(numero).pedido_actual


@registrar
@requiere_rol(Rol.MESERO, Rol.CAJERO)
def abrir_pedido(numero_mesa: int) -> Pedido:
    mesa = _mesa(numero_mesa)
    if mesa.pedido_actual:
        return mesa.pedido_actual
    pedido = ctx.repos.pedidos.agregar(Pedido(numero_mesa, ctx.usuario.nombre))
    mesa.ocupar(pedido)
    ctx.bus.publicar(ev.MESA_CAMBIADA, mesa)
    return pedido


@registrar
@requiere_rol(Rol.MESERO, Rol.CAJERO)
def agregar_item(numero_mesa: int, producto_id: int, cantidad: int = 1, nota: str = ""):
    datos = ItemPedidoIn(producto_id=producto_id, cantidad=cantidad, nota=nota)
    mesa = _mesa(numero_mesa)
    producto = ctx.repos.productos.obtener(datos.producto_id)
    if producto is None:
        raise ValueError("Producto inexistente")
    exigir("agregar_item", {"producto": producto, "cantidad": datos.cantidad, "mesa": mesa})
    pedido = abrir_pedido(numero_mesa)
    item = pedido.agregar(producto, datos.cantidad, datos.nota)
    ctx.bus.publicar(ev.PEDIDO_ACTUALIZADO, pedido)
    ctx.bus.publicar(ev.INVENTARIO_ACTUALIZADO, producto)
    if nivel := nivel_alerta(producto):
        ctx.bus.publicar(ev.STOCK_BAJO, (producto, nivel))
    return item


@registrar
@requiere_rol(Rol.MESERO, Rol.CAJERO)
def quitar_item(numero_mesa: int, indice: int) -> None:
    pedido = pedido_de_mesa(numero_mesa)
    if pedido is None:
        return
    item = pedido.items[indice]
    pedido.quitar(item)
    ctx.bus.publicar(ev.PEDIDO_ACTUALIZADO, pedido)
    ctx.bus.publicar(ev.INVENTARIO_ACTUALIZADO, item.producto)
    if pedido.vacio:
        cancelar_pedido(numero_mesa)


@registrar
@requiere_rol(Rol.MESERO, Rol.CAJERO)
def cancelar_pedido(numero_mesa: int) -> None:
    mesa = _mesa(numero_mesa)
    pedido = mesa.pedido_actual
    if pedido is None:
        return
    if any(i.enviado for i in pedido.items) and not ctx.usuario.tiene_rol(Rol.ADMIN):
        raise PermisoDenegado("Solo el administrador puede anular pedidos ya enviados a preparación")
    for item in list(pedido.items):
        item.producto.reponer_stock(item.cantidad)
    pedido.items.clear()
    pedido.estado = EstadoPedido.CANCELADO
    mesa.liberar()
    ctx.bus.publicar(ev.PEDIDO_ACTUALIZADO, pedido)
    ctx.bus.publicar(ev.MESA_CAMBIADA, mesa)
    ctx.bus.publicar(ev.INVENTARIO_ACTUALIZADO, None)


@registrar
@requiere_rol(Rol.MESERO, Rol.CAJERO)
def enviar_comanda(numero_mesa: int) -> int:
    """Envía los items pendientes a la cola concurrente de comandas. Devuelve cuántos envió."""
    pedido = pedido_de_mesa(numero_mesa)
    if pedido is None or not pedido.items_pendientes():
        return 0
    pendientes = pedido.items_pendientes()
    ctx.cola_comandas.enviar(pedido, pendientes)
    for item in pendientes:
        item.enviado = True
    ctx.bus.publicar(ev.COMANDA_ENVIADA, pedido)
    ctx.bus.publicar(ev.PEDIDO_ACTUALIZADO, pedido)
    return len(pendientes)


@registrar
@requiere_rol(Rol.MESERO, Rol.CAJERO)
def pedir_cuenta(numero_mesa: int) -> None:
    enviar_comanda(numero_mesa)
    mesa = _mesa(numero_mesa)
    mesa.solicitar_cuenta()
    ctx.bus.publicar(ev.MESA_CAMBIADA, mesa)


def calcular_cuenta(pedido: Pedido, incluir_propina: bool = True) -> dict:
    """Combina el motor de reglas (promociones) con las funciones puras (totales)."""
    descuentos = tuple(motor.evaluar(pedido, forzar_happy_hour=ctx.forzar_happy_hour))
    lineas = tuple((i.precio_unitario, i.cantidad) for i in pedido.items)
    totales = fp.total_factura(lineas, descuentos, settings.TASA_IMPOCONSUMO,
                               settings.PROPINA_SUGERIDA if incluir_propina else 0.0)
    return {**totales, "promociones": list(descuentos)}


def alertas_actuales():
    return alertas_inventario(ctx.repos.productos.todos())


def mesas_con_pedido() -> int:
    return len([m for m in ctx.repos.mesas.todos() if m.estado != EstadoMesa.LIBRE])
