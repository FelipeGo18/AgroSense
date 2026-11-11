import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RouterProvider, createMemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { PATHS } from "@/app/paths";
import { routes } from "@/app/routes";
import { monthName, sowingMonths } from "@/features/diagnosis/consult";
import type { Season } from "@/features/farm/seasons";
import {
  EMPTY_STRATEGY,
  START_PRIORITIES,
  currentFromHistory,
  explain422,
  freeHarvested,
  fromParams,
  previousFromSeasons,
  toParams,
  toRequest,
  validate,
  type StrategyForm,
} from "@/features/strategies/entry";
import { formatRange, ndviPeriod, noShortfall, windowSpans } from "@/features/strategies/cycle";
import { setLightMode } from "@/lib/lightMode";

// Datos de ejemplo de las pruebas (R5): catálogo, lote, siembras y respuesta de muestra.
const MONTHS = sowingMonths();
const MONTH = MONTHS[1].value;
const SIGNAL_DEFAULTS = { water: 3, frost: 3, heat: 3, soil: 2, supply: 2, market: 1 };
const MUNICIPALITIES = [
  { municipality_id: "15646", name: "Samacá", department: "Boyacá", lat: 5.49, lon: -73.49 },
  { municipality_id: "25899", name: "Zipaquirá", department: "Cundinamarca", lat: 5.02, lon: -74.0 },
];
const CROPS = [
  { crop_id: "papa", name_es: "Papa", kind: "crop", archetype: null, family: null, cycle_months: 5 },
  { crop_id: "arveja", name_es: "Arveja", kind: "crop", archetype: null, family: null, cycle_months: 4 },
  { crop_id: "avena_vicia", name_es: "Avena con vicia", kind: "cover", archetype: null, family: null, cycle_months: 4 },
  { crop_id: "descanso", name_es: "Descanso", kind: "fallow", archetype: null, family: null, cycle_months: 3 },
];
const VERSION = {
  dataset_version: "2026.11.0",
  rules_version: "1.0.0",
  created_at: null,
  region: "co-boyaca-cundinamarca",
  default_weights: SIGNAL_DEFAULTS,
  weights_version: "1",
  weights_reasons: {},
  sources: [
    { source_id: "agrosavia_rotacion", name: "Rotación papa, avena y arveja", institution: "Agrosavia" },
    { source_id: "nasa_power", name: "NASA POWER", institution: "NASA" },
  ],
};
const ROSA = {
  user_id: "1",
  username: "rosa.samaca",
  display_name: "Rosa",
  role: "farmer",
  consent_version: 3,
  consent_at: "2026-08-02T13:40:00Z",
  priorities: null,
  created_at: "2026-08-02T13:40:00Z",
};
const season = (id: string, crop: string, sowing: string, harvest: string | null, follows: string[] = [], area = 1): Season =>
  ({
    season_id: id,
    lot_id: "a1",
    crop_id: crop,
    area_ha: area,
    follows_season_ids: follows,
    sowing_date: sowing,
    harvest_date: harvest,
  }) as Season;
