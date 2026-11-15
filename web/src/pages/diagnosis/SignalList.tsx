import { t } from "@/lib/i18n";
import { useTranslation } from "react-i18next";
import type { ReactNode } from "react";
import { SoilDetails, type SoilContext } from "@/components/soil/SoilDetails";
import { EstimateLabel } from "@/components/ui/Labels";
import { Plate } from "@/components/ui/Plate";
import { signalTone } from "@/components/ui/SignalCard";
import { SignalIcon } from "@/components/ui/SignalIcon";
import { StatusIcon, TONE_STYLE } from "@/components/ui/StatusMark";
import { countsAlways, notCounted } from "@/features/diagnosis/lights";
import {
  SIGNAL_NAME,
  formatValue,
  indicatorName,
  irrigationNote,
  isGrave,
  isP0,
  orderedSignals,
  sourceName,
  sourceNote,
  supplyNote,
  type PriceHistory as PriceHistoryData,
  type Signal,
  type SourceValue,
  type SupplySemester,
} from "@/features/diagnosis/signals";
import type { Version } from "@/features/version";

export interface SignalListProps {
  signals: Record<string, Signal> | null | undefined;
  /** La señal que más limita la ventana con las prioridades de quien consulta (`overall.limiting_signal`). */
  limiting: string | null | undefined;
  irrigated: boolean | null | undefined;
  /** Los pesos con que se calculó la luz de quien consulta (`weights`), para «Cuenta siempre: riesgo grave» (HU-203). */
  weights?: Partial<Record<string, number>> | null;
  supplySemester: SupplySemester | null | undefined;
  soilContext: SoilContext;
  version: Version | undefined;
  /** La gráfica de la lluvia de la ventana año por año, dentro de la señal de agua (HU-093). */
  waterChart?: ReactNode;
}

/**
 * Las señales de la ventana (HU-092): las seis del P0 en su orden y las del P1 solo si vienen. Cada una con su estado en
 * forma y texto, su calificación de 0 a 100 (sin barra si no la tiene, R1), sus razones y, cuando trae varias fuentes,
 * todas juntas con la que calculó la señal marcada (R8). Nunca un valor combinado.
 */
export function SignalList({ signals, limiting, irrigated, weights, supplySemester, soilContext, version, waterChart }: SignalListProps) {
  useTranslation();
  const list = orderedSignals(signals);
  if (list.length === 0) return null;
  return (
    <ul className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-3" aria-label={t("pages.diagnosis.SignalList.windowSignals")}>
      {list.map(([key, signal]) => (
        <SignalItem key={key} id={key} signal={signal} limiting={key === limiting} always={countsAlways(key, signal, weights)}>
          {key === "water" && <Note>{irrigationNote(irrigated)}</Note>}
          {/* Con riego, la señal dice cuánto riego haría falta: es un resultado de riego y lleva su rótulo (R10). */}
          {key === "water" && irrigated === true && <EstimateLabel />}
          {key === "supply" && <Note>{supplyNote(supplySemester)}</Note>}
          {key === "soil" && <SoilDetails {...soilContext} />}
          {signal.reasons.length > 0 && (
            <ul className="relative flex list-disc flex-col gap-1 pl-5">
              {signal.reasons.map((reason) => (
                <li lang="es" key={reason}>
                  {reason}
                </li>
              ))}
            </ul>
          )}
          {key === "market" && signal.price_history && <PriceHistory history={signal.price_history} version={version} />}
          {key === "water" && waterChart}
          {signal.sources && signal.sources.length > 0 && <Sources sources={signal.sources} version={version} />}
        </SignalItem>
      ))}
    </ul>
  );
}

