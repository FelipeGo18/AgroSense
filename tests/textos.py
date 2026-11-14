"""Comprobaciones de texto que comparten varias pruebas (revisión de Haider del PR #86).

`FORECAST_WORDS`: palabras con que una razón se presentaría como pronóstico («va a», «será», «subirá»…). Venía de
`tests/engine/test_senal_mercado.py` (HU-073); vive aquí para que todas las pruebas usen la misma lista. AgroSense da
historia comparada y riesgo histórico, nunca pronóstico (decisión 4).
"""

import re

FORECAST_WORDS = re.compile(r"\b(va a|irá|subirá|bajará|estará|será|pronostic\w*|predic\w*|futur\w*)\b", re.IGNORECASE)

# Los rótulos que dicen justamente que no es un pronóstico no cuentan como pronóstico.
NOT_A_FORECAST = ("no es un pronóstico", "no un pronóstico")


def speaks_as_forecast(text: str) -> bool:
    """Si el texto se presenta como pronóstico, sin contar los rótulos que dicen que no lo es."""
    clean = text.lower()
    for label in NOT_A_FORECAST:
        clean = clean.replace(label, "")
    return bool(FORECAST_WORDS.search(clean))
