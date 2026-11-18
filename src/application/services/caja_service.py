"""Paradigma procedural / imperativo: la caja se maneja con procedimientos que modifican un
estado explícito (`_caja`) siguiendo pasos en orden."""
from datetime import datetime

from src.application.contexto import ctx
from src.application.decoradores import registrar, requiere_rol
from src.application.esquemas import AperturaCajaIn, PagoIn
from src.application.services import pedido_service, reporte_service
from src.config import settings
from src.domain.entities import EstadoPedido, Factura, Rol
from src.domain.pagos.metodos_pago import Efectivo, MetodoPago, Nequi, Tarjeta
from src.domain.reglas.reglas_negocio import exigir
from src.infraestructure.eventos import bus_eventos as ev
from src.infraestructure.exportacion import excel, pdf

# ---- estado global de la caja (procedural) ----
_caja = {"abierta": False, "apertura": None, "monto_inicial": 0.0, "cajero": None, "movimientos": []}
_historial_cierres: list[dict] = []


def caja_abierta() -> bool:
    return _caja["abierta"]


def estado_caja() -> dict:
    return dict(_caja)


def historial_cierres() -> list[dict]:
    return list(_historial_cierres)


@registrar
@requiere_rol(Rol.CAJERO)
def abrir_caja(monto_inicial: float) -> None:
    datos = AperturaCajaIn(monto_inicial=monto_inicial)
    exigir("abrir_caja", {"caja_abierta": _caja["abierta"]})
    _caja["abierta"] = True
    _caja["apertura"] = datetime.now()
    _caja["monto_inicial"] = datos.monto_inicial
    _caja["cajero"] = ctx.usuario.nombre
    _caja["movimientos"] = []
    ctx.bus.publicar(ev.CAJA_ABIERTA, estado_caja())


@registrar
@requiere_rol(Rol.CAJERO)
def registrar_movimiento(tipo: str, monto: float, concepto: str) -> dict:
    """tipo: 'ingreso' o 'egreso' (p.ej. compra de hielo, pago a proveedor)."""
    if not _caja["abierta"]:
        raise ValueError("La caja está cerrada")
    if tipo not in ("ingreso", "egreso") or monto <= 0:
        raise ValueError("Movimiento inválido: el monto debe ser mayor a 0")
    movimiento = {"tipo": tipo, "monto": float(monto), "concepto": concepto, "hora": datetime.now()}
    _caja["movimientos"].append(movimiento)
    return movimiento


def _crear_metodo(pago: PagoIn) -> MetodoPago:
    if pago.metodo == "Efectivo":
        return Efectivo(pago.recibido)
    if pago.metodo == "Tarjeta":
        return Tarjeta(pago.numero_tarjeta, pago.franquicia)
    return Nequi(pago.celular)


@registrar
@requiere_rol(Rol.CAJERO)
def cobrar_mesa(numero_mesa: int, pago: PagoIn) -> Factura:
    mesa = ctx.repos.mesas.obtener(numero_mesa)
    pedido = mesa.pedido_actual
    # 1. validar reglas de negocio
    exigir("facturar", {"caja_abierta": _caja["abierta"], "pedido": pedido})
    # 2. calcular totales (motor de reglas + funciones puras)
    cuenta = pedido_service.calcular_cuenta(pedido, pago.incluir_propina)
    # 3. procesar el pago (polimorfismo)
    metodo = _crear_metodo(pago)
    detalle = metodo.procesar(cuenta["total"])
    # 4. emitir la factura
    factura = Factura(
        pedido_id=pedido.id, mesa_numero=numero_mesa, cajero=ctx.usuario.nombre,
        lineas=[{"producto": i.producto.nombre, "cantidad": i.cantidad, "precio": i.precio_unitario,
                 "subtotal": i.subtotal} for i in pedido.items],
        subtotal=cuenta["subtotal"], descuentos=cuenta["promociones"], impuesto=cuenta["impuesto"],
        propina=cuenta["propina"], total=cuenta["total"], metodo_pago=metodo.nombre, detalle_pago=detalle)
    ctx.repos.facturas.agregar(factura)
    # 5. cerrar pedido y liberar mesa
    pedido.estado = EstadoPedido.FACTURADO
    mesa.liberar()
    # 6. imprimir ticket en segundo plano y notificar
    ctx.impresora.imprimir(factura)
    ctx.bus.publicar(ev.FACTURA_EMITIDA, factura)
    ctx.bus.publicar(ev.MESA_CAMBIADA, mesa)
    return factura