function SignalItem({
  id,
  signal,
  limiting,
  always,
  children,
}: {
  id: string;
  signal: Signal;
  limiting: boolean;
  always: boolean;
  children: ReactNode;
}) {
  useTranslation();
  const name = SIGNAL_NAME()[id] ?? id;
  const headingId = `senal-${id}`;
  return (
    <li className="relative flex min-w-0 flex-col gap-3 px-5 pt-5 pb-6" data-signal={id}>
      <Plate
        c={14}
        fill="var(--color-superficie-panel)"
        stroke={limiting ? "var(--color-paleta-calabaza)" : "var(--color-superficie-borde)"}
        strokeWidth={limiting ? 3 : 2}
      />
      <div className="relative flex min-w-0 items-center gap-3">
        {isP0(id) && <SignalIcon signal={id} />}
        <h3 id={headingId} className="min-w-0 text-[clamp(1.1rem,2.5vw,1.3rem)]">
          {name}
        </h3>
      </div>
      {limiting && <LimitingTag />}
      {notCounted(signal) && <CountTag kind="not_counted" />}
      {always && <CountTag kind="always" />}
      <StatusBadge signal={signal} grave={isGrave(id, signal)} />
      {/* «Sin calificar» (decisión 17) no tiene calificación: ni barra ni número, aunque llegara uno. */}
      {signal.level != null && <Score score={signal.score} />}
      {children}
    </li>
  );
}

/** «Lo que más limita», con forma (un banderín) y texto, no solo con el borde de color. */
function LimitingTag() {
  useTranslation();
  return (
    <p className="relative inline-flex w-fit items-center gap-2 font-bold text-oscuro-calabaza">
      <svg aria-hidden="true" viewBox="0 0 20 22" className="size-5 shrink-0">
        <polygon points="3,1 5,1 5,21 3,21" fill="var(--color-paleta-noche)" />
        <polygon points="5,2 18,6 5,11" fill="var(--color-paleta-calabaza)" />
      </svg>
      {t("pages.diagnosis.SignalList.mostLimitingFactor")}
    </p>
  );
}

/**
 * Si la señal cuenta para la luz con las prioridades de quien consulta (HU-203), con forma y texto: un anillo vacío
 * para «No cuenta» (la señal se sigue viendo) y un rombo lleno para el riesgo grave de clima que cuenta aunque su peso
 * sea 0 (R2).
 */
function CountTag({ kind }: { kind: "not_counted" | "always" }) {
  useTranslation();
  const always = kind === "always";
  return (
    <p
      className={`relative inline-flex w-fit items-center gap-2 text-[15px] font-bold ${always ? "text-oscuro-rojo" : "text-texto-secundario"}`}
    >
      <svg aria-hidden="true" viewBox="0 0 16 16" className="size-4 shrink-0">
        {always ? (
          <polygon points="8,1 15,8 8,15 1,8" fill="var(--color-oscuro-rojo)" />
        ) : (
          <circle cx="8" cy="8" r="6" fill="none" stroke="currentColor" strokeWidth="2" />
        )}
      </svg>
      {always ? t("pages.diagnosis.SignalList.alwaysCountsSevereRisk") : t("pages.diagnosis.SignalList.doesNotAffectTheLightWithYour")}
    </p>
  );
}

/**
 * El estado con silueta, ícono y texto (W2): «Desfavorable» es un cuadrado; «Datos insuficientes», una línea punteada
 * con «?»; «No aplica», un guion; «Sin calificar», tres barras sobre un borde liso, sin colores del semáforo.
 */
function StatusBadge({ signal, grave }: { signal: Signal; grave: boolean }) {
  useTranslation();
  const { tone, label } = signalTone({ ...signal, level: signal.level ?? null });
  const style = TONE_STYLE[tone];
  return (
    <span
      data-tone={tone}
      className={`relative inline-flex min-h-12 w-fit max-w-full items-center gap-2.5 px-5 py-2 font-bold ${style.ink}`}
    >
      <Plate {...style.plate} c={Math.min(style.plate.c ?? 10, 10)} />
      <span className="relative flex items-center gap-2.5">
        <StatusIcon icon={style.icon} />
        {grave ? t("pages.diagnosis.SignalList.severeRisk", { v0: label }) : label}
      </span>
    </span>
  );
}

/** La calificación de 0 a 100 junto al nivel. Sin calificación no se dibuja nada: una barra en cero diría «muy mal» (R1). */
function Score({ score }: { score: number | null | undefined }) {
  useTranslation();
  if (score === null || score === undefined) return null;
  const value = Math.max(0, Math.min(100, score));
  return (
    <div className="relative flex flex-col gap-1.5">
      <p>
        {t("pages.diagnosis.SignalList.score")} <span className="font-bold">{Math.round(value)}</span>{" "}
        {t("pages.diagnosis.SignalList.outOf100")}
      </p>
      <div aria-hidden="true" className="h-3 w-full overflow-hidden bg-superficie-panel-suave">
        <div className="h-full bg-oscuro-oliva" style={{ width: `${value}%` }} />
      </div>
    </div>
  );
}