// Historial del terreno: papa, después arveja (ya cosechada y libre). Aparte, una avena en curso.
const SEASONS = [
  season("s1", "papa", "2025-02-01", "2025-07-01"),
  season("s2", "arveja", "2025-08-01", "2025-11-30", ["s1"]),
  season("s3", "avena_vicia", "2026-09-01", null, [], 1),
];
const LOT_LIST = [
  {
    lot_id: "a1",
    municipality_id: "25899",
    name: "El Alto",
    geometry: null,
    area_ha: 3,
    irrigated: true,
    created_at: "2026-10-15T10:00:00Z",
    updated_at: "2026-10-15T10:00:00Z",
    current_crop_ids: ["avena_vicia"],
  },
];
const LOT_DETAIL = { ...LOT_LIST[0], soil: null, current_seasons: [{ season_id: "s3", crop_id: "avena_vicia", area_ha: 1 }] };
const SOW = ["2026-12-07", "2027-04-05", "2027-08-02"];
const HARVEST = ["2027-03-29", "2027-07-26", "2027-12-20"];
const signal = (level: string | null, score: number | null, reason: string) => ({
  status: level ? "available" : "insufficient_data",
  level,
  critical: false,
  score,
  counts: true,
  indicators: [],
  reasons: [reason],
  sources: null,
});
const DIAGNOSIS = {
  suitability: {
    level: "suitable",
    score: 95,
    basis: "municipality",
    tmean_annual_c: 12.8,
    altitude_m: 2660,
    reasons: ["La temperatura media anual (12,8 °C) está en el rango del cultivo"],
  },
  window: { sowing_start: "2027-04-05", harvest_estimate: "2027-07-26", harvest_basis: "calendar", supply_semester: null },
  overall: {
    light: "green",
    action: "sow",
    high_risk: false,
    weights_basis: "farmer",
    limiting_signal: "frost",
    reasons: ["Heladas raras en la floración"],
  },
  overall_default: {
    light: "green",
    action: "sow",
    high_risk: false,
    weights_basis: "default",
    limiting_signal: "frost",
    reasons: ["Heladas raras en la floración"],
  },
  weights: SIGNAL_DEFAULTS,
  signals: {
    water: signal("favorable", 82, "En 8 de los últimos 10 años la lluvia cubrió lo que necesita"),
    frost: signal("favorable", 72, "Heló en la floración 4 de cada 100 años"),
    heat: signal("favorable", 95, "La máxima rara vez pasa de 22 °C"),
    soil: signal("favorable", 78, "pH estimado en el rango del cultivo"),
    supply: signal("favorable", 76, "Se sembró menos que antes"),
    market: signal(null, null, "Sin datos de precios"),
  },
  limitations: ["Sin datos de mercado: el precio no se evaluó"],
  versions: { dataset: "ejemplo", rules: "ejemplo" },
};
const cycle = (n: number, crop: string, extra: Record<string, unknown> = {}) => ({
  cycle: n,
  crop_id: crop,
  sowing_date: SOW[n - 1],
  harvest_estimate: HARVEST[n - 1],
  harvest_basis: "calendar",
  light: crop === "descanso" ? null : "green",
  light_default: crop === "descanso" ? null : "green",
  limiting_signal: null,
  high_risk: false,
  diagnosis: crop === "descanso" ? null : DIAGNOSIS,
  ...extra,
});
const criterion = (level: string, reason: string, sources = ["agrosavia_rotacion"]) => ({
  status: "available",
  level,
  rule_ids: ["regla"],
  source_ids: sources,
  reasons: [reason],
});
const HEALTH = {
  nitrogen: criterion("favorable", "La arveja y la vicia fijan nitrógeno"),
  organic_carbon: criterion("moderate", "Un ciclo devuelve materia orgánica"),
  soil_cover: {
    status: "insufficient_data",
    level: null,
    rule_ids: [],
    source_ids: [],
    reasons: ["Aún no hay una regla con fuente que diga cuántos meses bastan"],
  },
  pest_break: criterion("favorable", "La papa vuelve después de dos ciclos de otras familias"),
  erosion: criterion("unfavorable", "Con pendiente de 9 %, el suelo queda descubierto 4 meses", ["agrosavia_rotacion", "nasa_power"]),
};
const strategy = (rank: number | null, kind: string, crops: string[], total: number, extra: Record<string, unknown> = {}) => ({
  rank,
  kind,
  crop_ids: crops,
  total_score: total,
  scores: { water: 70, soil: 80, income: 60, risk: 70 },
  vs_current: null,
  cycles: crops.map((crop, i) => cycle(i + 1, crop)),
  soil_health: HEALTH,
  issues: [],
  reasons: [],
  limitations: [],
  ...extra,
});
// Datos de ejemplo (R5): dos sugeridas (una con abono verde y otra con descanso), lo de hoy y una descartada.
const ROTATIONS = {
  strategies: [
    strategy(1, "suggested", ["avena_vicia", "arveja", "papa"], 76, {
      vs_current: { water: 6, soil: -10, income: 0, risk: 12, total: 15 },
      cycles: [
        cycle(1, "avena_vicia"),
        cycle(2, "arveja", { light: "yellow", light_default: "red", limiting_signal: "frost" }),
        cycle(3, "papa"),
      ],
      reasons: ["Empieza con un abono verde"],
    }),
    strategy(2, "suggested", ["descanso", "arveja", "papa"], 70, {
      scores: { water: 80, soil: 75, income: null, risk: 64 },
      vs_current: { water: 12, soil: 25, income: null, risk: 5, total: 9 },
    }),
  ],
  current_strategy: strategy(null, "current", ["papa", "arveja", "papa"], 58, {
    issues: [
      {
        cycle: 3,
        kind: "rule",
        rule_id: "papa_espera",
        reason: "La papa vuelve después de un solo ciclo",
        source_ids: ["agrosavia_rotacion"],
      },
    ],
  }),
  excluded: [
    {
      crop_ids: ["arveja", "papa", "avena_vicia"],
      cycle: 2,
      kind: "high_risk",
      signal: "frost",
      reason: "Heló en la floración de la papa 22 de cada 100 años",
      source_ids: ["nasa_power"],
    },
  ],
  excluded_counts: { rule: 5, high_risk: 2 },
  weights: START_PRIORITIES,
  soil_basis: "municipality",
  slope_basis: "municipality",
  limitations: ["Suelo estimado para el municipio, no para su lote"],
  versions: { dataset: "ejemplo", rules: "ejemplo" },
};
const waterMonth = (month: number, normal: number[] | null, dry: number[] | null) => ({
  year: 2027,
  month,
  status: normal ? "available" : "insufficient_data",
  stage: "mid",
  need_mm: 90,
  rain_mm: { normal: normal ? 70 : null, dry: normal ? 40 : null },
  deficit_mm: { normal, dry },
  volume_m3: { normal: normal && normal.map((mm) => mm * 20), dry: dry && dry.map((mm) => mm * 20) },
});
const WATER = {
  request: { municipality_id: "15646", total_area_ha: 2, crops: [{ crop_id: "arveja", area_pct: 100, sowing_date: SOW[1] }] },
  crops: [
    {
      crop_id: "arveja",
      area_ha: 2,
      sowing_date: SOW[1],
      harvest_estimate: HARVEST[1],
      harvest_basis: "calendar",
      months: [waterMonth(4, [0, 0], [5, 9]), waterMonth(5, [8, 20], [30, 44]), waterMonth(6, null, null)],
      total_volume_m3: { normal: [160, 400], dry: [700, 1060] },
    },
  ],
  farm: { months: [], total_volume_m3: { normal: [160, 400], dry: [700, 1060] } },
  soil_moisture: [
    { month: 4, source_id: "nasa_power", indicator: "soil_wetness_root", value: 0.62, unit: "fracción" },
    { month: 4, source_id: "smap", indicator: "soil_moisture_surface", value: 0.31, unit: "m³/m³" },
  ],
  sources: { rain: "imerg", et0: "nasa_power", soil: "soilgrids" },
  soil_basis: "municipality",
  limitations: [],
  versions: { dataset: "ejemplo", rules: "ejemplo" },
};
const TRENDS = (ndvi: Record<string, unknown>) => ({
  request: { municipality_id: "15646", crop_id: "arveja", sowing_date: SOW[1] },
  water: { status: "insufficient_data", source_id: null, unit: "mm", points: [] },
  supply: { status: "insufficient_data", source_id: "eva", unit: "ha", semester: null, points: [] },
  ndvi,
  versions: { dataset: "ejemplo", rules: "ejemplo" },
});
const NDVI = {
  status: "available",
  source_id: "modis_ndvi",
  quality: "ok",
  points: Array.from({ length: 23 }, (_, i) => ({ period: i + 1, ndvi_normal: i === 5 ? null : 0.5 + (i % 5) / 20 })),
};
const TRENDS_KEY = `GET /api/v1/trends?municipality_id=15646&crop_id=arveja&sowing_date=${SOW[1]}`;
const SOIL = (id: string) => ({
  municipality_id: id,
  ph: { value: 5.5, p05: 5.2, p95: 5.8 },
  soc_g_kg: { value: 31, p05: 25, p95: 38 },
  nitrogen_g_kg: null,
  clay_pct: null,
  sand_pct: null,
  silt_pct: null,
  texture_class: null,
  slope_pct: 9,
  cells: 10,
  quality: "ok",
  source_id: "soilgrids",
  versions: { dataset: "ejemplo", rules: "ejemplo" },
});

