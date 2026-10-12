"""Lámina completa del kit para Figma: paneles, piezas y textos en su sitio (HU-153).

Se importa con la herramienta create_svg del plugin local; los <text> llegan a Figma
como capas de texto editables con su fuente.
"""

from build_kit_svg import D, LIGHTS, P, PIECES, STATUS, WHITE, panel, poly, shade, spinner, svg

FONT_TITLE = "Fredoka"
FONT_TEXT = "Atkinson Hyperlegible"
SEC = D["cielo"]


def inner(markup):
    """Contenido de un SVG sin su etiqueta exterior, para anidarlo con <g>."""
    return markup[markup.index(">") + 1 : markup.rindex("</svg>")]


def at(x, y, markup):
    return f'<g transform="translate({x:g} {y:g})">{inner(markup)}</g>'


def text(x, y, content, size=18, weight=400, fill=None, font=FONT_TEXT, anchor="start"):
    content = content.replace("&", "&amp;").replace("<", "&lt;")
    return (
        f'<text x="{x:g}" y="{y:g}" font-family="{font}" font-weight="{weight}" font-size="{size}" '
        f'fill="{fill or P["noche"]}" text-anchor="{anchor}">{content}</text>'
    )


def lines(x, y, rows, size=16, gap=24, **kw):
    return [text(x, y + i * gap, row, size, **kw) for i, row in enumerate(rows)]


def section(x, y, w, h, title, body):
    head = [inner(panel(w, h)), text(32, 56, title, 28, 600, font=FONT_TITLE)]
    return f'<g transform="translate({x} {y})">{"".join(head + body)}</g>'


def ridges(width, y, height):
    """Franja de cerros low-poly al pie de la lámina: el kit vive en el mismo paisaje."""
    out = []
    layers = ((0.0, shade(P["oliva"], 0.35), 7), (0.35, P["oliva"], 9), (0.62, P["brote"], 6), (0.84, P["tierra"], 11))
    for depth, color, n in layers:
        base = y + height * depth
        step = width / n
        for i in range(n):
            peak = base - height * (0.42 - depth * 0.3) * (0.55 + 0.45 * ((i * 7 + int(depth * 10)) % 5) / 4)
            x0, x1 = i * step, (i + 1) * step
            mid = x0 + step * (0.35 + 0.3 * ((i * 3) % 4) / 3)
            out.append(poly([(x0, base), (mid, peak), (mid, y + height), (x0, y + height)], shade(color, 0.07)))
            out.append(poly([(mid, peak), (x1, base), (x1, y + height), (mid, y + height)], shade(color, -0.08)))
    return out


def buttons():
    b = []

    def btn(x, y, piece, label, ink=WHITE, dy=0, pad=0, spin=False):
        b.append(at(x - pad, y - pad, PIECES[piece]))
        if spin:
            b.append(at(x + 50, y + 15 + dy, spinner(ink)))
            b.append(text(x + 82, y + 33 + dy, label, 18, 700, ink))
        else:
            b.append(text(x + 120, y + 33 + dy, label, 18, 700, ink, anchor="middle"))

    btn(32, 100, "boton-primario", "Ver diagnóstico")
    btn(300, 100, "boton-primario-presionado", "Ver diagnóstico", dy=5)
    btn(568, 100, "boton-primario-foco", "Ver diagnóstico", pad=6)
    btn(32, 240, "boton-deshabilitado", "Ver diagnóstico", ink=SEC, dy=6)
    btn(300, 240, "boton-primario", "Calculando…", spin=True)
    btn(568, 240, "boton-secundario", "Cambiar cultivo", ink=P["noche"])
    captions = (
        (32, 186, "Primario · normal"),
        (300, 186, "Presionado · el bloque se hunde"),
        (568, 186, "Foco · contorno noche de 3 px"),
        (32, 326, "Deshabilitado · plano, sin canto"),
        (300, 326, "Cargando · bloqueado"),
        (568, 326, "Secundario · trigo, texto noche"),
    )
    b += [text(x, y, t, 14, fill=SEC) for x, y, t in captions]
    b += lines(32, 388, [
        "Bloque de 52 px de alto (táctil ≥ 44) con canto inferior de 6 px. Al presionar baja 5 px.",
        "Enter y Espacio lo activan. Con «reducir movimiento» no se anima el hundimiento.",
    ])
    return b


