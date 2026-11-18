import unittest
from datetime import datetime

from src.domain.entities import Bebida, Coctel, Mesa, Pedido, Plato
from src.domain.pagos.metodos_pago import Efectivo, Nequi, PagoRechazado, Tarjeta
from src.domain.reglas.motor_promociones import MotorPromociones
from src.domain.reglas.reglas_negocio import ReglaNegocioViolada, exigir, nivel_alerta

TARDE = datetime(2026, 1, 1, 18, 0)   # dentro del happy hour
NOCHE = datetime(2026, 1, 1, 22, 0)


def pedido_con(*productos_cantidad):
    p = Pedido(1, "test")
    for prod, cant in productos_cantidad:
        p.agregar(prod, cant)
    return p


class TestMotorPromociones(unittest.TestCase):
    def setUp(self):
        self.motor = MotorPromociones()
        self.hamb = Plato("Hamburguesa X", 20000)
        self.cerveza = Bebida("Pilsen", 5000, categoria="Cervezas")
        self.mojito = Coctel("Mojito", 10000)

    def test_happy_hour_cocteles_y_2x1(self):
        p = pedido_con((self.mojito, 2), (self.cerveza, 3))
        promos = dict(self.motor.evaluar(p, TARDE))
        self.assertEqual(promos["Happy Hour: 30% en cócteles"], 6000)
        self.assertEqual(promos["Happy Hour: 2x1 en cervezas"], 5000)

    def test_sin_happy_hour_en_la_noche(self):
        p = pedido_con((self.mojito, 2))
        self.assertEqual(self.motor.evaluar(p, NOCHE), [])

    def test_combo(self):
        p = pedido_con((self.hamb, 2), (self.cerveza, 1))
        self.assertEqual(self.motor.evaluar(p, NOCHE), [("Combo hamburguesa + cerveza (15%)", 3750)])

    def test_encadenamiento_monto_alto(self):
        p = pedido_con((Plato("Picada", 100000), 3))
        self.assertEqual(self.motor.evaluar(p, NOCHE), [("Cliente frecuente: 5% por consumo alto", 15000)])


class TestReglasNegocio(unittest.TestCase):
    def test_no_facturar_con_caja_cerrada(self):
        p = pedido_con((Plato("A", 1000), 1))
        with self.assertRaises(ReglaNegocioViolada):
            exigir("facturar", {"caja_abierta": False, "pedido": p})

    def test_alertas_inventario(self):
        self.assertEqual(nivel_alerta(Plato("A", 1, stock=0, stock_minimo=6)), "AGOTADO")
        self.assertEqual(nivel_alerta(Plato("A", 1, stock=2, stock_minimo=6)), "CRÍTICO")
        self.assertEqual(nivel_alerta(Plato("A", 1, stock=5, stock_minimo=6)), "BAJO")
        self.assertIsNone(nivel_alerta(Plato("A", 1, stock=50, stock_minimo=6)))

    def test_stock_insuficiente(self):
        with self.assertRaises(ValueError):
            pedido_con((Plato("A", 1000, stock=1), 2))


class TestPagos(unittest.TestCase):
    def test_polimorfismo(self):
        self.assertEqual(Efectivo(50000).procesar(42000)["cambio"], 8000)
        self.assertEqual(Tarjeta("4111 1111 1111 1234").procesar(1)["tarjeta"], "**** 1234")
        self.assertIn("referencia", Nequi("3001234567").procesar(1))
        with self.assertRaises(PagoRechazado):
            Efectivo(1000).procesar(5000)
        with self.assertRaises(PagoRechazado):
            Nequi("12345")

    def test_mesa(self):
        m = Mesa(1)
        m.ocupar(pedido_con((Plato("A", 1000), 1)))
        m.solicitar_cuenta()
        self.assertEqual(m.estado.value, "por_cobrar")


if __name__ == "__main__":
    unittest.main()
