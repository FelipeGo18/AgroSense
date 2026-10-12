"""Guiones de recorrido: fondos, mascota y un esbozo de interfaz por parada.

Sigue el método de motion de specs/05-frontend.md: por cada toma, qué se ve y cómo se pasa a la siguiente.
Escribe dos láminas para Figma:
  recorrido-a.svg     el descenso del satélite al lote, en siete paradas
  recorridos-b-c.svg  dos alternativas: el año del cultivo y la travesía por la cordillera

    python design/paisaje/storyboard.py
"""

import sys
from pathlib import Path

DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(DIR))
sys.path.insert(0, str(DIR.parent / "kit"))
sys.path.insert(0, str(DIR.parent / "mascota"))

from build_paisaje import H, SCENES, W  # noqa: E402
from build_kit_svg import BORDE, P, PIECES, WHITE, chamfer, poly, svg  # noqa: E402
from semilla_sputnik import seed_mascot  # noqa: E402
from sheet import FONT_TITLE, SEC, at, lines, ridges, section, text  # noqa: E402


def inner(markup):
    return markup[markup.index(">") + 1 : markup.rindex("</svg>")]


def mascot(x, y, scale, mood, seed="germinada"):
    return f'<g transform="translate({x:g} {y:g}) scale({scale:g})">{"".join(seed_mascot(mood, seed))}</g>'


def card(x, y, w, h):
    """Panel de interfaz sobre la escena: el dato va en HTML, encima del paisaje."""
    return [poly(chamfer(x, y + 8, w, h, 16), BORDE), poly(chamfer(x, y, w, h, 16), WHITE)]


def button(x, y, label, piece="boton-primario", ink=WHITE):
    return [at(x, y, PIECES[piece]), text(x + 120, y + 33, label, 18, 700, ink, anchor="middle")]


def caption(label):
    """Rótulo de una parada de tránsito: no tiene interfaz, solo se atraviesa."""
    w = 30 + len(label) * 15
    return card(60, 60, w, 64) + [text(84, 102, label, 26, 600, font=FONT_TITLE)]


def shot(name, overlay, x, y, width):
    """Una toma recortada a su marco. `overlay` se dibuja en coordenadas de la escena (1440 × 900)."""
    s = width / W
    fh = H * s
    scene = f'<g transform="scale({s:g})">{inner(SCENES[name]())}{"".join(overlay)}</g>'
    frame = poly(chamfer(-3, -3, width + 6, fh + 6, 0), "none", P["noche"], 6)
    clip = f'<defs><clipPath id="recorte-{name}"><rect width="{width}" height="{fh:g}"/></clipPath></defs>'
    return f'{clip}<g transform="translate({x} {y})"><g clip-path="url(#recorte-{name})">{scene}</g>{frame}</g>'


# ---------- Recorrido A ----------

def a_orbita():
    b = [text(70, 150, "AgroSense", 84, 600, WHITE, FONT_TITLE)]
    b += lines(72, 204, ["¿Es buen semestre para sembrar?", "Se lo decimos con datos del satélite", "y reglas que se pueden explicar."], 26, 36, fill=WHITE)
    b += button(72, 330, "Consultar sin cuenta") + button(330, 330, "Entrar", "boton-secundario", P["noche"])
    return b + [mascot(700, 110, 1.5, "guia")]


def a_region():
    b = card(60, 60, 470, 230)
    b += [text(88, 112, "¿Dónde está su finca?", 32, 600, font=FONT_TITLE), text(88, 148, "Municipio", 18, 700)]
    b += [at(88, 160, PIECES["campo-foco"].replace('width="504"', 'width="418"')), text(108, 194, "Sama", 18)]
    return b + [mascot(700, 60, 1.25, "vuelo")]


def a_municipio():
    b = card(60, 60, 430, 250)
    b += [text(88, 112, "Samacá, Boyacá", 32, 600, font=FONT_TITLE), text(88, 146, "Elija cultivo y semestre", 18, fill=SEC)]
    b += button(88, 168, "Papa · semestre B", "boton-secundario", P["noche"]) + button(88, 238, "Ver diagnóstico")
    return b + [mascot(560, 200, 1.05, "guia")]


def a_lote():
    b = card(60, 50, 520, 330)
    b += [text(88, 100, "Papa en Samacá · semestre B", 26, 600, font=FONT_TITLE)]
    b += [at(88, 122, PIECES["semaforo-amarillo"]), text(88 + 51, 160, "Amarillo · Con cuidado", 18, 700)]
    b += lines(88, 244, ["Sugerencia: esperar otro semestre.", "El clima acompaña, pero hay más área", "sembrada que en años anteriores."], 18, 26)
    b += [at(88, 318, PIECES["rotulo-ejemplo"]), text(118, 345, "EJEMPLO", 16, 700), text(202, 345, "· datos ficticios", 16)]
    return b + [mascot(700, 300, 1.15, "reposo")]


