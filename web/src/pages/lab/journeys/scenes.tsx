// Fondos generados por design/paisaje/build_paisaje.py. Entran como texto para poder animar cada capa.
import a1 from "../../../../../design/paisaje/svg/a1-orbita.svg?raw";
import a1b from "../../../../../design/paisaje/svg/a1b-orbita-cerca.svg?raw";
import a2 from "../../../../../design/paisaje/svg/a2-atmosfera.svg?raw";
import a3 from "../../../../../design/paisaje/svg/a3-region.svg?raw";
import a3b from "../../../../../design/paisaje/svg/a3b-region-baja.svg?raw";
import a4 from "../../../../../design/paisaje/svg/a4-valle.svg?raw";
import a5 from "../../../../../design/paisaje/svg/a5-municipio.svg?raw";
import a5b from "../../../../../design/paisaje/svg/a5b-municipio-cerca.svg?raw";
import a6 from "../../../../../design/paisaje/svg/a6-vereda.svg?raw";
import a7 from "../../../../../design/paisaje/svg/a7-lote.svg?raw";
import b1 from "../../../../../design/paisaje/svg/b1-preparar.svg?raw";
import b2 from "../../../../../design/paisaje/svg/b2-sembrar.svg?raw";
import b3 from "../../../../../design/paisaje/svg/b3-crecer.svg?raw";
import b4 from "../../../../../design/paisaje/svg/b4-cosechar.svg?raw";
import b5 from "../../../../../design/paisaje/svg/b5-rotar.svg?raw";
import c1 from "../../../../../design/paisaje/svg/c1-paramo.svg?raw";
import c2 from "../../../../../design/paisaje/svg/c2-ladera.svg?raw";
import c4 from "../../../../../design/paisaje/svg/c4-pueblo.svg?raw";

export const SCENES = { a1, a1b, a2, a3, a3b, a4, a5, a5b, a6, a7, b1, b2, b3, b4, b5, c1, c2, c4 };
export type SceneId = keyof typeof SCENES;

/** Capas que se mueven más despacio cuanto más lejos están: eso da la profundidad. */
export const DEPTH: Record<string, number> = {
  estrellas: 0.1,
  sol: 0.15,
  atmosfera: 0.2,
  "nubes-lejanas": 0.25,
  lejano: 0.25,
  "niebla-lejana": 0.3,
  "niebla-alta": 0.3,
  "nubes-medias": 0.5,
  medio: 0.45,
  "niebla-media": 0.55,
  niebla: 0.55,
  cercano: 0.7,
  "nubes-cercanas": 1,
};

/**
 * Una escena a pantalla completa. El SVG es nuestro (generado en el repositorio), por eso se inserta tal cual.
 * Se recorta para cubrir la pantalla, como una imagen de fondo.
 */
export function Scene({ id, className = "" }: { id: SceneId; className?: string }) {
  const markup = SCENES[id].replace("<svg ", '<svg preserveAspectRatio="xMidYMid slice" style="width:100%;height:100%;display:block" ');
  return (
    <div data-scene={id} aria-hidden="true" className={`absolute inset-0 ${className}`} dangerouslySetInnerHTML={{ __html: markup }} />
  );
}
