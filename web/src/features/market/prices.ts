import { useQuery } from "@tanstack/react-query";
import { api, type Schemas } from "@/api/client";

export type MarketPrices = Schemas["MarketPrices"];
export type ProductPrice = Schemas["ProductPrice"];
export type ProductHistory = Schemas["ProductHistory"];
export type Price = Schemas["Price"];
export type Season = Schemas["Season"];

/**
 * Los precios cambian solo con un dataset nuevo (el pipeline los publica): se piden una vez por central. Sin
 * `marketId`, la API responde la primera central (Corabastos).
 */
export function useMarketPrices(marketId: string | null) {
  return useQuery({
    queryKey: ["market", "prices", marketId],
    queryFn: () => api<MarketPrices>(`/market/prices${marketId ? `?market_id=${encodeURIComponent(marketId)}` : ""}`),
    staleTime: Infinity,
    retry: false,
  });
}

export function useProductHistory(productId: string | null, marketId: string | null) {
  return useQuery({
    queryKey: ["market", "history", productId, marketId],
    queryFn: () =>
      api<ProductHistory>(
        `/market/prices/${encodeURIComponent(productId!)}${marketId ? `?market_id=${encodeURIComponent(marketId)}` : ""}`,
      ),
    enabled: productId !== null,
    staleTime: Infinity,
    retry: false,
  });
}

const PESOS = new Intl.NumberFormat("es-CO", { style: "currency", currency: "COP", maximumFractionDigits: 0 });
const PERCENT = new Intl.NumberFormat("es-CO", { maximumFractionDigits: 1 });
const DAY = new Intl.DateTimeFormat("es-CO", { day: "numeric", month: "long", year: "numeric", timeZone: "UTC" });
const SHORT_DAY = new Intl.DateTimeFormat("es-CO", { day: "numeric", month: "short", timeZone: "UTC" });
const MONTH = new Intl.DateTimeFormat("es-CO", { month: "long", timeZone: "UTC" });
const SHORT_MONTH = new Intl.DateTimeFormat("es-CO", { month: "short", timeZone: "UTC" });

/** «$ 2.925». Sin decimales: el DANE publica pesos enteros por kilo. */
export const formatPesos = (value: number) => PESOS.format(value);

/** Las fechas de la API son días («2026-10-19»): se leen en UTC para que no cambien de día con la zona horaria. */
const asDate = (day: string) => new Date(`${day}T00:00:00Z`);

/** «19 de octubre de 2026». */
export const formatDay = (day: string) => DAY.format(asDate(day));

const UPDATED = new Intl.DateTimeFormat("es-CO", {
  day: "numeric",
  month: "long",
  hour: "numeric",
  minute: "2-digit",
  timeZone: "America/Bogota",
});
/** «20 de octubre, 3:05 p. m.»: cuándo bajó la API los precios del DANE (HU-222), en la hora de Colombia. */
export const formatUpdated = (instant: string) => UPDATED.format(new Date(instant));
/** «19 oct». */
export const formatShortDay = (day: string) => SHORT_DAY.format(asDate(day));
/** «octubre», con el número de mes de 1 a 12. */
export const monthName = (month: number) => MONTH.format(new Date(Date.UTC(2000, month - 1, 1)));
/** «oct». */
export const shortMonthName = (month: number) => SHORT_MONTH.format(new Date(Date.UTC(2000, month - 1, 1))).replace(".", "");

/** «Sube 6,4 %», «Baja 3 %» o «Igual». Siempre con palabras: el color no es la única pista. */
export function changeText(change: number) {
  if (change === 0) return "Igual que hace una semana";
  return `${change > 0 ? "Sube" : "Baja"} ${PERCENT.format(Math.abs(change))} % en una semana`;
}

/** Del índice estacional (1 = un mes como cualquiera) al porcentaje frente al promedio del año: 0,77 → −23. */
export const seasonPercent = (index: number) => Math.round((index - 1) * 100);

/** El mes más barato y el más caro de la temporada. */
export function seasonExtremes(season: Season) {
  const sorted = [...season.months].sort((a, b) => a.seasonal_index - b.seasonal_index);
  return { cheapest: sorted[0], priciest: sorted[sorted.length - 1] };
}

/** Quita tildes y mayúsculas para buscar «frijol» y encontrar «Fríjol verde». */
export const searchKey = (text: string) =>
  text
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLowerCase()
    .trim();