ROUTE_A = (
    ("1 · Órbita — inicio", "a1-orbita", a_orbita, [
        "La Tierra de noche, con un punto naranja sobre el altiplano. La mascota presenta AgroSense.",
        "Sale: la palabra «AgroSense» se abre como máscara y la Tierra crece hasta llenar la pantalla.",
    ]),
    ("2 · Atmósfera — tránsito", "a2-atmosfera", lambda: caption("Entrando a la atmósfera") + [mascot(560, 250, 1.3, "vuelo")], [
        "Capas de nubes que suben a distinta velocidad; el cielo pasa de noche a día. Sin interfaz.",
        "Es el momento para el video atado al scroll, si se usa. Sale: las nubes se abren.",
    ]),
    ("3 · Región — buscar el municipio", "a3-region", a_region, [
        "La cordillera desde lo alto, con niebla en los valles. Aparece el buscador de municipio.",
        "Sale: al elegir municipio, la cámara baja entre los cerros.",
    ]),
    ("4 · Valle — tránsito", "a4-valle", lambda: caption("Bajando a Samacá") + [mascot(640, 150, 1.2, "vuelo")], [
        "Dos laderas enmarcan el valle; al fondo, el río y las primeras parcelas. Sin interfaz.",
        "Sale: las laderas se abren hacia los lados y el mosaico de parcelas ocupa la pantalla.",
    ]),
    ("5 · Municipio — elegir cultivo", "a5-municipio", a_municipio, [
        "El mosaico de parcelas y el pueblo. Una parcela queda resaltada: su zona.",
        "Sale: la parcela resaltada crece; nos acercamos a la vereda.",
    ]),
    ("6 · Vereda — tránsito", "a6-vereda", lambda: caption("Llegando a su lote") + [mascot(520, 230, 1.2, "guia")], [
        "Parcelas grandes, la casa, el camino y los árboles. El lote resaltado ya se ve de cerca.",
        "Con cuenta, aquí se marca el primer lote. Sale: el borde naranja se vuelve el suelo.",
    ]),
    ("7 · Lote — el resultado", "a7-lote", a_lote, [
        "El lote a ras de suelo, con surcos y brotes. La mascota espera junto al resultado.",
        "Fin del descenso. Quien vuelve con sesión entra directo a esta altura, en Mi finca.",
    ]),
)


