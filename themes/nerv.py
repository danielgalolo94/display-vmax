"""
Tema: NERV — Evangelion HUD / MAGI System
Display landscape 960×480
Fondo negro con grilla hexagonal, colores naranja y lima, estética NERV/MAGI.
"""
import math, random, datetime, subprocess, threading, time, socket
import psutil
from PIL import Image, ImageDraw, ImageFont, ImageOps

W, H = 960, 480
import os
_BASE   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ASSETS = os.path.join(_BASE, "assets")
_FD     = os.path.join(_BASE, "fonts")

_F_ORB = os.path.join(_FD, "Orbitron-Black.ttf")
_F_RAJ = os.path.join(_FD, "Rajdhani-SemiBold.ttf")
_F_DAT = os.path.join(_FD, "NotoSansMono-Bold.ttf")
_F_MON = os.path.join(_FD, "ShareTechMono.ttf")
_F_NRD = os.path.join(_FD, "FiraCodeNerdFont-Medium.ttf")
_F_TEK = os.path.join(_FD, "Teko-Medium.ttf")

_FC = {}
def _fnt(p, s):
    k = (p, s)
    if k not in _FC:
        try:    _FC[k] = ImageFont.truetype(p, s)
        except: _FC[k] = ImageFont.load_default()
    return _FC[k]

Fo = lambda s: _fnt(_F_ORB, s)
Fr = lambda s: _fnt(_F_RAJ, s)
Fd = lambda s: _fnt(_F_DAT, s)
Fm = lambda s: _fnt(_F_MON, s)
Fn = lambda s: _fnt(_F_NRD, s)
Ft = lambda s: _fnt(_F_TEK, s)

# ── Paleta NERV ───────────────────────────────────────────────────────────────
BG     = (6,   6,   8)
ORANGE = (215,  95,  5)
LIME   = (145, 210,  0)
INK    = (225, 195, 140)
INK2   = (155, 120,  75)
INK3   = (75,   55,  28)
DIVL   = (35,   20,   8)
TRACK  = (18,   10,   4)
WARN   = (230, 160,  10)
CRIT   = (220,  35,  35)
GRN    = (40,  200,  80)
CY     = (0,   190, 240)

# ── Hexágono de fondo (precalculado) ─────────────────────────────────────────
_hex_bg_img = None
_hex_done   = False
_HEX_CENTERS = []   # (cx, cy, pts) for each hex cell
_HEX_POLYS   = []   # pts list for each hex cell

