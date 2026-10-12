import { describe, expect, it } from "vitest";
import { dayPhase } from "./dayPhase";

describe("El momento del día según la hora del dispositivo", () => {
  it.each([
    [0, "night"],
    [4, "night"],
    [5, "dawn"],
    [6, "dawn"],
    [7, "day"],
    [16, "day"],
    [17, "dusk"],
    [18, "dusk"],
    [19, "night"],
    [23, "night"],
  ] as const)("a las %i es %s", (hour, phase) => {
    expect(dayPhase(hour)).toBe(phase);
  });
});
