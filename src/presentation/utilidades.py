from PySide6.QtWidgets import QFrame, QLabel, QMessageBox, QVBoxLayout, QWidget

from src.application.esquemas import mensaje_error
from src.application.calculos.funciones_puras import formato_moneda  # noqa: F401  (reexport)


def ejecutar(padre: QWidget, accion, *args, **kwargs):
    """Ejecuta una acción de servicio mostrando cualquier error como diálogo."""
    try:
        return accion(*args, **kwargs)
    except Exception as e:  # ValidationError, ReglaNegocioViolada, PermisoDenegado, PagoRechazado...
        QMessageBox.warning(padre, "No se pudo completar", mensaje_error(e))
        return None


def refrescar_estilo(widget: QWidget) -> None:
    """Reaplica el QSS cuando cambia una propiedad dinámica usada en selectores."""
    widget.style().unpolish(widget)
    widget.style().polish(widget)


class Tarjeta(QFrame):
    """Tarjeta KPI: título pequeño + valor grande."""

    def __init__(self, titulo: str, valor: str = "-"):
        super().__init__()
        self.setObjectName("tarjeta")
        capa = QVBoxLayout(self)
        self.titulo = QLabel(titulo)
        self.titulo.setObjectName("tarjetaTitulo")
        self.valor = QLabel(valor)
        self.valor.setObjectName("tarjetaValor")
        capa.addWidget(self.titulo)
        capa.addWidget(self.valor)

    def poner(self, valor: str) -> None:
        self.valor.setText(valor)
