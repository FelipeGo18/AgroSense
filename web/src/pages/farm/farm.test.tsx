import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useEffect } from "react";
import { RouterProvider, createMemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { PATHS } from "@/app/paths";
import { routes } from "@/app/routes";
import type { MapCanvasProps } from "@/components/map/MapCanvas";
import { areaHa, type LotPolygon } from "@/features/farm/geo";
import { parseHa } from "@/features/farm/lots";
import { setLightMode } from "@/lib/lightMode";

// El mapa real necesita WebGL, que el entorno de pruebas no tiene. Este doble muestra lo que recibiría el mapa y deja
// «dibujar» un lote con un botón. La barra de dibujo, deshacer, la validación y el envío son los de verdad.
const DRAWN = { value: null as LotPolygon | null };
vi.mock("@/components/map/MapCanvas", () => ({
  default: function FakeMap({ lots = [], editing, onReady, onLotClick, boundary }: MapCanvasProps) {
    useEffect(() => onReady({ zoomIn: () => {}, zoomOut: () => {} }), [onReady]);
    return (
      <div data-testid="mapa" data-limite={boundary ? "sí" : "no"}>
        {lots.map((lot) => (
          <button key={lot.id} type="button" onClick={() => onLotClick?.(lot.id)}>
            En el mapa: {lot.name}
          </button>
        ))}
        {editing && (
          <>
            <span>Modo: {editing.mode}</span>
            {editing.areaLabel && <span>Etiqueta: {editing.areaLabel}</span>}
            <button
              type="button"
              onClick={() => {
                editing.onChange(DRAWN.value);
                editing.onModeChange("move");
              }}
            >
              Simular dibujo
            </button>
          </>
        )}
      </div>
    );
  },
}));

// Datos de ejemplo de las pruebas (R5): nombres, cifras y límites de muestra.
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
const square = (lon: number, lat: number, side: number): LotPolygon => ({
  type: "Polygon",
  coordinates: [
    [
      [lon, lat],
      [lon + side, lat],
      [lon + side, lat + side],
      [lon, lat + side],
      [lon, lat],
    ],
  ],
});
// Samacá: un cuadrado de 0,1° de ejemplo. El lote: unos 100 m de lado, adentro.
const SAMACA = {
  type: "Feature",
  properties: { municipality_id: "15646", name: "Samacá", source_id: "dane_mgn_2025" },
  geometry: square(-73.54, 5.44, 0.1),
};
const INSIDE = square(-73.49, 5.49, 0.0009);
const OUTSIDE = square(-73.3, 5.49, 0.0009);
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
const DRAWN_LOT = { ...LOT, lot_id: "d1", name: "La Vega", geometry: INSIDE, area_ha: 0.99 };
const DETAIL = { ...LOT, soil: null, current_seasons: [] };

const CROPS = [
  { crop_id: "papa", name_es: "Papa", kind: "crop", archetype: "tuber", family: "solanaceae", cycle_months: 5.4 },
  { crop_id: "arveja", name_es: "Arveja", kind: "crop", archetype: "legume", family: "fabaceae", cycle_months: 3.6 },
  { crop_id: "haba", name_es: "Haba", kind: "crop", archetype: "legume", family: "fabaceae", cycle_months: 4.6 },
];
// Las fechas de las siembras de ejemplo van contadas desde hoy: las pantallas no dejan fechas posteriores a hoy.
const ago = (days: number) => {
  const date = new Date();
  date.setDate(date.getDate() - days);
  return new Date(date.getTime() - date.getTimezoneOffset() * 60_000).toISOString().slice(0, 10);
};
const SEASON = {
  season_id: "s1",
  lot_id: "a1",
  crop_id: "papa",
  area_ha: 1.5,
  follows_season_ids: [],
  sowing_date: ago(60),
  harvest_date: null,
  diagnosis_light: null,
  diagnosis_light_default: null,
  diagnosis_action: null,
  diagnosis_weights: null,
  diagnosis_irrigated: null,
  dataset_version: null,
  rules_version: null,
  created_at: "2026-08-01T10:00:00Z",
  updated_at: "2026-08-01T10:00:00Z",
  days_since_sowing: 60,
  stage: "development",
  stage_progress_pct: 50,
  stage_method: "calendar",
  harvest_estimate: ago(-105),
  harvest_basis: "calendar",
  harvest_due: false,
};
const CURRENT = {
  season_id: "s1",
  crop_id: "papa",
  area_ha: 1.5,
  follows_season_ids: [],
  sowing_date: SEASON.sowing_date,
  days_since_sowing: 60,
  stage: "development",
  stage_progress_pct: 50,
  stage_method: "calendar",
  harvest_estimate: SEASON.harvest_estimate,
  harvest_basis: "calendar",
  harvest_due: false,
};

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
  "GET /api/v1/catalogs/municipalities/15646/boundary": { status: 200, body: SAMACA },
  "GET /api/v1/catalogs/crops": { status: 200, body: CROPS },
  "GET /api/v1/lots/a1/seasons": { status: 200, body: [] },
  "GET /api/v1/lots/d1/seasons": { status: 200, body: [] },
};
const open = (path: string) => render(<RouterProvider router={createMemoryRouter(routes, { initialEntries: [path] })} />);

