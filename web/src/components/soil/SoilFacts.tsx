import type { components } from "@/api/schema";
import { SOIL_ESTIMATE } from "@/features/diagnosis/signals";

type MunicipalitySoil = components["schemas"]["MunicipalitySoil"];
type SoilRange = components["schemas"]["SoilRange"];

const NUMBER = new Intl.NumberFormat("es-CO", { maximumFractionDigits: 1 });

/** «5,7 · entre 4,1 y 7,9»: el valor central y el rango probable (p05–p95) de un mapa de 250 m (R10). */
export function rangeText(range: SoilRange, unit = ""): string | null {
  const suffix = unit ? ` ${unit}` : "";
  const parts: string[] = [];
  if (range.value !== null) parts.push(`${NUMBER.format(range.value)}${suffix}`);
  if (range.p05 !== null && range.p95 !== null) parts.push(`entre ${NUMBER.format(range.p05)} y ${NUMBER.format(range.p95)}${suffix}`);
  return parts.length ? parts.join(" · ") : null;
}

interface Fact {
  label: string;
  value: string | null;
  meaning: string;
}

/** Lo que dice cada dato del suelo, en palabras sencillas (HU-185). Sin dato, «Sin dato»: no se inventa (R1). */
export function soilFacts(soil: MunicipalitySoil): Fact[] {
  return [
    {
      label: "pH",
      value: rangeText(soil.ph),
      meaning: "Qué tan ácido es el suelo. Cada cultivo aguanta un rango de pH; fuera de él crece mal.",
    },
    {
      label: "Carbono orgánico",
      value: rangeText(soil.soc_g_kg, "g/kg"),
      meaning: "La materia orgánica del suelo. Con poca, convienen los abonos verdes, el descanso y los cultivos que dejan residuos.",
    },
    {
      label: "Textura",
      value: soil.texture_class,
      meaning: "Cuánta arena, limo y arcilla tiene. Cambia cuánta agua guarda el suelo entre lluvias, y por eso entra en la señal de agua.",
    },
  ];
}

/**
 * El suelo estimado de la zona, explicado (HU-185): pH, carbono orgánico y textura, con su rango y qué significan, y el
 * rótulo de que es una estimación de 250 m, no una medición del lote (R10). Lo usan el detalle del lote (HU-169) y,
 * después, la señal de suelo y la salud del suelo de las estrategias.
 */
export function SoilFacts({ soil, place }: { soil: MunicipalitySoil; place: string }) {
  return (
    <div className="flex flex-col gap-3">
      <dl className="flex flex-col gap-3">
        {soilFacts(soil).map((fact) => (
          <div key={fact.label} className="flex min-w-0 flex-col gap-0.5">
            <dt className="text-[14px] font-bold text-texto-secundario">{fact.label}</dt>
            <dd className="font-bold">{fact.value ?? "Sin dato"}</dd>
            <dd className="text-[14px] text-texto-secundario">{fact.meaning}</dd>
          </div>
        ))}
      </dl>
      <p className="border-l-4 border-paleta-calabaza bg-superficie-panel-suave px-3 py-2 text-[14px]">
        Es el suelo de {place}, no una medición de su lote. {SOIL_ESTIMATE}
      </p>
      {soil.quality === "partial" && (
        <p className="text-[14px] text-texto-secundario">Parte de la zona no tiene dato en el mapa: la estimación es menos segura.</p>
      )}
    </div>
  );
}
