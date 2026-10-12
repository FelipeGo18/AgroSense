import { describe, expect, it } from "vitest";
import { lerpLon, lightFactor, parseHex, rotateInto, rotation, seeded, shade } from "./globe";

const toVec = (lon: number, lat: number) => {
  const lo = (lon * Math.PI) / 180;
  const la = (lat * Math.PI) / 180;
  return [Math.cos(la) * Math.sin(lo), Math.sin(la), Math.cos(la) * Math.cos(lo)];
};

describe("geometría de la Tierra", () => {
  it("el giro deja al frente el punto pedido", () => {
    const out = [0, 0, 0];
    rotateInto(out, toVec(-73.36, 5.55), 0, rotation(-73.36, 5.55));
    expect(out[0]).toBeCloseTo(0);
    expect(out[1]).toBeCloseTo(0);
    expect(out[2]).toBeCloseTo(1);
  });

  it("lo que está al otro lado queda detrás", () => {
    const out = [0, 0, 0];
    rotateInto(out, toVec(106.64, -5.55), 0, rotation(-73.36, 5.55));
    expect(out[2]).toBeCloseTo(-1);
  });

  it("va de una longitud a otra por el camino corto", () => {
    expect(lerpLon(170, -170, 0.5)).toBeCloseTo(180);
    expect(lerpLon(-30, -74, 1)).toBeCloseTo(-74);
    expect(lerpLon(-750, -74, 1) % 360).toBeCloseTo(-74);
    expect(lerpLon(20, -74, 0)).toBe(20);
  });

  it("aclara y oscurece como el kit de diseño", () => {
    expect(shade(parseHex("#2B6A99"), 0)).toBe("rgb(43 106 153)");
    expect(shade(parseHex("#000000"), 0.5)).toBe("rgb(128 128 128)");
    expect(shade(parseHex("#C86432"), -0.5)).toBe("rgb(100 50 25)");
  });

  it("la luz de una faceta nunca pasa de sus topes", () => {
    expect(lightFactor(1, 0.5)).toBe(0.14);
    expect(lightFactor(-1, 0)).toBe(-0.38);
  });

  it("las estrellas salen siempre en el mismo sitio (R4)", () => {
    const a = seeded(7);
    const b = seeded(7);
    expect([a(), a(), a()]).toEqual([b(), b(), b()]);
  });
});
