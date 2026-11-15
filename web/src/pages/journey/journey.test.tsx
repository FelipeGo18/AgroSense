import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RouterProvider, createMemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { PATHS } from "@/app/paths";
import { routes } from "@/app/routes";
import { setLightMode } from "@/lib/lightMode";

const open = () => render(<RouterProvider router={createMemoryRouter(routes, { initialEntries: [PATHS.journeyTour] })} />);

describe("Del satélite a su finca (HU-155)", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", async () => new Response(null, { status: 401 }));
    // jsdom no tiene `scrollIntoView`.
    Element.prototype.scrollIntoView = vi.fn();
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    setLightMode(false);
  });

  it("en modo ligero muestra los cuatro niveles con sus textos e ilustraciones 2D, sin escena 3D (HU-158)", async () => {
    setLightMode(true);
    const { container } = open();
    for (const title of ["Desde la órbita", "Boyacá y Cundinamarca", "Su municipio", "Su finca"]) {
      expect(await screen.findByRole("heading", { level: 2, name: title })).toBeInTheDocument();
    }
    expect(container.querySelector("canvas")).toBeNull();
    // Cada nivel con su ilustración del guion y la mascota quieta que dice lo suyo.
    expect(container.querySelectorAll("section svg").length).toBeGreaterThanOrEqual(4);
    expect(screen.getByText("Y llegamos a su lote.")).toBeInTheDocument();
    expect(screen.getByText(/el relieve y la finca son dibujos/)).toBeInTheDocument();
  });

  it("los niveles se recorren tocando: cada botón lleva a su nivel y pone el foco en su título", async () => {
    setLightMode(true);
    open();
    const nav = within(await screen.findByRole("navigation", { name: "Niveles del recorrido" }));
    expect(nav.getAllByRole("button")).toHaveLength(4);
    await userEvent.click(nav.getByRole("button", { name: "4. Finca" }));
    expect(Element.prototype.scrollIntoView).toHaveBeenCalledWith({ behavior: "auto", block: "center" });
    expect(screen.getByRole("heading", { level: 2, name: "Su finca" })).toHaveFocus();
    await userEvent.click(screen.getByRole("button", { name: "Bajar a: Región ↓" }));
    expect(screen.getByRole("heading", { level: 2, name: "Boyacá y Cundinamarca" })).toHaveFocus();
  });

  it("termina invitando a consultar y a ver cómo funciona", async () => {
    setLightMode(true);
    open();
    expect(await screen.findByRole("link", { name: "Consultar sin cuenta" })).toHaveAttribute("href", PATHS.consult);
    expect(screen.getByRole("link", { name: "¿Cómo funciona?" })).toHaveAttribute("href", PATHS.howItWorks);
  });
});
