import { useState } from "react";
import { ButtonLink } from "@/components/ui/Button";
import { SelectField } from "@/components/ui/SelectField";
import { changesLink } from "@/features/changes/changes";
import { useCrops } from "@/features/farm/seasons";

/** Solo una siembra en curso permite preseleccionar sin adivinar (decisión de Haider, 15 nov). */
export function LotChangesLink({
  municipalityId,
  irrigated,
  currentSeasons = [],
}: {
  municipalityId: string;
  irrigated: boolean | null;
  currentSeasons?: readonly { crop_id: string }[];
}) {
  const crops = useCrops();
  const [choice, setChoice] = useState<string | null>(null);
  const cropId = choice ?? (currentSeasons.length === 1 ? currentSeasons[0].crop_id : "");
  const selected = crops.data?.find((crop) => crop.crop_id === cropId && crop.kind === "crop");
  return (
    <section aria-label="Qué cambió en su zona" className="flex min-w-0 flex-col gap-3">
      <h2 className="text-[20px]">Qué cambió en su zona</h2>
      <p>Compare dos periodos de la historia del municipio para un cultivo. No es un pronóstico ni una medición de este lote.</p>
      {crops.isError ? (
        <p role="alert">No pudimos cargar los cultivos: {crops.error.message}</p>
      ) : (
        <>
          <SelectField
            label="Cultivo para comparar la historia de la zona"
            value={cropId}
            disabled={crops.isPending}
            onChange={(event) => setChoice(event.target.value)}
            options={[
              { value: "", label: crops.isPending ? "Cargando cultivos…" : "Elija un cultivo" },
              ...(crops.data ?? []).filter((crop) => crop.kind === "crop").map((crop) => ({ value: crop.crop_id, label: crop.name_es })),
            ]}
          />
          {selected && (
            <ButtonLink
              to={changesLink(municipalityId, selected.crop_id, irrigated)}
              variant="secondary"
              className="w-full sm:w-auto sm:self-start"
            >
              Ver qué cambió en su zona
            </ButtonLink>
          )}
        </>
      )}
    </section>
  );
}
