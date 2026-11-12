"""
Tema: TUF GAMING — ASUS TUF HUD display
Display landscape 960x480
Fuentes: Black Ops One · Chakra Petch · Audiowide · Saira Condensed
Fondo: GIF animado + partículas + scanlines + hexágonos pulsantes
"""
import math, datetime, subprocess, time, socket, json, random
import psutil
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H = 960, 480
import os
_BASE   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ASSETS = os.path.join(_BASE, "assets")
_FD     = os.path.join(_BASE, "fonts")

# ── Fuentes TUF FUTURISTA ─────────────────────────────────────────────────────
# Exo 2 XBold  — angular sci-fi, look gamer puro (números principales)
# Syncopate    — NASA/geometric (headers, badges)
# Oxanium XBold — curved futuristic (labels)
# Audiowide    — cockpit HUD (unidades)
# Chakra Petch — gaming angular (texto pequeño)
_F_EXO = os.path.join(_FD, "Exo2-ExtraBold.ttf")
_F_SYN = os.path.join(_FD, "Syncopate-Bold.ttf")
_F_OXA = os.path.join(_FD, "Oxanium-ExtraBold.ttf")
_F_AWD = os.path.join(_FD, "Audiowide-Regular.ttf")
_F_CHP = os.path.join(_FD, "ChakraPetch-Bold.ttf")
_F_CHS = os.path.join(_FD, "ChakraPetch-SemiBold.ttf")
_F_MAJ = os.path.join(_FD, "MajorMonoDisplay-Regular.ttf")

_FC = {}
def _fnt(p, s):
    k = (p, s)
    if k not in _FC:
        try:    _FC[k] = ImageFont.truetype(p, s)
        except: _FC[k] = ImageFont.load_default()
    return _FC[k]

Fex  = lambda s: _fnt(_F_EXO, s)   # Exo 2 XBold — números gaming
Fsy  = lambda s: _fnt(_F_SYN, s)   # Syncopate Bold — headers NASA
Fox  = lambda s: _fnt(_F_OXA, s)   # Oxanium XBold — labels futuristas
Faw  = lambda s: _fnt(_F_AWD, s)   # Audiowide — unidades cockpit
Fcp  = lambda s: _fnt(_F_CHP, s)   # Chakra Petch Bold
Fcps = lambda s: _fnt(_F_CHS, s)   # Chakra Petch SemiBold
Fmaj = lambda s: _fnt(_F_MAJ, s)   # Major Mono — hostname

# ── Paleta TUF ────────────────────────────────────────────────────────────────
BG        = (10,  10,  14)
TUF_Y     = (255, 158,  27)
TUF_GOLD  = (240, 204,   0)
TUF_DIM   = ( 55,  44,   6)
TUF_DARK  = ( 20,  16,   4)
LIME      = (120, 180,   0)
INK       = (232, 223, 208)
INK2      = (138, 124,  96)
INK3      = ( 50,  44,  28)
WARN      = (255,  96,   0)
CRIT      = (255,  40,   0)
TRACK     = ( 20,  16,   4)
DIVL      = ( 38,  32,  10)

# ── Sensores ──────────────────────────────────────────────────────────────────
def _cores():
    try:    return psutil.cpu_percent(percpu=True, interval=None)
    except: return [0.0]*4

def _mem():   return psutil.virtual_memory()

def _temp():
    try:
        t = psutil.sensors_temperatures()
        for k in ['k10temp','coretemp','cpu_thermal','acpitz']:
            if k in t and t[k]: return t[k][0].current
    except: pass
    return None

def _gpu():
    try:
        r = subprocess.run(['cat','/sys/class/drm/card1/device/gpu_busy_percent'],
                           capture_output=True,text=True,timeout=1)
        if r.returncode==0: return float(r.stdout.strip())
    except: pass
    return None

def _gtemp():
    try:
        t = psutil.sensors_temperatures()
        for k in ['amdgpu','nvidia','radeon']:
            if k in t and t[k]: return t[k][0].current
    except: pass
    return None

