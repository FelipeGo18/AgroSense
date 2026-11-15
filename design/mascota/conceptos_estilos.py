"""Nueve conceptos de mascota, cada uno con su propio estilo gráfico (HU-171, segunda ronda).

A diferencia de conceptos.py, aquí el estilo se aleja a propósito del kit y de su paleta:
cada mascota parte de una idea y se dibuja con el lenguaje que mejor la cuenta.

    python design/mascota/conceptos_estilos.py     # escribe conceptos-estilos.svg
"""

import math

from build_mascota import DIR, FONT_TITLE, P, SEC, chamfer, lines, poly, pts, ridges, section, svg, text

W, H = 300, 250


def el(tag, body="", **attrs):
    a = " ".join(f'{k.rstrip("_").replace("_", "-")}="{v}"' for k, v in attrs.items())
    return f"<{tag} {a}>{body}</{tag}>" if body else f"<{tag} {a}/>"


def circle(cx, cy, r, fill, stroke=None, sw=0, **kw):
    extra = dict(stroke=stroke, stroke_width=sw) if stroke else {}
    return el("circle", cx=cx, cy=cy, r=r, fill=fill, **extra, **kw)


def ellipse(cx, cy, rx, ry, fill, stroke=None, sw=0, **kw):
    extra = dict(stroke=stroke, stroke_width=sw) if stroke else {}
    return el("ellipse", cx=cx, cy=cy, rx=rx, ry=ry, fill=fill, **extra, **kw)


def path(d, fill="none", stroke=None, sw=0, **kw):
    extra = dict(stroke=stroke, stroke_width=sw, stroke_linecap="round", stroke_linejoin="round") if stroke else {}
    return el("path", d=d, fill=fill, **extra, **kw)


def rect(x, y, w, h, fill, stroke=None, sw=0, rx=0, **kw):
    extra = dict(stroke=stroke, stroke_width=sw) if stroke else {}
    return el("rect", x=x, y=y, width=w, height=h, rx=rx, fill=fill, **extra, **kw)


def line(x1, y1, x2, y2, stroke, sw, **kw):
    return el("line", x1=x1, y1=y1, x2=x2, y2=y2, stroke=stroke, stroke_width=sw, stroke_linecap="round", **kw)


# ---------- 1 · Papa: pegatina kawaii ----------

def papa():
    ink = "#4A2E17"
    b = []
    arm = "".join([
        line(92, 128, 70, 120, ink, 6),
        rect(26, 96, 46, 40, "#5EC2E8", ink, 5, 8),
        line(49, 98, 49, 134, ink, 3), line(28, 116, 70, 116, ink, 3),
    ])
    b += [arm, el("g", arm, transform="translate(300 0) scale(-1 1)")]  # panelitos como brazos
    b.append(path("M96 124 C84 84 128 56 170 62 C214 68 236 106 222 152 C212 190 160 206 120 194 C94 186 102 152 96 124Z", "#D9A45B", ink, 6))
    b.append(path("M112 112 C108 90 130 74 156 74 C140 84 122 96 112 112Z", "#EFC98A"))
    for x, y in ((196, 96), (206, 150), (124, 176)):  # los «ojos» de la papa
        b.append(ellipse(x, y, 6, 4, "#B98342"))
    for x in (136, 180):
        b.append(ellipse(x, 126, 9, 12, ink))
        b.append(circle(x + 3, 121, 3.5, "#FFFFFF"))
    b.append(path("M148 146 Q158 158 168 146", "none", ink, 4))
    b.append(ellipse(120, 146, 10, 6, "#F4978E"))
    b.append(ellipse(196, 146, 10, 6, "#F4978E"))
    b.append(path("M158 62 C158 50 156 44 152 38", "none", ink, 5))  # brote
    b.append(path("M152 40 C136 38 128 26 132 16 C146 18 154 28 152 40Z", "#7BC043", ink, 4))
    b.append(path("M154 42 C168 42 180 34 180 22 C166 20 154 28 154 42Z", "#A4D65E", ink, 4))
    return b


# ---------- 2 · Chía: constelación ----------

