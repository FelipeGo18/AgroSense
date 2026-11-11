import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RouterProvider, createMemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { PATHS } from "@/app/paths";
import { routes } from "@/app/routes";
import { sowingMonths } from "@/features/diagnosis/consult";
import { otherCropLink, seedsFor, suitabilityFacts, windowLink, type Suitability } from "@/features/diagnosis/windows";
import { setLightMode } from "@/lib/lightMode";

// Datos de ejemplo de las pruebas (R5): catálogo, ventanas y respuestas de muestra.
const MONTHS = sowingMonths();
const MONTH = MONTHS[0].value;
const REQUEST = { municipality_id: "15646", crop_id: "papa", sowing_date: `${MONTH}-01`, irrigated: false, lot_id: null };
const light = (light: string, action: string) => ({
  light,
  action,
  high_risk: false,
  weights_basis: "default",
  limiting_signal: null,
  reasons: [],
});
const BASE = {
  request: REQUEST,
  suitability: { level: "suitable", score: 92, basis: "municipality", tmean_annual_c: 12.8, altitude_m: 2660, reasons: [] },
  window: { sowing_start: `${MONTH}-01`, harvest_estimate: `${MONTHS[5].value}-15`, harvest_basis: "calendar", supply_semester: null },
  overall: light("green", "sow"),
  overall_default: light("green", "sow"),
  weights: {},
  signals: null,
  limitations: [],
  versions: { dataset: "2026.11.0", rules: "1.0.0" },
};
const NOT_SUITABLE = {
  ...BASE,
  suitability: {
    level: "not_suitable",
    score: 12,
    basis: "municipality",
    tmean_annual_c: 26.3,
    altitude_m: 300,
    reasons: ["La temperatura media anual (26,3 °C) pasa del máximo de la papa (16 °C). Fuente: ficha del cultivo, UPRA"],
  },
  window: null,
  overall: light("red", "rotate"),
  overall_default: light("red", "rotate"),
  limitations: ["Sin ventanas ni señales: el cultivo no es apto para la zona"],
};
const WINDOWS = [
  {
    sowing_start: `${MONTHS[3].value}-01`,
    harvest_estimate: `${MONTHS[8].value}-10`,
    limiting_signal: "water",
    limiting_score: 74,
    weighted_score: 81,
    high_risk: false,
  },
  {
    sowing_start: `${MONTHS[6].value}-01`,
    harvest_estimate: `${MONTHS[11].value}-20`,
    limiting_signal: null,
    limiting_score: 66,
    weighted_score: null,
    high_risk: false,
  },
];
const OTHER_WINDOW = {
  ...BASE,
  overall: light("red", "other_window"),
  overall_default: light("red", "other_window"),
  best_windows: WINDOWS,
};

function fakeApi(response: unknown) {
  const calls: { key: string; body: unknown }[] = [];
  const replies: Record<string, unknown> = {
    "GET /api/v1/catalogs/municipalities": [{ municipality_id: "15646", name: "Samacá", department: "Boyacá", lat: 5.49, lon: -73.49 }],
    "GET /api/v1/catalogs/crops": [
      { crop_id: "papa", name_es: "Papa", kind: "crop", archetype: null, family: null, cycle_months: 5 },
      { crop_id: "arveja", name_es: "Arveja", kind: "crop", archetype: null, family: null, cycle_months: 4 },
    ],
    "POST /api/v1/diagnostics": response,
  };
  vi.stubGlobal("fetch", async (url: string, init: RequestInit = {}) => {
    const key = `${init.method ?? "GET"} ${url}`;
    calls.push({ key, body: init.body ? JSON.parse(String(init.body)) : undefined });
    if (key in replies) return new Response(JSON.stringify(replies[key]), { status: 200 });
    return new Response(JSON.stringify({ error: { code: "unauthorized", message: "No." } }), { status: 401 });
  });
  return calls;
}
function open() {
  const router = createMemoryRouter(routes, {
    initialEntries: [`${PATHS.diagnosis}?municipio=15646&cultivo=papa&siembra=${MONTH}&riego=no`],
  });
  render(<RouterProvider router={router} />);
  return router;
}

afterEach(() => {
  vi.unstubAllGlobals();
  setLightMode(false);
});

