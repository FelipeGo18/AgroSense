"""Pantallas finales de Cuenta (EP-16: HU-162, HU-163, HU-166 y HU-168; rediseño, tanda 7: consentimiento v3 y «Sus prioridades», HU-202).

Iniciar sesión, crear cuenta con consentimiento, mi cuenta y confirmar el borrado, en escritorio y móvil.
Los campos son los del contrato: usuario, contraseña y nombre. No hay correo ni celular.

    python design/pantallas/cuenta.py     # escribe svg/cuenta-*.svg
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ui  # noqa: E402
import muestra  # noqa: E402
from senales import priorities_panel  # noqa: E402
from ui import (BORDE, D, DESKTOP, DIR, FONT_TITLE, MOBILE, P, SEC, WHITE, button, card, chamfer, checkbox, field, frame, group, link,
                mascot, p1_tag, paragraph, poly, scene, text, toggle, topbar, width_of)  # noqa: E402

# El enlace abre la página de la política de tratamiento de datos (pendiente de diseño: mapa.py, parte J).
POLICY = "Leer la política de tratamiento de datos"
POLICY_SHORT = "Leer la política de datos"
# Contenido de muestra de los diseños: una agricultora de Samacá.
NAME, USER, SINCE, LOTS, SEASONS = muestra.NAME, muestra.USERNAME, muestra.ACCOUNT_SINCE, muestra.N_LOTS, muestra.N_SEASONS
ACCEPTED = muestra.CONSENT_ACCEPTED  # la versión 3 no se pudo aceptar antes de existir: la fecha no es la de creación de la cuenta


def sign(x, y, w, label):
    """Letrero clavado, como los del kit: da la bienvenida junto a la mascota."""
    body = [poly([(w / 2 - 8, 52), (w / 2 + 8, 52), (w / 2 + 8, 82), (w / 2, 90), (w / 2 - 8, 82)], P["tierra"]),
            poly(chamfer(0, 0, w, 56, 10), P["trigo"], D["trigo"], 3), text(w / 2, 36, label, 20, 700, anchor="middle")]
    return [group("letrero", body, x, y)]


def alert(x, y, w, rows):
    """Aviso de error: borde rojo, cuadrado y texto. Nunca solo color."""
    h = 28 + len(rows) * 24
    body = [poly(chamfer(1.5, 1.5, w - 3, h - 3, 8), WHITE, D["rojo"], 3), poly([(18, 18), (32, 18), (32, 32), (18, 32)], D["rojo"])]
    body += paragraph(44, 31, rows, 16, 24, weight=700, fill=D["rojo"])
    return [group("aviso-error", body, x, y)]


# ---------- Iniciar sesión ----------
# El formulario cabe entero en la primera pantalla, sin hacer scroll (un portátil a 125 % deja unos 700 px de alto);
# debajo va el pie de página común.

def login(mobile=False, error=False):
    w, h = MOBILE if mobile else DESKTOP
    b = scene("a6-vereda", w, h, "recorte-login" + ("-m" if mobile else "") + ("-e" if error else ""))
    b += topbar(w)
    if mobile:
        b += mascot(300, 66, 0.21, "guia")  # se asoma por el borde de la tarjeta: no le quita alto al formulario
        x, y, cw, pad = 12, 104, 366, 22
    else:
        b += sign(800, 150, 330, "Su finca lo espera") + mascot(760, 236, 1.6, "guia")
        x, y, cw, pad = 96, 104, 480, 36
    fw = cw - 2 * pad
    c = [text(pad, 46, "ENTRAR", 15, 700, SEC), text(pad, 86, "Vuelva a su finca", 30 if mobile else 36, 600, font=FONT_TITLE)]
    top = 116
    if error:
        c += alert(pad, top - 12, fw, ["Usuario o contraseña incorrectos.", "Revíselos y vuelva a intentar."])
        top += 76
    else:
        c.append(text(pad, top, "Entre con su usuario y contraseña.", 18))
    c += field(pad, top + 40, fw, "Usuario", USER if error else "", "Su usuario", name="campo-usuario")
    c += field(pad, top + 132, fw, "Contraseña", "••••••••" if error else "", "Su contraseña", "error" if error else "normal", trailing="Mostrar", name="campo-contrasena")
    c += button(pad, top + 216, fw, "Entrar")
    c.append(text(pad, top + 306, "¿No tiene cuenta?", 18))
    c += link(pad + 162, top + 306, "Crear cuenta")
    c += link(pad, top + 340, "Seguir sin cuenta")
    c.append(f'<rect x="{pad}" y="{top + 358}" width="{fw}" height="2" fill="{BORDE}"/>')
    c += paragraph(pad, top + 384, ["Si olvida su contraseña, por ahora no se", "puede recuperar. No guardamos su correo", "ni su celular."] if mobile else
                   ["Si olvida su contraseña, por ahora no se puede recuperar.", "No guardamos su correo ni su celular."], 15, 20, fill=SEC)
    ch = top + (446 if mobile else 426)
    return ui.long_page((w, h), b + card(x, y, cw, ch) + [group("contenido", c, x, y)])


# ---------- Crear cuenta ----------
# En escritorio va en dos columnas (los datos y el consentimiento). En móvil, en dos pasos: primero los datos y después
# el consentimiento. Así cada pantalla cabe sin hacer scroll.

CONSENT = (  # versión 3 (HU-163), en primera persona: lo dice quien acepta
    "Acepto que AgroSense guarde mi usuario, mi nombre y mis prioridades, mis lotes con su ubicación en el mapa, si tienen riego y lo que siembro, para mostrarme mi finca.",
    "Soporte puede ver mis lotes para ayudarme, y se registra la actividad de mi cuenta durante 180 días.",
    "Lo que siembro se suma, sin mi nombre, a los totales de mi municipio, solo si hay al menos 5 cuentas.",
    "No se guarda correo, celular, documento ni dirección. Puedo borrar todo cuando quiera.",
)


def wrap(sentence, limit):
    """Parte una frase en renglones de hasta `limit` letras."""
    rows, row = [], ""
    for word in sentence.split():
        if row and len(row) + 1 + len(word) > limit:
            rows.append(row)
            row = word
        else:
            row = f"{row} {word}".strip()
    return rows + [row]


def consent_box(x, y, w, limit, size, policy):
    """El consentimiento con su casilla: qué se guarda y para qué. Sin aceptar no se crea la cuenta (R9)."""
    line = size + 6
    body, cy = checkbox(14, 14), 34
    for sentence in CONSENT:
        rows = wrap(sentence, limit)
        body += paragraph(58, cy, rows, size, line)
        cy += len(rows) * line + 8
    body += link(58, cy + 4, policy, size)
    h = cy + 26
    return [group("consentimiento", [poly(chamfer(0, 0, w, h, 12), P["niebla"])] + body, x, y)], h


def register(mobile=False, step=1):
    w, h = MOBILE if mobile else DESKTOP
    tag = "-m" + str(step) if mobile else ""
    b = scene("a6-vereda", w, h, "recorte-registro" + tag)
    b += topbar(w)
    if mobile:
        b += mascot(300, 66, 0.21, "celebra")
        x, y, cw, pad = 12, 104, 366, 22
        fw = cw - 2 * pad
        c = [text(pad, 46, f"CREAR CUENTA · PASO {step} DE 2", 15, 700, SEC)]
        if step == 1:
            c.append(text(pad, 86, "Guarde su finca", 30, 600, font=FONT_TITLE))
            c += field(pad, 126, fw, "¿Cómo quiere que lo llamemos?", NAME, name="campo-nombre")
            c += field(pad, 218, fw, "Usuario", USER, name="campo-usuario")
            c += field(pad, 310, fw, "Contraseña", "••••••••••", state="foco", trailing="Mostrar", hint="Al menos 8 caracteres. No se puede recuperar.", name="campo-contrasena")
            c += button(pad, 420, fw, "Continuar")
            c.append(text(pad, 510, "¿Ya tiene cuenta?", 18))
            c += link(pad + 158, 510, "Entrar")
            ch = 536
        else:
            box, bh = consent_box(pad, 64, fw, 38, 14, POLICY_SHORT)
            c += box
            c += button(pad, 64 + bh + 14, fw, "Crear cuenta")
            c += link(pad, 64 + bh + 108, "← Volver a mis datos")
            ch = 64 + bh + 134
        return ui.long_page((w, h), b + card(x, y, cw, ch) + [group("contenido", c, x, y)])
    b += sign(1080, 132, 290, "Sus lotes, guardados") + sign(1066, 212, 318, "Su historial de siembras") + mascot(1060, 300, 1.05, "celebra")
    x, y, cw, pad = 96, 104, 880, 36
    col = (cw - 2 * pad - 32) / 2
    c = [text(pad, 46, "CREAR CUENTA", 15, 700, SEC), text(pad, 86, "Guarde su finca", 36, 600, font=FONT_TITLE),
         text(pad, 116, "Solo un nombre, un usuario y una contraseña.", 18)]
    c += field(pad, 156, col, "¿Cómo quiere que lo llamemos?", NAME, name="campo-nombre")
    c += field(pad, 248, col, "Usuario", USER, hint="Con este usuario va a entrar.", name="campo-usuario")
    c += field(pad, 364, col, "Contraseña", "••••••••••", state="foco", trailing="Mostrar", hint="Al menos 8 caracteres. No se puede recuperar.", name="campo-contrasena")
    c.append(text(pad, 496, "¿Ya tiene cuenta?", 18))
    c += link(pad + 158, 496, "Entrar")
    box, bh = consent_box(pad + col + 32, 142, col, 44, 15, POLICY)
    c += box
    c += button(pad + col + 32, 142 + bh + 14, col, "Crear cuenta")
    ch = max(520, 142 + bh + 14 + 76)
    return ui.long_page((w, h), b + card(x, y, cw, ch) + [group("contenido", c, x, y)])


# ---------- Mi cuenta ----------

def row(y, label, value, w, editable=False):
    out = [text(0, y, label, 16, fill=SEC), text(0, y + 26, value, 20, 700), f'<rect x="0" y="{y + 42}" width="{w}" height="2" fill="{P["niebla"]}"/>']
    if editable:
        out += link(w, y + 26, "Editar", 16, anchor="end")
    return out


def pref(y, title, note, on, w, p1=False):
    """Una preferencia del dispositivo con su interruptor. `p1`: rótulo para el equipo (el sonido es P1)."""
    return [text(0, y, title, 18, 700), text(0, y + 24, note, 15, fill=SEC)] + toggle(w - 64, y - 20, on) + (p1_tag(width_of(title, 18, True) + 12, y - 18) if p1 else [])


def profile_cards(cw, mobile, editing=False):
    """Las cinco tarjetas de Mi cuenta, cada una con su alto. El orden es el de lectura."""
    pad = 22 if mobile else 32
    fw = cw - 2 * pad
    title = lambda t: text(pad, 50, t, 24, 600, font=FONT_TITLE)  # noqa: E731
    if editing:  # HU-160: se editan nombre y usuario en la misma tarjeta
        data = [title("Sus datos")]
        data += field(pad, 92, fw, "Nombre", NAME, name="campo-nombre")
        data += field(pad, 196, fw, "Usuario", "rosa", state="error", hint="Ese usuario ya existe. Pruebe con otro.", name="campo-usuario")
        bw = (fw - 16) / 2
        data += button(pad, 316, bw, "Guardar") + button(pad + bw + 16, 316, bw, "Cancelar", "secondary")
        data_h = 410
    else:
        rows = (row(94, "Nombre", NAME, fw, True), row(166, "Usuario", USER, fw, True), row(238, "Cuenta creada", SINCE, fw))
        data = [title("Sus datos")] + [group("fila", r, pad, 0) for r in rows]
        data.append(text(pad, 316, "Puede cambiar su nombre y su usuario cuando quiera.", 15, fill=SEC))
        data_h = 350
    stored_rows = (["Su usuario, su nombre y sus", "prioridades.", f"Sus {LOTS} lotes, con su ubicación", "en el mapa y si tienen riego, y", f"sus {SEASONS} temporadas.",
                    "Sus sesiones abiertas y la actividad", "de su cuenta (180 días).", "Sus siembras cuentan, sin su nombre,", "en los totales del municipio.",
                    "No guardamos correo, celular,", "documento ni dirección.", "",
                    "Aceptó el tratamiento de datos", f"(versión {muestra.CONSENT_VERSION}) el {ACCEPTED}."] if mobile else
                   ["Su usuario, su nombre y sus prioridades.", f"Sus {LOTS} lotes, con su ubicación en el mapa y si tienen riego,", f"y sus {SEASONS} temporadas de siembra.",
                    "Sus sesiones abiertas y la actividad de su cuenta (180 días).",
                    "Sus siembras cuentan, sin su nombre, en los totales del municipio.", "No guardamos correo, celular, documento ni dirección.", "",
                    f"Aceptó el tratamiento de datos (versión {muestra.CONSENT_VERSION})", f"el {ACCEPTED}."])
    stored = [title("Lo que guardamos de usted")] + paragraph(pad, 92, stored_rows, 16 if mobile else 18, 26)
    stored += link(pad, 92 + len(stored_rows) * 26 + 12, POLICY_SHORT if mobile else POLICY, 16)
    stored += link(pad if mobile else cw - pad, 92 + len(stored_rows) * 26 + (48 if mobile else 12), "Ver mi actividad", 16, anchor="start" if mobile else "end")
    prefs = [title("Preferencias" if mobile else "Preferencias de este dispositivo")]
    for i, (t, note, on) in enumerate((("Modo ligero", "Quita las animaciones y el scroll suave.", False),
                                       ("Sonido", "Ambiente y efectos. Empieza apagado.", False))):
        prefs.append(group("preferencia", pref(104 + i * 76, t, note.replace("animaciones pesadas", "animaciones") if mobile else note, on, fw, p1=t == "Sonido"), pad, 0))
    session = [title("Sesión y contraseña"), text(pad, 92, f"Entró como {USER}.", 18)]
    if mobile:
        session += button(pad, 116, fw, "Cambiar contraseña", "secondary") + button(pad, 188, fw, "Cerrar sesión", "secondary")
        session_h = 276
    else:
        bw = (fw - 16) / 2
        session += button(pad, 116, bw, "Cambiar contraseña", "secondary") + button(pad + bw + 16, 116, bw, "Cerrar sesión", "secondary")
        session_h = 204
    # Sus prioridades (HU-202): las mismas seis de la consulta; se guardan en el perfil (PATCH /me) al tocarlas.
    own, ph = priorities_panel(0, 0, fw, muestra.FARMER_WEIGHTS, compact=mobile)
    prio = [title("Sus prioridades")]
    prio += paragraph(pad, 84, ["Se usan en cada consulta y en el calendario.", "Se guardan al tocar las semillas."] if mobile else
                      ["Se usan en cada consulta y en el calendario. Se guardan al tocar las semillas."], 15, 21, fill=SEC)
    py = 84 + (2 if mobile else 1) * 21 + 22
    prio.append(group("panel", own, pad, py))
    prio += link(pad, py + ph + 18, "Volver al criterio de AgroSense", 16)
    prio += paragraph(pad, py + ph + 52, ["Con el criterio de AgroSense: " + ", ".join(f"{muestra.SIGNAL_NAME[k].lower()} {muestra.DEFAULT_WEIGHTS[k]}" for k in muestra.SIGNAL_ORDER[:3]) + ",",
                                          ", ".join(f"{muestra.SIGNAL_NAME[k].lower()} {muestra.DEFAULT_WEIGHTS[k]}" for k in muestra.SIGNAL_ORDER[3:]) + "."], 13, 19, fill=SEC)
    prio_h = py + ph + 52 + 38 + 20
    danger_rows = (["Se borran su usuario, sus sesiones,", f"sus {LOTS} lotes, sus {SEASONS} temporadas,", "sus reportes y su actividad.", "No se puede deshacer."] if mobile else
                   [f"Se borran su usuario, sus sesiones, sus {LOTS} lotes, sus {SEASONS}", "temporadas, sus reportes y el registro de su actividad.", "No se puede deshacer."])
    danger = [poly([(0, 18), (8, 18), (8, 0), (0, 0)], P["rojo"]), title("Borrar mi cuenta")] + paragraph(pad, 92, danger_rows, 16 if mobile else 18, 26)
    dy = 92 + len(danger_rows) * 26 + 6
    danger += button(pad, dy, min(fw, 260), "Borrar mi cuenta", "danger")
    return [("sus-datos", data, data_h), ("lo-que-guardamos", stored, 92 + len(stored_rows) * 26 + (86 if mobile else 50)), ("preferencias", prefs, 244),
            ("sesion", session, session_h), ("borrar-cuenta", danger, dy + 88), ("sus-prioridades", prio, prio_h)]


def profile(mobile=False, dialog=False, editing=False):
    w = MOBILE[0] if mobile else DESKTOP[0]
    cards = profile_cards(366 if mobile else 600, mobile, editing)
    if mobile:  # orden de lectura: datos, prioridades, lo que guardamos, preferencias, sesión y borrar
        cards = [cards[0], cards[5]] + cards[1:5]
        h = 250 + sum(ch + 28 for _, _, ch in cards) + 30
        places = []
        y = 250
        for name, body, ch in cards:
            places.append((12, y, 366, ch, name, body))
            y += ch + 28
    else:
        left, right = [cards[0], cards[5]], [cards[1], cards[2], cards[3], cards[4]]
        places, bottoms = [], []
        for x, column in ((96, left), (744, right)):
            y = 300
            for name, body, ch in column:
                places.append((x, y, 600, ch, name, body))
                y += ch + 32
            bottoms.append(y)
        h = max(bottoms) + 40
    tag = ("-m" if mobile else "") + ("-d" if dialog else "") + ("-e" if editing else "")
    b = [f'<rect width="{w}" height="{h}" fill="{P["niebla"]}"/>']
    # Franja de paisaje arriba: Mi cuenta sigue estando en el mismo mundo.
    strip = 230 if mobile else 280
    b.append(f'<g transform="translate(0 0)">{"".join(scene("a3-region", w, strip, "recorte-perfil" + tag))}</g>')
    b += topbar(w, user=None if mobile else NAME)
    b.append(text(12 if mobile else 96, 140 if mobile else 200, "Mi cuenta", 36 if mobile else 48, 600, font=FONT_TITLE))
    b += mascot(240 if mobile else 1090, 96 if mobile else 96, 0.5 if mobile else 0.7, "reposo")
    for x, y, cw, ch, name, body in places:
        b += card(x, y, cw, ch, c=16) + [group(name, body, x, y)]
    foot, fh = ui.footer(w, h, mobile, above=P["niebla"])
    b += foot
    if dialog:
        b.append(f'<rect id="velo" width="{w}" height="{h + fh}" fill="{P["noche"]}" fill-opacity="0.62"/>')
        dx, dy, dw = (w - 620) / 2, 250, 620
        d = [text(40, 70, "¿Borrar su cuenta?", 36, 600, font=FONT_TITLE)]
        d += paragraph(40, 116, ["Se va a borrar todo esto, para siempre:"], 18)
        for i, item in enumerate((f"Su usuario «{USER}» y su nombre.", "Sus sesiones en todos los dispositivos.", f"Sus {LOTS} lotes y sus {SEASONS} temporadas de siembra.",
                                  "Sus reportes y el registro de su actividad.")):
            d += [poly([(40, 146 + i * 32), (54, 146 + i * 32), (54, 160 + i * 32), (40, 160 + i * 32)], D["rojo"]), text(66, 160 + i * 32, item, 18)]
        d.append(text(40, 300, "No se puede deshacer.", 18, 700))
        d += button(40, 332, 250, "No, volver") + button(330, 332, 250, "Sí, borrar todo", "danger")
        b += card(dx, dy, dw, 432, "dialogo") + [group("dialogo-contenido", d, dx, dy)]
    return svg_frame(w, h + fh, b)


def change_password(mobile=False, error=False):
    """Cabe entero en la primera pantalla, sin hacer scroll; debajo va el pie de página común."""
    w, h = MOBILE if mobile else DESKTOP
    if mobile:
        x, y, cw, pad = 12, 104, 366, 22
    else:
        x, y, cw, pad = 96, 104, 480, 36
    fw = cw - 2 * pad
    c = [text(pad, 46, "MI CUENTA", 15, 700, SEC), text(pad, 86, "Cambiar contraseña", 30 if mobile else 36, 600, font=FONT_TITLE)]
    top = 116
    if error:
        c += alert(pad, top - 12, fw, ["La contraseña actual no es correcta.", "Su sesión sigue abierta."])
        top += 76
    else:
        c += paragraph(pad, top, ["Al cambiarla, se cierra su sesión en los", "demás dispositivos."] if mobile else ["Al cambiarla, se cierra su sesión en los demás", "dispositivos."], 16 if mobile else 18, 24)
        top += 24
    c += field(pad, top + 40, fw, "Contraseña actual", "••••••••", "", "error" if error else "normal", trailing="Mostrar", name="campo-actual")
    c += field(pad, top + 132, fw, "Contraseña nueva", "" if error else "••••••••••", "Al menos 8 caracteres", "normal" if error else "foco",
               hint="Al menos 8 caracteres. No se puede recuperar.", trailing="Mostrar", name="campo-nueva")
    c += field(pad, top + 248, fw, "Repita la contraseña nueva", "", "Escríbala otra vez", name="campo-repetir")
    c += button(pad, top + 332, fw, "Guardar contraseña")
    c += link(pad, top + 420, "Volver a Mi cuenta")
    ch = top + 448
    tag = ("-m" if mobile else "") + ("-e" if error else "")
    b = scene("a3-region", w, h, "recorte-contrasena" + tag) + topbar(w, user=None if mobile else NAME)
    b += mascot(300, 66, 0.21, "reposo") if mobile else mascot(800, 220, 1.5, "reposo")
    return ui.long_page((w, h), b + card(x, y, cw, ch) + [group("contenido", c, x, y)])


def svg_frame(w, h, body):
    from ui import svg

    return svg(w, h, body)


SCREENS = {
    "cuenta-01-iniciar-sesion-escritorio": lambda: login(),
    "cuenta-01-iniciar-sesion-movil": lambda: login(mobile=True),
    "cuenta-01-iniciar-sesion-error-escritorio": lambda: login(error=True),
    "cuenta-02-crear-cuenta-escritorio": lambda: register(),
    "cuenta-02-crear-cuenta-movil": lambda: register(mobile=True),
    "cuenta-02-crear-cuenta-paso2-movil": lambda: register(mobile=True, step=2),
    "cuenta-03-mi-cuenta-escritorio": lambda: profile(),
    "cuenta-03-mi-cuenta-movil": lambda: profile(mobile=True),
    "cuenta-04-confirmar-borrado-escritorio": lambda: profile(dialog=True),
    "cuenta-05-editar-datos-escritorio": lambda: profile(editing=True),
    "cuenta-05-editar-datos-movil": lambda: profile(mobile=True, editing=True),
    "cuenta-06-cambiar-contrasena-escritorio": lambda: change_password(),
    "cuenta-06-cambiar-contrasena-movil": lambda: change_password(mobile=True),
    "cuenta-06-cambiar-contrasena-error-escritorio": lambda: change_password(error=True),
}

if __name__ == "__main__":
    out = DIR / "svg"
    out.mkdir(exist_ok=True)
    for name, draw in SCREENS.items():
        (out / f"{name}.svg").write_text(draw(), encoding="utf-8", newline="\n")
        print(name)