def chia():
    star, wire = "#FFFFFF", "#8FC8FF"
    head = [(150 + 44 * math.cos(math.radians(a)), 130 + 40 * math.sin(math.radians(a))) for a in range(-90, 270, 60)]

    def node(x, y, r=4, color=star):
        return circle(x, y, r * 2.6, color, opacity=0.18) + circle(x, y, r, color)

    b = [el("polygon", points=pts(head), fill="none", stroke=wire, stroke_width=1.5)]
    wings = ([(86, 108), (40, 96), (34, 134), (84, 146)], [(214, 108), (260, 96), (266, 134), (216, 146)])
    for wing in wings:
        b.append(el("polygon", points=pts(wing), fill="none", stroke=wire, stroke_width=1.5))
        b.append(line(*wing[0], *wing[2], wire, 1))
        b.append(line(*wing[1], *wing[3], wire, 1))
    b.append(line(150, 90, 150, 56, wire, 1.5))
    b.append(path("M150 28 A18 18 0 1 0 168 50 A14 14 0 1 1 150 28Z", "#FFD86B"))  # la luna: Chía
    for i, (x, y) in enumerate(((150, 186), (140, 204), (156, 220), (146, 238))):  # estela
        b.append(node(x, y, 2.4 - i * 0.3))
    for x, y in head + wings[0] + wings[1]:
        b.append(node(x, y, 3.2))
    b.append(node(132, 124, 6.5, "#FFD86B"))  # ojos: las dos estrellas más brillantes
    b.append(node(168, 124, 6.5, "#FFD86B"))
    for x, y in ((138, 148), (150, 153), (162, 148)):
        b.append(circle(x, y, 1.8, star))
    return b


# ---------- 3 · Bit: pixel art ----------

SPRITE = (
    "................",
    ".......RR.......",
    ".......KK.......",
    "....KKKKKKKK....",
    "...KWWWWWWWWK...",
    "CBKWWWWWWWWWWKCB",
    "BBKWKKWWWWKKWKBB",
    "BCKWKHWWWWKHWKBC",
    "BBKWWWWWWWWWWKBB",
    "..KWPWWKKWWPWK..",
    "..KWWWWWWWWWSK..",
    "...KGGGGGGGGK...",
    "....KKKKKKKK....",
    ".....YK..KY.....",
    "......Y..Y......",
    "................",
)
PIXELS = {"K": "#1B1035", "W": "#F4F0FF", "S": "#CFC6EC", "B": "#3F8CFF", "C": "#8FD3FF", "R": "#FF4D6D", "P": "#FF9EB5",
          "G": "#8C7AE6", "Y": "#FFD23F", "H": "#FFFFFF"}


def bit():
    s, ox, oy = 12, 54, 30
    return [rect(ox + c * s, oy + r * s, s, s, PIXELS[ch]) for r, row in enumerate(SPRITE) for c, ch in enumerate(row) if ch != "."]


# ---------- 4 · Tunjo: orfebrería ----------

def tunjo():
    gold, deep, shine = "#E3B341", "#9C6F1C", "#F9E08A"
    b = []
    rays = [(150 + 62 * math.cos(math.radians(a)), 76 + 62 * math.sin(math.radians(a))) for a in range(-170, -9, 20)]
    for x, y in rays:  # tocado de rayos: también es el plato de la antena
        b.append(line(150, 76, x, y, gold, 5))
        b.append(circle(x, y, 5, gold))
    b.append(path("M96 76 A54 54 0 0 1 204 76Z", gold, deep, 2.5))
    for sx in (-1, 1):
        px = 150 + sx * 84
        b.append(line(150 + sx * 30, 134, px, 150, gold, 6))
        b.append(rect(px - 20, 122, 40, 58, gold, deep, 2.5, 3))
        for k in range(1, 3):
            b.append(line(px - 20, 122 + k * 19.3, px + 20, 122 + k * 19.3, deep, 2))
        b.append(line(px, 122, px, 180, deep, 2))
    b.append(el("polygon", points=pts([(122, 122), (178, 122), (198, 218), (102, 218)]), fill=gold, stroke=deep, stroke_width=2.5))
    b.append(path("M150 150 m-14 0 a14 14 0 1 1 14 14 a8 8 0 1 1 -8 -8", "none", shine, 3))  # espiral
    b.append(line(112, 200, 188, 200, deep, 2))
    b.append(rect(118, 66, 64, 58, gold, deep, 2.5, 10))
    for x in (134, 166):  # ojos de «grano de café», propios de la orfebrería
        b.append(ellipse(x, 90, 9, 5, shine, deep, 2))
        b.append(line(x - 8, 90, x + 8, 90, deep, 2))
    b.append(line(150, 90, 150, 104, deep, 2.5))
    b.append(line(140, 112, 160, 112, deep, 2.5))
    for x in (128, 172):
        b.append(rect(x - 8, 218, 16, 14, gold, deep, 2.5, 2))
    return b


# ---------- 5 · Gota: burbuja brillante ----------

GOTA_DEFS = (
    '<radialGradient id="gota-cuerpo" cx="0.38" cy="0.32" r="0.8"><stop offset="0" stop-color="#7DEFE4"/>'
    '<stop offset="0.55" stop-color="#2BB8C4"/><stop offset="1" stop-color="#14739B"/></radialGradient>'
)


