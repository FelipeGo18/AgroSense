import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RouterProvider, createMemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { PATHS } from "@/app/paths";
import { routes } from "@/app/routes";
import type { MarketPrices, ProductHistory } from "@/features/market/prices";
import { setLightMode } from "@/lib/lightMode";

// Precios de ejemplo para las pruebas, con la forma de la API (HU-221).
const MARKETS = [
  { market_id: "1", name: "Corabastos (Bogotá)" },
  { market_id: "9", name: "Tunja (Complejo de Servicios del Sur)" },
];
const day = (date: string, avg: number) => ({ date, min_cop_kg: avg - 100, avg_cop_kg: avg, max_cop_kg: avg + 100 });

const CORABASTOS: MarketPrices = {
  version: "sipsa-20261021T1505",
  updated_at: "2026-10-21T15:05:00-05:00",
  market: MARKETS[0],
  markets: MARKETS,
  date: "2026-10-19",
  source_id: "dane_sipsa",
  citation: "Fuente: Departamento Administrativo Nacional de Estadística: www.dane.gov.co",
  products: [
    {
      product_id: "papa-negra",
      product: "Papa negra",
      group: "Tubérculos, raíces y plátanos",
      several_varieties: true,
      latest: day("2026-10-19", 2925),
      week_ago: day("2026-10-12", 2750),
      change_pct: 6.4,
    },
    {
      product_id: "frijol-verde",
      product: "Fríjol verde",
      group: "Verduras y hortalizas",
      several_varieties: true,
      latest: day("2026-03-02", 4000),
      week_ago: null,
      change_pct: null,
    },
  ],
};
const TUNJA: MarketPrices = { ...CORABASTOS, market: MARKETS[1], products: [CORABASTOS.products[0]] };

const PAPA: ProductHistory = {
  version: "sipsa-20261021T1505",
  updated_at: "2026-10-21T15:05:00-05:00",
  product_id: "papa-negra",
  product: "Papa negra",
  group: "Tubérculos, raíces y plátanos",
  several_varieties: true,
  market: MARKETS[0],
  latest: day("2026-10-19", 2925),
  days: [day("2026-10-05", 2500), day("2026-10-12", 2750), day("2026-10-19", 2925)],
  season: {
    years: 5,
    first_year: 2021,
    last_year: 2025,
    months: Array.from({ length: 12 }, (_, i) => ({ month: i + 1, seasonal_index: i === 8 ? 0.77 : i === 4 ? 1.18 : 1 })),
  },
  source_id: "dane_sipsa",
  citation: "Fuente: Departamento Administrativo Nacional de Estadística: www.dane.gov.co",
};

const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status });

/** La API de ejemplo: sin sesión, y los precios según la dirección. */
function api(overrides: { prices?: () => Response } = {}) {
  const fetch = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.startsWith("/api/v1/market/prices/papa-negra")) return json(PAPA);
    if (url.startsWith("/api/v1/market/prices")) {
      if (overrides.prices) return overrides.prices();
      return json(url.includes("market_id=9") ? TUNJA : CORABASTOS);
    }
    return json({ error: { code: "unauthorized", message: "x" } }, 401);
  });
  vi.stubGlobal("fetch", fetch);
  return fetch;
}

const open = (path: string = PATHS.prices) => render(<RouterProvider router={createMemoryRouter(routes, { initialEntries: [path] })} />);

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("Precios en la central de abastos (HU-221)", () => {
  it("se ve sin cuenta: el último precio por kilo de cada producto, por grupo, con la fecha y la fuente", async () => {
    api();
    open();
    expect(await screen.findByRole("heading", { level: 1, name: "¿A cuánto se paga en la central?" })).toBeInTheDocument();
    expect(await screen.findByText(/Precios del 19 de octubre de 2026 en Corabastos \(Bogotá\)/)).toBeInTheDocument();
    // La cita textual que piden los términos del DANE (HU-221), tal como la manda la API.
    expect(
      screen.getByText(/Fuente: Departamento Administrativo Nacional de Estadística: www\.dane\.gov\.co\. Datos de SIPSA/),
    ).toBeInTheDocument();
    // Los precios se actualizan con el boletín del DANE (HU-222): la pantalla dice cuándo, en la hora de Colombia.
    expect(
      screen.getByText(/Actualizados del DANE el 21 de octubre(,| a las) 3:05 p\.\s?m\.; se actualizan de lunes a viernes/),
    ).toBeInTheDocument();
    const tubers = screen.getByRole("heading", { level: 2, name: "Tubérculos, raíces y plátanos" }).closest("section")!;
    const papa = within(tubers).getByRole("link", { name: /Papa negra/ });
    expect(papa).toHaveTextContent(/2\.925/);
    // El cambio se dice con palabras, no solo con la flecha.
    expect(papa).toHaveTextContent("Sube 6,4 % en una semana");
  });

  it("un producto sin precio reciente dice de cuándo es su último precio", async () => {
    api();
    open();
    const frijol = await screen.findByRole("link", { name: /Fríjol verde/ });
    expect(frijol).toHaveTextContent("Último precio: 2 de marzo de 2026");
  });

  it("busca sin importar tildes ni mayúsculas", async () => {
    api();
    open();
    await userEvent.type(await screen.findByLabelText("Buscar producto"), "FRIJOL");
    expect(screen.getByRole("link", { name: /Fríjol verde/ })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Papa negra/ })).not.toBeInTheDocument();
  });

  it("cambia de central", async () => {
    const fetch = api();
    open();
    await userEvent.click(await screen.findByRole("radio", { name: "Tunja" }));
    expect(await screen.findByText(/en Tunja \(Complejo de Servicios del Sur\)/)).toBeInTheDocument();
    expect(fetch).toHaveBeenCalledWith("/api/v1/market/prices?market_id=9", expect.anything());
  });

  it("al abrir un producto muestra su último año, sus meses caros y baratos, y que no es un pronóstico", async () => {
    api();
    open(`${PATHS.prices}?producto=papa-negra`);
    expect(await screen.findByRole("heading", { level: 2, name: "Papa negra" })).toBeInTheDocument();
    expect(screen.getByText(/Precio medio más bajo: .*2\.500/)).toBeInTheDocument();
    expect(screen.getByText(/Suele estar más barato en/)).toHaveTextContent("septiembre (-23 %) y más caro en mayo (+18 %)");
    expect(screen.getByRole("note")).toHaveTextContent("No es un pronóstico");
  });

  it("si los precios no están publicados lo dice, sin inventar ninguno", async () => {
    api({
      prices: () =>
        json(
          {
            error: { code: "market_unavailable", message: "Los precios de las centrales de abastos no están disponibles en este momento." },
          },
          503,
        ),
    });
    open();
    expect(await screen.findByRole("alert")).toHaveTextContent("no están disponibles");
    expect(screen.queryByRole("link", { name: /Papa negra/ })).not.toBeInTheDocument();
  });

  it("se ve completa en modo ligero", async () => {
    api();
    setLightMode(true);
    try {
      open(`${PATHS.prices}?producto=papa-negra`);
      expect(await screen.findByRole("heading", { level: 2, name: "Papa negra" })).toBeInTheDocument();
      expect(screen.getByRole("link", { name: /Fríjol verde/ })).toBeInTheDocument();
      expect(screen.getByRole("img", { name: /Precio por kilo del último año/ })).toBeInTheDocument();
    } finally {
      setLightMode(false);
    }
  });
});
