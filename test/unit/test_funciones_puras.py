import unittest

from src.application.calculos import funciones_puras as fp


class TestFuncionesPuras(unittest.TestCase):
    def test_subtotal(self):
        self.assertEqual(fp.subtotal([(1000, 2), (500, 3)]), 3500)
        self.assertEqual(fp.subtotal([]), 0)

    def test_descuento_impuesto_propina(self):
        self.assertEqual(fp.aplicar_descuento(10000, 0.3), 7000)
        self.assertEqual(fp.aplicar_descuento(10000, 2), 0)  # se limita a 100 %
        self.assertEqual(fp.calcular_impuesto(10000, 0.08), 800)
        self.assertEqual(fp.calcular_propina(10000), 1000)

    def test_total_factura(self):
        t = fp.total_factura(((10000, 2),), (("promo", 2000),), 0.08, 0.10)
        self.assertEqual(t, {"subtotal": 20000, "descuentos": 2000, "base": 18000, "impuesto": 1440,
                             "propina": 1800, "total": 21240})

    def test_es_pura_no_modifica_entrada(self):
        lineas = ((1000, 1),)
        fp.total_factura(lineas, (), 0.08, 0.1)
        self.assertEqual(lineas, ((1000, 1),))


if __name__ == "__main__":
    unittest.main()
