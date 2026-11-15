import { useSearchParams } from "react-router";
import { Combobox } from "@/components/ui/Combobox";
import { SelectField } from "@/components/ui/SelectField";
import { useMunicipalities } from "@/features/farm/lots";
import { useCrops } from "@/features/farm/seasons";

export function useChangesContext() {
  const [params, setParams] = useSearchParams();
  const municipalities = useMunicipalities();
  const crops = useCrops();
  const municipalityId = params.get("municipio") ?? "";
  const cropId = params.get("cultivo") ?? "";
  const irrigation = params.get("riego") ?? "nose";
  const municipality = municipalities.data?.find((item) => item.municipality_id === municipalityId);
  const crop = crops.data?.find((item) => item.crop_id === cropId && item.kind === "crop");
  const ready = municipalities.isSuccess && crops.isSuccess;
  const irrigationValid = ["si", "no", "nose"].includes(irrigation);
  return {
    municipalityId,
    cropId,
    irrigation,
    municipality,
    crop,
    municipalities,
    crops,
    ready,
    error: municipalities.error ?? crops.error,
    irrigationValid,
    valid: Boolean(ready && municipality && crop && irrigationValid),
    change(name: string, value: string) {
      const next = new URLSearchParams(params);
      if (value) next.set(name, value);
      else next.delete(name);
      setParams(next, { preventScrollReset: true });
    },
  };
}

export function ChangesContext({ context }: { context: ReturnType<typeof useChangesContext> }) {
  const { municipality, municipalities, crops, ready, error, change } = context;
  if (error) return <p role="alert">No pudimos cargar los municipios y los cultivos: {error.message}</p>;
  return (
    <div className="flex min-w-0 flex-col gap-5" aria-label="Contexto de la comparación histórica">
      <Combobox
        label="Municipio"
        placeholder="Busque su municipio"
        loading={municipalities.isPending}
        options={(municipalities.data ?? []).map((item) => ({ id: item.municipality_id, label: item.name, hint: item.department }))}
        value={municipality ? { id: municipality.municipality_id, label: municipality.name, hint: municipality.department } : null}
        onChange={(option) => change("municipio", option.id)}
        error={ready && context.municipalityId && !municipality ? "Elija un municipio del catálogo." : undefined}
      />
      <SelectField
        label="Cultivo"
        value={context.cropId}
        disabled={crops.isPending}
        onChange={(event) => change("cultivo", event.target.value)}
        options={[
          { value: "", label: "Elija un cultivo" },
          ...(crops.data ?? []).filter((item) => item.kind === "crop").map((item) => ({ value: item.crop_id, label: item.name_es })),
        ]}
        error={ready && context.cropId && !context.crop ? "Elija un cultivo del catálogo." : undefined}
      />
      <SelectField
        label="¿Tiene riego?"
        value={context.irrigationValid ? context.irrigation : ""}
        onChange={(event) => change("riego", event.target.value)}
        options={[
          { value: "", label: "Elija una opción" },
          { value: "si", label: "Sí" },
          { value: "no", label: "No" },
          { value: "nose", label: "No sé" },
        ]}
        error={context.irrigationValid ? undefined : "Elija una opción de riego."}
        hint="Si no sabe, se compara sin riego y se indica en las limitaciones."
      />
      {context.valid && (
        <p className="font-bold">
          {context.crop?.name_es} · {municipality?.name}, {municipality?.department}
        </p>
      )}
      <p className="text-sm text-texto-secundario">
        Los datos describen el municipio, también cuando llega desde un lote. No son mediciones de su terreno.
      </p>
    </div>
  );
}
