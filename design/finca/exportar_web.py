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
LOT_K = 0.5 * W / 620  # la finca entera cabe en la vista, de la huerta a la cerca del frente
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
    """El fondo: el pasto llena toda la vista, sin franja de cielo ni cerros (bajo la barra de la web quedan como un
    parche). El momento del día lo dan el tono de `tint` y, de noche, los faroles y las luciérnagas de la web."""
    del time
    return f'<rect width="{W}" height="{H}" fill="{shade(cv.GRASS, -0.15)}"/>', 0


def farm_anchors(farm):
    """Dónde queda cada cosa de la finca, en las coordenadas del lote, para las animaciones de la web: el humo sale de
    la chimenea, los faroles y la ventana se encienden de noche, el gato está en el porche, el colibrí en la huerta, el
    pájaro en la cerca y el perro corre alrededor del lote. Mismas cuentas que granja.py."""
    pt = lambda a, b, z=0.0: [round(v, 1) for v in farm.pt(a, b, z)]  # noqa: E731
    corners = lambda zone: [pt(zone[0], zone[2]), pt(zone[1], zone[2]), pt(zone[1], zone[3]), pt(zone[0], zone[3])]  # noqa: E731
    a0h, a1h = farm.a0 - 2.35, farm.a0 - 1.25  # la casa
    b0h, b1h = farm.GATE[0] - 0.5, farm.GATE[1] + 0.2
    bm, height, steps, dz = (b0h + b1h) / 2, 50, 4, 11
    ca, cb = a0h + 0.25, bm - 0.36
    a0, a1, b0, b1 = farm.a0, farm.a1, farm.b0, farm.b1
    out = 0.55  # el camino del perro, por fuera de la cerca
    return {
        "chimney": pt(ca + 0.12, cb + 0.12, height + steps * dz + 30),
        "window": pt(a1h + 0.002, b0h + 0.24, 31),
        "porch": pt(a1h + 0.2, bm + 0.18, 6),
        "garden": pt((a0 - 2.3 + a0 - 1.4) / 2, farm.GATE[1] + 0.97, 14),
        "dog": [round(v, 1) for v in farm.dog_spot()],
        "fence": pt(a1, (b0 + b1) / 2, 24),
        "lanterns": [pt(a, b, 42) for a, b in ((a0, b0), (a1, b0), (a1, b1), (a0, b1))],
        "path": [pt(a, b) for a, b in ((a0 - out, b1 + out), (a1 + out, b1 + out), (a1 + out, b0 - out), (a0 - out, b0 - out))],
        "hens": [pt(a0 - 0.55, farm.GATE[1] + 0.6), pt(a0 - 0.35, farm.GATE[1] + 0.95), pt(a0 - 0.8, farm.GATE[1] + 1.15)],
        "meadow": [pt(a0 - 0.6, b0 - 1.7), pt(a0 - 1.5, b0 - 0.9)],  # detrás del lote, entre la casa y el árbol
        "field": [pt(a0, b0), pt(a1, b1)],
        "pasture": corners(pasture(farm)),
        "yard": corners(yard(farm)),
    }


def pasture(farm):
    """El potrero de las vacas, en (a, b): al frente del lote, donde no hay casa, árboles ni estanque."""
    return farm.a0 + 0.15, farm.a1 - 0.35, farm.b1 + 0.95, farm.b1 + 2.35


def yard(farm):
    """El patio de las gallinas, en (a, b): frente a la casa, entre la huerta y el portón."""
    return farm.a0 - 1.3, farm.a0 - 0.3, farm.GATE[1] + 0.35, farm.b1 + 0.9


