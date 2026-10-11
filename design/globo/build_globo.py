"""La Tierra de AgroSense: continentes reales en el estilo diorama low-poly, girando.

- Contornos: Natural Earth 1:110m (dominio público), del paquete npm `world-atlas` 2.0.2 que ya usa la web.
- Color de cada faceta de tierra: la imagen Blue Marble: Next Generation (diciembre de 2004) de NASA Earth
  Observatory, reducida a medio grado por píxel con muestrear.mjs.
- Facetas: una icosfera. El océano usa facetas grandes; la tierra, facetas finas recortadas por la costa real,
  así el contorno es fiel y el interior queda facetado como el resto del kit.

    curl -o design/globo/fuente/blue-marble-200412.jpg       https://eoimages.gsfc.nasa.gov/images/imagerecords/73000/73909/world.topo.bathy.200412.3x5400x2700.jpg
    node design/globo/muestrear.mjs        # una vez: crea fuente/blue-marble-720x360.rgb (fuente/ no va a git)
    python design/globo/build_globo.py     # escribe svg/globo-*.svg
"""

import json
import math
import sys
from functools import lru_cache
from pathlib import Path

DIR = Path(__file__).resolve().parent
ROOT = DIR.parent.parent
sys.path.insert(0, str(DIR.parent / "kit"))
sys.path.insert(0, str(DIR.parent / "paisaje"))

from build_kit_svg import P, shade, svg  # noqa: E402

ATLAS = ROOT / "web" / "node_modules" / "world-atlas"
RGB = DIR / "fuente" / "blue-marble-720x360.rgb"
OCEAN = "#2B6A99"
LIGHT = (-0.55, 0.45, 0.70)  # luz lateral desde arriba a la izquierda, como el kit (x a la derecha, y arriba, z hacia la cámara)
COLOMBIA_ID = "170"
PILOTO = (-73.36, 5.55)  # altiplano de Boyacá (región piloto), lon y lat


# ---------- TopoJSON → anillos en lon/lat ----------

def topo_polygons(file, name, keep=None):
    """Polígonos de un objeto TopoJSON: lista de (exterior, [huecos]) con puntos (lon, lat)."""
    topo = json.loads((ATLAS / file).read_text(encoding="utf-8"))
    (sx, sy), (tx, ty) = topo["transform"]["scale"], topo["transform"]["translate"]
    arcs = []
    for arc in topo["arcs"]:
        x = y = 0
        pts = []
        for dx, dy in arc:
            x, y = x + dx, y + dy
            pts.append((x * sx + tx, y * sy + ty))
        arcs.append(pts)

    def ring(idx):
        out = []
        for i in idx:
            a = arcs[i] if i >= 0 else arcs[~i][::-1]
            out.extend(a if not out else a[1:])
        return unwrap(out)

    polys = []
    for geom in topo["objects"][name]["geometries"]:
        if keep and str(geom.get("id")) != keep:
            continue
        parts = geom["arcs"] if geom["type"] == "MultiPolygon" else [geom["arcs"]]
        for part in parts:
            rings = [ring(r) for r in part]
            polys.append((rings[0], rings[1:]))
    return polys


def unwrap(ring):
    """Un anillo que cruza el antimeridiano (Fiyi, Chukotka) salta de 180 a −180 y en el plano lon/lat se estira
    de lado a lado del mundo. Se desenrolla para que sea continuo (puede pasar de 180); las copias desplazadas ±360
    lo cubren. Si el anillo rodea un polo (Antártida), desenrollarlo lo abriría: se deja como está."""
    out, shift = [ring[0]], 0
    for (x0, _), (x1, y1) in zip(ring, ring[1:]):
        if x1 - x0 > 180:
            shift -= 360
        elif x0 - x1 > 180:
            shift += 360
        out.append((x1 + shift, y1))
    return ring if shift else out


# ---------- Icosfera ----------

