import { act, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, useLocation, RouterProvider, createMemoryRouter } from "react-router";
import { beforeEach, afterEach, describe, expect, it, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { routes } from "@/app/routes";
import { ApiLanguageNotice } from "@/components/ui/ApiLanguageNotice";
import { DiagnosisLights } from "@/pages/diagnosis/Lights";
import { IRRIGATION_CHOICES, monthName } from "@/features/diagnosis/consult";
import { SIGNAL_NAME } from "@/features/diagnosis/signals";
import { cropName, formatDate } from "@/features/farm/seasons";
import { formatHa } from "@/features/farm/lots";
import { explain422 } from "@/features/strategies/entry";
import { LanguageSelector } from "@/components/layout/LanguageSelector";
import { Link } from "@/components/layout/LanguageLink";
import { Preview } from "@/pages/landing/sections/Preview";
import es from "@/locales/es.json";
import en from "@/locales/en.json";
import { detectLanguage, i18n, initLanguage, LANGUAGE_KEY, languagePath } from "./i18n";

function Location() {
  const { search, hash } = useLocation();
  return (
    <output>
      {search}
      {hash}
    </output>
  );
}

beforeEach(async () => {
  localStorage.removeItem(LANGUAGE_KEY);
  window.history.replaceState(null, "", "/");
  await i18n.changeLanguage("es");
});
afterEach(() => vi.unstubAllGlobals());

describe("HU-233 · idiomas", () => {
  it("los diccionarios tienen las mismas claves y variables", () => {
    expect(Object.keys(es).sort()).toEqual(Object.keys(en).sort());
    for (const key of Object.keys(es) as (keyof typeof es)[]) {
      expect(en[key].trim()).not.toBe("");
      expect(en[key].match(/{{\w+}}/g)?.sort()).toEqual(es[key].match(/{{\w+}}/g)?.sort());
    }
  });

  it("el español es el predeterminado y la URL prima sobre la preferencia", () => {
    expect(detectLanguage("", null)).toBe("es");
    expect(detectLanguage("", "en")).toBe("en");
    expect(detectLanguage("?lang=en", "es")).toBe("en");
    expect(detectLanguage("?lang=es", "en")).toBe("es");
    expect(detectLanguage("?lang=fr", "invalid")).toBe("es");
  });

  it("?lang=en abre en inglés y actualiza html lang", () => {
    window.history.replaceState(null, "", "/?lang=en");
    act(() => initLanguage());
    expect(i18n.resolvedLanguage).toBe("en");
    expect(document.documentElement.lang).toBe("en");
    expect(localStorage.getItem(LANGUAGE_KEY)).toBe("en");
  });

  it("el selector cambia el idioma, lo recuerda y conserva consulta y fragmento", async () => {
    render(
      <MemoryRouter initialEntries={["/?municipio=15646#ejemplo"]}>
        <LanguageSelector />
        <Location />
        <Link to="/consultar?ciclos=3#resultado">Continue</Link>
      </MemoryRouter>,
    );
    await userEvent.selectOptions(screen.getByRole("combobox", { name: "Idioma" }), "en");
    expect(screen.getByRole("combobox", { name: "Language" })).toHaveValue("en");
    expect(localStorage.getItem(LANGUAGE_KEY)).toBe("en");
    expect(screen.getByRole("status")).toHaveTextContent("?municipio=15646&lang=en#ejemplo");
    expect(screen.getByRole("link", { name: "Continue" })).toHaveAttribute("href", "/consultar?ciclos=3&lang=en#resultado");
    // Simula el siguiente arranque en otra ruta sin lang.
    act(() => initLanguage());
    expect(i18n.resolvedLanguage).toBe("en");
    await userEvent.selectOptions(screen.getByRole("combobox"), "es");
    expect(document.documentElement.lang).toBe("es");
    expect(screen.getByRole("status")).toHaveTextContent("?municipio=15646#ejemplo");
  });

  it("traduce el ejemplo, sus estados y fecha sin cambiar sus identificadores", async () => {
    await act(() => i18n.changeLanguage("en"));
    render(
      <MemoryRouter>
        <Preview animated={false} />
      </MemoryRouter>,
    );
    expect(screen.getByRole("heading", { name: "How a crop cycle is assessed" })).toBeInTheDocument();
    expect(screen.getByText("Example")).toBeInTheDocument();
    expect(screen.getByText(/August 2, 2027/)).toBeInTheDocument();
    const market = screen.getByText("Market").closest("li")!;
    expect(within(market).getByText("No data").closest("[data-tone]")).toHaveAttribute("data-tone", "insufficient_data");
    expect(screen.getByText("Yellow light")).toBeInTheDocument();
  });

  it("conserva el fragmento y los parámetros al construir enlaces", () => {
    expect(languagePath("/consultar?municipio=15646#ciclo", "en")).toBe("/consultar?municipio=15646&lang=en#ciclo");
    expect(languagePath("/consultar?lang=en&ciclos=3#ciclo", "es")).toBe("/consultar?ciclos=3#ciclo");
    expect(languagePath("/mi-finca/lotes/a1/editar?dibujar", "es")).toBe("/mi-finca/lotes/a1/editar?dibujar");
    expect(languagePath("/mi-finca/lotes/a1/editar?dibujar#mapa", "en")).toBe("/mi-finca/lotes/a1/editar?dibujar&lang=en#mapa");
  });

  it("actualiza etiquetas y formatos al cambiar el idioma, conservando valores del contrato", async () => {
    expect(SIGNAL_NAME().water).toBe("Agua");
    expect(formatHa(2.5)).toBe("2,50 ha");
    await i18n.changeLanguage("en");
    expect(SIGNAL_NAME().water).toBe("Water");
    expect(IRRIGATION_CHOICES().map((item) => item.value)).toEqual(["si", "no", "nose"]);
    expect(IRRIGATION_CHOICES().map((item) => item.label)).toEqual(["Yes", "No", "I don't know"]);
    expect(monthName("2027-08")).toBe("August 2027");
    expect(formatDate("2027-08-02")).toBe("August 2, 2027");
    expect(formatHa(2.5)).toBe("2.50 ha");
    expect(cropName({ crop_id: "maiz", name_es: "Maíz" })).toBe("Maize");
    expect(cropName({ crop_id: "desconocido", name_es: "Nombre del catálogo" })).toBe("Nombre del catálogo");
  });

  it("muestra entrar en inglés y cambia a español sin perder lo escrito", async () => {
    vi.stubGlobal("fetch", async () =>
      Response.json({ error: { code: "unauthorized", message: "Inicie sesión para continuar." } }, { status: 401 }),
    );
    await i18n.changeLanguage("en");
    render(<RouterProvider router={createMemoryRouter(routes, { initialEntries: ["/entrar?lang=en"] })} />);
    await act(async () => {
      await vi.dynamicImportSettled();
    });
    expect(await screen.findByRole("heading", { level: 1, name: "Return to your farm" })).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("Username"), "rosa.samaca");
    await userEvent.selectOptions(screen.getByRole("combobox", { name: "Language" }), "es");
    expect(screen.getByRole("heading", { level: 1, name: "Vuelva a su finca" })).toBeInTheDocument();
    expect(screen.getByLabelText("Usuario")).toHaveValue("rosa.samaca");
    expect(document.title).toBe("Entrar · AgroSense");
  });

  it("conserva las razones de la API en español y muestra el aviso en inglés", async () => {
    vi.stubGlobal("fetch", async () => Response.json({}, { status: 503 }));
    await i18n.changeLanguage("en");
    const overall = {
      light: "yellow" as const,
      action: "other_window" as const,
      reasons: ["Esta razón original viene de la API"],
      limiting_signal: "frost" as const,
      high_risk: false,
      weights_basis: "default" as const,
    };
    render(
      <QueryClientProvider client={new QueryClient()}>
        <DiagnosisLights
          overall={overall}
          overallDefault={overall}
          weights={{ water: 3, frost: 3, heat: 3, soil: 2, supply: 2, market: 1 }}
        />
        <ApiLanguageNotice />
      </QueryClientProvider>,
    );
    expect(screen.getByText("Calculation details are in Spanish")).toBeInTheDocument();
    expect(screen.getByText("Esta razón original viene de la API").closest("[lang]")).toHaveAttribute("lang", "es");
    expect(screen.getByText("Consider another planting date")).toBeInTheDocument();
    expect(explain422("Hay datos inválidos. Revise: priorities.")).toBe("Hay datos inválidos. Revise: priorities.");
  });
});
