"""Métodos de pago (POO: clase abstracta + polimorfismo en procesar())."""
import random
from abc import ABC, abstractmethod


class PagoRechazado(Exception):
    pass


class MetodoPago(ABC):
    nombre: str = "Genérico"

    @abstractmethod
    def procesar(self, monto: float) -> dict:
        """Procesa el pago y devuelve el detalle del comprobante."""

    def __str__(self) -> str:
        return self.nombre


class Efectivo(MetodoPago):
    nombre = "Efectivo"

    def __init__(self, recibido: float):
        self.recibido = float(recibido)

    def procesar(self, monto: float) -> dict:
        if self.recibido < monto:
            raise PagoRechazado(f"Efectivo insuficiente: faltan ${monto - self.recibido:,.0f}")
        return {"recibido": self.recibido, "cambio": round(self.recibido - monto, 2)}


class Tarjeta(MetodoPago):
    nombre = "Tarjeta"

    def __init__(self, numero: str, franquicia: str = "Visa"):
        digitos = "".join(c for c in numero if c.isdigit())
        if len(digitos) < 4:
            raise PagoRechazado("Número de tarjeta inválido")
        self._ultimos4 = digitos[-4:]
        self.franquicia = franquicia

    def procesar(self, monto: float) -> dict:
        autorizacion = f"{random.randint(0, 999999):06d}"
        return {"franquicia": self.franquicia, "tarjeta": f"**** {self._ultimos4}",
                "autorizacion": autorizacion}


class Nequi(MetodoPago):
    nombre = "Nequi"

    def __init__(self, celular: str):
        digitos = "".join(c for c in celular if c.isdigit())
        if len(digitos) != 10 or not digitos.startswith("3"):
            raise PagoRechazado("Celular Nequi inválido (10 dígitos, inicia en 3)")
        self.celular = digitos

    def procesar(self, monto: float) -> dict:
        referencia = f"NQ{random.randint(10**7, 10**8 - 1)}"
        return {"celular": f"{self.celular[:3]}***{self.celular[-4:]}", "referencia": referencia}
