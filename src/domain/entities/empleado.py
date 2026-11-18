from enum import Enum


class Rol(str, Enum):
    ADMIN = "admin"
    MESERO = "mesero"
    CAJERO = "cajero"


class Empleado:
    def __init__(self, id: int, nombre: str, usuario: str, pin: str, rol: Rol):
        self.id = id
        self.nombre = nombre
        self.usuario = usuario
        self.__pin = pin  # atributo privado (name mangling)
        self.rol = rol

    def verificar_pin(self, pin: str) -> bool:
        return self.__pin == pin

    def tiene_rol(self, *roles: Rol) -> bool:
        return self.rol == Rol.ADMIN or self.rol in roles

    def a_dict(self) -> dict:
        return {"id": self.id, "nombre": self.nombre, "usuario": self.usuario, "rol": self.rol.value}

    def __repr__(self) -> str:
        return f"<Empleado {self.usuario} ({self.rol.value})>"
