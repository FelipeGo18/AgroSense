import { render, screen, within } from "@testing-library/react";
import { RouterProvider, createMemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { PATHS } from "@/app/paths";
import { routes } from "@/app/routes";
import { sowingMonths } from "@/features/diagnosis/consult";
import {
  formatValue,
  harvestNote,
  irrigationNote,
  isGrave,
  orderedSignals,
  phRange,
  sourceName,
  supplyNote,
  type MunicipalitySoil,
  type Signal,
} from "@/features/diagnosis/signals";
import type { Version } from "@/features/version";
import { setLightMode } from "@/lib/lightMode";

// Datos de ejemplo de las pruebas (R5): una respuesta como la del contrato, con cifras de muestra. Como en los ejemplos
// simulados, los campos nulos no vienen (`level` y `score` de una señal sin datos).
const MONTH = sowingMonths()[0].value;
const MUNICIPALITIES = [{ municipality_id: "15646", name: "Samacá", department: "Boyacá", lat: 5.49, lon: -73.49 }];
const CROPS = [{ crop_id: "papa", name_es: "Papa", kind: "crop", archetype: "tuber", family: "solanaceae", cycle_months: 5.4 }];
const signal = (extra: Partial<Signal>): Partial<Signal> => ({ critical: false, counts: true, indicators: [], reasons: [], ...extra });
const SIGNALS = {
  water: signal({
    status: "available",
    level: "favorable",
    score: 86,
    reasons: ["En 7 de los últimos 10 años la lluvia cubrió lo que necesita la papa"],
    sources: [
      { source_id: "imerg", indicator: "precip_mm", value: 410, unit: "mm", period: "2015-2024", used: true },
      { source_id: "nasa_power", indicator: "precip_mm", value: 380, unit: "mm", period: "2015-2024", used: false },
      { source_id: "nasa_power", indicator: "soil_wetness_root", value: 0.61, unit: "fracción", used: false },
    ],
  }),
  frost: signal({ status: "available", level: "moderate", score: 58, reasons: ["Heló en el llenado 12 de cada 100 años"] }),
  heat: signal({ status: "not_applicable", reasons: ["Ninguna etapa de este cultivo es sensible al calor"] }),
  soil: signal({ status: "available", level: "favorable", score: 80, reasons: ["pH dentro del rango de la papa"] }),
  supply: signal({
    status: "available",
    level: "unfavorable",
    critical: true,
    score: 22,
    sources: [{ source_id: "eva", indicator: "planted_change_pct", value: 35, unit: "%", period: "2025-B", preliminary: true, used: true }],
  }),
  market: signal({ status: "insufficient_data", reasons: ["Sin datos de mercado para la zona"] }),
};
const RESPONSE = {
  request: { municipality_id: "15646", crop_id: "papa", sowing_date: `${MONTH}-01`, irrigated: false, lot_id: null },
  suitability: { level: "suitable", score: 92, basis: "municipality", reasons: [] },
  window: {
    sowing_start: `${MONTH}-01`,
    harvest_estimate: `${MONTH}-28`,
    harvest_basis: "calendar",
    supply_semester: { year: 2025, semester: "B", preliminary: true },
  },
  overall: {
    light: "red",
    action: "rotate",
    high_risk: false,
    weights_basis: "default",
    limiting_signal: "frost",
    reasons: ["La oferta desfavorable y grave pone la luz en rojo"],
  },
  overall_default: { light: "red", action: "rotate", high_risk: false, weights_basis: "default", limiting_signal: "frost", reasons: [] },
  weights: { water: 3, frost: 3, heat: 3, soil: 3, supply: 3, market: 3 },
  signals: SIGNALS,
  limitations: ["Datos EVA del último año son preliminares", "Suelo estimado para el municipio, no para su lote"],
  versions: { dataset: "2026.11.0", rules: "1.0.0" },
};
const SOIL: MunicipalitySoil = {
  municipality_id: "15646",
  ph: { value: 5.5, p05: 5.2, p95: 5.8 },
  soc_g_kg: { value: 30, p05: 20, p95: 40 },
  nitrogen_g_kg: null,
  clay_pct: null,
  sand_pct: null,
  silt_pct: null,
  texture_class: null,
  slope_pct: null,
  cells: 120,
  quality: "ok",
  source_id: "soilgrids",
  versions: { dataset: "2026.11.0", rules: "1.0.0" },
};
const VERSION = {
  dataset_version: "2026.11.0",
  rules_version: "1.0.0",
  created_at: null,
  region: "co-boyaca-cundinamarca",
  default_weights: {},
  weights_version: "1",
  weights_reasons: {},
  sources: [{ source_id: "imerg", name: "GPM IMERG Final, lluvia mensual", institution: "NASA" }],
};

type Reply = { status: number; body?: unknown };
function fakeApi(replies: Record<string, Reply>) {
  vi.stubGlobal("fetch", async (url: string, init: RequestInit = {}) => {
    const reply = replies[`${init.method ?? "GET"} ${url}`] ?? { status: 401, body: { error: { code: "unauthorized", message: "No." } } };
    return new Response(reply.body === undefined ? null : JSON.stringify(reply.body), { status: reply.status });
  });
}
function replies(response: unknown = RESPONSE) {
  return {
    "GET /api/v1/catalogs/municipalities": { status: 200, body: MUNICIPALITIES },
    "GET /api/v1/catalogs/crops": { status: 200, body: CROPS },
    "GET /api/v1/catalogs/municipalities/15646/soil": { status: 200, body: SOIL },
    "GET /api/v1/version": { status: 200, body: VERSION },
    "POST /api/v1/diagnostics": { status: 200, body: response },
  };
}
const open = () =>
  render(
    <RouterProvider
      router={createMemoryRouter(routes, { initialEntries: [`${PATHS.diagnosis}?municipio=15646&cultivo=papa&siembra=${MONTH}&riego=no`] })}
    />,
  );
const card = (name: string) => screen.getByRole("heading", { level: 3, name }).closest("li") as HTMLElement;

afterEach(() => {
  vi.unstubAllGlobals();
  setLightMode(false);
});

describe("Las señales (HU-092)", () => {
  it("van en su orden, y una sin datos no se lee como calificación 0 (R1)", () => {
    const list = orderedSignals({ market: SIGNALS.market, water: SIGNALS.water, heat: SIGNALS.heat } as Record<string, Signal>);
    expect(list.map(([key]) => key)).toEqual(["water", "heat", "market"]);
    const market = list[2][1];
    expect(market.level).toBeNull();
    expect(market.score).toBeNull();
  });

  it("las del P1 solo aparecen si vienen", () => {
    const withP1 = { ...SIGNALS, excess_rain: signal({ status: "available", level: "favorable", score: 90 }) } as Record<string, Signal>;
    expect(orderedSignals(withP1).map(([key]) => key)).toEqual(["water", "frost", "heat", "soil", "supply", "market", "excess_rain"]);
    expect(orderedSignals(SIGNALS as Record<string, Signal>)).toHaveLength(6);
  });

  it("dicen el riego, el dato de EVA, el rango del suelo y el valor de cada fuente sin inventar nada", () => {
    expect(irrigationNote(true)).toMatch(/con riego/);
    expect(irrigationNote(false)).toBe("Evaluada sin riego.");
    expect(irrigationNote(null)).toMatch(/no dijo si tiene riego/);
    expect(supplyNote({ year: 2025, semester: "A", preliminary: false })).toBe("Dato de EVA de 2025, semestre A.");
    expect(supplyNote(null)).toMatch(/Sin dato de EVA/);
    expect(phRange(SOIL)).toBe("pH estimado de 5,2 a 5,8 (valor central 5,5)");
    expect(phRange({ ...SOIL, ph: { value: 5.5, p05: null, p95: null } })).toBeNull();
    expect(formatValue(null, "mm")).toBe("Sin dato");
    expect(formatValue(0.61, "fracción")).toBe("0,61 fracción");
    expect(sourceName("imerg", VERSION as Version)).toBe("GPM IMERG Final, lluvia mensual (NASA)");
    expect(sourceName("nasa_power", undefined)).toBe("NASA POWER");
    expect(sourceName("otra_fuente", undefined)).toBe("otra_fuente");
  });
});

describe("Reglas que la pantalla no puede romper (HU-092)", () => {
  it("el rótulo de la cosecha dice cómo se estimó: por calendario en el MVP, con un año normal en el P1 (R5)", () => {
    expect(harvestNote("calendar")).toBe("Cosecha estimada con la duración de las etapas del cultivo. No es pronóstico.");
    expect(harvestNote("normal_year")).toBe("Estimación con un año normal, no es pronóstico.");
  });

  it("el suelo, las enfermedades y el clima de la cosecha nunca se anuncian como riesgo grave", () => {
    const grave = { ...SIGNALS.supply, critical: true, level: "unfavorable" } as Signal;
    expect(isGrave("supply", grave)).toBe(true);
    expect(isGrave("frost", grave)).toBe(true);
    expect(isGrave("soil", grave)).toBe(false);
    expect(isGrave("disease", grave)).toBe(false);
    expect(isGrave("harvest_weather", grave)).toBe(false);
    expect(isGrave("supply", { ...grave, level: "moderate" })).toBe(false);
  });
});

describe("Resultado del diagnóstico (HU-092)", () => {
  it("la acción sugerida es lo primero que se lee, antes de la luz y de sus razones", async () => {
    fakeApi(replies());
    open();
    const action = await screen.findByText("Mejor siembre otro cultivo");
    const light = screen.getByText("Luz roja");
    expect(action.compareDocumentPosition(light) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(screen.getByText("La oferta desfavorable y grave pone la luz en rojo")).toBeInTheDocument();
    expect(screen.getByText("Cosecha estimada con la duración de las etapas del cultivo. No es pronóstico.")).toBeInTheDocument();
  });

  it("muestra las seis señales; desfavorable, datos insuficientes y no aplica se distinguen con forma y texto", async () => {
    fakeApi(replies());
    open();
    await screen.findByRole("heading", { level: 2, name: "Las señales de esta ventana" });
    const names = within(screen.getByRole("list", { name: "Señales de la ventana" }))
      .getAllByRole("heading", { level: 3 })
      .map((h) => h.textContent);
    expect(names).toEqual(["Agua", "Heladas", "Calor", "Suelo", "Oferta", "Mercado"]);

    const tone = (name: string) => card(name).querySelector("[data-tone]");
    expect(tone("Oferta")).toHaveAttribute("data-tone", "red");
    expect(tone("Oferta")).toHaveTextContent("Desfavorable · riesgo grave");
    expect(tone("Mercado")).toHaveAttribute("data-tone", "insufficient_data");
    expect(tone("Mercado")).toHaveTextContent("Datos insuficientes");
    expect(tone("Calor")).toHaveAttribute("data-tone", "not_applicable");
    expect(tone("Calor")).toHaveTextContent("No aplica");
  });

  it("cada señal con calificación la muestra junto al nivel; sin calificación no hay barra en cero (R1)", async () => {
    fakeApi(replies());
    open();
    await screen.findByRole("heading", { level: 2, name: "Las señales de esta ventana" });
    expect(within(card("Agua")).getByText(/Calificación:/)).toHaveTextContent("Calificación: 86 de 100");
    expect(within(card("Oferta")).getByText(/Calificación:/)).toHaveTextContent("Calificación: 22 de 100");
    expect(within(card("Mercado")).queryByText(/Calificación/)).not.toBeInTheDocument();
    expect(within(card("Calor")).queryByText(/Calificación/)).not.toBeInTheDocument();
  });

  it("marca «Lo que más limita» solo en la señal que más limita", async () => {
    fakeApi(replies());
    open();
    await screen.findByRole("heading", { level: 2, name: "Las señales de esta ventana" });
    expect(within(card("Heladas")).getByText("Lo que más limita")).toBeInTheDocument();
    expect(screen.getAllByText("Lo que más limita")).toHaveLength(1);
  });

  it("el agua dice con qué riego se evaluó y la oferta de qué año y semestre de EVA es su dato", async () => {
    fakeApi(replies());
    open();
    await screen.findByRole("heading", { level: 2, name: "Las señales de esta ventana" });
    expect(within(card("Agua")).getByText("Evaluada sin riego.")).toBeInTheDocument();
    expect(within(card("Oferta")).getByText("Dato de EVA de 2025, semestre B, preliminar.")).toBeInTheDocument();
  });

  it("las fuentes de un indicador van juntas, con su valor, su origen y su fecha, y se marca la que calculó la señal (R8)", async () => {
    fakeApi(replies());
    open();
    await screen.findByRole("heading", { level: 2, name: "Las señales de esta ventana" });
    const water = within(card("Agua"));
    expect(water.getAllByText("Usada para la luz")).toHaveLength(1);
    expect(water.getAllByText("Para contrastar")).toHaveLength(2);
    // El nombre sale de `GET /version` (la tabla `sources`), que llega un momento después.
    expect(await water.findByText(/GPM IMERG Final, lluvia mensual \(NASA\) · periodo 2015-2024/)).toBeInTheDocument();
    expect(water.getAllByText(/NASA POWER · periodo/)).toHaveLength(2);
    // POWER es un reanálisis y la humedad del suelo es de la zona: se dice siempre.
    expect(water.getAllByText(/Reanálisis: un modelo con observaciones/)).toHaveLength(2);
    // Cada fuente con su valor: nunca uno combinado.
    expect(water.getByText("410 mm")).toBeInTheDocument();
    expect(water.getByText("380 mm")).toBeInTheDocument();
    expect(water.queryByText("395 mm")).not.toBeInTheDocument();
  });

  it("el suelo lleva su rango y el rótulo de estimación (R10)", async () => {
    fakeApi(replies());
    open();
    expect(
      await within(await screen.findByText("Suelo").then((h) => h.closest("li") as HTMLElement)).findByText(
        "pH estimado de 5,2 a 5,8 (valor central 5,5), en el municipio.",
      ),
    ).toBeInTheDocument();
    expect(within(card("Suelo")).getByText(/Estimación de un mapa global de 250 m/)).toBeInTheDocument();
  });

  it("con riego, el agua lleva el rótulo de estimación del riego (R10); sin riego, no", async () => {
    fakeApi(replies({ ...RESPONSE, request: { ...RESPONSE.request, irrigated: true } }));
    open();
    await screen.findByRole("heading", { level: 2, name: "Las señales de esta ventana" });
    expect(within(card("Agua")).getByText(/Evaluada con riego/)).toBeInTheDocument();
    expect(
      within(card("Agua")).getByText("Estimación con el clima de la zona. Verifique la humedad del suelo en su lote"),
    ).toBeInTheDocument();
  });

  it("sin riego, el agua no lleva el rótulo del riego", async () => {
    fakeApi(replies());
    open();
    await screen.findByRole("heading", { level: 2, name: "Las señales de esta ventana" });
    expect(within(card("Agua")).queryByText(/Verifique la humedad del suelo/)).not.toBeInTheDocument();
  });

  it("un suelo marcado como crítico por error no se muestra como riesgo grave", async () => {
    fakeApi(replies({ ...RESPONSE, signals: { ...SIGNALS, soil: { ...SIGNALS.soil, level: "unfavorable", critical: true, score: 10 } } }));
    open();
    await screen.findByRole("heading", { level: 2, name: "Las señales de esta ventana" });
    expect(card("Suelo").querySelector("[data-tone]")).toHaveTextContent("Desfavorable");
    expect(card("Suelo").querySelector("[data-tone]")).not.toHaveTextContent("riesgo grave");
  });

  it("muestra las limitaciones del resultado", async () => {
    fakeApi(replies());
    open();
    const section = await screen.findByRole("heading", { level: 2, name: "Limitaciones de este resultado" });
    const list = within(section.parentElement as HTMLElement);
    expect(list.getByText("Datos EVA del último año son preliminares")).toBeInTheDocument();
    expect(list.getByText("Suelo estimado para el municipio, no para su lote")).toBeInTheDocument();
  });

  it("«no evaluable» se dice con forma y texto, distinto de una luz roja", async () => {
    fakeApi(
      replies({
        ...RESPONSE,
        overall: { ...RESPONSE.overall, light: "not_evaluable", action: "review_data", limiting_signal: null, reasons: [] },
      }),
    );
    open();
    expect(await screen.findByText("Faltan datos para evaluar esa fecha")).toBeInTheDocument();
    expect(screen.getByText("No evaluable")).toBeInTheDocument();
    expect(screen.queryByText("Luz roja")).not.toBeInTheDocument();
  });

  it("con un cultivo que no es apto no hay señales", async () => {
    fakeApi(
      replies({
        ...RESPONSE,
        suitability: { level: "not_suitable", score: 0, basis: "municipality", reasons: [] },
        window: null,
        signals: null,
        overall: { ...RESPONSE.overall, limiting_signal: null },
        limitations: [],
      }),
    );
    open();
    expect(await screen.findByText("Este cultivo no se da en su zona")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { level: 2, name: "Las señales de esta ventana" })).not.toBeInTheDocument();
  });

  it("en modo ligero se ve completa", async () => {
    setLightMode(true);
    fakeApi(replies());
    open();
    expect(await screen.findByRole("heading", { level: 2, name: "Las señales de esta ventana" })).toBeInTheDocument();
    expect(screen.getAllByRole("heading", { level: 3 }).length).toBeGreaterThanOrEqual(6);
  });
});
