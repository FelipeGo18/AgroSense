import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { SoilDetails } from "./SoilDetails";

// Propiedades de EJEMPLO con la forma del detalle del lote (R5).
const SOIL = {
  basis: "lot",
  ph: 5.75,
  ph_p05: 4.08,
  ph_p95: 7.9,
  soc_g_kg: 28,
  soc_p05: null,
  soc_p95: null,
  texture_class: "arenoso",
  quality: "partial",
};
function open(body: unknown, status = 200) {
  const fetch = vi.fn(async () => new Response(JSON.stringify(body), { status }));
  vi.stubGlobal("fetch", fetch);
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <SoilDetails municipalityId="15646" lotId="lote" />
    </QueryClientProvider>,
  );
  return fetch;
}
afterEach(() => vi.unstubAllGlobals());

describe("Suelo explicado del contexto del cálculo (HU-185)", () => {
  it("muestra las propiedades del polígono con precisión, incertidumbre y advertencia, sin pedir el municipio", async () => {
    const fetch = open({ soil: SOIL });
    expect(await screen.findByText("5,75")).not.toBeVisible();
    await userEvent.click(screen.getByText("Ver el suelo usado y qué significa"));
    expect(await screen.findByText("5,75")).toBeVisible();
    expect(screen.getByText("rango probable de 4,08 a 7,9")).toBeVisible();
    expect(screen.getByText("28 g/kg")).toBeVisible();
    expect(screen.getByText("Guarda poca agua")).toBeVisible();
    expect(screen.getByText(/Es el suelo de su lote dibujado/)).toHaveTextContent("Un análisis de suelo de su lote es más preciso");
    expect(screen.getByText(/la estimación es menos segura/)).toBeVisible();
    expect(fetch.mock.calls).toHaveLength(1);
  });
  it("sin suelo del lote no sustituye por el municipio ni muestra un riesgo", async () => {
    const fetch = open({ soil: null });
    await userEvent.click(screen.getByText("Ver el suelo usado y qué significa"));
    expect(
      await screen.findByText("Sin datos del suelo de su lote. Para conocer el suelo de su lote, haga un análisis de suelo."),
    ).toBeVisible();
    expect(screen.queryByText(/Estimación de un mapa global/)).not.toBeInTheDocument();
    expect(screen.queryByText("Bajo")).not.toBeInTheDocument();
    expect(fetch.mock.calls).toHaveLength(1);
  });
  it("un fallo permite reintentar y recuperar los datos", async () => {
    const fetch = open({ error: { code: "dataset_unavailable", message: "No disponible" } }, 503);
    await userEvent.click(screen.getByText("Ver el suelo usado y qué significa"));
    expect(await screen.findByRole("alert")).toHaveTextContent("No se pudieron cargar");
    fetch.mockImplementation(async () => new Response(JSON.stringify({ soil: { ...SOIL, basis: "municipality" } }), { status: 200 }));
    await userEvent.click(screen.getByRole("button", { name: "Reintentar" }));
    await waitFor(() => expect(screen.getByText(/Es el suelo de su municipio/)).toBeVisible());
  });
});
