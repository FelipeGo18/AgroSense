import { useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { ApiError } from "@/api/client";
import { PATHS } from "@/app/paths";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { TextField } from "@/components/ui/TextField";
import { formatHa, useLot, type LotDetail } from "@/features/farm/lots";
import { cropNames, formatDate, todayIso, useCrops, useSeasons, useUpdateSeason, type Season } from "@/features/farm/seasons";
import { AccountShell, LINK } from "@/pages/account/AccountShell";
import { Eyebrow } from "@/components/ui/Eyebrow";
import { Shell } from "./SeasonFormPage";
import { LotBar, type Part } from "./SeasonParts";

/**
 * Registrar la cosecha (HU-165). Figma: «Registrar la cosecha». La fecha va entre la siembra y hoy; al guardar, ese
 * terreno queda libre. «Guardar cosecha y registrar la siembra» lleva a la siembra con esta cosecha ya marcada.
 */
export function HarvestPage() {
  const { lotId = "", seasonId = "" } = useParams();
  const lot = useLot(lotId);
  const seasons = useSeasons(lotId);
  const crops = useCrops();
  const season = seasons.data?.find((s) => s.season_id === seasonId);
  const missing = seasons.isSuccess && (!season || !!season.harvest_date);
  return (
    <AccountShell>
      {() =>
        lot.isError || seasons.isError || crops.isError || missing ? (
          <Shell lotId={lotId} lotName={lot.data?.name}>
            <Alert>
              {lot.error instanceof ApiError && lot.error.status === 404
                ? "Ese lote no existe o no es suyo."
                : missing
                  ? season
                    ? "Esa siembra ya tiene la cosecha registrada."
                    : "Esa siembra no existe o no es suya."
                  : "No pudimos cargar los datos. Intente de nuevo en un momento."}
            </Alert>
          </Shell>
        ) : lot.isPending || seasons.isPending || crops.isPending || !season ? (
          <Shell lotId={lotId} lotName={lot.data?.name}>
            <p role="status">Cargando…</p>
          </Shell>
        ) : (
          <HarvestForm lot={lot.data} season={season} names={cropNames(crops.data)} />
        )
      }
    </AccountShell>
  );
}

function HarvestForm({ lot, season, names }: { lot: LotDetail; season: Season; names: Map<string, string> }) {
  const navigate = useNavigate();
  const update = useUpdateSeason(lot.lot_id, season.season_id);
  const [date, setDate] = useState(todayIso() < season.sowing_date ? season.sowing_date : todayIso());
  const [tried, setTried] = useState(false);
  const name = names.get(season.crop_id) ?? season.crop_id;

  const error = !date
    ? "Escriba la fecha de cosecha."
    : date < season.sowing_date
      ? "La cosecha no puede ser antes de la siembra."
      : date > todayIso()
        ? "La fecha de cosecha no puede ser posterior a hoy."
        : undefined;
  const save = (thenSow: boolean) => (event?: FormEvent) => {
    event?.preventDefault();
    setTried(true);
    if (error) return;
    update.mutate(
      { harvest_date: date },
      {
        onSuccess: () =>
          void navigate(thenSow ? PATHS.sow(lot.lot_id, season.season_id) : PATHS.lot(lot.lot_id), {
            state: { notice: `Cosecha de ${name.toLowerCase()} registrada. Ese terreno quedó libre.` },
          }),
      },
    );
  };

  // Después de cosechar, el terreno de esta siembra queda libre; las demás siguen como están.
  const others = lot.current_seasons.filter((s) => s.season_id !== season.season_id);
  const parts: Part[] = others.map((s) => ({ key: s.season_id, label: names.get(s.crop_id) ?? s.crop_id, ha: s.area_ha }));
  const free = lot.area_ha - parts.reduce((total, part) => total + part.ha, 0);
  if (free > 0.0001) parts.push({ key: "libre", label: "Libre", ha: free, free: true });

  return (
    <Shell
      lotId={lot.lot_id}
      lotName={lot.name}
      aside={
        <Card bodyClassName="gap-3">
          <Eyebrow>Cómo queda el lote</Eyebrow>
          <h2 className="text-[22px]">Después de cosechar</h2>
          <LotBar parts={parts} total={lot.area_ha} />
          <p className="text-[15px] text-texto-secundario">
            {formatHa(season.area_ha)} de {name.toLowerCase()} quedan libres para la siembra que sigue.
          </p>
        </Card>
      }
    >
      <title>{`Registrar cosecha · ${lot.name} · AgroSense`}</title>
      <header>
        <Eyebrow>Mi finca</Eyebrow>
        <h1 className="text-[clamp(1.75rem,2.6vw,2.25rem)]">Registrar la cosecha</h1>
        <p className="text-texto-secundario">
          {name} · {formatHa(season.area_ha)} · sembrada el {formatDate(season.sowing_date)}
        </p>
      </header>
      {update.isError && <Alert>{update.error instanceof ApiError ? update.error.message : "No se pudo guardar. Intente de nuevo."}</Alert>}
      <form onSubmit={save(false)} noValidate className="flex flex-col gap-5">
        <TextField
          label="¿Cuándo cosechó?"
          name="harvest_date"
          type="date"
          min={season.sowing_date}
          max={todayIso()}
          value={date}
          onChange={(event) => setDate(event.target.value)}
          hint={
            season.harvest_estimate
              ? `La cosecha estimada era el ${formatDate(season.harvest_estimate)} (por la duración de las etapas del cultivo).`
              : undefined
          }
          error={tried ? error : undefined}
        />
        <Button type="button" loading={update.isPending} loadingText="Guardando…" onClick={() => save(true)()}>
          Guardar cosecha y registrar la siembra
        </Button>
        <Button type="submit" variant="secondary" disabled={update.isPending}>
          Guardar solo la cosecha
        </Button>
        <Link to={PATHS.lot(lot.lot_id)} className={`${LINK} min-h-11 self-end py-2`}>
          Cancelar
        </Link>
      </form>
    </Shell>
  );
}
