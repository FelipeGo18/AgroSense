import { useState, type ReactNode } from "react";
import { Button } from "../components/Button";
import { Combobox, type Option } from "../components/Combobox";
import { EstimateLabel, ExampleLabel } from "../components/Labels";
import { Mascot, type MascotMood, type MascotSeed } from "../components/Mascot";
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

const MOODS: { id: MascotMood; label: string }[] = [
  { id: "idle", label: "Reposo" },
  { id: "guide", label: "Guía" },
  { id: "celebrate", label: "Celebra" },
  { id: "no_data", label: "Sin datos" },
  { id: "flying", label: "En vuelo" },
];

const SEEDS: { id: MascotSeed; label: string }[] = [
  { id: "sprouted", label: "Semilla germinada" },
  { id: "bean", label: "Frijol" },
  { id: "maize", label: "Maíz" },
];

function Choice<T extends string>({
  legend,
  options,
  value,
  onChange,
}: {
  legend: string;
  options: { id: T; label: string }[];
  value: T;
  onChange: (v: T) => void;
}) {
  return (
    <fieldset className="flex flex-wrap items-center gap-3">
      <legend className="mb-2 font-bold">{legend}</legend>
      {options.map((o) => (
        <Button key={o.id} variant={o.id === value ? "primary" : "secondary"} aria-pressed={o.id === value} onClick={() => onChange(o.id)}>
          {o.label}
        </Button>
      ))}
    </fieldset>
  );
}

export function KitPage() {
  const [municipality, setMunicipality] = useState<Option | null>(null);
  const [priorities, setPriorities] = useState<Priorities>({ water: 3, soil: 5, income: 2, risk: 4 });
  const [saving, setSaving] = useState(false);
  const [mood, setMood] = useState<MascotMood>("guide");
  const [seed, setSeed] = useState<MascotSeed>("sprouted");

  return (
    <main className="mx-auto flex max-w-6xl flex-col gap-6 px-4 py-8 sm:px-8">
      <header className="flex flex-wrap items-center gap-6">
        <Mascot mood="idle" size={150} decorative className="mascot-float" />
        <div className="flex min-w-72 flex-1 flex-col gap-3">
          <h1 className="text-3xl">Kit de componentes · AgroSense</h1>
          <p className="text-texto-principal">
            HU-153 y HU-171 · Estilo diorama low-poly y la mascota Semilla Sputnik. Pruebe todo con el teclado (Tab, flechas, Enter,
            Escape).
          </p>
          <ExampleLabel>los municipios, señales y prioridades de esta página son de muestra</ExampleLabel>
          <p>
            Recorridos de prueba:{" "}
            <a className="font-bold underline" href="/recorrido/1">
              1 · Del satélite al lote
            </a>
            {" · "}
            <a className="font-bold underline" href="/recorrido/2">
              2 · El año del cultivo
            </a>
            {" · "}
            <a className="font-bold underline" href="/recorrido/3">
              3 · Travesía por la cordillera
            </a>
          </p>
        </div>
      </header>

      <Section title="Mascota · Semilla Sputnik">
        <div className="flex flex-wrap items-center gap-8">
          <div className="flex flex-col items-center gap-3 bg-[#F4E9D0] p-4">
            <Mascot mood={mood} seed={seed} size={300} />
          </div>
          <div className="flex min-w-72 flex-1 flex-col gap-5">
            <Choice legend="Pose" options={MOODS} value={mood} onChange={setMood} />
            <Choice
              legend="Semilla (cambia según el contexto; la cara y el brote son la identidad)"
              options={SEEDS}
              value={seed}
              onChange={setSeed}
            />
            <div className="flex items-end gap-4">
              <Mascot mood={mood} seed={seed} size={96} decorative />
              <Mascot mood={mood} seed={seed} size={64} decorative />
              <Mascot mood={mood} seed={seed} size={48} decorative />
              <span className="text-sm text-texto-secundario">96, 64 y 48 px</span>
            </div>
          </div>
        </div>
      </Section>

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
