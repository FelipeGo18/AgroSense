import { act, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { GreenChart } from "@/pages/strategies/GreenChart";
import { describe as describeActivity } from "@/pages/account/activity";
import { supplyNote } from "@/features/diagnosis/signals";
import { suitabilityFacts } from "@/features/diagnosis/windows";
import { Alert } from "@/components/ui/Alert";
import { i18n } from "./i18n";

it("actualiza los meses del eje, la tabla y el resumen sin desmontar la gráfica", async () => {
  await act(() => i18n.changeLanguage("es"));
  render(<GreenChart points={[{ period: 1, ndvi_normal: 0.5 }]} spans={[]} />);
  expect(screen.getByText("1 · desde enero")).toBeInTheDocument();
  await act(() => i18n.changeLanguage("en"));
  expect(screen.getByText("1 · since January")).toBeInTheDocument();
  const chart = screen.getByRole("img");
  expect(chart.querySelectorAll("text")[3].textContent).toBe("J");
  await userEvent.click(chart.querySelector('rect[fill="transparent"]')!);
  expect(screen.getByText(/Period 1.*January/)).toBeInTheDocument();
});

it("traduce los campos de actividad, el sufijo preliminar y la altitud", async () => {
  await act(() => i18n.changeLanguage("en"));
  const item: Parameters<typeof describeActivity>[0] = {
    event_id: "example",
    occurred_at: "2026-11-15T00:00:00Z",
    actor_role: "farmer",
    object_type: "lot",
    object_id: "example-lot",
    ticket_id: null,
    action: "lot.updated",
    outcome: "ok",
    details: { fields: ["irrigated", "municipality_id", "crop_id"] },
  };
  expect(describeActivity(item).detail).toBe("Changed: irrigation, municipality, crop");
  expect(supplyNote({ year: 2025, semester: "B", preliminary: true })).toContain(", preliminary");
  const facts = { tmean_annual_c: 12.5, altitude_m: 2500, basis: "municipality" };
  expect(suitabilityFacts(facts as Parameters<typeof suitabilityFacts>[0])).toContain("2,500");
});

it("una validación local en inglés no anuncia detalles de cálculo en español", async () => {
  await act(() => i18n.changeLanguage("en"));
  render(<Alert>Choose at least one priority.</Alert>);
  expect(within(screen.getByRole("alert")).getByText("Choose at least one priority.")).toBeInTheDocument();
  expect(screen.queryByText("Calculation details are in Spanish")).not.toBeInTheDocument();
});
