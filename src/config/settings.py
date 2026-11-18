"""Configuración global del POS (valores constantes)."""
from pathlib import Path

NOMBRE_NEGOCIO = "Bar Gascón"
NIT = "900.123.456-7"

TASA_IMPOCONSUMO = 0.08      # Impuesto al consumo en Colombia para bares/restaurantes
PROPINA_SUGERIDA = 0.10      # 10 % voluntaria

HAPPY_HOUR_INICIO = 17       # 5:00 p.m.
HAPPY_HOUR_FIN = 19          # 7:00 p.m.
DESCUENTO_HAPPY_HOUR = 0.30  # 30 % en cócteles
DESCUENTO_COMBO = 0.15       # 15 % hamburguesa + cerveza
MONTO_DESCUENTO_ALTO = 200_000
DESCUENTO_MONTO_ALTO = 0.05

NUMERO_MESAS = 12

RAIZ = Path(__file__).resolve().parents[2]
DIR_SALIDAS = RAIZ / "salidas"
DIR_COMANDAS = DIR_SALIDAS / "comandas"
DIR_TICKETS = DIR_SALIDAS / "tickets"
DIR_REPORTES = DIR_SALIDAS / "reportes"
DIR_RESPALDOS = DIR_SALIDAS / "respaldos"
ARCHIVO_QSS = RAIZ / "src" / "presentation" / "estilos" / "tema.qss"

INTERVALO_RESPALDO_SEG = 60
INTERVALO_DASHBOARD_SEG = 5
