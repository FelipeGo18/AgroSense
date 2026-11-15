import type { components } from "@/api/schema";
import { SOIL_ESTIMATE } from "@/features/diagnosis/signals";

type MunicipalitySoil = components["schemas"]["MunicipalitySoil"];
export type SoilProperties = Pick<MunicipalitySoil, "ph" | "soc_g_kg" | "texture_class" | "quality">;
type SoilRange = components["schemas"]["SoilRange"];

const NUMBER = new Intl.NumberFormat("es-CO", { maximumFractionDigits: 2 });

/**
 * Niveles del carbono orgánico, en g/kg: los de la tabla 3 de Castro Franco (`cevipapa_taller_2005`, p. 35, «Niveles
 * críticos aplicables a suelos paperos del Altiplano Cundiboyacense»: materia orgánica baja < 5 %, media de 5 a 10 % y
 * alta > 10 %), pasados a carbono con el factor 1,724 (`fao_glosolan_wb_2019`). El corte bajo es el mismo de la regla de
 * salud del suelo `materia_organica_ciclos` (`params.soc_low_g_kg` de `catalog/rotation_rules.yaml`): si la regla
 * cambia su corte, cambia aquí, para que la web y las estrategias digan lo mismo.
 */
export const SOC_LOW_G_KG = 29;
export const SOC_HIGH_G_KG = 58;

/**
 * Cuánta agua guarda cada textura, en tres grupos, según el agua disponible de la tabla 2-1 del NRCS (NEH parte 652,
 * cap. 2, `nrcs_neh652_cap2`, la misma que usa el balance hídrico de HU-144): por debajo de 0,10 m³/m³ guarda poca;
 * de 0,10 a 0,14, algo; desde 0,14, bien. Los nombres son los del IGAC que publica `texture_class` (HU-181).
 */
const WATER_BY_TEXTURE: Record<string, "poca" | "algo" | "bien"> = {
  arenoso: "poca",
  "arenoso franco": "poca",
  "franco arenoso": "algo",
  franco: "bien",
  "franco limoso": "bien",
  limoso: "bien",
  "franco arcillo arenoso": "bien",
  "franco arcilloso": "bien",
  "franco arcillo limoso": "bien",
  "arcillo arenoso": "bien",
  "arcillo limoso": "bien",
  arcilloso: "bien",
};
const WATER_TEXT = { poca: "Guarda poca agua", algo: "Guarda algo de agua", bien: "Guarda bien el agua" } as const;

/** «rango probable de 4,7 a 172 g/kg» (p05–p95), o nada si el mapa no trae el rango (R10). */
export function rangeText(range: SoilRange, unit = ""): string | null {
  if (range.p05 === null || range.p95 === null) return null;
  const suffix = unit ? ` ${unit}` : "";
  return `rango probable de ${NUMBER.format(range.p05)} a ${NUMBER.format(range.p95)}${suffix}`;
}

const valueText = (range: SoilRange, unit = "") => (range.value === null ? null : `${NUMBER.format(range.value)}${unit ? ` ${unit}` : ""}`);

export interface SoilFact {
  label: string;
  value: string | null;
  /** Lo que el dato le dice al agricultor en dos o tres palabras; nulo si no hay un corte con fuente para decirlo (R8). */
  level: string | null;
  range: string | null;
  meaning: string;
}

/** Los tres datos del suelo, cada uno con su nivel y su rango (HU-185). Sin dato, «Sin dato»: no se inventa (R1). */
export function soilFacts(soil: SoilProperties): SoilFact[] {
  const soc = soil.soc_g_kg.value;
  const water = soil.texture_class ? WATER_BY_TEXTURE[soil.texture_class] : undefined;
  return [
    {
      label: "Carbono orgánico",
      value: valueText(soil.soc_g_kg, "g/kg"),
      level: soc === null ? null : soc < SOC_LOW_G_KG ? "Bajo" : soc > SOC_HIGH_G_KG ? "Alto" : "Medio",
      range: rangeText(soil.soc_g_kg, "g/kg"),
      meaning: `La materia orgánica del suelo. Por debajo de ${SOC_LOW_G_KG} g/kg es baja, y convienen los abonos verdes, el descanso y los cultivos que dejan residuos.`,
    },
    {
      label: "Textura",
      value: soil.texture_class,
      level: water ? WATER_TEXT[water] : null,
      range: null,
      meaning: "Cuánta arena, limo y arcilla tiene. Cambia cuánta agua guarda el suelo entre lluvias, y por eso entra en la señal de agua.",
    },
    {
      // Sin nivel: las clases de pH (ácido, neutro, alcalino) necesitan su fuente registrada en `sources` (R8).
      label: "pH",
      value: valueText(soil.ph),
      level: null,
      range: rangeText(soil.ph),
      meaning: "Qué tan ácido es el suelo. Cada cultivo aguanta un rango de pH; fuera de él crece mal.",
    },
  ];
}

/**
 * El suelo estimado de la zona, explicado (HU-185): de un vistazo, cada dato con su valor y lo que significa para el
 * agricultor («Medio», «Guarda bien el agua»); el rango probable en letra chica, y la explicación a pedido. Siempre dice
 * que es una estimación de 250 m, no una medición del lote (R10). Lo usan el detalle del lote (HU-169), la señal de suelo
 * y la salud del suelo de las estrategias, con el origen que publicó la API.
 */
export function SoilFacts({ soil, place }: { soil: SoilProperties; place: string }) {
  return (
    <div className="flex flex-col gap-3">
      <dl className="flex flex-col divide-y-2 divide-paleta-niebla">
        {soilFacts(soil).map((fact) => (
          <div key={fact.label} className="flex min-w-0 flex-col gap-1 py-3 first:pt-0">
            <dt className="text-[14px] font-bold text-texto-secundario">{fact.label}</dt>
            <dd className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
              <span className="text-[18px] font-bold">{fact.value ?? "Sin dato"}</span>
              {fact.level && (
                <span className="rounded-sm bg-oliva-claro px-2 py-0.5 text-[14px] font-bold text-oscuro-oliva">{fact.level}</span>
              )}
            </dd>
            {fact.range && <dd className="text-[13px] text-texto-secundario">{fact.range}</dd>}
            <dd>
              <details className="text-[14px]">
                <summary className="inline-flex min-h-11 cursor-pointer items-center font-bold text-oscuro-oliva underline decoration-2 underline-offset-4">
                  ¿Qué es esto?
                </summary>
                <p className="text-texto-secundario">{fact.meaning}</p>
              </details>
            </dd>
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
