"""Contenedor de dependencias de la aplicación (se llena en main.py al arrancar)."""
from dataclasses import dataclass, field

from src.domain.entities import Empleado, Rol
from src.infraestructure.database.repositorios import Repositorios
from src.infraestructure.eventos.bus_eventos import BusEventos, bus


@dataclass
class Contexto:
    repos: Repositorios = field(default_factory=Repositorios)
    bus: BusEventos = bus
    cola_comandas: object = None      # ColaComandas
    impresora: object = None          # ImpresoraTickets
    usuario: Empleado | None = None   # sesión actual
    forzar_happy_hour: bool = False   # para demostraciones fuera del horario

    def rol_actual(self) -> Rol | None:
        return self.usuario.rol if self.usuario else None


ctx = Contexto()