def selector():
    caret = f'<rect x="64" y="138" width="2" height="24" fill="{P["noche"]}"/>'
    b = [
        text(32, 110, "Municipio · abierto, escribiendo «s»", 18, 700),
        at(32, 122, PIECES["campo-foco"]), text(52, 156, "s", 18), caret,
        at(32, 186, PIECES["lista-2"]),
        text(76, 226, "Samacá", 18, 700), text(506, 226, "Boyacá", 16, fill=SEC, anchor="end"),
        text(76, 278, "Sogamoso", 18), text(506, 278, "Boyacá", 16, fill=SEC, anchor="end"),
        text(608, 110, "Fuera del catálogo · sin resultados", 18, 700),
        at(608, 122, PIECES["campo-foco"]), text(628, 156, "Inventado", 18),
        at(608, 186, PIECES["lista-vacia"]), text(628, 226, "Sin resultados. Revise cómo lo escribió.", 18, fill=SEC),
        text(608, 296, "Cultivo · cargando", 18, 700),
        at(608, 308, PIECES["campo-normal"]), text(628, 342, "Escriba su cultivo", 18, fill=SEC), at(1070, 325, spinner(SEC)),
        text(608, 394, "Semestre · deshabilitado", 18, 700),
        at(608, 406, PIECES["campo-deshabilitado"]), text(628, 440, "Elija primero el cultivo", 18, fill=SEC),
    ]
    b += lines(32, 348, [
        "Busca sin tildes ni mayúsculas: «samaca» encuentra Samacá.",
        "Flechas para moverse, Enter para elegir, Escape para cerrar.",
        "Solo se elige del catálogo (W1): lo escrito a mano no vale.",
        "La semilla marca la opción activa; cada fila mide 52 px.",
    ])
    return b


def traffic_lights():
    labels = {
        "verde": "Verde · Buen momento",
        "amarillo": "Amarillo · Con cuidado",
        "rojo": "Rojo · Mejor no ahora",
        "no-evaluable": "No evaluable · Faltan datos",
        "cargando": "Calculando semáforo…",
    }
    spots = {"verde": (32, 96), "amarillo": (32, 212), "rojo": (32, 328), "no-evaluable": (400, 96), "cargando": (400, 212)}
    b = []
    for key, (x, y) in spots.items():
        st = LIGHTS[key]
        b.append(at(x, y, PIECES[f"semaforo-{key}"]))
        b.append(text(x + 3 + max(st["c"], 14) + 34, y + 38, labels[key], 18, 700, st["ink"]))
    b += lines(770, 116, [
        "Un letrero clavado en la parcela.",
        "Cada luz tiene silueta, ícono y texto:",
        "nunca solo color (W2).",
        "· Verde: puntas en octágono.",
        "· Amarillo: bisel suave y triángulo.",
        "· Rojo: esquinas rectas y cuadrado.",
        "· No evaluable: niebla, borde y estaca",
        "  a trazos. Nunca rojo (R1).",
        "No es interactivo: sin foco",
        "ni estado deshabilitado.",
    ])
    b += lines(400, 350, ["El resultado escrito va siempre", "en HTML, encima de la escena 3D."], fill=SEC)
    return b


def priorities():
    words = ["No importa", "Muy poco", "Poco", "Algo", "Mucho", "Lo más importante"]
    rows = (
        ("Agua", "que necesite poca agua", 3, "prioridad-3"),
        ("Suelo", "que cuide el suelo", 5, "prioridad-5-foco"),
        ("Ingreso", "que deje buen ingreso", 2, "prioridad-2"),
        ("Riesgo", "que tenga poco riesgo", 0, "prioridad-0"),
    )
    b = []
    for i, (name, hint, value, piece) in enumerate(rows):
        y = 96 + i * 72
        b += [
            text(32, y + 31, name, 20, 700),
            text(124, y + 31, hint, 16, fill=SEC),
            at(420, y, PIECES[piece]),
            text(444, y + 31, "0", 18, 700, anchor="middle"),
            text(750, y + 31, f"{value} · {words[value]}", 18, fill=SEC),
        ]
    b += lines(32, 404, [
        "Cinco semillas y un «0»: se toca la semilla, no se arrastra. Cada objetivo mide 44 px.",
        "Con teclado: flechas para subir o bajar. El número va siempre con su palabra.",
    ])
    b.append(text(32, 468, "▲ Si todo queda en 0: suba al menos una prioridad para poder comparar opciones.", 16, 700, D["rojo"]))
    return b


