import { render, screen } from "@testing-library/react";
import { setupServer } from "msw/node";
import { api, ApiError } from "@/api/client";
import { SimulationStrip } from "@/components/layout/SimulationStrip";
import examples from "./examples.json";
import { handlers, SIMULATION_STATES } from "./handlers";

const server = setupServer(...handlers);

beforeAll(() => server.listen({ onUnhandledFrame: "error" }));
afterEach(() => {
  server.resetHandlers();
  window.history.replaceState(null, "", "/");
  vi.restoreAllMocks();
});
afterAll(() => server.close());

// `api()` llama a `/api/v1/...` con la dirección relativa, como en el navegador. En las pruebas se le da el origen.
beforeEach(() => {
  const realFetch = globalThis.fetch;
  vi.stubGlobal("fetch", (url: string, init?: RequestInit) => realFetch(new URL(url, window.location.origin), init));
});
afterEach(() => vi.unstubAllGlobals());

type Versions = { versions: { dataset: string; rules: string } };
type Diagnosis = Versions & { suitability: { level: string }; overall: { light: string } };
type Rotations = Versions & { strategies: { kind: string; cycles: unknown[] }[]; current_strategy: unknown };

const DIAGNOSIS_BODY = { municipality_id: "15001", crop_id: "papa", sowing_date: "2026-12-01" };
const diagnose = (estado?: string) => api<Diagnosis>(`/diagnostics${estado ? `?estado=${estado}` : ""}`, { body: DIAGNOSIS_BODY });

describe("respuestas simuladas (HU-013)", () => {
  it("responde todos los endpoints de cálculo P0, el suelo, los catálogos y las versiones", async () => {
    const calls: [string, unknown][] = [
      ["/diagnostics", DIAGNOSIS_BODY],
      ["/rotations", { municipality_id: "15001", area_ha: 1, sowing_date: "2026-12-01" }],
      ["/water-plans", { municipality_id: "15001", crops: [] }],
      ["/changes?municipality_id=15001&crop_id=papa", undefined],
      ["/trends?municipality_id=15001&crop_id=papa&sowing_date=2026-12-01", undefined],
      ["/catalogs/municipalities/15001/soil", undefined],
    ];
    for (const [path, body] of calls) {
      const response = await api<Versions>(path, { body });
      // Todo lo de cálculo y de suelo viene rotulado como ejemplo (R5).
      expect(response.versions).toEqual({ dataset: "ejemplo", rules: "ejemplo" });
    }
    expect(await api<unknown[]>("/catalogs/municipalities")).toHaveLength(examples.catalogs.municipalities.length);
    expect(await api<unknown[]>("/catalogs/crops")).toHaveLength(examples.catalogs.crops.length);
    expect(await api("/version")).toEqual(examples.catalogs.version);
  });

  it("las estrategias traen 3 ciclos y la rotación actual", async () => {
    const rotations = await api<Rotations>("/rotations", { body: {} });
    expect(rotations.strategies[0].cycles).toHaveLength(3);
    expect(rotations.current_strategy).not.toBeNull();
  });

  it("sin estado responde el primer ejemplo de la ruta", async () => {
    const diagnosis = await diagnose();
    expect(diagnosis.overall.light).toBe("green");
  });

  it("fuerza cada estado con ?estado= en la petición, por su nombre o por el del contrato", async () => {
    expect((await diagnose("no_apto")).suitability.level).toBe("not_suitable");
    expect((await diagnose("not_suitable")).suitability.level).toBe("not_suitable");
    expect((await diagnose("insufficient_data")).overall.light).toBe("not_evaluable");
  });

  it("fuerza el estado con ?estado= en la dirección de la página", async () => {
    window.history.replaceState(null, "", "/consultar?estado=no_apto");
    expect((await diagnose()).suitability.level).toBe("not_suitable");
  });

  it("fuerza un error por su número o por su código, con la forma de errores del contrato", async () => {
    for (const estado of ["503", "dataset_unavailable"]) {
      const error = await diagnose(estado).catch((e: unknown) => e);
      expect(error).toBeInstanceOf(ApiError);
      expect(error).toMatchObject({ status: 503, code: "dataset_unavailable" });
    }
    const unauthorized = await diagnose("unauthorized").catch((e: unknown) => e);
    expect(unauthorized).toMatchObject({ status: 401, code: "unauthorized" });
  });

  it("simula una falla de red", async () => {
    const error = await diagnose("sin_conexion").catch((e: unknown) => e);
    expect(error).toMatchObject({ status: 0, code: "offline" });
  });

  it("un estado que la ruta no tiene responde el de siempre y lo avisa", async () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
    const changes = await api<Versions>("/changes?municipality_id=15001&crop_id=papa&estado=no_apto");
    expect(changes.versions.dataset).toBe("ejemplo");
    expect(warn).toHaveBeenCalledWith(expect.stringContaining("no tiene el estado «no_apto»"));
  });

  it("lista los estados de cada ruta", () => {
    expect(SIMULATION_STATES["POST /diagnostics"]).toEqual(
      expect.arrayContaining(["favorable", "no_apto", "sin_agua", "no_aplica", "503", "dataset_unavailable"]),
    );
    expect(SIMULATION_STATES.todas).toEqual(["cargando", "sin_conexion"]);
  });

  it("la franja de simulación rotula las respuestas como ejemplo (R5)", () => {
    render(<SimulationStrip />);
    expect(screen.getByText("Ejemplo")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("respuestas simuladas");
  });
});