def sheet_a():
    SW, SH = 2400, 2240
    fw = 708
    fh = H * fw / W
    b = [f'<rect width="{SW}" height="{SH}" fill="{P["cielo"]}"/>']
    b += ridges(SW, 2110, 130)
    b.append(text(40, 84, "Recorrido A · del satélite al lote", 48, 600, font=FONT_TITLE))
    b.append(text(40, 122, "HU-155 · Aprobado. Siete paradas: cuatro con interfaz y tres de tránsito, para que el scroll fluya sin saltos. La interfaz dibujada es un esbozo; las pantallas se diseñan después.", 18))
    for i, (title, name, overlay, notes) in enumerate(ROUTE_A):
        body = [shot(name, overlay(), 32, 92, fw)] + lines(32, 92 + fh + 34, notes, 15, 22)
        b.append(section(40 + (i % 3) * 780, 150 + (i // 3) * 650, 772, 620, title, body))
    b.append(section(820, 1450, 1552, 620, "Cómo se mueve", lines(32, 104, [
        "Una sola línea de tiempo de GSAP, atada al scroll, recorre las siete paradas.",
        "",
        "· Las cuatro paradas con interfaz se fijan: la pantalla se queda quieta mientras el usuario elige.",
        "· Las tres de tránsito no se fijan: se atraviesan. Son las que dan la sensación de bajar.",
        "· En cada escena las capas (cielo, lejano, medio, niebla, cercano) se mueven a distinta velocidad.",
        "· Entre escenas siempre hay un objeto que pasa de una a la otra: el punto naranja de la órbita",
        "  es el mismo que resalta la parcela y que termina siendo el borde del lote.",
        "· La mascota viaja con el scroll: saluda, vuela, señala y espera. Sus raíces quedan atrás como estela.",
        "",
        "Técnicas por momento: máscara que se abre (1), video opcional o capas de nubes (2),",
        "sección fijada con paralaje (3, 5, 7), barrido lateral de laderas (4), acercamiento a la parcela (6).",
        "",
        "Peso: las siete escenas suman unos 116 KB (28 KB comprimidas). Con «reducir movimiento»,",
        "las paradas aparecen ya colocadas y las de tránsito se omiten.",
    ], 17, 27)))
    return svg(SW, SH, b)


# ---------- Recorridos B y C ----------

def label(texto, mood, mx=760, my=250, scale=1.5, seed="germinada"):
    return caption(texto) + [mascot(mx, my, scale, mood, seed)]


ROUTE_B = (
    ("b1-preparar", "1 · Preparar", lambda: label("Antes de sembrar", "reposo")),
    ("b2-sembrar", "2 · Sembrar", lambda: label("¿Es buen semestre?", "guia")),
    ("b3-crecer", "3 · Crecer", lambda: label("¿Cuánta agua?", "vuelo", 700, 180)),
    ("b4-cosechar", "4 · Cosechar", lambda: label("La cosecha", "celebra", 480, 240, 1.5, "maiz")),
    ("b5-rotar", "5 · Rotar", lambda: label("¿Qué sembrar después?", "guia", 780, 240, 1.5, "frijol")),
)

ROUTE_C = (
    ("c1-paramo", "1 · Páramo", lambda: label("Donde nace el agua", "reposo")),
    ("c2-ladera", "2 · Ladera", lambda: label("Bajando por el bosque", "vuelo", 520, 140)),
    ("a5-municipio", "3 · Mosaico", lambda: label("Las parcelas", "guia", 520, 150)),
    ("c4-pueblo", "4 · Pueblo", lambda: label("Su municipio", "guia", 330, 250, 1.3)),
    ("a6-vereda", "5 · Finca", lambda: label("Su lote", "celebra", 430, 250, 1.3)),
)


def route_row(shots, notes):
    fw = 440
    fh = H * fw / W
    b = []
    for i, (name, title, overlay) in enumerate(shots):
        x = 32 + i * 456
        b.append(shot(name, overlay(), x, 92, fw))
        b.append(text(x, 92 + fh + 30, title, 18, 700))
    b += lines(32, 92 + fh + 70, notes, 16, 25)
    return b


def sheet_bc():
    SW, SH = 2400, 1640
    b = [f'<rect width="{SW}" height="{SH}" fill="{P["cielo"]}"/>']
    b += ridges(SW, 1510, 130)
    b.append(text(40, 84, "Dos recorridos alternativos", 48, 600, font=FONT_TITLE))
    b.append(text(40, 122, "HU-155 · Otras dos formas de contar AgroSense con el scroll. Pueden reemplazar al descenso o convivir con él en otra sección de la web.", 18))
    b.append(section(40, 150, 2320, 640, "Recorrido B · El año del cultivo — el scroll avanza en el tiempo", route_row(ROUTE_B, [
        "La cámara no se mueve: se queda en el lote. Al bajar pasa el año: tierra preparada, siembra con lluvia, cultivo creciendo, cosecha y rotación. Cambian el cielo, la luz, el cultivo y la semilla de la mascota.",
        "A favor: cada parada es una de las tres preguntas de AgroSense (¿siembro ahora?, ¿cuánta agua?, ¿qué sigue?); es el más fácil de construir (una sola escena con cinco estados) y funciona igual en móvil.",
        "En contra: pierde el satélite y la sensación de viaje; no ubica el municipio. Sirve mejor para explicar la app en el inicio, o para Mi finca, que para llegar al lote.",
    ])))
    b.append(section(40, 830, 2320, 640, "Recorrido C · Travesía por la cordillera — el scroll avanza hacia un lado", route_row(ROUTE_C, [
        "Un paisaje panorámico que se recorre de lado, del páramo donde nace el agua a la finca: frailejones y laguna, bosque y quebrada, mosaico de parcelas, pueblo y lote. La mascota vuela a la altura de la vista.",
        "A favor: cuenta de dónde viene el agua, que es el tema del plan de riego, y tiene mucha identidad de altiplano. El movimiento lateral se siente distinto a casi todas las webs.",
        "En contra: el scroll horizontal es menos natural en móvil y hay que dibujar un panorama continuo (más trabajo). Tampoco muestra el satélite: habría que añadirlo como arranque.",
    ])))
    return svg(SW, SH, b)


if __name__ == "__main__":
    for name, draw in (("recorrido-a.svg", sheet_a), ("recorridos-b-c.svg", sheet_bc)):
        out = DIR / name
        out.write_text(draw(), encoding="utf-8", newline="\n")
        print(f"Escrito {out.name} ({out.stat().st_size // 1024} KB)")
