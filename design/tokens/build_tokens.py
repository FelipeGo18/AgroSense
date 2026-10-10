"""Genera los CSS de tokens desde tokens.json y comprueba el contraste (HU-152).

Uso:
    python design/tokens/build_tokens.py           # comprueba contraste y escribe los CSS
    python design/tokens/build_tokens.py --check   # falla si hay contraste insuficiente o CSS desactualizado

Solo usa la biblioteca estándar.
"""

import json
import re
import sys
from pathlib import Path

DIR = Path(__file__).parent
SOURCE = DIR / "tokens.json"
OUT_CSS = DIR / "tokens.css"
OUT_THEME = DIR / "tailwind-theme.css"

MIN_RATIO = {"texto": 4.5, "grafico": 3.0}

# Grupo de tokens.json -> prefijo de la variable CSS (nombres de Tailwind v4 donde existen).
PREFIXES = {
    "color": "color",
    "fuente.familia": "font",
    "fuente.tamano": "text",
    "fuente.peso": "font-weight",
    "fuente.interlineado": "leading",
    "espacio": "spacing",
    "radio": "radius",
    "sombra": "shadow",
}

REF = re.compile(r"^\{([^}]+)\}$")
HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


def flatten(node, path=()):
    """Devuelve {ruta.con.puntos: valor} para cada hoja con $value."""
    out = {}
    for key, child in node.items():
        if key.startswith("$") or not isinstance(child, dict):
            continue
        if "$value" in child:
            out[".".join(path + (key,))] = child["$value"]
        else:
            out.update(flatten(child, path + (key,)))
    return out


def resolve(tokens):
    resolved = {}

    def get(name, seen=()):
        if name in seen:
            raise ValueError(f"Referencia circular: {' -> '.join(seen + (name,))}")
        if name not in tokens:
            raise KeyError(f"Referencia a un token que no existe: {name}")
        value = tokens[name]
        match = REF.match(value) if isinstance(value, str) else None
        return get(match.group(1), seen + (name,)) if match else value

    for name in tokens:
        resolved[name] = get(name)
    return resolved


def luminance(hex_color):
    def channel(c):
        c = int(c, 16) / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (channel(hex_color[i : i + 2]) for i in (1, 3, 5))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def check_contrast(resolved, pairs):
    failures, lines = [], []
    for kind, fg, bg in pairs:
        ratio = contrast(resolved[fg], resolved[bg])
        ok = ratio >= MIN_RATIO[kind]
        lines.append(f"{'ok ' if ok else 'MAL'} {ratio:5.2f}:1  {kind:7}  {fg}  sobre  {bg}")
        if not ok:
            failures.append(lines[-1])
    return lines, failures


def css_vars(resolved):
    lines = []
    for name, value in resolved.items():
        for group, prefix in PREFIXES.items():
            if name == group or name.startswith(group + "."):
                rest = name[len(group) + 1 :].replace(".", "-")
                break
        else:
            continue
        # En color solo van colores; forma y etiqueta del semáforo son metadatos para el kit.
        if prefix == "color" and not HEX.match(str(value)) and not str(value).startswith("rgb"):
            continue
        lines.append(f"  --{prefix}-{rest}: {value};")
    return lines


def render(resolved):
    header = "/* Generado por design/tokens/build_tokens.py desde tokens.json (HU-152). No editar a mano. */\n"
    body = "\n".join(css_vars(resolved))
    css = f"{header}:root {{\n{body}\n}}\n"
    theme = f"{header}/* Para Tailwind v4: @import este archivo después de \"tailwindcss\". */\n@theme {{\n{body}\n}}\n"
    return css, theme


def main():
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    resolved = resolve(flatten(data))
    lines, failures = check_contrast(resolved, data["contraste"]["pares"])
    print("\n".join(lines))

    css, theme = render(resolved)
    if "--check" in sys.argv:
        stale = [p.name for p, text in ((OUT_CSS, css), (OUT_THEME, theme)) if not p.exists() or p.read_text(encoding="utf-8") != text]
        if stale:
            failures.append(f"CSS desactualizado: {', '.join(stale)}. Ejecute build_tokens.py")
    else:
        OUT_CSS.write_text(css, encoding="utf-8", newline="\n")
        OUT_THEME.write_text(theme, encoding="utf-8", newline="\n")
        print(f"Escritos {OUT_CSS.name} y {OUT_THEME.name}")

    if failures:
        print("\nFallas:\n" + "\n".join(failures), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
