import { t } from "@/lib/i18n";
import { useTranslation } from "react-i18next";
import { useRef, type KeyboardEvent } from "react";
import { Plate } from "./Plate";

/** `priorities` del cuerpo de POST /api/v1/rotations: enteros de 0 a 5; todos en 0 es inválido. */
export interface Priorities {
  water: number;
  soil: number;
  income: number;
  risk: number;
}

const CRITERIA = (): { key: keyof Priorities; label: string; hint: string }[] => [
  { key: "water", label: t("landing.signal.water"), hint: t("components.ui.PriorityControl.lowWaterNeeds") },
  { key: "soil", label: t("landing.signal.soil"), hint: t("components.ui.PriorityControl.protectingTheSoil") },
  { key: "income", label: t("components.ui.PriorityControl.income"), hint: t("priorities.market.hint") },
  { key: "risk", label: t("components.ui.PriorityControl.risk"), hint: t("components.ui.PriorityControl.lowRisk") },
];

export const LEVEL_WORD = () => [
  t("components.ui.PriorityControl.notImportant"),
  t("components.ui.PriorityControl.veryLittle"),
  t("components.ui.PriorityControl.little"),
  t("components.ui.PriorityControl.somewhat"),
  t("components.ui.PriorityControl.veryMuch"),
  t("components.ui.PriorityControl.mostImportant"),
];

export const MAX_PRIORITY = 5;
const LEVELS = [0, 1, 2, 3, 4, 5];

export function allZero(p: Priorities) {
  return CRITERIA().every(({ key }) => p[key] === 0);
}

/** La semilla del kit: llena o vacía. La usan el control de prioridad y la escala de aptitud (HU-194). */
export function Seed({ filled }: { filled: boolean }) {
  useTranslation();
  return (
    <svg aria-hidden="true" viewBox="0 0 44 44" className="size-full">
      {filled ? (
        <>
          <polygon
            points="22,3 35,14 35,26 22,41 9,26 9,14"
            fill="var(--color-paleta-brote)"
            stroke="var(--color-oscuro-brote)"
            strokeWidth="2.5"
            strokeLinejoin="round"
          />
          <polygon points="22,3 35,14 35,26 22,41" fill="color-mix(in srgb, var(--color-paleta-brote), black 14%)" />
        </>
      ) : (
        <polygon
          points="22,3 35,14 35,26 22,41 9,26 9,14"
          fill="var(--color-superficie-panel)"
          stroke="var(--color-oscuro-cielo)"
          strokeWidth="2"
          strokeLinejoin="round"
        />
      )}
    </svg>
  );
}

export interface SeedRowProps {
  label: string;
  hint: string;
  /** Una línea bajo el nombre, para lo que no se puede negociar (por ejemplo, que un riesgo grave cuenta siempre). */
  note?: string;
  value: number;
  disabled: boolean;
  onChange: (value: number) => void;
}

/** Un «0» y cinco semillas. Es un grupo de opciones: se toca la semilla, no se arrastra. */
export function SeedRow({ label, hint, note, value, disabled, onChange }: SeedRowProps) {
  useTranslation();
  const group = useRef<HTMLDivElement>(null);

  const move = (next: number) => {
    const clamped = Math.max(0, Math.min(MAX_PRIORITY, next));
    onChange(clamped);
    group.current?.querySelector<HTMLButtonElement>(`[data-level="${clamped}"]`)?.focus();
  };

  const onKeyDown = (e: KeyboardEvent) => {
    if (e.key === "ArrowRight" || e.key === "ArrowUp") move(value + 1);
    else if (e.key === "ArrowLeft" || e.key === "ArrowDown") move(value - 1);
    else if (e.key === "Home") move(0);
    else if (e.key === "End") move(MAX_PRIORITY);
    else return;
    e.preventDefault();
  };

  return (
    <div className="flex flex-wrap items-center gap-x-6 gap-y-1">
      <span className="min-w-56 grow basis-56">
        <span className="text-lg font-bold">{label}</span> <span className="text-sm text-texto-secundario">{hint}</span>
        {note && <span className="block text-sm font-bold text-oscuro-cielo">{note}</span>}
      </span>
      <div
        ref={group}
        role="radiogroup"
        aria-label={`${label}: ${hint}`}
        onKeyDown={onKeyDown}
        className="flex items-center gap-0 sm:gap-1.5"
      >
        {LEVELS.map((level) => (
          <button
            key={level}
            type="button"
            role="radio"
            data-level={level}
            aria-checked={value === level}
            aria-label={t("components.ui.PriorityControl.outOf", { v0: level, v1: MAX_PRIORITY, v2: LEVEL_WORD()[level] })}
            tabIndex={value === level ? 0 : -1}
            disabled={disabled}
            onClick={() => onChange(level)}
            className="relative size-tactil-minimo font-bold outline-none disabled:cursor-not-allowed"
          >
            {level === 0 ? (
              <>
                <Plate
                  c={8}
                  fill={value === 0 ? "var(--color-superficie-panel-suave)" : "var(--color-superficie-panel)"}
                  stroke={value === 0 ? "var(--color-paleta-noche)" : "var(--color-superficie-borde)"}
                  strokeWidth={2.5}
                  ring="focus"
                />
                <span className="relative">0</span>
              </>
            ) : (
              <>
                <Plate c={10} fill="transparent" ring="focus" />
                <span className="relative block size-full">
                  <Seed filled={level <= value} />
                </span>
              </>
            )}
          </button>
        ))}
      </div>
      <span className="min-w-44 text-texto-secundario tabular-nums" aria-hidden="true">
        {value} · {LEVEL_WORD()[value]}
      </span>
    </div>
  );
}

export interface PriorityControlProps {
  value: Priorities;
  onChange: (value: Priorities) => void;
  disabled?: boolean;
}

export function PriorityControl({ value, onChange, disabled = false }: PriorityControlProps) {
  useTranslation();
  const invalid = allZero(value);
  return (
    <fieldset
      disabled={disabled}
      className="flex flex-col gap-4 disabled:opacity-60"
      aria-describedby={invalid ? "priorities-error" : undefined}
    >
      <legend className="mb-3 font-titulos text-lg font-titulo">{t("components.ui.PriorityControl.whatMattersMostToYou")}</legend>
      {CRITERIA().map(({ key, label, hint }) => (
        <SeedRow
          key={key}
          label={label}
          hint={hint}
          value={value[key]}
          disabled={disabled}
          onChange={(v) => onChange({ ...value, [key]: v })}
        />
      ))}
      {invalid && (
        <p id="priorities-error" role="alert" className="font-bold text-oscuro-rojo">
          <span aria-hidden="true">▲ </span>
          {t("components.ui.PriorityControl.increaseAtLeastOnePriorityToCompare")}
        </p>
      )}
    </fieldset>
  );
}
