import { ExampleLabel } from "./components/Labels";
import { Mascot } from "./components/Mascot";
import { Plate } from "./components/Plate";

const PAGES = [
  { href: "/kit", title: "Kit de componentes", text: "Botón, selector, semáforo, prioridad, tarjetas de señal, rótulos y la mascota." },
  { href: "/recorrido/1", title: "Recorrido 1 · Del satélite al lote", text: "La cámara baja de la órbita al lote en diez escenas." },
  {
    href: "/recorrido/2",
    title: "Recorrido 2 · El año del cultivo",
    text: "La cámara se queda en el lote y el scroll avanza en el tiempo.",
  },
  { href: "/recorrido/3", title: "Recorrido 3 · Travesía por la cordillera", text: "Del páramo a la finca, de lado." },
];

/** Índice del prototipo: desde aquí se llega al kit y a los recorridos de prueba. */
export function Home() {
  return (
    <main className="mx-auto flex max-w-4xl flex-col gap-6 px-4 py-10 sm:px-8">
      <header className="flex flex-wrap items-center gap-6">
        <Mascot mood="guide" size={170} decorative className="mascot-float" />
        <div className="flex min-w-64 flex-1 flex-col gap-3">
          <h1 className="text-3xl">AgroSense · prototipo</h1>
          <p>Páginas de prueba de la fase 0. Todo lo que se ve usa datos de muestra.</p>
          <ExampleLabel />
        </div>
      </header>
      <ul className="flex flex-col gap-5">
        {PAGES.map((page) => (
          <li key={page.href}>
            <a href={page.href} className="relative block px-7 pt-5 pb-8 outline-none">
              <Plate c={16} fill="var(--color-superficie-panel)" depth={8} bottom={8} side="var(--color-superficie-borde)" ring="focus" />
              <span className="relative block font-titulos text-xl font-titulo">{page.title}</span>
              <span className="relative block text-texto-secundario">{page.text}</span>
              <span className="relative block text-sm font-bold underline">{page.href}</span>
            </a>
          </li>
        ))}
      </ul>
    </main>
  );
}
