import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RouterProvider, createMemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { PATHS } from "@/app/paths";
import { routes } from "@/app/routes";
import { sowingMonths } from "@/features/diagnosis/consult";
import { STORAGE_KEY, asWeights, readStored } from "@/features/diagnosis/priorities";
import { setLightMode } from "@/lib/lightMode";

// Datos de ejemplo de las pruebas (R5): catálogo, pesos por defecto, cuenta y respuesta de muestra.
const MONTH = sowingMonths()[0].value;
const DEFAULTS = { water: 3, frost: 3, heat: 3, soil: 2, supply: 2, market: 1 };
const VERSION = {
  dataset_version: "2026.11.0",
  rules_version: "1.0.0",
  created_at: null,
  region: "co-boyaca-cundinamarca",
  default_weights: DEFAULTS,
  weights_version: "1",
  weights_reasons: {},
  sources: [],
};
const ROSA = {
  user_id: "1",
  username: "rosa.samaca",
  display_name: "Rosa",
  role: "farmer",
  consent_version: 3,
  consent_at: "2026-08-02T13:40:00Z",
  priorities: null as Record<string, number> | null,
  created_at: "2026-08-02T13:40:00Z",
};
const RESPONSE = {
  request: { municipality_id: "15646", crop_id: "papa", sowing_date: `${MONTH}-01`, irrigated: true, lot_id: null },
  suitability: { level: "suitable", score: 90, basis: "municipality", reasons: [] },
  window: null,
  overall: { light: "green", action: "sow", high_risk: false, weights_basis: "farmer", reasons: [] },
  overall_default: { light: "green", action: "sow", high_risk: false, weights_basis: "default", reasons: [] },
  weights: DEFAULTS,
  signals: null,
  limitations: [],
  versions: { dataset: "2026.11.0", rules: "1.0.0" },
};

type Reply = { status: number; body?: unknown };
function fakeApi(extra: Record<string, Reply> = {}) {
  const calls: { key: string; body: unknown }[] = [];
  const replies: Record<string, Reply> = {
    "GET /api/v1/catalogs/municipalities": {
      status: 200,
      body: [{ municipality_id: "15646", name: "Samacá", department: "Boyacá", lat: 5.49, lon: -73.49 }],
    },
    "GET /api/v1/catalogs/crops": {
      status: 200,
      body: [{ crop_id: "papa", name_es: "Papa", kind: "crop", archetype: "tuber", family: "solanaceae", cycle_months: 5.4 }],
    },
    "GET /api/v1/version": { status: 200, body: VERSION },
    "POST /api/v1/diagnostics": { status: 200, body: RESPONSE },
    ...extra,
  };
  vi.stubGlobal("fetch", async (url: string, init: RequestInit = {}) => {
    const key = `${init.method ?? "GET"} ${url}`;
    calls.push({ key, body: init.body ? JSON.parse(String(init.body)) : undefined });
    const reply = replies[key] ?? { status: 401, body: { error: { code: "unauthorized", message: "No." } } };
    return new Response(reply.body === undefined ? null : JSON.stringify(reply.body), { status: reply.status });
  });
  return calls;
}
const diagnoses = (calls: { key: string; body: unknown }[]) =>
  calls.filter((c) => c.key === "POST /api/v1/diagnostics").map((c) => c.body as { priorities?: Record<string, number> });

const open = () =>
  render(
    <RouterProvider
      router={createMemoryRouter(routes, { initialEntries: [`${PATHS.diagnosis}?municipio=15646&cultivo=papa&siembra=${MONTH}&riego=si`] })}
    />,
  );
/** Abre el resumen plegado de las prioridades. */
async function openPanel(user: ReturnType<typeof userEvent.setup>, title = "Criterio de AgroSense · Ajustar") {
  await user.click(await screen.findByText(title));
}
const seeds = (label: string) => within(screen.getByRole("radiogroup", { name: new RegExp(`^${label}:`) }));
const checked = (label: string) => seeds(label).getByRole("radio", { checked: true }).getAttribute("data-level");

beforeEach(() => localStorage.clear());
afterEach(() => {
  vi.unstubAllGlobals();
  setLightMode(false);
  localStorage.clear();
});

