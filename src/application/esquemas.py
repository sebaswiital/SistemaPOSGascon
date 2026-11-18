"""Paradigma declarativo: modelos Pydantic que *declaran* las reglas de validación de los datos
de entrada; Pydantic se encarga de cómo validarlos."""
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class LoginIn(BaseModel):
    usuario: str = Field(min_length=3, max_length=30)
    pin: str = Field(pattern=r"^\d{4}$", description="PIN de 4 dígitos")

    @field_validator("usuario")
    @classmethod
    def normalizar(cls, v: str) -> str:
        return v.strip().lower()


class ProductoIn(BaseModel):
    tipo: Literal["Plato", "Bebida", "Coctel"]
    nombre: str = Field(min_length=2, max_length=60)
    precio: float = Field(gt=0, le=1_000_000)
    stock: int = Field(ge=0, default=50)
    stock_minimo: int = Field(ge=0, default=5)
    categoria: str | None = None


class ItemPedidoIn(BaseModel):
    producto_id: int = Field(gt=0)
    cantidad: int = Field(gt=0, le=50)
    nota: str = Field(default="", max_length=100)


class AjusteStockIn(BaseModel):
    producto_id: int = Field(gt=0)
    cantidad: int = Field(gt=0, le=10_000)


class AperturaCajaIn(BaseModel):
    monto_inicial: float = Field(ge=0, le=10_000_000)


class PagoIn(BaseModel):
    metodo: Literal["Efectivo", "Tarjeta", "Nequi"]
    incluir_propina: bool = True
    recibido: float | None = Field(default=None, ge=0)
    numero_tarjeta: str | None = None
    franquicia: str = "Visa"
    celular: str | None = None

    @model_validator(mode="after")
    def datos_segun_metodo(self):
        if self.metodo == "Efectivo" and self.recibido is None:
            raise ValueError("Indique el efectivo recibido")
        if self.metodo == "Tarjeta" and not self.numero_tarjeta:
            raise ValueError("Indique el número de tarjeta")
        if self.metodo == "Nequi" and not self.celular:
            raise ValueError("Indique el celular Nequi")
        return self


def mensaje_error(exc: Exception) -> str:
    """Convierte un ValidationError de Pydantic en texto legible."""
    errores = getattr(exc, "errors", None)
    if callable(errores):
        return "\n".join(f"{'.'.join(map(str, e['loc'])) or 'datos'}: {e['msg']}" for e in errores())
    return str(exc)
