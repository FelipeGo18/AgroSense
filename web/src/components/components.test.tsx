import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { Button } from "./Button";
import { Combobox, normalize, type Option } from "./Combobox";
import { ESTIMATE_TEXT, EstimateLabel, ExampleLabel } from "./Labels";
import { PriorityControl, allZero, type Priorities } from "./PriorityControl";
import { SignalCard, signalTone, type Signal } from "./SignalCard";
import { LIGHT_LABEL, TrafficLightBadge, type Light } from "./TrafficLightBadge";

describe("Button", () => {
  it("en carga se bloquea y lo anuncia", async () => {
    const onClick = vi.fn();
    render(<Button loading loadingText="Calculando…" onClick={onClick}>Ver</Button>);
    const button = screen.getByRole("button", { name: "Calculando…" });
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute("aria-busy", "true");
    await userEvent.click(button);
    expect(onClick).not.toHaveBeenCalled();
  });

  it("responde al teclado", async () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Ver</Button>);
    await userEvent.tab();
    await userEvent.keyboard("{Enter}");
    expect(onClick).toHaveBeenCalledOnce();
  });
});

describe("TrafficLightBadge", () => {
  it.each(Object.keys(LIGHT_LABEL) as Light[])("%s muestra texto, no solo color (W2)", (light) => {
    render(<TrafficLightBadge light={light} />);
    expect(screen.getByText(LIGHT_LABEL[light])).toBeInTheDocument();
  });

  it("no evaluable no usa el estilo rojo (R1)", () => {
    const { container } = render(<TrafficLightBadge light="not_evaluable" />);
    expect(container.innerHTML).not.toMatch(/semaforo-rojo/);
  });
});

describe("SignalCard", () => {
  it("sin datos es «datos insuficientes», nunca riesgo (R1)", () => {
    const signal: Signal = { status: "insufficient_data", level: null, indicators: [], reasons: ["Sin datos"] };
    expect(signalTone(signal).tone).toBe("insufficient_data");
    const { container } = render(<SignalCard kind="market" signal={signal} />);
    expect(screen.getByText("Datos insuficientes")).toBeInTheDocument();
    expect(container.innerHTML).not.toMatch(/semaforo-rojo/);
  });

  it("desfavorable se muestra con su razón", () => {
    render(
      <SignalCard
        kind="supply"
        signal={{ status: "available", level: "unfavorable", indicators: ["planted_change_pct"], reasons: ["Más área que el promedio"] }}
      />,
    );
    expect(screen.getByText("Desfavorable")).toBeInTheDocument();
    expect(screen.getByText("Más área que el promedio")).toBeInTheDocument();
  });
});

describe("Combobox", () => {
  const options: Option[] = [
    { id: "15001", label: "Tunja" },
    { id: "15646", label: "Samacá" },
  ];

  function Harness({ onPick }: { onPick: (o: Option) => void }) {
    const [value, setValue] = useState<Option | null>(null);
    return (
      <Combobox
        label="Municipio"
        options={options}
        value={value}
        onChange={(o) => {
          setValue(o);
          onPick(o);
        }}
      />
    );
  }

  it("busca sin tildes y elige con el teclado", async () => {
    const onPick = vi.fn();
    render(<Harness onPick={onPick} />);
    const input = screen.getByRole("combobox", { name: "Municipio" });
    await userEvent.type(input, "samaca");
    expect(screen.getAllByRole("option")).toHaveLength(1);
    await userEvent.keyboard("{Enter}");
    expect(onPick).toHaveBeenCalledWith(options[1]);
    expect(input).toHaveValue("Samacá");
  });

  it("lo escrito fuera del catálogo no queda como valor (W1)", async () => {
    const onPick = vi.fn();
    render(<Harness onPick={onPick} />);
    const input = screen.getByRole("combobox", { name: "Municipio" });
    await userEvent.type(input, "Inventado");
    expect(screen.getByText(/Sin resultados/)).toBeInTheDocument();
    await userEvent.tab();
    expect(onPick).not.toHaveBeenCalled();
    expect(input).toHaveValue("");
  });

  it("normaliza tildes y mayúsculas", () => {
    expect(normalize(" Bogotá ")).toBe("bogota");
  });
});

describe("PriorityControl", () => {
  it("avisa cuando todas las prioridades están en 0 (el contrato responde 422)", () => {
    const zero: Priorities = { water: 0, soil: 0, income: 0, risk: 0 };
    expect(allZero(zero)).toBe(true);
    render(<PriorityControl value={zero} onChange={() => {}} />);
    expect(screen.getByRole("alert")).toHaveTextContent("Suba al menos una prioridad");
  });

  it("cambia con las flechas del teclado, de 0 a 5", async () => {
    const onChange = vi.fn();
    render(<PriorityControl value={{ water: 5, soil: 0, income: 0, risk: 1 }} onChange={onChange} />);
    const water = screen.getByRole("radiogroup", { name: /Agua/ });
    expect(within(water).getAllByRole("radio")).toHaveLength(6);
    const current = within(water).getByRole("radio", { checked: true });
    expect(current).toHaveAccessibleName("5 de 5, Lo más importante");
    current.focus();
    await userEvent.keyboard("{ArrowLeft}");
    expect(onChange).toHaveBeenCalledWith({ water: 4, soil: 0, income: 0, risk: 1 });
  });

  it("tocar una semilla fija ese valor", async () => {
    const onChange = vi.fn();
    render(<PriorityControl value={{ water: 1, soil: 0, income: 0, risk: 0 }} onChange={onChange} />);
    const soil = screen.getByRole("radiogroup", { name: /Suelo/ });
    await userEvent.click(within(soil).getByRole("radio", { name: /^3 de 5/ }));
    expect(onChange).toHaveBeenCalledWith({ water: 1, soil: 3, income: 0, risk: 0 });
  });
});

describe("Rótulos", () => {
  it("el rótulo de estimación lleva el texto fijo de R10", () => {
    render(<EstimateLabel />);
    expect(screen.getByText(ESTIMATE_TEXT)).toBeInTheDocument();
  });

  it("el rótulo de ejemplo dice «Ejemplo» (R5)", () => {
    render(<ExampleLabel />);
    expect(screen.getByText("Ejemplo")).toBeInTheDocument();
  });
});
