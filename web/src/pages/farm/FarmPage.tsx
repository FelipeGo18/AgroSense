import type { ReactNode } from "react";
import { Link, useNavigate } from "react-router";
import { PATHS } from "@/app/paths";
import { FormScene } from "@/components/layout/FormScene";
import { MapScene, PANEL_WIDTH } from "@/components/layout/MapScene";
import { LotMap } from "@/components/map/LotMap";
import { Alert } from "@/components/ui/Alert";
import { Button, ButtonLink } from "@/components/ui/Button";
import { Plate } from "@/components/ui/Plate";
import { bbox, type LotPolygon } from "@/features/farm/geo";
import { byId, formatHa, useBoundary, useLots, useMunicipalities, type LotListItem } from "@/features/farm/lots";
import { cropNames, useCrops } from "@/features/farm/seasons";
import { LINK, RequireSession } from "@/pages/account/AccountShell";
import { Eyebrow } from "@/components/ui/Eyebrow";

/**
 * Mi finca (HU-169, HU-164). Figma: «D0 · Mis lotes» y «Lote sin dibujar / En Mi finca». Los lotes dibujados van en
 * el mapa y en la lista «En el mapa»; los que no, en «Sin dibujar», con «Dibujar en el mapa». Una sola zona: el mapa
 * muestra el municipio donde está el primer lote; un lote de otro municipio se ve en la lista y al abrirlo se centra allá.
 */
export function FarmPage() {
  return <RequireSession>{() => <Farm />}</RequireSession>;
}

/** «Papa y arveja en curso», con los nombres del catálogo. */
function cropsText(ids: string[], names: Map<string, string>) {
  if (ids.length === 0) return "Sin siembra en curso";
  const named = [...new Set(ids)].map((id) => names.get(id) ?? id);
  const list = named.length === 1 ? named[0] : `${named.slice(0, -1).join(", ")} y ${named.at(-1)!.toLowerCase()}`;
  return `${list} en curso`;
}

function Farm() {
  const navigate = useNavigate();
  const lots = useLots();
  const municipalities = useMunicipalities();
  const places = byId(municipalities.data);
  const all = lots.data ?? [];
  const drawn = all.filter((lot) => lot.geometry);
  const undrawn = all.filter((lot) => !lot.geometry);
  const zone = (drawn[0] ?? all[0])?.municipality_id;
  const boundary = useBoundary(zone);
  const towns = [...new Set(undrawn.map((lot) => places.get(lot.municipality_id)?.name ?? null))];
  const town = towns.length === 1 && towns[0] ? towns[0] : "su municipio";

  const header = (
    <header>
      <Eyebrow>Mi finca</Eyebrow>
      <h1 className="text-[clamp(1.75rem,2.6vw,2.25rem)]">Sus lotes</h1>
    </header>
  );

  // Sin lotes (o mientras cargan) no hay zona que mostrar en el mapa: el panel va sobre el paisaje.
  if (lots.isPending || lots.isError || all.length === 0) {
    return (
      <FormScene scene="region" mood="idle">
        <title>Mi finca · AgroSense</title>
        {header}
        {lots.isPending ? (
          <p role="status">Cargando sus lotes…</p>
        ) : lots.isError ? (
          <>
            <Alert>No pudimos cargar sus lotes. Intente de nuevo en un momento.</Alert>
            <Button variant="secondary" className="self-start" onClick={() => void lots.refetch()}>
              Volver a intentar
            </Button>
          </>
        ) : (
          <>
            <h2 className="text-[20px]">Todavía no tiene lotes</h2>
            <p>Agregue su primer lote: con él AgroSense le muestra estrategias de rotación y el diagnóstico de cada siembra.</p>
            <ButtonLink to={PATHS.addLot}>Agregar lote</ButtonLink>
          </>
        )}
      </FormScene>
    );
  }

  return (
    <MapScene
      map={
        <LotMap
          boundary={boundary.data?.geometry ?? null}
          focus={
            drawn.length
              ? envelope(drawn.filter((lot) => lot.municipality_id === zone).map((lot) => lot.geometry as unknown as LotPolygon))
              : null
          }
          lots={drawn.map((lot) => ({ id: lot.lot_id, name: lot.name, geometry: lot.geometry as unknown as LotPolygon }))}
          onLotClick={(id) => void navigate(PATHS.lot(id))}
          panelWidth={PANEL_WIDTH}
        />
      }
    >
      <title>Mi finca · AgroSense</title>
      {header}
      {drawn.length > 0 && (
        <section aria-labelledby="en-el-mapa" className="flex flex-col gap-2">
          <h2 id="en-el-mapa" className="text-[14px] font-bold tracking-wide text-texto-secundario uppercase">
            En el mapa
          </h2>
          <ul className="flex flex-col gap-2">
            {drawn.map((lot) => (
              <li key={lot.lot_id}>
                <DrawnRow lot={lot} place={places.get(lot.municipality_id)?.name} />
              </li>
            ))}
          </ul>
        </section>
      )}
      {undrawn.length > 0 && (
        <section aria-labelledby="sin-dibujar" className="flex flex-col gap-2">
          <h2 id="sin-dibujar" className="text-[14px] font-bold tracking-wide text-texto-secundario uppercase">
            Sin dibujar · No están en el mapa
          </h2>
          <ul className="flex flex-col gap-2">
            {undrawn.map((lot) => (
              <li key={lot.lot_id}>
                <UndrawnRow lot={lot} place={places.get(lot.municipality_id)?.name} />
              </li>
            ))}
          </ul>
          <p className="text-[14px] text-texto-secundario">Usan el suelo y la altitud de {town}, no los suyos.</p>
        </section>
      )}
      <ButtonLink to={PATHS.addLot} className="mt-1">
        Agregar lote
      </ButtonLink>
    </MapScene>
  );
}

