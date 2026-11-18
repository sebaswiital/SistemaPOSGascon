"""Repositorio genérico EN MEMORIA (sin base de datos: los datos viven mientras la app está abierta).

Las consultas son declarativas: se describe *qué* se quiere (criterios) y no *cómo* recorrer."""
import threading
from typing import Callable, Generic, Iterable, TypeVar

T = TypeVar("T")


class RepositorioBase(Generic[T]):
    def __init__(self):
        self._datos: dict[int, T] = {}
        self._lock = threading.RLock()

    def agregar(self, entidad: T) -> T:
        with self._lock:
            self._datos[entidad.id] = entidad
        return entidad

    def agregar_varios(self, entidades: Iterable[T]) -> None:
        for e in entidades:
            self.agregar(e)

    def obtener(self, id: int) -> T | None:
        return self._datos.get(id)

    def eliminar(self, id: int) -> None:
        with self._lock:
            self._datos.pop(id, None)

    def todos(self) -> list[T]:
        with self._lock:
            return list(self._datos.values())

    def buscar(self, filtro: Callable[[T], bool] | None = None, orden: Callable[[T], object] | None = None,
               **criterios) -> list[T]:
        """buscar(categoria="Cócteles", orden=lambda p: p.precio)  ≈  SELECT ... WHERE ... ORDER BY"""
        resultado = [e for e in self.todos()
                     if all(getattr(e, campo) == valor for campo, valor in criterios.items())
                     and (filtro is None or filtro(e))]
        return sorted(resultado, key=orden) if orden else resultado

    def primero(self, **criterios) -> T | None:
        return next(iter(self.buscar(**criterios)), None)

    def contar(self, **criterios) -> int:
        return len(self.buscar(**criterios))

    def __len__(self) -> int:
        return len(self._datos)
