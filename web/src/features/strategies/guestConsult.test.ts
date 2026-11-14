import { afterEach, describe, expect, it } from "vitest";
import { PATHS } from "@/app/paths";
import { EMPTY_STRATEGY, afterLoginPath, clearGuestConsult, readGuestConsult, writeGuestConsult } from "./entry";
afterEach(() => sessionStorage.clear());
describe("Consulta de invitado (HU-168, R9)", () => {
  it("guarda solo en la pestaña y limpia consulta y área", () => {
    writeGuestConsult({
      ...EMPTY_STRATEGY,
      municipalityId: "15646",
      areaText: " 2,73 ",
      irrigation: "si",
      previousMode: "crops",
      previous: ["papa", "", ""],
    });
    expect(readGuestConsult()).toEqual({ municipalityId: "15646", areaText: "2,73", irrigation: "si", previousCrops: ["papa"] });
    sessionStorage.setItem("agrosense.area", "2,73");
    expect(afterLoginPath()).toBe(PATHS.addLot + "?desde=consulta");
    clearGuestConsult();
    expect(readGuestConsult()).toBeNull();
    expect(sessionStorage.getItem("agrosense.area")).toBeNull();
    expect(afterLoginPath()).toBe(PATHS.farm);
  });
  it.each([
    "{roto",
    "null",
    "[]",
    '{"municipalityId":"15646"}',
    '{"municipalityId":"15646","areaText":[],"previousCrops":[],"irrigation":"si"}',
  ])("rechaza almacenamiento dañado: %s", (raw) => {
    sessionStorage.setItem("agrosense.guest-consult", raw);
    expect(readGuestConsult()).toBeNull();
    expect(afterLoginPath()).toBe(PATHS.farm);
  });
  it("no guarda sin municipio ni conserva cultivos cuando no había", () => {
    writeGuestConsult(EMPTY_STRATEGY);
    expect(readGuestConsult()).toBeNull();
    writeGuestConsult({ ...EMPTY_STRATEGY, municipalityId: "15646", previousMode: "none", previous: ["papa", "", ""] });
    expect(readGuestConsult()?.previousCrops).toEqual([]);
  });
});
