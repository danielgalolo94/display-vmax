#!/usr/bin/env python3
"""Genera wallpaper AMD Ryzen 9 — 1920x1080 para escritorio."""
import math, random, os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H     = 1920, 1080
OUT_FILE = os.path.join(os.path.expanduser('~'), 'Imágenes', 'Wallpaper', 'amd_ryzen_wallpaper.png')

_F_TEKO = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts', 'Teko-Medium.ttf')
_F_SEMI = '/usr/share/fonts/FiraCode/FiraCodeNerdFont-SemiBold.ttf'

def fnt(sz, style='teko'):
    p = _F_TEKO if style == 'teko' else _F_SEMI
    try:    return ImageFont.truetype(p, sz)
    except: return ImageFont.load_default()

BG     = (5,    1,   1)
BG2    = (12,   3,   3)
FIRE   = (237,  28,  36)
EMBER  = (255, 108,   0)
GLOW   = (255, 175,  55)
DFIRE  = (80,   10,   6)
VDFIRE = (25,    4,   3)
DIM    = (55,   14,  10)
WHITE  = (255, 232, 218)

random.seed(77)
img = Image.new('RGB', (W, H), BG)
d   = ImageDraw.Draw(img)

# ── Gradiente radial de fondo — caliente desde el centro ─────────────────────
cx_, cy_ = W // 2, H // 2
for y in range(H):
    for x in range(0, W, 4):   # paso 4 para velocidad
        dist = math.sqrt((x - cx_)**2 + (y - cy_)**2)
        max_d = math.sqrt(cx_**2 + cy_**2)
        t    = 1 - min(dist / max_d, 1)
        t2   = t * t
        r_   = int(BG[0] + (DFIRE[0] - BG[0]) * t2)
        g_   = int(BG[1] + (DFIRE[1] - BG[1]) * t2)
        b_   = int(BG[2] + (DFIRE[2] - BG[2]) * t2)
        d.line([(x, y), (x+3, y)], fill=(r_, g_, b_))

# ── Grid hexagonal — muy oscuro ───────────────────────────────────────────────
HR = 48; HH = HR * math.sqrt(3); HW = HR * 2
random.seed(42)
for row in range(-1, int(H / HH) + 3):
    for col in range(-1, int(W / (HW * 0.75)) + 3):
        hx  = col * HW * 0.75
        hy  = row * HH + (HH / 2 if col % 2 else 0)
        pts = [(hx + HR * math.cos(math.radians(60*i)),
                hy + HR * math.sin(math.radians(60*i))) for i in range(6)]
        lit = random.random() < 0.035
        col_h = DFIRE if lit else VDFIRE
        d.polygon(pts, outline=col_h)
        if lit:
            d.polygon(pts, fill=(*VDFIRE, ))

# ── Circuit traces ─────────────────────────────────────────────────────────────
random.seed(55)
for _ in range(30):
    x = random.randint(50, W-50); y = random.randint(50, H-50)
    bright = random.random() < 0.3
    col_t  = DFIRE if bright else VDFIRE
    steps  = [('H' if random.random() > 0.5 else 'V', random.randint(60, 280))
              for _ in range(random.randint(3, 6))]
    for direction, length in steps:
        nx = x + (length if direction == 'H' else 0)
        ny = y + (length if direction == 'V' else 0)
        nx = max(0, min(W, nx)); ny = max(0, min(H, ny))
        d.line([(x, y), (nx, ny)], fill=col_t, width=1)
        d.ellipse([nx-3, ny-3, nx+3, ny+3], fill=col_t)
        x, y = nx, ny

# ── Anillos concéntricos alrededor del logo ───────────────────────────────────
for r, alpha, col in [
    (320, 8,  DFIRE), (280, 15, DFIRE),
    (240, 25, FIRE),  (200, 12, DFIRE),
    (160, 30, FIRE),  (120, 15, EMBER),
]:
    ring = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    rd   = ImageDraw.Draw(ring)
    rd.arc([cx_-r, cy_-r, cx_+r, cy_+r], 0, 360, fill=(*col, alpha), width=2)
    img  = Image.alpha_composite(img.convert('RGBA'), ring).convert('RGB')
    d    = ImageDraw.Draw(img)

# ── Chevron AMD (forma de >) escalado ─────────────────────────────────────────
# El logo de AMD tiene la forma de un triángulo/flecha hacia adelante
chevron_size = 180
pts_chev = [
    (cx_ - chevron_size,          cy_ - chevron_size),
    (cx_,                         cy_),
    (cx_ - chevron_size,          cy_ + chevron_size),
    (cx_ - chevron_size + 40,     cy_ + chevron_size),
    (cx_ + 40,                    cy_),
    (cx_ - chevron_size + 40,     cy_ - chevron_size),
]

# Glow del chevron
chev_gl = Image.new('RGBA', (W, H), (0, 0, 0, 0))
cgd     = ImageDraw.Draw(chev_gl)
for expand in [30, 18, 10, 4]:
    expanded = [(x + (-expand if x < cx_ else expand), y + (-expand if y < cy_ else expand))
                for x, y in pts_chev]
    cgd.polygon(expanded, fill=(*FIRE, 12))
