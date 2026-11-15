import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { shouldPaint } from "./Animals";
import { FarmFireflies, FarmLifeSky, FarmLifeWorld, type FarmAnchors } from "./FarmLife";

// Solo `path` importa para las luciérnagas: las esquinas del camino alrededor del lote.
const anchors = {
  path: [
    [0, 0],
    [200, 100],
    [0, 200],
    [-200, 100],
  ],
} as unknown as FarmAnchors;

// Lo que pide `FarmLifeWorld` para dibujar el día: el campo, el camino y los puntos de la finca.
const world = {
  ...anchors,
  field: [
    [-100, 0],
    [100, 200],
  ],
  chimney: [0, -100],
  window: [10, -50],
  porch: [20, -40],
  garden: [-50, 50],
  dog: [-60, 40],
  fence: [80, 80],
  lanterns: [],
  hens: [],
  meadow: [],
} as unknown as FarmAnchors;

describe("menos partículas en el celular (HU-187)", () => {
  it("las luciérnagas bajan de 24 a 10", () => {
    const many = render(<svg>{<FarmFireflies anchors={anchors} />}</svg>);
    expect(many.container.querySelectorAll(".farm-firefly")).toHaveLength(24);
    const few = render(<svg>{<FarmFireflies anchors={anchors} few />}</svg>);
    expect(few.container.querySelectorAll(".farm-firefly")).toHaveLength(10);
  });

  it("de día, una mariposa y una hoja en vez de dos y tres", () => {
    const count = (few: boolean) =>
      render(<svg>{<FarmLifeSky width={960} height={600} time="dia" few={few} />}</svg>).container.querySelectorAll("animateMotion").length;
    expect(count(false)).toBe(5);
    expect(count(true)).toBe(2);
  });

  it("las abejas zumban sobre 1 cubo en flor en vez de 3", () => {
    const flowering: [number, number][] = [
      [0, 0],
      [40, 20],
      [80, 40],
    ];
    const bees = (few: boolean) =>
      render(<svg>{<FarmLifeWorld anchors={world} time="dia" flowering={flowering} few={few} />}</svg>).container.querySelectorAll(
        'circle[fill="#F2C232"][r="2.2"]',
      ).length;
    expect(bees(false)).toBe(6);
    expect(bees(true)).toBe(2);
  });

  it("los animales se repintan a unos 30 cuadros por segundo en el celular, no a 60", () => {
    // 100 ms a 60 cuadros por segundo: un cuadro cada 16,7 ms.
    const paints = (few: boolean) => {
      let painted = 0;
      let count = 0;
      for (let frame = 1; frame <= 6; frame++) {
        const now = frame * (1000 / 60);
        if (shouldPaint(now, painted, few)) {
          painted = now;
          count++;
        }
      }
      return count;
    };
    expect(paints(false)).toBe(6);
    expect(paints(true)).toBe(3);
  });
});
