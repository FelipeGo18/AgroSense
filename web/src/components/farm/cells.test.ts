import { describe, expect, it } from "vitest";
import { allocateCells, drawStage, timeOfDay, type LiveSeason } from "./cells";

const season = (seasonId: string, cropId: string, areaHa: number, stage: string | null = "mid"): LiveSeason => ({
  seasonId,
  cropId,
  areaHa,
  stage,
});
const count = (cells: ReturnType<typeof allocateCells>["cells"], id: string | null) =>
  cells.filter((c) => (c.season?.seasonId ?? null) === id).length;

describe("El reparto del lote vivo (HU-187)", () => {
  it("cada siembra ocupa cubos según su parte del área, y lo que sobra es la parte libre", () => {
    // El Alto del diseño: papa 1,26, haba 0,42 y cebolla 0,42 en 2,51 ha.
    const { layout, cells } = allocateCells(
      [season("p", "papa", 1.26), season("h", "haba", 0.42), season("c", "cebolla_bulbo", 0.42)],
      2.51,
    );
    expect(layout).toBe("2x2");
    expect(cells).toHaveLength(4);
    expect(count(cells, "p")).toBe(2);
    expect(count(cells, "h")).toBe(1);
    expect(count(cells, "c")).toBe(1);
  });

  it("toda siembra tiene al menos un cubo, aunque su parte sea chica", () => {
    const { cells } = allocateCells([season("p", "papa", 9.9), season("h", "haba", 0.1)], 10);
    expect(count(cells, "h")).toBeGreaterThanOrEqual(1);
    expect(cells).toHaveLength(4);
  });

  it("un lote sin siembras es todo parte libre", () => {
    expect(allocateCells([], 2).cells.every((c) => c.season === null)).toBe(true);
  });

  it("con más de tres siembras usa 6 cubos", () => {
    const four = ["a", "b", "c", "d"].map((id) => season(id, "papa", 1));
    expect(allocateCells(four, 4)).toMatchObject({ layout: "3x2" });
  });

  it("las mismas siembras dan el mismo reparto (R4)", () => {
    const seasons = [season("p", "papa", 1.26), season("h", "haba", 0.42)];
    expect(allocateCells(seasons, 2.51)).toEqual(allocateCells(seasons, 2.51));
  });

  it("la etapa de FAO-56 elige el dibujo, y sin etapa se dibuja recién nacido", () => {
    expect([drawStage("initial"), drawStage("development"), drawStage("mid"), drawStage("late"), drawStage(null)]).toEqual([1, 2, 3, 4, 1]);
  });

  it("el cielo sigue la hora local", () => {
    expect(timeOfDay(new Date(2026, 10, 14, 10))).toBe("dia");
    expect(timeOfDay(new Date(2026, 10, 14, 17, 30))).toBe("atardecer");
    expect(timeOfDay(new Date(2026, 10, 14, 22))).toBe("noche");
  });
});
