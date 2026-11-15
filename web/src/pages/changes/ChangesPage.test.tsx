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
    if (path === "/version") return examples.catalogs.version;
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
  const heading = screen.getByRole("heading", { name: "Temperatura máxima habitual" });
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
  const rain = within(screen.getByRole("heading", { name: "Lluvia normal" }).parentElement!);
  expect(rain.getAllByText(/Entre 2001 y 2012/).length).toBeGreaterThan(0);
  expect(rain.getAllByText(/Entre 2013 y 2024/).length).toBeGreaterThan(0);
  expect(rain.queryByText(/Entre 1981 y 2000/)).not.toBeInTheDocument();
  for (const name of ["Heladas", "Temperatura máxima habitual"]) {
    const climate = within(screen.getByRole("heading", { name }).parentElement!);
    expect(climate.getAllByText(/Entre 1981 y 2000/).length).toBeGreaterThan(0);
    expect(climate.getAllByText(/Entre 2005 y 2024/).length).toBeGreaterThan(0);
    expect(climate.queryByText(/Entre 2001 y 2012/)).not.toBeInTheDocument();
  }
});

it.each([501, 503, 0, 422, 500])("explica el error %i con el estado compartido y las acciones adecuadas", async (status) => {
  answer(fixture(), new ApiError(status, "error", "Mensaje interno crudo", "soporte-219"));
  open();
  expect(await screen.findByRole("alert")).toBeInTheDocument();
  expect(screen.queryByRole("heading", { name: "Heladas" })).not.toBeInTheDocument();
  expect(screen.queryByText("Mensaje interno crudo")).not.toBeInTheDocument();
  if (status === 501 || status === 422) {
    expect(screen.queryByRole("button", { name: "Reintentar" })).not.toBeInTheDocument();
    if (status === 501) expect(screen.getByText("Esta versión de AgroSense todavía no calcula esta comparación.")).toBeInTheDocument();
  } else {
    const before = mockedApi.mock.calls.filter(([path]) => path.startsWith("/changes?")).length;
    await userEvent.click(screen.getByRole("button", { name: "Reintentar" }));
    expect(mockedApi.mock.calls.filter(([path]) => path.startsWith("/changes?")).length).toBeGreaterThan(before);
  }
  if (status === 500) expect(screen.getByText("soporte-219")).toBeInTheDocument();
});

it("un municipio fuera de la región es «sin cobertura» y deja elegir otro (HU-094)", async () => {
  const message = "AgroSense todavía no tiene datos de ese municipio: por ahora cubre Boyacá y Cundinamarca.";
  answer(fixture(), new ApiError(422, "outside_region", message, "soporte-094"));
  open();
  expect(await screen.findByRole("heading", { name: "Sin datos de este municipio" })).toBeInTheDocument();
  expect(screen.getByText(message)).toBeInTheDocument();
  expect(screen.queryByText("Revise lo que eligió")).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Elegir otro municipio" }));
  expect(screen.getByRole("combobox", { name: "Municipio" })).toHaveFocus();
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

it.each([
  { name: "una siembra", seasons: [{ crop_id: "papa" }], expected: "papa" },
  { name: "varias siembras", seasons: [{ crop_id: "papa" }, { crop_id: "papa" }], expected: "" },
  { name: "ninguna siembra", seasons: [], expected: "" },
])("desde el lote con $name preselecciona solo cuando corresponde", async ({ seasons, expected }) => {
  answer();
  open("/", <LotChangesLink municipalityId="15646" irrigated={true} currentSeasons={seasons} />);
  await screen.findByRole("option", { name: "Papa" });
  const select = screen.getByLabelText("Cultivo para comparar la historia de la zona");
  expect(select).toHaveValue(expected);
  if (expected) {
    expect(screen.getByRole("link", { name: "Ver qué cambió en su zona" })).toHaveAttribute("href", changesLink("15646", "papa", true));
    await userEvent.selectOptions(select, "");
    expect(screen.queryByRole("link", { name: "Ver qué cambió en su zona" })).not.toBeInTheDocument();
  } else {
    expect(screen.queryByRole("link", { name: "Ver qué cambió en su zona" })).not.toBeInTheDocument();
  }
  await userEvent.selectOptions(select, "papa");
  expect(screen.getByRole("link", { name: "Ver qué cambió en su zona" })).toHaveAttribute("href", changesLink("15646", "papa", true));
});

it("distingue un mes ausente de un indicador sin datos", async () => {
  const response = fixture();
  response.months = [response.months[0]];
  answer(response);
  open();
  await screen.findByRole("heading", { name: "Heladas" });
  const section = screen.getByRole("heading", { name: "Heladas" }).parentElement!;
  const february = within(section).getByRole("heading", { name: "Febrero" }).parentElement!;
  expect(within(february).getByText("La respuesta no trae este mes.")).toBeInTheDocument();
  expect(within(february).queryByText("Sin datos suficientes")).not.toBeInTheDocument();
});
