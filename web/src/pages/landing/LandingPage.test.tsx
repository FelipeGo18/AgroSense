import { render, screen, within } from "@testing-library/react";
import { RouterProvider, createMemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import userEvent from "@testing-library/user-event";
import { SOCIAL_LINKS } from "@/app/config";
import { PATHS } from "@/app/paths";
import { routes } from "@/app/routes";
import { setLightMode } from "@/lib/lightMode";

// La portada se prueba como la ve quien pide «reducir movimiento»: sin scroll suave, giro ni vuelo.
beforeEach(() => {
  vi.stubGlobal("matchMedia", (query: string) => ({
    matches: query.includes("prefers-reduced-motion"),
    media: query,
    addEventListener: () => {},
    removeEventListener: () => {},
  }));
  vi.stubGlobal("fetch", () => Promise.reject(new Error("sin red en las pruebas")));
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(null);
});
afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

const open = (path: string) => render(<RouterProvider router={createMemoryRouter(routes, { initialEntries: [path] })} />);

describe("Inicio (HU-173)", () => {
  it("presenta AgroSense y ofrece consultar sin cuenta o entrar", async () => {
    open(PATHS.home);
    expect(await screen.findByRole("heading", { level: 1, name: "AgroSense" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Consultar sin cuenta" })).toHaveAttribute("href", PATHS.consult);
    const main = screen.getByRole("main");
    expect(within(main).getByRole("link", { name: "Entrar" })).toHaveAttribute("href", PATHS.login);
  });

  it("recorre tres paradas, cada una con su título y con lo que dice la mascota", async () => {
    open(PATHS.home);
    for (const title of ["Cuatro preguntas, cuatro respuestas claras", "Así se revisa un ciclo", "De dónde salen los datos"]) {
      expect(await screen.findByRole("heading", { level: 2, name: title })).toBeInTheDocument();
    }
    expect(screen.getByRole("link", { name: /Ver un ejemplo/ })).toHaveAttribute("href", "#ejemplo");
    expect(screen.getByRole("link", { name: /Ver de dónde salen los datos/ })).toHaveAttribute("href", "#fuentes");
    expect(screen.getByRole("link", { name: /Volver arriba/ })).toHaveAttribute("href", "#inicio");
  });

  it("con «reducir movimiento» cada parada tiene su mascota quieta y ninguna vuela", async () => {
    const { container } = open(PATHS.home);
    await screen.findByRole("heading", { level: 1 });
    expect(container.querySelector("[data-mascot-flyer]")).toBeNull();
    expect(container.querySelectorAll("[data-mascot-slot] svg")).toHaveLength(5);
  });

  it("con el modo ligero tampoco hay vuelo ni recorrido, aunque el equipo no pida reducir movimiento", async () => {
    vi.stubGlobal("matchMedia", (query: string) => ({
      matches: false,
      media: query,
      addEventListener: () => {},
      removeEventListener: () => {},
    }));
    setLightMode(true);
    try {
      const { container } = open(PATHS.home);
      await screen.findByRole("heading", { level: 1 });
      expect(container.querySelector("[data-mascot-flyer]")).toBeNull();
      expect(container.querySelectorAll("[data-mascot-slot] svg")).toHaveLength(5);
    } finally {
      setLightMode(false);
    }
  });

  it("rotula el resultado de muestra como ejemplo (R5)", async () => {
    open(PATHS.home);
    const example = (await screen.findByRole("heading", { level: 2, name: "Así se revisa un ciclo" })).closest("section")!;
    expect(within(example).getByText("Ejemplo")).toBeInTheDocument();
    expect(within(example).getByText("Luz amarilla")).toBeInTheDocument();
    expect(within(example).getAllByRole("listitem")).toHaveLength(6);
  });

  it("una señal sin datos dice «Sin datos» y no se pinta como riesgo (R1)", async () => {
    open(PATHS.home);
    const example = (await screen.findByRole("heading", { level: 2, name: "Así se revisa un ciclo" })).closest("section")!;
    const market = within(example).getByText("Mercado").closest("li")!;
    const tag = within(market).getByText("Sin datos").closest("[data-tone]");
    expect(tag).toHaveAttribute("data-tone", "insufficient_data");
  });

  it("dice que no es un pronóstico", async () => {
    open(PATHS.home);
    expect((await screen.findAllByText(/No es un pronóstico/)).length).toBeGreaterThan(0);
  });

  it("el sonido arranca apagado y se prende y se quita con su control", async () => {
    open(PATHS.home);
    const toggle = await screen.findByRole("button", { name: "Sonido" });
    expect(toggle).toHaveAttribute("aria-pressed", "false");
    await userEvent.click(toggle);
    expect(toggle).toHaveAttribute("aria-pressed", "true");
    await userEvent.click(toggle);
    expect(toggle).toHaveAttribute("aria-pressed", "false");
  });

  it("las redes del pie salen de la configuración y llevan a su dirección", async () => {
    open(PATHS.home);
    await screen.findByRole("heading", { level: 1 });
    for (const social of SOCIAL_LINKS) {
      expect(screen.getByRole("link", { name: new RegExp(`^${social.label} del equipo`) })).toHaveAttribute("href", social.href);
    }
  });

  it("no dibuja enlaces sin destino ni a las páginas de prueba", async () => {
    open(PATHS.home);
    await screen.findByRole("heading", { level: 1 });
    const hrefs = screen.getAllByRole("link").map((link) => link.getAttribute("href") ?? "");
    expect(hrefs.every((href) => href.length > 0 && href !== "#")).toBe(true);
    expect(hrefs.some((href) => href.startsWith(PATHS.kit) || href.startsWith("/recorrido") || href.startsWith(PATHS.lab))).toBe(false);
    // «Reportar un problema» es P1 (HU-170): no se dibuja hasta que exista.
    expect(screen.queryByText("Reportar un problema")).toBeNull();
  });
});

describe("rutas", () => {
  it("una pantalla que aún no está programada lo dice y deja volver al inicio", async () => {
    open(PATHS.consult);
    expect(await screen.findByRole("heading", { level: 1, name: "Consultar" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Volver al inicio" })).toHaveAttribute("href", PATHS.home);
  });

  it("las páginas de prueba siguen existiendo, pero solo por su dirección", async () => {
    open(PATHS.kit);
    expect(await screen.findByRole("heading", { level: 1, name: /Kit de componentes/ })).toBeInTheDocument();
  });

  it("una dirección que no existe lo dice", async () => {
    open("/no-existe");
    expect(await screen.findByRole("heading", { level: 1, name: "Esta dirección no existe" })).toBeInTheDocument();
  });
});