afterEach(() => {
  vi.unstubAllGlobals();
  setLightMode(false);
  DRAWN.value = null;
});

describe("Mi finca (HU-169)", () => {
  it("los lotes dibujados van en el mapa y en «En el mapa»; los demás, en «Sin dibujar», con «Dibujar en el mapa»", async () => {
    fakeApi({
      ...BASE,
      "GET /api/v1/lots": {
        status: 200,
        body: [
          { ...DRAWN_LOT, current_crop_ids: ["papa"] },
          { ...LOT, current_crop_ids: [] },
        ],
      },
    });
    open(PATHS.farm);
    expect(await screen.findByRole("heading", { level: 1, name: "Sus lotes" })).toBeInTheDocument();
    const map = await screen.findByTestId("mapa");
    expect(within(map).getByRole("button", { name: "En el mapa: La Vega" })).toBeInTheDocument();
    expect(within(map).queryByText(/El Alto/)).toBeNull();
    const onMap = within(screen.getByRole("region", { name: "En el mapa" }));
    expect(await onMap.findByText("Papa en curso · Samacá")).toBeInTheDocument();
    const undrawn = within(screen.getByRole("region", { name: "Sin dibujar · No están en el mapa" }));
    expect(undrawn.getByRole("link", { name: /El Alto/ })).toHaveAttribute("href", PATHS.lot("a1"));
    expect(undrawn.getByRole("link", { name: "Dibujar en el mapa" })).toHaveAttribute("href", PATHS.drawLot("a1"));
    expect(screen.getByText("Usan el suelo y la altitud de Samacá, no los suyos.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Agregar lote" })).toHaveAttribute("href", PATHS.addLot);
  });

  it("tocar un lote en el mapa lo abre", async () => {
    fakeApi({
      ...BASE,
      "GET /api/v1/lots": { status: 200, body: [{ ...DRAWN_LOT, current_crop_ids: [] }] },
      "GET /api/v1/lots/d1": { status: 200, body: { ...DRAWN_LOT, soil: null, current_seasons: [] } },
    });
    open(PATHS.farm);
    await userEvent.click(await screen.findByRole("button", { name: "En el mapa: La Vega" }));
    expect(await screen.findByRole("heading", { level: 1, name: "La Vega" })).toBeInTheDocument();
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
    "GET /api/v1/lots/a1/seasons": { status: 200, body: [SEASON] },
  };
  it.each([
    [PATHS.farm, "Sus lotes", "link", "Agregar lote"],
    [PATHS.addLot, "¿Dónde está el lote nuevo?", "button", "Seguir: dibujar el lote"],
    [PATHS.lot("a1"), "El Alto", "link", "Editar lote"],
    [PATHS.editLot("a1"), "El Alto", "button", "Guardar cambios"],
    [PATHS.sow("a1"), "Registrar la siembra", "button", "Guardar siembra"],
    [PATHS.harvest("a1", "s1"), "Registrar la cosecha", "button", "Guardar solo la cosecha"],
    [PATHS.editSeason("a1", "s1"), "Corregir la papa", "button", "Borrar esta siembra"],
  ] as const)("%s", async (path, title, role, action) => {
    setLightMode(true);
    fakeApi(replies);
    open(path);
    expect(await screen.findByRole("heading", { level: 1, name: title })).toBeVisible();
    expect(await screen.findByRole(role, { name: action })).toBeVisible();
  });
});

