import { render, screen } from "@testing-library/react";
import { RouterProvider, createMemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { PATHS } from "@/app/paths";
import { routes } from "@/app/routes";
import { setLightMode } from "@/lib/lightMode";

beforeEach(() => {
  vi.stubGlobal("fetch", () => Promise.reject(new Error("sin red en las pruebas")));
  setLightMode(true);
});
afterEach(() => {
  vi.unstubAllGlobals();
  setLightMode(false);
});

const open = (path: string) => render(<RouterProvider router={createMemoryRouter(routes, { initialEntries: [path] })} />);

// El pie de página va en todas las pantallas (specs/05-frontend.md): también en la de una dirección que no existe y en la
// de «Qué cambió», aunque todavía no se haya elegido el contexto o falle la carga de catálogos.
describe("Pie de página en las pantallas de aviso", () => {
  it("la dirección que no existe lleva el pie", async () => {
    open("/ruta-que-no-existe");
    expect(await screen.findByRole("heading", { name: "Esta dirección no existe" })).toBeInTheDocument();
    expect(screen.getByRole("contentinfo")).toBeInTheDocument();
  });

  it("la pantalla de qué cambió lleva el pie aunque no carguen los catálogos (HU-219)", async () => {
    open(PATHS.changes);
    expect(await screen.findByRole("heading", { level: 1, name: "¿Qué cambió en su zona?" })).toBeInTheDocument();
    expect(screen.queryByText(/todavía no está programada/)).not.toBeInTheDocument();
    expect(screen.getByRole("contentinfo")).toBeInTheDocument();
  });
});
