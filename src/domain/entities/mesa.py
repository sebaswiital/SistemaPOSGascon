from enum import Enum


class EstadoMesa(str, Enum):
    LIBRE = "libre"
    OCUPADA = "ocupada"
    POR_COBRAR = "por_cobrar"


class Mesa:
    def __init__(self, numero: int, capacidad: int = 4):
        self.numero = numero
        self.capacidad = capacidad
        self.estado = EstadoMesa.LIBRE
        self.pedido_actual = None  # Pedido | None

    @property
    def id(self) -> int:
        return self.numero

    def ocupar(self, pedido) -> None:
        self.pedido_actual = pedido
        self.estado = EstadoMesa.OCUPADA

    def solicitar_cuenta(self) -> None:
        if self.pedido_actual is None:
            raise ValueError("La mesa no tiene pedido")
        self.estado = EstadoMesa.POR_COBRAR

    def liberar(self) -> None:
        self.pedido_actual = None
        self.estado = EstadoMesa.LIBRE

    def a_dict(self) -> dict:
        return {"numero": self.numero, "capacidad": self.capacidad, "estado": self.estado.value,
                "pedido": self.pedido_actual.id if self.pedido_actual else None}

    def __repr__(self) -> str:
        return f"<Mesa {self.numero} {self.estado.value}>"
