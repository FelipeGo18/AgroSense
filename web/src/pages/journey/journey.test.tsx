import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RouterProvider, createMemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { PATHS } from "@/app/paths";
import { routes } from "@/app/routes";
import { setLightMode } from "@/lib/lightMode";
import { i18n } from "@/lib/i18n";
import { act } from "@testing-library/react";

// Con movimiento o sin él, según la prueba (en jsdom el motor de animaciones no está y la página sería siempre ligera).
const motion = vi.hoisted(() => ({ animated: false }));
vi.mock("@/hooks/useLightMode", async (original) => ({
  ...(await original<typeof import("@/hooks/useLightMode")>()),
  useAnimated: () => motion.animated,
}));

// En jsdom no hay WebGL: la escena 3D lanza un error al montar, como en un equipo sin WebGL.
vi.mock("./JourneyCanvas", () => ({
  default: () => {
    throw new Error("WebGL no disponible");
  },
}));

const open = () => render(<RouterProvider router={createMemoryRouter(routes, { initialEntries: [PATHS.journeyTour] })} />);

describe("Del satélite a su finca (HU-155)", () => {
  it("cambia los cuatro niveles y sus enlaces al inglés sin recargar (HU-233)", async () => {
    setLightMode(true);
    open();
    await screen.findByRole("heading", { level: 2, name: "Desde la órbita" });
    await act(() => i18n.changeLanguage("en"));
    for (const name of ["From orbit", "Boyacá and Cundinamarca", "Your municipality", "Your farm"]) {
      expect(screen.getByRole("heading", { level: 2, name })).toBeInTheDocument();
    }
    expect(screen.getByRole("navigation", { name: "Journey levels" })).toBeInTheDocument();
    expect(screen.getByText(/not a forecast/)).toBeInTheDocument();
    expect(screen.getByText(/a reanalysis combining/)).toBeInTheDocument();
    expect(screen.getByText(/the terrain and farm are drawings/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Continue without an account" })).toHaveAttribute("href", `${PATHS.consult}?lang=en`);
  });
  beforeEach(() => {
    vi.stubGlobal("fetch", async () => new Response(null, { status: 401 }));
    // jsdom no tiene `scrollIntoView`.
    Element.prototype.scrollIntoView = vi.fn();
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    motion.animated = false;
    setLightMode(false);
  });

  it("en modo ligero muestra los cuatro niveles con sus textos e ilustraciones 2D, sin escena 3D (HU-158)", async () => {
    setLightMode(true);
    const { container } = open();
    for (const title of ["Desde la órbita", "Boyacá y Cundinamarca", "Su municipio", "Su finca"]) {
      expect(await screen.findByRole("heading", { level: 2, name: title })).toBeInTheDocument();
    }
    expect(container.querySelector("canvas")).toBeNull();
    // Cada nivel con su ilustración del guion (una imagen por nivel) y la mascota quieta que dice lo suyo.
    expect(container.querySelectorAll("section img[data-scene]")).toHaveLength(4);
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

  it("si la escena 3D falla (sin WebGL), la página sigue con las ilustraciones 2D en vez de caerse", async () => {
    motion.animated = true;
    const logged = vi.spyOn(console, "error").mockImplementation(() => {});
    const { container } = open();
    expect(await screen.findByRole("heading", { level: 2, name: "Desde la órbita" })).toBeInTheDocument();
    await waitFor(() => expect(container.querySelectorAll("section img[data-scene]")).toHaveLength(4));
    expect(container.querySelector("canvas")).toBeNull();
    expect(screen.getByRole("heading", { level: 2, name: "Su finca" })).toBeInTheDocument();
    // La escena sí se intentó montar (con movimiento) y falló: la barrera lo atrapó.
    expect(logged.mock.calls.some((call) => String(call[0]).includes("WebGL") || String(call[1] ?? "").includes("WebGL"))).toBe(true);
  });

  it("termina invitando a consultar y a ver cómo funciona", async () => {
    setLightMode(true);
    open();
    expect(await screen.findByRole("link", { name: "Consultar sin cuenta" })).toHaveAttribute("href", PATHS.consult);
    expect(screen.getByRole("link", { name: "¿Cómo funciona?" })).toHaveAttribute("href", PATHS.howItWorks);
  });
});
