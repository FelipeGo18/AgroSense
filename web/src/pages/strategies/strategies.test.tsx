import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RouterProvider, createMemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { PATHS } from "@/app/paths";
import { routes } from "@/app/routes";
import { sowingMonths } from "@/features/diagnosis/consult";
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
];
const VERSION = {
  dataset_version: "2026.11.0",
  rules_version: "1.0.0",
  created_at: null,
  region: "co-boyaca-cundinamarca",
  default_weights: SIGNAL_DEFAULTS,
  weights_version: "1",
  weights_reasons: {},
  sources: [],
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
const strategy = (rank: number | null, kind: string, crops: string[], total: number) => ({
  rank,
  kind,
  crop_ids: crops,
  total_score: total,
  scores: { water: 70, soil: 80, income: 60, risk: 70 },
  vs_current: null,
  cycles: [],
  soil_health: {},
  issues: [],
  reasons: [],
});
const ROTATIONS = {
  strategies: [
    strategy(1, "suggested", ["avena_vicia", "arveja", "papa"], 76),
    strategy(2, "suggested", ["arveja", "avena_vicia", "papa"], 70),
  ],
  current_strategy: strategy(null, "current", ["papa", "arveja", "papa"], 58),
  excluded: [],
  excluded_counts: { rule: 5, high_risk: 2 },
  weights: START_PRIORITIES,
  soil_basis: "municipality",
  slope_basis: "municipality",
  limitations: ["Suelo estimado para el municipio, no para su lote"],
  versions: { dataset: "ejemplo", rules: "ejemplo" },
};

type Reply = { status: number; body?: unknown };
function fakeApi(extra: Record<string, Reply> = {}) {
  const calls: { key: string; body: unknown }[] = [];
  const replies: Record<string, Reply> = {
    "GET /api/v1/catalogs/municipalities": { status: 200, body: MUNICIPALITIES },
    "GET /api/v1/catalogs/crops": { status: 200, body: CROPS },
    "GET /api/v1/version": { status: 200, body: VERSION },
    "POST /api/v1/rotations": { status: 200, body: ROTATIONS },
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

    expect(await screen.findByText("Encontramos 2 estrategias")).toBeInTheDocument();
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

    expect(screen.getByText("1. Avena con vicia → Arveja → Papa")).toBeInTheDocument();
    expect(screen.getByText(/Su rotación actual:/).parentElement).toHaveTextContent("Papa → Arveja → Papa · 58 de 100");
    expect(screen.getByText("Se descartaron 7 combinaciones que no cumplen las reglas o tienen riesgo alto.")).toBeInTheDocument();
    expect(screen.getByText("Compara estrategias según reglas con fuente. No predice cuánto va a mejorar su suelo.")).toBeInTheDocument();
    expect(screen.getByText("respuesta simulada")).toBeInTheDocument();
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
    await screen.findByText("Encontramos 2 estrategias");
    expect(rotationCalls(calls)[0]).toMatchObject({ municipality_id: "15646", previous_crop_ids: ["papa"], irrigated: false });
  });

  it("la rotación que viene haciendo se envía en orden y es opcional", async () => {
    const calls = fakeApi();
    sessionStorage.setItem("agrosense.area", "2");
    open(`${PATHS.consult}?municipio=15646&siembra=${MONTH}&anterior=ninguno&riego=si`);
    const user = userEvent.setup();
    await screen.findByText("Encontramos 2 estrategias");
    expect(rotationCalls(calls)[0]).toMatchObject({ previous_crop_ids: [], current_crop_ids: null, irrigated: true });

    await user.click(group("¿Qué viene sembrando en este terreno?").getByRole("radio", { name: "Sí, en este orden" }));
    await user.selectOptions(screen.getByLabelText("Primero siembra"), "papa");
    await user.click(screen.getByRole("button", { name: "Ver estrategias" }));
    expect(await screen.findByText(STRATEGY_CURRENT_ERROR)).toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText("Después"), "arveja");
    await user.click(screen.getByRole("button", { name: "Ver estrategias" }));
    await waitFor(() => expect(rotationCalls(calls).at(-1)).toMatchObject({ current_crop_ids: ["papa", "arveja"] }));
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

  it("con las prioridades de la rotación todas en 0 no envía la petición y pide subir una", async () => {
    const calls = fakeApi();
    sessionStorage.setItem("agrosense.area", "2");
    open(`${PATHS.consult}?municipio=15646&siembra=${MONTH}&anterior=ninguno&riego=no`);
    const user = userEvent.setup();
    await screen.findByText("Encontramos 2 estrategias");
    const before = rotationCalls(calls).length;
    await user.click(screen.getByText("¿Qué busca en la rotación? · Ajustar"));
    for (const name of ["Agua", "Suelo", "Ingreso", "Riesgo"]) {
      await user.click(within(screen.getByRole("radiogroup", { name: new RegExp(`^${name}:`) })).getByRole("radio", { name: /^0 de 5/ }));
    }
    expect(await screen.findByText("Todas sus prioridades están en 0. Suba al menos una para comparar estrategias.")).toBeInTheDocument();
    expect(rotationCalls(calls)).toHaveLength(before + 3); // las tres primeras aún tenían alguna en más de 0
  });

  it("un 422 de la API se explica en palabras sencillas", async () => {
    fakeApi({
      "POST /api/v1/rotations": {
        status: 422,
        body: { error: { code: "invalid_input", message: "Hay datos que no son válidos. Revise: cycles.", request_id: "r1" } },
      },
    });
    sessionStorage.setItem("agrosense.area", "2");
    open(`${PATHS.consult}?municipio=15646&siembra=${MONTH}&anterior=ninguno&riego=no`);
    expect(await screen.findByText("Hay un dato que no sirve para consultar. Revise los ciclos.")).toBeInTheDocument();
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

    await screen.findByText("Encontramos 2 estrategias");
    expect(rotationCalls(calls)[0]).toMatchObject({
      municipality_id: "25899",
      previous_crop_ids: ["arveja"],
      current_crop_ids: ["papa", "arveja"],
      irrigated: true,
      lot_id: "a1",
    });
  });

  it("un lote en la dirección sin sesión no se consulta y lo dice", async () => {
    const calls = fakeApi();
    open(`${PATHS.consult}?lote=a1&siembra=${MONTH}`);
    expect(await screen.findByText(/Ese lote no está entre los suyos/)).toBeInTheDocument();
    expect(rotationCalls(calls)).toHaveLength(0);
  });
});
