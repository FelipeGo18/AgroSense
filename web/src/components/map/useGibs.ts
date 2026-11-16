import { useCallback, useEffect, useRef, useState } from "react";
import { fetchGibsDates, type GibsDates, type GibsLayer, type GibsSelection, type GibsStatus } from "./gibs";

/** Cuántos días hacia atrás se busca imagen de color real mientras la persona no elige fecha. La fecha por defecto de GIBS
 * es la de hoy en UTC, que casi nunca está procesada todavía, y MODIS deja franjas sin pasada cerca del ecuador. */
export const GIBS_COLOR_LOOKBACK_DAYS = 5;

/** El día anterior a una fecha `AAAA-MM-DD`, en UTC (la de GIBS). */
export function previousDay(date: string): string {
  const day = new Date(`${date}T00:00:00Z`);
  day.setUTCDate(day.getUTCDate() - 1);
  return day.toISOString().slice(0, 10);
}

export function useGibs() {
  const [selected, setSelected] = useState<GibsSelection>({ color: false, ndvi: false });
  const [dates, setDates] = useState<GibsDates | null>(null);
  const [latestDates, setLatestDates] = useState<GibsDates | null>(null);
  const [earliestDates, setEarliestDates] = useState<Partial<GibsDates>>({});
  const [status, setStatus] = useState<Record<GibsLayer, GibsStatus>>({ color: "off", ndvi: "off" });
  const [attempt, setAttempt] = useState(0);
  // Mientras la fecha de color real no la elija la persona, una vista sin imagen prueba el día anterior. Va en refs para
  // que `onStatus` no cambie: el mapa vuelve a montar las capas cuando cambia (MapCanvas).
  const [colorAuto, setColorAuto] = useState(true);
  const colorAutoRef = useRef(true);
  const lookbackRef = useRef(0);
  const earliestRef = useRef<Partial<GibsDates>>({});
  const datesRef = useRef<GibsDates | null>(null);
  useEffect(() => {
    datesRef.current = dates;
    earliestRef.current = earliestDates;
  }, [dates, earliestDates]);
  const enabled = selected.color || selected.ndvi;
  const onStatus = useCallback((layer: GibsLayer, value: GibsStatus) => {
    const current = datesRef.current;
    if (layer === "color" && value === "empty" && current && colorAutoRef.current && lookbackRef.current < GIBS_COLOR_LOOKBACK_DAYS) {
      const day = previousDay(current.color);
      const earliest = earliestRef.current.color;
      if (!earliest || day >= earliest) {
        lookbackRef.current += 1;
        const next = { ...current, color: day };
        datesRef.current = next;
        // El mapa monta la capa con la fecha nueva y vuelve a comprobar: el estado sigue «cargando».
        setDates(next);
        setStatus((previous) => (previous.color === "loading" ? previous : { ...previous, color: "loading" }));
        return;
      }
    }
    setStatus((previous) => (previous[layer] === value ? previous : { ...previous, [layer]: value }));
  }, []);

  useEffect(() => {
    if (!enabled || dates) return;
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 15000);
    let active = true;
    fetchGibsDates(controller.signal)
      .then((value) => {
        if (active) {
          setDates(value.dates);
          setLatestDates(value.dates);
          setEarliestDates(value.earliest);
        }
      })
      .catch(() => {
        if (active) setStatus({ color: "error", ndvi: "error" });
      });
    return () => {
      active = false;
      window.clearTimeout(timeout);
      controller.abort();
    };
  }, [enabled, dates, attempt]);

  const toggle = (layer: GibsLayer) => {
    setSelected((previous) => ({ ...previous, [layer]: !previous[layer] }));
    onStatus(layer, selected[layer] ? "off" : "loading");
    // También permite reintentar después de un fallo del catálogo.
    if (!dates) setAttempt((previous) => previous + 1);
  };
  const retry = () => {
    setStatus({ color: selected.color ? "loading" : "off", ndvi: selected.ndvi ? "loading" : "off" });
    setAttempt((previous) => previous + 1);
  };
  const chooseDate = (layer: GibsLayer, date: string) => {
    const earliest = earliestDates[layer];
    if (!dates || !latestDates || !/^\d{4}-\d{2}-\d{2}$/.test(date) || date > latestDates[layer] || (earliest && date < earliest)) return;
    // Una fecha que elige la persona se respeta: sin imagen, se dice y no se cambia en silencio.
    if (layer === "color") {
      colorAutoRef.current = false;
      setColorAuto(false);
    }
    setDates({ ...dates, [layer]: date });
    if (selected[layer]) onStatus(layer, "loading");
  };
  // La imagen de color real se muestra de un día anterior al más reciente de GIBS porque ese no tenía imagen aquí.
  const colorFallback = Boolean(colorAuto && dates && latestDates && dates.color !== latestDates.color);
  return { selected, dates, latestDates, earliestDates, status, attempt, onStatus, toggle, retry, chooseDate, colorFallback };
}
