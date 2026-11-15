import { useState } from "react";
import { ButtonLink } from "@/components/ui/Button";
import { SelectField } from "@/components/ui/SelectField";
import { changesLink } from "@/features/changes/changes";
import { useCrops } from "@/features/farm/seasons";

/** Un lote puede tener varios cultivos: la persona elige cuál comparar. */
export function LotChangesLink({ municipalityId, irrigated }: { municipalityId: string; irrigated: boolean | null }) {
  const crops = useCrops();
  const [cropId, setCropId] = useState("");
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
            onChange={(event) => setCropId(event.target.value)}
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
