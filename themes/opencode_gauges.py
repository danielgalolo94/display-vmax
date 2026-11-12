"""
Tema: OPENCODE GAUGES — 3 gauges full-screen
Display landscape 960x480
Cada gauge ocupa ~1/3 del ancho, valores enormes, glow pulsante
"""
import math, datetime, subprocess, os
import psutil
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 960, 480
_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_FD   = os.path.join(_BASE, "fonts")

_F_TKO = os.path.join(_FD, "Teko-Medium.ttf")
_F_ORB = os.path.join(_FD, "Orbitron-Bold.ttf")
_F_RAJ = os.path.join(_FD, "Rajdhani-SemiBold.ttf")
_F_DAT = os.path.join(_FD, "NotoSansMono-Bold.ttf")
_F_MON = os.path.join(_FD, "ShareTechMono.ttf")
_F_NRD = os.path.join(_FD, "FiraCodeNerdFont-Medium.ttf")

_FC = {}
def _fnt(p, s):
    k = (p, s)
    if k not in _FC:
        try:    _FC[k] = ImageFont.truetype(p, s)
        except: _FC[k] = ImageFont.load_default()
    return _FC[k]

Ft = lambda s: _fnt(_F_TKO, s)
Fo = lambda s: _fnt(_F_ORB, s)
Fr = lambda s: _fnt(_F_RAJ, s)
Fd = lambda s: _fnt(_F_DAT, s)
Fm = lambda s: _fnt(_F_MON, s)
Fn = lambda s: _fnt(_F_NRD, s)

BG     = (8,   10,  22)
PANEL  = (12,  16,  32)
DOT    = (18,  22,  40)
TEXT   = (220, 230, 250)
TEXT2  = (130, 140, 170)
TEXT3  = (60,   70, 100)
TRACK  = (25,  30,  55)

CYAN   = (0,   220, 255)
PURPLE = (170, 90,  255)
GREEN  = (50,  210, 120)
ORANGE = (255, 160, 30)
RED    = (245, 55,  55)

def _cores():
    try: return psutil.cpu_percent(percpu=True, interval=None)
    except: return [0.0]*4
def _mem(): return psutil.virtual_memory()
def _temp():
    try:
        t = psutil.sensors_temperatures()
        for k in ['k10temp','coretemp','cpu_thermal','acpitz']:
            if k in t and t[k]: return t[k][0].current
    except: return None
def _gpu():
    try:
        r = subprocess.run(['cat','/sys/class/drm/card0/device/gpu_busy_percent'],
                           capture_output=True, text=True, timeout=1)
        if r.returncode == 0: return float(r.stdout.strip())
    except: return None
def _gtemp():
    try:
        t = psutil.sensors_temperatures()
        for k in ['amdgpu','nvidia','radeon']:
            if k in t and t[k]: return t[k][0].current
    except: return None
def _disk():
    for m in ['/home','/']:
        try: return psutil.disk_usage(m), m
        except: pass
    return None, '/'
def _freq():
    try: return psutil.cpu_freq()
    except: return None

def _vc(v):
    if v < 70: return GREEN
    if v < 90: return ORANGE
    return RED
def _tc(t):
    if t is None: return TEXT2
    if t < 65: return GREEN
    if t < 80: return ORANGE
    return RED

