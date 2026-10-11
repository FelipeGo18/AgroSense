"""Mapa de las pantallas finales y orden en que se diseñan. Escribe svg/00-mapa-de-pantallas.svg.

    python design/pantallas/mapa.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ui import BORDE, D, DIR, FONT_TITLE, P, SEC, WHITE, chamfer, group, poly, svg, text  # noqa: E402

DONE, NEXT, TODO = "hecha", "sigue", "pendiente"

# (parte, quién la ve, [(pantalla, tanda, estado)])
PARTS = (
    ("A · Inicio", "Todos", [("Portada", 2, DONE)]),
    ("B · Descenso", "Invitado y usuario nuevo", [("Buscar mi municipio", 2, DONE), ("Dibujar mi lote en el mapa", 2, DONE)]),
    ("C · Consulta", "Todos", [("Elegir cultivo y semestre", 3, DONE), ("Resultado del diagnóstico", 3, DONE), ("Las cinco señales y gráficas", 3, DONE),
                               ("Qué sembrar después", 4, DONE)]),
    ("D · Mi finca", "Con cuenta", [("Mis lotes en el mapa", 7, NEXT), ("Lote vivo y paso del tiempo", 7, NEXT), ("Lote · calendario", 7, NEXT),
                                    ("Lote · próxima siembra", 7, NEXT), ("Lote · agua", 7, NEXT), ("Lote · historial y progreso", 8, TODO),
                                    ("Finca temporal (sin cuenta)", 8, TODO)]),
    ("E · Agregar", "Con cuenta", [("Agregar lote o zona", 8, TODO), ("Registrar cosecha y siembra", 8, TODO)]),
    ("F · Cuenta", "Todos", [("Iniciar sesión", 1, DONE), ("Crear cuenta", 1, DONE), ("Mi cuenta", 1, DONE), ("Confirmar borrado", 1, DONE), ("Editar datos y contraseña", 1, DONE), ("Mi actividad", 8, TODO),
                             ("Guardar la finca temporal", 8, TODO)]),
    ("G · Transversal", "Todos", [("¿Cómo funciona y de dónde sale esto?", 9, TODO), ("Estados: cargando, vacío, sin cobertura, error", 9, TODO),
                                  ("Menú en móvil", 9, TODO), ("Modo ligero", 9, TODO), ("Reportar un problema", 9, TODO)]),
    ("H · Administrador", "Rol admin · P1", [("Usuarios", 10, TODO), ("Ficha del agricultor", 10, TODO), ("Tickets", 10, TODO), ("Bitácora", 10, TODO), ("Métricas", 10, TODO)]),
    ("I · Catálogo visual", "Para Mi finca", [("Cultivos 1 · piloto", 5, DONE), ("Cultivos 2 · árboles frutales", 5, DONE), ("Cultivos 3 · musáceas y vides", 5, DONE),
                                              ("Cultivos 4 · raíces y hojas", 5, DONE), ("Cultivos 5 · más hortalizas", 5, DONE), ("Cultivos 6 · frutas andinas", 5, DONE),
                                              ("Cultivos 7 · permanentes", 5, DONE), ("Cultivos 8 · aromáticas y más", 5, DONE), ("Estados del ambiente", 6, DONE)]),
)

STYLE = {DONE: (P["brote"], D["brote"], P["noche"]), NEXT: (P["trigo"], D["trigo"], P["noche"]), TODO: (WHITE, BORDE, SEC)}


def chip(x, y, state, tanda):
    fill, stroke, ink = STYLE[state]
    return [poly(chamfer(x, y, 150, 30, 6), fill, stroke, 2), text(x + 75, y + 21, f"tanda {tanda} · {state}", 14, 700, ink, anchor="middle")]


def sheet():
    w, h = 1440, 1420
    b = [f'<rect width="{w}" height="{h}" fill="{P["niebla"]}"/>',
         text(48, 76, "Mapa de pantallas finales", 44, 600, font=FONT_TITLE),
         text(48, 112, "36 pantallas y láminas; las pantallas, en escritorio y en móvil. Se diseñan por tandas; cada tanda se aprueba en Figma antes de pasar a código.", 18)]
    cols = (PARTS[:3] + PARTS[8:], PARTS[3:5] + PARTS[7:8], PARTS[5:7])
    for ci, col in enumerate(cols):
        x, y = 48 + ci * 456, 150
        for part, who, screens in col:
            ph = 78 + len(screens) * 44
            body = [poly(chamfer(0, 8, 432, ph, 16), BORDE), poly(chamfer(0, 0, 432, ph, 16), WHITE),
                    text(24, 40, part, 24, 600, font=FONT_TITLE), text(408, 40, who, 14, fill=SEC, anchor="end")]
            for i, (name, tanda, state) in enumerate(screens):
                ry = 62 + i * 44
                body += [text(24, ry + 22, name if len(name) < 30 else name[:28] + "…", 16, 700 if state != TODO else 400)] + chip(258, ry, state, tanda)
            b.append(group(part.split(" · ")[1].lower().replace(" ", "-"), body, x, y))
            y += ph + 32
    order = ["Orden: 1 Cuenta, 2 Portada y descenso, 3 Diagnóstico, 4 Rotaciones y 5 Catálogo de 46 cultivos y 6 Estados del ambiente (hechas)",
             "→ 7 Mi finca: mapa, lote vivo, calendario, agua y próxima siembra → 8 Historial, agregar, finca temporal y Mi actividad → 9 Transversal → 10 Administrador (P1).",
             "Señales: lluvia, heladas, suelo, oferta y mercado. El lote vivo usa el catálogo de cultivos y el clima de ahora. Nombres y cifras de muestra."]
    for i, line in enumerate(order):
        b.append(text(48, 1310 + i * 26, line, 16, fill=SEC))
    return svg(w, h, b)


if __name__ == "__main__":
    out = DIR / "svg" / "00-mapa-de-pantallas.svg"
    out.write_text(sheet(), encoding="utf-8", newline="\n")
    print(out.name)