def scenery(farm, layout):
    """Lo que rodea la finca para que no quede vacía: árboles y arbustos, un
    estanque con juncos, pacas de heno, leña, un bebedero, un camino de tierra desde el portón, piedras y flores. Es
    ambiente: no muestra ningún dato. Devuelve (lo de atrás del lote, lo de adelante)."""
    rnd = random.Random(31)
    a0, a1, b0, b1 = farm.a0, farm.a1, farm.b0, farm.b1
    back, front = [], []

    # Camino de tierra del portón hacia el frente de la vista.
    for n in range(9):
        a, b = a0 - 0.2 - n * 0.42, farm.GATE[0] + 0.3 + n * 0.55
        back.append(farm.quad([(a, b), (a + 0.5, b), (a + 0.5, b + 0.6), (a, b + 0.6)], shade(granja.PATH, rnd.choice((-0.04, 0.0, 0.05)))))

    # Árboles de bloques alrededor (los de atrás antes, para que no tapen la casa).
    for a, b in ((a0 - 3.4, b0 - 1.2), (a1 + 0.9, b0 - 2.4), (a1 + 2.2, b0 - 1.6), (a0 + 1.2, b0 - 2.9)):
        back += farm.tree(a, b)
    for a, b in ((a1 + 1.0, b1 + 3.3), (a0 - 1.9, b1 + 2.4)):  # lejos del estanque y del potrero
        front += farm.tree(a, b)

    # Arbustos y flores sueltas en el pasto.
    for a, b in ((a1 + 1.0, b1 - 0.4), (a0 - 2.9, b1 + 0.6), (a1 + 0.5, b1 + 2.6), (a0 - 0.5, b1 + 2.7), (a1 + 2.6, b0 + 0.6)):
        x, y = farm.pt(a, b)
        front += cv.blob(x, y - 8, 14, "#5E9A3E", seed=int(abs(a * 10 + b))) + cv.blob(x + 12, y - 4, 10, "#6FAE4A", seed=int(abs(a * 7 + b * 3)))
        for _ in range(3):
            front += cv.flower(x + rnd.uniform(-16, 16), y + rnd.uniform(-2, 6), 2.6, rnd.choice(("#FFFFFF", "#F2D23A", "#E8607A")))

    # Estanque con juncos, a la derecha del lote, donde la vista no lo corta.
    pa, pb = a1 + 0.9, b0 + 0.9
    front.append(farm.quad([(pa, pb), (pa + 1.3, pb), (pa + 1.3, pb + 1.0), (pa, pb + 1.0)], "#6E9A3A"))
    front.append(farm.quad([(pa + 0.1, pb + 0.1), (pa + 1.2, pb + 0.1), (pa + 1.2, pb + 0.9), (pa + 0.1, pb + 0.9)], "#5B8FB8"))
    front.append(farm.quad([(pa + 0.25, pb + 0.25), (pa + 0.7, pb + 0.25), (pa + 0.7, pb + 0.45), (pa + 0.25, pb + 0.45)], "#8EB4D0"))
    for t in (0.15, 0.3, 0.85):
        x, y = farm.pt(pa + t * 1.3, pb + 0.95)
        for d in (-3, 0, 3):
            front += cv.blade(x + d, y, 90 + d * 5, rnd.uniform(12, 18), 1.6, "#4E7F35")

    # Pacas de heno y leña cerca de la casa; el bebedero, junto al potrero de las vacas.
    for a, b, z in ((a0 - 1.1, b0 - 0.6, 0), (a0 - 0.75, b0 - 0.6, 0), (a0 - 0.93, b0 - 0.6, 12)):
        back += farm.box(a, b, a + 0.32, b + 0.3, z, z + 12, "#E2C068", tone=(0.06, -0.08, -0.2))
    back += farm.box(a0 - 2.5, b1 - 0.1, a0 - 2.0, b1 + 0.15, 0, 9, "#8A6238")
    back += farm.box(a0 - 2.45, b1 - 0.05, a0 - 2.05, b1 + 0.1, 9, 15, "#A07444")

    # Piedras.
    for a, b in ((a1 + 0.5, b1 + 1.0), (a0 - 0.6, b1 + 1.4), (a1 + 1.9, b0 - 1.4)):
        front += farm.box(a, b, a + 0.18, b + 0.14, 0, 6, "#A9A69C")
        front += farm.box(a + 0.1, b + 0.1, a + 0.22, b + 0.2, 0, 4, "#8F8C83")
    # La cerca del potrero: los lados de atrás van detrás de las vacas; los del frente, delante.
    pa0, pa1, pb0, pb1 = pasture(farm)
    m = 0.12
    back += farm.fence((pa0 - m, pb0 - m), (pa1 + m, pb0 - m), lantern_ends=False)
    back += farm.fence((pa0 - m, pb0 - m), (pa0 - m, pb1 + m), lantern_ends=False)
    front += farm.fence((pa1 + m, pb0 - m), (pa1 + m, pb1 + m), lantern_ends=False)
    front += farm.fence((pa0 - m, pb1 + m), (pa1 + m, pb1 + m), lantern_ends=False)
    # El bebedero, pegado por fuera al lado izquierdo del potrero.
    ta, tb = pa0 - 0.7, pb0 + 0.4
    back += farm.box(ta, tb, ta + 0.22, tb + 0.55, 0, 8, "#8A8A86")
    back.append(farm.quad([(ta + 0.03, tb + 0.03, 8), (ta + 0.19, tb + 0.03, 8), (ta + 0.19, tb + 0.52, 8), (ta + 0.03, tb + 0.52, 8)], "#6F98B9"))
    return back, front


def tint(time):
    if time == "noche":
        return f'<rect width="{W}" height="{H}" fill="#0B1A3A" fill-opacity="0.45"/>'
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
            anchors = farm_anchors(farm)
            around_back, around_front = scenery(farm, layout)
            data["layouts"][name] = {
                "cells": [{"i": i, "j": j, "x": round(x, 2), "y": round(y, 2)} for (i, j) in cells for x, y in [escena.cube_pos(layout, i, j)]],
                "ground": join(farm.ground()),
                "back": join(around_back + farm.back()),
                "front": join(farm.front() + around_front),
                # El perro va aparte, centrado en su sitio: la web lo esconde cuando sale a correr detrás de la gallina.
                "dog": join(escena.dog(0, 0, 1.25)),
                "top": round(-cv.B * 1.2, 2),  # dónde va el rótulo sobre el centro del cubo
                "anchors": anchors,
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
