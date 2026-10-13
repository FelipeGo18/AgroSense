import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { resetLightMode, setLightMode } from "@/lib/lightMode";
import { LightModeSwitch, LightModeToggle } from "./LightModeToggle";

beforeEach(() => act(() => setLightMode(false)));
afterEach(() => act(() => resetLightMode()));

describe("Botón «Modo ligero» (HU-158)", () => {
  it("cambia el modo, lo dice en voz alta y lo marca en <html>", async () => {
    render(<LightModeToggle />);
    const button = screen.getByRole("button", { name: "Modo ligero" });
    expect(button).toHaveAttribute("aria-pressed", "false");
    await userEvent.click(button);
    expect(button).toHaveAttribute("aria-pressed", "true");
    expect(document.querySelector("[aria-live]")).toHaveTextContent("Modo ligero activado");
    expect(document.documentElement).toHaveAttribute("data-light");
    await userEvent.click(button);
    expect(button).toHaveAttribute("aria-pressed", "false");
    expect(document.querySelector("[aria-live]")).toHaveTextContent("Modo ligero desactivado");
    expect(document.documentElement).not.toHaveAttribute("data-light");
  });

  it("al pasar el cursor dice qué hace en una frase, y Escape lo cierra", async () => {
    render(<LightModeToggle />);
    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
    await userEvent.hover(screen.getByRole("button", { name: "Modo ligero" }));
    const tip = await screen.findByRole("tooltip");
    expect(tip).toHaveTextContent("Modo ligero: desactivado");
    expect(tip).toHaveTextContent("Quita las animaciones y el scroll suave");
    expect(screen.getByRole("button", { name: "Modo ligero" })).toHaveAccessibleDescription(/La información es la misma/);
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
  });

  it("al tocarlo deja el aviso abierto con el estado nuevo, también sin cursor", async () => {
    render(<LightModeToggle />);
    await userEvent.click(screen.getByRole("button", { name: "Modo ligero" }));
    await userEvent.unhover(screen.getByRole("button", { name: "Modo ligero" }));
    expect(await screen.findByRole("tooltip")).toHaveTextContent("Modo ligero: activado");
  });
});

describe("Interruptor «Modo ligero» del menú", () => {
  it("dice su estado con texto y cambia el modo", async () => {
    render(<LightModeSwitch />);
    const toggle = screen.getByRole("switch", { name: /Modo ligero/ });
    expect(toggle).toHaveAttribute("aria-checked", "false");
    expect(screen.getByText("Desactivado")).toBeInTheDocument();
    await userEvent.click(toggle);
    expect(toggle).toHaveAttribute("aria-checked", "true");
    expect(screen.getByText("Activado")).toBeInTheDocument();
  });
});
