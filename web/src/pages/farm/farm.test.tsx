import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RouterProvider, createMemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { PATHS } from "@/app/paths";
import { routes } from "@/app/routes";
import { setLightMode } from "@/lib/lightMode";
import { parseHa } from "@/features/farm/lots";

// Datos de ejemplo de las pruebas (R5): nombres y cifras de muestra.
const ROSA = {
  user_id: "1",
  username: "rosa.samaca",
  display_name: "Rosa",
  role: "farmer",
  consent_version: 3,
  consent_at: "2026-08-02T13:40:00Z",
  priorities: null,
  created_at: "2026-08-02T13:40:00Z",
};
const MUNICIPALITIES = [
  { municipality_id: "15646", name: "Samacá", department: "Boyacá", lat: 5.49, lon: -73.49 },
  { municipality_id: "15407", name: "Villa de Leyva", department: "Boyacá", lat: 5.63, lon: -73.52 },
  { municipality_id: "25899", name: "Zipaquirá", department: "Cundinamarca", lat: 5.02, lon: -74.0 },
];
const LOT = {
  lot_id: "a1",
  municipality_id: "15646",
  name: "El Alto",
  geometry: null,
  area_ha: 2.5,
  irrigated: false,
  created_at: "2026-10-15T10:00:00Z",
  updated_at: "2026-10-15T10:00:00Z",
};
const DETAIL = { ...LOT, soil: null, current_seasons: [] };

type Reply = { status: number; body?: unknown };

function fakeApi(replies: Record<string, Reply>) {
  const calls: { key: string; body: unknown }[] = [];
  vi.stubGlobal("fetch", async (url: string, init: RequestInit = {}) => {
    const key = `${init.method ?? "GET"} ${url}`;
    calls.push({ key, body: init.body ? JSON.parse(String(init.body)) : undefined });
    const reply = replies[key] ?? { status: 401, body: { error: { code: "unauthorized", message: "Inicie sesión para continuar." } } };
    return new Response(reply.body === undefined ? null : JSON.stringify(reply.body), { status: reply.status });
  });
  return calls;
}

const BASE = {
  "GET /api/v1/me": { status: 200, body: ROSA },
  "GET /api/v1/catalogs/municipalities": { status: 200, body: MUNICIPALITIES },
};
const open = (path: string) => render(<RouterProvider router={createMemoryRouter(routes, { initialEntries: [path] })} />);

afterEach(() => {
  vi.unstubAllGlobals();
  setLightMode(false);
});

