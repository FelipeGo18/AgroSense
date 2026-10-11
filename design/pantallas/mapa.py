"""Mapa de las pantallas finales y orden en que se diseñan. Escribe svg/00-mapa-de-pantallas.svg.

    python design/pantallas/mapa.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ui import BORDE, D, DIR, FONT_TITLE, P, SEC, WHITE, chamfer, group, poly, svg, text  # noqa: E402

DONE, NEXT, TODO, REVIEW = "hecha", "sigue", "pendiente", "revisar"
R = "rediseño"  # el rediseño por ventanas de siembra (11 de octubre de 2026), en siete tandas

# (parte, quién la ve, [(pantalla, tanda, estado)]). La tanda es un número o «rediseño N».
PARTS = (
    ("A · Inicio", "Todos", [("Portada", f"{R} 7", DONE)]),
    ("B · Descenso", "Invitado y usuario nuevo", [("Buscar mi municipio", 2, REVIEW), ("Dibujar mi lote y su riego", f"{R} 4", DONE)]),
    ("C · Consulta", "Todos", [("Elegir cultivo, fecha y riego", f"{R} 1", DONE), ("Resultado: una o dos luces", f"{R} 1", DONE),
                               ("Ajustar prioridades", f"{R} 1", DONE), ("Rojo, no evaluable, no apto", f"{R} 2", DONE),
                               ("Las seis señales y gráficas", f"{R} 2", DONE), ("Qué sembrar después", f"{R} 6", DONE), ("Calendario sin cuenta", f"{R} 3", DONE)]),
    ("D · Mi finca", "Con cuenta", [("Mis lotes en el mapa", f"{R} 4", DONE), ("Lote vivo y paso del tiempo", f"{R} 4", DONE), ("Editar y borrar lote", f"{R} 4", DONE),
                                    ("Lote · calendario", f"{R} 3", DONE), ("Lote · próxima siembra", f"{R} 6", DONE), ("Lote · agua", f"{R} 7", DONE),
                                    ("Lote · historial y progreso", f"{R} 5", DONE), ("Finca temporal (sin cuenta)", 8, DONE)]),
    ("E · Agregar", "Con cuenta", [("Agregar lote o zona", 8, DONE), ("Registrar cosecha y siembra", f"{R} 5", DONE)]),
    ("F · Cuenta", "Todos", [("Iniciar sesión", 1, DONE), ("Crear cuenta · consentim. 3", f"{R} 7", DONE), ("Mi cuenta y sus prioridades", f"{R} 7", DONE),
                             ("Confirmar borrado", 1, DONE), ("Editar datos y contraseña", 1, DONE), ("Mi actividad", 8, DONE), ("Guardar la finca temporal", 8, DONE)]),
    ("G · Transversal", "Todos", [("¿Cómo funciona y de dónde sale?", 9, DONE), ("Estados: carga, vacío, error", 9, DONE),
                                  ("Menú en móvil", 9, DONE), ("Modo ligero del lote", 9, DONE), ("Reportar un problema (P1)", 9, DONE)]),
    ("H · Administrador", "Rol admin · P1", [("Usuarios", 10, TODO), ("Ficha del agricultor", 10, TODO), ("Tickets", 10, TODO), ("Bitácora", 10, TODO), ("Métricas", 10, TODO)]),
    ("I · Catálogo visual", "Para Mi finca", [("Cultivos 1 · piloto", 5, DONE), ("Cultivos 2 · árboles frutales", 5, DONE), ("Cultivos 3 · musáceas y vides", 5, DONE),
                                              ("Cultivos 4 · raíces y hojas", 5, DONE), ("Cultivos 5 · más hortalizas", 5, DONE), ("Cultivos 6 · frutas andinas", 5, DONE),
                                              ("Cultivos 7 · permanentes", 5, DONE), ("Cultivos 8 · aromáticas y más", 5, DONE), ("Estados del ambiente", 6, DONE)]),
)

STYLE = {DONE: (P["brote"], D["brote"], P["noche"]), NEXT: (P["trigo"], D["trigo"], P["noche"]), TODO: (WHITE, BORDE, SEC),
         REVIEW: (WHITE, P["calabaza"], D["calabaza"])}


def chip(x, y, state, tanda):
    fill, stroke, ink = STYLE[state]
    label = f"{tanda} · {state}" if isinstance(tanda, str) else f"tanda {tanda} · {state}"
    return [poly(chamfer(x - 20, y, 170, 30, 6), fill, stroke, 2.5 if state == REVIEW else 2), text(x + 65, y + 21, label, 13, 700, ink, anchor="middle")]


def sheet():
    w, h = 1440, 1580
    b = [f'<rect width="{w}" height="{h}" fill="{P["niebla"]}"/>',
         text(48, 76, "Mapa de pantallas finales", 44, 600, font=FONT_TITLE),
         text(48, 112, f"{sum(len(screens) for _, _, screens in PARTS)} pantallas y láminas; las pantallas, en escritorio y en móvil. Se diseñan por tandas; cada tanda se aprueba en Figma antes de pasar a código.", 18)]
    cols = (PARTS[:3] + PARTS[8:], PARTS[3:5] + PARTS[7:8], PARTS[5:7])
    bottom = 0
    for ci, col in enumerate(cols):
        x, y = 48 + ci * 456, 150
        for part, who, screens in col:
            ph = 78 + len(screens) * 44
            body = [poly(chamfer(0, 8, 432, ph, 16), BORDE), poly(chamfer(0, 0, 432, ph, 16), WHITE),
                    text(24, 40, part, 24, 600, font=FONT_TITLE), text(408, 40, who, 14, fill=SEC, anchor="end")]
            for i, (name, tanda, state) in enumerate(screens):
                ry = 62 + i * 44
                body += [text(24, ry + 22, name if len(name) < 32 else name[:30] + "…", 15, 700 if state != TODO else 400)] + chip(258, ry, state, tanda)
            b.append(group(part.split(" · ")[1].lower().replace(" ", "-"), body, x, y))
            y += ph + 32
        bottom = max(bottom, y)
    order = ["Orden: tandas 1 a 9 (hechas) y rediseño por ventanas de siembra, del 1 al 7 (hecho)",
             "→ 10 Administrador (P1). «Revisar»: hecha, pero depende de algo por confirmar (Buscar mi municipio: la región, hasta el 28 de octubre).",
             "Seis señales por ventana de siembra: agua, heladas, calor, suelo, oferta y mercado. El lote vivo usa el catálogo de cultivos y el clima de ahora.",
             "Nombres y cifras de muestra."]
    for i, line in enumerate(order):
        b.append(text(48, bottom + 20 + i * 26, line, 16, fill=SEC))
    return svg(w, h, b)


if __name__ == "__main__":
    out = DIR / "svg" / "00-mapa-de-pantallas.svg"
    out.write_text(sheet(), encoding="utf-8", newline="\n")
    print(out.name)
