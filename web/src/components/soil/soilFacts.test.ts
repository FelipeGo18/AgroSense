import { describe, expect, it } from "vitest";
import type { components } from "@/api/schema";
import { SOC_HIGH_G_KG, SOC_LOW_G_KG, soilFacts } from "./SoilFacts";

type Soil = components["schemas"]["MunicipalitySoil"];

// Suelo DE EJEMPLO (R5).
const SOIL: Soil = {
  municipality_id: "15646",
  ph: { value: 5.7, p05: 4.13, p95: 7.88 },
  soc_g_kg: { value: 52.37, p05: 4.67, p95: 172.03 },
  nitrogen_g_kg: 4.1,
  clay_pct: 31.6,
  sand_pct: 37.1,
  silt_pct: 31.6,
  texture_class: "franco arcilloso",
  slope_pct: 19.8,
  cells: 2041,
  quality: "ok",
  source_id: "soilgrids",
  versions: { dataset: "ejemplo", rules: "ejemplo" },
};
const fact = (soil: Soil, label: string) => soilFacts(soil).find((f) => f.label === label)!;

describe("Los datos del suelo explicados (HU-185)", () => {
  it("el carbono sigue los niveles de CEVIPAPA: bajo bajo 29 g/kg (el corte de la regla), medio hasta 58 y alto después", () => {
    expect([SOC_LOW_G_KG, SOC_HIGH_G_KG]).toEqual([29, 58]);
    const level = (value: number) => fact({ ...SOIL, soc_g_kg: { value, p05: 10, p95: 90 } }, "Carbono orgánico").level;
    expect(level(28.9)).toBe("Bajo");
    expect(level(29)).toBe("Medio");
    expect(level(58)).toBe("Medio");
    expect(level(58.1)).toBe("Alto");
  });

  it("la textura dice cuánta agua guarda", () => {
    expect(fact(SOIL, "Carbono orgánico").level).toBe("Medio");
    expect(fact(SOIL, "Textura").level).toBe("Guarda bien el agua");
    expect(fact({ ...SOIL, texture_class: "arenoso franco" }, "Textura").level).toBe("Guarda poca agua");
    expect(fact({ ...SOIL, texture_class: "franco arenoso" }, "Textura").level).toBe("Guarda algo de agua");
  });

  it("el pH no tiene nivel: sus clases necesitan una fuente registrada (R8)", () => {
    expect(fact(SOIL, "pH").level).toBeNull();
  });

  it("sin dato no se inventa nada (R1)", () => {
    const empty = { ...SOIL, soc_g_kg: { value: null, p05: null, p95: null }, texture_class: null };
    expect(fact(empty, "Carbono orgánico")).toMatchObject({ value: null, level: null, range: null });
    expect(fact(empty, "Textura")).toMatchObject({ value: null, level: null });
  });
});
