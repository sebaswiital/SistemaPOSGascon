"""Paradigma imperativo: carga inicial de la carta, mesas y usuarios EN MEMORIA.

Se ejecuta en cada arranque (no hay base de datos). También se puede correr suelto:
    python -m scripts.seed_db
"""
from src.config import settings
from src.domain.entities import Bebida, Coctel, Empleado, Mesa, Plato, Rol

PLATOS = [
    # nombre, precio, minutos, categoría, stock
    ("Hamburguesa Gascón", 28000, 15, "Comida", 30),
    ("Hamburguesa BBQ", 30000, 15, "Comida", 25),
    ("Alitas picantes x8", 24000, 18, "Comida", 20),
    ("Nachos con queso", 19000, 8, "Picadas", 25),
    ("Papas rústicas", 12000, 10, "Picadas", 40),
    ("Picada para compartir", 48000, 20, "Picadas", 12),
    ("Empanadas x4", 10000, 6, "Picadas", 6),
]

BEBIDAS = [
    # nombre, precio, ml, alcohólica, categoría, stock
    ("Club Colombia", 8000, 330, True, "Cervezas", 80),
    ("Poker", 6500, 330, True, "Cervezas", 80),
    ("Corona", 11000, 355, True, "Cervezas", 48),
    ("Cerveza artesanal IPA", 14000, 330, True, "Cervezas", 4),
    ("Gaseosa", 5000, 400, False, "Sin alcohol", 60),
    ("Limonada de coco", 9000, 450, False, "Sin alcohol", 30),
    ("Agua", 4000, 600, False, "Sin alcohol", 50),
]

COCTELES = [
    # nombre, precio, ingredientes, stock
    ("Mojito", 22000, ["ron blanco", "hierbabuena", "limón", "soda"], 40),
    ("Margarita", 24000, ["tequila", "triple sec", "limón"], 40),
    ("Piña colada", 23000, ["ron", "crema de coco", "piña"], 30),
    ("Gin tonic", 26000, ["ginebra", "tónica", "pepino"], 35),
    ("Aguardiente sour", 20000, ["aguardiente", "limón", "clara de huevo"], 25),
]

EMPLEADOS = [
    # usuario, nombre, pin, rol
    ("admin", "Administrador", "1234", Rol.ADMIN),
    ("mesero", "Camila Mesera", "1111", Rol.MESERO),
    ("cajero", "Andrés Cajero", "2222", Rol.CAJERO),
]


def seed(repos) -> None:
    print("[seed] Cargando carta...")
    for nombre, precio, minutos, categoria, stock in PLATOS:
        repos.productos.agregar(Plato(nombre, precio, tiempo_preparacion_min=minutos, categoria=categoria,
                                      stock=stock, stock_minimo=5))
    for nombre, precio, ml, alcoholica, categoria, stock in BEBIDAS:
        repos.productos.agregar(Bebida(nombre, precio, mililitros=ml, alcoholica=alcoholica,
                                       categoria=categoria, stock=stock, stock_minimo=6))
    for nombre, precio, ingredientes, stock in COCTELES:
        repos.productos.agregar(Coctel(nombre, precio, ingredientes=ingredientes, stock=stock, stock_minimo=5))

    print(f"[seed] Creando {settings.NUMERO_MESAS} mesas...")
    numero = 1
    while numero <= settings.NUMERO_MESAS:
        capacidad = 6 if numero % 4 == 0 else (2 if numero % 3 == 0 else 4)
        repos.mesas.agregar(Mesa(numero, capacidad))
        numero += 1

    print("[seed] Creando usuarios...")
    for i, (usuario, nombre, pin, rol) in enumerate(EMPLEADOS, start=1):
        repos.empleados.agregar(Empleado(i, nombre, usuario, pin, rol))

    print(f"[seed] Listo: {len(repos.productos)} productos, {len(repos.mesas)} mesas, "
          f"{len(repos.empleados)} usuarios.")


if __name__ == "__main__":
    from src.infraestructure.database.repositorios import Repositorios

    seed(Repositorios())