def signals():
    cards = (
        ("senal-clima-favorable", "Clima", "favorable", "Favorable", ["Lluvia del semestre dentro del rango favorable."]),
        ("senal-oferta-desfavorable", "Oferta · área sembrada", "desfavorable", "Desfavorable",
         ["Área sembrada mayor que el promedio de los", "tres semestres B anteriores."]),
        ("senal-mercado-insuficiente", "Mercado", "insuficiente", "Datos insuficientes", ["Sin datos de mercado para la zona."]),
        ("senal-clima-cargando", "Clima · cargando", None, None, []),
    )
    b = []
    for i, (piece, title, status, label, reasons) in enumerate(cards):
        x, y = 32 + i * 570, 92
        b.append(at(x, y, PIECES[piece]))
        b.append(text(x + 31, y + 55, title, 24, 600, font=FONT_TITLE))
        if status:
            if status == "insuficiente":
                b.append(text(x + 56, y + 118, "?", 20, 700, anchor="middle"))
            b.append(text(x + 78, y + 117, label, 18, 700, STATUS[status]["ink"]))
            b += lines(x + 31, y + 172, reasons, 16, 22)
    b.append(text(32, 398, "Letrero de campo sobre dos estacas. «Datos insuficientes» lleva bruma y borde punteado: nunca se pinta como riesgo (R1). Las razones citan solo lo que el motor evaluó (R5).", 16, fill=SEC))
    return b


def labels():
    return [
        at(32, 92, PIECES["rotulo-ejemplo"]), text(62, 119, "EJEMPLO", 16, 700), text(146, 119, "· datos ficticios", 16),
        at(380, 88, PIECES["rotulo-estimacion"]),
        text(430, 119, "Estimación con el clima de la zona. Verifique la humedad del suelo en su lote", 16),
        text(1190, 119, "«Ejemplo» acompaña todo dato ficticio (R5). La estimación va junto a todo resultado de riego, con texto fijo (R10).", 16, fill=SEC),
        text(32, 166, "Etiqueta colgante de vivero y gota facetada: los dos rótulos se reconocen por su silueta aunque no se lea el color.", 16, fill=SEC),
    ]


def sheet():
    W, H = 2400, 2020
    b = [f'<rect width="{W}" height="{H}" fill="{P["cielo"]}"/>']
    b += ridges(W, 1890, 130)
    b.append(text(40, 84, "Kit de componentes · AgroSense", 48, 600, font=FONT_TITLE))
    b.append(text(40, 122, "HU-153 · Estilo diorama low-poly: cada pieza es un bloque del mismo paisaje. Esquinas biseladas, caras trianguladas, luz desde la izquierda.", 18))
    b.append(section(40, 150, 1140, 480, "Botón", buttons()))
    b.append(section(1220, 150, 1140, 480, "Selector con autocompletado", selector()))
    b.append(section(40, 670, 1140, 500, "Insignia de semáforo", traffic_lights()))
    b.append(section(1220, 670, 1140, 500, "Control de prioridad", priorities()))
    b.append(section(40, 1210, 2320, 420, "Tarjetas de señal", signals()))
    b.append(section(40, 1670, 2320, 190, "Rótulos", labels()))
    return svg(W, H, b)


if __name__ == "__main__":
    from pathlib import Path

    out = Path(__file__).resolve().parent / "kit.svg"
    out.write_text(sheet(), encoding="utf-8", newline="\n")
    print(f"Escrito {out.name} ({out.stat().st_size // 1024} KB)")