describe("Aptitud y ventanas: reglas (HU-194)", () => {
  it("la nota de aptitud va en cinco semillas, una por cada 20 puntos, y sin nota no hay semillas (R1)", () => {
    expect(seedsFor(92)).toBe(5);
    expect(seedsFor(50)).toBe(3);
    expect(seedsFor(12)).toBe(1);
    expect(seedsFor(0)).toBe(0);
    expect(seedsFor(null)).toBeNull();
    expect(seedsFor(undefined)).toBeNull();
  });

  it("dice con qué dato se decidió la aptitud: la temperatura media anual (decisión 13)", () => {
    expect(suitabilityFacts(NOT_SUITABLE.suitability as Suitability)).toBe(
      "Temperatura media anual de 26,3 °C a 300 m de altitud, la del municipio.",
    );
    expect(suitabilityFacts({ ...NOT_SUITABLE.suitability, basis: "lot" } as Suitability)).toMatch(/la de su lote\.$/);
    expect(suitabilityFacts({ ...NOT_SUITABLE.suitability, tmean_annual_c: null } as Suitability)).toBeNull();
  });

  it("tocar una ventana consulta esa fecha y «Elegir otro cultivo» deja la consulta sin cultivo", () => {
    expect(windowLink(REQUEST, `${MONTHS[3].value}-01`)).toBe(
      `${PATHS.diagnosis}?municipio=15646&cultivo=papa&siembra=${MONTHS[3].value}&riego=no`,
    );
    expect(otherCropLink(REQUEST)).toBe(`${PATHS.diagnosis}?municipio=15646&siembra=${MONTH}&riego=no`);
    expect(otherCropLink({ ...REQUEST, lot_id: "a1" })).toBe(`${PATHS.diagnosis}?lote=a1&siembra=${MONTH}`);
  });
});

describe("Cultivo no apto (HU-194)", () => {
  it("lo dice con su nota, sus semillas, el dato y la razón con su fuente, sin semáforo, señales ni ventana", async () => {
    fakeApi(NOT_SUITABLE);
    open();
    expect(await screen.findByText("Este cultivo no se da en su zona")).toBeInTheDocument();
    expect(screen.getByText(/Aptitud de la zona para este cultivo:/)).toHaveTextContent("12 de 100");
    expect(screen.getByRole("img", { name: "1 de 5 semillas" })).toBeInTheDocument();
    expect(screen.getByText("Temperatura media anual de 26,3 °C a 300 m de altitud, la del municipio.")).toBeInTheDocument();
    expect(screen.getByText(/Fuente: ficha del cultivo, UPRA/)).toBeInTheDocument();
    expect(screen.queryByText(/^Luz /)).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Las señales de esta ventana" })).not.toBeInTheDocument();
    // La ventana del resultado no se dibuja (la ayuda del formulario también dice «cosecha estimada»).
    expect(within(screen.getByRole("region", { name: /^Resultado para/ })).queryByText(/cosecha estimada/)).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Ver estrategias de rotación" })).toHaveAttribute(
      "href",
      `${PATHS.consult}?municipio=15646&siembra=${MONTH}&anterior=papa&riego=no`,
    );
  });

  it("«Elegir otro cultivo» deja el formulario listo para elegir otro", async () => {
    fakeApi(NOT_SUITABLE);
    const router = open();
    const user = userEvent.setup();
    await user.click(await screen.findByRole("link", { name: "Elegir otro cultivo" }));
    await waitFor(() => expect(router.state.location.search).toBe(`?municipio=15646&siembra=${MONTH}&riego=no`));
    expect(screen.getByLabelText("Cultivo")).toHaveValue("");
    expect(screen.getByText("Elija un cultivo de la lista.")).toBeInTheDocument();
  });

  it("sin nota de aptitud no dibuja semillas en cero (R1)", async () => {
    fakeApi({ ...NOT_SUITABLE, suitability: { ...NOT_SUITABLE.suitability, score: null } });
    open();
    expect(await screen.findByText("Este cultivo no se da en su zona")).toBeInTheDocument();
    expect(screen.queryByRole("img", { name: /semillas/ })).not.toBeInTheDocument();
    expect(screen.queryByText(/Aptitud de la zona/)).not.toBeInTheDocument();
  });
});