type Reply = { status: number; body?: unknown };
function fakeApi(extra: Record<string, Reply> = {}) {
  const calls: { key: string; body: unknown }[] = [];
  const replies: Record<string, Reply> = {
    "GET /api/v1/catalogs/municipalities": { status: 200, body: MUNICIPALITIES },
    "GET /api/v1/catalogs/crops": { status: 200, body: CROPS },
    "GET /api/v1/version": { status: 200, body: VERSION },
    "POST /api/v1/rotations": { status: 200, body: ROTATIONS },
    "GET /api/v1/catalogs/municipalities/15646/soil": { status: 200, body: SOIL("15646") },
    "GET /api/v1/catalogs/municipalities/25899/soil": { status: 200, body: SOIL("25899") },
    "POST /api/v1/water-plans": { status: 200, body: WATER },
    [TRENDS_KEY]: { status: 200, body: TRENDS(NDVI) },
    ...extra,
  };
  vi.stubGlobal("fetch", async (url: string, init: RequestInit = {}) => {
    const key = `${init.method ?? "GET"} ${url}`;
    calls.push({ key, body: init.body ? JSON.parse(String(init.body)) : undefined });
    const reply = replies[key] ?? { status: 401, body: { error: { code: "unauthorized", message: "No." } } };
    return new Response(reply.body === undefined ? null : JSON.stringify(reply.body), { status: reply.status });
  });
  return calls;
}
const rotationCalls = (calls: { key: string; body: unknown }[]) =>
  calls.filter((c) => c.key === "POST /api/v1/rotations").map((c) => c.body);
function open(path: string = PATHS.consult) {
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  render(<RouterProvider router={router} />);
  return router;
}
const group = (legend: string) => within(screen.getByRole("group", { name: legend }));
const ORDERED = "Estrategias ordenadas por lo que le importa";
const results = () => screen.findByRole("heading", { name: ORDERED });
const card = (name: string | RegExp) => within(screen.getByRole("article", { name }));
const GUEST = `${PATHS.consult}?municipio=15646&siembra=${MONTH}&anterior=papa&riego=no&ciclos=3`;

beforeEach(() => {
  sessionStorage.clear();
  localStorage.clear();
});
afterEach(() => {
  vi.unstubAllGlobals();
  setLightMode(false);
});

describe("La entrada (HU-214): reglas", () => {
  const ok: StrategyForm = {
    ...EMPTY_STRATEGY,
    municipalityId: "15646",
    areaText: "2,5",
    previousMode: "crops",
    previous: ["papa", "", ""],
    month: MONTH,
    irrigation: "no",
  };
  const context = {
    municipalityIds: new Set(["15646"]),
    cropIds: new Set(["papa", "arveja", "avena_vicia"]),
    months: MONTHS.map((m) => m.value),
    lot: false,
  };

  it("el área nunca va en la dirección (R9); lo demás va y vuelve", () => {
    const params = toParams({ ...ok, currentMode: "crops", current: ["papa", "arveja", ""] });
    expect(params.toString()).toBe(`municipio=15646&siembra=${MONTH}&anterior=papa&riego=no&ciclos=3&actual=papa%2Carveja`);
    expect(params.has("area")).toBe(false);
    expect(fromParams(params)).toMatchObject({
      municipalityId: "15646",
      previous: ["papa", "", ""],
      current: ["papa", "arveja", ""],
      cycles: 3,
    });
    expect(toParams({ ...ok, previousMode: "none" }).get("anterior")).toBe("ninguno");
  });

  it("valida el área, lo de antes sin huecos, la rotación actual de 2 o 3 y los demás campos", () => {
    expect(validate(ok, context)).toEqual({});
    expect(validate({ ...ok, areaText: "0" }, context)).toHaveProperty("area");
    expect(validate({ ...ok, areaText: "abc" }, context)).toHaveProperty("area");
    expect(validate({ ...ok, previousMode: "" }, context)).toHaveProperty("previous");
    expect(validate({ ...ok, previous: ["", "papa", ""] }, context)).toHaveProperty("previous"); // hueco
    expect(validate({ ...ok, previousMode: "none", previous: ["", "", ""] }, context)).toEqual({});
    expect(validate({ ...ok, currentMode: "crops", current: ["papa", "", ""] }, context)).toHaveProperty("current"); // solo uno
    expect(validate({ ...ok, currentMode: "crops", current: ["papa", "arveja", "papa"] }, context)).toEqual({});
    expect(validate({ ...ok, month: "2020-01" }, context)).toHaveProperty("month");
    // Con lote, el municipio, el área, lo de antes y el riego salen del lote.
    expect(validate({ ...EMPTY_STRATEGY, month: MONTH, lotId: "a1" }, { ...context, lot: true })).toEqual({});
  });

  it("con cuenta, lo de antes y la rotación actual salen del historial del terreno", () => {
    expect(freeHarvested(SEASONS).map((s) => s.season_id)).toEqual(["s2"]); // la papa ya tiene la arveja encima
    expect(previousFromSeasons([SEASONS[1]])).toEqual(["arveja"]);
    expect(currentFromHistory([SEASONS[1]], SEASONS)).toEqual(["papa", "arveja"]);
    expect(currentFromHistory([SEASONS[0]], SEASONS)).toEqual([]); // con un solo cultivo no hay rotación
  });

  it("el cuerpo de POST /rotations lleva las prioridades de la rotación y las de las señales", () => {
    expect(toRequest({ ...ok, cycles: 2 }, START_PRIORITIES, SIGNAL_DEFAULTS)).toEqual({
      municipality_id: "15646",
      sowing_date: `${MONTH}-01`,
      previous_crop_ids: ["papa"],
      current_crop_ids: null,
      cycles: 2,
      priorities: { water: 3, soil: 3, income: 3, risk: 3 },
      signal_priorities: SIGNAL_DEFAULTS,
      irrigated: false,
      lot_id: null,
    });
  });

  it("un 422 se explica en palabras sencillas", () => {
    expect(explain422("Hay datos que no son válidos. Revise: priorities.")).toBe(
      "Hay un dato que no sirve para consultar. Revise sus prioridades de la rotación.",
    );
    expect(explain422("Hay datos que no son válidos. Revise: cycles, current_crop_ids.0.")).toBe(
      "Hay un dato que no sirve para consultar. Revise los ciclos y la rotación que viene haciendo.",
    );
    expect(explain422("Otro mensaje")).toBe("Otro mensaje");
  });
});

