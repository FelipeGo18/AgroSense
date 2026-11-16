import { t } from "@/lib/i18n";
import { Link } from "@/components/layout/LanguageLink";
import { useTranslation } from "react-i18next";
import { useState, type ReactNode } from "react";
import { Button } from "@/components/ui/Button";
import { Combobox, type Option } from "@/components/ui/Combobox";
import { EstimateLabel, ExampleLabel } from "@/components/ui/Labels";
import { Mascot, type MascotMood, type MascotSeed } from "@/components/mascot/Mascot";
import { Plate } from "@/components/ui/Plate";
import { PriorityControl, type Priorities } from "@/components/ui/PriorityControl";
import { SignalCard, type Signal } from "@/components/ui/SignalCard";
import { TrafficLightBadge } from "@/components/ui/TrafficLightBadge";

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

const SIGNALS = (): Record<string, Signal> => ({
  favorable: {
    status: "available",
    level: "favorable",
    indicators: ["precip_anomaly_pct"],
    reasons: [t("lab.kit.signal.rain")],
  },
  unfavorable: {
    status: "available",
    level: "unfavorable",
    indicators: ["frost_freq_pct"],
    reasons: [t("lab.kit.signal.frost")],
  },
  // La oferta y el mercado con dato se muestran sin calificar (decisión 17): `available` sin nivel.
  unrated: {
    status: "available",
    level: null,
    indicators: ["planted_change_pct"],
    reasons: [t("lab.kit.signal.supply")],
  },
  insufficient: {
    status: "insufficient_data",
    level: null,
    indicators: [],
    reasons: [t("lab.kit.signal.market")],
  },
});

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="relative flex flex-col gap-4 px-7 pt-6 pb-9">
      <Plate c={24} fill="var(--color-superficie-panel)" depth={8} bottom={8} side="var(--color-superficie-borde)" />
      <h2 className="relative text-xl">{title}</h2>
      <div className="relative flex flex-col gap-4">{children}</div>
    </section>
  );
}

const MOODS = (): { id: MascotMood; label: string }[] => [
  { id: "idle", label: t("lab.kit.mood.idle") },
  { id: "guide", label: t("lab.kit.mood.guide") },
  { id: "celebrate", label: t("lab.kit.mood.celebrate") },
  { id: "no_data", label: t("lab.kit.mood.noData") },
  { id: "flying", label: t("lab.kit.mood.flying") },
];

