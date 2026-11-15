"""Exporta a la web las piezas del lote vivo (HU-187): el cielo según la hora, la finca alrededor y un cubo por cultivo y
etapa, todo con el mismo dibujo del diseño (granja.py, cultivos.py y escena.py).

La web arma el diorama con estas piezas según las siembras en curso del lote: cada cultivo ocupa tantos cubos como su
parte del área y se dibuja en su etapa. No hay datos aquí: solo dibujo.

    python design/finca/exportar_web.py     # escribe web/src/components/farm/diorama/

Se parte en una base (cielo, finca y cubo libre) y un archivo por cultivo, para que la web descargue solo los cultivos
del lote.
"""

import json
import random
import sys
from pathlib import Path

DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(DIR))
sys.path.insert(0, str(DIR.parent / "kit"))

import ambiente as am  # noqa: E402
import cultivos as cv  # noqa: E402
import escena  # noqa: E402
import granja  # noqa: E402
from build_kit_svg import shade  # noqa: E402
from sheet import ridges  # noqa: E402

OUT = DIR.parent.parent / "web" / "src" / "components" / "farm" / "diorama"
W, H = 960, 600
K = W / am.W
LOT_K = 0.62 * W / 620  # como el lote vivo de finca.py en el celular (lot_k = 0.62): se ve la finca entera, con la casa
CX, CY = W * 0.55, H * 0.62

# Los cultivos del catálogo de AgroSense, con su dibujo del diseño (cultivos.py).
CROP_KEYS = {
    "papa": "papa",
    "maiz": "maiz",
    "arveja": "arveja",
    "haba": "haba",
    "zanahoria": "zanahoria",
    "cebolla_bulbo": "cebolla",
    "avena_vicia": "abono",
    "descanso": "descanso",
}
# Etapas del dibujo (0 siembra … 5 cosecha) que se usan para las cuatro etapas de FAO-56 de la ficha.
STAGES = (1, 2, 3, 4)

# Cubos del lote por tamaño: (i, j) a lo largo del surco y entre surcos.
LAYOUTS = {
    "2x2": [(0, 0), (1, 0), (0, 1), (1, 1)],
    "3x2": [(0, 0), (1, 0), (2, 0), (0, 1), (1, 1), (2, 1)],
}


def join(items):
    return "".join(items)


def sky(time):
    """Cielo, sol o luna, nubes, cerros y pasto: todo lo que no se mueve al recorrer la finca."""
    top, bottom = escena.sky_colors(time, set())
    rnd = random.Random(1)
    out = [f'<defs><linearGradient id="cielo-{time}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{top}"/>'
           f'<stop offset="1" stop-color="{bottom}"/></linearGradient></defs>',
           f'<rect width="{W}" height="{H}" fill="url(#cielo-{time})"/>']
    if time == "noche":
        out += am.stars(rnd, int(70 * K)) + am.moon(int(W * 0.8), int(64 * K))
    elif time == "atardecer":
        out += am.sun(int(W * 0.78), int(H * 0.2), 22 * K, "#F28C4A", "#F7C08A")
    else:
        out += am.sun(int(W * 0.82), int(62 * K), 18 * K)
    if time != "noche":
        for x, y, r, sd in ((0.18, 70, 18, 5), (0.48, 110, 14, 6)):
            out += am.cloud(W * x, y * K, r * K, "#FFFFFF" if time == "dia" else "#F2C9A8", sd)
    hy, rh = H * 0.1, 40 * K
    out.append(f'<g transform="translate(0 {hy:.0f})" opacity="{0.55 if time == "noche" else 0.9}">{join(ridges(W, 0, rh))}</g>')
    out.append(f'<rect y="{hy + rh:.0f}" width="{W}" height="{H}" fill="{shade(cv.GRASS, -0.15)}"/>')
    return join(out), hy + rh


def tint(time):
    if time == "noche":
        return f'<rect width="{W}" height="{H}" fill="#0B1A3A" fill-opacity="0.28"/>'
    if time == "atardecer":
        return f'<rect width="{W}" height="{H}" fill="#F28C4A" fill-opacity="0.1"/>'
    return ""


def main():
    data = {"width": W, "height": H, "lot": {"x": CX, "y": CY, "scale": LOT_K}, "sky": {}, "tint": {}, "layouts": {}, "free": ""}
    horizon = 0
    for time in ("dia", "atardecer", "noche"):
        data["sky"][time], horizon = sky(time)
        data["tint"][time] = tint(time)
    data["horizon"] = horizon
    with escena.low_beds():
        for name, cells in LAYOUTS.items():
            layout = [(i, j, "x", None, 0) for i, j in cells]
            farm = granja.Farm(layout)
            dog_x, dog_y = farm.dog_spot()
            data["layouts"][name] = {
                "cells": [{"i": i, "j": j, "x": round(x, 2), "y": round(y, 2)} for (i, j) in cells for x, y in [escena.cube_pos(layout, i, j)]],
                "ground": join(farm.ground()),
                "back": join(farm.back()),
                "front": join(farm.front() + escena.dog(dog_x, dog_y, 1.25)),
                "top": round(-cv.B * 1.2, 2),  # dónde va el rótulo sobre el centro del cubo
            }
        data["free"] = join(escena.cell(None, 0))
        crops = {c[0]: c for c in cv.CROPS}
        per_crop = {crop_id: {str(stage): join(escena.cell(crops[key], stage)) for stage in STAGES} for crop_id, key in CROP_KEYS.items()}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "crops").mkdir(exist_ok=True)
    write = lambda path, value: path.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")  # noqa: E731
    write(OUT / "base.json", data)
    for crop_id, stages in per_crop.items():
        write(OUT / "crops" / f"{crop_id}.json", stages)
    total = sum(f.stat().st_size for f in OUT.rglob("*.json"))
    print(f"{OUT}: {total // 1024} KB en {len(per_crop) + 1} archivos")


if __name__ == "__main__":
    main()