def _build_hex_bg():
    global _hex_bg_img, _hex_done, _HEX_CENTERS, _HEX_POLYS
    if _hex_done:
        return
    img = Image.new('RGB', (W, H), BG)
    d   = ImageDraw.Draw(img)
    R   = 26
    HEX_COL = (22, 13, 5)
    dx  = int(R * math.sqrt(3))
    dy  = int(R * 1.5)
    cols = W // dx + 3
    rows = H // dy + 3
    for row in range(rows):
        for col in range(cols):
            cx = col * dx + (dx // 2 if row % 2 else 0) - dx
            cy = row * dy - R
            pts = []
            for i in range(6):
                a = math.radians(60 * i - 30)
                pts.append((cx + R * math.cos(a), cy + R * math.sin(a)))
            for i in range(6):
                x1, y1 = pts[i]
                x2, y2 = pts[(i+1) % 6]
                d.line([(x1, y1), (x2, y2)], fill=HEX_COL, width=1)
            _HEX_CENTERS.append((cx, cy))
            _HEX_POLYS.append(pts)
    _hex_bg_img = img
    _hex_done   = True

_build_hex_bg()

# ── Sensores ──────────────────────────────────────────────────────────────────
def _cores():
    try:    return psutil.cpu_percent(percpu=True, interval=None)
    except: return [0.0] * 4

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
    for mount in ['/home', '/']:
        try:
            d = psutil.disk_usage(mount)
            return d, mount
        except: pass
    return None, '/'

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

def _gpu_name():
    try:
        r = subprocess.run(['cat','/sys/class/drm/card1/device/product_name'],
                           capture_output=True, text=True, timeout=1)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()[:18]
    except: pass
    return "GPU"

def _vram():
    try:
        u = int(open('/sys/class/drm/card1/device/mem_info_vram_used').read().strip())
        t = int(open('/sys/class/drm/card1/device/mem_info_vram_total').read().strip())
        return u / 1024**3, t / 1024**3
    except: return None, None

_ni = {'iface': None, 'ip': None, 'ts': 0.0}

def _net_info():
    if time.time() - _ni['ts'] < 10:
        return _ni['iface'], _ni['ip']
    try:
        stats    = psutil.net_if_stats()
        addrs    = psutil.net_if_addrs()
        counters = psutil.net_io_counters(pernic=True)
        best, best_b = None, 0
        for iface, cnt in counters.items():
            if iface == 'lo': continue
            if not stats.get(iface) or not stats[iface].isup: continue
            total = cnt.bytes_sent + cnt.bytes_recv
            if total > best_b:
                best_b, best = total, iface
        if best and best in addrs:
            for addr in addrs[best]:
                if addr.family == socket.AF_INET:
                    _ni.update({'iface': best[:10], 'ip': addr.address, 'ts': time.time()})
                    return _ni['iface'], _ni['ip']
    except: pass
    _ni['ts'] = time.time()
    return _ni.get('iface'), _ni.get('ip')

_nt  = [0, 0]
_ntx = [0] * 40
_nrx = [0] * 40

_dt  = [0, 0]
_dwr = [0] * 40
_drr = [0] * 40

def _update_disk_io():
    global _dt, _dwr, _drr
    try:
        c = psutil.disk_io_counters()
        if c:
            w, r = c.write_bytes, c.read_bytes
            pw, pr = _dt
            if pw:
                _dwr = _dwr[1:] + [max(0, w - pw)]
                _drr = _drr[1:] + [max(0, r - pr)]
            _dt = [w, r]
    except: pass

def _update_net():
    global _nt, _ntx, _nrx
    try:
        c = psutil.net_io_counters()
        tx, rx = c.bytes_sent, c.bytes_recv
        pt, pr = _nt
        if pt:
            _ntx = _ntx[1:] + [max(0, tx - pt)]
            _nrx = _nrx[1:] + [max(0, rx - pr)]
        _nt = [tx, rx]
    except: pass

def _fmt(b):
    if b > 1_000_000: return f"{b/1_000_000:.1f}M"
    if b > 1_000:     return f"{b/1_000:.0f}K"
    return f"{int(b)}B"

def _volt():
    try:
        r = subprocess.run(['sensors'], capture_output=True, text=True, timeout=2)
        for line in r.stdout.split('\n'):
            if 'Vcore' in line or 'vccp' in line.lower():
                for p in line.split():
                    try:
                        v = float(p.replace('V','').replace('+',''))
                        if 0.4 < v < 2.5: return v
                    except: pass
    except: pass
    return None

_upd = {'count': None, 'checking': False, 'ts': 0.0}

def _bg_check_updates():
    try:
        r = subprocess.run(
            ['dnf', 'check-update', '-q', '--cacheonly'],
            capture_output=True, text=True, timeout=15
        )
        if r.returncode in (0, 100):
            lines = [l for l in r.stdout.strip().splitlines()
                     if l and not l.startswith('Obsoleting') and not l.startswith('Last')]
            _upd['count'] = len(lines)
        else:
            r2 = subprocess.run(
                ['dnf', 'list', 'updates', '-q'],
                capture_output=True, text=True, timeout=30
            )
            lines = [l for l in r2.stdout.strip().splitlines()
                     if l and not l.startswith('Last') and not l.startswith('Obsoleting')]
            _upd['count'] = max(0, len(lines) - 1)
    except Exception:
        _upd['count'] = None
    finally:
        _upd['checking'] = False
        _upd['ts'] = time.time()

def _get_updates():
    now = time.time()
    if not _upd['checking'] and (now - _upd['ts']) > 600:
        _upd['checking'] = True
        _upd['ts'] = now
        threading.Thread(target=_bg_check_updates, daemon=True).start()
    return _upd['count']

_HOSTNAME = socket.gethostname()

# ── Color helpers ─────────────────────────────────────────────────────────────
def _vc(v, w=70, c=90):
    if v < w: return ORANGE
    if v < c: return WARN
    return CRIT

def _tc(t):
    if t is None: return LIME
    if t < 65:    return LIME
    if t < 80:    return WARN
    return CRIT

# ── Primitivas ────────────────────────────────────────────────────────────────
def _ctr(d, cx, y, txt, font, col):
    bb = d.textbbox((0,0), txt, font=font)
    d.text((cx-(bb[2]-bb[0])//2, y), txt, font=font, fill=col)

def _right(d, rx, y, txt, font, col):
    bb = d.textbbox((0,0), txt, font=font)
    d.text((rx-(bb[2]-bb[0]), y), txt, font=font, fill=col)

def _section(d, x, y, accent, label):
    d.rectangle([x, y, x+3, y+26], fill=accent)
    glow = tuple(min(255, c//3) for c in accent)
    d.rectangle([x+3, y, x+8, y+26], fill=glow)
    d.text((x+9, y+3), label, font=Fr(28), fill=INK2)

def _hbar(d, x, y, w, h, pct, col):
    d.rectangle([x,y,x+w,y+h], fill=TRACK)
    fw = int(pct/100*w)
    if fw > 0:
        glow = tuple(min(255, c//3) for c in col)
        d.rectangle([x,y,x+fw,y+h], fill=glow)
        for i in range(fw):
            t = 0.45 + 0.55*(i/fw)
            d.line([(x+i,y),(x+i,y+h)],
                fill=(min(255,int(col[0]*t)), min(255,int(col[1]*t)), min(255,int(col[2]*t))))
        d.line([(x+fw-1,y),(x+fw-1,y+h)], fill=INK)

def _spark(d, x, y, w, h, data, col):
    if not any(data): return
    mx = max(data) or 1
    n  = len(data)
    pts = [(x + int(i*w/(n-1)), y+h - int(v/mx*h)) for i,v in enumerate(data)]
    if len(pts) > 1:
        d.line(pts, fill=col, width=1)

def _divider(d, x, y, w):
    d.line([(x,y),(x+w,y)], fill=DIVL, width=1)

# ── Gauge NERV (doble arco con colores naranja/lima) ─────────────────────────
def _gauge(d, cx, cy, r, cpu, temp):
    S, SPAN = -220, 260
    AW = 22
    TW = 10
    IR = r - 12
    TR = IR - AW - 10

    # Glow exterior naranja
    for rr_off, al in [(18, 30),(14, 22),(10, 15),(6, 10)]:
        rr = r + rr_off - al//3
        gv = min(255, ORANGE[0]*al//30)
        d.ellipse([cx-rr,cy-rr,cx+rr,cy+rr],
                  fill=(gv, min(255,ORANGE[1]*al//30), 0))

    d.ellipse([cx-r-2,cy-r-2,cx+r+2,cy+r+2], fill=(20, 10, 4))
    d.ellipse([cx-r,cy-r,cx+r,cy+r], fill=BG)

    # Ticks
    N = 26
    for i in range(N+1):
        a   = math.radians(S + SPAN*i/N)
        big = (i % (N//5) == 0)
        r1  = r - (14 if big else 6)
        r2  = r + 2
        x1,y1 = cx+r1*math.cos(a), cy+r1*math.sin(a)
        x2,y2 = cx+r2*math.cos(a), cy+r2*math.sin(a)
        tick_col = INK2 if big else DIVL
        d.line([(x1,y1),(x2,y2)], fill=tick_col, width=(2 if big else 1))
        if big and 0 < i < N:
            pv = int(100*i/N)
            nf = Fm(14)
            nb = d.textbbox((0,0), str(pv), font=nf)
            nx = cx+(r+16)*math.cos(a)-(nb[2]-nb[0])//2
            ny = cy+(r+16)*math.sin(a)-(nb[3]-nb[1])//2
            d.text((nx,ny), str(pv), font=nf, fill=INK3)

    # Pista arco CPU
    d.arc([cx-IR,cy-IR,cx+IR,cy+IR], start=S, end=S+SPAN, fill=TRACK, width=AW)

    # Arco CPU — ORANGE
    arc_cpu = int(SPAN * max(cpu, 3) / 100)
    cpu_col  = ORANGE if cpu < 90 else CRIT
    halo = tuple(min(255, c//2) for c in cpu_col)
    d.arc([cx-IR-6,cy-IR-6,cx+IR+6,cy+IR+6],
          start=S, end=S+arc_cpu, fill=halo, width=AW+14)
    d.arc([cx-IR-2,cy-IR-2,cx+IR+2,cy+IR+2],
          start=S, end=S+arc_cpu, fill=cpu_col, width=AW+4)
    d.arc([cx-IR,cy-IR,cx+IR,cy+IR], start=S, end=S+arc_cpu, fill=cpu_col, width=AW)
    d.arc([cx-IR+AW//2-2,cy-IR+AW//2-2,cx+IR-AW//2+2,cy+IR-AW//2+2],
          start=S, end=S+arc_cpu, fill=tuple(min(255,c+80) for c in cpu_col), width=2)

    tip_a = math.radians(S + arc_cpu)
    tx,ty = cx+IR*math.cos(tip_a), cy+IR*math.sin(tip_a)
    d.ellipse([tx-13,ty-13,tx+13,ty+13], fill=halo)
    d.ellipse([tx-9, ty-9, tx+9, ty+9],  fill=BG, outline=cpu_col, width=2)
    d.ellipse([tx-4, ty-4, tx+4, ty+4],  fill=cpu_col)

    # Arco temperatura — LIME
    d.arc([cx-TR,cy-TR,cx+TR,cy+TR], start=S, end=S+SPAN, fill=TRACK, width=TW)
    if temp is not None:
        arc_t = int(SPAN * min(temp, 100) / 100)
        tcol  = _tc(temp)
        thalo = tuple(min(255, c//2) for c in tcol)
        d.arc([cx-TR-2,cy-TR-2,cx+TR+2,cy+TR+2], start=S, end=S+arc_t, fill=thalo, width=TW+4)
        d.arc([cx-TR,cy-TR,cx+TR,cy+TR], start=S, end=S+arc_t, fill=tcol, width=TW)

    # Círculo interior
    NR = TR - TW - 10
    d.ellipse([cx-NR,cy-NR,cx+NR,cy+NR], fill=BG)

    vs   = f"{cpu:.0f}"
    fsz  = 96 if len(vs) < 3 else 80
    vf   = Fo(fsz)
    bb   = d.textbbox((0,0), vs, font=vf)
    tw2, th = bb[2]-bb[0], bb[3]-bb[1]
    vx   = cx - tw2//2 - bb[0]
    vy   = cy - th//2  - bb[1] - 8
    for off in [(2,2),(-2,2),(2,-2),(-2,-2)]:
        d.text((vx+off[0], vy+off[1]), vs, font=vf,
               fill=tuple(min(255, c//4) for c in cpu_col))
    d.text((vx, vy), vs, font=vf, fill=INK)
    d.text((cx+tw2//2+3, vy+fsz//2+4), "%", font=Fr(26), fill=INK2)
    _ctr(d, cx, cy+NR-28, "CASPAR", Fm(18), INK3)


# ── Render ────────────────────────────────────────────────────────────────────
def render(frame):
    if frame % 2 == 0:
        _update_net()
        _update_disk_io()

    # Fondo con grilla hexagonal
    if _hex_bg_img:
        img = _hex_bg_img.copy()
    else:
        img = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(img)

    # Animación: ripple hexagonal pulsante desde el centro
    for idx, (hcx, hcy) in enumerate(_HEX_CENTERS):
        dist = math.sqrt((hcx - W/2)**2 + (hcy - H/2)**2)
        ripple_phase = (frame * 8 - dist * 0.15) % (2 * math.pi)
        brightness = max(0, math.sin(ripple_phase)) * 0.4 + 0.1
        if brightness > 0.12:
            bv = int(brightness * 80)
            glow_col = (min(255, bv*2), min(255, bv), 0)
            pts = _HEX_POLYS[idx]
            d.polygon(pts, fill=glow_col)

    # Datos
    cores  = _cores()
    cpu    = sum(cores)/len(cores) if cores else 0.0
    mem    = _mem()
    ct     = _temp()
    gpu    = _gpu()
    gt     = _gtemp()
    disk, disk_mount = _disk()
    freq   = _freq()
    fan    = _fan()
    now    = datetime.datetime.now()
    cpu_nm = _cpu_name()
    gpu_nm = _gpu_name() if gpu is not None else "GPU"

    # ── TOP BAR (60px) ────────────────────────────────────────────────────────
    TB = 60
    d.rectangle([0,0,W,TB], fill=BG)
    d.line([(0,TB-2),(W,TB-2)], fill=ORANGE, width=2)

    # Texto central: título NERV con CJK
    title = "MAGI SYSTEM — NERV HQ — 第三新東京市"
    try:
        _ctr(d, W//2, 14, title, Fr(22), ORANGE)
    except Exception:
        _ctr(d, W//2, 14, "** MAGI SYSTEM -- NERV HQ **", Fr(22), ORANGE)

    # Reloj LIME
    ts = now.strftime("%H:%M:%S")
    bb = d.textbbox((0,0), ts, font=Fo(28))
    d.text((W - (bb[2]-bb[0]) - 10, 8), ts, font=Fo(28), fill=LIME)

    # ALERT LVL derecha — removed (too small, time takes that spot)

    # ── LAYOUT ───────────────────────────────────────────────────────────────
    UY = TB + 5
    UB = H
    LX, LW = 12, 190
    RX, RW = W-12-190, 190
    MX  = LX+LW+6
    MW  = RX-MX-6
    GCX = MX + MW//2
    GCY = UY + 190
    GR  = 162

    # ── GAUGE ─────────────────────────────────────────────────────────────────
    _gauge(d, GCX, GCY, GR, cpu, ct)

    # Líneas decorativas
    ga_l = GCX - GR - 6
    ga_r = GCX + GR + 6
    d.line([(MX+4, GCY),(ga_l, GCY)], fill=DIVL, width=1)
    d.line([(ga_r, GCY),(MX+MW-4, GCY)], fill=DIVL, width=1)
    d.ellipse([ga_l-3,GCY-3,ga_l+3,GCY+3], fill=INK3)
    d.ellipse([ga_r-3,GCY-3,ga_r+3,GCY+3], fill=INK3)

    # Texto bajo el gauge
    CLK_Y = GCY + GR + 10
    _ctr(d, GCX, CLK_Y,    "AT-FIELD STATUS : INACTIVE", Fm(20), ORANGE)
    _ctr(d, GCX, CLK_Y+26, now.strftime("%A  %d / %m / %Y"), Fr(20), INK3)

    # ── PANEL IZQUIERDO ───────────────────────────────────────────────────────
    py = UY

    # CPU
    _section(d, LX, py, ORANGE, "CPU  プロセサ")
    cc = ORANGE if cpu >= 70 else INK
    d.text((LX+9, py+28), f"{cpu:.1f}%", font=Fo(56), fill=cc)
    if ct is not None:
        col_t = _tc(ct)
        d.text((LX+LW-52, py+28), f"{ct:.0f}C", font=Fd(18), fill=col_t)
    _hbar(d, LX+9, py+86, LW-18, 14, cpu, ORANGE if cpu<70 else CRIT)
    py += 106
    _divider(d, LX, py, LW)
    py += 6

    # MEMORIA
    _section(d, LX, py, GRN, "MEM  メモリ")
    ram = (mem.total-mem.available)/1024**3
    tot = mem.total/1024**3
    rc  = GRN if mem.percent < 80 else WARN
    d.text((LX+9, py+28), f"{ram:.1f}G", font=Fo(46), fill=rc)
    _right(d, LX+LW-4, py+40, f"/{tot:.0f}G", Fd(18), INK3)
    _hbar(d, LX+9, py+74, LW-18, 14, mem.percent, GRN)
    d.text((LX+9, py+91), f"{mem.percent:.0f}%  {ram:.1f}/{tot:.0f}G", font=Fm(18), fill=INK3)
    py += 112
    _divider(d, LX, py, LW)
    py += 6

    # DISCO
    _section(d, LX, py, ORANGE, "DISC ストレージ")
    if disk:
        dc  = ORANGE if disk.percent < 80 else CRIT
        dg  = disk.used/1024**3
        dt  = disk.total/1024**3
        d.text((LX+9, py+28), f"{dg:.0f}G", font=Fo(40), fill=dc)
        _right(d, LX+LW-4, py+38, f"/{dt:.0f}G", Fd(16), INK3)
        d.text((LX+9, py+72), f"{disk.percent:.0f}%  libre: {dt-dg:.0f}G", font=Fm(16), fill=INK3)
        _hbar(d, LX+9, py+88, LW-18, 14, disk.percent, ORANGE)
        py += 106
    else:
        d.text((LX+9, py+28), "N/A", font=Fo(36), fill=INK3)
        py += 60
    _divider(d, LX, py, LW)
    py += 6

    # RED
    _section(d, LX, py, LIME, "NET  ネットワーク")
    tx_v = _ntx[-1]; rx_v = _nrx[-1]
    iface, ip = _net_info()
    d.text((LX+9, py+28), f"UP {_fmt(tx_v)}/s", font=Fd(20), fill=LIME)
    d.text((LX+9, py+50), f"DL {_fmt(rx_v)}/s", font=Fd(20), fill=INK3)

    # ── PANEL DERECHO ─────────────────────────────────────────────────────────
    py = UY

    # GPU
    _section(d, RX, py, CY, "GPU")
    vu, vt = _vram()
    if gpu is not None:
        gc  = CY if gpu < 70 else WARN
        d.text((RX+9, py+28), f"{gpu:.1f}%", font=Fo(46), fill=gc)
        if gt is not None:
            d.text((RX+RW-52, py+28), f"{gt:.0f}C", font=Fd(18), fill=_tc(gt))
        _hbar(d, RX+9, py+74, RW-18, 14, gpu, CY)
        if vu is not None:
            d.text((RX+9, py+92), f"VRAM {vu:.1f}/{vt:.0f}G", font=Fm(18), fill=INK3)
        else:
            d.text((RX+9, py+92), gpu_nm, font=Fm(18), fill=INK3)
    else:
        d.text((RX+9, py+28), "--", font=Fo(44), fill=INK3)
    py += 112
    _divider(d, RX, py, RW)
    py += 6

    # DISCO IO
    _section(d, RX, py, ORANGE, "DISCO IO")
    wr_now = _dwr[-1]
    rd_now = _drr[-1]
    writing = wr_now > 500_000
    wr_col  = (ORANGE if (frame % 8) < 5 else WARN) if writing else INK2
    d.text((RX+9, py+32), f"WR {_fmt(wr_now)}", font=Fo(30), fill=wr_col)
    d.text((RX+9, py+66), f"RD {_fmt(rd_now)}", font=Fd(18), fill=INK3)
    if writing and (frame % 8) < 5:
        d.ellipse([RX+RW-20, py+62, RX+RW-2, py+80],
                  fill=tuple(min(255, c//2) for c in ORANGE))
        d.ellipse([RX+RW-17, py+65, RX+RW-5, py+77], fill=ORANGE)
    else:
        d.ellipse([RX+RW-17, py+65, RX+RW-5, py+77], fill=TRACK)
    py += 90
    _divider(d, RX, py, RW)
    py += 6

    # FAN
    _section(d, RX, py, LIME, "FAN")
    if fan is not None:
        fc = LIME if fan < 2500 else WARN if fan < 3500 else CRIT
        d.text((RX+9, py+32), str(fan), font=Fo(34), fill=fc)
        d.text((RX+9, py+70), "RPM", font=Fr(22), fill=INK3)
    else:
        if ct is not None:
            tc2 = _tc(ct)
            d.text((RX+9, py+32), f"{ct:.1f}", font=Fo(38), fill=tc2)
            d.text((RX+9, py+74), "°C  CPU", font=Fr(22), fill=INK3)
        else:
            d.text((RX+9, py+32), "sin sensor", font=Fm(20), fill=INK3)
    py += 96
    _divider(d, RX, py, RW)
    py += 6

    # SISTEMA (load + uptime combinados)
    _section(d, RX, py, GRN, "SISTEMA")
    la  = os.getloadavg()
    nc2 = psutil.cpu_count() or 4
    lc  = GRN if la[0] < nc2*0.7 else WARN if la[0] < nc2 else CRIT
    d.text((RX+9,     py+28), f"{la[0]:.2f}", font=Fo(28), fill=lc)
    d.text((RX+9+70,  py+32), f"{la[1]:.2f}", font=Fd(18), fill=INK2)
    d.text((RX+9+120, py+32), f"{la[2]:.2f}", font=Fd(18), fill=INK3)
    d.text((RX+9,     py+50), "1m",  font=Fm(18), fill=lc)
    d.text((RX+9+70,  py+50), "5m",  font=Fm(18), fill=INK3)
    d.text((RX+9+120, py+50), "15m", font=Fm(18), fill=INK3)
    uptime = now - datetime.datetime.fromtimestamp(psutil.boot_time())
    uh, um = divmod(int(uptime.total_seconds())//60, 60)
    d.text((RX+9, py+70), f"{uh}h {um:02d}m", font=Fo(22), fill=INK)

    return img
