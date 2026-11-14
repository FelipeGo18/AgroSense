import { render, screen, within } from "@testing-library/react";
import { RouterProvider, createMemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { PATHS } from "@/app/paths";
import { routes } from "@/app/routes";
import { setLightMode } from "@/lib/lightMode";
import { NEVER, STEPS } from "./content";
import { splitSources } from "./HowItWorksPage";

// Respuesta DE EJEMPLO de GET /version (R5): la forma del contrato, con dos fuentes reales del dataset.
const VERSION = {
  dataset_version: "2026.11.17",
  rules_version: "0.1.0",
  created_at: "2026-11-14T18:09:36Z",
  region: "Boyacá y Cundinamarca, Colombia",
  default_weights: { water: 3, frost: 4, heat: 2, soil: 2, supply: 1, market: 1 },
  weights_version: "1.0.0",
  weights_reasons: { frost: "Las heladas dañan la cosecha en el altiplano." },
  sources: [
    {
      source_id: "nasa_power",
      name: "NASA POWER · Datos diarios por punto (comunidad AG)",
      institution: "NASA Langley Research Center, proyecto POWER",
      url: "https://power.larc.nasa.gov/",
      coverage: "Mundial",
      period_covered: "1981 a hoy",
      license: "La página de POWER no da una licencia; pide citar la fuente",
    },
    {
      source_id: "dane_divipola",
      name: "DIVIPOLA- Códigos municipios",
      institution: "Departamento Administrativo Nacional de Estadística (DANE)",
      url: null,
      coverage: "Colombia",
      period_covered: null,
      license: null,
    },
  ],
};

const respond = (version: unknown, status = 200) =>
  vi.stubGlobal("fetch", async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.includes("/version")) return new Response(JSON.stringify(version), { status });
    return new Response(JSON.stringify({ error: { code: "unauthorized", message: "x" } }), { status: 401 });
  });

const open = () => render(<RouterProvider router={createMemoryRouter(routes, { initialEntries: [PATHS.howItWorks] })} />);

afterEach(() => {
  vi.unstubAllGlobals();
  setLightMode(false);
});

describe("¿Cómo funciona? (HU-122, HU-198)", () => {
  it("explica cómo se decide y lo que AgroSense no hace", async () => {
    respond(VERSION);
    open();
    expect(await screen.findByRole("heading", { level: 1, name: "¿Cómo funciona?" })).toBeInTheDocument();
    for (const step of STEPS) expect(screen.getByRole("heading", { level: 3, name: step.title })).toBeInTheDocument();
    for (const item of NEVER) expect(screen.getByText(item)).toBeInTheDocument();
    expect(screen.getByText(/No es un pronóstico/)).toBeInTheDocument();
  });

  it("muestra los pesos por defecto de /version con su porqué y su versión", async () => {
    respond(VERSION);
    open();
    const weights = await screen.findByRole("region", { name: "Pesos por defecto" });
    const frost = within(weights).getByText("Heladas").closest("li")!;
    expect(within(frost).getByText("4 de 5")).toBeInTheDocument();
    expect(within(within(weights).getByText("Agua").closest("li")!).getByText("3 de 5")).toBeInTheDocument();
    expect(within(weights).getByText("Las heladas dañan la cosecha en el altiplano.")).toBeInTheDocument();
    expect(within(weights).getByText(/versión 1.0.0/)).toBeInTheDocument();
  });

  it("lista las fuentes con su licencia, la NASA primero, y la versión de los datos", async () => {
    respond(VERSION);
    open();
    const sources = await screen.findByRole("region", { name: "Fuentes y versión" });
    expect(within(sources).getByText(/Datos 2026.11.17 · Reglas 0.1.0 · Región: Boyacá y Cundinamarca/)).toBeInTheDocument();
    expect(within(sources).getByRole("link", { name: /NASA POWER/ })).toHaveAttribute("href", "https://power.larc.nasa.gov/");
    expect(within(sources).getByText(/reanálisis/)).toBeInTheDocument();
    // Sin licencia publicada no se inventa una: se dice cómo se usa (R5, R8).
    expect(within(sources).getByText(/Sin licencia explícita: se usan cifras con su cita/)).toBeInTheDocument();
  });

  it("sin dataset publicado no inventa fuentes", async () => {
    respond({ ...VERSION, dataset_version: null, rules_version: null, region: null, sources: [] });
    open();
    expect(await screen.findByText("Sin fuentes publicadas")).toBeInTheDocument();
    expect(screen.getByText(/Sin dataset publicado/)).toBeInTheDocument();
  });

  it("si el servidor no responde, lo dice y deja reintentar", async () => {
    respond({ error: { code: "internal_error", message: "x" } }, 500);
    open();
    expect(await screen.findByText("No pudimos cargar las fuentes")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Volver a intentar" })).toBeInTheDocument();
  });

  it("en modo ligero se ve completa", async () => {
    setLightMode(true);
    respond(VERSION);
    open();
    expect(await screen.findByRole("region", { name: "Fuentes y versión" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 2, name: "Cómo se decide" })).toBeInTheDocument();
  });

  it("separa los productos de la NASA de las demás fuentes", () => {
    const { nasa, others } = splitSources(VERSION.sources);
    expect(nasa.map((s) => s.source_id)).toEqual(["nasa_power"]);
    expect(others.map((s) => s.source_id)).toEqual(["dane_divipola"]);
  });
});
