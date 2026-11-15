"""La señal de agua: si la lluvia que suele caer en la ventana, con el agua que guarda el suelo, cubre lo que el cultivo
necesita (HU-071; specs/01-reglas.md, «Señales de una ventana», «Cómo se califica cada señal» y «Agregación del
semáforo»).

- **Qué califica:** el porcentaje de lo que pide el cultivo en la ventana que cubren la lluvia del **año seco** de la
  fuente que dice `catalog/sources.yaml` (`precip_dry_mm`, la que se supera en 4 de cada 5 años) y el agua que retiene
  el suelo según su textura. No la normal: decidido por Felipe el 11 de noviembre de 2026 (las dos fuentes de la NASA
  dan casi el doble de lluvia en los valles del altiplano; PR #44). La curva es la de `thresholds.yaml` (del WRSI de
  FEWS NET) y la calificación, el nivel y si es crítica salen solo de `score_signal` (HU-196).
- **El extremo bajo:** el balance da la cobertura como un rango [mínimo, máximo] (la retención del suelo es un rango).
  Sin riego se califica el extremo **bajo**: la decisión prudente; el rango no compensa su peor caso (R2).
- **Con riego** (`irrigated = true`) la falta de lluvia no es un riesgo: la señal es `favorable`, con la calificación de
  la curva en una cobertura del 100 % (el riego pone lo que falta), nunca crítica, y la razón dice cuánto regar como
  rango en milímetros enteros, con el rótulo de estimación (R10). `irrigated` nulo se evalúa como sin riego; la
  limitación «Sin dato de riego» la pone `/diagnostics` (HU-076), no esta señal.
- **Sin balance** (o sin lo que pide el cultivo, o sin el déficit del año seco): `insufficient_data`, nivel y
  calificación nulos, no crítica, también con riego (sin balance no se puede decir cuánto regar), y la razón va a las
  limitaciones (R1). Sin la textura del suelo el balance va sin retención: la señal se califica igual y lo dice
  `NO_RETENTION` en las limitaciones.
- **La razón sin datos dice la causa real** (R5): si a algún mes de la ventana le falta la lluvia del año seco de la
  fuente que calcula la señal o la ET0, el balance ni se pide y la razón es esa (`missing_data`: «Sin la lluvia de GPM
  IMERG para la zona en …»); «Sin el balance hídrico…» queda solo para cuando esos datos están y falta el balance.
- **El aviso de la fuente** (`rain_caveat` de `catalog/sources.yaml`) va a las limitaciones en toda respuesta, se
  califique o no la señal (como el `frost_caveat` de HU-077).

El balance llega ya hecho (`WaterBalanceSummary`): esta señal no calcula la necesidad del cultivo ni el déficit, para
que no haya dos cuentas del agua (HU-144). Función pura (R6): no lee archivos, ni el dataset, ni la configuración. Es
historia de la zona, nunca un pronóstico (decisión 4).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from backend.engine.sensitive_signal import ClimateSignalResult, insufficient, months_phrase, scored
from backend.engine.signal_score import AVAILABLE, round_half_up, score_signal
from backend.engine.stages import CropWindow, WindowMonth

if TYPE_CHECKING:
    from backend.config.thresholds import Thresholds

WATER = "water"
INDICATOR = "water_deficit_mm"
# Sin la textura del suelo o la raíz del cultivo, el balance de HU-144 va sin el agua que guarda el suelo
# (specs/01-reglas.md, «Cómo se califica cada señal»): la señal se califica igual y se dice. Sin el agua guardada, el
# déficit no es menor que con ella (el suelo solo guarda lo que sobra de un mes para los siguientes), así que el error
# va del lado prudente.
NO_RETENTION = (
    "El agua se calculó sin la que guarda el suelo: puede faltar menos agua de la que se dice. Verifique la humedad del suelo en campo."
)
# La cobertura que deja el riego: pone lo que falta.
IRRIGATED_COVERAGE = 100.0

Range = tuple[float, float]


@dataclass(frozen=True)
class WaterBalanceSummary:
    """Lo que la señal lee del balance hídrico de la ventana (HU-144): lo que pide el cultivo en la ventana (`need_mm`,
    ETc de FAO-56), el déficit del año seco como rango [mínimo, máximo] (`dry_deficit_mm`) y si se tuvo en cuenta el
    agua que guarda el suelo (`retention`). Nulo: sin dato (R1).

    Sale del `WaterBalance` de HU-144 en `window_signals.balance_for`; `covered_pct` es la misma fórmula que
    `WaterBalance.covered_pct`, así que la cuenta no se duplica.
    """

    need_mm: float | None
    dry_deficit_mm: Range | None
    retention: bool

    def covered_pct(self) -> Range | None:
        """Qué porcentaje de lo que necesita el cultivo cubren la lluvia del año seco y el agua guardada, [mínimo,
        máximo], a un decimal y nunca negativo. El mínimo sale del déficit máximo y el máximo, del mínimo. Si el cultivo
        no pide agua en la ventana, (100, 100). Nulo sin lo que pide el cultivo o sin el déficit (R1)."""
        if self.need_mm is None or self.dry_deficit_mm is None:
            return None
        if self.need_mm == 0:
            return (100.0, 100.0)
        deficit_min, deficit_max = self.dry_deficit_mm
        low = round(max(0.0, 100 * (1 - deficit_max / self.need_mm)), 1)
        high = round(max(0.0, 100 * (1 - deficit_min / self.need_mm)), 1)
        return (low, high)


@dataclass(frozen=True)
class RainSource:
    """La fuente de la lluvia que calcula la señal, como se dice en la razón («GPM IMERG»), los años de su periodo
    normal (del que sale el año seco) y su aviso fijo (`rain_caveat`), si lo tiene."""

    name: str
    first_year: int | None
    last_year: int | None
    caveat: str | None


def in_months(months: Sequence[WindowMonth]) -> str:
    """«en septiembre», «en octubre y diciembre» o «de agosto a noviembre» (sin «en» delante de un tramo)."""
    phrase = months_phrase(months)
    return phrase if phrase.startswith("de ") else f"en {phrase}"


def missing_data(rain: RainSource, no_rain: Sequence[WindowMonth], no_et0: Sequence[WindowMonth]) -> tuple[str, ...]:
    """Por qué no se puede pedir el balance de la ventana: los meses sin la lluvia del año seco de la fuente que calcula
    la señal (`no_rain`) y los meses sin la ET0 (`no_et0`), en orden cronológico. Vacío si no falta nada. Nunca se usa
    la fuente de contraste en lugar de la que falta (R1)."""
    notes = []
    if no_rain:
        notes.append(
            f"Sin la lluvia de {rain.name} para la zona {in_months(no_rain)}: el agua no se evalúa, y no se usa otra fuente en su lugar"
        )
    if no_et0:
        notes.append(f"Sin la evapotranspiración de referencia de la zona {in_months(no_et0)}: el agua no se evalúa")
    return tuple(notes)


def water_signal(
    balance: WaterBalanceSummary | None,
    irrigated: bool | None,
    rain: RainSource,
    window: CropWindow | None,
    thresholds: Thresholds,
    crop_name: str,
    missing: Sequence[str] = (),
) -> ClimateSignalResult:
    """La señal `water` de la ventana. `balance` nulo: sin balance hídrico. `irrigated` nulo se evalúa como sin riego.
    `window` nula (un cultivo sin etapas) no tiene meses que nombrar: sin datos. `crop_name` lleva su artículo («la
    papa»). `missing` son los datos que le faltan al balance (`missing_data`): con alguno, la señal es sin datos y la
    primera es su razón, aunque llegue un balance."""
    notices = (rain.caveat,) if rain.caveat else ()
    if missing:
        return insufficient(missing[0], (*missing[1:], *notices))
    covered = None if balance is None else balance.covered_pct()
    if covered is None or window is None:
        return insufficient(f"Sin el balance hídrico de {crop_name} en esta ventana: el agua no se evalúa", notices)
    if rain.first_year is None or rain.last_year is None:
        # Sin el periodo no se puede decir de qué años es la lluvia del año seco (R5): no se califica.
        return insufficient(f"Sin el periodo de la lluvia de {rain.name}: el agua no se evalúa", notices)
    limitations = (() if balance.retention else (NO_RETENTION,)) + notices
    # Con riego, la cobertura es la del riego (pone lo que falta); sin riego (o sin dato de riego), el extremo bajo de
    # la cobertura del balance: la decisión prudente.
    score = score_signal(WATER, IRRIGATED_COVERAGE if irrigated else covered[0], thresholds)
    if score.status != AVAILABLE:
        # Una curva de `water` nula en `thresholds.yaml` (sin fuente para sus cortes): no se califica (R1, R8).
        return insufficient(f"Sin una curva con fuente para calificar el agua de {crop_name}: el agua no se evalúa", limitations)
    when = in_months(window.months())
    # El año seco de cada mes, sumado: un poco más seco que el año seco de la ventana (va del lado prudente, PR #115).
    dry_year = (
        "En un año seco, si cada mes llueve como en sus años secos (menos que en 4 de cada 5), "
        f"con la lluvia de {rain.name} de {rain.first_year} a {rain.last_year}"
    )
    covers = "la lluvia y el agua que guarda el suelo cubren" if balance.retention else "la lluvia cubre"
    estimate = "Es una estimación con el clima de la zona, no una medición de su lote: verifique la humedad del suelo en campo"
    if irrigated:
        low_mm, high_mm = (round_half_up(value) for value in balance.dry_deficit_mm)
        if high_mm == 0:
            need = f"{covers} lo que necesita {crop_name} {when}: no haría falta regar"
        else:
            amount = f"unos {low_mm} mm" if low_mm == high_mm else f"de {low_mm} a {high_mm} mm"
            need = f"haría falta regar {amount} para cubrir lo que necesita {crop_name} {when}"
        reason = f"Con riego, la falta de lluvia no es un riesgo. {dry_year}, {need}. {estimate}"
        return scored(score, INDICATOR, reason, limitations)
    low_pct, high_pct = (round_half_up(value) for value in covered)
    share = f"el {low_pct} %" if low_pct == high_pct else f"de {low_pct} % a {high_pct} %"
    reason = f"{dry_year}, {covers} {share} de lo que necesita {crop_name} {when}. {estimate}"
    return scored(score, INDICATOR, reason, limitations)
