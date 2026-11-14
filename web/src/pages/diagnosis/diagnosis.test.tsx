import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RouterProvider, createMemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { PATHS } from "@/app/paths";
import { routes } from "@/app/routes";
import { EMPTY_FORM, fromParams, sowingMonths, toParams, toRequest, validate, type ConsultForm } from "@/features/diagnosis/consult";
import { setLightMode } from "@/lib/lightMode";

// Datos de ejemplo de las pruebas (R5): municipios, cultivos, lote y respuesta de muestra.
const MUNICIPALITIES = [
  { municipality_id: "15646", name: "Samacá", department: "Boyacá", lat: 5.49, lon: -73.49 },
  { municipality_id: "15407", name: "Villa de Leyva", department: "Boyacá", lat: 5.63, lon: -73.52 },
  { municipality_id: "25899", name: "Zipaquirá", department: "Cundinamarca", lat: 5.02, lon: -74.0 },
];
const CROPS = [
  { crop_id: "papa", name_es: "Papa", kind: "crop", archetype: "tuber", family: "solanaceae", cycle_months: 5.4 },
  { crop_id: "arveja", name_es: "Arveja", kind: "crop", archetype: "legume", family: "fabaceae", cycle_months: 3.6 },
  { crop_id: "avena_vicia", name_es: "Avena con vicia", kind: "cover", archetype: null, family: null, cycle_months: 4 },
  { crop_id: "descanso", name_es: "Descanso", kind: "fallow", archetype: null, family: null, cycle_months: 3 },
];
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
const LOT = {
  lot_id: "a1",
  municipality_id: "25899",
  name: "El Alto",
  geometry: null,
  area_ha: 2.5,
  irrigated: true,
  created_at: "2026-10-15T10:00:00Z",
  updated_at: "2026-10-15T10:00:00Z",
  current_crop_ids: [],
};
const OTHER_LOT = { ...LOT, lot_id: "a2", name: "La Vega" };
const MONTHS = sowingMonths();
const RESPONSE = {
  suitability: { level: "suitable", score: 90 },
  window: {
    sowing_start: `${MONTHS[2].value}-01`,
    harvest_estimate: `${MONTHS[7].value}-15`,
    harvest_basis: "calendar",
    supply_semester: null,
  },
  overall: { light: "green", action: "sow", high_risk: false, weights_basis: "default" },
  overall_default: { light: "green", action: "sow", high_risk: false, weights_basis: "default" },
  weights: {},
  signals: {},
  limitations: [],
  versions: { dataset: "ejemplo", rules: "ejemplo" },
  request: {},
};

type Reply = { status: number; body?: unknown; headers?: Record<string, string> };

function fakeApi(replies: Record<string, Reply | Reply[]>) {
  const calls: { key: string; body: unknown }[] = [];
  const replyIndexes = new Map<string, number>();
  vi.stubGlobal("fetch", async (url: string, init: RequestInit = {}) => {
    const key = `${init.method ?? "GET"} ${url}`;
    calls.push({ key, body: init.body ? JSON.parse(String(init.body)) : undefined });
    const configured = replies[key];
    const index = replyIndexes.get(key) ?? 0;
    const reply = Array.isArray(configured) ? configured[Math.min(index, configured.length - 1)] : configured;
    if (Array.isArray(configured)) replyIndexes.set(key, index + 1);
    const response = reply ?? { status: 401, body: { error: { code: "unauthorized", message: "Inicie sesión para continuar." } } };
    return new Response(response.body === undefined ? null : JSON.stringify(response.body), {
      status: response.status,
      headers: response.headers,
    });
  });
  return calls;
}

const CATALOGS = {
  "GET /api/v1/catalogs/municipalities": { status: 200, body: MUNICIPALITIES },
  "GET /api/v1/catalogs/crops": { status: 200, body: CROPS },
  "POST /api/v1/diagnostics": { status: 200, body: RESPONSE },
};

function open(path: string) {
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  render(<RouterProvider router={router} />);
  return router;
}

