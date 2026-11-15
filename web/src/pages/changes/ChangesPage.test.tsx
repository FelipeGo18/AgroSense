import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { api, ApiError } from "@/api/client";
import { changesLink, type ChangesResponse } from "@/features/changes/changes";
import examples from "@/mocks/examples.json";
import { ChangesPage } from "./ChangesPage";
import { LotChangesLink } from "./LotChangesLink";

vi.mock("@/api/client", async (original) => ({ ...(await original<typeof import("@/api/client")>()), api: vi.fn() }));
vi.mock("@/components/layout/TopBar", () => ({ TopBar: () => null }));
vi.mock("@/components/layout/Footer", () => ({ Footer: () => <footer>Pie</footer> }));

const mockedApi = vi.mocked(api);
const fixture = () => structuredClone(examples.routes["GET /changes"].ok.cambios) as ChangesResponse;

function answer(response = fixture(), failure?: ApiError) {
  mockedApi.mockImplementation(async (path) => {
    if (path === "/catalogs/municipalities") return examples.catalogs.municipalities;
    if (path === "/catalogs/crops") return examples.catalogs.crops;
    if (path.startsWith("/changes?")) {
      if (failure) throw failure;
      return response;
    }
    throw new Error(`Petición inesperada: ${path}`);
  });
}

function open(url = "/que-cambio?municipio=15646&cultivo=papa&riego=no", child = <ChangesPage />) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[url]}>{child}</MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  mockedApi.mockReset();
});

it("muestra periodos, unidades, ventanas y el aviso histórico, con riego en la consulta", async () => {
  answer();
  open();
  expect(await screen.findByRole("heading", { name: "Heladas" })).toBeInTheDocument();
  expect(screen.getByText("Así fue en la historia de su zona. No es un pronóstico")).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Las mejores fechas de siembra, antes y después" })).toBeInTheDocument();
  expect(screen.getAllByText(/Entre 1981 y 2000/).length).toBeGreaterThan(0);
  expect(screen.getByText(/Fuente: NASA POWER. Unidades: mm/)).toBeInTheDocument();
  expect(mockedApi).toHaveBeenCalledWith("/changes?municipality_id=15646&crop_id=papa&irrigated=false");
});

it("conserva el valor conocido y no inventa el cambio si falta un periodo", async () => {
  const response = fixture();
  response.months[0].tmax_p90_c = { status: "insufficient_data", before: null, after: 21.4, change: null };
  answer(response);
  open();
  await screen.findByRole("heading", { name: "Heladas" });
  const heading = screen.getByRole("heading", { name: "Temperatura máxima · percentil 90" });
  const january = heading.parentElement!.querySelector("li")!;
  expect(within(january).getByText("21,4 °C")).toBeInTheDocument();
  expect(within(january).getAllByText("Sin datos suficientes")).toHaveLength(2);
  expect(within(january).queryByText(/Cambio, después menos antes:/)).not.toBeInTheDocument();
});

it("con cultivo no apto muestra la razón y el clima, sin ventanas", async () => {
  const response = fixture();
  response.suitability.level = "not_suitable";
  response.suitability.reasons = ["Temperatura fuera del rango del cultivo."];
  response.best_windows = { before: [], after: [] };
  answer(response);
  open();
  expect(await screen.findByText("Este cultivo no se da en su zona")).toBeInTheDocument();
  expect(screen.getByText("Temperatura fuera del rango del cultivo.")).toBeInTheDocument();
  expect(screen.queryByRole("heading", { name: "Las mejores fechas de siembra, antes y después" })).not.toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Heladas" })).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Elegir otro cultivo" }));
  expect(screen.queryByRole("heading", { name: "Heladas" })).not.toBeInTheDocument();
});

it("usa los años de IMERG solo para lluvia y explica que empieza en 2000", async () => {
  const response = fixture();
  response.precip_periods = {
    before: { period_id: "before", start_year: 2001, end_year: 2012, source_id: "gpm_imerg" },
    after: { period_id: "after", start_year: 2013, end_year: 2024, source_id: "gpm_imerg" },
  };
  answer(response);
  open();
  expect(await screen.findByText(/Los datos de IMERG empiezan en 2000/)).toBeInTheDocument();
  expect(screen.getAllByText(/Entre 2001 y 2012/).length).toBeGreaterThan(0);
  expect(screen.getAllByText(/Entre 1981 y 2000/).length).toBeGreaterThan(0);
});

it.each([501, 503, 0])("explica el error %i sin mostrar un resultado vacío", async (status) => {
  answer(fixture(), new ApiError(status, "error", "No hay conexión o datos disponibles.", ""));
  open();
  expect(await screen.findByRole("alert")).toBeInTheDocument();
  expect(screen.queryByRole("heading", { name: "Heladas" })).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Volver a intentar" })).toBeInTheDocument();
});

it("no consulta un municipio que no pertenece al catálogo", async () => {
  answer();
  open("/que-cambio?municipio=99999&cultivo=papa");
  await screen.findByText("Elija un municipio del catálogo.");
  expect(mockedApi.mock.calls.some(([path]) => path.startsWith("/changes?"))).toBe(false);
});

it("desde el lote deja escoger el cultivo y conserva municipio y riego", async () => {
  answer();
  open("/", <LotChangesLink municipalityId="15646" irrigated={true} />);
  await screen.findByRole("option", { name: "Papa" });
  await userEvent.selectOptions(screen.getByLabelText("Cultivo para comparar la historia de la zona"), "papa");
  expect(screen.getByRole("link", { name: "Ver qué cambió en su zona" })).toHaveAttribute(
    "href",
    "/que-cambio?municipio=15646&cultivo=papa&riego=si",
  );
});

it("el enlace no inventa riego cuando no se conoce", () => {
  expect(changesLink("15646", "papa", null)).toBe("/que-cambio?municipio=15646&cultivo=papa");
});
