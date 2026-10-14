import { render, screen, within } from "@testing-library/react";
import { RouterProvider, createMemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { PATHS } from "@/app/paths";
import { routes } from "@/app/routes";
import { setLightMode } from "@/lib/lightMode";
import { SECTIONS } from "./content";

const open = () => render(<RouterProvider router={createMemoryRouter(routes, { initialEntries: [PATHS.dataPolicy] })} />);
const guest = () =>
  vi.stubGlobal("fetch", async () => new Response(JSON.stringify({ error: { code: "unauthorized", message: "x" } }), { status: 401 }));

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("Política de tratamiento de datos (HU-163)", () => {
  it("se lee sin cuenta y dice qué se guarda, qué no, para qué y cómo borrarlo", async () => {
    guest();
    open();
    expect(await screen.findByRole("heading", { level: 1, name: "Política de tratamiento de datos" })).toBeInTheDocument();
    expect(screen.getByText(/Versión 3 · vigente desde/)).toBeInTheDocument();
    for (const section of SECTIONS) expect(screen.getByRole("heading", { level: 2, name: section.title })).toBeInTheDocument();
    // Lo que nunca se guarda se dice con texto, no solo con la marca.
    const never = screen.getByRole("heading", { level: 2, name: "Qué no guardamos" }).closest("section")!;
    expect(within(never).getByText(/Correo, celular, documento ni dirección/)).toBeInTheDocument();
    expect(within(never).getAllByText("No se guarda:", { exact: false }).length).toBe(4);
    expect(screen.getByText(/Borrar la cuenta lo borra todo/)).toBeInTheDocument();
  });

  it("avisa que el texto todavía necesita revisión legal", async () => {
    guest();
    open();
    expect(await screen.findByRole("note")).toHaveTextContent("Este texto todavía necesita revisión legal");
  });

  it("sin cuenta ofrece crear cuenta o entrar", async () => {
    guest();
    open();
    const main = await screen.findByRole("main");
    expect(within(main).getByRole("link", { name: "Crear cuenta" })).toHaveAttribute("href", PATHS.signup);
    expect(within(main).getByRole("link", { name: "Entrar" })).toHaveAttribute("href", PATHS.login);
  });

  it("se ve completa en modo ligero", async () => {
    guest();
    setLightMode(true);
    try {
      open();
      expect(await screen.findByRole("heading", { level: 1 })).toBeInTheDocument();
      expect(within(screen.getByRole("main")).getAllByRole("heading", { level: 2 })).toHaveLength(SECTIONS.length);
    } finally {
      setLightMode(false);
    }
  });
});
