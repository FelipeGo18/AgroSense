import type { ReactNode } from "react";
import { Link, useLocation, useParams } from "react-router";
import { ApiError } from "@/api/client";
import { PATHS } from "@/app/paths";
import { FormScene } from "@/components/layout/FormScene";
import { Alert } from "@/components/ui/Alert";
import { ButtonLink } from "@/components/ui/Button";
import { byId, formatHa, useLot, useMunicipalities, type LotDetail } from "@/features/farm/lots";
import { LINK, RequireSession } from "@/pages/account/AccountShell";
import { Eyebrow, WithoutDrawing, irrigationText, placeName } from "./common";

const DATE = new Intl.DateTimeFormat("es-CO", { day: "numeric", month: "long", year: "numeric", timeZone: "UTC" });

/**
 * El lote (HU-164, HU-169), entrega 1: lo que se sabe de él, sus siembras en curso y su suelo, en una tarjeta que cabe
 * sin scroll en escritorio. Editar y borrar van en «Editar lote» (Figma: «D1 · Editar lote»). Sin dibujo no hay mapa;
 * el lote vivo (HU-187) y «Ver estrategias de rotación» (HU-214) llegan después.
 */
export function LotPage() {
  return <RequireSession>{() => <LotView />}</RequireSession>;
}

function LotView() {
  const { lotId = "" } = useParams();
  const notice = (useLocation().state as { notice?: string } | null)?.notice;
  const lot = useLot(lotId);
  const municipalities = useMunicipalities();
  const municipality = lot.data ? byId(municipalities.data).get(lot.data.municipality_id) : undefined;
  const back = (
    <Link to={PATHS.farm} className={`${LINK} min-h-11 self-start py-2`}>
      ‹ Mi finca
    </Link>
  );

  if (lot.isPending || lot.isError) {
    return (
      <FormScene scene="region" mood={lot.isError ? "no_data" : "idle"}>
        <title>Lote · Mi finca · AgroSense</title>
        {back}
        {lot.isPending ? (
          <p role="status">Cargando el lote…</p>
        ) : (
          <Alert>
            {lot.error instanceof ApiError && lot.error.status === 404
              ? "Ese lote no existe o no es suyo."
              : "No pudimos cargar el lote. Intente de nuevo."}
          </Alert>
        )}
      </FormScene>
    );
  }
  return (
    <FormScene scene="region" mood="idle" wide>
      <title>{`${lot.data.name} · Mi finca · AgroSense`}</title>
      {back}
      <header className="flex flex-wrap items-end justify-between gap-x-6 gap-y-3">
        <div className="min-w-0">
          <Eyebrow>{placeName(municipality, lot.data.municipality_id)}</Eyebrow>
          <h1 className="text-[clamp(1.75rem,2.6vw,2.25rem)] break-words">{lot.data.name}</h1>
        </div>
        <ButtonLink to={PATHS.editLot(lot.data.lot_id)} variant="secondary" className="w-full sm:w-[200px]">
          Editar lote
        </ButtonLink>
      </header>
      {notice && (
        <p role="status" className="border-l-8 border-oscuro-oliva bg-paleta-niebla px-4 py-2 font-bold">
          {notice}
        </p>
      )}
      <div className="grid grid-cols-1 gap-x-8 gap-y-5 lg:grid-cols-2">
        <LotFacts lot={lot.data} town={municipality?.name ?? "su municipio"} />
        <div className="flex flex-col gap-5">
          <Seasons lot={lot.data} />
          <Soil town={municipality?.name ?? "su municipio"} />
        </div>
      </div>
    </FormScene>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="flex flex-col gap-2">
      <h2 className="text-[20px]">{title}</h2>
      {children}
    </section>
  );
}

function LotFacts({ lot, town }: { lot: LotDetail; town: string }) {
  return (
    <Section title="Su lote">
      <dl className="grid grid-cols-[auto_1fr] gap-x-5 gap-y-1">
        <dt className="font-bold">Área</dt>
        <dd>{formatHa(lot.area_ha)} · escrita a mano</dd>
        <dt className="font-bold">Riego</dt>
        <dd>{irrigationText(lot.irrigated)}</dd>
      </dl>
      <WithoutDrawing place={town} />
    </Section>
  );
}

/** Las siembras en curso (GET /lots/{id}, `current_seasons`). Registrar una siembra llega con la entrega 3. */
function Seasons({ lot }: { lot: LotDetail }) {
  return (
    <Section title="Siembras en curso">
      {lot.current_seasons.length === 0 ? (
        <p className="text-texto-secundario">Sin siembra en curso.</p>
      ) : (
        <ul className="flex flex-col gap-1">
          {lot.current_seasons.map((season) => (
            <li key={season.season_id} className="flex flex-col">
              <span className="font-bold">{season.crop_id}</span>
              <span className="text-[14px] text-texto-secundario">
                {formatHa(season.area_ha)} · sembrado el {DATE.format(new Date(season.sowing_date))} · día {season.days_since_sowing}
              </span>
            </li>
          ))}
        </ul>
      )}
    </Section>
  );
}

/** El suelo (HU-185): sin el suelo publicado no se inventa nada (R1, R10). */
function Soil({ town }: { town: string }) {
  return (
    <Section title="Suelo">
      <p className="font-bold">Sin datos del suelo todavía.</p>
      <p className="text-[14px] text-texto-secundario">
        Será el estimado de {town} (mapa global de 250 m), con su rango. Para conocer el de su lote, haga un análisis de suelo.
      </p>
    </Section>
  );
}
