/** Marca: la semilla y el nombre. El color del nombre sale del texto que la contiene. */
export function Logo({ className = "" }: { className?: string }) {
  return (
    <span className={`inline-flex items-center gap-2 font-titulos text-[28px] leading-none font-titulo ${className}`}>
      <svg aria-hidden="true" viewBox="0 0 30 40" className="h-10 w-[30px] shrink-0">
        <path d="M16 9c9 .6 13 9 12 17-.8 8-7 12-13 12S3 34 2 26C1 17 7 9 16 9z" fill="#C8873A" stroke="#1D1D1B" strokeWidth="2.5" />
        <path d="M15 9c-5 0-7-4-6-7 4 .6 7 3 6 7zm2 0c4 .6 8-2 8-6-4-.6-7 2-8 6z" fill="#5FA052" stroke="#1D1D1B" strokeWidth="2" />
      </svg>
      AgroSense
    </span>
  );
}
