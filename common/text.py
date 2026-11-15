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
    return format_decimal(value)


def format_decimal(value: float) -> str:
    """Siempre con un decimal y coma, también si es entero: «5,0», «5,75» → «5,8». Así se escribe el pH en las razones
    de la señal de suelo (HU-183) y en el descarte `soil_ph` de las estrategias."""
    return f"{value:.1f}".replace(".", ",")


def format_precise(value: float) -> str:
    """Con los decimales que tenga, hasta dos, y coma: «5,75», «5,7», «5,0». Para un valor que se compara con un límite
    de un decimal (el pH frente a la ficha): con uno solo, 5,75 se vería igual que un óptimo de 5,8 (PR #129)."""
    rounded = round(value, 2)
    return format_decimal(rounded) if rounded == round(value, 1) else f"{rounded:.2f}".replace(".", ",")


def join(items: Iterable[str]) -> str:
    """«a», «a y b», «a, b y c»."""
    words = list(items)
    return words[0] if len(words) == 1 else f"{', '.join(words[:-1])} y {words[-1]}"


def of(name: str) -> str:
    """«de» delante de un nombre con su artículo, con la contracción del español: «de la papa», «del maíz»."""
    return f"del {name[3:]}" if name.startswith("el ") else f"de {name}"