afterEach(() => {
  vi.unstubAllGlobals();
  setLightMode(false);
});

describe("La consulta (HU-091)", () => {
  it("se elige entre los próximos doce meses, empezando por el mes en curso, y se envía su día 1", () => {
    const months = sowingMonths(new Date(2026, 10, 25)); // 25 de noviembre de 2026
    expect(months).toHaveLength(12);
    expect(months[0]).toEqual({ value: "2026-11", label: "noviembre de 2026" });
    expect(months[1].value).toBe("2026-12");
    expect(months[2].value).toBe("2027-01");
    expect(months[11].value).toBe("2027-10");
    const form: ConsultForm = { ...EMPTY_FORM, municipalityId: "15646", cropId: "papa", month: "2027-01", irrigation: "no" };
    expect(toRequest(form).sowing_date).toBe("2027-01-01");
  });

  it("el mes en curso se cuenta en la hora de Bogotá (UTC−5), como en la API, no en UTC ni en la del navegador", () => {
    // 30 de noviembre, 8:00 p. m. en Bogotá: en UTC ya es 1 de diciembre. Noviembre sigue siendo el mes en curso.
    expect(sowingMonths(new Date("2026-12-01T01:00:00Z"))[0].value).toBe("2026-11");
    // 1 de diciembre, 12:30 a. m. en Bogotá: ya es diciembre.
    expect(sowingMonths(new Date("2026-12-01T05:30:00Z"))[0].value).toBe("2026-12");
    // Fin de año: 31 de diciembre, 11:00 p. m. en Bogotá, ya 2027 en UTC.
    const months = sowingMonths(new Date("2027-01-01T04:00:00Z"));
    expect(months[0].value).toBe("2026-12");
    expect(months[11].value).toBe("2027-11");
  });

  it("«Sí», «No» y «No sé» se envían como riego verdadero, falso o nulo", () => {
    const base: ConsultForm = { ...EMPTY_FORM, municipalityId: "15646", cropId: "papa", month: "2027-01" };
    expect(toRequest({ ...base, irrigation: "si" }).irrigated).toBe(true);
    expect(toRequest({ ...base, irrigation: "no" }).irrigated).toBe(false);
    expect(toRequest({ ...base, irrigation: "nose" }).irrigated).toBeNull();
  });

  it("con un lote, el municipio y el riego salen del lote", () => {
    const form: ConsultForm = { ...EMPTY_FORM, cropId: "papa", month: "2027-01", lotId: "a1", irrigation: "no", municipalityId: "15646" };
    expect(toRequest(form, LOT)).toEqual({
      municipality_id: "25899",
      crop_id: "papa",
      sowing_date: "2027-01-01",
      irrigated: true,
      lot_id: "a1",
    });
  });

  it("la consulta va y vuelve de la dirección", () => {
    const form: ConsultForm = { ...EMPTY_FORM, municipalityId: "15646", cropId: "papa", month: "2027-01", irrigation: "nose" };
    expect(toParams(form).toString()).toBe("municipio=15646&cultivo=papa&siembra=2027-01&riego=nose");
    expect(fromParams(toParams(form))).toEqual(form);
    expect(toParams({ ...form, lotId: "a1" }).toString()).toBe("lote=a1&cultivo=papa&siembra=2027-01");
  });

  it("solo valen opciones del catálogo: un municipio o un mes que no están, o un abono verde, no pasan", () => {
    const catalogs = { municipalities: MUNICIPALITIES, crops: CROPS, months: MONTHS.map((m) => m.value) };
    const ok: ConsultForm = { ...EMPTY_FORM, municipalityId: "15646", cropId: "papa", month: MONTHS[0].value, irrigation: "si" };
    expect(validate(ok, catalogs)).toEqual({});
    expect(validate({ ...ok, municipalityId: "99999" }, catalogs)).toHaveProperty("municipality");
    expect(validate({ ...ok, cropId: "avena_vicia" }, catalogs)).toHaveProperty("crop");
    expect(validate({ ...ok, month: "2020-01" }, catalogs)).toHaveProperty("month");
    expect(validate({ ...ok, irrigation: "" }, catalogs)).toHaveProperty("irrigation");
  });
});