def _disk():
    for m in ['/home','/']:
        try:    return psutil.disk_usage(m), m
        except: pass
    return None, '/'

def _freq():
    try:    return psutil.cpu_freq()
    except: return None

def _vram():
    try:
        u=int(open('/sys/class/drm/card1/device/mem_info_vram_used').read().strip())
        t=int(open('/sys/class/drm/card1/device/mem_info_vram_total').read().strip())
        return u/1024**3, t/1024**3
    except: return None, None

def _gpu_clock():
    try:
        with open('/sys/class/drm/card1/device/pp_dpm_sclk') as f:
            for line in f:
                if '*' in line:
                    for p in line.split():
                        q = p.replace('Mhz','').replace('MHz','')
                        try: return float(q)
                        except: pass
    except: pass
    return None

_mc = {'res':None,'hz':None,'ts':0.0}
def _monitor_info():
    if time.time()-_mc['ts']<60: return _mc['res'],_mc['hz']
    try:
        r=subprocess.run(['hyprctl','monitors','-j'],capture_output=True,text=True,timeout=2)
        if r.returncode==0:
            ms=json.loads(r.stdout)
            if ms:
                m=ms[0]
                _mc['res']=(m.get('width',1920),m.get('height',1080))
                _mc['hz']=int(m.get('refreshRate',60))
    except: pass
    _mc['ts']=time.time()
    return _mc['res'],_mc['hz']

def _tc(t):
    if t is None: return LIME
    if t<65:      return LIME
    if t<80:      return WARN
    return CRIT

def _vc(v):
    if v<70: return INK
    if v<90: return WARN
    return CRIT

# ── Primitivas ────────────────────────────────────────────────────────────────
def _tw(d, txt, font):
    bb=d.textbbox((0,0),txt,font=font)
    return bb[2]-bb[0], bb[3]-bb[1]