describe("Entrada a las estrategias sin cuenta (HU-214)", () => {
  it("pide los datos del terreno, envía POST /rotations y el área se queda en el navegador", async () => {
    const calls = fakeApi();
    const router = open();
    const user = userEvent.setup();

    await user.type(await screen.findByRole("combobox", { name: "Municipio" }), "sama");
    await user.click(await screen.findByRole("option", { name: /Samacá/ }));
    await user.type(screen.getByLabelText("Área del terreno, en hectáreas"), "2,5");
    await user.click(group("¿Qué había antes en el terreno?").getByRole("radio", { name: "Uno o más cultivos" }));
    await user.selectOptions(screen.getByLabelText("Lo último que sembró"), "papa");
    await user.selectOptions(screen.getByLabelText("¿Cuándo sembraría el primer ciclo?"), MONTH);
    await user.click(group("¿Tiene riego?").getByRole("radio", { name: "No" }));
    await user.click(group("¿Cuántos ciclos quiere planear?").getByRole("radio", { name: "2 ciclos" }));
    await user.click(screen.getByRole("button", { name: "Ver estrategias" }));

    await results();
    expect(rotationCalls(calls)[0]).toEqual({
      municipality_id: "15646",
      sowing_date: `${MONTH}-01`,
      previous_crop_ids: ["papa"],
      current_crop_ids: null,
      cycles: 2,
      priorities: START_PRIORITIES,
      signal_priorities: SIGNAL_DEFAULTS,
      irrigated: false,
      lot_id: null,
    });
    // El área no viaja a la API ni a la dirección (R9): solo queda en esta pestaña.
    expect(JSON.stringify(rotationCalls(calls)[0])).not.toContain("2,5");
    expect(router.state.location.search).not.toContain("area");
    expect(sessionStorage.getItem("agrosense.area")).toBe("2,5");

    // El resumen de la consulta, con «Cambiar».
    expect(screen.getByRole("heading", { level: 1, name: "Estrategias para los próximos 2 ciclos" })).toBeInTheDocument();
    expect(screen.getByText("Estrategias · Samacá, Boyacá")).toBeInTheDocument();
    expect(screen.getByText("2,50 ha · antes: papa · sin cuenta")).toBeInTheDocument();
    expect(screen.getByText("No tiene una rotación fija")).toBeInTheDocument();
    expect(screen.getByText(`${monthName(MONTH)} · sin riego`)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Cambiar: terreno y lo que había antes" })).toBeInTheDocument();
  });

  it("desde el diagnóstico llega con el municipio, la fecha, el riego y el cultivo como lo que había antes", async () => {
    const calls = fakeApi();
    open(`${PATHS.consult}?municipio=15646&siembra=${MONTH}&anterior=papa&riego=no`);
    await waitFor(() => expect(screen.getByRole("combobox", { name: "Municipio" })).toHaveValue("Samacá"));
    expect(screen.getByLabelText("Lo último que sembró")).toHaveValue("papa");
    expect(screen.getByLabelText("¿Cuándo sembraría el primer ciclo?")).toHaveValue(MONTH);
    expect(group("¿Tiene riego?").getByRole("radio", { name: "No" })).toBeChecked();
    // Falta el área, que nunca viaja en la dirección: se pide y no se consulta todavía.
    expect(await screen.findByText(/Escriba el área en hectáreas/)).toBeInTheDocument();
    expect(rotationCalls(calls)).toHaveLength(0);

    const user = userEvent.setup();
    await user.type(screen.getByLabelText("Área del terreno, en hectáreas"), "1");
    await user.click(screen.getByRole("button", { name: "Ver estrategias" }));
    await results();
    expect(rotationCalls(calls)[0]).toMatchObject({ municipality_id: "15646", previous_crop_ids: ["papa"], irrigated: false });
  });

  it("la rotación que viene haciendo se envía en orden y es opcional", async () => {
    const calls = fakeApi();
    sessionStorage.setItem("agrosense.area", "2");
    open(`${PATHS.consult}?municipio=15646&siembra=${MONTH}&anterior=ninguno&riego=si`);
    const user = userEvent.setup();
    await results();
    expect(rotationCalls(calls)[0]).toMatchObject({ previous_crop_ids: [], current_crop_ids: null, irrigated: true });

    await user.click(screen.getByRole("button", { name: "Cambiar: lo que viene sembrando" }));
    expect(screen.getByRole("heading", { level: 1, name: "¿Qué sembrar en los próximos ciclos?" })).toHaveFocus();
    await user.click(group("¿Qué viene sembrando en este terreno?").getByRole("radio", { name: "Sí, en este orden" }));
    await user.selectOptions(screen.getByLabelText("Primero siembra"), "papa");
    await user.click(screen.getByRole("button", { name: "Ver estrategias" }));
    expect(await screen.findByText(STRATEGY_CURRENT_ERROR)).toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText("Después"), "arveja");
    await user.click(screen.getByRole("button", { name: "Ver estrategias" }));
    await waitFor(() => expect(rotationCalls(calls).at(-1)).toMatchObject({ current_crop_ids: ["papa", "arveja"] }));
    expect(await screen.findByText("Papa → Arveja")).toBeInTheDocument();
  });

  it("valida en el acto: un área que no sirve se marca al salir del campo", async () => {
    fakeApi();
    open();
    const user = userEvent.setup();
    const area = await screen.findByLabelText("Área del terreno, en hectáreas");
    await user.type(area, "cero");
    await user.tab();
    expect(screen.getByText("Escriba el área en hectáreas, mayor que cero (por ejemplo, 2,5).")).toBeInTheDocument();
  });

  it("un 422 de la API se explica en palabras sencillas", async () => {
    fakeApi({
      "POST /api/v1/rotations": {
        status: 422,
        body: { error: { code: "invalid_input", message: "Hay datos que no son válidos. Revise: cycles.", request_id: "r1" } },
      },
    });
    sessionStorage.setItem("agrosense.area", "2");
    open(GUEST);
    expect(await screen.findByText("Hay un dato que no sirve para consultar. Revise los ciclos.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Cambiar los datos" })).toBeInTheDocument();
  });

  it("en modo ligero se ve completa", async () => {
    setLightMode(true);
    fakeApi();
    open();
    expect(await screen.findByRole("heading", { level: 1, name: "¿Qué sembrar en los próximos ciclos?" })).toBeInTheDocument();
    expect(await screen.findByRole("combobox", { name: "Municipio" })).toBeInTheDocument();
    expect(screen.getByLabelText("Área del terreno, en hectáreas")).toBeInTheDocument();
  });
});

