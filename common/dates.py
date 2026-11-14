"""Aritmética de meses del calendario, sin día (HU-192).

Está en `common/` porque la usan la API (el rango de fechas de siembra aceptadas, contrato, «Fechas») y el motor (las
ventanas por mes y los meses que toca una ventana) sin importarse: el motor no puede importar `backend/api/` (R6). Es
una función pura: no lee el reloj ni archivos.
"""


def add_months(year: int, month: int, offset: int) -> tuple[int, int]:
    """Avanza (año, mes) por `offset` meses (puede ser negativo) y devuelve el (año, mes) de destino, con el mes de 1
    a 12. No decide el día: cada quien pone el suyo (el 1 del mes, o el mismo día recortado al último del mes)."""
    total = year * 12 + (month - 1) + offset
    return total // 12, total % 12 + 1