/**
 * De dónde sale la historia del precio del mercado (HU-073, decisión 17): la central (y si es la de ese cultivo), el
 * periodo y la fuente, nombrada como las demás (`GET /version`). Lo que dice la historia (los años por encima y por
 * debajo, y que no es un pronóstico) ya está en las razones: no se repite. Sin colores del semáforo: no califica.
 */
export function PriceHistory({ history, version }: { history: PriceHistoryData; version: Version | undefined }) {
  useTranslation();
  const period =
    history.first_year !== null && history.last_year !== null
      ? history.first_year === history.last_year
        ? `${history.first_year}`
        : `${history.first_year}–${history.last_year}`
      : null;
  const note = sourceNote(history.source_id);
  return (
    <div
      data-price-history
      className="relative flex min-w-0 flex-col gap-1 border-l-4 border-superficie-borde py-1 pl-3 text-[15px] leading-snug"
    >
      <p className="font-bold">{t("priceHistory.title")}</p>
      <p>
        {t("priceHistory.market", { market: history.market })}
        {history.market_basis === "crop_override" && t("priceHistory.override")}
      </p>
      {period && <p>{t("priceHistory.period", { period })}</p>}
      <p className="text-texto-secundario">{t("priceHistory.source", { source: sourceName(history.source_id, version) })}</p>
      {note && <p className="text-texto-secundario">{note}</p>}
    </div>
  );
}

function Note({ children }: { children: ReactNode }) {
  return <p className="relative text-[15px] leading-snug text-texto-secundario">{children}</p>;
}

/**
 * Todas las fuentes de un indicador juntas, cada una con su valor, su origen y su fecha, y cuál calculó la señal (R8).
 * Nunca se mezclan ni se promedian.
 */
function Sources({ sources, version }: { sources: SourceValue[]; version: Version | undefined }) {
  useTranslation();
  return (
    <div className="relative flex flex-col gap-2">
      <p className="text-[15px] font-bold">{t("pages.diagnosis.SignalList.whatEachSourceSays")}</p>
      <ul className="flex flex-col gap-2">
        {sources.map((source) => {
          const note = sourceNote(source.source_id);
          return (
            <li
              key={`${source.source_id}-${source.indicator}`}
              className={`flex min-w-0 flex-col gap-0.5 border-l-4 py-1 pl-3 text-[15px] leading-snug ${
                source.used ? "border-oscuro-oliva" : "border-superficie-borde"
              }`}
            >
              <UsedTag used={source.used} />
              <p>
                <span className="font-bold">{indicatorName(source.indicator)}:</span> {formatValue(source.value, source.unit)}
                {source.preliminary ? t("data.preliminary") : ""}
              </p>
              <p className="text-texto-secundario">
                {sourceName(source.source_id, version)} ·{" "}
                {source.period
                  ? t("pages.diagnosis.SignalList.period", { v0: source.period })
                  : t("pages.diagnosis.SignalList.periodNotReported")}
              </p>
              {note && <p className="text-texto-secundario">{note}</p>}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

/** «Usada para la luz» (rombo lleno) o «Para contrastar» (rombo vacío): forma y texto. */
function UsedTag({ used }: { used: boolean }) {
  useTranslation();
  return (
    <span className="inline-flex items-center gap-2 font-bold">
      <svg aria-hidden="true" viewBox="0 0 14 14" className="size-3.5 shrink-0">
        <polygon
          points="7,1 13,7 7,13 1,7"
          fill={used ? "var(--color-oscuro-oliva)" : "none"}
          stroke="var(--color-oscuro-oliva)"
          strokeWidth="2"
        />
      </svg>
      {used ? t("pages.diagnosis.SignalList.usedForTheLight") : t("pages.diagnosis.SignalList.forComparison")}
    </span>
  );
}