const STRATEGY_CURRENT_ERROR = "Elija al menos dos cultivos, en el orden en que los siembra, o «No tengo una rotación fija».";

describe("Prioridades de la rotación (HU-101)", () => {
  it("al moverlas se vuelve a pedir el orden con ellas, y todas en 0 no consultan", async () => {
    const calls = fakeApi();
    sessionStorage.setItem("agrosense.area", "2");
    open(GUEST);
    const user = userEvent.setup();
    await results();
    expect(screen.getByText("Toque las semillas: el orden cambia al instante.")).toBeInTheDocument();

    const seeds = (name: string) => within(screen.getByRole("radiogroup", { name: new RegExp(`^${name}:`) }));
    await user.click(seeds("Agua").getByRole("radio", { name: /^5 de 5/ }));
    await waitFor(() => expect(rotationCalls(calls).at(-1)).toMatchObject({ priorities: { water: 5, soil: 3, income: 3, risk: 3 } }));

    const before = rotationCalls(calls).length;
    for (const name of ["Agua", "Suelo", "Ingreso", "Riesgo"]) await user.click(seeds(name).getByRole("radio", { name: /^0 de 5/ }));
    expect(await screen.findByText("Todas sus prioridades están en 0. Suba al menos una para comparar estrategias.")).toBeInTheDocument();
    expect(rotationCalls(calls)).toHaveLength(before + 3); // las tres primeras aún tenían alguna en más de 0
    expect(screen.queryByRole("heading", { name: ORDERED })).not.toBeInTheDocument();
  });
});