describe("Pantalla del diagnóstico (HU-091)", () => {
  it("busca el municipio con autocompletado, ofrece solo cultivos y pide el diagnóstico con la fecha del día 1", async () => {
    const calls = fakeApi(CATALOGS);
    const router = open(PATHS.diagnosis);
    const user = userEvent.setup();

    const place = await screen.findByRole("combobox", { name: "Municipio" });
    await user.type(place, "sama");
    await user.click(await screen.findByRole("option", { name: /Samacá/ }));

    const crop = screen.getByLabelText("Cultivo");
    await waitFor(() => expect(within(crop).getByRole("option", { name: "Papa" })).toBeInTheDocument());
    // Para el diagnóstico, solo `kind = crop`: ni abonos verdes ni descanso.
    expect(within(crop).queryByRole("option", { name: "Avena con vicia" })).not.toBeInTheDocument();
    expect(within(crop).queryByRole("option", { name: "Descanso" })).not.toBeInTheDocument();
    await user.selectOptions(crop, "papa");

    const month = screen.getByLabelText("¿Cuándo quiere sembrar?");
    expect(within(month).getAllByRole("option")).toHaveLength(13); // «Elija un mes» y los doce
    await user.selectOptions(month, MONTHS[2].value);
    await user.click(screen.getByRole("radio", { name: "No sé" }));
    await user.click(screen.getByRole("button", { name: "Ver el diagnóstico" }));

    expect(await screen.findByText("Puede sembrar en esa fecha")).toBeInTheDocument();
    expect(calls.find((call) => call.key === "POST /api/v1/diagnostics")?.body).toEqual({
      municipality_id: "15646",
      crop_id: "papa",
      sowing_date: `${MONTHS[2].value}-01`,
      irrigated: null,
      lot_id: null,
    });
    expect(router.state.location.search).toBe(`?municipio=15646&cultivo=papa&siembra=${MONTHS[2].value}&riego=nose`);
    // La respuesta simulada lleva su rótulo de ejemplo (R5).
    expect(screen.getByText("respuesta simulada")).toBeInTheDocument();
  });

  it("sin completar, dice en pantalla qué falta y no pide nada", async () => {
    const calls = fakeApi(CATALOGS);
    open(PATHS.diagnosis);
    const user = userEvent.setup();
    await screen.findByRole("combobox", { name: "Municipio" });
    await waitFor(() => expect(screen.getByRole("button", { name: "Ver el diagnóstico" })).toBeEnabled());
    await user.click(screen.getByRole("button", { name: "Ver el diagnóstico" }));

    expect(screen.getByText("Elija su municipio de la lista.")).toBeInTheDocument();
    expect(screen.getByText("Elija un cultivo de la lista.")).toBeInTheDocument();
    expect(screen.getByText("Elija el mes en que quiere sembrar.")).toBeInTheDocument();
    expect(screen.getByText("Diga si tiene riego. Si no sabe, elija «No sé».")).toBeInTheDocument();
    // Al corregir un campo, su error se va en el acto.
    await user.selectOptions(screen.getByLabelText("Cultivo"), "arveja");
    expect(screen.queryByText("Elija un cultivo de la lista.")).not.toBeInTheDocument();
    expect(calls.some((call) => call.key === "POST /api/v1/diagnostics")).toBe(false);
  });

  it("valida cada campo apenas se usa, sin esperar a enviar, y el error queda enlazado al campo", async () => {
    fakeApi(CATALOGS);
    open(PATHS.diagnosis);
    const user = userEvent.setup();
    const place = await screen.findByRole("combobox", { name: "Municipio" });
    await waitFor(() => expect(screen.getByRole("button", { name: "Ver el diagnóstico" })).toBeEnabled());

    // Escribe sin elegir de la lista y sale del campo: el error aparece en el acto.
    await user.type(place, "Bogotá");
    await user.tab();
    const error = screen.getByText("Elija su municipio de la lista.");
    expect(place).toHaveAttribute("aria-invalid", "true");
    expect(place).toHaveAttribute("aria-describedby", error.id);
    expect(place).toHaveValue(""); // lo escrito a mano no es un valor
    // Los campos que no ha tocado todavía no muestran error.
    expect(screen.queryByText("Elija un cultivo de la lista.")).not.toBeInTheDocument();

    // Elegir un cultivo y volver a «Elija un cultivo» lo marca en el acto.
    const crop = screen.getByLabelText("Cultivo");
    await user.selectOptions(crop, "papa");
    expect(screen.queryByText("Elija un cultivo de la lista.")).not.toBeInTheDocument();
    await user.selectOptions(crop, "");
    expect(screen.getByText("Elija un cultivo de la lista.")).toBeInTheDocument();
    expect(crop).toHaveAttribute("aria-invalid", "true");

    // Al elegir de la lista, el error del municipio se va.
    await user.type(place, "zipa");
    await user.click(await screen.findByRole("option", { name: /Zipaquirá/ }));
    expect(screen.queryByText("Elija su municipio de la lista.")).not.toBeInTheDocument();
    expect(place).not.toHaveAttribute("aria-invalid");
  });

  it("sin catálogo no hay consulta, y dice el motivo que da la API", async () => {
    fakeApi({
      ...CATALOGS,
      "GET /api/v1/catalogs/municipalities": {
        status: 503,
        body: { error: { code: "dataset_unavailable", message: "El dataset no está publicado.", request_id: "r1" } },
      },
    });
    open(PATHS.diagnosis);
    expect(await screen.findByText(/No pudimos cargar los municipios y los cultivos: El dataset no está publicado\./)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Ver el diagnóstico" })).not.toBeInTheDocument();
  });

  it("una consulta en la dirección con un cultivo que no es del diagnóstico se marca de una vez y no se pide", async () => {
    const calls = fakeApi(CATALOGS);
    open(`${PATHS.diagnosis}?municipio=15646&cultivo=avena_vicia&siembra=${MONTHS[0].value}&riego=si`);
    expect(await screen.findByText("Elija un cultivo de la lista.")).toBeInTheDocument();
    expect(calls.some((call) => call.key === "POST /api/v1/diagnostics")).toBe(false);
  });

  it("una consulta completa en la dirección se abre ya calculada", async () => {
    const calls = fakeApi(CATALOGS);
    open(`${PATHS.diagnosis}?municipio=15646&cultivo=papa&siembra=${MONTHS[0].value}&riego=si`);
    expect(await screen.findByText("Puede sembrar en esa fecha")).toBeInTheDocument();
    expect(calls.find((call) => call.key === "POST /api/v1/diagnostics")?.body).toMatchObject({ irrigated: true });
    // El formulario muestra la consulta de la dirección, también el municipio, que llega cuando carga el catálogo.
    expect(screen.getByRole("combobox", { name: "Municipio" })).toHaveValue("Samacá");
    expect(screen.getByLabelText("Cultivo")).toHaveValue("papa");
    expect(screen.getByRole("radio", { name: "Sí" })).toBeChecked();
    expect(screen.getByText("Cosecha estimada con la duración de las etapas del cultivo. No es pronóstico.")).toBeInTheDocument();
  });

  it("sin cuenta no pide los lotes", async () => {
    const calls = fakeApi(CATALOGS);
    open(PATHS.diagnosis);
    await screen.findByRole("combobox", { name: "Municipio" });
    expect(calls.some((call) => call.key === "GET /api/v1/lots")).toBe(false);
    expect(screen.queryByLabelText("¿Para cuál terreno?")).not.toBeInTheDocument();
  });

  it("con un lote, no pregunta municipio ni riego: salen del lote", async () => {
    const calls = fakeApi({
      ...CATALOGS,
      "GET /api/v1/me": { status: 200, body: ROSA },
      "GET /api/v1/lots": { status: 200, body: [LOT] },
    });
    open(PATHS.diagnosis);
    const user = userEvent.setup();
    const land = await screen.findByLabelText("¿Para cuál terreno?");
    await user.selectOptions(land, "a1");

    expect(screen.queryByRole("combobox", { name: "Municipio" })).not.toBeInTheDocument();
    expect(screen.queryByRole("radio", { name: "No sé" })).not.toBeInTheDocument();
    expect(screen.getByText(/Zipaquirá, Cundinamarca, el de su lote/)).toBeInTheDocument();
    expect(screen.getByText("Con riego")).toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText("Cultivo"), "papa");
    await user.selectOptions(screen.getByLabelText("¿Cuándo quiere sembrar?"), MONTHS[1].value);
    await user.click(screen.getByRole("button", { name: "Ver el diagnóstico" }));

    await screen.findByText("Puede sembrar en esa fecha");
    expect(calls.find((call) => call.key === "POST /api/v1/diagnostics")?.body).toEqual({
      municipality_id: "25899",
      crop_id: "papa",
      sowing_date: `${MONTHS[1].value}-01`,
      irrigated: true,
      lot_id: "a1",
    });
  });

  it("un lote en la dirección sin sesión no se consulta y lo dice", async () => {
    const calls = fakeApi(CATALOGS);
    open(`${PATHS.diagnosis}?lote=a1&cultivo=papa&siembra=${MONTHS[0].value}`);
    expect(await screen.findByText(/Ese lote no está entre los suyos/)).toBeInTheDocument();
    expect(calls.some((call) => call.key === "POST /api/v1/diagnostics")).toBe(false);
  });

  it("en modo ligero se ve completa, con el mismo formulario", async () => {
    setLightMode(true);
    fakeApi(CATALOGS);
    open(PATHS.diagnosis);
    expect(await screen.findByRole("heading", { level: 1, name: "¿Conviene sembrar en esa fecha?" })).toBeInTheDocument();
    expect(await screen.findByRole("combobox", { name: "Municipio" })).toBeInTheDocument();
    expect(screen.getByLabelText("Cultivo")).toBeInTheDocument();
    expect(screen.getByLabelText("¿Cuándo quiere sembrar?")).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "No sé" })).toBeInTheDocument();
  });

  describe("Estados de carga, vacío y error (HU-094)", () => {
    it("muestra el esqueleto de carga con el resumen mientras la API calcula", async () => {
      // Simula que la API se queda pensando (promesa pendiente)
      vi.stubGlobal("fetch", async (url: string, init: RequestInit = {}) => {
        const key = `${init.method ?? "GET"} ${url}`;
        if (key === "GET /api/v1/catalogs/municipalities") return new Response(JSON.stringify(MUNICIPALITIES), { status: 200 });
        if (key === "GET /api/v1/catalogs/crops") return new Response(JSON.stringify(CROPS), { status: 200 });
        if (key === "POST /api/v1/diagnostics") {
          // Devolvemos una promesa que nunca se resuelve para simular la carga
          return new Promise(() => {});
        }
        return new Response(null, { status: 404 });
      });
      open(`${PATHS.diagnosis}?municipio=15646&cultivo=papa&siembra=${MONTHS[2].value}&riego=si`);
      // Verifica que aparezca el esqueleto de carga con el resumen
      expect(await screen.findByRole("heading", { name: "Calculando su diagnóstico…" })).toBeInTheDocument();
      expect(screen.getByText(/Papa ·.*· Samacá/)).toBeInTheDocument();
      expect(screen.getByText("Calculando su diagnóstico. Por favor espere.")).toBeInTheDocument();
    });
    it("un fallo del servidor (500) muestra la tarjeta de error con código de soporte y botón reintentar", async () => {
      fakeApi({
        ...CATALOGS,
        "POST /api/v1/diagnostics": {
          status: 500,
          headers: { "x-request-id": "req-soporte-789" },
          body: { error: { code: "internal_error", message: "Falla interna", request_id: "req-soporte-789" } },
        },
      });
      open(`${PATHS.diagnosis}?municipio=15646&cultivo=papa&siembra=${MONTHS[2].value}&riego=si`);
      expect(await screen.findByRole("heading", { name: "Algo falló de nuestro lado" })).toBeInTheDocument();
      expect(screen.getByText(/No pudimos calcular su diagnóstico/)).toBeInTheDocument();
      expect(screen.getByText("req-soporte-789")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Reintentar" })).toBeInTheDocument();
    });
    it("si no hay otro lote, el 404 permite consultar por municipio sin usar el lote", async () => {
      const calls = fakeApi({
        ...CATALOGS,
        "GET /api/v1/me": { status: 200, body: ROSA },
        "GET /api/v1/lots": { status: 200, body: [LOT] },
        "POST /api/v1/diagnostics": [
          { status: 404, body: { error: { code: "not_found", message: "Ese lote no existe o no es suyo." } } },
          { status: 200, body: RESPONSE },
        ],
      });
      const user = userEvent.setup();
      const router = open(`${PATHS.diagnosis}?lote=a1&cultivo=papa&siembra=${MONTHS[2].value}`);
      expect(await screen.findByRole("heading", { name: "Ese lote no existe o no es suyo" })).toBeInTheDocument();
      expect(screen.getByRole("alert")).toBeInTheDocument();
      expect(screen.queryByText("Sin datos de este municipio")).not.toBeInTheDocument();
      expect(calls.find((call) => call.key === "POST /api/v1/diagnostics")?.body).toMatchObject({ lot_id: "a1" });
      expect(screen.queryByRole("button", { name: "Elegir otro lote" })).not.toBeInTheDocument();
      await user.click(screen.getByRole("button", { name: "Consultar sin lote" }));
      expect(await screen.findByText("Puede sembrar en esa fecha")).toBeInTheDocument();
      await waitFor(() => {
        expect(router.state.location.search).toContain("municipio=25899");
        expect(router.state.location.search).not.toContain("lote=");
      });
      const diagnosisCalls = calls.filter((call) => call.key === "POST /api/v1/diagnostics");
      expect(diagnosisCalls[1].body).toMatchObject({
        municipality_id: "25899",
        irrigated: true,
        crop_id: "papa",
        lot_id: null,
      });
    });
    it("si hay otros lotes, el botón de elegir otro enfoca el selector", async () => {
      fakeApi({
        ...CATALOGS,
        "GET /api/v1/me": { status: 200, body: ROSA },
        "GET /api/v1/lots": { status: 200, body: [LOT, OTHER_LOT] },
        "POST /api/v1/diagnostics": {
          status: 404,
          body: { error: { code: "not_found", message: "Ese lote no existe o no es suyo." } },
        },
      });
      const user = userEvent.setup();
      open(`${PATHS.diagnosis}?lote=a1&cultivo=papa&siembra=${MONTHS[2].value}`);
      expect(await screen.findByRole("heading", { name: "Ese lote no existe o no es suyo" })).toBeInTheDocument();
      expect(screen.getByRole("alert")).toBeInTheDocument();
      const lotSelector = screen.getByLabelText("¿Para cuál terreno?");
      await user.click(screen.getByRole("button", { name: "Elegir otro lote" }));
      expect(lotSelector).toHaveFocus();
      expect(lotSelector).toHaveTextContent("La Vega");
    });
    it("una fecha fuera de rango permite corregir el mes", async () => {
      fakeApi({
        ...CATALOGS,
        "POST /api/v1/diagnostics": {
          status: 422,
          body: {
            error: {
              code: "invalid_input",
              message: "La fecha de siembra debe estar entre este mes y los próximos doce.",
            },
          },
        },
      });

      const user = userEvent.setup();
      open(`${PATHS.diagnosis}?municipio=15646&cultivo=papa&siembra=${MONTHS[2].value}&riego=si`);

      expect(
        await screen.findByRole("heading", {
          name: "Esa fecha no se puede consultar",
        }),
      ).toBeInTheDocument();

      await user.click(screen.getByRole("button", { name: "Cambiar la fecha" }));

      expect(screen.getByRole("combobox", { name: "¿Cuándo quiere sembrar?" })).toHaveFocus();
    });
    it("un 422 muestra el mensaje de la API y el botón devuelve el foco al formulario", async () => {
      fakeApi({
        ...CATALOGS,
        "POST /api/v1/diagnostics": {
          status: 422,
          body: { error: { code: "invalid_input", message: "Hay datos que no son válidos. Revise: priorities." } },
        },
      });
      const user = userEvent.setup();
      open(`${PATHS.diagnosis}?municipio=15646&cultivo=papa&siembra=${MONTHS[2].value}&riego=si`);
      expect(await screen.findByRole("heading", { name: "Revise lo que eligió" })).toBeInTheDocument();
      expect(screen.getByText("Hay datos que no son válidos. Revise: priorities.")).toBeInTheDocument();
      await user.click(screen.getByRole("button", { name: "Volver al formulario" }));
      expect(screen.getByRole("combobox", { name: "Municipio" })).toHaveFocus();
    });
    it("un 501 dice que el cálculo aún no está disponible y no permite reintentar", async () => {
      fakeApi({
        ...CATALOGS,
        "POST /api/v1/diagnostics": {
          status: 501,
          body: { error: { code: "not_implemented", message: "Este cálculo todavía no está disponible." } },
        },
      });
      open(`${PATHS.diagnosis}?municipio=15646&cultivo=papa&siembra=${MONTHS[2].value}&riego=si`);
      expect(await screen.findByRole("heading", { name: "Este cálculo todavía no está disponible" })).toBeInTheDocument();
      expect(screen.queryByRole("button", { name: "Reintentar" })).not.toBeInTheDocument();
    });
    it("un 503 dataset_unavailable permite reintentar", async () => {
      fakeApi({
        ...CATALOGS,
        "POST /api/v1/diagnostics": {
          status: 503,
          body: { error: { code: "dataset_unavailable", message: "Los datos no están disponibles." } },
        },
      });
      open(`${PATHS.diagnosis}?municipio=15646&cultivo=papa&siembra=${MONTHS[2].value}&riego=si`);
      expect(await screen.findByRole("heading", { name: "Los datos no están disponibles en este momento" })).toBeInTheDocument();
      expect(screen.getByRole("alert")).toBeInTheDocument();
      expect(screen.getByText("Intente más tarde.")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Reintentar" })).toBeInTheDocument();
    });
    it("sin conexión a internet muestra la tarjeta de sin conexión con botón reintentar", async () => {
      vi.stubGlobal("fetch", async (url: string, init: RequestInit = {}) => {
        const key = `${init.method ?? "GET"} ${url}`;
        if (key === "GET /api/v1/catalogs/municipalities") return new Response(JSON.stringify(MUNICIPALITIES), { status: 200 });
        if (key === "GET /api/v1/catalogs/crops") return new Response(JSON.stringify(CROPS), { status: 200 });
        // Simula fallo de red
        throw new TypeError("Failed to fetch");
      });
      open(`${PATHS.diagnosis}?municipio=15646&cultivo=papa&siembra=${MONTHS[2].value}&riego=si`);
      expect(await screen.findByRole("heading", { name: "Sin conexión" })).toBeInTheDocument();
      expect(screen.getByText(/Revise la señal/)).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Reintentar" })).toBeInTheDocument();
    });
    it("los datos de ejemplo se rotulan con la etiqueta de respuesta simulada (R5)", async () => {
      fakeApi(CATALOGS);
      open(`${PATHS.diagnosis}?municipio=15646&cultivo=papa&siembra=${MONTHS[2].value}&riego=si`);
      // RESPONSE en los mocks usa `dataset: "ejemplo"`, por lo que debe mostrar el rótulo
      expect(await screen.findByText("respuesta simulada")).toBeInTheDocument();
    });
  });
});
