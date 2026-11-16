import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { i18n } from "@/lib/i18n";
import { KitPage } from "./KitPage";
import { LabIndexPage } from "./LabIndexPage";

it("el kit cambia de idioma sin reiniciar la semilla y traduce sus ejemplos locales", async () => {
  render(
    <MemoryRouter>
      <KitPage />
    </MemoryRouter>,
  );
  await userEvent.click(screen.getByRole("button", { name: "Frijol" }));
  await act(() => i18n.changeLanguage("en"));
  expect(screen.getByRole("heading", { name: "Component kit · AgroSense" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Bean", pressed: true })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "1 · From satellite to plot" })).toHaveAttribute("href", "/recorrido/1?lang=en");
  expect(screen.getByText("Semester rainfall within the favorable range").closest("[lang]")).toHaveAttribute("lang", "en");
});

it("el índice del laboratorio conserva el idioma en todos sus enlaces", async () => {
  await act(() => i18n.changeLanguage("en"));
  render(
    <MemoryRouter>
      <LabIndexPage />
    </MemoryRouter>,
  );
  expect(screen.getByRole("heading", { name: "AgroSense · prototypes" })).toBeInTheDocument();
  for (const link of screen.getAllByRole("link")) expect(link.getAttribute("href")).toContain("lang=en");
});
