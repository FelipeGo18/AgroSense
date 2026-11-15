"""Lo que un cultivo necesita de agua en una ventana de siembra y la lluvia que cae en ella (FAO-56).

Es la base del balance hídrico (M7): la necesidad es la evapotranspiración del cultivo, ETc = Kc × ET0 (FAO-56,
cap. 6), sumada día por día sobre la ventana. La reutilizan las tendencias (`/trends`, HU-078) y la reutilizará el
déficit de HU-144, para que no haya dos cuentas del agua.

- **El Kc de cada día** sigue la curva de FAO-56 (Allen et al. 1998, *Evapotranspiración del cultivo*, Estudio FAO
  Riego y Drenaje 56, cap. 6, figura 25 y ecuación 66): constante en la etapa inicial y en la media; en la de
  desarrollo, cuyo `kc` es nulo en `crop_stages` por diseño, sube en línea recta del Kc de la inicial al de la media; en
  la final baja en línea recta del Kc de la media al de la etapa final (`kc` de `late` es el Kc al final del ciclo). En
  el día `j` (de 1 a `L`) de una etapa en rampa de `L` días, Kc = Kc_antes + (j / L) × (Kc_después − Kc_antes): el
  último día llega al Kc de destino, como en la ecuación 66.
- **Prorrateo por días:** los datos son totales mensuales. Cada mes que toca la ventana aporta una fracción de su total:
  los días de la ventana que caen en él divididos por los días del mes del que sale el total (`month_days`, el mes
  histórico). La lluvia del mes se multiplica por esa fracción; la ET0 del mes se divide por los días del mes histórico
  y se multiplica por el Kc de cada uno de esos días. Es la misma fracción para la lluvia y para la ETc, así que son
  comparables mes por mes. Sin `month_days`, el mes histórico es el del calendario de la ventana.
- **Febrero bisiesto:** la ventana proyectada son las mismas fechas (mes y día) en el año histórico. Un 29 de febrero
  de la ventana no existe en un año histórico de febrero de 28 días: ese día no aporta lluvia ni necesidad (ni su Kc),
  y la fracción de febrero nunca pasa de 1 (un febrero entero de 29 días sobre uno de 28 vale 28/28, no 29/28). Una
  siembra el 29 de febrero, proyectada a un año no bisiesto, empieza a sumar el 1 de marzo. Al revés, una ventana de
  un año de febrero de 28 días proyectada a uno bisiesto no incluye el 29: su febrero entero vale 28/29.
- **Sin dato no hay cuenta (R1):** si falta la lluvia o la ET0 de algún mes de la ventana, o el Kc con que se arma la
  curva, el total es `None`. Nunca se rellena con cero ni se suma solo lo que hay.

Son funciones puras: reciben la ventana y los totales mensuales ya leídos; no leen archivos, ni el reloj, ni tablas
(R4, R6). Los meses se identifican por `(año, mes)` del calendario de la ventana (`CropWindow.months()`); quien llama
decide de qué año histórico sale cada valor.
"""

from calendar import monthrange
from collections.abc import Mapping, Sequence
from datetime import date

from backend.engine.stages import CropWindow, StageSpan

# La etapa final de FAO-56: su `kc` es el del final del ciclo y se llega a él en rampa desde la etapa anterior.
LATE = "late"

MonthKey = tuple[int, int]


def daily_kc(stages: Sequence[StageSpan]) -> tuple[float, ...] | None:
    """El Kc de cada día del ciclo, en orden, con la curva de FAO-56 (ver el módulo).

    Devuelve `None` si la curva no se puede armar con datos con fuente (R1): una etapa constante sin `kc`, una etapa
    en rampa sin el Kc de la etapa anterior o el de la siguiente, o una etapa final sin su `kc`.
    """
    values: list[float] = []
    previous_end: float | None = None
    for index, span in enumerate(stages):
        if span.stage == LATE:
            start, end = previous_end, span.kc
        elif span.kc is None:
            # El destino es el Kc constante de la etapa siguiente (la media). El `kc` de una etapa final no sirve: es el
            # del final del ciclo, no el del inicio de esa etapa.
            following = stages[index + 1] if index + 1 < len(stages) else None
            start, end = previous_end, following.kc if following is not None and following.stage != LATE else None
        else:
            start = end = span.kc
        if start is None or end is None:
            return None
        values.extend(start + (end - start) * day / span.days for day in range(1, span.days + 1))
        previous_end = end
    return tuple(values)


