"""Semilla Sputnik: la semilla-satélite dibujada como caricatura de los años 60 (HU-171, tercera ronda).

Fusión de dos propuestas: el concepto de la semilla satélite y el estilo de Sputnik.
Las antenas barridas del Sputnik son las raíces; el brote es la antena de señal; las hojas, los paneles.

    python design/mascota/semilla_sputnik.py     # escribe semilla-sputnik.svg
"""

from build_mascota import DIR, FONT_TITLE, P, SEC, chamfer, lines, poly, ridges, section, svg, text
from conceptos_estilos import circle, el, ellipse, line, path

W, H = 300, 250
INK, CREAM, RED, LEAF, LEAF2 = "#1D1D1B", "#FFF6E0", "#E76F51", "#5FA052", "#8CC56A"
PAPER, NIGHT = "#F4E9D0", "#1F2A44"

# Forma de la semilla: (contorno, color, luz, detalle propio)
SEEDS = {
    "germinada": dict(
        d="M158 58 C196 62 216 98 212 132 C208 168 184 188 156 188 C126 188 104 166 102 134 C100 98 122 60 158 58Z",
        fill="#C8873A", light="#E3AE68"),
    "frijol": dict(
        d="M126 76 C156 50 208 70 212 118 C216 162 184 190 150 186 C114 182 96 154 108 130 C114 118 130 120 130 108 C130 96 114 94 126 76Z",
        fill="#A8463A", light="#CC6B58"),
    "maiz": dict(
        d="M124 64 C140 54 178 54 194 64 C214 78 212 120 200 152 C190 178 172 190 158 190 C144 190 126 178 116 152 C104 120 104 78 124 64Z",
        fill="#F2C230", light="#FBE08A"),
}

MOODS = {
    "reposo": dict(eyes="pie", mouth="smile", arms=("down", "down")),
    "guia": dict(eyes="pie", look=4, mouth="open", arms=("down", "point"), waves=2),
    "celebra": dict(eyes="happy", mouth="big", arms=("up", "up"), lift=-8, sparkles=True),
    "sin-datos": dict(eyes="hollow", mouth="flat", arms=("tuck", "tuck"), scale=0.9, mist=True, droop=True),
    "vuelo": dict(eyes="pie", look=5, mouth="open", arms=("back", "point"), tilt=-16, speed=True, waves=1),
}


def sparkle(x, y, r, color=RED):
    return path(f"M{x} {y - r} Q{x} {y} {x + r} {y} Q{x} {y} {x} {y + r} Q{x} {y} {x - r} {y} Q{x} {y} {x} {y - r}Z", color)


def roots(droop):
    """Las cuatro antenas del Sputnik, vueltas raíces. Salen de abajo y se barren hacia atrás."""
    ends = ((30, 190), (52, 220), (86, 238), (120, 242)) if not droop else ((70, 214), (92, 226), (116, 234), (140, 238))
    out = []
    for i, (x, y) in enumerate(ends):
        mx, my = (128 + x) / 2 + 6, (166 + y) / 2 + (14 - i * 6)
        out.append(path(f"M128 166 Q{mx:g} {my:g} {x} {y}", "none", INK, 4))
        out.append(circle(x, y, 5.5, RED, INK, 3))
    return out


def sprout(waves):
    out = [path("M158 62 C160 48 158 40 154 30", "none", INK, 5)]
    out.append(path("M154 32 C136 32 124 18 128 6 C144 8 156 18 154 32Z", LEAF, INK, 4))
    out.append(path("M156 34 C172 36 188 26 188 12 C172 10 158 20 156 34Z", LEAF2, INK, 4))
    # Nervaduras en cuadrícula: las hojas son los paneles solares.
    out.append(path("M150 28 C142 24 136 18 132 10 M146 16 L136 22 M178 14 C172 22 166 28 158 32 M172 28 L166 16", "none", INK, 1.8))
    for i in range(waves):
        r = 14 + i * 10
        out.append(path(f"M{196 + r * 0.5:g} {10 - r * 0.5:g} Q{200 + r:g} {14} {196 + r * 0.5:g} {20 + r * 0.6:g}", "none", RED, 3.5))
    return out


