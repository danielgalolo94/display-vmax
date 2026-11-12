#!/usr/bin/env python3
"""Genera wallpaper retrowave 1920x1080 para escritorio."""
import math, random
from PIL import Image, ImageDraw, ImageFont

W, H     = 1920, 1080
SKY_H    = 620
OUT_FILE = os.path.join(os.path.expanduser("~"), "Imágenes", "Wallpaper", "retrowave_wallpaper.png")

FONT_PATH = "/tmp/vmax_theme/Falloutchiro/font/Teko-Medium-3.ttf"
def fnt(size):
    try:    return ImageFont.truetype(FONT_PATH, size)
    except: return ImageFont.load_default()

BG    = (13,  0, 25)
PINK  = (255,  0, 110)
DPINK = (100,  0,  45)
CYAN  = (0, 245, 255)
GOLD  = (255, 190,  11)
DPUR  = (35,   0,   65)

random.seed(42)
stars = [(random.randint(0,W), random.randint(0, SKY_H-100),
          random.randint(1,3)) for _ in range(340)]

img = Image.new('RGB', (W, H), BG)
d   = ImageDraw.Draw(img)

# ── Cielo ─────────────────────────────────────────────────────────────────────
for y in range(SKY_H):
    ratio = y / SKY_H
    r = int(13 + ratio*35)
    b = int(25 + ratio*22)
    d.line([(0,y),(W,y)], fill=(r, 0, b))

# Estrellas
for sx, sy, sr in stars:
    d.ellipse([sx-sr,sy-sr,sx+sr,sy+sr], fill=(180,180,220))

# Sol
sun_cx, sun_cy = W//2, 240
sun_r  = 165
HORIZ  = 440

for gr in range(sun_r+60, sun_r+8, -8):
    fade = max(0, 80-(gr-sun_r)*3)
    d.ellipse([sun_cx-gr,sun_cy-gr,sun_cx+gr,sun_cy+gr],
              fill=(min(255,fade+35),0,min(255,fade)))
for sy in range(sun_cy-sun_r, sun_cy+sun_r+1):
    dy2 = (sy-sun_cy)**2
    if dy2 > sun_r**2: continue
    xd    = int(math.sqrt(sun_r**2 - dy2))
    ratio = (sy-(sun_cy-sun_r))/(2*sun_r)
    d.line([(sun_cx-xd,sy),(sun_cx+xd,sy)],
           fill=(255, max(0,int(165-ratio*185)), min(255,int(ratio*185))))
for sy in range(sun_cy-sun_r, sun_cy+sun_r+1, 11):
    dy2 = (sy-sun_cy)**2
    if dy2 > sun_r**2: continue
    xd = int(math.sqrt(sun_r**2 - dy2))
    d.line([(sun_cx-xd,sy),(sun_cx+xd,sy)], fill=BG, width=4)

# Grid perspectiva
VP_X = W//2
for i in range(-18, 19):
    d.line([(VP_X, HORIZ),(VP_X + i*120, SKY_H)], fill=DPINK, width=1)
for step in range(16):
    t  = step/16.0
    t2 = t * t
    gy = int(HORIZ + t2*(SKY_H-HORIZ))
    lx = int(VP_X - t2*VP_X)
    rx = int(VP_X + t2*(W-VP_X))
    intensity = int(35 + t2*185)
    d.line([(lx,gy),(rx,gy)], fill=(min(255,intensity),0,min(255,intensity*42//100)), width=1)
for lw, col in [(8,DPINK),(4,PINK),(2,(255,130,170))]:
    d.line([(0,HORIZ),(W,HORIZ)], fill=col, width=lw)

# ── Suelo ─────────────────────────────────────────────────────────────────────
for y in range(SKY_H, H):
    ratio = (y-SKY_H) / (H-SKY_H)
    r = int(8  + ratio*22)
    b = int(14 + ratio*10)
    d.line([(0,y),(W,y)], fill=(r,0,b))

# ── Texto ─────────────────────────────────────────────────────────────────────
def glow(x, y, text, size, col, dim):
    for dx,dy in [(-3,-2),(3,-2),(-3,2),(3,2),(0,-4),(0,4),(-5,0),(5,0)]:
        d.text((x+dx,y+dy), text, font=fnt(size), fill=dim)
    d.text((x,y), text, font=fnt(size), fill=col)

glow(W//2-320, H-260, "RETROWAVE", 200, PINK, DPINK)
glow(W//2-80,  H-100, "1986", 92, CYAN, (0,60,90))

img.save(OUT_FILE, format='PNG', optimize=True)
print(f"Guardado: {OUT_FILE}")