def _month_days(window: CropWindow, month_days: Mapping[MonthKey, int] | None) -> list[tuple[MonthKey, int, int, int]]:
    """Por cada mes de la ventana: su llave, el índice del primer día de la ventana que cae en él (0 es la siembra),
    cuántos de esos días existen en el mes histórico y cuántos días tiene el mes histórico.

    Los días de la ventana en un mes son seguidos; los que pasan del último día del mes histórico (solo el 29 de
    febrero sobre un febrero de 28) no existen en él y no cuentan (ver el módulo, «Febrero bisiesto»)."""
    result = []
    for month in window.months():
        key = (month.year, month.month)
        first = max(date(month.year, month.month, 1), window.sowing_date)
        length = month_days[key] if month_days is not None else monthrange(month.year, month.month)[1]
        kept = max(0, min(first.day + month.days - 1, length) - first.day + 1)
        result.append((key, (first - window.sowing_date).days, kept, length))
    return result


def window_rain_mm(
    window: CropWindow, rain_mm: Mapping[MonthKey, float | None], month_days: Mapping[MonthKey, int] | None = None
) -> float | None:
    """La lluvia de la ventana: la de cada mes por la fracción de sus días que caen en ella. `None` si falta algún mes."""
    total = 0.0
    for key, _first, days, month_days_of in _month_days(window, month_days):
        value = rain_mm.get(key)
        if value is None:
            return None
        total += value * days / month_days_of
    return total


def window_etc_mm(
    window: CropWindow, et0_mm: Mapping[MonthKey, float | None], month_days: Mapping[MonthKey, int] | None = None
) -> float | None:
    """Lo que el cultivo necesita en la ventana (ETc, FAO-56): Σ por día de Kc del día × ET0 del mes ÷ días del mes.

    `None` si falta la ET0 de algún mes o si la curva de Kc no se puede armar (R1).
    """
    kc = daily_kc([period.span for period in window.periods])
    if kc is None or len(kc) != window.length_days:
        return None
    total = 0.0
    for key, first, days, month_days_of in _month_days(window, month_days):
        value = et0_mm.get(key)
        if value is None:
            return None
        total += value / month_days_of * sum(kc[first : first + days])
    return total


def window_deficit_mm(
    window: CropWindow,
    rain_mm: Mapping[MonthKey, float | None],
    et0_mm: Mapping[MonthKey, float | None],
    month_days: Mapping[MonthKey, int] | None = None,
) -> float | None:
    """Lo que la lluvia no alcanza a cubrir en la ventana, mes a mes y sin el agua que guarda el suelo: Σ por mes de
    max(0, ETc del mes − lluvia del mes), con el mismo prorrateo por días que `window_rain_mm` y `window_etc_mm`. Lo que
    sobra un mes no pasa al siguiente: eso es el agua guardada, que pone el balance de HU-144.

    `None` si falta la lluvia o la ET0 de algún mes, o si la curva de Kc no se puede armar (R1).
    """
    kc = daily_kc([period.span for period in window.periods])
    if kc is None or len(kc) != window.length_days:
        return None
    total = 0.0
    for key, first, days, month_days_of in _month_days(window, month_days):
        rain, et0 = rain_mm.get(key), et0_mm.get(key)
        if rain is None or et0 is None:
            return None
        total += max(0.0, et0 / month_days_of * sum(kc[first : first + days]) - rain * days / month_days_of)
    return total