def arm(kind, side):
    """Brazo de manguera con guante. `side`: -1 izquierdo, 1 derecho."""
    sx = 158 + side * 50
    paths = {
        "down": (f"M{sx} 138 C{sx + side * 26} 148 {sx + side * 32} 166 {sx + side * 28} 184", (sx + side * 28, 188)),
        "up": (f"M{sx} 126 C{sx + side * 30} 112 {sx + side * 42} 88 {sx + side * 40} 62", (sx + side * 40, 58)),
        "point": (f"M{sx} 130 C{sx + side * 22} 124 {sx + side * 44} 118 {sx + side * 64} 112", (sx + side * 68, 111)),
        "tuck": (f"M{sx} 140 C{sx + side * 16} 150 {sx + side * 10} 166 {sx - side * 6} 168", (sx - side * 8, 168)),
        "back": (f"M{sx} 140 C{sx + side * 18} 156 {sx + side * 34} 162 {sx + side * 54} 170", (sx + side * 58, 172)),
    }
    d, (hx, hy) = paths[kind]
    out = [path(d, "none", INK, 9), circle(hx, hy, 13, CREAM, INK, 4)]
    if kind == "point":  # el dedo que señala
        out.append(path(f"M{hx + side * 8} {hy - 2} l{side * 16} -3", "none", INK, 7))
        out.append(path(f"M{hx + side * 8} {hy - 2} l{side * 16} -3", "none", CREAM, 3))
    return out


def eyes(kind, look):
    out = []
    for x in (140, 182):
        if kind == "happy":
            out.append(path(f"M{x - 14} 122 Q{x} 100 {x + 14} 122", "none", INK, 5))
        elif kind == "hollow":  # sin datos: el ojo queda en contorno a trazos, vacío; no triste
            out.append(ellipse(x, 116, 15, 20, CREAM, INK, 3.5, stroke_dasharray="5 5"))
        else:
            out.append(ellipse(x, 116, 15, 20, CREAM, INK, 4))
            out.append(path(f"M{x + look} 120 m0 -10 a10 10 0 1 1 -9 6 l9 4Z", INK))
    return out


def mouth(kind):
    if kind == "smile":
        return [path("M146 150 Q160 164 176 150", "none", INK, 4)]
    if kind == "open":
        return [path("M138 148 Q160 172 184 148Z", CREAM, INK, 4)]
    if kind == "big":
        return [path("M132 144 Q160 186 190 144Z", CREAM, INK, 4), path("M146 162 Q160 172 176 162", RED)]
    return [line(150, 154, 172, 154, INK, 4)]


def seed_mascot(mood="reposo", seed="germinada"):
    m, s = MOODS[mood], SEEDS[seed]
    body = [
        path(s["d"], s["fill"], INK, 5),
        path("M124 92 A46 46 0 0 1 164 70", "none", s["light"], 8),  # brillo de caricatura
        path("M116 128 C114 150 124 168 140 178", "none", INK, 2.5, opacity=0.35),  # veta de la cáscara
        path("M146 66 Q158 78 170 64", "none", INK, 3.5),  # la cáscara se abre: de ahí sale el brote
        ellipse(124, 142, 9, 5, RED, opacity=0.55),
        ellipse(196, 142, 9, 5, RED, opacity=0.55),
    ]
    if seed == "maiz":
        body.insert(1, path("M140 184 C148 192 168 192 176 184 C170 172 146 172 140 184Z", "#FFF4CC"))
    parts = roots(m.get("droop", False)) + arm(m["arms"][0], -1) + sprout(m.get("waves", 0)) + body
    parts += eyes(m["eyes"], m.get("look", 0)) + mouth(m["mouth"]) + arm(m["arms"][1], 1)
    transforms = []
    if m.get("lift"):
        transforms.append(f"translate(0 {m['lift']})")
    if m.get("tilt"):
        transforms.append(f"rotate({m['tilt']} 158 124)")
    if m.get("scale"):
        transforms.append(f"translate(16 22) scale({m['scale']})")
    out = [el("g", "".join(parts), id="semilla", transform=" ".join(transforms) or "translate(0 0)")]
    if m.get("sparkles"):
        out += [sparkle(46, 60, 12), sparkle(262, 96, 9), sparkle(238, 214, 8), sparkle(74, 26, 6, "#2A9D8F")]
    if m.get("speed"):
        for y, x1, x2 in ((70, 20, 70), (104, 6, 50), (140, 14, 44)):
            out.append(line(x1, y, x2, y - 12, INK, 3.5))
    if m.get("mist"):
        for x, k in ((84, 1.0), (214, 0.8)):
            out.append(path(f"M{x - 44 * k:g} 232 q{14 * k:g} {-22 * k:g} {34 * k:g} {-10 * k:g} q{16 * k:g} {-18 * k:g} {32 * k:g} 0 q{22 * k:g} {-6 * k:g} {22 * k:g} 10Z", "#FFFFFF", INK, 3, opacity=0.9))
    return out


def stage(x, y, w, h, color=PAPER, stars=False):
    out = [poly(chamfer(x, y, w, h, 16), color)]
    if stars:
        for i in range(14):
            out.append(sparkle(x + 30 + (i * 139) % (w - 60), y + 24 + (i * 67) % (h - 50), 4, CREAM))
    return out


