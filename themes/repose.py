"""
Tema: repose — pantalla de reposo. Reloj tenue pulsante, fondo casi negro.
Se activa automáticamente tras 30 min de inactividad del sistema.
"""
import math, datetime
from PIL import Image, ImageDraw, ImageFont

W, H = 960, 480
_BASE = __file__.replace("/themes/repose.py", "")

def _F(name, size):
    try:
        return ImageFont.truetype(f"{_BASE}/fonts/{name}", size)
    except:
        return ImageFont.load_default()

def _Fo(s): return _F("Orbitron-Bold.ttf", s)
def _Fr(s): return _F("Rajdhani-SemiBold.ttf", s)

def _glow(d, x, y, text, font, col, intensity=2, anchor="mm"):
    for r in range(intensity * 2, 0, -1):
        alpha = int(60 / r)
        gc = tuple(min(255, c) for c in col) + (alpha,)
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        od = ImageDraw.Draw(ov)
        od.text((x, y), text, font=font, fill=gc, anchor=anchor)
        # draw is on img directly via a trick — just draw with low alpha col
    d.text((x, y), text, font=font, fill=col, anchor=anchor)

def render(frame):
    # pulso lento: ciclo completo cada ~40 s a 5fps
    pulse = 0.25 + 0.75 * (math.sin(frame * 0.032) * 0.5 + 0.5)

    img = Image.new("RGB", (W, H), (0, 0, 0))
    d   = ImageDraw.Draw(img)

    # fondo: degradado radial muy sutil azul-negro
    cx, cy = W // 2, H // 2
    for r in range(min(cx, cy), 0, -4):
        v = int(8 * (1 - r / min(cx, cy)))
        d.ellipse([cx-r, cy-r, cx+r, cy+r], fill=(0, v, v*2))

    now  = datetime.datetime.now()
    hhmm = now.strftime("%H:%M")
    ss   = now.strftime("%S")
    date = now.strftime("%A  %d %B %Y").upper()

    # brillo según pulso
    bri  = int(pulse * 210)
    dim  = int(pulse * 90)
    tick = int(pulse * 130)

    # hora grande
    _glow(d, cx, cy - 30, hhmm, _Fo(140), (bri, bri, bri), intensity=3)

    # segundos pequeños a la derecha del centro
    bb = d.textbbox((cx, cy - 30), hhmm, font=_Fo(140), anchor="mm")
    sx = bb[2] + 14
    sy = bb[1] + 20
    d.text((sx, sy), ss, font=_Fo(38), fill=(tick, tick, tick+20), anchor="lt")

    # fecha
    d.text((cx, cy + 85), date, font=_Fr(22),
           fill=(dim, dim, dim+10), anchor="mm")

    # separador
    sep_w = 220
    sv = int(pulse * 60)
    d.line([(cx - sep_w, cy + 60), (cx + sep_w, cy + 60)],
           fill=(sv, sv, sv+10), width=1)

    # indicador de reposo, muy tenue
    rv = int(pulse * 45)
    d.text((cx, H - 18), "EN REPOSO", font=_Fr(14),
           fill=(rv, rv+5, rv+10), anchor="mm")

    return img.convert("RGB")
