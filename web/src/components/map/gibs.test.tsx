import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { Map as MapLibreMap } from "maplibre-gl";
import { useEffect } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { GibsPanel } from "./GibsPanel";
import { GIBS_LAYERS, gibsSample, gibsTiles, hasVisiblePixels, parseGibsDates, parseGibsEarliest } from "./gibs";
import { mountGibsColor, mountGibsLayer } from "./gibsMap";
import { GIBS_COLOR_LOOKBACK_DAYS, previousDay, useGibs } from "./useGibs";

// Fragmentos de ejemplo con la estructura del GetCapabilities verificado en HU-211; sin red en CI.
const XML = `<Capabilities xmlns="http://www.opengis.net/wmts/1.0" xmlns:ows="http://www.opengis.net/ows/1.1"><Contents>${Object.entries(
  GIBS_LAYERS,
)
  .map(
    ([key, spec]) =>
      `<Layer><ows:Identifier>${spec.product}</ows:Identifier><Dimension><ows:Identifier>Time</ows:Identifier><Default>2026-11-${key === "color" ? "15" : "14"}</Default><Value>${key === "color" ? "2000-02-24/2026-11-15/P1D" : "2025-02-12/2026-11-14/P8D"}</Value></Dimension><TileMatrixSetLink><TileMatrixSet>GoogleMapsCompatible_Level9</TileMatrixSet></TileMatrixSetLink><Format>${spec.format}</Format></Layer>`,
  )
  .join("")}</Contents></Capabilities>`;

function Panel() {
  return <GibsPanel gibs={useGibs()} />;
}

// El panel con el hook a mano, para avisar «sin imagen» como lo hace el mapa (`mountGibsColor`).
const hook: { current?: ReturnType<typeof useGibs> } = {};
function Harness() {
  const gibs = useGibs();
  useEffect(() => {
    hook.current = gibs;
  });
  return <GibsPanel gibs={gibs} />;
}
async function openColor() {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, text: async () => XML }));
  render(<Harness />);
  fireEvent.click(screen.getByText("Capas de la NASA"));
  fireEvent.click(screen.getByRole("checkbox", { name: "Imagen satelital" }));
  await screen.findByText("Fecha de la imagen: 2026-11-15");
}
const EMPTY =
  "No hay imagen para el centro de esta zona en la fecha elegida. Mostramos el mapa base. Pruebe una fecha anterior o mueva el mapa.";