def icosphere(level):
    t = (1 + 5**0.5) / 2
    verts = [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t),
             (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]
    verts = [norm(v) for v in verts]
    faces = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6), (7, 1, 8),
             (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1)]
    for _ in range(level):
        cache, nxt = {}, []

        def mid(a, b):
            key = (min(a, b), max(a, b))
            if key not in cache:
                verts.append(norm(tuple((verts[a][k] + verts[b][k]) / 2 for k in range(3))))
                cache[key] = len(verts) - 1
            return cache[key]

        for a, b, c in faces:
            ab, bc, ca = mid(a, b), mid(b, c), mid(c, a)
            nxt += [(a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)]
        faces = nxt
    return verts, faces


def norm(v):
    n = math.sqrt(sum(c * c for c in v))
    return tuple(c / n for c in v)


def to_lonlat(v):
    # Eje y del icosaedro = norte; así ningún vértice cae justo en el polo.
    x, y, z = v
    return math.degrees(math.atan2(x, z)), math.degrees(math.asin(max(-1, min(1, y))))


def to_vec(lon, lat):
    lo, la = math.radians(lon), math.radians(lat)
    return (math.cos(la) * math.sin(lo), math.sin(la), math.cos(la) * math.cos(lo))


# ---------- Recorte: polígono (cualquiera) contra triángulo (convexo), Sutherland–Hodgman ----------

def clip(subject, tri):
    def inside(p, a, b):
        return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0]) >= 0

    def cross(p, q, a, b):
        x1, y1, x2, y2, x3, y3, x4, y4 = *p, *q, *a, *b
        d = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if d == 0:
            return q
        u = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / d
        return (x1 + u * (x2 - x1), y1 + u * (y2 - y1))

    if area(tri) < 0:
        tri = tri[::-1]
    out = subject
    for i in range(3):
        a, b = tri[i], tri[(i + 1) % 3]
        inp, out = out, []
        if not inp:
            break
        s = inp[-1]
        for e in inp:
            if inside(e, a, b):
                if not inside(s, a, b):
                    out.append(cross(s, e, a, b))
                out.append(e)
            elif inside(s, a, b):
                out.append(cross(s, e, a, b))
            s = e
    return out


def area(poly):
    return sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1])) / 2


def bbox(ring):
    xs, ys = [p[0] for p in ring], [p[1] for p in ring]
    return min(xs), min(ys), max(xs), max(ys)


# ---------- Color desde Blue Marble ----------

@lru_cache(maxsize=1)
def marble():
    return RGB.read_bytes()


def sample(lon, lat):
    data = marble()
    acc = [0, 0, 0]
    n = 0
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            px = int(((lon + 180) / 360 * 720 + dx)) % 720
            py = min(359, max(0, int((90 - lat) / 180 * 360 + dy)))
            i = (py * 720 + px) * 3
            for k in range(3):
                acc[k] += data[i + k]
            n += 1
    r, g, b = (c / n for c in acc)
    # Ajuste suave hacia la paleta cálida del kit: un poco más de saturación y calidez, sin cambiar el tono real.
    m = (r + g + b) / 3
    r, g, b = (m + (c - m) * 1.25 for c in (r, g, b))
    r, b = r * 1.04, b * 0.92
    return "#" + "".join(f"{max(0, min(255, round(c))):02X}" for c in (r, g, b))


# ---------- Malla precalculada (no depende de la rotación) ----------