describe("Mi finca (HU-169)", () => {
  it("lista los lotes sin dibujar con su área, su municipio y si tienen siembra", async () => {
    fakeApi({
      ...BASE,
      "GET /api/v1/lots": {
        status: 200,
        body: [
          { ...LOT, current_crop_ids: [] },
          { ...LOT, lot_id: "b2", name: "La Esperanza", municipality_id: "15407", area_ha: 1, current_crop_ids: ["papa", "arveja"] },
        ],
      },
    });
    open(PATHS.farm);
    expect(await screen.findByRole("heading", { level: 1, name: "Sus lotes" })).toBeInTheDocument();
    const list = within(await screen.findByRole("region", { name: "Sin dibujar · No están en el mapa" }));
    const alto = list.getByRole("link", { name: /El Alto/ });
    expect(alto).toHaveAttribute("href", PATHS.lot("a1"));
    expect(alto).toHaveTextContent("2,50 ha");
    expect(await within(alto).findByText("Sin siembra en curso · Samacá")).toBeInTheDocument();
    expect(alto).toHaveTextContent("Área escrita a mano");
    expect(list.getByRole("link", { name: /La Esperanza/ })).toHaveTextContent("2 siembras en curso · Villa de Leyva");
    // Lotes de dos municipios: la nota no nombra uno solo.
    expect(screen.getByText("Usan el suelo y la altitud de su municipio, no los suyos.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Agregar lote" })).toHaveAttribute("href", PATHS.addLot);
  });

  it("sin lotes invita a agregar el primero", async () => {
    fakeApi({ ...BASE, "GET /api/v1/lots": { status: 200, body: [] } });
    open(PATHS.farm);
    expect(await screen.findByRole("heading", { level: 2, name: "Todavía no tiene lotes" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Agregar lote" })).toHaveAttribute("href", PATHS.addLot);
  });

  it("sin sesión lleva a «Entrar»", async () => {
    fakeApi({});
    open(PATHS.farm);
    expect(await screen.findByRole("heading", { level: 1, name: "Vuelva a su finca" })).toBeInTheDocument();
  });
});

describe("En modo ligero se ven completas, sin tocar nada (HU-158)", () => {
  const replies = {
    ...BASE,
    "GET /api/v1/lots": { status: 200, body: [{ ...LOT, current_crop_ids: [] }] },
    "GET /api/v1/lots/a1": { status: 200, body: DETAIL },
  };
  it.each([
    [PATHS.farm, "Sus lotes", "link", "Agregar lote"],
    [PATHS.addLot, "¿Dónde está el lote nuevo?", "button", "Seguir"],
    [PATHS.lot("a1"), "El Alto", "link", "Editar lote"],
    [PATHS.editLot("a1"), "El Alto", "button", "Guardar cambios"],
  ] as const)("%s", async (path, title, role, action) => {
    setLightMode(true);
    fakeApi(replies);
    open(path);
    expect(await screen.findByRole("heading", { level: 1, name: title })).toBeVisible();
    expect(await screen.findByRole(role, { name: action })).toBeVisible();
  });
});

describe("Agregar lote sin dibujar (HU-164)", () => {
  it("elige el municipio, escribe el área, el nombre y el riego, y guarda", async () => {
    const calls = fakeApi({
      ...BASE,
      "GET /api/v1/lots": { status: 200, body: [] },
      "POST /api/v1/lots": { status: 201, body: { ...LOT, lot_id: "n1", name: "La Esperanza", municipality_id: "15407", irrigated: true } },
      "GET /api/v1/lots/n1": { status: 200, body: { ...DETAIL, lot_id: "n1", name: "La Esperanza" } },
    });
    open(PATHS.addLot);
    expect(await screen.findByRole("heading", { level: 1, name: "¿Dónde está el lote nuevo?" })).toBeInTheDocument();
    // Sin municipio no sigue.
    await userEvent.click(screen.getByRole("button", { name: "Seguir" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Elija el municipio de su lote.");
    await userEvent.type(screen.getByRole("combobox", { name: "Municipio" }), "villa de");
    await userEvent.click(await screen.findByRole("option", { name: /Villa de Leyva/ }));
    await userEvent.click(screen.getByRole("button", { name: "Seguir" }));

    expect(await screen.findByRole("heading", { level: 1, name: "Su lote, sin dibujar" })).toBeInTheDocument();
    expect(screen.getByText(/El suelo y la altitud son los de Villa de Leyva/)).toBeInTheDocument();
    // Sin área ni nombre no se envía nada.
    await userEvent.click(screen.getByRole("button", { name: "Guardar lote" }));
    expect(screen.getByText("Escriba el área en hectáreas, mayor que cero (por ejemplo, 2,5).")).toBeInTheDocument();
    expect(screen.getByText("Escriba un nombre para el lote.")).toBeInTheDocument();
    expect(calls.some((call) => call.key === "POST /api/v1/lots")).toBe(false);

    await userEvent.type(screen.getByLabelText("Área del lote (ha)"), "2,5");
    await userEvent.type(screen.getByLabelText("Nombre del lote"), "La Esperanza");
    await userEvent.click(within(screen.getByRole("group", { name: "¿Este lote tiene riego?" })).getByRole("radio", { name: "Sí" }));
    await userEvent.click(screen.getByRole("button", { name: "Guardar lote" }));
    expect(calls.find((call) => call.key === "POST /api/v1/lots")?.body).toEqual({
      name: "La Esperanza",
      municipality_id: "15407",
      area_ha: 2.5,
      irrigated: true,
    });
    expect(await screen.findByRole("heading", { level: 1, name: "La Esperanza" })).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Lote guardado.");
  });

  it("ofrece primero las zonas donde ya tiene lotes, con cuántos lotes tiene", async () => {
    const calls = fakeApi({
      ...BASE,
      "GET /api/v1/lots": { status: 200, body: [{ ...LOT, current_crop_ids: [] }] },
      "POST /api/v1/lots": { status: 201, body: { ...LOT, lot_id: "n2" } },
      "GET /api/v1/lots/n2": { status: 200, body: { ...DETAIL, lot_id: "n2" } },
    });
    open(PATHS.addLot);
    const zones = within(await screen.findByRole("group", { name: "En una zona donde ya tiene lotes" }));
    expect(zones.getByRole("radio", { name: /Samacá, Boyacá\s*1 lote/ })).toBeChecked();
    expect(zones.getByRole("radio", { name: /En otro municipio/ })).not.toBeChecked();
    expect(screen.queryByRole("combobox")).toBeNull();
    await userEvent.click(screen.getByRole("button", { name: "Seguir" }));
    await userEvent.type(await screen.findByLabelText("Área del lote (ha)"), "1.25");
    await userEvent.type(screen.getByLabelText("Nombre del lote"), "El Bajo");
    await userEvent.click(screen.getByRole("button", { name: "Guardar lote" }));
    // El riego sin responder va nulo: «Todavía no sé».
    expect(calls.find((call) => call.key === "POST /api/v1/lots")?.body).toEqual({
      name: "El Bajo",
      municipality_id: "15646",
      area_ha: 1.25,
      irrigated: null,
    });
  });

  it("«Cancelar» vuelve a Mi finca sin guardar nada, también desde el paso 2", async () => {
    const calls = fakeApi({ ...BASE, "GET /api/v1/lots": { status: 200, body: [{ ...LOT, current_crop_ids: [] }] } });
    open(PATHS.addLot);
    expect(await screen.findByRole("link", { name: "Cancelar" })).toHaveAttribute("href", PATHS.farm);
    await userEvent.click(screen.getByRole("button", { name: "Seguir" }));
    // En el paso 2 hay dos salidas: volver al paso 1 o cancelar.
    expect(await screen.findByRole("button", { name: "‹ Samacá, Boyacá" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("link", { name: "Cancelar" }));
    expect(await screen.findByRole("heading", { level: 1, name: "Sus lotes" })).toBeInTheDocument();
    expect(calls.some((call) => call.key.startsWith("POST"))).toBe(false);
  });

  it("si los datos de AgroSense no están, lo dice y no muestra un formulario sin municipios", async () => {
    fakeApi({
      ...BASE,
      "GET /api/v1/lots": { status: 200, body: [] },
      "GET /api/v1/catalogs/municipalities": {
        status: 503,
        body: {
          error: {
            code: "dataset_unavailable",
            message: "Los datos de AgroSense no están disponibles en este momento. Intente de nuevo más tarde.",
          },
        },
      },
    });
    open(PATHS.addLot);
    expect(await screen.findByRole("alert")).toHaveTextContent("Los datos de AgroSense no están disponibles");
    expect(screen.queryByRole("button", { name: "Seguir" })).toBeNull();
    expect(screen.getByRole("link", { name: "Cancelar" })).toHaveAttribute("href", PATHS.farm);
  });
});

describe("El lote (HU-164)", () => {
  it("muestra el área, el riego, que no tiene dibujo y que no hay datos del suelo", async () => {
    fakeApi({ ...BASE, "GET /api/v1/lots/a1": { status: 200, body: DETAIL } });
    open(PATHS.lot("a1"));
    expect(await screen.findByRole("heading", { level: 1, name: "El Alto" })).toBeInTheDocument();
    expect(await screen.findByText("Samacá, Boyacá")).toBeInTheDocument();
    expect(screen.getByText("2,50 ha · escrita a mano")).toBeInTheDocument();
    expect(screen.getByText("Sin riego")).toBeInTheDocument();
    expect(screen.getByText("Sin siembra en curso.")).toBeInTheDocument();
    expect(screen.getByText("Sin datos del suelo todavía.")).toBeInTheDocument();
    expect(screen.getByText("No sale en el mapa de su finca.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Editar lote" })).toHaveAttribute("href", PATHS.editLot("a1"));
    expect(screen.getByRole("link", { name: "‹ Mi finca" })).toHaveAttribute("href", PATHS.farm);
    // Borrar va en «Editar lote», no aquí.
    expect(screen.queryByRole("button", { name: "Borrar este lote" })).toBeNull();
  });

  it("un lote ajeno o que no existe lo dice", async () => {
    fakeApi({
      ...BASE,
      "GET /api/v1/lots/zz": { status: 404, body: { error: { code: "not_found", message: "Ese lote no existe o no es suyo." } } },
    });
    open(PATHS.lot("zz"));
    expect(await screen.findByRole("alert")).toHaveTextContent("Ese lote no existe o no es suyo.");
    expect(screen.getByRole("link", { name: "‹ Mi finca" })).toHaveAttribute("href", PATHS.farm);
  });
});

describe("Editar lote (HU-164)", () => {
  it("cambia el nombre, el área y el riego, y vuelve al lote", async () => {
    const calls = fakeApi({
      ...BASE,
      "GET /api/v1/lots/a1": { status: 200, body: DETAIL },
      "PATCH /api/v1/lots/a1": { status: 200, body: { ...LOT, name: "El Alto de abajo", area_ha: 3, irrigated: null } },
    });
    open(PATHS.editLot("a1"));
    const name = await screen.findByLabelText("Nombre del lote");
    expect(name).toHaveValue("El Alto");
    await userEvent.clear(name);
    await userEvent.type(name, "El Alto de abajo");
    const area = screen.getByLabelText("Área del lote (ha)");
    expect(area).toHaveValue("2,5");
    await userEvent.clear(area);
    await userEvent.type(area, "3");
    await userEvent.click(screen.getByRole("radio", { name: "Todavía no sé" }));
    await userEvent.click(screen.getByRole("button", { name: "Guardar cambios" }));
    expect(calls.find((call) => call.key === "PATCH /api/v1/lots/a1")?.body).toEqual({
      name: "El Alto de abajo",
      area_ha: 3,
      irrigated: null,
    });
    expect(await screen.findByRole("status")).toHaveTextContent("Cambios guardados.");
  });

  it("«Cancelar» vuelve al lote sin guardar", async () => {
    fakeApi({ ...BASE, "GET /api/v1/lots/a1": { status: 200, body: DETAIL } });
    open(PATHS.editLot("a1"));
    expect(await screen.findByRole("link", { name: "Cancelar" })).toHaveAttribute("href", PATHS.lot("a1"));
  });

  it("si el área queda menor que lo sembrado, lo avisa antes y dice por qué", async () => {
    const season = {
      season_id: "s1",
      crop_id: "papa",
      area_ha: 2,
      follows_season_ids: [],
      sowing_date: "2026-09-01",
      days_since_sowing: 44,
    };
    fakeApi({
      ...BASE,
      "GET /api/v1/lots/a1": { status: 200, body: { ...DETAIL, current_seasons: [season] } },
      "PATCH /api/v1/lots/a1": {
        status: 422,
        body: { error: { code: "area_below_seasons", message: "El lote no puede quedar más chico que lo que tiene sembrado: 2,00 ha." } },
      },
    });
    open(PATHS.editLot("a1"));
    expect(await screen.findByText("No puede quedar más chico que lo sembrado (2,00 ha).")).toBeInTheDocument();
    const area = screen.getByLabelText("Área del lote (ha)");
    await userEvent.clear(area);
    await userEvent.type(area, "1");
    await userEvent.click(screen.getByRole("button", { name: "Guardar cambios" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("lo que tiene sembrado: 2,00 ha");
  });

  it("«Borrar este lote» pide confirmar y vuelve a Mi finca", async () => {
    const calls = fakeApi({
      ...BASE,
      "GET /api/v1/lots/a1": { status: 200, body: DETAIL },
      "DELETE /api/v1/lots/a1": { status: 204 },
      "GET /api/v1/lots": { status: 200, body: [] },
    });
    open(PATHS.editLot("a1"));
    await userEvent.click(await screen.findByRole("button", { name: "Borrar este lote" }));
    const dialog = await screen.findByRole("dialog", { name: "¿Borrar El Alto?" });
    expect(within(dialog).getByText("Deja de verse en Mi finca con su historial.")).toBeInTheDocument();
    await userEvent.click(within(dialog).getByRole("button", { name: "No, volver" }));
    expect(calls.some((call) => call.key.startsWith("DELETE"))).toBe(false);
    await userEvent.click(screen.getByRole("button", { name: "Borrar este lote" }));
    await userEvent.click(within(await screen.findByRole("dialog")).getByRole("button", { name: "Sí, borrar el lote" }));
    expect(await screen.findByRole("heading", { level: 1, name: "Sus lotes" })).toBeInTheDocument();
    expect(calls.some((call) => call.key === "DELETE /api/v1/lots/a1")).toBe(true);
  });
});

describe("El área escrita a mano", () => {
  it("acepta coma o punto y rechaza lo que no es un área", () => {
    expect([parseHa("2,5"), parseHa("2.5"), parseHa(" 10 "), parseHa("0"), parseHa("-1"), parseHa("abc"), parseHa("100001")]).toEqual([
      2.5,
      2.5,
      10,
      null,
      null,
      null,
      null,
    ]);
  });
});
