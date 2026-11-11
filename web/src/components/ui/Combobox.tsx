import { useId, useMemo, useState, type KeyboardEvent } from "react";
import { Plate, tone } from "./Plate";
import { Spinner } from "./Spinner";

export interface Option {
  id: string;
  label: string;
  /** Texto secundario, por ejemplo el departamento de un municipio. */
  hint?: string;
}

export interface ComboboxProps {
  label: string;
  options: Option[];
  value: Option | null;
  onChange: (option: Option) => void;
  placeholder?: string;
  loading?: boolean;
  disabled?: boolean;
  emptyText?: string;
  /** Error bajo el campo, enlazado al campo (`aria-invalid` y `aria-describedby`). */
  error?: string;
  /** Al salir del campo: para validar en el acto si quedó sin elegir. */
  onBlur?: () => void;
}

/** Compara sin tildes ni mayúsculas: «bogota» encuentra «Bogotá». */
export function normalize(text: string) {
  return text
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLowerCase()
    .trim();
}

/**
 * Selector con autocompletado (patrón combobox de WAI-ARIA 1.2).
 * Solo deja elegir opciones del catálogo (W1): lo escrito a mano no es un valor.
 */
export function Combobox({
  label,
  options,
  value,
  onChange,
  placeholder,
  loading = false,
  disabled = false,
  emptyText = "Sin resultados. Revise cómo lo escribió.",
  error,
  onBlur,
}: ComboboxProps) {
  const id = useId();
  const listId = `${id}-list`;
  const [query, setQuery] = useState(value?.label ?? "");
  // Si el valor llega o cambia desde afuera (por ejemplo, de la dirección cuando el catálogo termina de cargar), el
  // texto lo muestra. Se ajusta durante el render, sin un efecto.
  const [shownId, setShownId] = useState(value?.id);
  if (value?.id !== shownId) {
    setShownId(value?.id);
    setQuery(value?.label ?? "");
  }
  const [open, setOpen] = useState(false);
  const [focused, setFocused] = useState(false);
  const [active, setActive] = useState(0);

  const results = useMemo(() => {
    const q = normalize(query);
    if (!q || q === normalize(value?.label ?? "")) return options;
    return options.filter((o) => normalize(o.label).includes(q));
  }, [options, query, value]);

  const select = (option: Option) => {
    onChange(option);
    setQuery(option.label);
    setOpen(false);
  };

  const onKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      if (!open) {
        setOpen(true);
        return;
      }
      const step = e.key === "ArrowDown" ? 1 : -1;
      setActive((i) => (results.length ? (i + step + results.length) % results.length : 0));
    } else if (e.key === "Enter" && open && results[active]) {
      e.preventDefault();
      select(results[active]);
    } else if (e.key === "Escape") {
      setOpen(false);
      setQuery(value?.label ?? "");
    }
  };

  const activeId = open && results[active] ? `${id}-opt-${results[active].id}` : undefined;
  const message = loading ? "Cargando opciones…" : results.length === 0 ? emptyText : null;

  return (
    <div className="relative flex flex-col gap-1.5">
      <label htmlFor={`${id}-input`} className="font-bold">
        {label}
      </label>
      <div className="relative h-14">
        <Plate
          fill={disabled ? "var(--color-superficie-panel-suave)" : "var(--color-superficie-panel)"}
          stroke={error ? "var(--color-oscuro-rojo)" : focused ? "var(--color-accion-foco)" : "var(--color-superficie-borde)"}
        />
        <input
          id={`${id}-input`}
          role="combobox"
          aria-expanded={open}
          aria-controls={listId}
          aria-autocomplete="list"
          aria-activedescendant={activeId}
          aria-busy={loading || undefined}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? `${id}-error` : undefined}
          autoComplete="off"
          disabled={disabled}
          placeholder={placeholder}
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setActive(0);
            setOpen(true);
          }}
          onFocus={() => {
            setFocused(true);
            setOpen(true);
          }}
          onBlur={() => {
            setFocused(false);
            setOpen(false);
            setQuery(value?.label ?? "");
            onBlur?.();
          }}
          onKeyDown={onKeyDown}
          // El foco lo muestra el contorno de la placa, que pasa a color noche.
          className="relative size-full bg-transparent px-5 pr-12 text-texto-principal outline-none placeholder:text-texto-secundario disabled:cursor-not-allowed"
        />
        {loading && <Spinner className="absolute top-1/2 right-4 -translate-y-1/2 text-texto-secundario" />}
        {/* La lista cuelga de la caja del campo: así queda pegada a él aunque haya un error debajo. */}
        {open && !disabled && (
          <div className="absolute top-full z-10 mt-2 w-full px-1.5 pt-1.5 pb-3">
            <Plate
              c={12}
              fill="var(--color-superficie-panel)"
              stroke="var(--color-superficie-borde)"
              strokeWidth={2}
              depth={6}
              bottom={6}
              side="var(--color-superficie-borde)"
            />
            {/* data-lenis-prevent: la rueda sobre la lista mueve la lista, no la página con scroll suave. */}
            <ul id={listId} role="listbox" aria-label={label} data-lenis-prevent className="relative max-h-80 overflow-auto">
              {message ? (
                <li
                  role="option"
                  aria-disabled="true"
                  aria-selected="false"
                  className="relative flex min-h-[52px] items-center px-4 text-texto-secundario"
                >
                  {message}
                </li>
              ) : (
                results.map((option, i) => (
                  <li
                    key={option.id}
                    id={`${id}-opt-${option.id}`}
                    role="option"
                    aria-selected={value?.id === option.id}
                    onMouseDown={(e) => e.preventDefault()}
                    onClick={() => select(option)}
                    onMouseEnter={() => setActive(i)}
                    className={`relative flex min-h-[52px] cursor-pointer items-center justify-between gap-4 pr-4 pl-11 ${i === active ? "font-bold" : ""}`}
                  >
                    {i === active && (
                      <>
                        <Plate c={8} fill={tone("var(--color-paleta-brote)", 0.72)} />
                        {/* La semilla marca la opción activa. */}
                        <svg aria-hidden="true" viewBox="0 0 16 16" className="absolute left-4 size-4">
                          <polygon points="8,0 16,8 8,16 0,8" fill="var(--color-oscuro-brote)" />
                        </svg>
                      </>
                    )}
                    <span className="relative">{option.label}</span>
                    {option.hint && <span className="relative text-sm font-normal text-texto-secundario">{option.hint}</span>}
                  </li>
                ))
              )}
            </ul>
          </div>
        )}
      </div>
      {error && (
        <p id={`${id}-error`} role="alert" className="text-[15px] leading-snug font-bold text-oscuro-rojo">
          {error}
        </p>
      )}
    </div>
  );
}