def gota():
    ink = "#0B3A52"
    b = [path("M92 172 A62 22 0 0 1 208 158", "none", "#FF7A59", 6)]  # anillo, parte de atrás
    b.append(path("M150 34 C150 34 94 108 94 152 A56 56 0 0 0 206 152 C206 108 150 34 150 34Z", "url(#gota-cuerpo)"))
    b.append(path("M132 86 C118 106 110 126 110 142 C112 122 124 102 138 88Z", "#FFFFFF", opacity=0.6))
    for x in (132, 170):
        b.append(circle(x, 148, 13, "#FFFFFF"))
        b.append(circle(x + 2, 150, 7, ink))
        b.append(circle(x + 4, 147, 2.4, "#FFFFFF"))
    b.append(path("M144 172 Q151 180 158 172", "none", ink, 3.5))
    b.append(path("M208 158 A62 22 0 0 1 92 172", "none", "#FF7A59", 6))  # anillo, parte de adelante
    b.append(circle(216, 150, 10, "#FF7A59", "#FFFFFF", 3))  # la «luna» que la orbita
    return b


# ---------- 6 · Sputnik: caricatura de los años 60 ----------

def sputnik():
    ink, teal, cream, red = "#1D1D1B", "#2A9D8F", "#FFF6E0", "#E76F51"
    b = []
    for x2, y2 in ((40, 214), (72, 232), (112, 240), (20, 184)):  # cuatro antenas barridas hacia atrás
        b.append(line(128, 150, x2, y2, ink, 4))
        b.append(circle(x2, y2, 5, red, ink, 3))
    b.append(path("M196 120 C226 104 246 86 250 60", "none", ink, 9))  # brazo de manguera que saluda
    b.append(circle(250, 56, 13, cream, ink, 4))
    b.append(path("M110 152 C86 162 76 176 74 196", "none", ink, 9))
    b.append(circle(74, 198, 13, cream, ink, 4))
    b.append(circle(158, 124, 58, teal, ink, 5))
    b.append(path("M118 92 A52 52 0 0 1 176 72", "none", cream, 7, opacity=0.9))
    for x in (138, 180):  # ojos de «pastel con porción»
        b.append(ellipse(x, 116, 15, 20, cream, ink, 4))
        b.append(path(f"M{x + 2} 120 m0 -10 a10 10 0 1 1 -9 6 l9 4Z", ink))
    b.append(path("M130 150 Q160 178 190 148", cream, ink, 4))
    for x, y, r in ((52, 60, 12), (236, 196, 9), (96, 30, 7)):  # destellos
        b.append(path(f"M{x} {y - r} Q{x} {y} {x + r} {y} Q{x} {y} {x} {y + r} Q{x} {y} {x - r} {y} Q{x} {y} {x} {y - r}Z", red))
    return b


# ---------- 7 · Lana: tejido ----------

def lana():
    wool, stitch, face = "#FFF8EC", "#A9886B", "#5B4636"
    b = []
    for x in (120, 144, 164, 186):
        b.append(rect(x - 6, 178, 12, 34, face, rx=5))
    for cx, cy, r in ((108, 138, 34), (146, 110, 38), (190, 126, 34), (176, 158, 32), (130, 162, 30)):
        b.append(circle(cx, cy, r, wool))
    for cx, cy, r in ((108, 138, 34), (146, 110, 38), (190, 126, 34), (176, 158, 32), (130, 162, 30)):
        b.append(circle(cx, cy, r - 5, "none", stitch, 2, stroke_dasharray="6 5"))
    stripes = ("#D1495B", "#EDAE49", "#00798C", "#D1495B", "#EDAE49")  # la ruana
    for i, color in enumerate(stripes):
        b.append(rect(128 + i * 12, 118, 12, 56, color))
    b.append(rect(128, 118, 60, 56, "none", stitch, 2, stroke_dasharray="5 4"))
    b.append(ellipse(82, 128, 26, 30, face))
    b.append(ellipse(60, 108, 12, 7, face, transform="rotate(-30 60 108)"))
    b.append(ellipse(104, 104, 12, 7, face, transform="rotate(30 104 104)"))
    for x in (72, 92):
        b.append(path(f"M{x - 6} 126 Q{x} 134 {x + 6} 126", "none", "#FFFFFF", 3))
    b.append(ellipse(82, 142, 5, 3, "#F4978E"))
    b.append(line(170, 86, 214, 30, "#C9C2B8", 4))  # agujas de tejer: las antenas
    b.append(line(184, 92, 238, 46, "#C9C2B8", 4))
    b.append(circle(214, 30, 5, "#C9C2B8"))
    b.append(circle(238, 46, 5, "#C9C2B8"))
    b.append(path("M196 62 C230 70 256 96 248 132", "none", "#D1495B", 2.5, stroke_dasharray="2 5"))
    b.append(circle(250, 150, 18, "#D1495B"))  # el ovillo que la orbita
    b.append(path("M236 144 Q250 134 264 146 M236 156 Q250 148 266 156", "none", "#F2A0AA", 2.5))
    return b


