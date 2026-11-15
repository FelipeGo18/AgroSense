import * as maplibregl from "maplibre-gl";
import type { GeoJSONSource, Map as MapLibreMap } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
// El worker de MapLibre lo empaqueta Vite con lo que importa: MapLibre arma su ruta en tiempo de ejecución y, sin esto,
// ni el servidor de desarrollo ni el build lo encuentran.
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url";
import { useEffect, useRef, useState } from "react";
import { TerraDraw, TerraDrawPolygonMode, TerraDrawSelectMode, ValidateNotSelfIntersecting } from "terra-draw";
import { TerraDrawMapLibreGLAdapter } from "terra-draw-maplibre-gl-adapter";
import { bbox, center, type Boundary, type LotPolygon } from "@/features/farm/geo";

/** Mapa base de OpenStreetMap servido por OpenFreeMap (specs/04-stack.md). Sin clave ni cuenta. */
export const STYLE_URL = "https://tiles.openfreemap.org/styles/liberty";

// Colores del diseño (Figma: «Dibuje su lote»): el lote en tierra, el límite del municipio en morado punteado.
const LOT_FILL = "#E3C38F";
const LOT_LINE = "#92490B";
const BOUNDARY_LINE = "#6B4E9B";

export type DrawMode = "draw" | "move" | "view";

export interface MapLot {
  id: string;
  name: string;
  geometry: LotPolygon;
  selected?: boolean;
}

export interface Editing {
  geometry: LotPolygon | null;
  mode: DrawMode;
  onChange: (geometry: LotPolygon | null) => void;
  /** Al cerrar el lote, el mapa pasa solo a «Mover puntos». */
  onModeChange: (mode: DrawMode) => void;
  /** «2,51 ha», sobre el lote. */
  areaLabel?: string;
  /** El dibujo se sale del municipio: la etiqueta va en rojo. */
  outside?: boolean;
}

export interface MapControls {
  zoomIn: () => void;
  zoomOut: () => void;
}

export interface MapCanvasProps {
  animated: boolean;
  boundary: Boundary | null;
  /** Lo que se encuadra al abrir: el lote, o si no hay, el municipio. */
  focus: LotPolygon | null;
  lots?: MapLot[];
  onLotClick?: (id: string) => void;
  editing?: Editing;
  /** Espacio que tapan el panel y las barras, para encuadrar sin que nada quede debajo. */
  padding: { top: number; bottom: number; left: number; right: number };
  onReady: (controls: MapControls) => void;
  /** El navegador no puede mostrar el mapa (sin WebGL) o el mapa base no cargó. */
  onFail: () => void;
}

maplibregl.setWorkerUrl(workerUrl);

const empty = { type: "FeatureCollection" as const, features: [] };
type GeoJSONData = Parameters<GeoJSONSource["setData"]>[0];

/**
 * El mapa real del lote (HU-164, HU-169): MapLibre GL sobre OpenStreetMap y Terra Draw para dibujar el contorno.
 * Es la única pieza que conoce MapLibre; se carga aparte (React.lazy) para que las páginas sin mapa no la descarguen.
 * En modo ligero el mapa no anima: encuadra, acerca y aleja sin movimiento.
 */