def _ctr(d, cx, y, txt, font, col):
    bb = d.textbbox((0,0), txt, font=font)
    d.text((cx-(bb[2]-bb[0])//2, y), txt, font=font, fill=col)

def _gauge(d, cx, cy, r, pct, val_txt, label, color, temp=None, frame=0):
    S, SPAN = -210, 240
    pct = max(0, min(100, pct))
    AW = 22
    IR = r - 8
    pulse = 0.7 + 0.3 * math.sin(frame * 0.12)

    glow = Image.new('RGBA', (W, H), (0,0,0,0))
    gd = ImageDraw.Draw(glow)

    gd.ellipse([cx-r-4,cy-r-4,cx+r+4,cy+r+4], fill=(12, 16, 34))
    d.ellipse([cx-r,cy-r,cx+r,cy+r], fill=BG)

    for ox, oy, al in [(0,0,35),(0,0,22),(0,0,12)]:
        rr = r + 12 - al//4
        gd.ellipse([cx-rr+ox,cy-rr+oy,cx+rr+ox,cy+rr+oy],
                    fill=tuple(min(255,c*al//35) for c in color))

    glow = glow.filter(ImageFilter.GaussianBlur(radius=8))
    base = d._image.convert('RGBA')
    base.alpha_composite(glow)
    ImageDraw.Draw(base)

    N = 20
    for i in range(N+1):
        a = math.radians(S + SPAN*i/N)
        big = (i % (N//4) == 0)
        r1 = r - (14 if big else 6)
        r2 = r + 2
        x1,y1 = cx+r1*math.cos(a), cy+r1*math.sin(a)
        x2,y2 = cx+r2*math.cos(a), cy+r2*math.sin(a)
        d.line([(x1,y1),(x2,y2)], fill=TEXT if big else TEXT3, width=(2 if big else 1))
        if big and 0 < i < N:
            pv = int(100*i/N)
            nf = Fm(12)
            nb = d.textbbox((0,0), str(pv), font=nf)
            nx = cx+(r+16)*math.cos(a)-(nb[2]-nb[0])//2
            ny = cy+(r+16)*math.sin(a)-(nb[3]-nb[1])//2
            d.text((nx,ny), str(pv), font=nf, fill=TEXT3)

    d.arc([cx-IR,cy-IR,cx+IR,cy+IR], start=S, end=S+SPAN, fill=TRACK, width=AW)
    arc_pct = int(SPAN * max(pct, 2) / 100)
    halo = tuple(c//2 for c in color)
    d.arc([cx-IR-5,cy-IR-5,cx+IR+5,cy+IR+5], start=S, end=S+arc_pct,
           fill=halo, width=AW+12)
    d.arc([cx-IR-2,cy-IR-2,cx+IR+2,cy+IR+2], start=S, end=S+arc_pct,
           fill=color, width=AW+4)
    d.arc([cx-IR,cy-IR,cx+IR,cy+IR], start=S, end=S+arc_pct,
           fill=color, width=AW)

    d.arc([cx-IR+AW//2-2,cy-IR+AW//2-2,cx+IR-AW//2+2,cy+IR-AW//2+2],
           start=S, end=S+arc_pct,
           fill=tuple(min(255,c+60) for c in color), width=2)

    tip_a = math.radians(S + arc_pct)
    tx,ty = cx+IR*math.cos(tip_a), cy+IR*math.sin(tip_a)
    d.ellipse([tx-15,ty-15,tx+15,ty+15], fill=halo)
    d.ellipse([tx-9,ty-9,tx+9,ty+9], fill=color)
    d.ellipse([tx-3,ty-3,tx+3,ty+3], fill=TEXT)

    NR = IR - AW - 12
    d.ellipse([cx-NR,cy-NR,cx+NR,cy+NR], fill=BG)

    vs = str(val_txt)
    fsz = 100 if len(vs) < 3 else 80
    fsz = min(fsz, int(NR * 1.6))
    vf = Ft(fsz)
    bb = d.textbbox((0,0), vs, font=vf)
    tw, th = bb[2]-bb[0], bb[3]-bb[1]
    vx = cx - tw//2 - bb[0]
    vy = cy - th//2 - bb[1] - 4
    dim = tuple(c//5 for c in color)
    for off in [(2,2),(-2,2),(2,-2),(-2,-2)]:
        d.text((vx+off[0], vy+off[1]), vs, font=vf, fill=dim)
    d.text((vx, vy), vs, font=vf, fill=TEXT)

    d.text((cx+tw//2+4, vy+fsz//2+2), "%" if label != "MEM" else "G",
            font=Fr(28), fill=color)

    _ctr(d, cx, cy+NR-30, label, Fr(28), color)

    if temp is not None:
        tc = _tc(temp)
        _ctr(d, cx, cy+NR-4, f"{temp:.1f}C", Fd(38), tc)

    by = cy + IR + 18
    bw = IR * 2 - 20
    _hbar(d, cx-bw//2, by, bw, 14, pct, color)

def _hbar(d, x, y, w, h, pct, col):
    d.rectangle([x-1,y-1,x+w+1,y+h+1], fill=(8, 10, 24), outline=TEXT3, width=1)
    fw = int(pct/100*w)
    if fw < 1: return
    for i in range(fw):
        t = 0.5 + 0.5*(i/fw)
        d.line([(x+i,y),(x+i,y+h)],
            fill=(min(255,int(col[0]*t)), min(255,int(col[1]*t)), min(255,int(col[2]*t))))
    d.line([(x+fw-1,y),(x+fw-1,y+h)], fill=TEXT, width=2)

def render(frame):
    cores = _cores()
    cpu   = sum(cores)/len(cores) if cores else 0.0
    mem   = _mem()
    ct    = _temp()
    gpu   = _gpu()
    gt    = _gtemp()
    disk, dm = _disk()
    freq  = _freq()
    now   = datetime.datetime.now()
    la    = os.getloadavg()
    ram   = (mem.total-mem.available)/1024**3
    tot   = mem.total/1024**3
    uptime = now - datetime.datetime.fromtimestamp(psutil.boot_time())
    uh, um = divmod(int(uptime.total_seconds())//60, 60)

    img = Image.new('RGB', (W, H), BG)

    for x in range(0, W, 24):
        for y in range(0, H, 24):
            img.putpixel((x, y), DOT)

    d = ImageDraw.Draw(img)

    TB = 44
    d.rectangle([0,0,W,TB], fill=PANEL)
    d.rectangle([0,TB-1,W,TB], fill=CYAN)

    blink = CYAN if (frame % 12) < 8 else (0, 40, 70)
    d.ellipse([10, TB//2-8, 24, TB//2+6], fill=blink, outline=CYAN, width=1)
    d.text((30, TB//2-14), "OPENCODE", font=Fo(24), fill=TEXT)
    d.text((30, TB//2+8),  "gauges",   font=Fm(14), fill=TEXT2)

    _ctr(d, W//2, TB//2-14, now.strftime("%H:%M:%S"), Fo(80), CYAN)
    _ctr(d, W//2, TB//2+14, now.strftime("%a %d/%m/%Y"), Fm(18), TEXT3)

    d.text((W-150, TB//2-14), "arch-01", font=Fr(22), fill=TEXT)
    d.text((W-150, TB//2+8),  "RYZEN 9", font=Fm(14), fill=TEXT2)

    UY = TB + 6
    GH = H - UY - 24
    GW = W // 3
    centers = [
        (GW//2, UY + GH//2),
        (GW + GW//2, UY + GH//2),
        (GW*2 + GW//2, UY + GH//2),
    ]
    GR = min(GW, GH) // 2 - 10

    gpu_pct = gpu if gpu is not None else 0
    _gauge(d, centers[0][0], centers[0][1], GR, cpu,
           f"{cpu:.0f}", "CPU", CYAN, ct, frame)

    _gauge(d, centers[1][0], centers[1][1], GR, gpu_pct,
           f"{gpu_pct:.0f}", "GPU", PURPLE, gt, frame)

    mem_pct = mem.percent
    _gauge(d, centers[2][0], centers[2][1], GR, mem_pct,
           f"{ram:.1f}", "MEM", GREEN, None, frame)

    BB = H - 22
    d.rectangle([0,BB,W,H], fill=PANEL)
    d.line([(0,BB),(W,BB)], fill=TEXT3, width=1)
    d.line([(0,BB+1),(W,BB+1)], fill=(10, 12, 28), width=1)

    blink2 = CYAN if (frame % 14) < 9 else TEXT3
    d.ellipse([8, BB+5, 16, BB+15], fill=blink2)

    items = [
        f"CPU {ct:.1f}C" if ct else "",
        f"load {la[0]:.2f}",
        f"{uh}h {um:02d}m",
        f"{len(psutil.pids())} proc",
        f"MEM {mem.percent:.0f}%",
    ]
    sx = 24
    for item in items:
        if item:
            d.text((sx, BB+3), item, font=Fm(18), fill=TEXT2)
            sx += d.textbbox((0,0), item, font=Fm(18))[2] - d.textbbox((0,0), item, font=Fm(18))[0] + 28

    if freq:
        d.text((W-200, BB+2), f"{freq.current/1000:.2f} GHz", font=Fd(20), fill=TEXT3)

    d.text((W-90, BB+2), "OK", font=Fm(18), fill=GREEN)

    for yy in range(0, H, 6):
        a = 4 + int(3 * math.sin((yy + frame * 4) * 0.08))
        d.line([(0, yy+a), (W, yy+a)], fill=(0, 0, 0, 6), width=1)

    return img
