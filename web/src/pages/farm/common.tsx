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
      <p className="font-bold">Podrá dibujarlo cuando llegue el mapa.</p>
    </div>
  );
}
