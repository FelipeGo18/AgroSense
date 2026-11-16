import { useCallback, useEffect, useState } from "react";
import { fetchGibsDates, type GibsDates, type GibsLayer, type GibsSelection, type GibsStatus } from "./gibs";

export function useGibs() {
  const [selected, setSelected] = useState<GibsSelection>({ color: false, ndvi: false });
  const [dates, setDates] = useState<GibsDates | null>(null);
  const [latestDates, setLatestDates] = useState<GibsDates | null>(null);
  const [earliestDates, setEarliestDates] = useState<Partial<GibsDates>>({});
  const [status, setStatus] = useState<Record<GibsLayer, GibsStatus>>({ color: "off", ndvi: "off" });
  const [attempt, setAttempt] = useState(0);
  const enabled = selected.color || selected.ndvi;
  const onStatus = useCallback((layer: GibsLayer, value: GibsStatus) => {
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
    setDates({ ...dates, [layer]: date });
    if (selected[layer]) onStatus(layer, "loading");
  };
  return { selected, dates, latestDates, earliestDates, status, attempt, onStatus, toggle, retry, chooseDate };
}