# ---------- 8 · Paja: garabato a crayón ----------

def paja():
    ink = "#35322E"

    def crayon(d, color):  # relleno corrido, como al colorear saliéndose de la línea
        return path(d, color, transform="translate(5 4)", opacity=0.9) + path(d, "none", ink, 4)

    b = [line(150, 120, 150, 238, "#8A5A2B", 9), line(62, 150, 238, 152, "#8A5A2B", 8)]
    for x, d in ((62, -1), (238, 1)):
        for k in (-14, 0, 14):
            b.append(line(x, 150, x + d * 22, 150 + k, "#E0B43A", 4))
    b.append(crayon("M112 138 L190 136 L200 214 L104 216Z", "#E4572E"))
    for k in range(3):
        b.append(line(118 + k * 26, 140, 114 + k * 28, 214, ink, 2))
    b.append(crayon("M150 62 C182 60 196 84 192 108 C188 132 166 142 146 140 C120 138 106 118 110 96 C112 76 128 64 150 62Z", "#F1DDB3"))
    b.append(path("M124 96 l12 12 m0 -12 l-12 12", "none", ink, 4))
    b.append(circle(170, 102, 7, "none", ink, 4))
    b.append(path("M128 120 Q150 134 174 120", "none", ink, 4))
    for x in (136, 150, 164):
        b.append(line(x, 122, x, 130, ink, 3))
    b.append(crayon("M92 70 L210 62 L190 44 L116 48Z", "#F2C230"))  # el sombrero es el plato de la antena
    b.append(line(152, 46, 160, 16, ink, 4))
    b.append(circle(161, 12, 6, "#E4572E", ink, 3))
    for r in (16, 28):
        b.append(path(f"M{161 + r} {12 - r * 0.6} Q{161 + r * 1.5} 12 {161 + r} {12 + r * 0.6}", "none", "#2E86AB", 3.5))
    return b


# ---------- 9 · Cometa: papel recortado ----------

def cometa():
    top, right, bottom, left, c = (150, 22), (222, 104), (150, 196), (78, 104), (150, 104)
    quads = (((top, right, c), "#E63E8C"), ((right, bottom, c), "#FFC93C"), ((bottom, left, c), "#1FB5AD"), ((left, top, c), "#FF7B39"))
    b = [path("M150 196 C132 210 172 222 150 240", "none", "#5A4A42", 3)]
    for x, y, a in ((140, 210, -20), (162, 224, 15)):  # los lazos de la cola son panelitos
        b.append(el("g", rect(-16, -9, 32, 18, "#2D6CDF") + line(0, -9, 0, 9, "#FFFFFF", 1.5) + line(-16, 0, 16, 0, "#FFFFFF", 1.5),
                    transform=f"translate({x} {y}) rotate({a})"))
    b.append(el("polygon", points=pts([(x + 6, y + 7) for x, y in (top, right, bottom, left)]), fill="#1D2A44", opacity=0.2))  # sombra de papel
    for tri, color in quads:
        b.append(el("polygon", points=pts(tri), fill=color))
    b.append(line(*top, *bottom, "#FFFFFF", 2.5, opacity=0.8))
    b.append(line(*left, *right, "#FFFFFF", 2.5, opacity=0.8))
    for x in (130, 170):
        b.append(circle(x + 2, 98, 13, "#1D2A44", opacity=0.2))
        b.append(circle(x, 96, 13, "#FFFFFF"))
        b.append(circle(x + 3, 98, 6, "#1D2A44"))
    b.append(path("M134 124 Q150 142 166 124Z", "#FFFFFF"))
    b.append(circle(116, 120, 7, "#FFFFFF", opacity=0.55))
    b.append(circle(184, 120, 7, "#FFFFFF", opacity=0.55))
    b.append(line(150, 22, 150, 6, "#5A4A42", 3))
    b.append(circle(150, 6, 5, "#FFC93C"))
    return b


