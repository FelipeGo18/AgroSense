import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { rateFor, restTarget, stepToward } from "@/lib/followScroll";
import { Button } from "./Button";
import { Combobox, normalize, type Option } from "./Combobox";
import { ESTIMATE_TEXT, EstimateLabel, ExampleLabel } from "./Labels";
import { Mascot } from "@/components/mascot/Mascot";
import { PriorityControl, allZero, type Priorities } from "./PriorityControl";
import { SignalCard, signalTone, type Signal } from "./SignalCard";
import { LIGHT_LABEL, TrafficLightBadge, type Light } from "./TrafficLightBadge";

describe("Button", () => {
  it("en carga se bloquea y lo anuncia", async () => {
    const onClick = vi.fn();
    render(
      <Button loading loadingText="Calculando…" onClick={onClick}>
        Ver
      </Button>,
    );
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

describe("Mascot", () => {
  it("dice con texto qué semilla es y qué hace", () => {
    render(<Mascot mood="celebrate" seed="maize" />);
    expect(screen.getByRole("img", { name: "Mascota de AgroSense, grano de maíz, celebrando" })).toBeInTheDocument();
  });

  it("cambiar la semilla no cambia la cara ni la pose", () => {
    const { container, rerender } = render(<Mascot mood="guide" seed="sprouted" />);
    const face = () => container.querySelector(".mascot-eyes")!.innerHTML + container.querySelector(".mascot-mouth")!.innerHTML;
    const before = face();
    rerender(<Mascot mood="guide" seed="bean" />);
    expect(face()).toBe(before);
  });

  it("sin datos no usa la cara de celebrar ni se anuncia como riesgo (R1)", () => {
    render(<Mascot mood="no_data" />);
    expect(screen.getByRole("img")).toHaveAccessibleName(/sin datos/);
  });

  it("decorativa queda fuera del árbol de accesibilidad", () => {
    const { container } = render(<Mascot decorative />);
    expect(container.querySelector("svg")).toHaveAttribute("aria-hidden", "true");
  });
});

describe("Recorridos: tope de velocidad del scroll", () => {
  const simulate = (target: number, total: number, maxRate: number) => {
    let progress = 0;
    let ms = 0;
    while (progress !== target && ms < 120_000) {
      progress = stepToward(progress, target, 16, total, maxRate);
      ms += 16;
    }
    return ms / 1000;
  };

  it("un scroll brusco hasta el final no reproduce el recorrido en un instante", () => {
    // 15,4 unidades de línea de tiempo a 1,1 por segundo: 14 s como mínimo, aunque el scroll llegue de golpe.
    expect(simulate(1, 15.4, 1.1)).toBeGreaterThanOrEqual(14);
  });

  it("un paso entre escenas dura al menos 1 / velocidad máxima", () => {
    expect(simulate(1 / 15.4, 15.4, 1.1)).toBeGreaterThanOrEqual(0.9);
  });

  it("un scroll lento se sigue casi al instante y llega exacto", () => {
    const next = stepToward(0.5, 0.5004, 16, 15.4, 1.1);
    expect(next).toBeGreaterThan(0.5);
    expect(next).toBeLessThanOrEqual(0.5004);
    expect(simulate(0.01, 15.4, 1.1)).toBeLessThan(1);
  });
});

describe("Recorridos: el seguidor del scroll aguanta entradas hostiles", () => {
  // Generador determinista: las pruebas con valores «al azar» dan siempre lo mismo.
  const rng = (seed: number) => () => ((seed = (seed * 1103515245 + 12345) % 2147483648), seed / 2147483648);

  it("nunca supera el tope de velocidad ni se pasa del destino, con destinos y cuadros caóticos", () => {
    const next = rng(7);
    const total = 8.5;
    const maxRate = 1.1;
    let progress = 0;
    for (let i = 0; i < 20_000; i++) {
      const target = next(); // el scroll salta a cualquier parte en cada cuadro
      const dt = 1 + next() * 63; // cuadros de 1 a 64 ms
      const before = progress;
      progress = stepToward(progress, target, dt, total, maxRate);
      const rate = (Math.abs(progress - before) * total) / (dt / 1000);
      expect(rate).toBeLessThanOrEqual(maxRate + 1e-9);
      expect(progress).toBeGreaterThanOrEqual(Math.min(before, target) - 1e-12);
      expect(progress).toBeLessThanOrEqual(Math.max(before, target) + 1e-12);
    }
  });

  it("con el destino quieto siempre llega, sin rebotar", () => {
    const next = rng(11);
    for (let round = 0; round < 200; round++) {
      const target = next();
      let progress = next();
      let lastGap = Math.abs(target - progress);
      let frames = 0;
      while (progress !== target && frames < 10_000) {
        progress = stepToward(progress, target, 16, 8.5, 1.1);
        const gap = Math.abs(target - progress);
        expect(gap).toBeLessThanOrEqual(lastGap);
        lastGap = gap;
        frames++;
      }
      expect(progress).toBe(target);
    }
  });

  it("un cuadro de duración cero o un destino igual al actual no mueven nada ni dan NaN", () => {
    expect(stepToward(0.3, 0.9, 0, 8.5, 1.1)).toBe(0.3);
    expect(stepToward(0.4, 0.4, 16, 8.5, 1.1)).toBe(0.4);
    expect(Number.isNaN(stepToward(0, 1, 16, 8.5, 1.1))).toBe(false);
  });
});

describe("Recorridos: imán hacia las paradas con contenido", () => {
  // Las cuatro paradas con interfaz del recorrido 1, en unidades de línea de tiempo.
  const rests = [
    [0, 1],
    [2.65, 3.65],
    [4.7, 5.7],
    [7.05, 8.05],
  ] as const;

  it("dentro de una parada no mueve al usuario", () => {
    for (const t of [0, 0.5, 1, 2.65, 3.2, 5.7, 8.05]) expect(restTarget(t, 1, rests)).toBeNull();
  });

  it("en una escena de relleno, bajando, lleva a la parada siguiente; subiendo, a la anterior", () => {
    expect(restTarget(1.8, 1, rests)).toBeCloseTo(2.71);
    expect(restTarget(1.8, -1, rests)).toBeCloseTo(0.94);
    expect(restTarget(6.2, 1, rests)).toBeCloseTo(7.11);
    expect(restTarget(6.2, -1, rests)).toBeCloseTo(5.64);
  });

  it("el destino siempre cae dentro de una parada: nunca deja al usuario en el relleno", () => {
    for (let t = 0; t <= 8.05; t += 0.01) {
      for (const direction of [-1, 0, 1]) {
        const to = restTarget(t, direction, rests);
        if (to !== null) expect(rests.some(([a, b]) => to >= a && to <= b)).toBe(true);
      }
    }
  });

  it("sin paradas definidas no hace nada", () => {
    expect(restTarget(3, 1, [])).toBeNull();
  });
});

describe("Recorridos: velocidad según el tipo de movimiento", () => {
  it("con rueda o dedo el tope no se levanta nunca, por lejos que quede el destino", () => {
    for (const gap of [0.1, 2, 5, 8.5]) expect(rateFor(gap, 1.3, false)).toBe(1.3);
  });

  it("un salto corto (avanzar página) va al tope normal", () => {
    expect(rateFor(1, 1.3, true)).toBe(1.3);
    expect(rateFor(2, 1.3, true)).toBe(1.3);
  });

  it("un salto largo (barra de scroll, Inicio o Fin) se acelera, hasta 4 veces", () => {
    expect(rateFor(4, 1.3, true)).toBeCloseTo(1.3 * 2.5);
    expect(rateFor(8.5, 1.3, true)).toBeCloseTo(1.3 * 4);
    expect(rateFor(100, 1.3, true)).toBeCloseTo(1.3 * 4);
  });
});