describe("Aptitud en un resultado normal (HU-194)", () => {
  it("con un cultivo apto, la nota va con sus semillas y dice que es informativa", async () => {
    fakeApi(BASE);
    open();
    expect(await screen.findByText("Puede sembrar en esa fecha")).toBeInTheDocument();
    expect(screen.getByText(/Aptitud de la zona para este cultivo:/)).toHaveTextContent("92 de 100");
    expect(screen.getByRole("img", { name: "5 de 5 semillas" })).toBeInTheDocument();
    expect(screen.getByText("Es una nota informativa: no cambia la luz.")).toBeInTheDocument();
  });

  it("con aptitud sin datos, el resultado es normal, la limitación lo dice y no se pinta como riesgo (R1)", async () => {
    fakeApi({
      ...BASE,
      suitability: { level: "insufficient_data", score: null, basis: "municipality", reasons: [] },
      limitations: ["La ficha de la papa no tiene el rango de temperatura media con fuente: no se evaluó la aptitud"],
    });
    open();
    expect(await screen.findByText("Puede sembrar en esa fecha")).toBeInTheDocument();
    expect(screen.getByText("Luz verde")).toBeInTheDocument();
    expect(screen.queryByText("Este cultivo no se da en su zona")).not.toBeInTheDocument();
    expect(screen.queryByRole("img", { name: /semillas/ })).not.toBeInTheDocument();
    expect(screen.getByText(/no se evaluó la aptitud/)).toBeInTheDocument();
  });
});

describe("Mejores ventanas (HU-194)", () => {
  it("con «otra fecha», lista las mejores con su siembra, cosecha, lo que más limita y el promedio, y el rótulo", async () => {
    fakeApi(OTHER_WINDOW);
    open();
    const section = await screen.findByRole("region", { name: "Mejores fechas de los próximos doce meses" });
    const items = within(section).getAllByRole("listitem");
    expect(items).toHaveLength(2);
    expect(items[0]).toHaveTextContent(/Sembrar el/);
    expect(items[0]).toHaveTextContent(/Cosecha estimada el/);
    expect(items[0]).toHaveTextContent("Lo que más limita (Agua): 74 de 100");
    expect(items[0]).toHaveTextContent("Promedio con sus prioridades: 81 de 100");
    // Sin promedio no se inventa uno.
    expect(items[1]).not.toHaveTextContent(/Promedio/);
    expect(within(section).getByText("Según la historia de la zona. No es un pronóstico.")).toBeInTheDocument();
  });

  it("tocar una consulta el diagnóstico de esa fecha, y el formulario la muestra", async () => {
    const calls = fakeApi(OTHER_WINDOW);
    const router = open();
    const user = userEvent.setup();
    const section = await screen.findByRole("region", { name: "Mejores fechas de los próximos doce meses" });
    await user.click(within(section).getAllByRole("link")[0]);
    await waitFor(() => expect(router.state.location.search).toBe(`?municipio=15646&cultivo=papa&siembra=${MONTHS[3].value}&riego=no`));
    await waitFor(() =>
      expect(calls.filter((c) => c.key === "POST /api/v1/diagnostics").at(-1)?.body).toMatchObject({
        sowing_date: `${MONTHS[3].value}-01`,
      }),
    );
    expect(screen.getByLabelText("¿Cuándo quiere sembrar?")).toHaveValue(MONTHS[3].value);
  });

  it("sin ventanas sin riesgo alto lo dice y ofrece las estrategias", async () => {
    fakeApi({ ...OTHER_WINDOW, best_windows: [] });
    open();
    expect(await screen.findByText("En los próximos doce meses no hay una ventana sin riesgo alto.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Ver estrategias de rotación" })).toBeInTheDocument();
  });

  it("si la otra luz dice «rotar», no repite el botón de las estrategias", async () => {
    fakeApi({ ...OTHER_WINDOW, overall_default: light("yellow", "rotate"), best_windows: [] });
    open();
    await screen.findByText("En los próximos doce meses no hay una ventana sin riesgo alto.");
    expect(screen.getAllByRole("link", { name: "Ver estrategias de rotación" })).toHaveLength(1);
  });

  it("sin «otra fecha» en ninguna luz, no hay lista de ventanas", async () => {
    fakeApi({ ...BASE, best_windows: WINDOWS });
    open();
    await screen.findByText("Puede sembrar en esa fecha");
    expect(screen.queryByRole("region", { name: "Mejores fechas de los próximos doce meses" })).not.toBeInTheDocument();
  });

  it("en modo ligero se ve completo", async () => {
    setLightMode(true);
    fakeApi(OTHER_WINDOW);
    open();
    expect(await screen.findByRole("region", { name: "Mejores fechas de los próximos doce meses" })).toBeInTheDocument();
  });
});