def _ctr(d, cx, y, txt, font, col):
    bb=d.textbbox((0,0),txt,font=font)
    d.text((cx-(bb[2]-bb[0])//2, y), txt, font=font, fill=col)

def _bar(d, x, y, w, h, pct, col=TUF_Y, bg=TRACK):
    d.rectangle([x,y,x+w,y+h], fill=bg)
    fw=max(0,int(w*pct/100))
    if fw>0: d.rectangle([x,y,x+fw,y+h], fill=col)

def _dotline(d, x, y, w, col, dw=6, gap=4):
    px=x
    while px<x+w:
        d.line([(px,y),(min(px+dw,x+w),y)], fill=col, width=2)
        px+=dw+gap

# ── Número centrado: [valor] [unidad] ─────────────────────────────────────────
def _num_ctr(d, cx, y, val, unit, vfont, ufont, vcol=INK):
    vw, vh = _tw(d, val, vfont)
    uw, uh = _tw(d, unit, ufont)
    total  = vw + 5 + uw
    sx = cx - total//2
    # glow
    for ox,oy in [(3,0),(-3,0),(0,3),(0,-3)]:
        d.text((sx+ox, y+oy), val, font=vfont,
               fill=tuple(min(255,c//8) for c in TUF_Y))
    d.text((sx, y), val, font=vfont, fill=vcol)
    d.text((sx+vw+5, y+vh-uh-2), unit, font=ufont, fill=INK2)
    return vh

# ── Badge TUF centrado ────────────────────────────────────────────────────────
def _badge_ctr(d, cx, y1, y2, text):
    bw = 180
    x1, x2 = cx-bw//2, cx+bw//2
    h = y2-y1
    d.rectangle([x1,y1,x2,y2], fill=TUF_Y)
    slash = int(h*0.85)
    d.polygon([(x1,y1),(x1+slash,y1),(x1,y2)], fill=TUF_GOLD)
    d.polygon([(x2,y1),(x2-slash,y1),(x2,y2)], fill=TUF_GOLD)
    _ctr(d, cx, y1+(h-20)//2, text, Fsy(18), (8,6,2))

# ── Core bars centradas ───────────────────────────────────────────────────────
def _core_bars_ctr(d, cx, y, w, cores):
    n=len(cores)
    if not n: return
    bw=max(4,(w-(n-1)*3)//n)
    bh=20
    sx=cx-((bw+3)*n-3)//2
    for i,pct in enumerate(cores):
        bx=sx+i*(bw+3)
        d.rectangle([bx,y,bx+bw,y+bh], fill=(20,16,5))
        fh=max(0,int(bh*pct/100))
        col=LIME if pct<70 else (WARN if pct<90 else CRIT)
        if fh>0:
            d.rectangle([bx,y+bh-fh,bx+bw,y+bh], fill=col)

# ═══════════════════════════════════════════════════════════════════════
# ANIMACIONES DE FONDO
# ═══════════════════════════════════════════════════════════════════════

# ── Pre-compute grid hexagonal ────────────────────────────────────────
_HEX_CENTERS = []
_HEX_PTS     = []

def _build_hex_grid():
    global _HEX_CENTERS, _HEX_PTS
    if _HEX_CENTERS: return
    R = 28
    dx_h = int(R*1.732)
    dy_h = int(R*1.5)
    for row in range(-1, H//dy_h+3):
        for col in range(-1, W//dx_h+2):
            cx = col*dx_h + (dx_h//2 if row%2 else 0)
            cy = row*dy_h
            pts = []
            for i in range(6):
                a = math.radians(60*i-30)
                pts.append((cx+R*math.cos(a), cy+R*math.sin(a)))
            _HEX_CENTERS.append((cx,cy))
            _HEX_PTS.append(pts)

def _draw_hex_bg(d, frame):
    _build_hex_grid()
    base_fill = (14,13,8)
    outline   = (22,20,12)
    t = frame * 0.04
    for (cx,cy), pts in zip(_HEX_CENTERS, _HEX_PTS):
        # pulso basado en posición + tiempo
        wave = 0.5 + 0.5*math.sin(t + cx*0.02 + cy*0.015)
        if wave > 0.85:
            fill = (int(14+wave*30), int(13+wave*20), int(8+wave*5))
        else:
            fill = base_fill
        d.polygon(pts, fill=fill, outline=outline)

# ── Partículas / lluvia de puntos TUF ────────────────────────────────
_N_PARTICLES = 60
_PART_X = None
_PART_Y = None
_PART_SPD = None
_PART_SZ  = None
_PART_BR  = None

def _init_particles():
    global _PART_X, _PART_Y, _PART_SPD, _PART_SZ, _PART_BR
    if _PART_X is not None: return
    rng = np.random.default_rng(42)
    _PART_X   = rng.integers(0, W, _N_PARTICLES).astype(float)
    _PART_Y   = rng.integers(0, H, _N_PARTICLES).astype(float)
    _PART_SPD = rng.uniform(0.4, 2.2, _N_PARTICLES)
    _PART_SZ  = rng.integers(1, 4, _N_PARTICLES)
    _PART_BR  = rng.uniform(0.3, 1.0, _N_PARTICLES)

def _update_particles():
    global _PART_Y
    _PART_Y += _PART_SPD
    wrap = _PART_Y >= H
    _PART_Y[wrap] = 0.0

def _draw_particles(d):
    _init_particles()
    _update_particles()
    for i in range(_N_PARTICLES):
        x,y = int(_PART_X[i]), int(_PART_Y[i])
        sz  = int(_PART_SZ[i])
        br  = _PART_BR[i]
        col = (int(TUF_Y[0]*br), int(TUF_Y[1]*br), int(TUF_Y[2]*br*0.3))
        if 0<=x<W and 0<=y<H:
            d.ellipse([x,y,x+sz,y+sz], fill=col)

# ── Scanlines animadas ────────────────────────────────────────────────
def _draw_scanlines(d, frame):
    offset = (frame * 3) % 8
    for y in range(offset, H, 8):
        d.line([(0,y),(W,y)], fill=(0,0,0,0))   # line placeholder — se hace via overlay

def _scanline_overlay(img, frame):
    ov = Image.new('RGBA', (W,H), (0,0,0,0))
    od = ImageDraw.Draw(ov)
    offset = (frame * 2) % 6
    for y in range(offset, H, 6):
        od.line([(0,y),(W,y)], fill=(0,0,0,35))
    base = img.convert('RGBA')
    return Image.alpha_composite(base, ov).convert('RGB')

# ── GIF strip animado (starwars) ──────────────────────────────────────
_GIF_FRAMES = None
_GIF_N      = 0

def _load_gif():
    global _GIF_FRAMES, _GIF_N
    if _GIF_FRAMES is not None: return
    path = os.path.join(_ASSETS, 'starwars_battle.gif')
    try:
        g = Image.open(path)
        _GIF_N = g.n_frames
        frames = []
        STRIP_H = 50
        for i in range(_GIF_N):
            g.seek(i)
            fr = g.convert('RGB')
            # escalar para llenar 960 de ancho, 50 de alto
            fr = fr.resize((W, STRIP_H), Image.BILINEAR)
            # tint TUF amarillo
            arr = np.array(fr).astype(float)
            arr[:,:,0] = np.clip(arr[:,:,0]*0.4 + TUF_Y[0]*0.35, 0, 255)
            arr[:,:,1] = np.clip(arr[:,:,1]*0.4 + TUF_Y[1]*0.25, 0, 255)
            arr[:,:,2] = np.clip(arr[:,:,2]*0.2, 0, 255)
            frames.append(Image.fromarray(arr.astype(np.uint8)))
        _GIF_FRAMES = frames
    except:
        _GIF_FRAMES = []
        _GIF_N = 1

# ── Radar sweep en esquina ────────────────────────────────────────────
def _draw_radar(d, frame):
    cx, cy = 50, H-50
    r = 44
    d.ellipse([cx-r,cy-r,cx+r,cy+r], outline=(50,38,5), width=1)
    d.ellipse([cx-r//2,cy-r//2,cx+r//2,cy+r//2], outline=(35,26,4), width=1)
    # sweep
    angle = math.radians((frame*4) % 360 - 90)
    ex = cx + r*math.cos(angle)
    ey = cy + r*math.sin(angle)
    d.line([(cx,cy),(ex,ey)], fill=TUF_Y, width=2)
    # trail
    for i in range(1,6):
        a2 = math.radians(((frame*4)-i*12)%360-90)
        ex2=cx+r*math.cos(a2); ey2=cy+r*math.sin(a2)
        alpha=int(TUF_Y[0]*(1-i/6))
        d.line([(cx,cy),(ex2,ey2)], fill=(alpha,int(alpha*0.62),0), width=1)
    # blip
    d.ellipse([cx-2,cy-2,cx+2,cy+2], fill=TUF_GOLD)

# ── Corner bracket decoration ─────────────────────────────────────────
def _draw_corners(d, frame):
    pulse = 0.7 + 0.3*math.sin(frame*0.1)
    col = tuple(int(c*pulse) for c in TUF_Y)
    sz = 22
    for (x,y,sx,sy) in [(0,0,1,1),(W,0,-1,1),(0,H,1,-1),(W,H,-1,-1)]:
        d.line([(x,y),(x+sx*sz,y)], fill=col, width=3)
        d.line([(x,y),(x,y+sy*sz)], fill=col, width=3)

# ═══════════════════════════════════════════════════════════════════════
# GAUGE RAM
# ═══════════════════════════════════════════════════════════════════════
def _tuf_gauge(d, cx, cy, r, pct, frame):
    d.ellipse([cx-(r+36),cy-(r+36),cx+(r+36),cy+(r+36)], fill=(8,7,4))
    # glow
    for gr in range(r+34,r+8,-5):
        i=max(0,18-(gr-r))
        d.ellipse([cx-gr,cy-gr,cx+gr,cy+gr], outline=(i*3,int(i*1.7),0), width=1)
    # ticks
    for i in range(60):
        a=math.radians(-90+i*6)
        big=(i%5==0)
        r1=r+(1 if big else 3); r2=r+(14 if big else 8)
        d.line([(cx+r1*math.cos(a),cy+r1*math.sin(a)),
                (cx+r2*math.cos(a),cy+r2*math.sin(a))],
               fill=(INK3 if big else (30,24,8)), width=(2 if big else 1))
    # segmentos
    N=36; r_arc=r-22; filled=int(N*pct/100)
    for i in range(N):
        sa=-90+i*360/N; ea=sa+360/N-2.5
        if i<filled:
            ratio=i/max(1,N)
            col=(int(TUF_Y[0]+(TUF_GOLD[0]-TUF_Y[0])*ratio),
                 int(TUF_Y[1]+(TUF_GOLD[1]-TUF_Y[1])*ratio), 0)
            if i==filled-1:
                d.arc([cx-r_arc-5,cy-r_arc-5,cx+r_arc+5,cy+r_arc+5],
                      start=sa,end=ea,fill=TUF_Y,width=22)
        else:
            col=(26,20,6)
        d.arc([cx-r_arc,cy-r_arc,cx+r_arc,cy+r_arc],
              start=sa,end=ea,fill=col,width=14)
    # arco exterior
    if pct>1:
        ae=-90+360*pct/100
        d.arc([cx-(r+20),cy-(r+20),cx+(r+20),cy+(r+20)],
              start=-90,end=ae,fill=TUF_Y,width=4)
        ta=math.radians(ae)
        tx=cx+(r+20)*math.cos(ta); ty=cy+(r+20)*math.sin(ta)
        d.ellipse([tx-7,ty-7,tx+7,ty+7], fill=TUF_GOLD)
    # indicador superior
    d.polygon([(cx,cy-r-24),(cx-8,cy-r-9),(cx+8,cy-r-9)], fill=TUF_Y)
    # aspas interiores
    NB=24; r_blade=r_arc-18; fb=int(NB*pct/100)
    for i in range(NB):
        sa=-90+i*360/NB; ea=sa+360/NB-3
        col=(int(88+i/NB*44),int(62+i/NB*32),8) if i<fb else (18,14,4)
        d.arc([cx-r_blade,cy-r_blade,cx+r_blade,cy+r_blade],
              start=sa,end=ea,fill=col,width=15)
    r_center=r_blade-18
    d.ellipse([cx-r_center,cy-r_center,cx+r_center,cy+r_center], fill=(10,8,3))
    # pulso animado
    pulse=0.5+0.5*math.sin(frame*0.09)
    pr=int(r_center-5-pulse*5); pc=int(50*pulse)
    d.ellipse([cx-pr,cy-pr,cx+pr,cy+pr], outline=(pc,int(pc*0.65),0), width=1)
    # número central ENORME (Black Ops One)
    pct_str=f"{pct:.0f}"
    fs=118 if len(pct_str)<=2 else 96
    pfont=Fex(fs)
    pw,ph=_tw(d,pct_str,pfont)
    for ox,oy in [(5,0),(-5,0),(0,5),(0,-5)]:
        d.text((cx-pw//2+ox,cy-ph//2-2+oy),pct_str,font=pfont,fill=(70,52,0))
    d.text((cx-pw//2,cy-ph//2-2),pct_str,font=pfont,fill=INK)
    d.text((cx+pw//2+4,cy-ph//2+10),"%",font=Fcp(28),fill=INK2)
    _ctr(d,cx,cy+ph//2+6, "RAM USAGE",Faw(14),INK2)
    _ctr(d,cx,cy-ph//2-28,"MEMORY",   Fcps(13),INK3)
    # mini barra
    rbw=r_center*2-14; bx=cx-rbw//2; by=cy+ph//2+26
    d.rectangle([bx,by,bx+rbw,by+5],fill=(18,14,4))
    fw=int(rbw*pct/100)
    if fw>0: d.rectangle([bx,by,bx+fw,by+5],fill=TUF_Y)

# ═══════════════════════════════════════════════════════════════════════
# RENDER PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════
def render(frame):
    _load_gif()
    img = Image.new('RGB', (W,H), BG)
    d   = ImageDraw.Draw(img)

    # ── 1. Fondo hexagonal animado ────────────────────────────────────
    _draw_hex_bg(d, frame)

    # ── 2. GIF strip en footer (últimos 50px) ─────────────────────────
    if _GIF_FRAMES:
        gf_idx = frame % _GIF_N
        gif_strip = _GIF_FRAMES[gf_idx]
        img.paste(gif_strip, (0, H-50))

    # ── 3. Partículas animadas ────────────────────────────────────────
    _draw_particles(d)

    # Refresh draw después de partículas
    d = ImageDraw.Draw(img)

    # ── 4. Scanlines (overlay al final) ──────────────────────────────
    # (se aplica al final)

    # ── 5. Sensores ───────────────────────────────────────────────────
    cores = _cores()
    cpu   = sum(cores)/len(cores) if cores else 0.0
    mem   = _mem()
    ct    = _temp()
    gpu   = _gpu()
    gt    = _gtemp()
    disk, _ = _disk()
    freq  = _freq()
    vu, vt  = _vram()
    gpu_clk = _gpu_clock()
    res, hz = _monitor_info()
    now   = datetime.datetime.now()

    # ── Layout ────────────────────────────────────────────────────────
    LCX = 155    # centro columna CPU
    RCX = 805    # centro columna GPU
    GCX = 480    # centro gauge
    GCY = 255    # centro gauge Y
    GR  = 147    # radio gauge
    LW  = 280    # ancho panel (para barras)
    LX  = 15     # borde izq panel
    RX  = 665    # borde izq panel GPU

    FOOTER_Y = H - 50   # inicio strip GIF

    # ── 6. Líneas TUF ────────────────────────────────────────────────
    d.rectangle([0,0,W,4], fill=TUF_Y)                       # borde superior
    d.line([(0,52),(W,52)], fill=DIVL, width=1)               # separador header
    d.line([(LX+LW//2+10, 55),(LX+LW//2+10, FOOTER_Y-4)],    # divisor L
           fill=DIVL, width=1)
    d.line([(RX-10, 55),(RX-10, FOOTER_Y-4)],                 # divisor R
           fill=DIVL, width=1)
    d.line([(0, FOOTER_Y-4),(W, FOOTER_Y-4)], fill=DIVL, width=1)  # sobre footer

    # ── 7. Header: brand izq, fecha der (sin reloj) ───────────────────
    d.text((LX, 8),  "TUF GAMING",            font=Faw(20),  fill=TUF_Y)
    d.text((LX, 30), socket.gethostname().upper(), font=Fmaj(12), fill=INK2)
    # Fecha derecha en Chakra Petch
    date_str = now.strftime("%d %b %Y").upper()
    bb = d.textbbox((0,0), date_str, font=Fcp(20))
    d.text((W-15-(bb[2]-bb[0]), 8),  date_str,              font=Fcp(20),  fill=INK2)
    day_str  = now.strftime("%A").upper()
    bb2 = d.textbbox((0,0), day_str, font=Fcps(14))
    d.text((W-15-(bb2[2]-bb2[0]), 30), day_str,             font=Fcps(14), fill=INK3)

    # Radar en el centro del header (donde estaba el reloj)
    _draw_radar(d, frame)

    # Corner brackets
    _draw_corners(d, frame)

    # ══════════════════════════════════════════════════════════════════
    # PANEL CPU — todo centrado en LCX=155
    # ══════════════════════════════════════════════════════════════════
    Y = 56
    _badge_ctr(d, LCX, Y, Y+30, "CPU")
    d.line([(LX, Y+31),(LX+LW//2+6, Y+31)], fill=TUF_Y, width=2)
    Y += 38

    # Temperatura CPU
    tc_str = f"{ct:.1f}" if ct else "--.-"
    tc_col = _tc(ct)
    vh = _num_ctr(d, LCX, Y, tc_str, "°C", Fex(84), Fcp(28), vcol=tc_col)
    _bar(d, LX, Y+vh+3, LW//2-10, 5, min(100,ct or 0), col=tc_col)
    _dotline(d, LX, Y+vh+10, LW//2-10, TUF_DIM)
    Y += vh+18

    # Frecuencia CPU — Saira para variedad
    freq_str = f"{freq.current:.0f}" if freq else "---"
    vw2, vh2 = _tw(d, freq_str, Fox(70))
    uw2, uh2 = _tw(d, "MHz", Fcp(26))
    sx2 = LCX - (vw2+5+uw2)//2
    d.text((sx2, Y), freq_str, font=Fox(70), fill=INK)
    d.text((sx2+vw2+5, Y+vh2-uh2-2), "MHz", font=Fcp(26), fill=INK2)
    _dotline(d, LX, Y+vh2+10, LW//2-10, TUF_DIM)
    Y += vh2+18

    # Uso CPU %
    cpu_str = f"{cpu:.1f}"
    cc = _vc(cpu)
    vh3 = _num_ctr(d, LCX, Y, cpu_str, "%", Fex(74), Fcp(28), vcol=cc)
    _bar(d, LX, Y+vh3+3, LW//2-10, 7, cpu, col=TUF_Y)
    _dotline(d, LX, Y+vh3+12, LW//2-10, TUF_DIM)
    Y += vh3+20

    d.line([(LX, Y),(LX+LW//2+6, Y)], fill=DIVL, width=1)
    Y += 8

    # Storage
    _ctr(d, LCX, Y, "STORAGE", Fox(13), INK2)
    Y += 18
    if disk:
        ds = f"{disk.percent:.0f}"
        vh_d = _num_ctr(d, LCX, Y, ds, "%", Fex(50), Fcp(22))
        _bar(d, LX, Y+vh_d+3, LW//2-10, 5, disk.percent)
        Y += vh_d+12
    else:
        _ctr(d, LCX, Y, "N/A", Fex(44), INK3)
        Y += 48

    # Cores
    if cores and Y+28 < FOOTER_Y-12:
        d.line([(LX, Y),(LX+LW//2+6, Y)], fill=DIVL, width=1)
        Y += 6
        _ctr(d, LCX, Y, "CORES", Fox(13), INK2)
        Y += 18
        _core_bars_ctr(d, LCX, Y, LW//2-10, cores[:min(len(cores),12)])

    # ══════════════════════════════════════════════════════════════════
    # PANEL GPU — todo centrado en RCX=805
    # ══════════════════════════════════════════════════════════════════
    Y = 56
    _badge_ctr(d, RCX, Y, Y+30, "GPU")
    d.line([(RX-6, Y+31),(RX-6+LW//2+6, Y+31)], fill=TUF_Y, width=2)
    Y += 38

    # Temperatura GPU
    gt_str = f"{gt:.1f}" if gt else "--.-"
    gtc = _tc(gt)
    gvh = _num_ctr(d, RCX, Y, gt_str, "°C", Fex(84), Fcp(28), vcol=gtc)
    _bar(d, RX-6, Y+gvh+3, LW//2-10, 5, min(100,gt or 0), col=gtc)
    _dotline(d, RX-6, Y+gvh+10, LW//2-10, TUF_DIM)
    Y += gvh+18

    # GPU Clock — Saira
    clk_str = f"{gpu_clk:.0f}" if gpu_clk else (f"{vu*1000:.0f}" if vu else "---")
    cw, ch = _tw(d, clk_str, Fox(70))
    uw, uh = _tw(d, "MHz", Fcp(26))
    sx3 = RCX - (cw+5+uw)//2
    d.text((sx3, Y), clk_str, font=Fox(70), fill=INK)
    d.text((sx3+cw+5, Y+ch-uh-2), "MHz", font=Fcp(26), fill=INK2)
    _dotline(d, RX-6, Y+ch+10, LW//2-10, TUF_DIM)
    Y += ch+18

    # GPU Usage %
    gpu_pct = gpu if gpu is not None else 0.0
    gpu_str = f"{gpu_pct:.1f}"
    gc = _vc(gpu_pct)
    gvh3 = _num_ctr(d, RCX, Y, gpu_str, "%", Fex(74), Fcp(28), vcol=gc)
    _bar(d, RX-6, Y+gvh3+3, LW//2-10, 7, gpu_pct, col=TUF_Y)
    _dotline(d, RX-6, Y+gvh3+12, LW//2-10, TUF_DIM)
    Y += gvh3+20

    d.line([(RX-6, Y),(RX-6+LW//2+6, Y)], fill=DIVL, width=1)
    Y += 8

    # Resolution
    _ctr(d, RCX, Y, "RESOLUTION", Fox(13), INK2)
    Y += 18
    res_str = f"{res[0]}x{res[1]}" if res else "1920x1080"
    _ctr(d, RCX, Y, res_str, Fox(32), INK)
    _, rsh = _tw(d, res_str, Fox(32))
    _bar(d, RX-6, Y+rsh+3, LW//2-10, 4, 100, col=TUF_DIM)
    Y += rsh+12

    # VRAM
    d.line([(RX-6, Y),(RX-6+LW//2+6, Y)], fill=DIVL, width=1)
    Y += 8
    _ctr(d, RCX, Y, "VRAM", Fox(13), INK2)
    Y += 18
    if vu is not None and vt is not None:
        vram_str = f"{vu:.1f} / {vt:.0f} GB"
        _ctr(d, RCX, Y, vram_str, Fox(30), INK)
        _, vrh = _tw(d, vram_str, Fox(30))
        _bar(d, RX-6, Y+vrh+3, LW//2-10, 5, vu/vt*100 if vt else 0)
        Y += vrh+12
    else:
        _ctr(d, RCX, Y, "N/A", Fox(30), INK3)
        Y += 36

    # Refresh rate
    if Y+46 < FOOTER_Y-12:
        d.line([(RX-6, Y),(RX-6+LW//2+6, Y)], fill=DIVL, width=1)
        Y += 8
        _ctr(d, RCX, Y, "REFRESH", Fox(13), INK2)
        Y += 18
        fps_str = f"{hz or 60} Hz"
        _ctr(d, RCX, Y, fps_str, Fex(42), INK)

    # ══════════════════════════════════════════════════════════════════
    # GAUGE RAM — centro
    # ══════════════════════════════════════════════════════════════════
    _tuf_gauge(d, GCX, GCY, GR, mem.percent, frame)
    ram_used = (mem.total-mem.available)/1024**3
    ram_tot  = mem.total/1024**3
    _ctr(d, GCX, GCY+GR+18, f"{ram_used:.1f} / {ram_tot:.0f} GB", Fcp(15), INK3)

    # líneas laterales al gauge
    gl  = GCX-GR-26; gr_ = GCX+GR+26
    LLX = LX+LW//2+14; RLX = RX-14
    d.line([(LLX, GCY),(gl, GCY)], fill=DIVL, width=1)
    d.line([(gr_, GCY),(RLX, GCY)], fill=DIVL, width=1)
    d.ellipse([gl-4,GCY-4,gl+4,GCY+4], fill=TUF_DARK, outline=INK3)
    d.ellipse([gr_-4,GCY-4,gr_+4,GCY+4], fill=TUF_DARK, outline=INK3)

    # ── 8. Scanlines overlay (al final) ──────────────────────────────
    img = _scanline_overlay(img, frame)

    return img
