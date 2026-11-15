/**
 * El momento del día según la hora de este dispositivo. Es ambiente: tiñe el paisaje y nada más. No es el clima ni la
 * hora solar de un municipio (eso es HU-174, con la posición de la zona) y nunca entra a un cálculo (decisión 7).
 */
export type DayPhase = "dawn" | "day" | "dusk" | "night";

/** Amanece de 5 a 7 y atardece de 17 a 19: lo usual cerca del ecuador, donde el día dura casi igual todo el año. */
export function dayPhase(hour: number): DayPhase {
  if (hour >= 7 && hour < 17) return "day";
  if (hour >= 5 && hour < 7) return "dawn";
  if (hour >= 17 && hour < 19) return "dusk";
  return "night";
}
