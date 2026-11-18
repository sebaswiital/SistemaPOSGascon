from src.application.contexto import ctx
from src.application.decoradores import registrar
from src.application.esquemas import LoginIn
from src.domain.entities import Empleado
from src.infraestructure.eventos import bus_eventos as ev


class CredencialesInvalidas(Exception):
    pass


@registrar
def iniciar_sesion(usuario: str, pin: str) -> Empleado:
    datos = LoginIn(usuario=usuario, pin=pin)
    empleado = ctx.repos.empleados.por_usuario(datos.usuario)
    if empleado is None or not empleado.verificar_pin(datos.pin):
        raise CredencialesInvalidas("Usuario o PIN incorrectos")
    ctx.usuario = empleado
    ctx.bus.publicar(ev.SESION_INICIADA, empleado)
    return empleado


def cerrar_sesion() -> None:
    ctx.usuario = None
