"""Cómo se escriben los números y las listas en los textos para el agricultor (razones de la API y del motor).

Está en `common/` porque lo usan la API (la razón de la aptitud, `backend/api/calculations.py`) y el motor (las razones
de heladas y calor, `backend/engine/sensitive_signal.py`), y el motor no importa la API (R6). No lee archivos ni importa
nada: el motor puede usarlo.
"""

from collections.abc import Iterable


def format_number(value: float) -> str:
    """Sin decimales si es entero y, si no, con un decimal y coma: «30», «22,4», «29,96» → «30,0».

    Un valor que no es entero conserva su decimal aunque redondee a entero («30,0»): así lo escribe la razón de la
    aptitud desde HU-191, y sus respuestas no cambian.
    """
    if value == int(value):
        return str(int(value))
    return f"{value:.1f}".replace(".", ",")


def join(items: Iterable[str]) -> str:
    """«a», «a y b», «a, b y c»."""
    words = list(items)
    return words[0] if len(words) == 1 else f"{', '.join(words[:-1])} y {words[-1]}"
