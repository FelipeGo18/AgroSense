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
                               ("Qué sembrar después", 4, NEXT)]),
    ("D · Mi finca", "Con cuenta", [("Mis lotes en el mapa", 5, TODO), ("Lote · ahora y su suelo", 5, TODO), ("Lote · calendario", 5, TODO), ("Lote · próxima siembra", 5, TODO), ("Lote · agua", 5, TODO),
                                    ("Lote · historial y progreso", 6, TODO), ("Finca temporal (sin cuenta)", 6, TODO)]),
    ("E · Agregar", "Con cuenta", [("Agregar lote o zona", 6, TODO), ("Registrar cosecha y siembra", 6, TODO)]),
    ("F · Cuenta", "Todos", [("Iniciar sesión", 1, DONE), ("Crear cuenta", 1, DONE), ("Mi cuenta", 1, DONE), ("Confirmar borrado", 1, DONE), ("Editar datos y contraseña", 1, DONE), ("Mi actividad", 6, TODO),
                             ("Guardar la finca temporal", 6, TODO)]),
    ("G · Transversal", "Todos", [("¿Cómo funciona y de dónde sale esto?", 7, TODO), ("Estados: cargando, vacío, sin cobertura, error", 7, TODO),
                                  ("Menú en móvil", 7, TODO), ("Modo ligero", 7, TODO), ("Reportar un problema", 7, TODO)]),
    ("H · Administrador", "Rol admin · P1", [("Usuarios", 8, TODO), ("Ficha del agricultor", 8, TODO), ("Tickets", 8, TODO), ("Bitácora", 8, TODO), ("Métricas", 8, TODO)]),
)

STYLE = {DONE: (P["brote"], D["brote"], P["noche"]), NEXT: (P["trigo"], D["trigo"], P["noche"]), TODO: (WHITE, BORDE, SEC)}


def chip(x, y, state, tanda):
    fill, stroke, ink = STYLE[state]
    return [poly(chamfer(x, y, 150, 30, 6), fill, stroke, 2), text(x + 75, y + 21, f"tanda {tanda} · {state}", 14, 700, ink, anchor="middle")]


def sheet():
    w, h = 1440, 1200
    b = [f'<rect width="{w}" height="{h}" fill="{P["niebla"]}"/>',
         text(48, 76, "Mapa de pantallas finales", 44, 600, font=FONT_TITLE),
         text(48, 112, "34 pantallas, cada una en escritorio y en móvil. Se diseñan por tandas; cada tanda se aprueba en Figma antes de pasar a código.", 18)]
    cols = (PARTS[:3], PARTS[3:5] + PARTS[7:], PARTS[5:7])
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
    order = ["Orden: 1 Cuenta, 2 Portada y descenso y 3 Diagnóstico (hechas) → 4 Rotaciones → 5 Mi finca, lote y agua → 6 Historial, agregar",
             "y finca temporal → 7 Transversal → 8 Administrador (P1). El lote se dibuja en un mapa real (HU-164).",
             "Señales: lluvia, heladas, suelo, oferta y mercado. El lote muestra su etapa (HU-150), su suelo (EP-18) y su calendario (HU-180). Nombres y cifras de muestra."]
    for i, line in enumerate(order):
        b.append(text(48, 1090 + i * 26, line, 16, fill=SEC))
    return svg(w, h, b)


if __name__ == "__main__":
    out = DIR / "svg" / "00-mapa-de-pantallas.svg"
    out.write_text(sheet(), encoding="utf-8", newline="\n")
    print(out.name)
