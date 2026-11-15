"""HU-211: publica solo la procedencia de la capa web, sin reconstruir ni cambiar los indicadores.

Ejecutar en Docker: python -m scripts.publish_gibs_source
Las reconstrucciones completas ya incluyen esta fuente desde pipeline.build.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

import polars as pl

from pipeline import schema


def publish(folder: Path = Path("data/published")) -> None:
    source = json.loads(Path("catalog/gibs.json").read_text(encoding="utf-8"))
    sources = pl.read_parquet(folder / "sources.parquet")
    updated = pl.concat(
        [sources.filter(pl.col("source_id") != source["source_id"]), pl.DataFrame([source], schema=sources.schema)],
    ).sort("source_id")
    schema.check("sources", updated)
    if sources.sort("source_id").equals(updated):
        return
    manifest_path = folder / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["tables"]["sources"]["rows"] = updated.height
    manifest["dataset_version"] += "-hu211"
    manifest["created_at"] = datetime.now(UTC).isoformat(timespec="seconds")
    updated.write_parquet(folder / "sources.parquet")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    publish()