export default function MapCanvas({ animated, boundary, focus, lots = [], onLotClick, editing, padding, onReady, onFail }: MapCanvasProps) {
  const container = useRef<HTMLDivElement>(null);
  const map = useRef<MapLibreMap | null>(null);
  const draw = useRef<TerraDraw | null>(null);
  const featureId = useRef<string | null>(null);
  const lastEmitted = useRef<string>("null");
  const markers = useRef<maplibregl.Marker[]>([]);
  const areaMarker = useRef<maplibregl.Marker | null>(null);
  const fitted = useRef<string>("");
  const [ready, setReady] = useState(false);
  // Lo último que llegó por props, para los manejadores que se registran una sola vez.
  const latest = useRef({ animated, editing, onLotClick });
  useEffect(() => {
    latest.current = { animated, editing, onLotClick };
  });

  // ---------- El mapa ----------
  useEffect(() => {
    if (!container.current) return;
    let instance: MapLibreMap;
    try {
      instance = new maplibregl.Map({
        container: container.current,
        style: STYLE_URL,
        center: [-74, 4.6],
        zoom: 6,
        attributionControl: false,
        fadeDuration: animated ? 300 : 0,
        dragRotate: false,
        pitchWithRotate: false,
      });
    } catch {
      onFail();
      return;
    }
    map.current = instance;
    instance.touchZoomRotate.disableRotation();
    instance.addControl(new maplibregl.AttributionControl({ compact: false }), "bottom-right");
    // A la derecha: a la izquierda la tapa el panel.
    instance.addControl(new maplibregl.ScaleControl({ unit: "metric" }), "bottom-right");
    let loaded = false;
    instance.on("error", () => {
      // Si ni siquiera cargó el mapa base, no hay mapa que mostrar. Una tesela que falla después no lo tumba.
      if (!loaded) onFail();
    });
    instance.on("load", () => {
      loaded = true;
      instance.addSource("limite", { type: "geojson", data: empty });
      instance.addLayer({
        id: "limite-linea",
        type: "line",
        source: "limite",
        paint: { "line-color": BOUNDARY_LINE, "line-width": 3, "line-dasharray": [2, 1.5] },
      });
      instance.addSource("lotes", { type: "geojson", data: empty });
      instance.addLayer({
        id: "lotes-relleno",
        type: "fill",
        source: "lotes",
        paint: { "fill-color": LOT_FILL, "fill-opacity": ["case", ["get", "selected"], 0.85, 0.65] },
      });
      instance.addLayer({
        id: "lotes-linea",
        type: "line",
        source: "lotes",
        paint: { "line-color": LOT_LINE, "line-width": ["case", ["get", "selected"], 4, 2.5] },
      });
      instance.on("click", "lotes-relleno", (event) => {
        const id = event.features?.[0]?.properties?.id;
        if (typeof id === "string") latest.current.onLotClick?.(id);
      });
      instance.on("mouseenter", "lotes-relleno", () => (instance.getCanvas().style.cursor = "pointer"));
      instance.on("mouseleave", "lotes-relleno", () => (instance.getCanvas().style.cursor = ""));
      setReady(true);
      onReady({
        zoomIn: () => instance.zoomIn({ animate: latest.current.animated }),
        zoomOut: () => instance.zoomOut({ animate: latest.current.animated }),
      });
    });
    return () => {
      draw.current?.stop();
      draw.current = null;
      instance.remove();
      map.current = null;
    };
    // El mapa se crea una vez; lo que cambia después se aplica en los efectos de abajo.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ---------- El límite del municipio y el encuadre ----------
  useEffect(() => {
    const instance = map.current;
    if (!ready || !instance) return;
    const outline = boundary ? { type: "Feature", properties: {}, geometry: boundary } : empty;
    (instance.getSource("limite") as GeoJSONSource).setData(outline as GeoJSONData);
    const target = focus ?? boundary;
    if (!target) return;
    // Se encuadra una vez por lote o municipio: no se mueve la cámara mientras la persona dibuja.
    const key = JSON.stringify(bbox(target));
    if (fitted.current === key) return;
    fitted.current = key;
    const [w, s, e, n] = bbox(target);
    instance.fitBounds(
      [
        [w, s],
        [e, n],
      ],
      { padding, maxZoom: focus ? 17 : 13, animate: animated, duration: animated ? 900 : 0 },
    );
  }, [ready, boundary, focus, padding, animated]);

  // ---------- Los lotes dibujados (Mi finca, el lote) ----------
  useEffect(() => {
    const instance = map.current;
    if (!ready || !instance) return;
    (instance.getSource("lotes") as GeoJSONSource).setData({
      type: "FeatureCollection",
      features: lots.map((lot) => ({
        type: "Feature",
        properties: { id: lot.id, selected: Boolean(lot.selected) },
        geometry: lot.geometry,
      })),
    });
    for (const marker of markers.current) marker.remove();
    markers.current = lots.map((lot) => {
      const label = document.createElement("button");
      label.type = "button";
      label.className = "map-label";
      label.textContent = lot.name;
      label.addEventListener("click", () => latest.current.onLotClick?.(lot.id));
      return new maplibregl.Marker({ element: label }).setLngLat(center(lot.geometry)).addTo(instance);
    });
  }, [ready, lots]);

  // ---------- Dibujar y mover puntos (Terra Draw) ----------
  useEffect(() => {
    const instance = map.current;
    if (!ready || !instance || !editing || draw.current) return;
    const terra = new TerraDraw({
      adapter: new TerraDrawMapLibreGLAdapter({ map: instance }),
      modes: [
        new TerraDrawPolygonMode({
          validation: (feature, { updateType }) =>
            updateType === "finish" || updateType === "commit" ? ValidateNotSelfIntersecting(feature) : { valid: true },
          styles: {
            fillColor: LOT_FILL,
            fillOpacity: 0.7,
            outlineColor: LOT_LINE,
            outlineWidth: 3,
            closingPointColor: "#F0913A",
            closingPointWidth: 8,
            closingPointOutlineColor: "#1E2A3A",
            closingPointOutlineWidth: 2,
          },
        }),
        new TerraDrawSelectMode({
          flags: {
            polygon: {
              feature: { draggable: false, coordinates: { draggable: true, midpoints: true, deletable: true } },
            },
          },
          styles: {
            selectedPolygonColor: LOT_FILL,
            selectedPolygonFillOpacity: 0.7,
            selectedPolygonOutlineColor: LOT_LINE,
            selectedPolygonOutlineWidth: 3,
            selectionPointColor: "#FFFFFF",
            selectionPointOutlineColor: "#1E2A3A",
            selectionPointWidth: 7,
            selectionPointOutlineWidth: 2,
            midPointColor: "#FFFFFF",
            midPointOutlineColor: LOT_LINE,
            midPointWidth: 4,
          },
        }),
      ],
    });
    terra.start();
    terra.on("finish", (id) => {
      const feature = terra.getSnapshotFeature(id);
      if (!feature || feature.geometry.type !== "Polygon") return;
      // Un lote es un solo contorno: al cerrar uno nuevo se quitan los demás.
      const others = terra
        .getSnapshot()
        .filter((f) => f.id !== id)
        .map((f) => f.id as string);
      if (others.length) terra.removeFeatures(others);
      featureId.current = id as string;
      const geometry = feature.geometry as LotPolygon;
      lastEmitted.current = JSON.stringify(geometry);
      latest.current.editing?.onChange(geometry);
      if (terra.getMode() === "polygon") latest.current.editing?.onModeChange("move");
    });
    draw.current = terra;
  }, [ready, editing]);

  // El dibujo que llega por props (al abrir, al deshacer o al borrar) se refleja en Terra Draw, y el modo también.
  const geometryKey = JSON.stringify(editing?.geometry ?? null);
  const mode = editing?.mode;
  useEffect(() => {
    const terra = draw.current;
    if (!terra) return;
    if (geometryKey !== lastEmitted.current) {
      terra.clear();
      featureId.current = null;
      const geometry = JSON.parse(geometryKey) as LotPolygon | null;
      if (geometry) {
        const id = crypto.randomUUID();
        terra.addFeatures([{ id, type: "Feature", geometry, properties: { mode: "polygon" } }]);
        featureId.current = id;
      }
      lastEmitted.current = geometryKey;
    }
    if (mode === "draw") terra.setMode("polygon");
    else if (mode === "move" && featureId.current) terra.selectFeature(featureId.current);
    else terra.setMode("static");
  }, [geometryKey, mode, ready]);

  // La etiqueta del área sobre el lote que se dibuja.
  const areaLabel = editing?.areaLabel;
  const outside = editing?.outside;
  useEffect(() => {
    const instance = map.current;
    areaMarker.current?.remove();
    areaMarker.current = null;
    const geometry = JSON.parse(geometryKey) as LotPolygon | null;
    if (!ready || !instance || !geometry || !areaLabel) return;
    const label = document.createElement("span");
    label.className = `map-area ${outside ? "map-area-outside" : ""}`;
    label.textContent = areaLabel;
    areaMarker.current = new maplibregl.Marker({ element: label }).setLngLat(center(geometry)).addTo(instance);
  }, [ready, geometryKey, areaLabel, outside]);

  // MapLibre le pone `position: relative` a su contenedor: el que ocupa el espacio es el envoltorio.
  return (
    <div className="absolute inset-0">
      <div ref={container} className="size-full" />
    </div>
  );
}
