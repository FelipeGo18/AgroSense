/** Indicador de carga: hexágono facetado que gira. Decorativo; el texto que lo acompaña anuncia el estado. */
export function Spinner({ className = "" }: { className?: string }) {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 22 22"
      className={`inline-block size-[22px] shrink-0 animate-spin [animation-duration:1.4s] motion-reduce:animate-none ${className}`}
    >
      <polygon points="11,1 19.66,6 19.66,16 11,21 2.34,16 2.34,6" fill="none" stroke="currentColor" strokeWidth="2.5" />
      <polygon points="11,1 19.66,6 19.66,16 11,21 11,11" fill="currentColor" />
    </svg>
  );
}