describe("Estrategias con ciclos, desglose y salud del suelo (HU-102)", () => {
  async function openResults(rotations: unknown = ROTATIONS) {
    const calls = fakeApi({ "POST /api/v1/rotations": { status: 200, body: rotations } });
    sessionStorage.setItem("agrosense.area", "2");
    const router = open(GUEST);
    await screen.findByRole("heading", { level: 1, name: "Estrategias para los próximos 3 ciclos" });
    return { calls, router, user: userEvent.setup() };
  }

  it("lo de hoy va primero y después las sugeridas en su orden, con su puntaje y lo que ganan o pierden", async () => {
    await openResults();
    await results();
    const articles = screen.getAllByRole("article").map((a) => a.getAttribute("aria-label"));
    expect(articles).toEqual([
      "Lo que siembra hoy: Papa → Arveja → Papa",
      "Estrategia 1: Avena con vicia → Arveja → Papa",
      "Estrategia 2: Descanso → Arveja → Papa",
    ]);
    const today = card(/^Lo que siembra hoy/);
    expect(today.getByText("Se evalúa igual que las demás y no entra al orden.")).toBeInTheDocument();
    expect(today.getByText("Ciclo 3: no cumple una regla de rotación")).toBeInTheDocument();
    expect(today.getByText("La papa vuelve después de un solo ciclo")).toBeInTheDocument();

    const first = card(/^Estrategia 1/);
    expect(first.getByLabelText("Puesto 1")).toBeInTheDocument();
    expect(first.getByText("76")).toBeInTheDocument();
    expect(first.getByText("15 más que hoy en total")).toBeInTheDocument();
    // El desglose: puntaje, peso y diferencia frente a hoy, con forma y texto.
    expect(first.getByText("6 más que hoy")).toBeInTheDocument();
    expect(first.getByText("10 menos que hoy")).toBeInTheDocument();
    expect(first.getByText("Igual que hoy")).toBeInTheDocument();
    expect(first.getAllByText("peso 3")).toHaveLength(4);
    expect(first.getByText("Empieza con un abono verde")).toBeInTheDocument();

    // Un criterio sin datos no tiene barra ni cuenta como malo (R1).
    expect(card(/^Estrategia 2/).getByText("Sin datos: no entra al total")).toBeInTheDocument();
  });

  it("cada ciclo dice su cultivo, sus fechas y su luz con forma y texto; el descanso no tiene semáforo", async () => {
    await openResults();
    await results();
    const first = card(/^Estrategia 1/);
    const cover = within(first.getByRole("listitem", { name: "Ciclo 1 de 3: Avena con vicia" }));
    expect(cover.getByText("Abono verde")).toBeInTheDocument();
    expect(cover.getByText(/^Se incorpora ~/)).toBeInTheDocument();
    const peas = within(first.getByRole("listitem", { name: "Ciclo 2 de 3: Arveja" }));
    expect(peas.getByText("Luz amarilla")).toBeInTheDocument();
    expect(peas.getByText("luz roja").parentElement).toHaveTextContent("Con el criterio de AgroSense: luz roja");
    expect(peas.getByText("Limita: heladas")).toBeInTheDocument();
    expect(peas.getByText(/^Cosecha ~/)).toBeInTheDocument();
    expect(first.getByText("Cosecha estimada con la duración de las etapas del cultivo. No es pronóstico.")).toBeInTheDocument();

    const rest = within(card(/^Estrategia 2/).getByRole("listitem", { name: "Ciclo 1 de 3: Descanso" }));
    expect(rest.getByText("Sin semáforo: no se siembra")).toBeInTheDocument();
    expect(rest.queryByText(/^Luz /)).not.toBeInTheDocument();
  });

  it("la salud del suelo trae sus cinco criterios con nivel, razón y fuente; sin datos no se pinta como malo", async () => {
    await openResults();
    await results();
    const health = within(card(/^Estrategia 1/).getByRole("region", { name: "Salud del suelo" }));
    expect(health.getByText("Comparación, no predicción")).toBeInTheDocument();
    for (const label of ["Nitrógeno", "Carbono orgánico", "Suelo cubierto", "Corte de plagas", "Erosión"]) {
      expect(health.getByText(label)).toBeInTheDocument();
    }
    expect(health.getByText("Sin datos suficientes")).toBeInTheDocument();
    expect(health.getByText("Desfavorable")).toBeInTheDocument();
    expect(health.getAllByText("Fuente: Rotación papa, avena y arveja (Agrosavia)")).toHaveLength(3);
    expect(health.getByText("Fuente: Rotación papa, avena y arveja (Agrosavia) · NASA POWER (NASA)")).toBeInTheDocument();
    // El criterio sin regla con fuente no inventa una (R8).
    const cover = health.getByText("Suelo cubierto").closest("li")!;
    expect(cover).not.toHaveTextContent("Fuente:");
  });

  it("dice el suelo que se usó con su rango y que es una estimación, y los rótulos de comparación y decisión", async () => {
    await openResults();
    await results();
    expect(await screen.findByText("pH estimado de 5,2 a 5,8 (valor central 5,5) · carbono orgánico de 25 a 38 g/kg")).toBeInTheDocument();
    expect(screen.getByText("Suelo estimado de Samacá · 250 m")).toBeInTheDocument();
    expect(screen.getByText("Estimación de un mapa global de 250 m. Un análisis de suelo de su lote es más preciso.")).toBeInTheDocument();
    expect(screen.getByText("Compara estrategias según reglas con fuente. No predice cuánto va a mejorar su suelo.")).toBeInTheDocument();
    expect(screen.getByText("Es información para decidir. La decisión es suya.")).toBeInTheDocument();
    expect(screen.getByText("respuesta simulada")).toBeInTheDocument();
    expect(screen.getByText("Datos ejemplo · Reglas ejemplo")).toBeInTheDocument();
  });

  it("las descartadas se ven a pedido, con su ciclo, su motivo y su fuente, y cuántas son en total", async () => {
    const { user } = await openResults();
    await results();
    const details = screen.getByText("7 estrategias descartadas, cada una con su regla o motivo").closest("details")!;
    expect(details).not.toHaveAttribute("open");
    await user.click(within(details).getByText("Ver por qué"));
    expect(details).toHaveAttribute("open");
    const list = within(details);
    expect(list.getByText("Arveja → Papa → Avena con vicia")).toBeInTheDocument();
    expect(list.getByText("Ciclo 2: alto riesgo de clima (heladas)")).toBeInTheDocument();
    expect(list.getByText("Heló en la floración de la papa 22 de cada 100 años")).toBeInTheDocument();
    expect(list.getByText("Fuente: NASA POWER (NASA)")).toBeInTheDocument();
    expect(
      list.getByText("Aquí van las primeras 1. En total se descartaron 5 por reglas de rotación, 2 por riesgo grave de clima."),
    ).toBeInTheDocument();
  });

  it("sin rotación actual lo dice y ofrece escribirla", async () => {
    const { user } = await openResults({
      ...ROTATIONS,
      current_strategy: null,
      strategies: ROTATIONS.strategies.map((s) => ({ ...s, vs_current: null })),
    });
    await results();
    expect(screen.getByText(/No nos dijo qué viene sembrando en este terreno/)).toBeInTheDocument();
    expect(screen.queryByText(/más que hoy/)).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Escribir lo que siembro" }));
    expect(group("¿Qué viene sembrando en este terreno?").getByRole("radio", { name: "Sí, en este orden" })).toBeChecked();
    expect(screen.getByLabelText("Primero siembra")).toBeInTheDocument();
    // «Volver sin cambiar» regresa a las mismas estrategias.
    await user.click(screen.getByRole("button", { name: "Volver sin cambiar" }));
    await results();
  });

  it("sin estrategias válidas: estado vacío con las descartadas a la vista y qué cambiar", async () => {
    const empty = { ...ROTATIONS, strategies: [], current_strategy: null };
    const { calls, user } = await openResults(empty);
    expect(await screen.findByRole("heading", { name: "Ninguna estrategia cumple las reglas con estos datos" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: ORDERED })).not.toBeInTheDocument();
    const details = screen.getByText("7 estrategias descartadas, cada una con su regla o motivo").closest("details")!;
    expect(details).toHaveAttribute("open");

    await user.click(screen.getByRole("button", { name: "Probar con 2 ciclos" }));
    await waitFor(() => expect(rotationCalls(calls).at(-1)).toMatchObject({ cycles: 2 }));
    expect(await screen.findByRole("heading", { level: 1, name: "Estrategias para los próximos 2 ciclos" })).toBeInTheDocument();
    // Con dos ciclos ya no se ofrece bajar más: solo cambiar la fecha, que vuelve a la entrada.
    expect(await screen.findByRole("heading", { name: "Ninguna estrategia cumple las reglas con estos datos" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Probar con 2 ciclos" })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Cambiar la fecha" }));
    expect(screen.getByLabelText("¿Cuándo sembraría el primer ciclo?")).toHaveValue(MONTH);
  });
});

describe("Entrada a las estrategias desde el lote (HU-214)", () => {
  it("toma el municipio, el riego y el historial del lote, y envía lot_id", async () => {
    const calls = fakeApi({
      "GET /api/v1/me": { status: 200, body: ROSA },
      "GET /api/v1/lots": { status: 200, body: LOT_LIST },
      "GET /api/v1/lots/a1": { status: 200, body: LOT_DETAIL },
      "GET /api/v1/lots/a1/seasons": { status: 200, body: SEASONS },
    });
    open(`${PATHS.consult}?lote=a1`);
    const user = userEvent.setup();

    expect(await screen.findByText(/Zipaquirá, Cundinamarca/)).toBeInTheDocument();
    expect(screen.getByText("Con riego")).toBeInTheDocument();
    expect(screen.queryByRole("combobox", { name: "Municipio" })).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Área del terreno, en hectáreas")).not.toBeInTheDocument();

    // Elige el terreno que dejó la arveja: lo de antes es la arveja y la rotación actual, papa y arveja.
    await user.click(screen.getByRole("checkbox", { name: /Arveja/ }));
    expect(screen.getByLabelText("Primero siembra")).toHaveValue("papa");
    expect(screen.getByLabelText("Después")).toHaveValue("arveja");
    await user.selectOptions(screen.getByLabelText("¿Cuándo sembraría el primer ciclo?"), MONTH);
    await user.click(screen.getByRole("button", { name: "Ver estrategias" }));

    await results();
    expect(rotationCalls(calls)[0]).toMatchObject({
      municipality_id: "25899",
      previous_crop_ids: ["arveja"],
      current_crop_ids: ["papa", "arveja"],
      irrigated: true,
      lot_id: "a1",
    });
    expect(screen.getByText("Estrategias · Zipaquirá, Cundinamarca")).toBeInTheDocument();
    expect(screen.getByText("El Alto · 1,00 ha · antes: arveja")).toBeInTheDocument();
    expect(screen.getByText(`${monthName(MONTH)} · con riego`)).toBeInTheDocument();
  });

  it("un lote en la dirección sin sesión no se consulta y lo dice", async () => {
    const calls = fakeApi();
    open(`${PATHS.consult}?lote=a1&siembra=${MONTH}`);
    expect(await screen.findByText(/Ese lote no está entre los suyos/)).toBeInTheDocument();
    expect(rotationCalls(calls)).toHaveLength(0);
  });
});