describe("HU-211 · sin imagen en la fecha más reciente", () => {
  it("el día anterior se cuenta en UTC, también al cambiar de mes y de año", () => {
    expect(previousDay("2026-11-16")).toBe("2026-11-15");
    expect(previousDay("2026-03-01")).toBe("2026-02-28");
    expect(previousDay("2027-01-01")).toBe("2026-12-31");
  });

  it("con la fecha por defecto, una vista sin imagen prueba el día anterior y lo dice", async () => {
    await openColor();
    act(() => hook.current!.onStatus("color", "empty"));
    expect(screen.getByText("Fecha de la imagen: 2026-11-14")).toBeInTheDocument();
    expect(screen.getByText(/No hay imagen de la NASA del 2026-11-15/)).toBeInTheDocument();
    expect(screen.queryByText(EMPTY)).not.toBeInTheDocument();
    expect(screen.getByText("Cargando imágenes de la NASA…")).toBeInTheDocument();
  });

  it(`se detiene a los ${GIBS_COLOR_LOOKBACK_DAYS} días y entonces dice que no hay imagen`, async () => {
    await openColor();
    for (let i = 0; i <= GIBS_COLOR_LOOKBACK_DAYS; i++) act(() => hook.current!.onStatus("color", "empty"));
    expect(screen.getByText("Fecha de la imagen: 2026-11-10")).toBeInTheDocument();
    expect(screen.getByText(EMPTY)).toBeInTheDocument();
  });

  it("una fecha que elige la persona no se cambia en silencio", async () => {
    await openColor();
    fireEvent.change(screen.getByLabelText("Fecha · Imagen satelital"), { target: { value: "2026-11-13" } });
    act(() => hook.current!.onStatus("color", "empty"));
    expect(screen.getByText("Fecha de la imagen: 2026-11-13")).toBeInTheDocument();
    expect(screen.getByText(EMPTY)).toBeInTheDocument();
    expect(screen.queryByText(/No hay imagen de la NASA del/)).not.toBeInTheDocument();
  });

  it("el verdor (NDVI) no cambia de fecha: es un compuesto de 8 días", async () => {
    await openColor();
    fireEvent.click(screen.getByRole("checkbox", { name: "Verdor (NDVI)" }));
    act(() => hook.current!.onStatus("ndvi", "empty"));
    expect(screen.getByText("Compuesto móvil de 8 días · fecha GIBS: 2026-11-14")).toBeInTheDocument();
  });
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

describe("HU-211 · catálogo y controles", () => {
  it("distingue la tesela negra de Aquitania de una observación oscura real", () => {
    expect(gibsSample(-72.88, 5.52)).toMatchObject({ x: 152, y: 248 });
    expect(hasVisiblePixels(new Uint8ClampedArray([0, 0, 0, 255, 0, 0, 0, 255]))).toBe(false);
    // El ruido del JPEG en una zona negra (1 a 3) no es imagen; una observación oscura real sí.
    expect(hasVisiblePixels(new Uint8ClampedArray([1, 3, 2, 255, 0, 2, 1, 255]))).toBe(false);
    expect(hasVisiblePixels(new Uint8ClampedArray([12, 9, 8, 255]))).toBe(true);
  });

  it("permite elegir otro día de forma explícita", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, text: async () => XML }));
    render(<Panel />);
    fireEvent.click(screen.getByText("Capas de la NASA"));
    fireEvent.click(screen.getByRole("checkbox", { name: "Imagen satelital" }));
    await screen.findByText("Fecha de la imagen: 2026-11-15");
    fireEvent.change(screen.getByLabelText("Fecha · Imagen satelital"), { target: { value: "2026-11-13" } });
    expect(screen.getByText("Fecha de la imagen: 2026-11-13")).toBeInTheDocument();
  });
  it("usa la fecha de cada producto y la matriz y formato verificados, sin suponer hoy", () => {
    expect(parseGibsDates(XML)).toEqual({ color: "2026-11-15", ndvi: "2026-11-14" });
    // La primera fecha también sale del servicio: si GIBS recorta su historial, el selector lo sigue.
    expect(parseGibsEarliest(XML)).toEqual({ color: "2000-02-24", ndvi: "2025-02-12" });
    expect(parseGibsEarliest(XML.replace("2025-02-12/2026-11-14/P8D", "2025-06-01/2026-11-14/P8D"))).toMatchObject({ ndvi: "2025-06-01" });
    expect(gibsTiles("ndvi", "2026-11-14")).toContain(
      "MODIS_Terra_NDVI_8Day/default/2026-11-14/GoogleMapsCompatible_Level9/{z}/{y}/{x}.png",
    );
    for (const invalid of [
      "<bad",
      XML.replace("GoogleMapsCompatible_Level9", "unknown"),
      XML.replace("2026-11-15", "default"),
      XML.replace("image/png", "image/jpeg"),
    ]) {
      expect(() => parseGibsDates(invalid)).toThrow();
    }
  });

  it("no consulta NASA hasta activar; muestra fechas, límites, fuente y controles independientes", async () => {
    const fetcher = vi.fn().mockResolvedValue({ ok: true, text: async () => XML });
    vi.stubGlobal("fetch", fetcher);
    render(<Panel />);
    expect(fetcher).not.toHaveBeenCalled();
    fireEvent.click(screen.getByText("Capas de la NASA"));
    fireEvent.click(screen.getByRole("checkbox", { name: "Imagen satelital" }));
    await screen.findByText("Fecha de la imagen: 2026-11-15");
    expect(screen.getByText(/Compuesto móvil de 8 días.*2026-11-14/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("checkbox", { name: "Verdor (NDVI)" }));
    fireEvent.click(screen.getByRole("checkbox", { name: "Imagen satelital" }));
    expect(screen.getByRole("checkbox", { name: "Verdor (NDVI)" })).toBeChecked();
    expect(screen.getByRole("checkbox", { name: "Imagen satelital" })).not.toBeChecked();
    expect(fetcher).toHaveBeenCalledTimes(1);
    expect(screen.getByText(/no una medición de su lote/)).toBeInTheDocument();
    expect(screen.getByText(/no cambian los resultados/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /condiciones de uso/ })).toHaveAttribute("href", "https://nasa-gibs.github.io/gibs-api-docs/");
  });

  it("avisa el fallo del catálogo y permite reintentar sin perder la selección", async () => {
    const fetcher = vi
      .fn()
      .mockRejectedValueOnce(new Error("offline"))
      .mockResolvedValue({ ok: true, text: async () => XML });
    vi.stubGlobal("fetch", fetcher);
    render(<Panel />);
    fireEvent.click(screen.getByText("Capas de la NASA"));
    fireEvent.click(screen.getByRole("checkbox", { name: "Imagen satelital" }));
    await screen.findByText(/GIBS no responde/);
    fireEvent.click(screen.getByRole("button", { name: "Reintentar" }));
    await screen.findByText("Fecha de la imagen: 2026-11-15");
    expect(screen.getByRole("checkbox", { name: "Imagen satelital" })).toBeChecked();
    expect(screen.queryByText(/GIBS no responde/)).not.toBeInTheDocument();
  });

  it("aborta la consulta al apagar la última capa y descarta respuestas tardías", async () => {
    let signal: AbortSignal;
    const fetcher = vi.fn((_url, options) => {
      signal = options.signal;
      return new Promise(() => {});
    });
    vi.stubGlobal("fetch", fetcher);
    const view = render(<Panel />);
    fireEvent.click(screen.getByText("Capas de la NASA"));
    fireEvent.click(screen.getByRole("checkbox", { name: "Imagen satelital" }));
    await waitFor(() => expect(fetcher).toHaveBeenCalled());
    fireEvent.click(screen.getByRole("checkbox", { name: "Imagen satelital" }));
    expect(signal!.aborted).toBe(true);
    view.unmount();
  });

  it("muestra el aviso si el catálogo se queda esperando más de 15 segundos", async () => {
    vi.useFakeTimers();
    vi.stubGlobal(
      "fetch",
      vi.fn(
        (_url, options) =>
          new Promise((_resolve, reject) => {
            options.signal.addEventListener("abort", () => reject(new Error("timeout")));
          }),
      ),
    );
    render(<Panel />);
    fireEvent.click(screen.getByText("Capas de la NASA"));
    fireEvent.click(screen.getByRole("checkbox", { name: "Imagen satelital" }));
    await act(() => vi.advanceTimersByTimeAsync(15000));
    expect(screen.getByText(/GIBS no responde/)).toBeInTheDocument();
  });
});

