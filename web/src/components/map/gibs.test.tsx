import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { Map as MapLibreMap } from "maplibre-gl";
import { afterEach, describe, expect, it, vi } from "vitest";
import { GibsPanel } from "./GibsPanel";
import { GIBS_LAYERS, gibsSample, gibsTiles, hasVisiblePixels, parseGibsDates } from "./gibs";
import { mountGibsColor, mountGibsLayer } from "./gibsMap";
import { useGibs } from "./useGibs";

// Fragmentos de ejemplo con la estructura del GetCapabilities verificado en HU-211; sin red en CI.
const XML = `<Capabilities xmlns="http://www.opengis.net/wmts/1.0" xmlns:ows="http://www.opengis.net/ows/1.1"><Contents>${Object.entries(
  GIBS_LAYERS,
)
  .map(
    ([key, spec]) =>
      `<Layer><ows:Identifier>${spec.product}</ows:Identifier><Dimension><ows:Identifier>Time</ows:Identifier><Default>2026-11-${key === "color" ? "15" : "14"}</Default></Dimension><TileMatrixSetLink><TileMatrixSet>GoogleMapsCompatible_Level9</TileMatrixSet></TileMatrixSetLink><Format>${spec.format}</Format></Layer>`,
  )
  .join("")}</Contents></Capabilities>`;

function Panel() {
  return <GibsPanel gibs={useGibs()} />;
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

describe("HU-211 · catálogo y controles", () => {
  it("distingue la tesela negra de Aquitania de una observación oscura real", () => {
    expect(gibsSample(-72.88, 5.52)).toMatchObject({ x: 152, y: 248 });
    expect(hasVisiblePixels(new Uint8ClampedArray([0, 0, 0, 255, 0, 0, 0, 255]))).toBe(false);
    expect(hasVisiblePixels(new Uint8ClampedArray([0, 1, 0, 255]))).toBe(true);
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
