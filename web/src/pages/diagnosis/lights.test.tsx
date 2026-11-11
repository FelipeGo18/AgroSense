import { render, screen, within } from "@testing-library/react";
import { RouterProvider, createMemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { PATHS } from "@/app/paths";
import { routes } from "@/app/routes";
import { sowingMonths } from "@/features/diagnosis/consult";
import { countsAlways, strategiesLink, whyDifferent } from "@/features/diagnosis/lights";
import type { Signal } from "@/features/diagnosis/signals";
import { setLightMode } from "@/lib/lightMode";

// Datos de ejemplo de las pruebas (R5): pesos, señales y respuesta de muestra.
const MONTH = sowingMonths()[0].value;
const DEFAULTS = { water: 3, frost: 3, heat: 3, soil: 2, supply: 2, market: 1 };
const MINE = { ...DEFAULTS, frost: 0, supply: 0 };
const base = { critical: false, counts: true, indicators: [], reasons: [] };
const SIGNALS = {
  water: { ...base, status: "available", level: "favorable", score: 80 },
  frost: { ...base, status: "available", level: "unfavorable", critical: true, score: 12, counts: true },
  heat: { ...base, status: "available", level: "favorable", score: 90 },
  soil: { ...base, status: "available", level: "favorable", score: 75 },
  supply: { ...base, status: "available", level: "unfavorable", score: 25, counts: false },
  market: { ...base, status: "insufficient_data" },
};
const light = (light: string, action: string, limiting: string | null, reasons: string[]) => ({
  light,
  action,
  high_risk: false,
  weights_basis: "farmer",
  limiting_signal: limiting,
  reasons,
});
const DIFFERENT = {
  request: { municipality_id: "15646", crop_id: "papa", sowing_date: `${MONTH}-01`, irrigated: false, lot_id: null },
  suitability: { level: "suitable", score: 90, basis: "municipality", reasons: [] },
  window: null,
  overall: light("red", "other_window", "frost", ["La helada grave pone la luz en rojo, aunque usted le puso 0"]),
  overall_default: {
    ...light("yellow", "rotate", "supply", ["Con el criterio de AgroSense, la oferta desfavorable pone la luz en amarillo"]),
    weights_basis: "default",
  },
  weights: MINE,
  signals: SIGNALS,
  limitations: [],
  versions: { dataset: "2026.11.0", rules: "1.0.0" },
};
const SAME = {
  ...DIFFERENT,
  overall: light("green", "sow", "water", ["Ninguna señal que cuenta es desfavorable"]),
  overall_default: { ...light("green", "sow", "water", []), weights_basis: "default" },
  weights: DEFAULTS,
  signals: { ...SIGNALS, frost: { ...SIGNALS.frost, level: "favorable", critical: false, score: 85 } },
};
const VERSION = {
  dataset_version: "2026.11.0",
  rules_version: "1.0.0",
  created_at: null,
  region: "co-boyaca-cundinamarca",
  default_weights: DEFAULTS,
  weights_version: "1",
  weights_reasons: {},
  sources: [],
};

function fakeApi(response: unknown) {
  const replies: Record<string, unknown> = {
    "GET /api/v1/catalogs/municipalities": [{ municipality_id: "15646", name: "Samacá", department: "Boyacá", lat: 5.49, lon: -73.49 }],
    "GET /api/v1/catalogs/crops": [{ crop_id: "papa", name_es: "Papa", kind: "crop", archetype: null, family: null, cycle_months: 5 }],
    "GET /api/v1/version": VERSION,
    "POST /api/v1/diagnostics": response,
  };
  vi.stubGlobal("fetch", async (url: string, init: RequestInit = {}) => {
    const key = `${init.method ?? "GET"} ${url}`;
    if (key in replies) return new Response(JSON.stringify(replies[key]), { status: 200 });
    return new Response(JSON.stringify({ error: { code: "unauthorized", message: "No." } }), { status: 401 });
  });
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

describe("Dos luces: reglas (HU-203)", () => {
  it("dice por qué difieren las luces con los pesos que la persona cambió", () => {
    expect(whyDifferent(MINE, DEFAULTS)).toBe("Usted puso las heladas en 0 (AgroSense: 3) y la oferta en 0 (AgroSense: 2).");
    expect(whyDifferent({ ...DEFAULTS, supply: 0 }, DEFAULTS)).toBe("Usted puso la oferta en 0 (AgroSense: 2).");
    expect(whyDifferent(MINE, null)).toBe("Las luces difieren porque usted usa sus propias prioridades.");
  });

  it("solo un riesgo grave de clima con peso 0 «cuenta siempre»", () => {
    const grave = SIGNALS.frost as Signal;
    expect(countsAlways("frost", grave, MINE)).toBe(true);
    expect(countsAlways("frost", grave, DEFAULTS)).toBe(false); // con peso, cuenta como cualquiera
    expect(countsAlways("frost", { ...grave, critical: false }, MINE)).toBe(false);
    // La oferta puede ser crítica, pero no es un riesgo de clima: con peso 0 no cuenta.
    expect(countsAlways("supply", { ...grave, counts: true } as Signal, MINE)).toBe(false);
  });

  it("el camino a las estrategias lleva el municipio (o el lote), la fecha y el cultivo como anterior", () => {
    expect(strategiesLink(DIFFERENT.request)).toBe(`${PATHS.consult}?municipio=15646&siembra=${MONTH}&anterior=papa&riego=no`);
    expect(strategiesLink({ ...DIFFERENT.request, lot_id: "a1", irrigated: null })).toBe(
      `${PATHS.consult}?lote=a1&siembra=${MONTH}&anterior=papa`,
    );
  });
});

describe("Dos luces en la pantalla (HU-203)", () => {
  it("si las luces son iguales se ve una sola", async () => {
    fakeApi(SAME);
    open();
    expect(await screen.findByText("Puede sembrar en esa fecha")).toBeInTheDocument();
    expect(screen.getAllByText("Luz verde")).toHaveLength(1);
    expect(screen.queryByText(/Con sus prioridades:/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Con el criterio de AgroSense:/)).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Ver estrategias de rotación" })).not.toBeInTheDocument();
    expect(screen.getByText("Es información para decidir. La decisión es suya.")).toBeInTheDocument();
  });

  it("si difieren se ven las dos con su acción y lo que más limita, la suya primero, y por qué difieren", async () => {
    fakeApi(DIFFERENT);
    open();
    const mine = await screen.findByRole("region", { name: "Con sus prioridades" });
    const agrosense = screen.getByRole("region", { name: "Con el criterio de AgroSense" });
    expect(mine.compareDocumentPosition(agrosense) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();

    expect(within(mine).getByText("Con sus prioridades: Mejor busque otra fecha de siembra")).toBeInTheDocument();
    expect(within(mine).getByText("Luz roja")).toBeInTheDocument();
    expect(within(mine).getByText("Lo que más limita:").parentElement).toHaveTextContent("Lo que más limita: Heladas");
    expect(within(agrosense).getByText("Con el criterio de AgroSense: Mejor siembre otro cultivo")).toBeInTheDocument();
    expect(within(agrosense).getByText("Luz amarilla")).toBeInTheDocument();
    expect(within(agrosense).getByText("Lo que más limita:").parentElement).toHaveTextContent("Lo que más limita: Oferta");

    expect(await screen.findByText("Usted puso las heladas en 0 (AgroSense: 3) y la oferta en 0 (AgroSense: 2).")).toBeInTheDocument();
    expect(screen.getByText("Es información para decidir. La decisión es suya.")).toBeInTheDocument();
  });

  it("con «rotar» en cualquiera de las dos luces lleva a las estrategias con el municipio, la fecha y el cultivo anterior", async () => {
    fakeApi(DIFFERENT);
    open();
    const link = await screen.findByRole("link", { name: "Ver estrategias de rotación" });
    expect(link).toHaveAttribute("href", `${PATHS.consult}?municipio=15646&siembra=${MONTH}&anterior=papa&riego=no`);
  });

  it("una señal que no cuenta se sigue viendo con su rótulo, y un riesgo grave de clima con peso 0 dice que cuenta siempre", async () => {
    fakeApi(DIFFERENT);
    open();
    await screen.findByRole("heading", { level: 2, name: "Las señales de esta ventana" });
    expect(within(card("Oferta")).getByText("No cuenta para la luz con sus prioridades")).toBeInTheDocument();
    expect(within(card("Oferta")).getByText("Desfavorable")).toBeInTheDocument(); // se sigue viendo
    expect(within(card("Heladas")).getByText("Cuenta siempre: riesgo grave")).toBeInTheDocument();
    expect(within(card("Agua")).queryByText(/Cuenta siempre|No cuenta/)).not.toBeInTheDocument();
  });

  it("en modo ligero se ven las dos luces", async () => {
    setLightMode(true);
    fakeApi(DIFFERENT);
    open();
    expect(await screen.findByRole("region", { name: "Con sus prioridades" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Con el criterio de AgroSense" })).toBeInTheDocument();
  });
});
