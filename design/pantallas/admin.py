"""Tanda 10 · Administrador (P1, HU-170). Solo escritorio: es una herramienta de oficina, no de campo. Lleva el pie de página común.

El panel va dentro de la misma web, en /admin, con su propia barra lateral (supuesto: el contrato aún no decide si
va aparte). Toda acción queda en `activity_log`; ver una ficha también (`admin.user_viewed`). Borrar o restaurar
datos de un agricultor exige motivo y, si viene de un ticket, el ticket. Las métricas son agregadas y sin datos
personales: las consultas salen del contador anónimo `usage_daily` (día, tipo, municipio y cultivo, sin quién consultó)
y los lotes y siembras, de las cuentas. Un grupo con menos de 5 va en «Otros». Los nombres y las cifras son de muestra.

    python design/pantallas/admin.py     # escribe svg/admin-*.svg
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ui  # noqa: E402,F401
from calendario import wrap_lines  # noqa: E402
from ui import (BORDE, D, DIR, FONT_TITLE, P, SEC, WHITE, button, card, chamfer, field, frame, group, link, logo, p1_tag, paragraph, poly,  # noqa: E402
                text, width_of)

W = 1440
NAV = ("Usuarios", "Tickets", "Bitácora", "Métricas")
OUT = {"ok": ("Hecho", D["oliva"], "#E9F2D8"), "denied": ("Rechazado", D["rojo"], "#FBE6E2"), "failed": ("Falló", D["calabaza"], "#FCEBD6")}


def chrome(active, h):
    """Barra lateral del panel: marca, «Administración», secciones y quién está conectado."""
    b = [f'<rect width="{W}" height="{h}" fill="{P["niebla"]}"/>', f'<rect width="260" height="{h}" fill="{P["noche"]}"/>']
    b += logo(28, 30, WHITE)
    b += [text(30, 104, "ADMINISTRACIÓN", 12, 700, P["niebla"])]
    for i, item in enumerate(NAV):
        y = 150 + i * 56
        on = item == active
        if on:
            b.append(poly(chamfer(16, y - 30, 228, 46, 8), WHITE))
        b.append(text(36, y, item, 18, 700, P["noche"] if on else WHITE))
    # arriba de los cerros del pie, que asoman sobre el final de la página
    b += [text(30, h - 182, "Ana (admin)", 15, 700, WHITE), text(30, h - 158, "Todo lo que hace queda", 12, fill=P["niebla"]),
          text(30, h - 140, "en la bitácora.", 12, fill=P["niebla"])]
    b += [text(30, h - 108, "Volver a la web", 14, 700, P["trigo"]), f'<rect x="30" y="{h - 103}" width="112" height="2" fill="{P["trigo"]}"/>']
    return b


def pill(x, y, label, fill, ink=None, stroke=None):
    w = width_of(label, 12, True) + 20
    return [poly(chamfer(x, y, w, 24, 6), fill, stroke, 1.5 if stroke else 0), text(x + w / 2, y + 17, label, 12, 700, ink or P["noche"], anchor="middle")], w


def page_title(title, sub, x=300, y=80):
    """Título de una pantalla del panel con su rótulo «P1»: todo el administrador es P1 (HU-170)."""
    return [text(x, y, title, 36, 600, font=FONT_TITLE)] + p1_tag(x + width_of(title, 36, True) + 16, y - 24) + paragraph(x, y + 30, [sub], 15, fill=SEC)


def table(x, y, w, heads, cols, rows, row_h=56, name="tabla"):
    """Tabla simple: encabezados y filas. Cada celda es una lista de piezas en coordenadas de su columna."""
    out = [poly(chamfer(0, 8, w, 60 + len(rows) * row_h, 14), BORDE), poly(chamfer(0, 0, w, 60 + len(rows) * row_h, 14), WHITE)]
    out += [text(cx, 38, hd, 12, 700, SEC) for cx, hd in zip(cols, heads)]
    for i, cells in enumerate(rows):
        ry = 56 + i * row_h
        out.append(f'<rect x="20" y="{ry}" width="{w - 40}" height="1" fill="{BORDE}"/>')
        for cx, cell in zip(cols, cells):
            out.append(f'<g transform="translate({cx} {ry})">{"".join(cell)}</g>')
    return [group(name, out, x, y)], 60 + len(rows) * row_h


# ---------- Usuarios ----------

# Tickets abiertos (sin cerrar) por usuario, los mismos de la bandeja: Rosa 1 en revisión, Lucía 1 y Ernesto 1 abiertos.
USERS = (("rosa.samaca", "Rosa", "Agricultor", "20 ene 2025", 4, 1, None), ("don.ernesto", "Ernesto", "Agricultor", "3 mar 2025", 2, 1, None),
         ("lucia.toca", "Lucía", "Agricultor", "11 may 2025", 1, 1, "8 oct"), ("ana", "Ana", "Administrador", "10 ene 2025", 0, 0, None),
         ("marta.ventaquemada", "Marta", "Agricultor", "2 ago 2026", 3, 0, None))


def users():
    h = 900
    b = chrome("Usuarios", h)
    b += page_title("Usuarios", "Agricultores y administradores. Ver una ficha queda registrado.")
    # «Buscar» filtra la lista ya cargada, en el navegador. No hay filtro por rol: GET /admin/users no lo tiene en el contrato.
    b += field(300, 150, 420, "Buscar", "", "Usuario o nombre", name="campo-buscar")
    b += button(W - 48 - 220, 164, 220, "Crear usuario")
    cols = (24, 230, 370, 530, 670, 760, 930)
    rows = []
    for user, name, role, since, lots, tickets, blocked in USERS:
        st = pill(0, 18, "Bloqueado " + blocked, "#FBE6E2", D["rojo"], D["rojo"])[0] if blocked else pill(0, 18, "Activo", "#E9F2D8", D["oliva"])[0]
        rows.append(([text(0, 36, user, 16, 700)], [text(0, 36, name, 15)], [text(0, 36, role, 15)], [text(0, 36, since, 14, fill=SEC)],
                     [text(0, 36, str(lots), 15)], [text(0, 36, str(tickets), 15, 700 if tickets else 400, D["calabaza"] if tickets else P["noche"])], st))
    t, th = table(300, 260, W - 348, ("USUARIO", "NOMBRE", "ROL", "CREADA", "LOTES", "TICKETS ABIERTOS", "ESTADO"), cols, rows)
    b += t
    b += link(W - 48 - 120, 260 + th + 40, "Ver más", 15)
    b += paragraph(300, 260 + th + 40, ["Tocar una fila abre la ficha del agricultor."], 14, fill=SEC)
    return ui.long_page((W, h), b, P["niebla"])


# ---------- Ficha del agricultor ----------

def profile(dialog=False):
    h = 1180
    b = chrome("Usuarios", h)
    b += link(300, 50, "‹ Usuarios", 15)
    b += [text(300, 100, "Rosa", 36, 600, font=FONT_TITLE)] + p1_tag(398, 76) + [text(456, 98, "rosa.samaca · agricultor · desde el 20 ene 2025 · consentimiento 3", 15, fill=SEC)]
    b += [poly(chamfer(300, 120, W - 348, 40, 8), "#E6F0F5"), text(318, 146, "Abrió esta ficha: queda en la bitácora como «admin.user_viewed», y Rosa lo ve en Mi actividad.", 14, 700)]
    b += button(W - 48 - 200, 70, 200, "Bloquear", "danger", h=44) + button(W - 48 - 420, 70, 200, "Cambiar rol", "secondary", h=44)
    # lotes
    cols = (24, 230, 390, 620, 900)
    lots = (("El Alto", "2,51 ha · sin riego", "Papa, haba y cebolla", None), ("La Vega", "1,66 ha · con riego", "Maíz", None),
            ("El Bajo", "1,33 ha · sin riego", "Arveja", None), ("Potrero", "1,19 ha", "Sin siembra", None),
            ("La Loma", "0,86 ha", "Borrado el 3 oct · restaurable hasta el 2 nov", "restore"))
    rows = []
    for name, area, crops, act in lots:
        rows.append(([text(0, 34, name, 16, 700, SEC if act else P["noche"])], [text(0, 34, area, 14, fill=SEC)], [text(0, 34, "Samacá", 14)],
                     [text(0, 34, crops, 14, fill=SEC if act else P["noche"])],
                     link(0, 34, "Restaurar", 14) if act else link(0, 34, "Ver temporadas", 14) + link(140, 34, "Borrar", 14)))
    b.append(text(300, 210, "Lotes", 22, 600, font=FONT_TITLE))
    t, th = table(300, 228, W - 348, ("LOTE", "ÁREA", "ZONA", "CULTIVOS", "ACCIONES"), cols, rows, 52)
    b += t
    y = 228 + th + 46
    b.append(text(300, y, "Tickets", 22, 600, font=FONT_TITLE))
    tcols = (24, 420, 620, 800)
    trows = [([text(0, 34, "El calendario no muestra la cebolla", 15, 700)], [text(0, 34, "2 oct · lote El Alto", 14, fill=SEC)],
              pill(0, 16, "En revisión", P["trigo"])[0], link(0, 34, "Abrir ticket", 14)),
             ([text(0, 34, "Un lote no me deja guardar la siembra", 15, 700)], [text(0, 34, "9 oct · lote El Alto", 14, fill=SEC)],
              pill(0, 16, "Cerrado", P["brote"])[0], link(0, 34, "Abrir ticket", 14))]
    t2, th2 = table(300, y + 18, W - 348, ("ASUNTO", "ENVIADO", "ESTADO", ""), tcols, trows, 52)
    b += t2
    y += 18 + th2 + 40
    b += paragraph(300, y, ["El administrador no ve contraseñas ni el texto de los campos en la bitácora. Borrar o restaurar exige un motivo."], 14, fill=SEC)
    if dialog:
        foot, fh = ui.footer(W, h, above=P["niebla"])
        b += foot
        b.append(f'<rect width="{W}" height="{h + fh}" fill="{P["noche"]}" fill-opacity="0.62"/>')
        dx, dy, dw = (W - 640) / 2, 220, 640
        d = [text(36, 60, "Borrar el lote El Bajo de Rosa", 26, 600, font=FONT_TITLE)]
        d += paragraph(36, 96, ["Se puede restaurar durante 30 días. Rosa lo verá en Mi actividad."], 15, fill=SEC)
        d += field(36, 140, dw - 72, "Motivo (obligatorio)", "Rosa pidió borrarlo: lo registró dos veces", state="foco", name="campo-motivo")
        d += field(36, 244, dw - 72, "Ticket", "El calendario no muestra la cebolla · 2 oct", trailing="▾", name="campo-ticket", hint="Opcional si no viene de un ticket")
        d += button(36, 370, 260, "No, volver") + button(dw - 36 - 260, 370, 260, "Borrar el lote", "danger")
        b += card(dx, dy, dw, 460, "dialogo") + [group("dialogo-contenido", d, dx, dy)]
        return frame((W, h + fh), b, P["niebla"])
    return ui.long_page((W, h), b, P["niebla"])


# ---------- Tickets ----------

TICKETS = (("El calendario no muestra la cebolla", "rosa.samaca", "2 oct", "En revisión", True),
           ("No puedo entrar desde el celular", "lucia.toca", "8 oct", "Abierto", False),
           ("La oferta de haba sale sin datos", "don.ernesto", "9 oct", "Abierto", False),
           ("Un lote no me deja guardar la siembra", "rosa.samaca", "9 oct", "Cerrado", False))
STATUS_FILL = {"Abierto": WHITE, "En revisión": P["trigo"], "Cerrado": P["brote"]}


def tickets():
    h = 900
    b = chrome("Tickets", h)
    b += page_title("Tickets", "Reportes de los agricultores. Cambiar el estado queda en la bitácora.")
    lx, lw = 300, 520
    tabs = (("Todos", len(TICKETS)), ("Abiertos", 2), ("En revisión", 1), ("Cerrados", 1))  # activa «Todos»: la lista trae los cuatro y el detalle es uno en revisión
    tx = lx
    for i, (label, n) in enumerate(tabs):
        pl, pw = pill(tx, 140, f"{label} · {n}", P["noche"] if i == 0 else WHITE, WHITE if i == 0 else P["noche"], None if i == 0 else BORDE)
        b += pl
        tx += pw + 8
    y = 184
    for title, user, date, status, on in TICKETS:
        body = [poly(chamfer(0, 0, lw, 86, 12), "#FFF6EA" if on else WHITE, P["calabaza"] if on else BORDE, 2 if on else 1.5),
                text(18, 32, title, 16, 700), text(18, 58, f"{user} · {date}", 13, fill=SEC)]
        body += pill(lw - 130, 18, status, STATUS_FILL[status], stroke=BORDE if status == "Abierto" else None)[0]
        b.append(group("ticket", body, lx, y))
        y += 98
    dx, dw = lx + lw + 24, W - 48 - (lx + lw + 24)
    d = [text(28, 46, "El calendario no muestra la cebolla", 22, 600, font=FONT_TITLE), text(28, 74, "rosa.samaca · 2 oct · lote El Alto", 14, fill=SEC)]
    d += link(dw - 28, 74, "Ver ficha", 14, anchor="end")
    d += [poly(chamfer(28, 96, dw - 56, 96, 10), P["niebla"])]
    d += paragraph(46, 126, wrap_lines(["Registré la cebolla en agosto y en el calendario solo sale la papa. ¿Hice algo mal?"], 56), 15, 22)
    d += [poly(chamfer(28, 208, dw - 56, 36, 8), WHITE, BORDE, 1.5), text(44, 232, "Código para soporte: 9b1e-42c7", 14, 700)]
    # El contrato de un ticket solo tiene `message` y `status`: no hay nota interna. PATCH /admin/tickets/{id} cambia el estado.
    d += field(28, 286, 240, "Estado", "En revisión", trailing="▾", name="campo-estado")
    d += button(28, 394, 220, "Guardar estado")
    d += paragraph(28, 486, wrap_lines(["Para borrar o restaurar algo de Rosa por este ticket, hágalo desde su ficha: el ticket queda unido a la acción."], 60), 13, 19, fill=SEC)
    b += card(dx, 140, dw, 546, "detalle-ticket") + [group("detalle-ticket-texto", d, dx, 140)]
    return ui.long_page((W, h), b, P["niebla"])


# ---------- Bitácora ----------

# Los eventos de Rosa son los mismos de «Mi actividad» (actividad.py). Un intento de entrada fallido no guarda de quién
# fue: por eso no aparece en la actividad de nadie. La acción de soporte del 9 de octubre va unida al reporte de ese día.
LOG = (("11 oct 10:42", "rosa.samaca", "Agricultor", "lot.updated", "lote El Alto · riego", "ok", "a41f…", None),
       ("11 oct 10:30", "rosa.samaca", "Agricultor", "auth.login", "—", "ok", "a3f0…", None),
       ("11 oct 10:05", "ana", "Admin", "admin.activity_viewed", "bitácora", "ok", "77c2…", None),
       ("10 oct 18:05", "—", "—", "auth.login_failed", "—", "failed", "e9d0…", None),
       ("10 oct 17:50", "rosa.samaca", "Agricultor", "auth.logout", "—", "ok", "c3a7…", None),
       ("9 oct 16:20", "ana", "Admin", "admin.user_viewed", "rosa.samaca", "ok", "5c11…", "9 oct"),
       ("8 oct 07:55", "rosa.samaca", "Agricultor", "auth.password_changed", "—", "denied", "1b8e…", None),
       ("8 oct 07:40", "ana", "Admin", "admin.user_blocked", "lucia.toca", "ok", "0d2a…", None))


def activity():
    h = 980
    b = chrome("Bitácora", h)
    b += page_title("Bitácora", "Quién hizo qué y cuándo. Consultarla también queda registrado. Se guarda 180 días.")
    fw = (W - 348 - 3 * 16 - 140) / 4
    for i, (label, value) in enumerate((("Usuario", "Todos"), ("Acción", "Todas"), ("Resultado", "Todos"), ("Fechas", "1 – 11 oct 2026"))):
        b += field(300 + i * (fw + 16), 150, fw, label, value, trailing="▾", name=f"filtro-{label.lower()}")
    b += button(W - 48 - 130, 164, 130, "Filtrar", "secondary")
    cols = (24, 170, 330, 450, 690, 900, 1010)
    rows = []
    for when, who, role, action, obj, outcome, req, ticket in LOG:
        label, ink, fill = OUT[outcome]
        rows.append(([text(0, 32, when, 13)], [text(0, 32, who, 14, 700)], [text(0, 32, role, 13, fill=SEC)], [text(0, 32, action, 13, 700, font="Atkinson Hyperlegible")],
                     [text(0, 32, obj + (f" · ticket {ticket}" if ticket else ""), 13)], pill(0, 14, label, fill, ink)[0], [text(0, 32, req, 13, fill=SEC)]))
    t, th = table(300, 260, W - 348, ("CUÁNDO", "QUIÉN", "ROL", "ACCIÓN", "SOBRE QUÉ", "RESULTADO", "REQUEST_ID"), cols, rows, 50)
    b += t
    b += button(300, 260 + th + 30, 240, "Ver más antiguos", "secondary")
    b += paragraph(560, 260 + th + 62, ["Nunca guarda contraseñas, tokens, el polígono, valores de campos ni el usuario de un intento fallido."], 13, fill=SEC)
    return ui.long_page((W, max(h, 260 + th + 120)), b, P["niebla"])


# ---------- Métricas ----------

DAYS = (49, 45, 58, 54, 70, 65, 78, 73, 87, 81, 99, 95, 103, 109)  # suman 1.066, como la cifra de arriba y los dos desgloses
assert sum(DAYS) == 1066
LOTS_BY_TOWN = (("Samacá", 38), ("Ventaquemada", 21), ("Toca", 12), ("Otros municipios*", 9))
TOWNS_QUERIED = (("Samacá", 412), ("Ventaquemada", 268), ("Toca", 171), ("Tunja", 96), ("Otros municipios*", 119))
CROPS_QUERIED = (("Papa", 498), ("Arveja", 187), ("Maíz", 142), ("Haba", 121), ("Otros cultivos*", 118))
CROPS = (("Papa", 46), ("Arveja", 19), ("Maíz", 14), ("Haba", 11), ("Cebolla", 8))


def metrics():
    h = 1440
    b = chrome("Métricas", h)
    b += page_title("Métricas", "Agregadas y sin datos personales. Ningún grupo con menos de 5 cuentas se muestra aparte.")
    kw = (W - 348 - 3 * 20) / 4
    for i, (n, label) in enumerate((("1.066", "consultas en 14 días"), ("31", "cuentas creadas en octubre"), ("80", "lotes registrados"), ("98", "siembras registradas"))):
        c = [text(24, 56, n, 34, 600, font=FONT_TITLE), text(24, 84, label, 14, fill=SEC)]
        b += card(300 + i * (kw + 20), 140, kw, 110, f"cifra-{i + 1}") + [group(f"cifra-{i + 1}-texto", c, 300 + i * (kw + 20), 140)]
    # consultas por día
    cw = W - 348
    c = [text(24, 40, "Consultas por día", 20, 700), text(24, 62, "Del contador anónimo: no guarda quién consultó, ni la hora, la fecha de siembra o el área.", 13, fill=SEC)]
    bw = (cw - 48) / len(DAYS)
    vmax = max(DAYS)
    for i, v in enumerate(DAYS):
        bh = 150 * v / vmax
        c += [poly(chamfer(24 + i * bw + 6, 240 - bh, bw - 12, bh, 3), P["cielo"], D["cielo"], 1.5), text(24 + i * bw + bw / 2, 260, f"{28 + i if 28 + i <= 30 else i - 2}", 11, fill=SEC, anchor="middle")]
    c.append(text(24, 284, "Del 28 de septiembre al 11 de octubre", 12, fill=SEC))
    b += card(300, 280, cw, 306, "consultas") + [group("consultas-texto", c, 300, 280)]
    # lotes por municipio y siembras por cultivo
    half = (cw - 24) / 2
    groups = (("Municipios más consultados", "Consultas de los últimos 14 días.", TOWNS_QUERIED), ("Cultivos más consultados", "Consultas de los últimos 14 días.", CROPS_QUERIED),
              ("Lotes por municipio", "De las cuentas, no de las consultas.", LOTS_BY_TOWN), ("Siembras registradas por cultivo", "Temporadas en curso y cosechadas.", CROPS))
    for k, (title, sub, data) in enumerate(groups):
        c = [text(24, 40, title, 20, 700), text(24, 62, sub, 13, fill=SEC)]
        vmax = max(v for _, v in data)
        for i, (name, v) in enumerate(data):
            ry = 90 + i * 40
            c += [text(24, ry + 18, name if len(name) < 22 else name[:20] + "…", 14), poly(chamfer(200, ry + 4, (half - 270) * v / vmax, 20, 3), P["brote"] if k % 2 else P["trigo"], D["oliva"] if k % 2 else D["trigo"], 1.5),
                  text(200 + (half - 270) * v / vmax + 10, ry + 19, str(v), 14, 700)]
        hh = 90 + 5 * 40 + 20
        bx, by = 300 + (k % 2) * (half + 24), 610 + (k // 2) * (hh + 24)
        b += card(bx, by, half, hh, f"barras-{k + 1}") + [group(f"barras-{k + 1}-texto", c, bx, by)]
    b += paragraph(300, 610 + 2 * (90 + 5 * 40 + 20 + 24) + 20, ["* «Otros» junta los grupos con menos de 5 consultas o de menos de 5 cuentas, para que nadie se pueda reconocer. Las cifras son de muestra."], 13, fill=SEC)
    return ui.long_page((W, h), b, P["niebla"])


SCREENS = {
    "admin-01-usuarios-escritorio": users,
    "admin-02-ficha-agricultor-escritorio": profile,
    "admin-02-ficha-borrar-lote-escritorio": lambda: profile(dialog=True),
    "admin-03-tickets-escritorio": tickets,
    "admin-04-bitacora-escritorio": activity,
    "admin-05-metricas-escritorio": metrics,
}

if __name__ == "__main__":
    out = DIR / "svg"
    for name, draw in SCREENS.items():
        (out / f"{name}.svg").write_text(draw(), encoding="utf-8", newline="\n")
        print(name)