async function toDrawStep() {
  await userEvent.click(await screen.findByRole("button", { name: "Seguir: dibujar el lote" }));
  expect(await screen.findByRole("heading", { level: 1, name: "Dibuje su lote" })).toBeInTheDocument();
}

describe("Agregar lote dibujado (HU-164)", () => {
  const replies = (extra: Record<string, Reply> = {}) => ({
    ...BASE,
    "GET /api/v1/lots": { status: 200, body: [{ ...LOT, current_crop_ids: [] }] },
    ...extra,
  });

  it("dibuja el lote en el mapa, ve el área y guarda el contorno (sin área: la calcula la API)", async () => {
    DRAWN.value = INSIDE;
    const calls = fakeApi(
      replies({
        "POST /api/v1/lots": { status: 201, body: { ...DRAWN_LOT, lot_id: "n1", name: "La Vega" } },
        "GET /api/v1/lots/n1": { status: 200, body: { ...DRAWN_LOT, lot_id: "n1", soil: null, current_seasons: [] } },
      }),
    );
    open(PATHS.addLot);
    await toDrawStep();
    expect(screen.getByText("Toque cada esquina del lote.")).toBeInTheDocument();
    expect(await screen.findByTestId("mapa")).toHaveAttribute("data-limite", "sí");
    // Sin dibujo no se envía nada.
    await userEvent.type(screen.getByLabelText("Nombre del lote"), "La Vega");
    await userEvent.click(screen.getByRole("button", { name: "Guardar lote" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Dibuje su lote en el mapa, o escriba su área a mano.");
    expect(calls.some((call) => call.key === "POST /api/v1/lots")).toBe(false);

    await userEvent.click(screen.getByRole("button", { name: "Simular dibujo" }));
    const ha = `${areaHa(INSIDE).toFixed(2).replace(".", ",")} ha`;
    expect(screen.getByText("Área calculada con su dibujo")).toBeInTheDocument();
    expect(screen.getByText(`Etiqueta: ${ha}`)).toBeInTheDocument();
    // Al cerrar el lote, la barra pasa a «Mover puntos».
    expect(screen.getByRole("button", { name: "Mover puntos" })).toHaveAttribute("aria-pressed", "true");
    await userEvent.click(screen.getByRole("radio", { name: "Sí" }));
    await userEvent.click(screen.getByRole("button", { name: "Guardar lote" }));
    expect(calls.find((call) => call.key === "POST /api/v1/lots")?.body).toEqual({
      name: "La Vega",
      municipality_id: "15646",
      geometry: INSIDE,
      irrigated: true,
    });
    expect(await screen.findByRole("heading", { level: 1, name: "La Vega" })).toBeInTheDocument();
  });

  it("si el dibujo se sale del municipio lo dice y no deja guardar", async () => {
    DRAWN.value = OUTSIDE;
    const calls = fakeApi(replies());
    open(PATHS.addLot);
    await toDrawStep();
    await screen.findByTestId("mapa");
    await userEvent.click(screen.getByRole("button", { name: "Simular dibujo" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Su lote se sale de Samacá");
    expect(screen.getByRole("button", { name: "Guardar lote" })).toBeDisabled();
    expect(calls.some((call) => call.key.startsWith("POST"))).toBe(false);
  });

  it("«Deshacer» vuelve al dibujo anterior y «Borrar» lo quita", async () => {
    DRAWN.value = INSIDE;
    fakeApi(replies());
    open(PATHS.addLot);
    await toDrawStep();
    await screen.findByTestId("mapa");
    expect(screen.getByRole("button", { name: "Deshacer" })).toBeDisabled();
    await userEvent.click(screen.getByRole("button", { name: "Simular dibujo" }));
    expect(screen.getByText("Área calculada con su dibujo")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Deshacer" }));
    expect(screen.queryByText("Área calculada con su dibujo")).toBeNull();
    expect(screen.getByText("Modo: draw")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Simular dibujo" }));
    await userEvent.click(screen.getByRole("button", { name: "Borrar" }));
    expect(screen.queryByText("Área calculada con su dibujo")).toBeNull();
    expect(screen.getByRole("button", { name: "Dibujar" })).toHaveAttribute("aria-pressed", "true");
  });

  it("«Escribir el área a mano» guarda el lote sin dibujo, y se puede volver al mapa", async () => {
    const calls = fakeApi(
      replies({
        "POST /api/v1/lots": { status: 201, body: { ...LOT, lot_id: "n2" } },
        "GET /api/v1/lots/n2": { status: 200, body: { ...DETAIL, lot_id: "n2" } },
      }),
    );
    open(PATHS.addLot);
    await toDrawStep();
    await userEvent.click(screen.getByRole("button", { name: "Escribir el área a mano" }));
    expect(await screen.findByRole("heading", { level: 1, name: "Su lote, sin dibujar" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Dibujar en el mapa" })).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("Área del lote (ha)"), "1,25");
    await userEvent.type(screen.getByLabelText("Nombre del lote"), "El Bajo");
    await userEvent.click(screen.getByRole("button", { name: "Guardar lote" }));
    expect(calls.find((call) => call.key === "POST /api/v1/lots")?.body).toEqual({
      name: "El Bajo",
      municipality_id: "15646",
      area_ha: 1.25,
      irrigated: null,
    });
  });

  it("elige otro municipio con el buscador", async () => {
    fakeApi({ ...BASE, "GET /api/v1/lots": { status: 200, body: [] } });
    open(PATHS.addLot);
    expect(await screen.findByRole("heading", { level: 1, name: "¿Dónde está el lote nuevo?" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Seguir: dibujar el lote" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Elija el municipio de su lote.");
    await userEvent.type(screen.getByRole("combobox", { name: "Municipio" }), "villa de");
    await userEvent.click(await screen.findByRole("option", { name: /Villa de Leyva/ }));
    await toDrawStep();
    expect(screen.getByRole("button", { name: "‹ Villa de Leyva, Boyacá" })).toBeInTheDocument();
  });

  it("ofrece primero las zonas donde ya tiene lotes, con cuántos lotes tiene", async () => {
    fakeApi(replies());
    open(PATHS.addLot);
    const zones = within(await screen.findByRole("group", { name: "En una zona donde ya tiene lotes" }));
    expect(zones.getByRole("radio", { name: /Samacá, Boyacá\s*1 lote/ })).toBeChecked();
    expect(zones.getByRole("radio", { name: /En otro municipio/ })).not.toBeChecked();
    expect(screen.queryByRole("combobox")).toBeNull();
  });

  it("«Cancelar» vuelve a Mi finca sin guardar nada, también desde el dibujo", async () => {
    const calls = fakeApi(replies());
    open(PATHS.addLot);
    expect(await screen.findByRole("link", { name: "Cancelar" })).toHaveAttribute("href", PATHS.farm);
    await toDrawStep();
    expect(screen.getByRole("button", { name: "‹ Samacá, Boyacá" })).toBeInTheDocument();
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
    expect(screen.queryByRole("button", { name: "Seguir: dibujar el lote" })).toBeNull();
    expect(screen.getByRole("link", { name: "Cancelar" })).toHaveAttribute("href", PATHS.farm);
  });
});

describe("El lote (HU-164)", () => {
  it("un lote sin dibujar dice que no tiene ubicación y ofrece dibujarlo", async () => {
    fakeApi({ ...BASE, "GET /api/v1/lots/a1": { status: 200, body: DETAIL } });
    open(PATHS.lot("a1"));
    expect(await screen.findByRole("heading", { level: 1, name: "El Alto" })).toBeInTheDocument();
    expect(await screen.findByText("Samacá, Boyacá")).toBeInTheDocument();
    expect(screen.getByText("2,50 ha · escrita a mano")).toBeInTheDocument();
    expect(screen.getByText("Sin riego")).toBeInTheDocument();
    expect(screen.getByText("Sin siembra en curso.")).toBeInTheDocument();
    expect(screen.getByText("Sin datos del suelo todavía.")).toBeInTheDocument();
    expect(screen.getByText("No sale en el mapa de su finca.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Dibujar en el mapa" })).toHaveAttribute("href", PATHS.drawLot("a1"));
    expect(screen.getByRole("link", { name: "Editar lote" })).toHaveAttribute("href", PATHS.editLot("a1"));
    // Borrar va en «Editar lote», no aquí.
    expect(screen.queryByRole("button", { name: "Borrar este lote" })).toBeNull();
  });

  it("un lote dibujado sale en el mapa con el área de su dibujo", async () => {
    fakeApi({ ...BASE, "GET /api/v1/lots/d1": { status: 200, body: { ...DRAWN_LOT, soil: null, current_seasons: [] } } });
    open(PATHS.lot("d1"));
    expect(await screen.findByRole("button", { name: "En el mapa: La Vega" })).toBeInTheDocument();
    expect(screen.getByText("0,99 ha · calculada con su dibujo")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Dibujar en el mapa" })).toBeNull();
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
  it("un lote sin dibujar cambia el nombre, el área y el riego", async () => {
    const calls = fakeApi({
      ...BASE,
      "GET /api/v1/lots/a1": { status: 200, body: DETAIL },
      "PATCH /api/v1/lots/a1": { status: 200, body: { ...LOT, name: "El Alto de abajo", area_ha: 3, irrigated: null } },
      "GET /api/v1/lots": { status: 200, body: [] },
    });
    open(PATHS.editLot("a1"));
    const name = await screen.findByLabelText("Nombre del lote");
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
    expect(await screen.findByText("Cambios guardados.")).toBeInTheDocument();
  });

  it("«Dibujar en el mapa» abre el mapa listo para dibujar y guarda el contorno", async () => {
    DRAWN.value = INSIDE;
    const calls = fakeApi({
      ...BASE,
      "GET /api/v1/lots/a1": { status: 200, body: DETAIL },
      "PATCH /api/v1/lots/a1": { status: 200, body: DRAWN_LOT },
    });
    open(PATHS.drawLot("a1"));
    expect(await screen.findByText("Modo: draw")).toBeInTheDocument();
    expect(screen.getByText("Toque el primer punto para cerrarlo.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Simular dibujo" }));
    // Con dibujo, el área sale de él: ya no se escribe.
    expect(screen.queryByLabelText("Área del lote (ha)")).toBeNull();
    await userEvent.click(screen.getByRole("button", { name: "Guardar cambios" }));
    expect(calls.find((call) => call.key === "PATCH /api/v1/lots/a1")?.body).toEqual({
      name: "El Alto",
      irrigated: false,
      geometry: INSIDE,
    });
  });

  it("un lote dibujado abre en «Mover puntos» y no manda el contorno si no cambió", async () => {
    const calls = fakeApi({
      ...BASE,
      "GET /api/v1/lots/d1": { status: 200, body: { ...DRAWN_LOT, soil: null, current_seasons: [] } },
      "PATCH /api/v1/lots/d1": { status: 200, body: DRAWN_LOT },
    });
    open(PATHS.editLot("d1"));
    expect(await screen.findByText("Modo: move")).toBeInTheDocument();
    expect(screen.getByText("Área calculada con su dibujo")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Guardar cambios" }));
    expect(calls.find((call) => call.key === "PATCH /api/v1/lots/d1")?.body).toEqual({ name: "La Vega", irrigated: false });
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

describe("Siembras y cosechas (HU-165, HU-220)", () => {
  const WITH_PAPA = { ...DETAIL, current_seasons: [CURRENT] };

  it("el lote muestra cada siembra con su cultivo, etapa, día y cosecha estimada", async () => {
    const harvested = {
      ...SEASON,
      season_id: "s0",
      crop_id: "arveja",
      area_ha: 1,
      sowing_date: ago(300),
      harvest_date: ago(200),
      stage: null,
    };
    fakeApi({
      ...BASE,
      "GET /api/v1/lots/a1": { status: 200, body: WITH_PAPA },
      "GET /api/v1/lots/a1/seasons": { status: 200, body: [SEASON, harvested] },
    });
    open(PATHS.lot("a1"));
    expect(await screen.findByText("Papa")).toBeInTheDocument();
    expect(screen.getByText(/Desarrollo · día 60/)).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "Desarrollo: lleva el 50 % de la etapa" })).toBeInTheDocument();
    expect(screen.getByText(/Cosecha estimada: .* Sale de la duración de las etapas del cultivo/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Registrar cosecha" })).toHaveAttribute("href", PATHS.harvest("a1", "s1"));
    // 2,5 ha del lote con 1,5 sembradas: queda 1 ha libre para otra siembra.
    expect(screen.getByRole("link", { name: "Registrar siembra" })).toHaveAttribute("href", PATHS.sow("a1"));
    const done = within(await screen.findByRole("region", { name: "Ya cosechado" }));
    expect(done.getByText("Arveja")).toBeInTheDocument();
    expect(done.getByRole("link", { name: "Corregir" })).toHaveAttribute("href", PATHS.editSeason("a1", "s0"));
  });

  it("con todo el lote sembrado no ofrece registrar otra siembra", async () => {
    fakeApi({ ...BASE, "GET /api/v1/lots/a1": { status: 200, body: { ...DETAIL, current_seasons: [{ ...CURRENT, area_ha: 2.5 }] } } });
    open(PATHS.lot("a1"));
    expect(await screen.findByText("Todo el lote está sembrado. Registre una cosecha para sembrar de nuevo.")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Registrar siembra" })).toBeNull();
  });

  it("registrar una siembra manda cultivo, área, fecha y lo de antes, y vuelve al lote", async () => {
    const calls = fakeApi({
      ...BASE,
      "GET /api/v1/lots/a1": { status: 200, body: WITH_PAPA },
      "GET /api/v1/lots/a1/seasons": { status: 200, body: [SEASON] },
      "POST /api/v1/lots/a1/seasons": { status: 201, body: { ...SEASON, season_id: "s2", crop_id: "arveja", area_ha: 1 } },
    });
    open(PATHS.sow("a1"));
    expect(await screen.findByRole("heading", { level: 1, name: "Registrar la siembra" })).toBeInTheDocument();
    // Lo libre es lo que no ocupa la papa en curso.
    expect(screen.getByText("Hay 1,00 ha libres en el lote.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Guardar siembra" }));
    expect(await screen.findByText("Elija el cultivo.")).toBeInTheDocument();
    await userEvent.selectOptions(screen.getByLabelText("Cultivo"), "arveja");
    await userEvent.click(screen.getByRole("button", { name: "Guardar siembra" }));
    expect(await screen.findByText("Siembra de arveja registrada.")).toBeInTheDocument();
    const post = calls.find((call) => call.key === "POST /api/v1/lots/a1/seasons");
    expect(post?.body).toEqual({ crop_id: "arveja", sowing_date: ago(0), area_ha: 1, follows_season_ids: [] });
  });

  it("no deja sembrar más de lo libre", async () => {
    const calls = fakeApi({ ...BASE, "GET /api/v1/lots/a1": { status: 200, body: WITH_PAPA } });
    open(PATHS.sow("a1"));
    const area = await screen.findByLabelText("Área que siembra (ha)");
    await userEvent.clear(area);
    await userEvent.type(area, "2");
    await userEvent.selectOptions(screen.getByLabelText("Cultivo"), "haba");
    await userEvent.click(screen.getByRole("button", { name: "Guardar siembra" }));
    expect(await screen.findByText("No cabe: en el lote quedan 1,00 ha libres.")).toBeInTheDocument();
    expect(calls.some((call) => call.key.startsWith("POST"))).toBe(false);
  });

  it("registrar la cosecha y seguir lleva a la siembra con esa cosecha marcada", async () => {
    const harvestedPapa = { ...SEASON, harvest_date: ago(0), stage: null };
    const replies: Record<string, Reply> = {
      ...BASE,
      "GET /api/v1/lots/a1": { status: 200, body: WITH_PAPA },
      "GET /api/v1/lots/a1/seasons": { status: 200, body: [SEASON] },
      "PATCH /api/v1/seasons/s1": { status: 200, body: harvestedPapa },
    };
    const calls = fakeApi(replies);
    open(PATHS.harvest("a1", "s1"));
    expect(await screen.findByRole("heading", { level: 1, name: "Registrar la cosecha" })).toBeInTheDocument();
    expect(screen.getByText(/La cosecha estimada era el/)).toBeInTheDocument();
    // Después de guardar, el lote y su historial ya vienen con la papa cosechada.
    replies["GET /api/v1/lots/a1"] = { status: 200, body: DETAIL };
    replies["GET /api/v1/lots/a1/seasons"] = { status: 200, body: [harvestedPapa] };
    await userEvent.click(screen.getByRole("button", { name: "Guardar cosecha y registrar la siembra" }));
    expect(await screen.findByRole("heading", { level: 1, name: "Registrar la siembra" })).toBeInTheDocument();
    expect(calls.find((call) => call.key === "PATCH /api/v1/seasons/s1")?.body).toEqual({ harvest_date: ago(0) });
    expect(await screen.findByRole("checkbox", { name: /Papa/ })).toBeChecked();
    // El área sugerida es la de la papa cosechada.
    expect(screen.getByLabelText("Área que siembra (ha)")).toHaveValue("1,5");
  });

  it("«Borrar esta siembra» pide confirmar y vuelve al lote", async () => {
    const calls = fakeApi({
      ...BASE,
      "GET /api/v1/lots/a1": { status: 200, body: WITH_PAPA },
      "GET /api/v1/lots/a1/seasons": { status: 200, body: [SEASON] },
      "DELETE /api/v1/seasons/s1": { status: 204 },
    });
    open(PATHS.editSeason("a1", "s1"));
    await userEvent.click(await screen.findByRole("button", { name: "Borrar esta siembra" }));
    const dialog = await screen.findByRole("dialog", { name: "¿Borrar la papa?" });
    await userEvent.click(within(dialog).getByRole("button", { name: "Sí, borrar la siembra" }));
    expect(await screen.findByText("Siembra borrada.")).toBeInTheDocument();
    expect(calls.some((call) => call.key === "DELETE /api/v1/seasons/s1")).toBe(true);
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
