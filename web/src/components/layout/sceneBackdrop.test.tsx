import { render } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { setLightMode } from "@/lib/lightMode";
import { SceneBackdrop } from "./SceneBackdrop";

beforeEach(() => setLightMode(true));
afterEach(() => setLightMode(false));

describe("Fondo de paisaje de la consulta", () => {
  it("de fondo completo cubre la pantalla detrás de la página, sin anunciarse", () => {
    const { container } = render(<SceneBackdrop scene="municipio" variant="full" />);
    const img = container.querySelector("img");
    expect(img?.getAttribute("src")).toContain("a5-municipio");
    expect(img).toHaveAttribute("aria-hidden", "true");
    expect(img?.className).toContain("fixed");
  });

  it("en franja va arriba, con el paisaje que se pida y sin recibir el puntero", () => {
    const { container } = render(<SceneBackdrop scene="vereda" variant="band" />);
    const band = container.firstElementChild;
    expect(band).toHaveAttribute("aria-hidden", "true");
    expect(band?.className).toContain("pointer-events-none");
    expect(band?.querySelector("img")?.getAttribute("src")).toContain("a6-vereda");
  });
});