@lru_cache(maxsize=1)
def mesh():
    land = topo_polygons("land-110m.json", "land")
    shapes = []  # (anillo, es_hueco, bbox) con copias desplazadas ±360 para el antimeridiano
    for outer, holes in land:
        for ring, hole in [(outer, False)] + [(h, True) for h in holes]:
            for shift in (-360, 0, 360):
                r = [(x + shift, y) for x, y in ring]
                shapes.append((r, hole, bbox(r)))

    verts, faces = icosphere(4)
    pieces = []  # (vector normal de la faceta, color, puntos lon/lat, color de base)
    for a, b, c in faces:
        tri3 = [verts[a], verts[b], verts[c]]
        n = norm(tuple(sum(v[k] for v in tri3) for k in range(3)))
        tri = [to_lonlat(v) for v in tri3]
        lats = [p[1] for p in tri]
        if max(abs(x) for x in lats) > 78:  # casquetes polares: hielo o mar por su latitud
            clon, clat = to_lonlat(n)
            if clat < -60 or clat > 70 and sample(clon, clat).startswith(("#F", "#E", "#D")):
                pieces.append((n, "#EEF3F6", tri, True))
            continue
        lons = [p[0] for p in tri]
        if max(lons) - min(lons) > 180:
            tri = [(x + 360 if x < 0 else x, y) for x, y in tri]
        tb = bbox(tri)
        for ring, hole, rb in shapes:
            if rb[2] < tb[0] or rb[0] > tb[2] or rb[3] < tb[1] or rb[1] > tb[3]:
                continue
            piece = clip(ring, tri)
            if len(piece) < 3 or abs(area(piece)) < 1e-4:
                continue
            cx = sum(p[0] for p in piece) / len(piece)
            cy = sum(p[1] for p in piece) / len(piece)
            color = OCEAN if hole else sample(((cx + 180) % 360) - 180, cy)
            pieces.append((n, color, piece, False))
    return pieces


@lru_cache(maxsize=1)
def ocean_faces():
    verts, faces = icosphere(3)
    return [[verts[a], verts[b], verts[c]] for a, b, c in faces]


# ---------- Proyección ortográfica ----------

def rotate(v, lon0, lat0):
    """Gira el globo para que (lon0, lat0) quede al frente. Devuelve (x, y, z) con z hacia la cámara."""
    x, y, z = v
    lo = math.radians(-lon0)
    x, z = x * math.cos(lo) + z * math.sin(lo), -x * math.sin(lo) + z * math.cos(lo)
    la = math.radians(lat0)
    y, z = y * math.cos(la) - z * math.sin(la), y * math.sin(la) + z * math.cos(la)
    return x, y, z


def lit(color, n_view, jitter=0.0):
    d = sum(a * b for a, b in zip(norm(LIGHT), n_view))
    return shade(color, max(-0.38, min(0.14, (d - 0.62) * 0.55 + jitter)))


