import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RouterProvider, createMemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { PATHS } from "@/app/paths";
import { routes } from "@/app/routes";
import { sowingMonths } from "@/features/diagnosis/consult";
import type { WaterSeries } from "@/features/diagnosis/trends";
import { setLightMode } from "@/lib/lightMode";
import { WaterChart, waterTitle } from "./WaterChart";

// Datos de ejemplo (R5): diez años de lluvia de la ventana; en 2018, 2019 y 2022 no alcanzó y 2017 no tiene dato.
const SERIES: WaterSeries = {
  status: "available",
  source_id: "imerg",
  unit: "mm",
  points: [
    [2015, 470, 430],
    [2016, 505, 432],
    [2017, null, 428],
    [2018, 360, 435],
    [2019, 385, 431],
    [2020, 540, 429],
    [2021, 495, 433],
    [2022, 350, 436],
    [2023, 455, 430],
    [2024, 448, 434],
  ].map(([year, precip_mm, need_mm]) => ({ year: year as number, precip_mm, need_mm })),
};
const VERSION = {
  dataset_version: "ejemplo",
  rules_version: "ejemplo",
  created_at: null,
  region: null,
  default_weights: {},
  weights_version: "1",
  weights_reasons: {},
  sources: [],
};

const chart = (props: Partial<Parameters<typeof WaterChart>[0]> = {}) =>
  render(<WaterChart series={SERIES} status="success" cropName="Papa" from="2027-08-02" to="2027-12-27" version={VERSION} {...props} />);

afterEach(() => {
  vi.unstubAllGlobals();
  setLightMode(false);
});

describe("Gráfica de la lluvia de la ventana (HU-093)", () => {
  it("el título dice los meses de la ventana, el cultivo y la unidad", () => {
    expect(waterTitle("Papa", "2027-08-02", "2027-12-27")).toBe("Lluvia de ago a dic frente a lo que necesita el cultivo (papa), en mm");
    expect(waterTitle("Papa", null, null)).toBe("Lluvia de la ventana frente a lo que necesita el cultivo (papa), en mm");
  });

  it("por año, la lluvia frente a lo que necesita, con el periodo, la fuente y los años en que no alcanzó", () => {
    chart();
    expect(screen.getByRole("img", { name: /años 2015–2024\. La lluvia no alcanzó en 3 de 9 años/ })).toBeInTheDocument();
    expect(screen.getByText("Años en que la lluvia no alcanzó: 3 de 9")).toBeInTheDocument();
    const note = screen.getByText(/^Años 2015–2024/);
    expect(note).toHaveTextContent("Lluvia: GPM IMERG (NASA y JAXA)");
    expect(note).toHaveTextContent("Es la historia de la zona, no un pronóstico.");
    // Una barra por año con dato: el año sin dato no tiene barra (R1), y los que no alcanzaron van punteados.
    const svg = screen.getByRole("img", { name: /Lluvia de ago a dic/ });
    const bars = svg.querySelectorAll("rect[rx]");
    expect(bars).toHaveLength(9);
    expect([...bars].filter((bar) => bar.getAttribute("stroke-dasharray"))).toHaveLength(3);
  });

  it("se puede leer en una tabla y cada año dice sus cifras al tocarlo", async () => {
    chart();
    const table = within(screen.getByRole("table"));
    expect(table.getByRole("row", { name: "2017 Sin dato 428 mm" })).toBeInTheDocument();
    expect(table.getByRole("row", { name: "2022 350 mm 436 mm" })).toBeInTheDocument();
    const user = userEvent.setup();
    const svg = screen.getByRole("img", { name: /Lluvia de ago a dic/ });
    const zones = svg.querySelectorAll('rect[fill="transparent"]');
    await user.click(zones[7]);
    expect(screen.getByText("2022: llovieron 350 mm; necesitaba 436 mm.")).toBeInTheDocument();
  });

  it("sin datos, dice «sin datos» en vez de una gráfica en cero (R1)", () => {
    chart({ series: { status: "insufficient_data", source_id: "imerg", unit: "mm", points: [] } });
    expect(screen.getByText(/Sin datos suficientes de la lluvia de esta ventana año por año/)).toBeInTheDocument();
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
  });

  it("un valor que no viene en la respuesta es «sin dato», no un cero", () => {
    const missing = { ...SERIES, points: SERIES.points.map((p) => (p.year === 2017 ? { year: 2017, need_mm: 428 } : p)) };
    chart({ series: missing as WaterSeries });
    expect(screen.getByText("Años en que la lluvia no alcanzó: 3 de 9")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: /Lluvia de ago a dic/ }).querySelectorAll("rect[rx]")).toHaveLength(9);
  });

  it("mientras carga o si falla, lo dice", () => {
    const { unmount } = chart({ status: "pending", series: undefined });
    expect(screen.getByRole("status")).toHaveTextContent("Cargando la lluvia año por año…");
    unmount();
    chart({ status: "error", series: undefined });
    expect(screen.getByText("No pudimos cargar la lluvia año por año. Intente más tarde.")).toBeInTheDocument();
  });
});

