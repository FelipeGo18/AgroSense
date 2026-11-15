import type { Map as MapLibreMap } from "maplibre-gl";
import { gibsTiles, hasGibsObservation, type GibsLayer, type GibsStatus } from "./gibs";

/** Verifica cobertura al activar y al mover el mapa. Un JPEG negro también puede responder HTTP 200. */
export function mountGibsColor(
  map: MapLibreMap,
  date: string,
  onStatus: (layer: GibsLayer, status: GibsStatus) => void,
  probe = hasGibsObservation,
) {
  let controller: AbortController | undefined;
  let dispose: (() => void) | undefined;
  let timeout: ReturnType<typeof setTimeout> | undefined;
  const check = () => {
    controller?.abort();
    clearTimeout(timeout);
    dispose?.();
    dispose = undefined;
    const request = new AbortController();
    controller = request;
    timeout = setTimeout(() => {
      request.abort();
      if (controller === request) onStatus("color", "error");
    }, 20000);
    const { lng, lat } = map.getCenter();
    onStatus("color", "loading");
    probe(date, lng, lat, request.signal)
      .then((available) => {
        if (request !== controller || request.signal.aborted) return;
        clearTimeout(timeout);
        if (available) dispose = mountGibsLayer(map, "color", date, onStatus);
        else onStatus("color", "empty");
      })
      .catch(() => {
        if (request === controller) onStatus("color", "error");
      });
  };
  map.on("moveend", check);
  check();
  return () => {
    controller?.abort();
    controller = undefined;
    clearTimeout(timeout);
    dispose?.();
    map.off("moveend", check);
  };
}

/** Un fallo o tiempo de espera solo retira esta capa: nunca destruye el mapa ni Terra Draw. */
export function mountGibsLayer(map: MapLibreMap, layer: GibsLayer, date: string, onStatus: (layer: GibsLayer, status: GibsStatus) => void) {
  const id = `gibs-${layer}`;
  let failed = false;
  const remove = () => {
    if (map.getLayer(id)) map.removeLayer(id);
    if (map.getSource(id)) map.removeSource(id);
  };
  const fail = () => {
    if (failed) return;
    failed = true;
    clearTimeout(timer);
    remove();
    onStatus(layer, "error");
  };
  const error = (event: unknown) => {
    if (event && typeof event === "object" && "sourceId" in event && event.sourceId === id) fail();
  };
  const data = (event: { sourceId?: string; isSourceLoaded?: boolean; sourceDataType?: string; tile?: unknown }) => {
    // RasterTileSource emite el evento de tesela sin sourceDataType; `idle` cubre una vista sin teselas pendientes.
    if (!failed && event.sourceId === id && event.isSourceLoaded && (event.tile || event.sourceDataType === "idle")) {
      clearTimeout(timer);
      onStatus(layer, "ready");
    }
  };
  onStatus(layer, "loading");
  map.on("error", error);
  map.on("sourcedata", data);
  const timer = setTimeout(fail, 20000);
  try {
    map.addSource(id, {
      type: "raster",
      tiles: [gibsTiles(layer, date)],
      tileSize: 256,
      minzoom: 0,
      maxzoom: 9,
      attribution: "NASA GIBS / ESDIS · MODIS Terra",
    });
    map.addLayer(
      {
        id,
        type: "raster",
        source: id,
        paint: { "raster-opacity": 1, "raster-resampling": "nearest", "raster-fade-duration": 0 },
      },
      layer === "color" && map.getLayer("gibs-ndvi") ? "gibs-ndvi" : "limite-linea",
    );
  } catch {
    fail();
  }
  return () => {
    clearTimeout(timer);
    map.off("error", error);
    map.off("sourcedata", data);
    remove();
  };
}
