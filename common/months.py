"""Los nombres de los meses en español, en minúscula y en orden (enero es el índice 0).

Está en `common/` porque los usan el pipeline (las fechas de los boletines de SIPSA) y el motor (las razones de las
señal de heladas) sin importarse. No lee archivos ni importa nada: el motor puede usarlo (R6).
"""

MONTH_NAMES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre")


def month_name(month: int) -> str:
    """El nombre del mes `month` (1 a 12)."""
    return MONTH_NAMES[month - 1]
