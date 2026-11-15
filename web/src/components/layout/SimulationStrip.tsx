import { ExampleLabel } from "@/components/ui/Labels";

/**
 * Franja fija al pie mientras la web responde con ejemplos (HU-013, R5): todo lo que llegue de la simulación se ve
 * rotulado como ejemplo, en cualquier pantalla. No se mueve. El espacio de abajo evita que tape el final de la página.
 */
export function SimulationStrip() {
  return (
    <>
      <div aria-hidden="true" className="h-16" />
      <div
        role="status"
        className="fixed inset-x-0 bottom-0 z-50 flex flex-wrap items-center justify-center gap-x-3 gap-y-1 border-t-2 border-oscuro-calabaza bg-superficie-panel px-3 py-1.5"
      >
        <ExampleLabel>respuestas simuladas</ExampleLabel>
        {/* En el celular basta el rótulo: la franja no puede comerse la pantalla. */}
        <span className="hidden min-w-0 text-sm text-texto-principal sm:inline">Modo simulación: nada de esto viene del motor.</span>
      </div>
    </>
  );
}
