"""Lámina de tokens para Figma, en el mismo estilo diorama del kit (HU-152 y HU-153).

Escribe design/tokens/tokens.svg leyendo los valores de design/tokens/tokens.json.

    python design/kit/tokens_sheet.py
"""

from pathlib import Path

from build_kit_svg import BORDE, D, P, PIECES, TOKENS, WHITE, chamfer, facets, poly, shade, svg
from sheet import FONT_TITLE, SEC, at, lines, ridges, section, text


def px(group, key):
    return float(TOKENS[group][key]["$value"].replace("px", ""))


def palette():
    b = []
    names = list(P)
    for i, name in enumerate(names):
        x, y = 32 + (i % 3) * 350, 96 + (i // 3) * 160
        base = P[name]
        side = D.get(name) or (BORDE if name == "niebla" else shade(base, -0.45))
        ink = WHITE if name in ("noche", "tierra", "rojo", "oliva") else P["noche"]
        b.append(poly(chamfer(x, y + 14, 320, 96, 10), side))
        b.append(poly(chamfer(x, y, 320, 96, 10), base))
        b += facets(x, y, 320, 96, 10, base)
        b.append(text(x + 24, y + 44, name, 24, 600, ink, FONT_TITLE))
        b.append(text(x + 24, y + 72, base, 16, fill=ink))
        note = f"canto y texto: oscuro {D[name]}" if name in D else ("solo fondo; siempre con texto noche" if name == "niebla" else "texto principal")
        b.append(text(x + 4, y + 134, note, 14, fill=SEC))
    b.append(text(32, 580, "La cara de cada bloque es el color base; su canto es la variante oscura, que también sirve para texto sobre blanco o niebla (≥ 4,5:1).", 16, fill=SEC))
    return b


def traffic_lights():
    labels = (
        ("verde", "Verde · Buen momento", P["noche"]),
        ("amarillo", "Amarillo · Con cuidado", P["noche"]),
        ("rojo", "Rojo · Mejor no ahora", WHITE),
        ("no-evaluable", "No evaluable · Faltan datos", P["noche"]),
    )
    b = []
    for i, (key, label, ink) in enumerate(labels):
        y = 92 + i * 100
        b.append(at(32, y, PIECES[f"semaforo-{key}"]))
        b.append(text(32 + (63 if key == "verde" else 51), y + 38, label, 18, 700, ink))
    y = 500
    b.append(poly(chamfer(35, y, 320, 52, 10), WHITE, D["cielo"], 3, "3 5"))
    b.append(text(59, y + 34, "?", 20, 700, anchor="middle"))
    b.append(text(83, y + 33, "Datos insuficientes", 18, 700))
    b += lines(420, 116, [
        "Cada estado se reconoce por tres cosas a la vez:",
        "silueta, ícono y texto. Nunca solo por el color (W2).",
        "",
        "Verde · bisel 26 (puntas en octágono) · octágono",
        "Amarillo · bisel 10 · triángulo",
        "Rojo · bisel 0 (esquinas rectas) · cuadrado",
        "No evaluable · niebla, contorno y estaca a trazos · anillo",
        "Datos insuficientes · contorno punteado y bruma · «?»",
        "",
        "«No evaluable» es una luz; «datos insuficientes» es el",
        "estado de una señal. Ninguno usa rojo ni se parece",
        "a un riesgo (R1).",
        "",
        "Contraste de texto comprobado por build_tokens.py:",
        "verde 7,0:1 · amarillo 7,4:1 · rojo 5,7:1 · niebla 11,4:1",
    ], 17, 26)
    return b


def typography():
    return [
        text(32, 132, "Fredoka 48 · Títulos", 48, 600, font=FONT_TITLE),
        text(32, 182, "Fredoka 28 · ¿Siembro papa en semestre B?", 28, 600, font=FONT_TITLE),
        text(32, 224, "Atkinson Hyperlegible 22 · Subtítulos y acciones", 22),
        text(32, 260, "Atkinson Hyperlegible 18 · Texto corriente. La lluvia del semestre estuvo un 18 % por debajo de lo normal.", 18),
        text(32, 292, "Atkinson Hyperlegible 18 negrita · Botones y etiquetas de estado", 18, 700),
        text(32, 322, "16 · Notas y razones secundarias        14 · mínimo, solo créditos y pies", 16, fill=SEC),
        text(32, 362, "Fredoka redondeada da el tono de juego; Atkinson se diseñó para baja visión y se lee bien al sol. Cifras con números tabulares.", 16, fill=SEC),
    ]


def bevel_and_edge():
    b = []
    for i, (key, token) in enumerate((k, v) for k, v in TOKENS["bisel"].items() if not k.startswith("$")):
        x, c = 32 + i * 152, float(token["$value"].replace("px", ""))
        b.append(poly(chamfer(x, 96, 120, 64 if key == "octagono" else 90, c), P["niebla"], D["cielo"], 3))
        b.append(text(x + 60, 212, key, 16, 700, anchor="middle"))
        b.append(text(x + 60, 234, token["$value"], 14, fill=SEC, anchor="middle"))
    blocks = (("boton", "Botón"), ("boton-hundido", "Botón presionado"), ("lista", "Lista"), ("panel", "Panel"))
    for i, (key, label) in enumerate(blocks):
        x, depth = 32 + i * 270, px("canto", key)
        color, side = (D["oliva"], "#3A4A1D") if key.startswith("boton") else (WHITE, BORDE)
        top = 276 + (6 - depth if key == "boton-hundido" else 0)
        b.append(poly(chamfer(x, top + depth, 230, 52, 10), side))
        b.append(poly(chamfer(x, top, 230, 52, 10), color, None if key.startswith("boton") else BORDE, 2))
        if key.startswith("boton"):
            b += facets(x, top, 230, 52, 10, color)
        b.append(text(x, 366, f"{label} · canto {depth:g} px", 14, fill=SEC))
    return b


def spacing():
    b = []
    x = 32
    for key, token in TOKENS["espacio"].items():
        if key.startswith("$") or key in ("0", "tactil-minimo"):
            continue
        size = float(token["$value"].replace("px", ""))
        b.append(poly(chamfer(x, 150 - size, size, size, 0), P["oliva"]))
        b.append(text(x + size / 2, 176, f"{size:g}", 14, fill=SEC, anchor="middle"))
        x += size + 40
    b.append(poly(chamfer(700, 106, 44, 44, 8), WHITE, P["noche"], 2.5))
    b.append(text(760, 124, "Objetivo táctil mínimo: 44 px", 16, 700))
    b.append(text(760, 146, "Base de 4 px. Entre piezas, 16 a 24.", 16, fill=SEC))
    return b


def strokes():
    samples = (
        ("contorno · 3 px", dict(stroke=D["cielo"], sw=3, dash=None)),
        ("a trazos · 9 6", dict(stroke=D["cielo"], sw=3, dash="9 6")),
        ("punteado · 3 5", dict(stroke=D["cielo"], sw=3, dash="3 5")),
    )
    b = []
    for i, (label, s) in enumerate(samples):
        x = 32 + i * 270
        b.append(poly(chamfer(x, 100, 230, 52, 10), WHITE, s["stroke"], s["sw"], s["dash"]))
        b.append(text(x, 180, label, 14, fill=SEC))
    x = 32 + 3 * 270 + 6
    b.append(poly(chamfer(x - 4.5, 95.5, 239, 61, 14), "none", P["noche"], 3))
    b.append(poly(chamfer(x, 100, 230, 52, 10), D["oliva"]))
    b += facets(x, 100, 230, 52, 10, D["oliva"])
    b.append(text(x - 4, 180, "foco · contorno noche, separado 3 px", 14, fill=SEC))
    return b


def sheet():
    W, H = 2340, 1610
    b = [f'<rect width="{W}" height="{H}" fill="{P["cielo"]}"/>']
    b += ridges(W, 1500, 110)
    b.append(text(40, 84, "Tokens de diseño · AgroSense", 48, 600, font=FONT_TITLE))
    b.append(text(40, 122, "HU-152 · Fuente de verdad: design/tokens/tokens.json. Nada lleva esquinas redondas ni sombras: el volumen lo dan el bisel, las facetas y el canto.", 18))
    b.append(section(40, 150, 1100, 610, "Paleta", palette()))
    b.append(section(1180, 150, 1120, 610, "Semáforo y estados", traffic_lights()))
    b.append(section(40, 800, 1100, 390, "Tipografía", typography()))
    b.append(section(1180, 800, 1120, 390, "Bisel y canto", bevel_and_edge()))
    b.append(section(40, 1230, 1100, 210, "Espaciado", spacing()))
    b.append(section(1180, 1230, 1120, 210, "Trazos", strokes()))
    return svg(W, H, b)


if __name__ == "__main__":
    out = Path(__file__).resolve().parent.parent / "tokens" / "tokens.svg"
    out.write_text(sheet(), encoding="utf-8", newline="\n")
    print(f"Escrito {out.name} ({out.stat().st_size // 1024} KB)")
