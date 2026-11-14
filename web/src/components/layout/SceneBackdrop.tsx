import municipio from "../../../../design/paisaje/svg/a5-municipio.svg?url";
import region from "../../../../design/paisaje/svg/a3-region.svg?url";
import vereda from "../../../../design/paisaje/svg/a6-vereda.svg?url";
import { SceneAmbient } from "@/components/layout/SceneAmbient";

const SCENES = { municipio, region, vereda };

export interface SceneBackdropProps {
  /** El paisaje: el municipio (la consulta y sus resultados), la región o la vereda (un cultivo que no se da en la zona). */
  scene: keyof typeof SCENES;
  /**
   * `full`: cubre toda la pantalla, detrás de la página (las pantallas para elegir, como en el diseño).
   * `band`: una franja arriba, detrás del encabezado (las pantallas de resultado); abajo sigue el fondo claro.
   */
  variant: "full" | "band";
}

/**
 * Fondo de paisaje de las pantallas de la consulta (`design/pantallas/estrategias.py`, `diagnostico.py`, `ciclo.py`:
 * `scene(...)`). Lleva un velo oscuro, como el diseño (10 % en las pantallas para elegir, 12 % en las franjas), para
 * que el contenido mande. Es decoración: va detrás de todo, no recibe el puntero y el lector de pantalla no lo anuncia.
 * El paisaje no se mueve; lo que se mueve es el ambiente (`SceneAmbient`), que en modo ligero se queda quieto.
 *
 * La página que lo usa pone `relative isolate` en su caja: así el paisaje queda sobre su fondo y debajo del contenido.
 */
export function SceneBackdrop({ scene, variant }: SceneBackdropProps) {
  if (variant === "full") {
    return (
      <>
        <img src={SCENES[scene]} alt="" aria-hidden="true" className="fixed inset-0 -z-10 size-full object-cover" />
        <div aria-hidden="true" className="pointer-events-none fixed inset-0 -z-10 bg-paleta-noche/10" />
        <SceneAmbient />
      </>
    );
  }
  return (
    <div aria-hidden="true" className="pointer-events-none absolute inset-x-0 top-0 -z-10 h-[560px] overflow-hidden md:h-[440px]">
      <img src={SCENES[scene]} alt="" className="absolute inset-0 size-full object-cover" />
      <SceneAmbient contained />
      <div className="absolute inset-0 bg-paleta-noche/[0.12]" />
    </div>
  );
}