@registrar
@requiere_rol(Rol.CAJERO)
def cerrar_caja(efectivo_contado: float | None = None) -> dict:
    """Flujo imperativo de cierre de caja, paso a paso."""
    # Paso 1: validar
    exigir("cerrar_caja", {"caja_abierta": _caja["abierta"],
                           "mesas_con_pedido": pedido_service.mesas_con_pedido()})

    # Paso 2: recolectar facturas del turno
    facturas = ctx.repos.facturas.desde(_caja["apertura"])

    # Paso 3: acumular totales con un ciclo (estilo imperativo)
    totales_metodo = {"Efectivo": 0.0, "Tarjeta": 0.0, "Nequi": 0.0}
    total_ventas = 0.0
    total_impuesto = 0.0
    total_propinas = 0.0
    total_descuentos = 0.0
    for f in facturas:
        totales_metodo[f.metodo_pago] += f.total
        total_ventas += f.total
        total_impuesto += f.impuesto
        total_propinas += f.propina
        total_descuentos += f.total_descuentos

    # Paso 4: movimientos manuales
    ingresos = 0.0
    egresos = 0.0
    for m in _caja["movimientos"]:
        if m["tipo"] == "ingreso":
            ingresos += m["monto"]
        else:
            egresos += m["monto"]

    # Paso 5: cuadre de efectivo
    efectivo_esperado = _caja["monto_inicial"] + totales_metodo["Efectivo"] + ingresos - egresos
    if efectivo_contado is None:
        efectivo_contado = efectivo_esperado
    diferencia = efectivo_contado - efectivo_esperado

    # Paso 6: armar resumen
    cierre = datetime.now()
    resumen = {
        "negocio": settings.NOMBRE_NEGOCIO, "cajero": _caja["cajero"],
        "apertura": _caja["apertura"], "cierre": cierre,
        "monto_inicial": _caja["monto_inicial"], "num_facturas": len(facturas),
        "total_ventas": round(total_ventas, 2), "total_impuesto": round(total_impuesto, 2),
        "total_propinas": round(total_propinas, 2), "total_descuentos": round(total_descuentos, 2),
        "por_metodo": totales_metodo, "ingresos": ingresos, "egresos": egresos,
        "efectivo_esperado": round(efectivo_esperado, 2), "efectivo_contado": round(efectivo_contado, 2),
        "diferencia": round(diferencia, 2),
        "top_productos": reporte_service.top_productos(facturas, 5),
    }

    # Paso 7: exportar
    settings.DIR_REPORTES.mkdir(parents=True, exist_ok=True)
    sello = cierre.strftime("%Y%m%d_%H%M%S")
    resumen["archivo_excel"] = str(excel.exportar_cierre_excel(
        resumen, facturas, settings.DIR_REPORTES / f"cierre_{sello}.xlsx"))
    resumen["archivo_pdf"] = str(pdf.exportar_cierre_pdf(
        resumen, facturas, settings.DIR_REPORTES / f"cierre_{sello}.pdf"))

    # Paso 8: reiniciar estado de la caja
    _caja["abierta"] = False
    _caja["apertura"] = None
    _caja["monto_inicial"] = 0.0
    _caja["cajero"] = None
    _caja["movimientos"] = []
    _historial_cierres.append(resumen)

    # Paso 9: notificar
    ctx.bus.publicar(ev.CAJA_CERRADA, resumen)
    return resumen
