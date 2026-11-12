"""
Tema: HUD CYAN — Tactical System Monitor
Display landscape 960x480
"""
import math, random, datetime, subprocess
import psutil
from PIL import Image, ImageDraw, ImageFont

W, H = 960, 480
import os
_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_FD   = os.path.join(_BASE, "fonts")

_F_ORB = os.path.join(_FD, "Orbitron-Black.ttf")
_F_RAJ = os.path.join(_FD, "Rajdhani-SemiBold.ttf")
_F_DAT = os.path.join(_FD, "NotoSansMono-Bold.ttf")
_F_MON = os.path.join(_FD, "ShareTechMono.ttf")

_FC = {}
def _fnt(p, s):
    k = (p, s)
    if k not in _FC:
        try:    _FC[k] = ImageFont.truetype(p, s)
        except: _FC[k] = ImageFont.load_default()
    return _FC[k]

Fo = lambda s: _fnt(_F_ORB, s)   # Orbitron Black — impacto
Fr = lambda s: _fnt(_F_RAJ, s)   # Rajdhani — labels
Fd = lambda s: _fnt(_F_DAT, s)   # NotoSansMono — datos
Fm = lambda s: _fnt(_F_MON, s)   # ShareTechMono — secundario

# ── Paleta ────────────────────────────────────────────────────────────────────
BG   = (2,   8,  20)
CY   = (0,  222, 255)
CY2  = (0,  158, 195)
DCY  = (0,   42,  66)
VCY  = (148, 252, 255)
TEA  = (0,  198, 175)
DTEA = (0,   52,  48)
PNL  = (4,   13,  34)
WARN = (255, 188,   0)
CRIT = (255,  48,  48)
DIM  = (26,  56,  76)
WD   = (85,  62,   0)
CD   = (78,   8,   8)

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
                           capture_output=True, text=True, timeout=1)
        if r.returncode == 0: return float(r.stdout.strip())
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
    for path in ('/home', '/'):
        try:    return psutil.disk_usage(path)
        except: pass
    return None

def _freq():
    try:    return psutil.cpu_freq()
    except: return None

def _fan():
    try:
        f = psutil.sensors_fans()
        for v in f.values():
            if v: return int(v[0].current)
    except: pass
    return None

def _cpu_name():
    try:
        with open('/proc/cpuinfo') as f:
            for line in f:
                if 'model name' in line:
                    n = line.split(':')[1].strip()
                    n = n.replace('(TM)','').replace('(R)','').replace(' CPU','')
                    return ' '.join(n.split()[:4])[:22]
    except: pass
    return "CPU"

_nt  = [0, 0]
_ntx = [0]*40
_nrx = [0]*40

def _update_net():
    global _nt, _ntx, _nrx
    try:
        c = psutil.net_io_counters()
        tx, rx = c.bytes_sent, c.bytes_recv
        pt, pr = _nt
        if pt:
            _ntx = _ntx[1:] + [max(0, tx-pt)]
            _nrx = _nrx[1:] + [max(0, rx-pr)]
        _nt = [tx, rx]
    except: pass

def _fmt(b):
    if b>1_000_000: return f"{b/1_000_000:.1f}M"
    if b>1_000:     return f"{b/1_000:.0f}K"
    return f"{int(b)}B"

# ── Color helpers ─────────────────────────────────────────────────────────────
def _vc(v, w=70, c=90):
    if v < w: return CY
    if v < c: return WARN
    return CRIT

def _vd(col):
    if col == CY:   return DCY
    if col == WARN: return WD
    return CD

def _tc(t):
    if t is None: return DCY
    if t < 65: return CY
    if t < 80: return WARN
    return CRIT

# ── Primitivas ────────────────────────────────────────────────────────────────
def _glow(d, x, y, txt, font, col, sp=2):
    dim = _vd(col)
    for dx, dy in [(-sp,0),(sp,0),(0,-sp),(0,sp),(-sp,-sp),(sp,sp)]:
        d.text((x+dx, y+dy), txt, font=font, fill=dim)
    d.text((x, y), txt, font=font, fill=col)

