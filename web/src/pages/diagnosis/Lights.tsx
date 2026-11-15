import { TrafficLightBadge } from "@/components/ui/TrafficLightBadge";
import type { DiagnosisResponse } from "@/features/diagnosis/consult";
import { sameLight, whyDifferent } from "@/features/diagnosis/lights";
import { asWeights } from "@/features/diagnosis/priorities";
import { SIGNAL_NAME } from "@/features/diagnosis/signals";
import { useVersion } from "@/features/version";

type LightResult = DiagnosisResponse["overall"];

/** Lo primero que se lee del resultado: qué hacer (`specs/01-reglas.md`, «Agregación del semáforo»). */
export const ACTION_TEXT: Record<LightResult["action"], string> = {
  sow: "Puede sembrar en esa fecha",
  other_window: "Mejor busque otra fecha de siembra",
  rotate: "Mejor siembre otro cultivo",
  review_data: "Faltan datos para evaluar esa fecha",
};

/**
 * Las luces de una ventana (HU-092, HU-203): la acción primero. Si la luz con sus prioridades y la del criterio de
 * AgroSense coinciden, se ve una sola; si difieren, las dos con su acción y su factor que más limita, la suya primero y
 * más grande, y una línea que dice por qué difieren. La usan el diagnóstico y el ciclo de una estrategia (HU-215).
 */
export function DiagnosisLights({
  overall,
  overallDefault,
  weights,
}: {
  overall: LightResult;
  overallDefault: LightResult;
  weights: DiagnosisResponse["weights"];
}) {
  const version = useVersion();
  const defaults = version.data ? asWeights(version.data.default_weights) : null;
  if (sameLight(overall, overallDefault)) {
    return (
      <>
        <p className="font-titulos text-[clamp(1.4rem,3.5vw,2rem)] leading-tight font-semibold">{ACTION_TEXT[overall.action]}</p>
        <TrafficLightBadge light={overall.light} className="self-start" />
        <LimitingLine signal={overall.limiting_signal} />
        <Reasons reasons={overall.reasons} />
      </>
    );
  }
  return (
    <>
      <LightBlock title="Con sus prioridades" result={overall} primary />
      <LightBlock title="Con el criterio de AgroSense" result={overallDefault} />
      <p className="border-l-4 border-paleta-calabaza pl-3 text-[15px] leading-snug">{whyDifferent(weights, defaults)}</p>
    </>
  );
}

/** Una de las dos luces cuando difieren: de quién es el criterio y su acción, la luz con forma y texto, lo que más la limita y sus razones. */
function LightBlock({ title, result, primary = false }: { title: string; result: LightResult; primary?: boolean }) {
  return (
    <section aria-label={title} className={`flex min-w-0 flex-col gap-2 ${primary ? "" : "border-t-2 border-superficie-borde pt-4"}`}>
      <p
        className={`font-titulos leading-tight font-semibold ${
          primary ? "text-[clamp(1.4rem,3.5vw,2rem)]" : "text-[clamp(1.1rem,2.5vw,1.35rem)]"
        }`}
      >
        {title}: {ACTION_TEXT[result.action]}
      </p>
      <TrafficLightBadge light={result.light} className="self-start" />
      <LimitingLine signal={result.limiting_signal} />
      <Reasons reasons={result.reasons} />
    </section>
  );
}

/** Cada luz dice cuál es su factor que más limita (`specs/05-frontend.md`, «Dos luces»). */
function LimitingLine({ signal }: { signal: string | null | undefined }) {
  if (!signal) return null;
  return (
    <p>
      Lo que más limita: <span className="font-bold">{SIGNAL_NAME[signal] ?? signal}</span>
    </p>
  );
}

function Reasons({ reasons }: { reasons: string[] | null | undefined }) {
  if (!reasons || reasons.length === 0) return null;
  return (
    <ul className="flex list-disc flex-col gap-1 pl-5" aria-label="Por qué esta luz">
      {reasons.map((reason) => (
        <li key={reason}>{reason}</li>
      ))}
    </ul>
  );
}
