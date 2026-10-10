import { useState, type ReactNode } from "react";
import { Button } from "../components/Button";
import { Combobox, type Option } from "../components/Combobox";
import { EstimateLabel, ExampleLabel } from "../components/Labels";
import { Plate } from "../components/Plate";
import { PriorityControl, type Priorities } from "../components/PriorityControl";
import { SignalCard, type Signal } from "../components/SignalCard";
import { TrafficLightBadge } from "../components/TrafficLightBadge";

// Datos de ejemplo para mostrar el kit (R5: se rotulan en pantalla).
const MUNICIPALITIES: Option[] = [
  { id: "15001", label: "Tunja", hint: "Boyacá" },
  { id: "15047", label: "Aquitania", hint: "Boyacá" },
  { id: "15238", label: "Duitama", hint: "Boyacá" },
  { id: "15646", label: "Samacá", hint: "Boyacá" },
  { id: "15759", label: "Sogamoso", hint: "Boyacá" },
  { id: "15814", label: "Toca", hint: "Boyacá" },
  { id: "15861", label: "Ventaquemada", hint: "Boyacá" },
];

const SIGNALS: Record<string, Signal> = {
  favorable: {
    status: "available",
    level: "favorable",
    indicators: ["precip_anomaly_pct"],
    reasons: ["Lluvia del semestre dentro del rango favorable"],
  },
  unfavorable: {
    status: "available",
    level: "unfavorable",
    indicators: ["planted_change_pct"],
    reasons: ["Área sembrada mayor que el promedio de los tres semestres B anteriores"],
  },
  insufficient: {
    status: "insufficient_data",
    level: null,
    indicators: [],
    reasons: ["Sin datos de mercado para la zona"],
  },
};

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="relative flex flex-col gap-4 px-7 pt-6 pb-9">
      <Plate c={24} fill="var(--color-superficie-panel)" depth={8} bottom={8} side="var(--color-superficie-borde)" />
      <h2 className="relative text-xl">{title}</h2>
      <div className="relative flex flex-col gap-4">{children}</div>
    </section>
  );
}

export function KitPage() {
  const [municipality, setMunicipality] = useState<Option | null>(null);
  const [priorities, setPriorities] = useState<Priorities>({ water: 3, soil: 5, income: 2, risk: 4 });
  const [saving, setSaving] = useState(false);

  return (
    <main className="mx-auto flex max-w-6xl flex-col gap-6 px-4 py-8 sm:px-8">
      <header className="flex flex-col gap-3">
        <h1 className="text-3xl">Kit de componentes · AgroSense</h1>
        <p className="text-texto-principal">
          HU-153 · Estilo diorama low-poly: cada pieza es un bloque del mismo paisaje. Pruebe todo con el teclado (Tab, flechas, Enter, Escape).
        </p>
        <ExampleLabel>los municipios, señales y prioridades de esta página son de muestra</ExampleLabel>
      </header>

      <div className="grid gap-6 lg:grid-cols-2">
        <Section title="Botón">
          <div className="flex flex-wrap gap-4">
            <Button
              loading={saving}
              loadingText="Calculando…"
              onClick={() => {
                setSaving(true);
                setTimeout(() => setSaving(false), 1500);
              }}
            >
              Ver diagnóstico
            </Button>
            <Button variant="secondary">Cambiar cultivo</Button>
          </div>
          <div className="flex flex-wrap gap-4">
            <Button disabled>Deshabilitado</Button>
            <Button loading>Cargando</Button>
          </div>
        </Section>

        <Section title="Selector con autocompletado">
          <Combobox
            label="Municipio"
            placeholder="Escriba su municipio"
            options={MUNICIPALITIES}
            value={municipality}
            onChange={setMunicipality}
          />
          <Combobox label="Cultivo (cargando)" options={[]} value={null} onChange={() => {}} loading />
          <Combobox label="Semestre (deshabilitado)" options={[]} value={null} onChange={() => {}} disabled />
        </Section>

        <Section title="Insignia de semáforo">
          <div className="flex flex-col items-start gap-3">
            <TrafficLightBadge light="green" />
            <TrafficLightBadge light="yellow" />
            <TrafficLightBadge light="red" />
            <TrafficLightBadge light="not_evaluable" />
            <TrafficLightBadge loading />
          </div>
        </Section>

        <Section title="Control de prioridad">
          <PriorityControl value={priorities} onChange={setPriorities} />
          <Button variant="secondary" onClick={() => setPriorities({ water: 0, soil: 0, income: 0, risk: 0 })}>
            Poner todo en 0
          </Button>
        </Section>
      </div>

      <h2 className="text-xl">Tarjetas de señal</h2>
      <div className="grid gap-6 md:grid-cols-2">
        <SignalCard kind="climate" signal={SIGNALS.favorable} />
        <SignalCard kind="supply" signal={SIGNALS.unfavorable} />
        <SignalCard kind="market" signal={SIGNALS.insufficient} />
        <SignalCard kind="climate" loading />
      </div>

      <Section title="Rótulos">
        <div className="flex flex-col items-start gap-3">
          <ExampleLabel />
          <EstimateLabel />
        </div>
      </Section>
    </main>
  );
}