const SEEDS = (): { id: MascotSeed; label: string }[] => [
  { id: "sprouted", label: t("lab.kit.seed.sprouted") },
  { id: "bean", label: t("lab.kit.seed.bean") },
  { id: "maize", label: t("lab.kit.seed.maize") },
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
  const { t, i18n } = useTranslation();
  const reasonLanguage = i18n.resolvedLanguage === "en" ? "en" : "es";
  const [municipality, setMunicipality] = useState<Option | null>(null);
  const [priorities, setPriorities] = useState<Priorities>({ water: 3, soil: 5, income: 2, risk: 4 });
  const [saving, setSaving] = useState(false);
  const [mood, setMood] = useState<MascotMood>("guide");
  const [seed, setSeed] = useState<MascotSeed>("sprouted");

  return (
    <main className="mx-auto flex max-w-6xl flex-col gap-6 px-4 py-8 sm:px-8">
      <title>{t("lab.kit.title")}</title>
      <header className="flex flex-wrap items-center gap-6">
        <Mascot mood="idle" size={150} decorative className="mascot-float" />
        <div className="flex w-full min-w-0 flex-col gap-3 sm:flex-1">
          <h1 className="text-3xl">{t("lab.kit.title")}</h1>
          <p className="text-texto-principal">{t("lab.kit.intro")}</p>
          <ExampleLabel>{t("lab.kit.example")}</ExampleLabel>
          <p>
            {t("lab.kit.journeys")}{" "}
            <Link className="font-bold underline" to="/recorrido/1">
              {t("lab.nav.orbit")}
            </Link>
            {" · "}
            <Link className="font-bold underline" to="/recorrido/2">
              {t("lab.nav.year")}
            </Link>
            {" · "}
            <Link className="font-bold underline" to="/recorrido/3">
              {t("lab.nav.range")}
            </Link>
          </p>
        </div>
      </header>

      <Section title={t("lab.kit.mascot")}>
        <div className="flex flex-wrap items-center gap-8">
          <div className="flex w-full max-w-[332px] flex-col items-center gap-3 bg-[#F4E9D0] p-4">
            <Mascot mood={mood} seed={seed} size={300} className="h-auto max-w-full" />
          </div>
          <div className="flex min-w-0 flex-1 flex-col gap-5">
            <Choice legend={t("lab.kit.pose")} options={MOODS()} value={mood} onChange={setMood} />
            <Choice legend={t("lab.kit.seed")} options={SEEDS()} value={seed} onChange={setSeed} />
            <div className="flex flex-wrap items-end gap-4">
              <Mascot mood={mood} seed={seed} size={96} decorative />
              <Mascot mood={mood} seed={seed} size={64} decorative />
              <Mascot mood={mood} seed={seed} size={48} decorative />
              <span className="text-sm text-texto-secundario">{t("lab.kit.sizes")}</span>
            </div>
          </div>
        </div>
      </Section>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Section title={t("lab.kit.button")}>
          <div className="flex flex-wrap gap-4">
            <Button
              loading={saving}
              loadingText={t("lab.kit.calculating")}
              onClick={() => {
                setSaving(true);
                setTimeout(() => setSaving(false), 1500);
              }}
            >
              {t("lab.diagnosis")}
            </Button>
            <Button variant="secondary">{t("lab.kit.changeCrop")}</Button>
          </div>
          <div className="flex flex-wrap gap-4">
            <Button disabled>{t("lab.kit.disabled")}</Button>
            <Button loading>{t("lab.kit.loading")}</Button>
          </div>
        </Section>

        <Section title={t("lab.kit.combobox")}>
          <Combobox
            label={t("lab.municipality")}
            placeholder={t("lab.municipality.placeholder")}
            options={MUNICIPALITIES}
            value={municipality}
            onChange={setMunicipality}
          />
          <Combobox label={t("lab.kit.loadingCrop")} options={[]} value={null} onChange={() => {}} loading />
          <Combobox label={t("lab.kit.disabledSemester")} options={[]} value={null} onChange={() => {}} disabled />
        </Section>

        <Section title={t("lab.kit.trafficLight")}>
          <div className="flex flex-col items-start gap-3">
            <TrafficLightBadge light="green" />
            <TrafficLightBadge light="yellow" />
            <TrafficLightBadge light="red" />
            <TrafficLightBadge light="not_evaluable" />
            <TrafficLightBadge loading />
          </div>
        </Section>

        <Section title={t("lab.kit.priority")}>
          <PriorityControl value={priorities} onChange={setPriorities} />
          <Button variant="secondary" onClick={() => setPriorities({ water: 0, soil: 0, income: 0, risk: 0 })}>
            {t("lab.kit.zero")}
          </Button>
        </Section>
      </div>

      <h2 className="text-xl">{t("lab.kit.signals")}</h2>
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        <SignalCard kind="climate" signal={SIGNALS().favorable} reasonLanguage={reasonLanguage} />
        <SignalCard kind="climate" signal={SIGNALS().unfavorable} reasonLanguage={reasonLanguage} />
        <SignalCard kind="supply" signal={SIGNALS().unrated} reasonLanguage={reasonLanguage} />
        <SignalCard kind="market" signal={SIGNALS().insufficient} reasonLanguage={reasonLanguage} />
        <SignalCard kind="climate" loading />
      </div>

      <Section title={t("lab.kit.labels")}>
        <div className="flex flex-col items-start gap-3">
          <ExampleLabel />
          <EstimateLabel />
        </div>
      </Section>
    </main>
  );
}
