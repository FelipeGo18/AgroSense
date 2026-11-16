import type { Map as MapLibreMap } from "maplibre-gl";
import { gibsTiles, hasGibsObservation, type GibsLayer, type GibsStatus } from "./gibs";

/** Verifica cobertura al activar y al mover el mapa. Un JPEG negro también puede responder HTTP 200.
 * La capa montada se queda mientras se comprueba la nueva vista (sin parpadeo al mover el mapa) y solo se quita cuando la
 * comprobación dice que no hay imagen o falla (revisión del PR #144). */
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
    const request = new AbortController();
    controller = request;
    const unmount = () => {
      dispose?.();
      dispose = undefined;
    };
    timeout = setTimeout(() => {
      request.abort();
      if (controller === request) {
        unmount();
        onStatus("color", "error");
      }
    }, 20000);
    const { lng, lat } = map.getCenter();
    if (!dispose) onStatus("color", "loading");
    probe(date, lng, lat, request.signal)
      .then((available) => {
        if (request !== controller || request.signal.aborted) return;
        clearTimeout(timeout);
        if (available) {
          // Si las teselas fallan, la capa se quita sola: se olvida para volver a montarla en la próxima vista.
          if (!dispose) {
            // La limpieza se guarda en un objeto que existe antes de montar: un fallo síncrono llama a la callback antes
            // de que `mountGibsLayer` devuelva (revisión del #186). Al fallar, se quitan también los oyentes de la capa.
            const layer: { remove?: () => void; failed?: boolean } = {};
            layer.remove = mountGibsLayer(map, "color", date, (name, value) => {
              if (value === "error") {
                layer.failed = true;
                const cleanup = layer.remove;
                if (cleanup && dispose === cleanup) dispose = undefined;
                if (cleanup) queueMicrotask(cleanup);
              }
              onStatus(name, value);
            });
            if (layer.failed) layer.remove();
            else dispose = layer.remove;
          }
        } else {
          unmount();
          onStatus("color", "empty");
        }
      })
      .catch(() => {
        if (request !== controller) return;
        unmount();
        onStatus("color", "error");
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