describe("Prioridades guardadas (HU-202)", () => {
  it("solo valen seis pesos enteros de 0 a 5; lo demás o todo en 0 no se usa", () => {
    expect(asWeights(DEFAULTS)).toEqual(DEFAULTS);
    expect(asWeights({ ...DEFAULTS, water: 6 })).toBeNull();
    expect(asWeights({ ...DEFAULTS, frost: 2.5 })).toBeNull();
    expect(asWeights({ water: 3 })).toBeNull();
    localStorage.setItem(STORAGE_KEY, "no es json");
    expect(readStored()).toBeNull();
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ water: 0, frost: 0, heat: 0, soil: 0, supply: 0, market: 0 }));
    expect(readStored()).toBeNull();
  });
});

describe("Ajustar mis prioridades al consultar (HU-202)", () => {
  it("empiezan en el criterio de AgroSense, con un control de 0 a 5 por señal que se califica y el texto de qué significan", async () => {
    const calls = fakeApi();
    open();
    const user = userEvent.setup();
    await screen.findByText("Puede sembrar en esa fecha");
    // Antes de tocar nada, se consulta con los pesos de AgroSense: los seis, también los de la oferta y el mercado.
    expect(diagnoses(calls)[0].priorities).toEqual(DEFAULTS);

    await openPanel(user);
    // La oferta se muestra sin calificar (decisión 17): su peso no tiene efecto y no se dibuja su control. El mercado sí
    // (HU-240): con 4 o 5 ordena las ventanas, y su nota dice que no cambia la luz.
    expect(screen.getAllByRole("radiogroup")).toHaveLength(5);
    expect(screen.queryByRole("radiogroup", { name: /^Oferta:/ })).not.toBeInTheDocument();
    expect(checked("Mercado")).toBe("1");
    expect(screen.getByText("Solo ordena las ventanas con 4 o 5; no cambia la luz")).toBeInTheDocument();
    expect(screen.getByText("La oferta se muestra sin calificar y no tiene prioridad.")).toBeInTheDocument();
    expect(checked("Agua")).toBe("3");
    expect(checked("Suelo")).toBe("2");
    expect(seeds("Agua").getAllByRole("radio")).toHaveLength(6); // el «0» y cinco semillas
    expect(
      screen.getByText("0: no cambia la luz, salvo un riesgo grave de clima. 4 o 5: un resultado medio cuenta como desfavorable."),
    ).toBeInTheDocument();
    // Con el criterio de AgroSense no hay nada a qué volver: el botón no se dibuja sin función.
    expect(screen.queryByRole("button", { name: "Volver al criterio de AgroSense" })).not.toBeInTheDocument();
  });

  it("al cambiar uno, vuelve a pedir el diagnóstico con esas prioridades y las recuerda en el navegador", async () => {
    const calls = fakeApi();
    open();
    const user = userEvent.setup();
    await screen.findByText("Puede sembrar en esa fecha");
    await openPanel(user);
    await user.click(seeds("Agua").getByRole("radio", { name: /^5 de 5/ }));

    await waitFor(() => expect(diagnoses(calls).at(-1)?.priorities).toEqual({ ...DEFAULTS, water: 5 }));
    expect(screen.getByText("Sus prioridades · Ajustar")).toBeInTheDocument();
    expect(JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "null")).toEqual({ ...DEFAULTS, water: 5 });
    expect(screen.getByText("Se recuerdan en este dispositivo, sin cuenta.")).toBeInTheDocument();
  });

  it("«Volver al criterio de AgroSense» las restablece y vuelve a consultar con los pesos por defecto", async () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ ...DEFAULTS, water: 5 }));
    const calls = fakeApi();
    open();
    const user = userEvent.setup();
    await screen.findByText("Puede sembrar en esa fecha");
    // Al volver, se usan las que había dejado.
    expect(diagnoses(calls)[0].priorities).toEqual({ ...DEFAULTS, water: 5 });

    await openPanel(user, "Sus prioridades · Ajustar");
    await user.click(screen.getByRole("button", { name: "Volver al criterio de AgroSense" }));
    await waitFor(() => expect(diagnoses(calls).at(-1)?.priorities).toEqual(DEFAULTS));
    expect(localStorage.getItem(STORAGE_KEY)).toBeNull();
    expect(screen.getByText("Criterio de AgroSense · Ajustar")).toBeInTheDocument();
  });

  it("la oferta, sin control, se envía con el peso de AgroSense aunque haya otro guardado; el mercado, con el suyo", async () => {
    const stored = { ...DEFAULTS, water: 5, supply: 0, market: 5 };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(stored));
    const calls = fakeApi();
    open();
    await screen.findByText("Puede sembrar en esa fecha");
    // Los seis pesos: los suyos donde hay control (también el mercado, HU-240) y el de AgroSense en la oferta.
    expect(diagnoses(calls)[0].priorities).toEqual({ ...DEFAULTS, water: 5, market: 5 });
    // Lo guardado no cambia.
    expect(JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "null")).toEqual(stored);
  });

  it("con todas en 0 no envía la petición y pide subir al menos una", async () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ water: 1, frost: 0, heat: 0, soil: 0, supply: 0, market: 0 }));
    const calls = fakeApi();
    open();
    const user = userEvent.setup();
    await screen.findByText("Puede sembrar en esa fecha");
    const before = diagnoses(calls).length;

    await openPanel(user, "Sus prioridades · Ajustar");
    await user.click(seeds("Agua").getByRole("radio", { name: /^0 de 5/ }));

    expect(await screen.findByText(/Suba al menos una prioridad: con todas en 0/)).toBeInTheDocument();
    expect(screen.getByText(/Todas sus prioridades están en 0/)).toBeInTheDocument();
    expect(diagnoses(calls)).toHaveLength(before);
    // Todo en 0 no se guarda: queda lo último válido.
    expect(JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "null")).toMatchObject({ water: 1 });
  });

  it("con cuenta, empiezan en las de su perfil y al cambiar una se guardan en el perfil", async () => {
    const own = { ...DEFAULTS, frost: 5 };
    const calls = fakeApi({
      "GET /api/v1/me": { status: 200, body: { ...ROSA, priorities: own } },
      "GET /api/v1/lots": { status: 200, body: [] },
      "PATCH /api/v1/me": { status: 200, body: { ...ROSA, priorities: { ...own, soil: 4 } } },
    });
    open();
    const user = userEvent.setup();
    await screen.findByText("Puede sembrar en esa fecha");
    expect(diagnoses(calls)[0].priorities).toEqual(own);

    await openPanel(user, "Sus prioridades · Ajustar");
    expect(screen.getByText("Se guardan en su perfil, como en «Mi cuenta».")).toBeInTheDocument();
    await user.click(seeds("Suelo").getByRole("radio", { name: /^4 de 5/ }));
    // Se guardan y se consultan los seis pesos: la oferta y el mercado con los que tenía, aunque no tengan control.
    await waitFor(() => expect(calls.find((c) => c.key === "PATCH /api/v1/me")?.body).toEqual({ priorities: { ...own, soil: 4 } }));
    await waitFor(() => expect(diagnoses(calls).at(-1)?.priorities).toEqual({ ...own, soil: 4 }));
    expect(localStorage.getItem(STORAGE_KEY)).toBeNull();
  });

  it("si el criterio de AgroSense no carga, consulta igual con los pesos de la API y no lo pide en bucle", async () => {
    const calls = fakeApi({
      "GET /api/v1/version": { status: 503, body: { error: { code: "dataset_unavailable", message: "Sin dataset." } } },
    });
    open();
    expect(await screen.findByText("Puede sembrar en esa fecha")).toBeInTheDocument();
    expect(diagnoses(calls)[0]).not.toHaveProperty("priorities");
    expect(screen.getByText(/No pudimos cargar el criterio de AgroSense/)).toBeInTheDocument();
    await new Promise((resolve) => setTimeout(resolve, 300));
    expect(calls.filter((c) => c.key === "GET /api/v1/version")).toHaveLength(1);
    expect(diagnoses(calls)).toHaveLength(1);
  });

  it("en modo ligero el resumen se abre y los controles funcionan igual", async () => {
    setLightMode(true);
    const calls = fakeApi();
    open();
    const user = userEvent.setup();
    await screen.findByText("Puede sembrar en esa fecha");
    await openPanel(user);
    await user.click(seeds("Calor").getByRole("radio", { name: /^4 de 5/ }));
    await waitFor(() => expect(diagnoses(calls).at(-1)?.priorities).toEqual({ ...DEFAULTS, heat: 4 }));
  });
});