/** La caja que abarca todos los lotes dibujados de la zona, como un polígono: el mapa la encuadra. */
function envelope(polygons: LotPolygon[]): LotPolygon | null {
  if (polygons.length === 0) return null;
  const boxes = polygons.map(bbox);
  const [w, s, e, n] = [
    Math.min(...boxes.map((b) => b[0])),
    Math.min(...boxes.map((b) => b[1])),
    Math.max(...boxes.map((b) => b[2])),
    Math.max(...boxes.map((b) => b[3])),
  ];
  return {
    type: "Polygon",
    coordinates: [
      [
        [w, s],
        [e, s],
        [e, n],
        [w, n],
        [w, s],
      ],
    ],
  };
}

/** El contorno del lote, en pequeño, para la miniatura de la fila. */
function Shape({ polygon }: { polygon: LotPolygon }) {
  const [w, s, e, n] = bbox(polygon);
  const size = Math.max(e - w, n - s) || 1;
  const points = polygon.coordinates[0].map(([x, y]) => `${4 + ((x - w) / size) * 32},${36 - ((y - s) / size) * 32}`).join(" ");
  return (
    <svg viewBox="0 0 40 40" className="relative size-9">
      <polygon points={points} fill="#E3C38F" stroke="#92490B" strokeWidth="2" strokeLinejoin="round" />
    </svg>
  );
}

function Thumb({ children }: { children: ReactNode }) {
  return (
    <span aria-hidden="true" className="relative grid size-[60px] shrink-0 place-items-center">
      <Plate c={8} fill="#F2F5F7" stroke="var(--color-superficie-borde)" strokeWidth={1.5} />
      {children}
    </span>
  );
}

function DrawnRow({ lot, place }: { lot: LotListItem; place: string | undefined }) {
  const names = cropNames(useCrops().data);
  return (
    <Link to={PATHS.lot(lot.lot_id)} className="relative flex min-h-11 items-center gap-4 px-3 py-3 hover:brightness-[0.98]">
      <Plate c={12} fill="var(--color-superficie-panel)" stroke="var(--color-superficie-borde)" strokeWidth={2} />
      <Thumb>
        <Shape polygon={lot.geometry as unknown as LotPolygon} />
      </Thumb>
      <span className="relative flex min-w-0 flex-1 flex-col">
        <span className="flex flex-wrap items-baseline justify-between gap-x-3">
          <span className="min-w-0 text-[18px] font-bold break-words">{lot.name}</span>
          <span className="text-[14px] text-texto-secundario">{formatHa(lot.area_ha)}</span>
        </span>
        <span className="text-[14px] text-texto-secundario">
          {cropsText(lot.current_crop_ids, names)}
          {place ? ` · ${place}` : ""}
        </span>
      </span>
    </Link>
  );
}

/** Un lote sin dibujar: borde punteado y su contorno sin trazar. Tocarlo abre el lote; «Dibujar en el mapa», el dibujo. */
function UndrawnRow({ lot, place }: { lot: LotListItem; place: string | undefined }) {
  const names = cropNames(useCrops().data);
  return (
    <div className="relative flex items-start gap-4 px-3 py-3">
      <Plate c={12} fill="var(--color-superficie-panel)" stroke="var(--color-oscuro-cielo)" strokeWidth={2} dash="6 5" />
      <Thumb>
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
      </Thumb>
      <span className="relative flex min-w-0 flex-1 flex-col">
        <Link to={PATHS.lot(lot.lot_id)} className="flex min-h-11 flex-col hover:underline">
          <span className="flex flex-wrap items-baseline justify-between gap-x-3">
            <span className="min-w-0 text-[18px] font-bold break-words">{lot.name}</span>
            <span className="text-[14px] text-texto-secundario">{formatHa(lot.area_ha)}</span>
          </span>
          <span className="text-[14px] text-texto-secundario">
            {cropsText(lot.current_crop_ids, names)}
            {place ? ` · ${place}` : ""}
          </span>
          <span className="text-[13px] text-texto-secundario">Área escrita a mano</span>
        </Link>
        <Link to={PATHS.drawLot(lot.lot_id)} className={`${LINK} min-h-11 self-start py-2 text-[15px]`}>
          Dibujar en el mapa
        </Link>
      </span>
    </div>
  );
}
