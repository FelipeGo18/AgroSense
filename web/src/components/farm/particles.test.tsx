import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { FarmFireflies, FarmLifeSky, type FarmAnchors } from "./FarmLife";

// Solo `path` importa para las luciérnagas: las esquinas del camino alrededor del lote.
const anchors = {
  path: [
    [0, 0],
    [200, 100],
    [0, 200],
    [-200, 100],
  ],
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
});
