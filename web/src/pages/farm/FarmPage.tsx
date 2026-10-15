import { Link } from "react-router";
import { PATHS } from "@/app/paths";
import { FormScene } from "@/components/layout/FormScene";
import { Alert } from "@/components/ui/Alert";
import { Button, ButtonLink } from "@/components/ui/Button";
import { Plate } from "@/components/ui/Plate";
import { byId, formatHa, useLots, useMunicipalities, type LotListItem } from "@/features/farm/lots";
import { RequireSession } from "@/pages/account/AccountShell";
import { Eyebrow } from "./common";

/**
 * Mi finca (HU-169, HU-164), entrega 1. Figma: «Lote sin dibujar / En Mi finca». Es el panel de «Sus lotes»; sin el
 * mapa (entrega 2), va sobre el paisaje y todos los lotes son «sin dibujar», en su lista.
 */
export function FarmPage() {
  return <RequireSession>{() => <Farm />}</RequireSession>;
}

function Farm() {
  const lots = useLots();
  const municipalities = useMunicipalities();
  const places = byId(municipalities.data);
  // Si todos los lotes son del mismo municipio, la nota lo nombra: «Usan el suelo y la altitud de Samacá».
  const towns = [...new Set((lots.data ?? []).map((lot) => places.get(lot.municipality_id)?.name ?? null))];
  const town = towns.length === 1 && towns[0] ? towns[0] : "su municipio";
  return (
    <FormScene scene="region" mood="idle">
      <title>Mi finca · AgroSense</title>
      <header>
        <Eyebrow>Mi finca</Eyebrow>
        <h1 className="text-[clamp(1.75rem,2.6vw,2.25rem)]">Sus lotes</h1>
      </header>
      {lots.isPending ? (
        <p role="status">Cargando sus lotes…</p>
      ) : lots.isError ? (
        <>
          <Alert>No pudimos cargar sus lotes. Intente de nuevo en un momento.</Alert>
          <Button variant="secondary" className="self-start" onClick={() => void lots.refetch()}>
            Volver a intentar
          </Button>
        </>
      ) : lots.data.length === 0 ? (
        <>
          <h2 className="text-[20px]">Todavía no tiene lotes</h2>
          <p>Agregue su primer lote: con él AgroSense le muestra estrategias de rotación y el diagnóstico de cada siembra.</p>
          <ButtonLink to={PATHS.addLot}>Agregar lote</ButtonLink>
        </>
      ) : (
        <>
          <section aria-labelledby="sin-dibujar" className="flex flex-col gap-2">
            <h2 id="sin-dibujar" className="text-[14px] font-bold tracking-wide text-texto-secundario uppercase">
              Sin dibujar · No están en el mapa
            </h2>
            <ul className="flex flex-col gap-2">
              {lots.data.map((lot) => (
                <li key={lot.lot_id}>
                  <LotRow lot={lot} place={places.get(lot.municipality_id)?.name} />
                </li>
              ))}
            </ul>
            <p className="text-[14px] text-texto-secundario">Usan el suelo y la altitud de {town}, no los suyos.</p>
          </section>
          <ButtonLink to={PATHS.addLot} className="mt-1">
            Agregar lote
          </ButtonLink>
        </>
      )}
    </FormScene>
  );
}

/** Un lote sin dibujar: borde punteado y su contorno sin trazar. Tocarlo abre el lote. */
function LotRow({ lot, place }: { lot: LotListItem; place: string | undefined }) {
  const crops = lot.current_crop_ids.length;
  return (
    <Link to={PATHS.lot(lot.lot_id)} className="relative flex min-h-11 items-center gap-4 px-3 py-3 hover:brightness-[0.98]">
      <Plate c={12} fill="var(--color-superficie-panel)" stroke="var(--color-oscuro-cielo)" strokeWidth={2} dash="6 5" />
      <span aria-hidden="true" className="relative grid size-[60px] shrink-0 place-items-center">
        <Plate c={8} fill="#F2F5F7" stroke="var(--color-superficie-borde)" strokeWidth={1.5} />
        <svg viewBox="0 0 40 40" className="relative size-9">
          <path
            d="M8 32 L13 9 L33 14 L28 34 Z"
            fill="none"
            stroke="var(--color-oscuro-cielo)"
            strokeWidth="2.5"
            strokeDasharray="5 4"
            strokeLinejoin="round"
          />
        </svg>
      </span>
      <span className="relative flex min-w-0 flex-1 flex-col">
        <span className="flex flex-wrap items-baseline justify-between gap-x-3">
          <span className="min-w-0 text-[18px] font-bold break-words">{lot.name}</span>
          <span className="text-[14px] text-texto-secundario">{formatHa(lot.area_ha)}</span>
        </span>
        <span className="text-[14px] text-texto-secundario">
          {crops === 0 ? "Sin siembra en curso" : crops === 1 ? "1 siembra en curso" : `${crops} siembras en curso`}
          {place ? ` · ${place}` : ""}
        </span>
        <span className="text-[13px] text-texto-secundario">Área escrita a mano</span>
      </span>
    </Link>
  );
}