def globe(lon0, lat0, R, cx, cy, marker=True):
    hid = f"halo-{lon0:g}-{lat0:g}".replace(".", "_").replace("-", "m")
    out = [f'<defs><radialGradient id="{hid}" cx="0.5" cy="0.5" r="0.5"><stop offset="0.86" stop-color="#9FD3FF" stop-opacity="0.5"/>'
           f'<stop offset="1" stop-color="#9FD3FF" stop-opacity="0"/></radialGradient></defs>'
           f'<circle id="atmosfera" cx="{cx}" cy="{cy}" r="{R * 1.16:.1f}" fill="url(#{hid})"/>',
           f'<circle cx="{cx}" cy="{cy}" r="{R}" fill="{shade(OCEAN, -0.12)}"/>']  # base: tapa las rendijas entre facetas
    for i, tri in enumerate(ocean_faces()):
        rv = [rotate(v, lon0, lat0) for v in tri]
        if min(p[2] for p in rv) < -0.05:
            continue
        n = norm(tuple(sum(p[k] for p in rv) for k in range(3)))
        pts = " ".join(f"{cx + R * x:.1f},{cy - R * y:.1f}" for x, y, _ in rv)
        col = lit(OCEAN, n, (-0.02, 0.0, 0.02)[i % 3])
        out.append(f'<polygon points="{pts}" fill="{col}" stroke="{col}" stroke-width="0.6" stroke-linejoin="round"/>')
    for i, (n, color, piece, polar) in enumerate(mesh()):
        nv = rotate(n, lon0, lat0)
        if nv[2] < 0.02:
            continue
        rv = [rotate(to_vec(x, y), lon0, lat0) for x, y in piece]
        pts = " ".join(f"{cx + R * x:.1f},{cy - R * y:.1f}" for x, y, _ in rv)
        col = lit(color, nv, (-0.03, 0.0, 0.025, 0.01)[i % 4])
        out.append(f'<polygon points="{pts}" fill="{col}"/>')
    # Colombia: el contorno del país, para que se lea dónde vamos a bajar.
    for outer, _ in topo_polygons("countries-110m.json", "countries", keep=COLOMBIA_ID):
        rv = [rotate(to_vec(x, y), lon0, lat0) for x, y in outer]
        if sum(p[2] for p in rv) / len(rv) > 0.1:
            pts = " ".join(f"{cx + R * x:.1f},{cy - R * y:.1f}" for x, y, _ in rv)
            out.append(f'<polygon id="colombia" points="{pts}" fill="none" stroke="#FFFFFF" stroke-width="{max(1.5, R / 160):.1f}" stroke-linejoin="round" opacity="0.9"/>')
    # Sombra de la noche y brillo de la atmósfera.
    gid = f"noche-{lon0:g}-{lat0:g}".replace(".", "_").replace("-", "m")
    out.append(f'<defs><linearGradient id="{gid}" x1="0" y1="0" x2="1" y2="0.3"><stop offset="0.55" stop-color="#0B1226" stop-opacity="0"/>'
               f'<stop offset="1" stop-color="#0B1226" stop-opacity="0.55"/></linearGradient></defs>'
               f'<circle cx="{cx}" cy="{cy}" r="{R}" fill="url(#{gid})"/>')
    out.append(f'<circle cx="{cx}" cy="{cy}" r="{R}" fill="none" stroke="#BFE3FF" stroke-width="{R * 0.012:.1f}" stroke-opacity="0.55"/>')  # borde de luz
    if marker:
        x, y, z = rotate(to_vec(*PILOTO), lon0, lat0)
        if z > 0.2:
            mx, my = cx + R * x, cy - R * y
            k = R / 300
            out.append(f'<g id="region-piloto"><circle cx="{mx:.1f}" cy="{my:.1f}" r="{22 * k:.1f}" fill="{P["calabaza"]}" fill-opacity="0.3"/>'
                       f'<circle cx="{mx:.1f}" cy="{my:.1f}" r="{8 * k:.1f}" fill="{P["calabaza"]}" stroke="#FFFFFF" stroke-width="{3 * k:.1f}"/></g>')
    return out


# ---------- Láminas ----------

def space(w, h, seed=7):
    """Cielo de noche con estrellas, como la escena de órbita."""
    import random
    rnd = random.Random(seed)
    out = [f'<defs><linearGradient id="cielo-espacio" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0B1226"/>'
           f'<stop offset="1" stop-color="#1B3358"/></linearGradient></defs><rect width="{w}" height="{h}" fill="url(#cielo-espacio)"/>']
    for _ in range(int(w * h / 9000)):
        x, y, r = rnd.uniform(0, w), rnd.uniform(0, h), rnd.choice((0.8, 1.1, 1.6))
        out.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r}" fill="#FFFFFF" fill-opacity="{rnd.uniform(0.35, 0.9):.2f}"/>')
    return out


FRAMES = (  # el globo gira de oeste a este: la longitud al frente baja con el tiempo
    ("globo-1-africa", 25, 8, "1 · Otra cara: África y Europa"),
    ("globo-2-atlantico", -28, 6, "2 · A mitad del giro: el Atlántico"),
    ("globo-3-colombia", -74, 5, "3 · Colombia al frente, con la región piloto"),
)

if __name__ == "__main__":
    out = DIR / "svg"
    out.mkdir(exist_ok=True)
    for name, lon0, lat0, _ in FRAMES:
        body = space(800, 800) + [f'<g id="globo">{"".join(globe(lon0, lat0, 300, 400, 400))}</g>']
        (out / f"{name}.svg").write_text(svg(800, 800, body), encoding="utf-8", newline="\n")
        print(name, len(body[-1]) // 1024, "KB")