function fakeMap() {
  const layers = new Set(["limite-linea", "lotes-relleno", "terra-draw"]);
  const sources = new Set(["lotes", "limite"]);
  const listeners = new Map<string, Set<(event: unknown) => void>>();
  const map = {
    getCenter: () => ({ lng: -72.88, lat: 5.52 }),
    on: vi.fn((name: string, cb: (event: unknown) => void) => {
      if (!listeners.has(name)) listeners.set(name, new Set());
      listeners.get(name)!.add(cb);
    }),
    off: vi.fn((name: string, cb: (event: unknown) => void) => listeners.get(name)?.delete(cb)),
    addSource: vi.fn((id: string) => sources.add(id)),
    getSource: (id: string) => sources.has(id),
    removeSource: vi.fn((id: string) => sources.delete(id)),
    addLayer: vi.fn((layer: { id: string }, before?: string) => {
      void before;
      return layers.add(layer.id);
    }),
    getLayer: (id: string) => layers.has(id),
    removeLayer: vi.fn((id: string) => layers.delete(id)),
  };
  return {
    map,
    layers,
    sources,
    emit: (name: string, event: unknown) => {
      for (const cb of [...(listeners.get(name) ?? [])]) cb(event);
    },
  };
}

describe("HU-211 · integración MapLibre", () => {
  it("una imagen negra con HTTP 200 no tapa OSM; al mover el mapa vuelve a comprobar", async () => {
    const { map, layers, emit } = fakeMap();
    const status = vi.fn();
    const probe = vi.fn().mockResolvedValueOnce(false).mockResolvedValueOnce(true);
    const dispose = mountGibsColor(map as unknown as MapLibreMap, "2026-11-15", status, probe);
    await waitFor(() => expect(status).toHaveBeenCalledWith("color", "empty"));
    expect(layers.has("gibs-color")).toBe(false);
    expect(layers.has("terra-draw")).toBe(true);
    emit("moveend", {});
    await waitFor(() => expect(layers.has("gibs-color")).toBe(true));
    dispose();
    expect(layers.has("gibs-color")).toBe(false);
  });

  it("al mover el mapa la capa con imagen no se quita mientras se comprueba: no parpadea", async () => {
    const { map, layers, emit } = fakeMap();
    const status = vi.fn();
    let resolve!: (value: boolean) => void;
    const probe = vi
      .fn()
      .mockResolvedValueOnce(true)
      .mockImplementationOnce(() => new Promise<boolean>((done) => (resolve = done)));
    const dispose = mountGibsColor(map as unknown as MapLibreMap, "2026-11-15", status, probe);
    await waitFor(() => expect(layers.has("gibs-color")).toBe(true));
    emit("moveend", {});
    expect(layers.has("gibs-color")).toBe(true);
    expect(map.addLayer).toHaveBeenCalledTimes(1);
    resolve(false);
    await waitFor(() => expect(layers.has("gibs-color")).toBe(false));
    expect(status).toHaveBeenLastCalledWith("color", "empty");
    dispose();
  });

  it("si la capa falla al montarse, queda en error sin excepción y quita sus oyentes (revisión del #186)", async () => {
    const { map, layers } = fakeMap();
    map.addLayer.mockImplementation(() => {
      throw new Error("estilo sin cargar");
    });
    const status = vi.fn();
    const dispose = mountGibsColor(map as unknown as MapLibreMap, "2026-11-15", status, vi.fn().mockResolvedValue(true));
    await waitFor(() => expect(status).toHaveBeenLastCalledWith("color", "error"));
    expect(layers.has("gibs-color")).toBe(false);
    const removed = map.off.mock.calls.map(([name]) => name);
    expect(removed).toContain("error");
    expect(removed).toContain("sourcedata");
    dispose();
  });

  it("descarta una comprobación tardía al apagar la capa", async () => {
    const { map, layers } = fakeMap();
    let resolve!: (value: boolean) => void;
    const probe = vi.fn(
      () =>
        new Promise<boolean>((done) => {
          resolve = done;
        }),
    );
    const status = vi.fn();
    const dispose = mountGibsColor(map as unknown as MapLibreMap, "2026-11-15", status, probe);
    dispose();
    resolve(true);
    await Promise.resolve();
    expect(layers.has("gibs-color")).toBe(false);
    expect(status).not.toHaveBeenCalledWith("color", "ready");
  });
  it("mantiene límites, lotes y dibujo encima; permite quitar cada capa y limpia los manejadores", () => {
    const { map, layers, emit } = fakeMap();
    const status = vi.fn();
    const removeNdvi = mountGibsLayer(map as unknown as MapLibreMap, "ndvi", "2026-11-14", status);
    const removeColor = mountGibsLayer(map as unknown as MapLibreMap, "color", "2026-11-15", status);
    expect(map.addLayer.mock.calls[1][1]).toBe("gibs-ndvi");
    emit("sourcedata", { sourceId: "gibs-color", isSourceLoaded: true, sourceDataType: "metadata" });
    emit("sourcedata", { sourceId: "gibs-color", isSourceLoaded: true, sourceDataType: "visibility" });
    expect(status).not.toHaveBeenCalledWith("color", "ready");
    // RasterTileSource emite la tesela sin sourceDataType; no confundir metadatos o visibilidad con una imagen.
    emit("sourcedata", { sourceId: "gibs-color", isSourceLoaded: true, tile: {} });
    expect(status).toHaveBeenCalledWith("color", "ready");
    removeColor();
    expect(layers.has("gibs-ndvi")).toBe(true);
    expect(layers.has("terra-draw")).toBe(true);
    removeNdvi();
    expect(map.off).toHaveBeenCalledTimes(4);
  });

  it("un error de tesela retira solo su capa y deja el mapa y el dibujo funcionando", () => {
    const { map, layers, sources, emit } = fakeMap();
    const status = vi.fn();
    const dispose = mountGibsLayer(map as unknown as MapLibreMap, "color", "2026-11-15", status);
    emit("error", { sourceId: "unrelated" });
    expect(layers.has("gibs-color")).toBe(true);
    emit("error", { sourceId: "gibs-color" });
    expect(status).toHaveBeenLastCalledWith("color", "error");
    expect(layers.has("gibs-color")).toBe(false);
    expect(layers.has("terra-draw") && sources.has("lotes")).toBe(true);
    dispose();
  });

  it("vuelve al mapa base si las teselas se quedan esperando", () => {
    vi.useFakeTimers();
    const { map, layers } = fakeMap();
    const status = vi.fn();
    const dispose = mountGibsLayer(map as unknown as MapLibreMap, "ndvi", "2026-11-14", status);
    act(() => vi.advanceTimersByTime(20000));
    expect(status).toHaveBeenLastCalledWith("ndvi", "error");
    expect(layers.has("gibs-ndvi")).toBe(false);
    expect(layers.has("terra-draw")).toBe(true);
    dispose();
  });
});
