"""Curva EcoCrop de calificación 0-100, compartida entre HU-191 (aptitud del cultivo) y HU-196 (calificación de
las seis señales); specs/01-reglas.md, «Aptitud del cultivo en la zona» y «Cómo se califica cada señal».

Califica un valor en una curva con puntos ordenados: 0 en los límites absolutos, 100 en el tramo óptimo,
recta entre medio. El formato de los puntos es el mismo de `backend/config/thresholds.yaml`.
"""

from collections.abc import Sequence

CurvePoint = tuple[float, float]  # (valor, calificación 0-100)


def crop_curve(abs_min: float, opt_min: float, opt_max: float, abs_max: float) -> tuple[CurvePoint, ...]:
    """Curva EcoCrop de un cultivo: 4 puntos (límite absoluto bajo a 0, óptimo bajo a 100, óptimo alto a 100,
    límite absoluto alto a 0)."""
    return (float(abs_min), 0.0), (float(opt_min), 100.0), (float(opt_max), 100.0), (float(abs_max), 0.0)


def score_from_curve(points: Sequence[CurvePoint], value: float) -> float:
    """Califica `value` dentro de una curva de puntos (valor, calificación) ordenados de menor a mayor valor,
    interpolando en línea recta entre puntos consecutivos.

    Fuera de los extremos, la calificación del punto extremo más cercano (no clamp a 0). Si dos puntos
    consecutivos tienen el mismo valor (tramo vertical), devuelve la calificación del ÚLTIMO. El score es
    informativo (R3): nunca lanza excepción por datos de cultivo faltantes, solo por una curva vacía o
    desordenada, que son errores de configuración (R1, R8).
    """
    if not points:
        raise ValueError("La curva no puede estar vacía")

    # Verifica que está ordenada (no decreciente)
    for i in range(len(points) - 1):
        if points[i][0] > points[i + 1][0]:
            raise ValueError("Los puntos de la curva deben estar ordenados de menor a mayor valor")

    # Coincidencia exacta con algún punto: la calificación del ÚLTIMO punto con ese valor
    matching_indices = [i for i, (x, _) in enumerate(points) if x == value]
    if matching_indices:
        return points[matching_indices[-1]][1]

    # Fuera de los extremos: la calificación del punto extremo más cercano
    if value < points[0][0]:
        return points[0][1]
    if value > points[-1][0]:
        return points[-1][1]

    # Interpola linealmente en el intervalo entre dos puntos consecutivos
    for i in range(len(points) - 1):
        x1, y1 = points[i]
        x2, y2 = points[i + 1]
        if x1 < value < x2:
            return y1 + (y2 - y1) * (value - x1) / (x2 - x1)

    # Con la curva ordenada y los casos de arriba, todo value queda cubierto; si llega aquí es un error de datos.
    raise ValueError(f"No se encontró un tramo de la curva para value={value}")
