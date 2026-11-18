"""Paradigma funcional: funciones de orden superior (decoradores) para registro y permisos."""
import functools
import logging
import time

from src.domain.entities import Rol


class PermisoDenegado(Exception):
    pass


def registrar(func):
    """Registra en el log cada llamada, su duración y si falló."""
    log = logging.getLogger(func.__module__.split(".")[-1])

    @functools.wraps(func)
    def envoltura(*args, **kwargs):
        inicio = time.perf_counter()
        try:
            resultado = func(*args, **kwargs)
            log.info("%s OK (%.1f ms)", func.__name__, (time.perf_counter() - inicio) * 1000)
            return resultado
        except Exception as e:
            log.warning("%s FALLÓ: %s", func.__name__, e)
            raise

    return envoltura


def requiere_rol(*roles: Rol):
    """Solo permite ejecutar la función si el usuario en sesión tiene alguno de los roles
    (el ADMIN siempre tiene permiso)."""

    def decorador(func):
        @functools.wraps(func)
        def envoltura(*args, **kwargs):
            from src.application.contexto import ctx
            if ctx.usuario is None:
                raise PermisoDenegado("Debe iniciar sesión")
            if not ctx.usuario.tiene_rol(*roles):
                permitidos = ", ".join(r.value for r in roles)
                raise PermisoDenegado(f"'{ctx.usuario.usuario}' no tiene permiso ({permitidos})")
            return func(*args, **kwargs)

        return envoltura

    return decorador
