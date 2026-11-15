"""La finca alrededor del lote vivo, hecha de bloques: terreno de pasto, camas de cultivo juntas sobre un piso de
tierra pisada, cerca de madera con faroles y portón, y la casa campesina con techo escalonado, porche, materas,
chimenea, barriles, huerta de flores y un árbol. Un perro duerme junto al porche.

Inspirada en las granjas de bloques (Minecraft) solo como estilo: todo se dibuja aquí, con la paleta de AgroSense.
Es ambiente: no muestra ningún dato. Las medidas van en celdas del lote (una celda = un cubo de cultivo) y en
unidades del catálogo para la altura.
"""

import random
import sys
from pathlib import Path

DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(DIR))
sys.path.insert(0, str(DIR.parent / "kit"))

import cultivos as cv  # noqa: E402
from build_kit_svg import poly, shade  # noqa: E402

GAP = 14  # separación entre cubos: el camino de tierra entre las camas
WOOD, WOOD_D = "#B98A52", "#8A6238"
PATH = "#CDAA6E"
WALL, STONE, ROOF = "#F1E9D8", "#A9A69C", "#B5532F"


class Farm:
    """Proyección isométrica de la finca. (a, b) en celdas del lote, z en unidades de altura; el suelo es z = 0."""

    def __init__(self, layout):
        k = 1 + GAP / (2 * cv.A)
        self.kx, self.ky = cv.A * k, cv.B * k
        cells = [(c[0], c[1]) for c in layout]
        self.mx = sum((i - j) * self.kx for i, j in cells) / len(cells)
        self.my = sum((i + j) * self.ky for i, j in cells) / len(cells)
        self.a0, self.a1 = min(i for i, _ in cells) - 0.9, max(i for i, _ in cells) + 0.9  # el cercado del lote
        self.b0, self.b1 = min(j for _, j in cells) - 0.9, max(j for _, j in cells) + 0.9

    def cube(self, i, j):
        """Centro de la cara superior del cubo (i, j)."""
        return ((i - j) * self.kx - self.mx, (i + j) * self.ky - self.my)

    def pt(self, a, b, z=0.0):
        return ((a - b) * self.kx - self.mx, (a + b) * self.ky - self.my + cv.DEPTH - z)

    def quad(self, pts3, fill, stroke=None, sw=0):
        return poly([self.pt(*p) for p in pts3], fill, stroke, sw)

    def box(self, a0, b0, a1, b1, z0, z1, color, top=None, tone=(0.0, -0.1, -0.22)):
        """Bloque: cara de arriba, cara que mira a la izquierda (+b) y cara que mira a la derecha (+a)."""
        top = top or color
        return [self.quad([(a0, b1, z1), (a1, b1, z1), (a1, b1, z0), (a0, b1, z0)], shade(color, tone[1])),
                self.quad([(a1, b0, z1), (a1, b1, z1), (a1, b1, z0), (a1, b0, z0)], shade(color, tone[2])),
                self.quad([(a0, b0, z1), (a1, b0, z1), (a1, b1, z1), (a0, b1, z1)], shade(top, tone[0]))]

    def on_a(self, a, b0, b1, z0, z1, fill, stroke=None, sw=0):
        """Rectángulo pintado sobre una cara que mira a la derecha (plano a = constante)."""
        return self.quad([(a, b0, z1), (a, b1, z1), (a, b1, z0), (a, b0, z0)], fill, stroke, sw)

    def on_b(self, b, a0, a1, z0, z1, fill, stroke=None, sw=0):
        return self.quad([(a0, b, z1), (a1, b, z1), (a1, b, z0), (a0, b, z0)], fill, stroke, sw)

    # ---------- Terreno ----------

    def ground(self, seed=3):
        """Pasto en bloques: baldosas de dos tonos, matas y flores sueltas. Sigue más allá del marco."""
        rnd = random.Random(seed)
        out = []
        for a in range(-12, 14):
            for b in range(-12, 14):
                r = rnd.random()
                if r < 0.22:
                    tone = 0.05 if r < 0.11 else -0.05
                    out.append(self.quad([(a, b), (a + 1, b), (a + 1, b + 1), (a, b + 1)], shade(cv.GRASS, -0.15 + tone)))
                if rnd.random() < 0.3:
                    x, y = self.pt(a + rnd.random(), b + rnd.random())
                    for d in (-3, 0, 3):
                        out += cv.blade(x + d, y, 90 + d * 6, rnd.uniform(6, 10), 1.8, rnd.choice(("#6E9A3A", "#8DBA4F", "#7DAE45")))
                    if rnd.random() < 0.3:
                        out += cv.flower(x + 5, y - 6, 2.2, rnd.choice(("#FFFFFF", "#F2D23A", "#E8A0C0")))
        return out

    def lot_floor(self):
        """Piso de tierra pisada bajo las camas: se ve como camino entre los cubos y hasta el portón."""
        a0, a1, b0, b1 = self.a0, self.a1, self.b0, self.b1
        out = [self.quad([(a0, b0), (a1, b0), (a1, b1), (a0, b1)], PATH)]
        rnd = random.Random(8)
        for _ in range(40):
            a, b = rnd.uniform(a0, a1 - 0.3), rnd.uniform(b0, b1 - 0.3)
            out.append(self.quad([(a, b), (a + 0.3, b), (a + 0.3, b + 0.3), (a, b + 0.3)], shade(PATH, rnd.choice((-0.06, 0.06)))))
        return out

    # ---------- Cerca ----------

    def fence(self, pa, pb, lantern_ends=True, skip=None):
        """Cerca de madera de pa a pb (misma a o misma b): postes cada media celda y dos travesaños.
        `skip` es el tramo (desde, hasta) que queda abierto para el portón."""
        (a0, b0), (a1, b1) = pa, pb
        along_a = b0 == b1
        length = (a1 - a0) if along_a else (b1 - b0)
        n = max(1, round(abs(length) / 0.5))
        stops = [i / n for i in range(n + 1)]
        at = lambda t: (a0 + (a1 - a0) * t, b0 + (b1 - b0) * t)  # noqa: E731
        coord = lambda t: (a0 + length * t) if along_a else (b0 + length * t)  # noqa: E731
        opened = lambda t: skip and skip[0] - 1e-6 <= coord(t) <= skip[1] + 1e-6  # noqa: E731
        out = []
        for t0, t1 in zip(stops, stops[1:]):  # travesaños
            if skip and opened((t0 + t1) / 2):
                continue
            for z in (11, 22):
                (x0, y0), (x1, y1) = self.pt(*at(t0), z), self.pt(*at(t1), z)
                out.append(f'<line x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1:.1f}" y2="{y1:.1f}" stroke="{WOOD_D}" stroke-width="5.5" stroke-linecap="round"/>')
                out.append(f'<line x1="{x0:.1f}" y1="{y0 - 1:.1f}" x2="{x1:.1f}" y2="{y1 - 1:.1f}" stroke="{WOOD}" stroke-width="3.5" stroke-linecap="round"/>')
        for i, t in enumerate(stops):  # postes
            if skip and skip[0] + 1e-6 < coord(t) < skip[1] - 1e-6:
                continue
            a, b = at(t)
            end = i in (0, len(stops) - 1)
            hgt = 34 if end else 28
            out += self.box(a - 0.05, b - 0.05, a + 0.05, b + 0.05, 0, hgt, WOOD)
            if end and lantern_ends:  # farol en las esquinas
                out += self.box(a - 0.07, b - 0.07, a + 0.07, b + 0.07, hgt, hgt + 3, "#5A4A3A")
                out += self.box(a - 0.05, b - 0.05, a + 0.05, b + 0.05, hgt + 3, hgt + 13, "#F7D774", tone=(0.1, 0.0, -0.1))
                out += self.box(a - 0.07, b - 0.07, a + 0.07, b + 0.07, hgt + 13, hgt + 16, "#5A4A3A")
        return out

    GATE = (0.2, 0.8)  # el portón, en b, sobre el lado del lote que mira a la casa

    def fence_back(self):
        out = self.fence((self.a0, self.b0), (self.a1, self.b0))
        out += self.fence((self.a0, self.b0), (self.a0, self.b1), skip=self.GATE)
        # hoja del portón, abierta hacia afuera
        g0 = self.GATE[0]
        for z in (11, 22):
            (x0, y0), (x1, y1) = self.pt(self.a0, g0, z), self.pt(self.a0 - 0.42, g0 + 0.12, z)
            out.append(f'<line x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1:.1f}" y2="{y1:.1f}" stroke="{WOOD_D}" stroke-width="5" stroke-linecap="round"/>')
            out.append(f'<line x1="{x0:.1f}" y1="{y0 - 1:.1f}" x2="{x1:.1f}" y2="{y1 - 1:.1f}" stroke="{WOOD}" stroke-width="3" stroke-linecap="round"/>')
        out += self.box(self.a0 - 0.46, g0 + 0.08, self.a0 - 0.38, g0 + 0.16, 0, 26, WOOD)
        return out

    def fence_front(self):
        return self.fence((self.a1, self.b0), (self.a1, self.b1)) + self.fence((self.a0, self.b1), (self.a1, self.b1))

    # ---------- Casa ----------

    def house(self):
        a0, a1 = self.a0 - 2.35, self.a0 - 1.25   # la casa queda detrás y a la izquierda del lote
        b0, b1 = self.GATE[0] - 0.5, self.GATE[1] + 0.2
        H = 50
        bm = (b0 + b1) / 2
        out = []
        # sendero de la puerta al portón
        out.append(self.quad([(a1, self.GATE[0]), (self.a0, self.GATE[0]), (self.a0, self.GATE[1]), (a1, self.GATE[1])], PATH))
        rnd = random.Random(5)
        for _ in range(8):
            a, b = rnd.uniform(a1 + 0.3, self.a0 - 0.3), rnd.uniform(self.GATE[0], self.GATE[1] - 0.2)
            out.append(self.quad([(a, b), (a + 0.25, b), (a + 0.25, b + 0.2), (a, b + 0.2)], shade(PATH, -0.07)))
        # sombra, zócalo de piedra y paredes
        out.append(self.quad([(a0 - 0.1, b0 + 0.2), (a1 + 0.5, b0 + 0.2), (a1 + 0.5, b1 + 0.35), (a0 - 0.1, b1 + 0.35)], "#000000").replace('fill="#000000"', 'fill="#000" fill-opacity="0.14"'))
        out += self.box(a0 - 0.04, b0 - 0.04, a1 + 0.04, b1 + 0.04, 0, 8, STONE)
        out += self.box(a0, b0, a1, b1, 8, H, WALL)
        # vigas de madera en las esquinas
        for b in (b0, b1 - 0.07):
            out.append(self.on_a(a1 + 0.001, b, b + 0.07, 8, H, WOOD_D))
        for a in (a0, a1 - 0.07):
            out.append(self.on_b(b1 + 0.001, a, a + 0.07, 8, H, WOOD_D))
        # ventanas del costado (+b), con postigos y matera
        for wa in (a0 + 0.2, a0 + 0.66):
            out += self.window_b(b1, wa, wa + 0.26, 22, 40)
        # hastial escalonado y techo de teja en gradas
        steps, s, dz = 4, (b1 - b0 + 0.3) / 2 / 4.6, 11
        for n in range(steps):
            lo, hi = b0 + n * s * 0.94, b1 - n * s * 0.94
            if hi - lo > 0.1:
                out += self.box(a0, lo, a1, hi, H + n * dz, H + (n + 1) * dz, WALL)
        out.append(self.on_a(a1 + 0.002, bm - 0.1, bm + 0.1, H + 8, H + 24, "#7FA8C9", "#5A4A3A", 1.5))  # ventana del altillo
        for n in range(steps):  # agua de atrás (se dibuja primero)
            lo = b0 - 0.15 + n * s
            out += self.box(a0 - 0.12, lo, a1 + 0.12, lo + s * 1.12, H - 3 + n * dz, H + 4 + (n + 1) * dz - 7, ROOF, tone=(0.06, -0.08, -0.2))
        # chimenea de piedra con humo
        ca, cb = a0 + 0.25, bm - 0.36
        out += self.box(ca, cb, ca + 0.2, cb + 0.2, H + 20, H + steps * dz + 22, STONE)
        out += self.box(ca - 0.03, cb - 0.03, ca + 0.23, cb + 0.23, H + steps * dz + 22, H + steps * dz + 27, shade(STONE, -0.2))
        sx, sy = self.pt(ca + 0.12, cb + 0.12, H + steps * dz + 30)
        for i, r in enumerate((6, 8, 10)):
            out.append(f'<ellipse cx="{sx + i * 5:.1f}" cy="{sy - 8 - i * 13:.1f}" rx="{r}" ry="{r * 0.8:.1f}" fill="#FFFFFF" fill-opacity="{0.55 - i * 0.13:.2f}"/>')
        out += self.box(a0 - 0.12, bm - s * 0.55, a1 + 0.12, bm + s * 0.55, H - 3 + steps * dz - 6, H + steps * dz + 2, ROOF, tone=(0.1, -0.06, -0.18))  # cumbrera
        for n in range(steps):  # agua del frente
            hi = b1 + 0.15 - n * s
            out += self.box(a0 - 0.12, hi - s * 1.12, a1 + 0.12, hi, H - 3 + n * dz, H + 4 + (n + 1) * dz - 7, ROOF, tone=(0.06, -0.08, -0.2))
        # fachada (+a): puerta, ventanas con postigos y materas
        da = a1 + 0.002
        out.append(self.on_a(da, bm - 0.14, bm + 0.14, 8, 42, "#5A4A3A"))
        out.append(self.on_a(da + 0.001, bm - 0.11, bm + 0.11, 8, 40, "#3F6E9A"))
        out.append(self.on_a(da + 0.002, bm - 0.07, bm + 0.07, 26, 36, "#7FA8C9"))
        kx, ky = self.pt(da, bm + 0.07, 22)
        out.append(f'<circle cx="{kx:.1f}" cy="{ky:.1f}" r="1.8" fill="#F2C232"/>')
        for wb in (b0 + 0.14, b1 - 0.34):
            out += self.window_a(da, wb, wb + 0.2, 22, 40)
        # porche: piso de tabla, postes y alero
        pa0, pa1, pb0, pb1 = a1, a1 + 0.36, bm - 0.3, bm + 0.3
        out += self.box(pa0, pb0, pa1, pb1, 0, 6, WOOD)
        for pb in (pb0, pb1 - 0.06):
            out += self.box(pa1 - 0.06, pb, pa1, pb + 0.06, 6, 44, WOOD_D)
        out += self.box(pa0, pb0 - 0.06, pa1 + 0.06, pb1 + 0.06, 44, 49, ROOF, tone=(0.06, -0.08, -0.2))
        # barriles y leña junto a la casa
        for i, (ba, bb) in enumerate(((a1 + 0.06, b1 - 0.2), (a1 + 0.24, b1 - 0.14))):
            out += self.box(ba, bb, ba + 0.14, bb + 0.14, 0, 18 - i * 4, "#9A6A3C")
            x0, y0 = self.pt(ba, bb + 0.14, 10 - i * 2)
            x1, y1 = self.pt(ba + 0.14, bb + 0.14, 10 - i * 2)
            x2, y2 = self.pt(ba + 0.14, bb, 10 - i * 2)
            out.append(f'<polyline points="{x0:.1f},{y0:.1f} {x1:.1f},{y1:.1f} {x2:.1f},{y2:.1f}" fill="none" stroke="#5A4A3A" stroke-width="1.6"/>')
        return out

    def window_a(self, a, b0, b1, z0=28, z1=50):
        out = [self.on_a(a, b0 - 0.03, b1 + 0.03, z0 - 2, z1 + 2, "#FFFFFF"), self.on_a(a + 0.001, b0, b1, z0, z1, "#7FA8C9"),
               self.on_a(a + 0.002, (b0 + b1) / 2 - 0.012, (b0 + b1) / 2 + 0.012, z0, z1, "#FFFFFF"),
               self.on_a(a + 0.002, b0 - 0.11, b0 - 0.03, z0 - 2, z1 + 2, "#3F6E9A"), self.on_a(a + 0.002, b1 + 0.03, b1 + 0.11, z0 - 2, z1 + 2, "#3F6E9A")]
        out += self.box(a, b0 - 0.04, a + 0.07, b1 + 0.04, z0 - 9, z0 - 3, "#8A6238")  # matera
        for i, t in enumerate((0.15, 0.5, 0.85)):
            x, y = self.pt(a + 0.04, b0 + (b1 - b0) * t, z0 - 1)
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="{("#E8607A", "#F2C232", "#E8607A")[i]}"/>')
            out.append(f'<circle cx="{x - 2:.1f}" cy="{y + 3:.1f}" r="2.4" fill="#5FA34A"/>')
        return out

    def window_b(self, b, a0, a1, z0=28, z1=50):
        return [self.on_b(b + 0.001, a0 - 0.03, a1 + 0.03, z0 - 2, z1 + 2, "#FFFFFF"), self.on_b(b + 0.002, a0, a1, z0, z1, "#6F98B9"),
                self.on_b(b + 0.003, (a0 + a1) / 2 - 0.012, (a0 + a1) / 2 + 0.012, z0, z1, "#FFFFFF"),
                self.on_b(b + 0.003, a0 - 0.11, a0 - 0.03, z0 - 2, z1 + 2, "#35608A"), self.on_b(b + 0.003, a1 + 0.03, a1 + 0.11, z0 - 2, z1 + 2, "#35608A")]

    # ---------- Huerta de flores, árbol y perro ----------

    def flower_garden(self):
        a0, a1 = self.a0 - 2.3, self.a0 - 1.4
        b0, b1 = self.GATE[1] + 0.75, self.GATE[1] + 1.2
        out = self.box(a0, b0, a1, b1, 0, 5, "#6B4026")
        rnd = random.Random(12)
        for _ in range(16):
            x, y = self.pt(rnd.uniform(a0 + 0.08, a1 - 0.08), rnd.uniform(b0 + 0.08, b1 - 0.08), 5)
            out += cv.blade(x, y, 90, 9, 1.6, "#5FA34A") + cv.flower(x, y - 10, 3, rnd.choice(("#E8607A", "#F2C232", "#FFFFFF", "#B49AD8")))
        out += self.fence((a0 - 0.12, b1 + 0.12), (a1 + 0.12, b1 + 0.12), lantern_ends=False)
        out += self.fence((a1 + 0.12, b0 - 0.12), (a1 + 0.12, b1 + 0.12), lantern_ends=False)
        return out

    def tree(self, a, b):
        """Árbol de bloques: tronco y copa en tres pisos."""
        out = [self.quad([(a - 0.35, b - 0.1), (a + 0.6, b - 0.1), (a + 0.6, b + 0.75), (a - 0.35, b + 0.75)], "#000000").replace('fill="#000000"', 'fill="#000" fill-opacity="0.14"')]
        out += self.box(a, b, a + 0.2, b + 0.2, 0, 46, "#7A5632")
        for r, z0, z1, col in ((0.3, 38, 54, "#4E8F3A"), (0.38, 54, 74, "#57993F"), (0.26, 74, 90, "#5FA34A"), (0.13, 90, 100, "#6FB04A")):
            out += self.box(a + 0.1 - r, b + 0.1 - r, a + 0.1 + r, b + 0.1 + r, z0, z1, col)
        for da, db, z in ((0.48, 0.3, 62), (0.3, 0.48, 70), (0.48, 0.05, 58)):  # frutas
            x, y = self.pt(a + da, b + db, z)
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.4" fill="#E0503A"/>')
        return out

    def dog_spot(self):
        """Dónde duerme el perro: en el pasto, junto al sendero y al porche."""
        return self.pt(self.a0 - 0.7, self.GATE[1] + 0.45)

    # ---------- Capas ----------

    def back(self):
        """Lo que queda detrás de las camas: piso del lote, casa, árbol y cerca del fondo."""
        return self.tree(self.a0 + 0.7, self.b0 - 1.5) + self.lot_floor() + self.house() + self.fence_back()

    def front(self):
        """Lo que queda delante de las camas: cerca del frente y huerta de flores."""
        return self.fence_front() + self.flower_garden()