chev_gl = chev_gl.filter(ImageFilter.GaussianBlur(radius=20))
img = Image.alpha_composite(img.convert('RGBA'), chev_gl).convert('RGB')
d   = ImageDraw.Draw(img)

# Relleno con gradiente naranja→rojo
for i in range(len(pts_chev)):
    p1  = pts_chev[i]; p2 = pts_chev[(i+1) % len(pts_chev)]
    mid = ((p1[0]+p2[0])//2, (p1[1]+p2[1])//2)
    t   = i / len(pts_chev)
    gc  = (int(EMBER[0] + (FIRE[0]-EMBER[0])*t),
           int(EMBER[1] + (FIRE[1]-EMBER[1])*t),
           int(EMBER[2] + (FIRE[2]-EMBER[2])*t))
    d.line([p1, p2], fill=gc, width=3)
d.polygon(pts_chev, fill=VDFIRE, outline=FIRE)

# Borde naranja/rojo
d.polygon(pts_chev, outline=EMBER)

# ── Texto "RYZEN 9" ───────────────────────────────────────────────────────────
f_big = fnt(220, 'teko')
text  = 'RYZEN 9'
bb    = d.textbbox((0, 0), text, font=f_big)
tx    = cx_ - (bb[2] - bb[0]) // 2 + 130   # desplazado derecha del chevron
ty    = cy_ - (bb[3] - bb[1]) // 2

# Glow rojo intenso detrás del texto
text_gl = Image.new('RGBA', (W, H), (0, 0, 0, 0))
tgd     = ImageDraw.Draw(text_gl)
for dx, dy in [(-6,-3),(6,-3),(-6,3),(6,3),(0,-8),(0,8),(-8,0),(8,0)]:
    tgd.text((tx+dx, ty+dy), text, font=f_big, fill=(*DFIRE, 180))
text_gl = text_gl.filter(ImageFilter.GaussianBlur(radius=12))
img  = Image.alpha_composite(img.convert('RGBA'), text_gl).convert('RGB')
d    = ImageDraw.Draw(img)

# Texto con sombra
for dx, dy in [(-3,-2),(3,-2),(-3,2),(3,2)]:
    d.text((tx+dx, ty+dy), text, font=f_big, fill=DFIRE)
d.text((tx, ty), text, font=f_big, fill=WHITE)

# ── Subtexto "AMD RYZEN™ 9 SERIES" ───────────────────────────────────────────
f_sub  = fnt(52, 'label')
sub    = 'AMD  RYZEN™ 9  SERIES'
bb_s   = d.textbbox((0, 0), sub, font=f_sub)
sx     = cx_ - (bb_s[2] - bb_s[0]) // 2 + 130
sy_    = ty + (bb[3] - bb[1]) + 12
aw_s   = d.textbbox((0, 0), 'AMD  ', font=f_sub)[2]
d.text((sx,       sy_), 'AMD  ',                font=f_sub, fill=EMBER)
d.text((sx+aw_s,  sy_), 'RYZEN™ 9  SERIES',    font=f_sub, fill=FIRE)

# ── Línea divisoria ──────────────────────────────────────────────────────────
lx1 = cx_ - 280 + 130; lx2 = cx_ + 280 + 130
ly_ = ty + (bb[3] - bb[1]) + 8
d.line([(lx1, ly_), (lx2, ly_)], fill=DFIRE, width=1)

# ── Nodos decorativos en las esquinas ─────────────────────────────────────────
for nx_, ny_, r in [(60,60,6),(W-60,60,6),(60,H-60,6),(W-60,H-60,6),
                    (cx_,30,3),(cx_,H-30,3),(30,cy_,3),(W-30,cy_,3)]:
    d.ellipse([nx_-r, ny_-r, nx_+r, ny_+r], fill=DFIRE, outline=FIRE)

# Líneas desde esquinas hacia el centro
for ex, ey in [(0, 0), (W, 0), (0, H), (W, H)]:
    dx_ = cx_ - ex; dy_ = cy_ - ey
    length = math.sqrt(dx_**2 + dy_**2)
    nx_ = int(ex + dx_ / length * 200)
    ny_ = int(ey + dy_ / length * 200)
    d.line([(ex, ey), (nx_, ny_)], fill=VDFIRE, width=1)

# ── Marco exterior ────────────────────────────────────────────────────────────
def corners(sz=40, col=FIRE, lw=2):
    segs = [(0,sz,0,0,sz,0),(W-sz,0,W,0,W,sz),
            (0,H-sz,0,H,sz,H),(W-sz,H,W,H,W,H-sz)]
    for ax,ay,bx,by,cx2,cy2 in segs:
        d.line([(ax,ay),(bx,by)], fill=col, width=lw)
        d.line([(bx,by),(cx2,cy2)], fill=col, width=lw)

corners(sz=50, col=FIRE, lw=2)
d.line([(0,0),(W,0)],   fill=FIRE,  width=2)
d.line([(0,H-1),(W,H-1)], fill=FIRE, width=2)

# ── Guardar ───────────────────────────────────────────────────────────────────
os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
img.save(OUT_FILE, 'PNG')
print(f"Wallpaper guardado en: {OUT_FILE}")