CONCEPTS = (
    ("1 · Papa", "Pegatina kawaii", "#FFF1D6", papa, [
        "Una papa que se fue a órbita: el cultivo de Boyacá vuelto personaje.",
        "Contorno grueso y ojos brillantes, como una calcomanía. La más tierna.",
        "Riesgo: se lee como comida antes que como satélite.",
    ]),
    ("2 · Chía", "Constelación", "#0F1B2D", chia, [
        "Chía, la luna de los muiscas: una constelación con forma de satélite.",
        "Solo puntos y líneas de luz. Se anima uniendo estrellas una a una.",
        "Riesgo: solo vive sobre fondos oscuros; de día pierde fuerza.",
    ]),
    ("3 · Bit", "Pixel art", "#2B1B4A", bit, [
        "Un satélite de videojuego de 16 píxeles: el lado «juego» de AgroSense.",
        "Se anima por cuadros, barato y con mucho carácter.",
        "Riesgo: el píxel choca con el paisaje low-poly de la escena.",
    ]),
    ("4 · Tunjo", "Orfebrería en oro", "#0E3B36", tunjo, [
        "Inspirado en la orfebrería muisca del altiplano: figura plana de oro,",
        "con tocado de rayos (el plato) y dos escudos (los paneles).",
        "Riesgo: es patrimonio; pide respeto y asesoría. La menos «tierna».",
    ]),
    ("5 · Gota", "Burbuja brillante", "#DDF5F3", gota, [
        "Una gota de agua con un anillo que la orbita: el plan de riego.",
        "Degradados y brillo, como las mascotas de las apps actuales.",
        "Riesgo: habla solo del agua, no del clima ni del mercado.",
    ]),
    ("6 · Sputnik", "Caricatura de los 60", "#F4E9D0", sputnik, [
        "El primer satélite, dibujado como caricatura antigua: ojos de pastel,",
        "brazos de manguera que saludan y señalan. La más expresiva.",
        "Riesgo: recuerda a caricaturas clásicas conocidas.",
    ]),
    ("7 · Lana", "Tejido a mano", "#F7E6DC", lana, [
        "Una oveja-nube con ruana, agujas por antenas y un ovillo que la orbita:",
        "la lana de Boyacá y las nubes de lluvia en un solo personaje.",
        "Riesgo: mucho detalle; a 48 px hay que simplificarla.",
    ]),
    ("8 · Paja", "Garabato a crayón", "#FDFBF2", paja, [
        "El espantapájaros que cuida el lote, con un sombrero que es la antena.",
        "Trazo de crayón que se sale de la línea: cercano, hecho a mano.",
        "Riesgo: no vuela; guiaría el descenso desde abajo, no desde el cielo.",
    ]),
    ("9 · Cometa", "Papel recortado", "#BFE4FF", cometa, [
        "Una cometa como las de agosto en Villa de Leyva, que subió hasta",
        "volverse satélite. Capas de papel de colores con su sombra.",
        "Riesgo: «cometa» también es el astro; puede confundir.",
    ]),
)


def cell(name, style, bg, draw, notes):
    b = [poly(chamfer(32, 92, 696, 380, 16), bg)]
    b.append(f'<g transform="translate({32 + 348 - W * 0.75:g} {92 + 4:g}) scale(1.5)">{"".join(draw())}</g>')
    b.append(poly(chamfer(32, 484, 74, 74, 10), bg))
    b.append(f'<g transform="translate({32 + 37 - 48 * W / H / 2:g} {484 + 13:g}) scale({48 / H:g})">{"".join(draw())}</g>')
    b.append(text(122, 504, style, 18, 700))
    b += lines(122, 528, notes, 15, 21)
    return b


def sheet():
    SW, SH = 2400, 2220
    b = [f"<defs>{GOTA_DEFS}</defs>", f'<rect width="{SW}" height="{SH}" fill="{P["cielo"]}"/>']
    b += ridges(SW, 2090, 130)
    b.append(text(40, 84, "Mascota · nueve conceptos, nueve estilos", 48, 600, font=FONT_TITLE))
    b.append(text(40, 122, "HU-171, segunda ronda · Cada mascota parte de una idea y se dibuja con su propio lenguaje, fuera del kit y de su paleta. A la izquierda de cada texto, la mascota a 48 px.", 18))
    for i, (name, style, bg, draw, notes) in enumerate(CONCEPTS):
        b.append(section(40 + (i % 3) * 780, 150 + (i // 3) * 640, 760, 610, name, cell(name, style, bg, draw, notes)))
    return svg(SW, SH, b)


if __name__ == "__main__":
    out = DIR / "conceptos-estilos.svg"
    out.write_text(sheet(), encoding="utf-8", newline="\n")
    print(f"Escrito {out.name} ({out.stat().st_size // 1024} KB)")