def _ctr(d, cx, y, txt, font, col):
    bb = d.textbbox((0,0), txt, font=font)
    d.text((cx-(bb[2]-bb[0])//2, y), txt, font=font, fill=col)

def _glow_c(d, cx, y, txt, font, col, sp=2):
    bb = d.textbbox((0,0), txt, font=font)
    _glow(d, cx-(bb[2]-bb[0])//2, y, txt, font, col, sp)

def _panel(d, x, y, w, h, col=None):
    col = col or DCY
    d.rectangle([x,y,x+w,y+h], fill=PNL, outline=col, width=1)
    s = 7
    corners = [
        ((x,y),(x+s,y)), ((x,y),(x,y+s)),
        ((x+w,y),(x+w-s,y)), ((x+w,y),(x+w,y+s)),
        ((x,y+h),(x+s,y+h)), ((x,y+h),(x,y+h-s)),
        ((x+w,y+h),(x+w-s,y+h)), ((x+w,y+h),(x+w,y+h-s)),
    ]
    for p1, p2 in corners:
        d.line([p1, p2], fill=VCY, width=2)

def _hbar(d, x, y, w, h, pct, col, segs=20):
    d.rectangle([x-1,y-1,x+w+1,y+h+1], fill=(2,8,22), outline=DCY, width=1)
    sw = max(1, (w-segs)//segs)
    fi = int(pct/100*segs)
    for i in range(segs):
        sx = x + i*(sw+1)
        if i < fi:
            t = 0.5 + 0.5*i/segs
            d.rectangle([sx,y,sx+sw,y+h],
                fill=(min(255,int(col[0]*t)), min(255,int(col[1]*t)), min(255,int(col[2]*t))))
        else:
            d.rectangle([sx,y,sx+sw,y+h], fill=(4,12,28))

def _spark(d, x, y, w, h, data, col):
    if not any(data): return
    mx = max(data) or 1
    n  = len(data)
    pts = [(x+int(i*w/(n-1)), y+h-int(v/mx*h)) for i,v in enumerate(data)]
    if len(pts) > 1:
        d.line(pts, fill=col, width=1)

# ── Gauge circular tipo cockpit ───────────────────────────────────────────────
def _gauge(d, cx, cy, r, val, col, label=""):
    S, SPAN = -220, 260
    val = max(0.0, min(100.0, val))
    AW  = 18    # ancho del arco

    # Fondo negro del gauge
    d.ellipse([cx-r-8, cy-r-8, cx+r+8, cy+r+8], fill=(1,5,15))

    # Anillos decorativos exteriores (3 arcos tenues)
    for i, (off, bright) in enumerate([(r+6,18),(r+12,11),(r+18,6)]):
        d.arc([cx-off,cy-off,cx+off,cy+off],
              start=S, end=S+SPAN, fill=(0,bright,bright+8), width=1)

    # Ticks de escala
    N = 26
    for i in range(N+1):
        a   = math.radians(S + SPAN*i/N)
        big = (i % (N//5) == 0)
        r1  = r - (10 if big else 5)
        r2  = r + 5
        x1, y1 = cx+r1*math.cos(a), cy+r1*math.sin(a)
        x2, y2 = cx+r2*math.cos(a), cy+r2*math.sin(a)
        d.line([(x1,y1),(x2,y2)], fill=(VCY if big else DCY), width=(2 if big else 1))
        if big and 0 < i < N:
            pv  = int(100*i/N)
            nf  = Fm(10)
            nb  = d.textbbox((0,0), str(pv), font=nf)
            nx  = cx + (r+18)*math.cos(a) - (nb[2]-nb[0])//2
            ny  = cy + (r+18)*math.sin(a) - (nb[3]-nb[1])//2
            d.text((nx,ny), str(pv), font=nf, fill=DIM)

    # Pista de fondo
    IR = r - 10
    d.arc([cx-IR,cy-IR,cx+IR,cy+IR], start=S, end=S+SPAN, fill=(0,22,38), width=AW)
    # Borde interno de la pista
    d.arc([cx-IR+AW//2,cy-IR+AW//2,cx+IR-AW//2,cy+IR-AW//2],
          start=S, end=S+SPAN, fill=(0,30,50), width=1)

    # Arco de valor (mínimo 4% para visibilidad)
    arc_span = SPAN * max(val, 4) / 100
    arc_col  = _vc(val)
    d.arc([cx-IR,cy-IR,cx+IR,cy+IR], start=S, end=S+arc_span, fill=arc_col, width=AW)

    # Halo del arco (arco más ancho y tenue detrás)
    halo = _vd(arc_col)
    halo = tuple(min(255, c*3) for c in halo)
    d.arc([cx-IR-3,cy-IR-3,cx+IR+3,cy+IR+3], start=S, end=S+arc_span,
          fill=halo, width=AW+8)
    d.arc([cx-IR,cy-IR,cx+IR,cy+IR], start=S, end=S+arc_span, fill=arc_col, width=AW)

    # Dot y resplandor en la punta del arco
    tip_a  = math.radians(S + arc_span)
    tip_x  = cx + IR*math.cos(tip_a)
    tip_y  = cy + IR*math.sin(tip_a)
    for rs, alpha in [(9,30),(7,60),(5,120),(3,255)]:
        rc2 = tuple(min(255, int(c * alpha/255)) for c in VCY)
        d.ellipse([tip_x-rs,tip_y-rs,tip_x+rs,tip_y+rs], fill=rc2)

    # Anillo interior decorativo
    IIR = IR - AW - 6
    d.arc([cx-IIR,cy-IIR,cx+IIR,cy+IIR], start=0, end=360, fill=(0,35,55), width=1)
    # Segundo anillo más pequeño
    d.arc([cx-IIR+10,cy-IIR+10,cx+IIR-10,cy+IIR-10],
          start=S, end=S+SPAN, fill=(0,28,44), width=2)

    # Fondo interior negro para el número
    NR = IIR - 6
    d.ellipse([cx-NR,cy-NR,cx+NR,cy+NR], fill=(2,6,18))

    # Número central (Orbitron Black — máximo impacto)
    vs  = f"{val:.0f}"
    fsz = 96 if len(vs) < 3 else 80
    vf  = Fo(fsz)
    bb  = d.textbbox((0,0), vs, font=vf)
    tw, th = bb[2]-bb[0], bb[3]-bb[1]
    vx  = cx - tw//2 - bb[0]
    vy  = cy - th//2 - bb[1] - 6
    _glow(d, vx, vy, vs, vf, col, sp=5)

    # "%" en Rajdhani junto al número
    pf  = Fr(26)
    pb  = d.textbbox((0,0), "%", font=pf)
    d.text((cx + tw//2 + 4, vy + fsz//2 + 2), "%", font=pf, fill=CY2)

    # Label inferior
    if label:
        _glow_c(d, cx, cy+NR-24, label, Fr(18), CY2, sp=1)


# ── Render ────────────────────────────────────────────────────────────────────
def render(frame):
    if frame % 2 == 0:
        _update_net()

    img = Image.new('RGB', (W, H), BG)
    d   = ImageDraw.Draw(img)

    # Grilla de fondo sutil
    for x in range(0, W, 48): d.line([(x,0),(x,H)], fill=(0,13,28))
    for y in range(0, H, 48): d.line([(0,y),(W,y)], fill=(0,13,28))

    # Leer sensores
    cores = _cores()
    cpu   = sum(cores)/len(cores) if cores else 0.0
    mem   = _mem()
    ct    = _temp()
    gpu   = _gpu()
    gt    = _gtemp()
    disk  = _disk()
    freq  = _freq()
    fan   = _fan()
    now   = datetime.datetime.now()
    pulse = abs(math.sin(frame * 0.09))

    # ── TOP BAR 40px ─────────────────────────────────────────────────────────
    TB = 40
    d.rectangle([0,0,W,TB], fill=(3,11,29))
    d.line([(0,TB),(W,TB)], fill=CY, width=2)
    pw_ = int(pulse*90)
    d.line([(W//2-pw_,TB+1),(W//2+pw_,TB+1)], fill=VCY, width=1)

    blink = VCY if (frame%14)<9 else DCY
    d.ellipse([10,12,24,26], fill=blink, outline=CY, width=1)
    d.text((30,9), "SISTEMA ACTIVO", font=Fr(22), fill=CY)
    _ctr(d, W//2, 10, _cpu_name(), Fr(20), VCY)
    ts  = now.strftime("%H:%M:%S")
    tb2 = d.textbbox((0,0), ts, font=Fo(18))
    d.text((W-(tb2[2]-tb2[0])-10, 9), ts, font=Fo(18), fill=CY)

    # ── Layout ────────────────────────────────────────────────────────────────
    # UY..UB = zona útil vertical
    # Left [LX..LX+LW] | Center [MX..MX+MW] | Right [RX..RX+RW]
    UY  = TB + 5
    UB  = H - 22
    UH  = UB - UY       # ~413px

    LX, LW = 8, 192
    RW = 192
    RX  = W - 8 - RW
    MX  = LX + LW + 5
    MW  = RX - MX - 5
    GCX = MX + MW//2
    GCY = UY + 232      # centro gauge: 45+232=277
    GR  = 142           # radio: top=135, bot=419

    # ── Mini stats arriba del centro ──────────────────────────────────────────
    MINI_H = 50
    SLOT_W = MW // 3
    items = [
        ("CPU",  f"{cpu:.0f}%",                           _vc(cpu)),
        ("GPU",  f"{gpu:.0f}%" if gpu is not None else "--", _vc(gpu or 0)),
        ("DISK", f"{disk.percent:.0f}%" if disk else "--", _vc(disk.percent if disk else 0)),
    ]
    for i, (lbl, val, col2) in enumerate(items):
        sx = MX + i*SLOT_W
        _panel(d, sx+2, UY, SLOT_W-5, MINI_H, col2)
        d.text((sx+10, UY+4),  lbl, font=Fr(16), fill=col2)
        d.text((sx+10, UY+20), val, font=Fo(24), fill=col2)

    # Líneas decorativas que conectan mini stats con el gauge
    for i in range(3):
        sx = MX + i*SLOT_W + SLOT_W//2
        d.line([(sx, UY+MINI_H+1),(sx, UY+MINI_H+8)], fill=DCY, width=1)

    # ── GAUGE ─────────────────────────────────────────────────────────────────
    _gauge(d, GCX, GCY, GR, cpu, _vc(cpu), "CPU LOAD")

    # Decoración: líneas horizontales que salen del gauge
    ga_left  = GCX - GR - 8
    ga_right = GCX + GR + 8
    d.line([(MX+2, GCY),(ga_left, GCY)], fill=DCY, width=1)
    d.line([(ga_right, GCY),(MX+MW-2, GCY)], fill=DCY, width=1)
    d.ellipse([ga_left-3,GCY-3,ga_left+3,GCY+3], fill=CY2)
    d.ellipse([ga_right-3,GCY-3,ga_right+3,GCY+3], fill=CY2)

    # ── Reloj compacto bajo el gauge ──────────────────────────────────────────
    CLK_Y = GCY + GR + 12  # ~419+12=431
    cs2   = now.strftime("%H:%M")
    cf2   = Fo(32)
    cb2   = d.textbbox((0,0), cs2, font=cf2)
    cx_   = GCX - (cb2[2]-cb2[0])//2
    _glow(d, cx_, CLK_Y, cs2, cf2, VCY, sp=3)
    sc2 = now.strftime(":%S")
    d.text((cx_+(cb2[2]-cb2[0])+2, CLK_Y+7), sc2, font=Fo(18), fill=CY2)
    # Fecha en la misma línea a la derecha
    ds2 = now.strftime("%d/%m/%y")
    d.text((GCX+80, CLK_Y+9), ds2, font=Fr(16), fill=DCY)

    # ── PANEL IZQUIERDO ───────────────────────────────────────────────────────
    py = UY

    # CPU — 148px
    H1 = 148
    _panel(d, LX, py, LW, H1)
    d.text((LX+8, py+5), "CPU", font=Fr(26), fill=CY)
    if ct is not None:
        d.text((LX+LW-62, py+6), f"{ct:.0f}C", font=Fd(20), fill=_tc(ct))
    cc_ = _vc(cpu)
    _glow(d, LX+8, py+32, f"{cpu:.1f}%", Fo(38), cc_, 2)
    _hbar(d, LX+8, py+80, LW-16, 9, cpu, cc_)
    if freq:
        d.text((LX+8, py+95), f"{freq.current/1000:.2f} GHz", font=Fd(16), fill=CY2)
    d.text((LX+8, py+115), "CORES", font=Fr(15), fill=DCY)
    nc  = min(len(cores), 8)
    bw2 = (LW-20)//nc - 2
    for i in range(nc):
        bx2 = LX+8 + i*(bw2+2)
        bh2 = max(2, int(cores[i]/100*26))
        d.rectangle([bx2, py+132, bx2+bw2, py+145], fill=(4,12,28))
        d.rectangle([bx2, py+145-bh2, bx2+bw2, py+145], fill=_vc(cores[i]))
    py += H1 + 5

    # MEMORIA — 90px
    H2 = 90
    _panel(d, LX, py, LW, H2)
    d.text((LX+8, py+4), "MEMORIA", font=Fr(20), fill=CY)
    ram = (mem.total-mem.available)/1024**3
    tot = mem.total/1024**3
    rc_ = _vc(mem.percent)
    _glow(d, LX+8, py+26, f"{ram:.1f}G", Fo(32), rc_, 2)
    d.text((LX+LW-50, py+38), f"/{tot:.0f}G", font=Fd(16), fill=CY2)
    _hbar(d, LX+8, py+68, LW-16, 8, mem.percent, rc_)
    d.text((LX+8, py+80), f"{mem.percent:.0f}%  {ram:.1f}/{tot:.0f}G", font=Fm(12), fill=DIM)
    py += H2 + 5

    # DISCO — 76px
    H3 = 76
    _panel(d, LX, py, LW, H3)
    d.text((LX+8, py+4), "DISCO", font=Fr(20), fill=CY)
    if disk:
        dc_ = _vc(disk.percent, 75, 90)
        dg_ = disk.used/1024**3
        dt_ = disk.total/1024**3
        _glow(d, LX+8, py+26, f"{dg_:.0f}G", Fo(28), dc_, 2)
        d.text((LX+LW-48, py+36), f"/{dt_:.0f}G", font=Fd(14), fill=CY2)
        _hbar(d, LX+8, py+58, LW-16, 8, disk.percent, dc_)
        d.text((LX+8, py+70), f"{disk.percent:.0f}% USADO", font=Fm(12), fill=DIM)
    py += H3 + 5

    # RED — resto izquierda
    H4 = UB - py
    if H4 > 42:
        _panel(d, LX, py, LW, H4)
        d.text((LX+8, py+4), "RED", font=Fr(18), fill=CY)
        d.text((LX+8, py+24), f"UP {_fmt(_ntx[-1])}/s", font=Fd(13), fill=TEA)
        d.text((LX+8, py+38), f"DL {_fmt(_nrx[-1])}/s", font=Fd(13), fill=CY2)
        sh = (H4-58)//2 - 2
        if sh > 4:
            _spark(d, LX+8, py+54, LW-16, sh, _ntx, TEA)
            _spark(d, LX+8, py+56+sh, LW-16, sh, _nrx, CY2)

    # ── PANEL DERECHO ─────────────────────────────────────────────────────────
    py = UY

    # GPU — 148px
    H5 = 148
    _panel(d, RX, py, RW, H5, TEA)
    d.text((RX+8, py+5), "GPU", font=Fr(26), fill=TEA)
    if gpu is not None:
        if gt is not None:
            d.text((RX+RW-62, py+6), f"{gt:.0f}C", font=Fd(20), fill=_tc(gt))
        gc_ = _vc(gpu)
        _glow(d, RX+8, py+32, f"{gpu:.1f}%", Fo(38), gc_, 2)
        _hbar(d, RX+8, py+80, RW-16, 9, gpu, gc_)
        d.text((RX+8, py+95), "GPU LOAD", font=Fr(16), fill=DTEA)
        d.text((RX+8, py+115), "CORES", font=Fr(15), fill=DTEA)
        nc2 = min(len(cores), 8)
        bw3 = (RW-20)//nc2-2
        for i in range(nc2):
            bx3 = RX+8+i*(bw3+2)
            bh3 = max(2, int(cores[i]/100*26))
            d.rectangle([bx3, py+132, bx3+bw3, py+145], fill=(4,12,28))
            d.rectangle([bx3, py+145-bh3, bx3+bw3, py+145], fill=TEA)
    else:
        d.text((RX+8, py+5), "CORES DETAIL", font=Fr(18), fill=CY)
        for i, cv in enumerate(cores[:8]):
            ry3 = py+32+i*14
            _hbar(d, RX+30, ry3+1, RW-40, 8, cv, _vc(cv))
            d.text((RX+8, ry3), f"C{i}", font=Fm(11), fill=DIM)
    py += H5 + 5

    # VOLTAJE — 78px
    H6 = 78
    _panel(d, RX, py, RW, H6)
    d.text((RX+8, py+4), "VOLTAJE", font=Fr(20), fill=CY)
    volt = None
    try:
        rv = subprocess.run(['sensors'], capture_output=True, text=True, timeout=2)
        for line in rv.stdout.split('\n'):
            if 'Vcore' in line or 'vccp' in line.lower():
                for p in line.split():
                    try:
                        v2 = float(p.replace('V','').replace('+',''))
                        if 0.4 < v2 < 2.5: volt=v2; break
                    except: pass
                if volt: break
    except: pass
    if volt:
        _glow(d, RX+8, py+26, f"{volt:.3f}V", Fo(28), VCY, 2)
        d.text((RX+8, py+62), "VCORE", font=Fr(16), fill=DCY)
    else:
        d.text((RX+8, py+28), "N/A", font=Fo(22), fill=DCY)
        d.text((RX+8, py+62), "VCORE", font=Fr(16), fill=DIM)
    health = "OK" if (ct or 0)<80 and cpu<90 and mem.percent<85 else "WARN"
    hcol = CY if health=="OK" else WARN
    d.text((RX+RW-52, py+62), health, font=Fd(16), fill=hcol)
    py += H6 + 5

    # FAN — 80px
    H7 = 80
    _panel(d, RX, py, RW, H7)
    d.text((RX+8, py+4), "FAN", font=Fr(22), fill=CY)
    if fan:
        fc3 = CY if fan<2500 else WARN if fan<3500 else CRIT
        _glow(d, RX+8, py+26, str(fan), Fo(28), fc3, 2)
        d.text((RX+8, py+62), "RPM", font=Fr(16), fill=DCY)
        fa2 = frame * 0.13 * (fan/1500)
        for i in range(4):
            a3  = fa2 + i*math.pi/2
            bx4 = (RX+RW-36) + int(13*math.cos(a3))
            by4 = (py+44)     + int(13*math.sin(a3))
            d.ellipse([bx4-4,by4-4,bx4+4,by4+4], fill=TEA)
        d.ellipse([RX+RW-40,py+40,RX+RW-32,py+48], fill=CY)
    else:
        d.text((RX+8, py+28), "--", font=Fo(24), fill=DCY)
        d.text((RX+8, py+62), "RPM", font=Fr(16), fill=DIM)
    if ct is not None:
        d.text((RX+RW-72, py+62), f"{ct:.1f}C", font=Fd(16), fill=_tc(ct))
    py += H7 + 5

    # UPTIME — resto derecha
    H8 = UB - py
    if H8 > 42:
        _panel(d, RX, py, RW, H8)
        uptime = now - datetime.datetime.fromtimestamp(psutil.boot_time())
        uh_, um_ = divmod(int(uptime.total_seconds())//60, 60)
        d.text((RX+8, py+4), "UPTIME", font=Fr(18), fill=DCY)
        d.text((RX+8, py+22), f"{uh_}h {um_:02d}m", font=Fo(20), fill=CY2)
        d.text((RX+8, py+50), f"PROC {len(psutil.pids())}", font=Fr(15), fill=DCY)
        d.text((RX+8, py+68) if H8>80 else (RX+8, py+50),
               f"MEM {mem.percent:.0f}%", font=Fm(13), fill=DIM)

    # ── BOTTOM BAR ────────────────────────────────────────────────────────────
    d.line([(0,UB),(W,UB)], fill=CY, width=2)
    d.rectangle([0,UB+2,W,H], fill=(3,11,28))
    uptime2 = now - datetime.datetime.fromtimestamp(psutil.boot_time())
    uh2, um2 = divmod(int(uptime2.total_seconds())//60, 60)
    d.text((10, UB+4), f"UP {uh2}h{um2:02d}m", font=Fm(13), fill=DCY)
    d.text((150, UB+4), f"PROC {len(psutil.pids())}", font=Fm(13), fill=DCY)
    d.text((288, UB+4), now.strftime("%a %d/%m/%Y"), font=Fm(13), fill=DIM)
    pw4 = int(pulse*80)
    d.line([(W//2-pw4,UB+2),(W//2+pw4,UB+2)], fill=VCY, width=2)

    return img
