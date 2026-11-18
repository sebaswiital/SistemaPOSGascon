from dataclasses import dataclass, field
from datetime import datetime
from itertools import count

_ids = count(1001)


@dataclass
class Factura:
    pedido_id: int
    mesa_numero: int
    cajero: str
    lineas: list[dict]                 # [{producto, cantidad, precio, subtotal}]
    subtotal: float
    descuentos: list[tuple[str, float]]
    impuesto: float
    propina: float
    total: float
    metodo_pago: str
    detalle_pago: dict
    numero: int = field(default_factory=lambda: next(_ids))
    fecha: datetime = field(default_factory=datetime.now)

    @property
    def id(self) -> int:
        return self.numero

    @property
    def total_descuentos(self) -> float:
        return sum(v for _, v in self.descuentos)

    def a_dict(self) -> dict:
        return {"numero": self.numero, "fecha": self.fecha.isoformat(), "pedido": self.pedido_id,
                "mesa": self.mesa_numero, "cajero": self.cajero, "lineas": self.lineas,
                "subtotal": self.subtotal, "descuentos": self.descuentos, "impuesto": self.impuesto,
                "propina": self.propina, "total": self.total, "metodo_pago": self.metodo_pago,
                "detalle_pago": self.detalle_pago}