def place(x, y, scale, mood="reposo", seed="germinada"):
    return f'<g transform="translate({x:g} {y:g}) scale({scale:g})">{"".join(seed_mascot(mood, seed))}</g>'


def main_panel():
    b = stage(32, 96, 700, 600) + [place(32 + 350 - W * 1.15, 96 + 12, 2.3)]
    b += stage(752, 96, 340, 290, NIGHT, stars=True) + [place(752 + 170 - W * 0.55, 96 + 8, 1.1)]
    b.append(text(752, 410, "De noche: tinta y crema se sostienen", 14, fill=SEC))
    for i, (size, color) in enumerate(((96, PAPER), (64, PAPER), (48, PAPER), (48, P["cielo"]))):
        x = 752 + i * 86
        b += [poly(chamfer(x, 440, 78, 110, 10), color), place(x + 39 - size * W / H / 2, 440 + 55 - size / 2, size / H)]
        b.append(text(x + 39, 572, f"{size} px", 13, fill=SEC, anchor="middle"))
    b += lines(752, 612, ["A 48 px quedan la silueta de semilla,", "los dos ojos y el brote.", "El último está sobre el cielo de la app."], 15, 21, fill=SEC)
    return b


def poses_panel():
    poses = (("guia", "Guía", "Señala con el guante; ondas en el brote."),
             ("celebra", "Celebra · verde", "Brazos arriba, ojos en arco, destellos."),
             ("sin-datos", "Sin datos", "Se encoge, ojos vacíos a trazos, niebla. No está triste (R1)."),
             ("vuelo", "En vuelo (scroll)", "Se inclina; las raíces quedan atrás como estela."))
    b = []
    for i, (mood, title, note) in enumerate(poses):
        x, y = 32 + (i % 2) * 562, 96 + (i // 2) * 310
        b += stage(x, y, 544, 230) + [place(x + 272 - W * 0.46, y + 2, 0.92, mood)]
        b += [text(x, y + 256, title, 18, 700), text(x, y + 280, note, 15, fill=SEC)]
    return b


def sheet():
    SW, SH = 2400, 1540
    b = [f'<rect width="{SW}" height="{SH}" fill="{P["cielo"]}"/>']
    b += ridges(SW, 1410, 130)
    b.append(text(40, 84, "Semilla Sputnik", 48, 600, font=FONT_TITLE))
    b.append(text(40, 122, "HU-171, tercera ronda · La semilla satélite dibujada como caricatura de los años 60: una semilla germinando que vuela con sus raíces por antenas.", 18))
    b.append(section(40, 150, 1130, 740, "La mascota", main_panel()))
    b.append(section(1190, 150, 1170, 740, "Poses", poses_panel()))
    b.append(section(40, 930, 2320, 440, "", []))
    b.append(f'<g transform="translate(40 760)">{"".join(idea_panel_wide())}</g>')
    return svg(SW, SH, b)


def idea_panel_wide():
    """La idea y las variantes de semilla, en dos columnas dentro del panel inferior."""
    left = [text(32, 226, "De dónde sale", 28, 600, font=FONT_TITLE)] + lines(32, 268, [
        "De la Semilla sale el concepto; de Sputnik, el dibujo.",
        "· Raíces = las cuatro antenas barridas del Sputnik. Al volar quedan atrás como estela: dan dirección.",
        "· Brote = la antena de señal. Emite ondas cuando guía.",
        "· Dos hojas = los paneles solares, con nervaduras en cuadrícula: la hoja ya es un panel solar natural.",
        "· La cáscara abierta arriba dice «semilla germinando», no «robot redondo».",
        "· Brazos de manguera con guantes: saluda, señala y celebra. Es lo que la hace guía.",
        "· Ojos de pastel: muy expresivos y fáciles de animar.",
        "",
        "Estilo: tinta gruesa y cinco colores planos, sin degradados. No es low-poly a propósito:",
        "es «otro material» que viaja por el paisaje de bloques.",
        "",
        "Capas para animar: raíces (4), brazo-izq, brazo-der, brote, cuerpo, ojos, boca.",
    ], 16, 25)
    right = [text(1230, 226, "¿Qué semilla?", 28, 600, font=FONT_TITLE)]
    for i, (seed, name) in enumerate((("germinada", "Semilla germinada (propuesta)"), ("frijol", "Frijol"), ("maiz", "Grano de maíz"))):
        x = 1230 + i * 350
        right += stage(x, 250, 330, 270) + [place(x + 165 - W * 0.5, 256, 1.0, "reposo", seed)]
        right.append(text(x, 546, name, 15, fill=SEC))
    return left + right


if __name__ == "__main__":
    out = DIR / "semilla-sputnik.svg"
    out.write_text(sheet(), encoding="utf-8", newline="\n")
    print(f"Escrito {out.name} ({out.stat().st_size // 1024} KB)")