describe("Ciclo de una estrategia (HU-215)", () => {
  const CYCLE = `${GUEST}&estrategia=avena_vicia-arveja-papa&ciclo=2`;
  const waterCalls = (calls: { key: string; body: unknown }[]) =>
    calls.filter((c) => c.key === "POST /api/v1/water-plans").map((c) => c.body);

  it("reglas: el periodo del NDVI, la ventana que pasa de año y los rangos", () => {
    expect(ndviPeriod("2027-01-01")).toBe(1);
    expect(ndviPeriod("2027-12-31")).toBe(23);
    expect(windowSpans("2027-04-05", "2027-07-26")).toEqual([[6, 13]]);
    expect(windowSpans("2027-11-01", "2028-02-15")).toEqual([
      [20, 23], // el 1 de noviembre es el día 305: periodo 20
      [1, 3],
    ]);
    expect(windowSpans("2027-01-01", "2028-01-02")).toEqual([[1, 23]]);
    expect(formatRange([8, 20], "mm")).toBe("8 a 20 mm");
    expect(formatRange([20, 20], "mm")).toBe("20 mm");
    expect(formatRange(null, "mm")).toBeNull();
    expect(noShortfall([0, 0])).toBe(true);
    expect(noShortfall([0, 4])).toBe(false);
  });

  it("tocar un ciclo abre su detalle con el diagnóstico que ya vino, sin pedir otro", async () => {
    const calls = fakeApi();
    sessionStorage.setItem("agrosense.area", "2");
    const router = open(GUEST);
    const user = userEvent.setup();
    await results();
    await user.click(card(/^Estrategia 1/).getByRole("link", { name: "Ver el ciclo 2 de 3: Arveja" }));

    expect(await screen.findByRole("heading", { level: 1, name: "Ciclo 2 de 3: arveja" })).toBeInTheDocument();
    expect(new URLSearchParams(router.state.location.search).get("estrategia")).toBe("avena_vicia-arveja-papa");
    expect(screen.getByRole("link", { name: "2 · Arveja" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByText("Puede sembrar en esa fecha")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Las seis señales de este ciclo" })).toBeInTheDocument();
    expect(screen.getByText("Heló en la floración 4 de cada 100 años")).toBeInTheDocument();
    expect(calls.some((c) => c.key === "POST /api/v1/diagnostics")).toBe(false);
    // Ciclo anterior y siguiente, y volver a las estrategias.
    expect(screen.getByRole("link", { name: "‹ Ciclo 1: avena con vicia" })).toBeInTheDocument();
    await user.click(screen.getByRole("link", { name: "Ciclo 3: papa ›" }));
    expect(await screen.findByRole("heading", { level: 1, name: "Ciclo 3 de 3: papa" })).toBeInTheDocument();
    await user.click(screen.getByRole("link", { name: "‹ Volver a las estrategias" }));
    await results();
  });

  it("el agua del ciclo: por mes en rangos, año normal o seco, con el rótulo de estimación", async () => {
    const calls = fakeApi();
    sessionStorage.setItem("agrosense.area", "2");
    open(CYCLE);
    const user = userEvent.setup();
    expect(await screen.findByRole("heading", { name: "Agua de este ciclo" })).toBeInTheDocument();
    await waitFor(() =>
      expect(waterCalls(calls)[0]).toEqual({
        municipality_id: "15646",
        total_area_ha: 2,
        crops: [{ crop_id: "arveja", area_pct: 100, sowing_date: SOW[1] }],
      }),
    );
    expect(await screen.findByText("Estimación con el clima de la zona. Verifique la humedad del suelo en su lote")).toBeInTheDocument();
    const may = within(screen.getByRole("listitem", { name: /^may/i }));
    expect(may.getByText("8 a 20 mm")).toBeInTheDocument();
    expect(may.getByText("160 a 400 m³")).toBeInTheDocument();
    expect(may.getByText("el cultivo pasaría sed")).toBeInTheDocument();
    expect(within(screen.getByRole("listitem", { name: /^abr/i })).getByText("La lluvia alcanza")).toBeInTheDocument();
    expect(within(screen.getByRole("listitem", { name: /^jun/i })).getByText("Sin datos suficientes")).toBeInTheDocument();
    expect(screen.getByText(/En el ciclo faltarían 160 a 400 m³/)).toBeInTheDocument();

    await user.click(group("¿Qué año ver?").getByRole("radio", { name: "Año seco" }));
    expect(within(screen.getByRole("listitem", { name: /^abr/i })).getByText("5 a 9 mm")).toBeInTheDocument();
    expect(screen.getByText(/En el ciclo faltarían 700 a 1.060 m³ en un año seco/)).toBeInTheDocument();

    // La humedad del suelo de la zona, por fuente y en su unidad, para contrastar.
    const moisture = within(screen.getByRole("region", { name: "Humedad del suelo de la zona" }));
    expect(moisture.getByText("NASA POWER (NASA)")).toBeInTheDocument();
    expect(moisture.getByText("SMAP (NASA)")).toBeInTheDocument();
    expect(moisture.getByText("0,31 m³/m³")).toBeInTheDocument();
    expect(moisture.getAllByText("Para contrastar")).toHaveLength(2);
  });

  it("con riego, lo que falta es el riego que haría falta", async () => {
    fakeApi();
    sessionStorage.setItem("agrosense.area", "2");
    open(CYCLE.replace("riego=no", "riego=si"));
    const may = await screen.findByRole("listitem", { name: /^may/i });
    expect(within(may).getByText("riego que haría falta")).toBeInTheDocument();
  });

  it("el verdor de la zona con la ventana del ciclo, en gráfica y en tabla, y el enlace a qué cambió", async () => {
    fakeApi();
    sessionStorage.setItem("agrosense.area", "2");
    open(CYCLE);
    expect(await screen.findByText("Cuándo suele estar verde el campo en su zona · MODIS, 250 m")).toBeInTheDocument();
    expect(await screen.findByRole("img", { name: /Verdor normal de la zona/ })).toBeInTheDocument();
    expect(screen.getByText("Ver los datos en una tabla")).toBeInTheDocument();
    expect(screen.getAllByText("Sin dato").length).toBeGreaterThan(0); // el periodo sin dato no se inventa
    expect(screen.getByRole("link", { name: "Ver qué cambió en su zona" })).toHaveAttribute(
      "href",
      `${PATHS.changes}?municipio=15646&cultivo=arveja`,
    );
  });

  it("sin datos del verdor, lo dice en vez de dibujar", async () => {
    fakeApi({
      [TRENDS_KEY]: { status: 200, body: TRENDS({ status: "insufficient_data", source_id: "modis_ndvi", quality: null, points: [] }) },
    });
    sessionStorage.setItem("agrosense.area", "2");
    open(CYCLE);
    expect(await screen.findByText("Sin datos suficientes del verdor de su zona.")).toBeInTheDocument();
    expect(screen.queryByRole("img", { name: /Verdor normal/ })).not.toBeInTheDocument();
  });

  it("un descanso no tiene semáforo: dice cuánto dura y por qué se propone", async () => {
    const calls = fakeApi();
    sessionStorage.setItem("agrosense.area", "2");
    open(`${GUEST}&estrategia=descanso-arveja-papa&ciclo=1`);
    expect(await screen.findByRole("heading", { level: 1, name: "Ciclo 1 de 3: descanso" })).toBeInTheDocument();
    expect(screen.getByText("Sin semáforo: en un descanso no se siembra")).toBeInTheDocument();
    expect(screen.getByText(/semanas sin sembrar/)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Después del descanso" })).toBeInTheDocument();
    expect(screen.getByText("Datos ejemplo · Reglas ejemplo")).toBeInTheDocument();
    expect(screen.queryByText(/^Luz /)).not.toBeInTheDocument();
    expect(waterCalls(calls)).toHaveLength(0);
  });

  it("un ciclo que ya no está en la respuesta vuelve a la lista", async () => {
    fakeApi();
    sessionStorage.setItem("agrosense.area", "2");
    open(`${GUEST}&estrategia=maiz-papa-arveja&ciclo=1`);
    await results();
  });

  it("sin cuenta, el primer ciclo ofrece crear cuenta para registrarlo", async () => {
    fakeApi();
    sessionStorage.setItem("agrosense.area", "2");
    open(`${GUEST}&estrategia=avena_vicia-arveja-papa&ciclo=1`);
    expect(await screen.findByRole("link", { name: "Crear cuenta y registrarla" })).toHaveAttribute("href", PATHS.signup);
  });
});

describe("Registrar el primer ciclo desde el lote (HU-215, HU-165)", () => {
  const lotApi = (sowing: string) => {
    const rotations = {
      ...ROTATIONS,
      strategies: [
        strategy(1, "suggested", ["avena_vicia", "arveja", "papa"], 76, {
          cycles: [cycle(1, "avena_vicia", { sowing_date: sowing }), cycle(2, "arveja"), cycle(3, "papa")],
        }),
      ],
    };
    return fakeApi({
      "GET /api/v1/me": { status: 200, body: ROSA },
      "GET /api/v1/lots": { status: 200, body: LOT_LIST },
      "GET /api/v1/lots/a1": { status: 200, body: LOT_DETAIL },
      "GET /api/v1/lots/a1/seasons": { status: 200, body: SEASONS },
      "POST /api/v1/rotations": { status: 200, body: rotations },
      "POST /api/v1/lots/a1/seasons": { status: 201, body: SEASONS[0] },
    });
  };
  const LOT_CYCLE = `${PATHS.consult}?lote=a1&siembras=s2&siembra=${MONTH}&ciclos=3&estrategia=avena_vicia-arveja-papa&ciclo=1`;

  it("lleva al formulario de siembra ya armado, y la siembra se guarda con el diagnóstico que vio", async () => {
    const calls = lotApi("2026-01-05");
    const router = open(LOT_CYCLE);
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "Registrar esta siembra de avena con vicia" }));

    expect(await screen.findByRole("heading", { level: 1, name: "Registrar la siembra" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe(PATHS.sow("a1"));
    expect(screen.getByLabelText("Cultivo")).toHaveValue("avena_vicia");
    expect(screen.getByLabelText("Fecha de siembra")).toHaveValue("2026-01-05");
    expect(screen.getByText(/Se guarda con el diagnóstico que vio en la estrategia \(luz verde\)/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Guardar siembra" }));
    await waitFor(() =>
      expect(calls.find((c) => c.key === "POST /api/v1/lots/a1/seasons")?.body).toMatchObject({
        crop_id: "avena_vicia",
        sowing_date: "2026-01-05",
        follows_season_ids: ["s2"],
        diagnosis_light: "green",
        diagnosis_light_default: "green",
        diagnosis_action: "sow",
        diagnosis_irrigated: true,
        dataset_version: "ejemplo",
      }),
    );
  });

  it("con otro cultivo, el diagnóstico de la estrategia ya no corresponde y no se guarda", async () => {
    const calls = lotApi("2026-01-05");
    open(LOT_CYCLE);
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "Registrar esta siembra de avena con vicia" }));
    await user.selectOptions(await screen.findByLabelText("Cultivo"), "papa");
    expect(screen.getByText(/el diagnóstico de la estrategia ya no corresponde/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Guardar siembra" }));
    await waitFor(() => expect(calls.find((c) => c.key === "POST /api/v1/lots/a1/seasons")).toBeDefined());
    expect(calls.find((c) => c.key === "POST /api/v1/lots/a1/seasons")?.body).not.toHaveProperty("diagnosis_light");
  });

  it("si la fecha del primer ciclo todavía no llega, dice cuándo registrarla", async () => {
    lotApi("2099-01-05");
    open(LOT_CYCLE);
    expect(await screen.findByText(/Cuando la siembre, desde el 5 de enero de 2099, regístrela en su lote/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Registrar esta siembra/ })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Ir a mi lote" })).toHaveAttribute("href", PATHS.lot("a1"));
  });
});