describe("La gráfica en el diagnóstico (HU-093)", () => {
  it("va dentro de la señal de agua, con la serie de GET /trends de la misma ventana", async () => {
    const month = sowingMonths()[0].value;
    const signal = (level: string, score: number) => ({
      status: "available",
      level,
      critical: false,
      score,
      counts: true,
      indicators: [],
      reasons: [],
    });
    const response = {
      request: { municipality_id: "15646", crop_id: "papa", sowing_date: `${month}-01`, irrigated: false, lot_id: null },
      suitability: { level: "suitable", score: 92, basis: "municipality", reasons: [] },
      window: { sowing_start: `${month}-01`, harvest_estimate: `${month}-28`, harvest_basis: "calendar", supply_semester: null },
      overall: { light: "green", action: "sow", high_risk: false, weights_basis: "default", limiting_signal: null, reasons: [] },
      overall_default: { light: "green", action: "sow", high_risk: false, weights_basis: "default", limiting_signal: null, reasons: [] },
      weights: { water: 3, frost: 3, heat: 3, soil: 3, supply: 3, market: 3 },
      signals: { water: signal("favorable", 86), frost: signal("favorable", 80) },
      limitations: [],
      versions: { dataset: "ejemplo", rules: "ejemplo" },
    };
    const calls: string[] = [];
    const replies: Record<string, unknown> = {
      "GET /api/v1/catalogs/municipalities": [{ municipality_id: "15646", name: "Samacá", department: "Boyacá", lat: 5.49, lon: -73.49 }],
      "GET /api/v1/catalogs/crops": [
        { crop_id: "papa", name_es: "Papa", kind: "crop", archetype: "tuber", family: "solanaceae", cycle_months: 5.4 },
      ],
      "GET /api/v1/version": VERSION,
      "POST /api/v1/diagnostics": response,
      [`GET /api/v1/trends?municipality_id=15646&crop_id=papa&sowing_date=${month}-01`]: {
        request: {},
        water: SERIES,
        supply: { status: "insufficient_data", source_id: "eva", unit: "ha", semester: null, points: [] },
        ndvi: { status: "insufficient_data", source_id: null, quality: null, points: [] },
        versions: { dataset: "ejemplo", rules: "ejemplo" },
      },
    };
    vi.stubGlobal("fetch", async (url: string, init: RequestInit = {}) => {
      const key = `${init.method ?? "GET"} ${url}`;
      calls.push(key);
      return key in replies
        ? new Response(JSON.stringify(replies[key]), { status: 200 })
        : new Response(JSON.stringify({ error: { code: "unauthorized", message: "No." } }), { status: 401 });
    });
    render(
      <RouterProvider
        router={createMemoryRouter(routes, {
          initialEntries: [`${PATHS.diagnosis}?municipio=15646&cultivo=papa&siembra=${month}&riego=no`],
        })}
      />,
    );
    const water = (await screen.findByRole("heading", { level: 3, name: "Agua" })).closest("li") as HTMLElement;
    expect(await within(water).findByText("Años en que la lluvia no alcanzó: 3 de 9")).toBeInTheDocument();
    expect(within(water).getByText(/frente a lo que necesita el cultivo \(papa\), en mm/)).toBeInTheDocument();
    // Solo la señal de agua la lleva.
    const frost = screen.getByRole("heading", { level: 3, name: "Heladas" }).closest("li") as HTMLElement;
    expect(within(frost).queryByText(/Lluvia de/)).not.toBeInTheDocument();
    expect(calls.filter((call) => call.startsWith("GET /api/v1/trends"))).toHaveLength(1);
  });
});
