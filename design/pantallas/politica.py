"""Tanda 11 · «Política de tratamiento de datos» (HU-163, R9). Escritorio y móvil.

La página a la que llevan el consentimiento de «Crear cuenta», «Lo que guardamos de usted» de Mi cuenta y el pie.
Dice, en español claro, lo mismo que el consentimiento versión 3 con más detalle: qué se guarda, qué no, para qué,
quién lo ve, cuánto tiempo y cómo borrarlo. Se puede leer sin cuenta.

Cada frase sale de las specs (R9 de `specs/01-reglas.md`, HU-160 a HU-165, HU-170, HU-178, HU-200 y
`specs/02-contratos.md`): aquí no se promete nada que el sistema no haga. Por confirmar antes de publicar, y por eso
rotulado para el equipo: la revisión legal del texto (Ley 1581 de 2012 de Colombia, decisión 11), el canal de
contacto del responsable y qué pasa con una cuenta que aceptó una versión anterior.

    python design/pantallas/politica.py     # escribe svg/transversal-06-politica-de-datos-*.svg
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ui  # noqa: E402
import muestra  # noqa: E402
from cuenta import wrap  # noqa: E402
from ui import BORDE, D, DIR, FONT_TITLE, MOBILE, P, SEC, WHITE, card, chamfer, group, link, mascot, paragraph, poly, text, topbar  # noqa: E402

VERSION = muestra.CONSENT_VERSION
SINCE = "11 de octubre de 2026"

# (título, [(marca, frase)]). Marca: «si» se guarda o se hace, «no» nunca, «» es texto corrido.
SECTIONS = (
    ("Qué guardamos cuando tiene cuenta", [
        ("si", "Su usuario, el nombre con que quiere que lo llamemos y sus prioridades."),
        ("si", "Sus lotes: el nombre, el contorno que dibujó en el mapa, su área y si tienen riego."),
        ("si", "Sus siembras y cosechas, con el diagnóstico que vio al sembrar."),
        ("si", "Sus sesiones abiertas, para que pueda entrar desde varios dispositivos."),
        ("si", "La actividad de su cuenta durante 180 días: qué se hizo y cuándo, no lo que escribió."),
        ("si", "Los reportes que nos escriba."),
    ]),
    ("Qué no guardamos", [
        ("no", "Correo, celular, documento ni dirección. No los pedimos."),
        ("no", "Su contraseña: se guarda una huella que no se puede leer. Por eso no se puede recuperar."),
        ("no", "Lo que consulta sin cuenta: se envía solo para calcular y no queda guardado."),
        ("no", "Quién hizo cada consulta. Solo se cuenta cuántas hubo por día, municipio y cultivo."),
    ]),
    ("Para qué los usamos", [
        ("", "Para mostrarle su finca y para que las estrategias de rotación usen su historial real."),
        ("", "Lo que siembra se suma, sin su nombre, a los totales de su municipio. Esos totales solo se muestran cuando hay al menos 5 cuentas."),
        ("", "No se usan para nada más."),
    ]),
    ("Quién puede verlos", [
        ("", "Usted, con su usuario y su contraseña."),
        ("", "Soporte puede ver sus lotes para ayudarle. Cada vez que lo hace queda escrito en «Mi actividad», donde usted lo puede ver."),
    ]),
    ("Cuánto tiempo y cómo borrarlos", [
        ("", "Se guardan mientras tenga la cuenta. La actividad se borra sola a los 180 días."),
        ("", "En «Mi cuenta» puede ver lo que guardamos, cambiar su nombre y su usuario, y borrar su cuenta."),
        ("", "Borrar la cuenta lo borra todo: usuario, sesiones, lotes, siembras, reportes y actividad. No se puede deshacer."),
    ]),
    ("En su navegador", [
        ("", "Una sola cookie, la de su sesión. No hay cookies de publicidad ni de seguimiento."),
        ("", "El modo ligero, el sonido y, sin cuenta, sus prioridades se recuerdan en este dispositivo y no salen de él."),
    ]),
)

# Lo que falta decidir: se rotula para el equipo y en la app no se dibuja.
TEAM_NOTE = ("Borrador para el equipo: falta la revisión legal (Ley 1581 de 2012), el canal de contacto del responsable",
             "y qué pasa con quien aceptó una versión anterior. Este recuadro no se dibuja en la app.")


def mark(kind, x, y):
    """Visto bueno o equis junto a cada frase: lo que se guarda y lo que no se distinguen por forma, no solo por color."""
    if kind == "si":
        return [poly(chamfer(x, y - 16, 20, 20, 4), "#E9F2D8", D["oliva"], 2),
                f'<polyline points="{x + 4},{y - 6} {x + 8},{y - 1} {x + 16},{y - 11}" fill="none" stroke="{D["oliva"]}" stroke-width="2.5" stroke-linecap="round"/>']
    if kind == "no":
        return [poly([(x, y - 16), (x + 20, y - 16), (x + 20, y + 4), (x, y + 4)], "#FBE6E2", D["rojo"], 2),
                f'<path d="M{x + 5} {y - 11} l10 10 M{x + 15} {y - 11} l-10 10" stroke="{D["rojo"]}" stroke-width="2.5" stroke-linecap="round"/>']
    return [poly([(x + 6, y - 12), (x + 14, y - 6), (x + 6, y)], P["calabaza"])]


def policy(mobile=False):
    w = MOBILE[0] if mobile else 1440
    pad = 12 if mobile else 96
    cw = w - 2 * pad if mobile else 880
    inner = 22 if mobile else 40
    size, line, limit = (16, 23, 34) if mobile else (18, 27, 86)
    c, y = [], 0
    for title, items in SECTIONS:
        rows = wrap(title, 26 if mobile else 60)
        c += paragraph(inner, y + 48, rows, 22 if mobile else 26, 30, weight=600, font=FONT_TITLE)
        y += 48 + (len(rows) - 1) * 30 + 34
        for kind, sentence in items:
            c += mark(kind, inner, y)
            lines = wrap(sentence, limit)
            c += paragraph(inner + 34, y, lines, size, line)
            y += len(lines) * line + 12
        y += 6
        if title != SECTIONS[-1][0]:
            c.append(f'<rect x="{inner}" y="{y + 6}" width="{cw - 2 * inner}" height="2" fill="{P["niebla"]}"/>')
    ch = y + 30
    top = 150 if mobile else 180
    b = [f'<rect width="{w}" height="9000" fill="{P["niebla"]}"/>'] + topbar(w)
    title_rows = ["Política de", "tratamiento de datos"] if mobile else ["Política de tratamiento de datos"]
    b += paragraph(pad, top, title_rows, 30 if mobile else 48, 38, weight=600, font=FONT_TITLE)
    y0 = top + (len(title_rows) - 1) * 38 + (34 if mobile else 44)
    b.append(text(pad, y0, f"Versión {VERSION} · vigente desde el {SINCE}", 15 if mobile else 18, fill=SEC))
    intro = (["Lo que guardamos de usted, para qué y cómo", "borrarlo. Sin cuenta no se guarda nada", "de su finca."] if mobile else
             ["Lo que guardamos de usted, para qué y cómo borrarlo. Sin cuenta no se guarda nada de su finca."])
    b += paragraph(pad, y0 + 34, intro, 16 if mobile else 18, 24)
    if not mobile:
        b += mascot(1060, 150, 0.9, "guia")
    y1 = y0 + 34 + len(intro) * 24 + 16
    b += card(pad, y1, cw, ch, c=16) + [group("contenido", c, pad, y1)]
    # Quién responde y a dónde volver.
    y2 = y1 + ch + 36
    b += paragraph(pad, y2, ["Responde por estos datos el equipo RealE4Life,", "que hace AgroSense."] if mobile else ["Responde por estos datos el equipo RealE4Life, que hace AgroSense."], 16 if mobile else 18, 24)
    y2 += (2 if mobile else 1) * 24 + 14
    b += link(pad, y2, "Ir a Mi cuenta", 17)
    b += link(pad + (150 if mobile else 170), y2, "Crear cuenta", 17)
    y2 += 40
    nw = cw
    note_rows = wrap(" ".join(TEAM_NOTE), 44) if mobile else list(TEAM_NOTE)
    nh = 24 + len(note_rows) * 20
    b.append(group("nota-equipo", [poly(chamfer(1, 1, nw - 2, nh, 10), WHITE, D["cielo"], 2, "6 5"), *paragraph(16, 28, note_rows, 14, 20, fill=D["cielo"])], pad, y2))
    return ui.long_page((w, y2 + nh + 50), b, P["niebla"])


SCREENS = {
    "transversal-06-politica-de-datos-escritorio": policy,
    "transversal-06-politica-de-datos-movil": lambda: policy(mobile=True),
}

if __name__ == "__main__":
    out = DIR / "svg"
    for name, draw in SCREENS.items():
        (out / f"{name}.svg").write_text(draw(), encoding="utf-8", newline="\n")
        print(name)
