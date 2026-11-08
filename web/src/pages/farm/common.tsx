import type { ReactNode } from "react";
import type { Choice } from "@/components/ui/ChoiceGroup";
import type { Municipality } from "@/features/farm/lots";

/** «¿Este lote tiene riego?» (`irrigated`): sí, no, o nulo si todavía no lo sabe (HU-164). */
export const IRRIGATION: Choice<boolean | null>[] = [
  { value: true, label: "Sí" },
  { value: false, label: "No" },
  { value: null, label: "Todavía no sé" },
];

export const IRRIGATION_HINT =
  "Con riego, la falta de lluvia no se cuenta como riesgo: le mostramos cuánto riego haría falta. Puede cambiarlo después.";

export const irrigationText = (irrigated: boolean | null | undefined) =>
  irrigated === true ? "Con riego" : irrigated === false ? "Sin riego" : "Riego: todavía no lo ha dicho";

export const AREA_HINT = "En hectáreas. Una hectárea son 10.000 m².";
export const AREA_ERROR = "Escriba el área en hectáreas, mayor que cero (por ejemplo, 2,5).";
export const NAME_ERROR = "Escriba un nombre para el lote.";

/** «Samacá, Boyacá». Sin catálogo, el código: nunca se inventa un nombre. */
export const placeName = (municipality: Municipality | undefined, id: string) =>
  municipality ? `${municipality.name}, ${municipality.department}` : `Municipio ${id}`;

/** El rótulo pequeño en mayúsculas que va sobre los títulos («MI FINCA»). */
export function Eyebrow({ children }: { children: ReactNode }) {
  return <p className="text-[15px] font-bold tracking-wide text-texto-secundario uppercase">{children}</p>;
}

/** Lo que cambia sin dibujo, dicho antes de guardar y en el lote (Figma: «Lote sin dibujar / Área a mano»). */
export function WithoutDrawing({ place }: { place: string }) {
  return (
    <div className="border-2 border-oscuro-cielo/60 bg-[#E6F0F5] px-4 py-3 text-[14px] leading-snug">
      <p className="font-bold">Sin dibujo, su lote queda sin ubicación:</p>
      <ul className="flex list-['·_'] flex-col pl-3">
        <li>No sale en el mapa de su finca.</li>
        <li>El suelo y la altitud son los de {place}, no los de su lote.</li>
      </ul>
      <p className="font-bold">Puede dibujarlo después, cuando quiera.</p>
    </div>
  );
}

/** «Área calculada con su dibujo» (Figma: «Dibuje su lote»). Es la del navegador; la que se guarda la calcula la API. */
export function DrawnArea({ ha, m2 }: { ha: string; m2: string }) {
  return (
    <div className="border-[2.5px] border-paleta-calabaza bg-[#FFF1DF] px-5 py-3">
      <p className="text-[15px] font-bold text-oscuro-calabaza">Área calculada con su dibujo</p>
      <p className="flex flex-wrap items-baseline justify-between gap-x-4">
        <span className="font-titulos text-[30px] leading-tight font-semibold">{ha}</span>
        <span className="text-texto-secundario">{m2}</span>
      </p>
    </div>
  );
}

/** El dibujo se sale del municipio (Figma: «se sale del municipio»). No se puede guardar así. */
export function OutsideWarning({ place }: { place: string }) {
  return (
    <div role="alert" className="border-2 border-oscuro-rojo bg-[#F9E3DF] px-4 py-3 text-[15px] leading-snug">
      <p className="font-bold text-oscuro-rojo">
        <span aria-hidden="true">▲ </span>Su lote se sale de {place}
      </p>
      <p>Mueva los puntos dentro de la línea punteada morada.</p>
    </div>
  );
}

/** Los pasos para dibujar, con el rombo del kit. */
export function DrawSteps({ steps }: { steps: string[] }) {
  return (
    <ol className="flex flex-col gap-1.5">
      {steps.map((step) => (
        <li key={step} className="flex items-center gap-3">
          <svg aria-hidden="true" viewBox="0 0 20 20" className="size-4 shrink-0">
            <polygon points="10,1 19,10 10,19 1,10" fill="var(--color-accion-primaria)" />
          </svg>
          {step}
        </li>
      ))}
    </ol>
  );
}
