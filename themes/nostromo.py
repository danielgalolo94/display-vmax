"""
Tema: NOSTROMO — Weyland-Yutani MU/TH/UR 6000 Terminal
Display landscape 960×480
Monocromático verde fósforo, estética CRT, fuente mono.
"""
import math, datetime, subprocess, threading, time, socket
import psutil
from PIL import Image, ImageDraw, ImageFont

W, H = 960, 480
import os
_BASE   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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

# ── Paleta NOSTROMO ───────────────────────────────────────────────────────────
BG        = (0,  0,  0)
PHOS      = (0, 180, 40)
PHOS2     = (0, 120, 25)
PHOS_DIM  = (0,  60, 12)
PHOS_TRACK= (0,  20,  5)
GRID      = (0,  35,  8)
INK       = PHOS
INK2      = PHOS2
INK3      = PHOS_DIM
WARN      = (180, 180, 20)
CRIT      = (180, 30, 10)
TRACK     = PHOS_TRACK

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

_upd = {'count': None, 'checking': False, 'ts': 0.0}

def _bg_check_updates():
    try:
        r = subprocess.run(['dnf','check-update','-q','--cacheonly'],
                           capture_output=True, text=True, timeout=15)
        if r.returncode in (0, 100):
            lines = [l for l in r.stdout.strip().splitlines()
                     if l and not l.startswith('Obsoleting') and not l.startswith('Last')]
            _upd['count'] = len(lines)
        else:
            r2 = subprocess.run(['dnf','list','updates','-q'],
                                capture_output=True, text=True, timeout=30)
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

def _tc(t):
    if t is None: return PHOS
    if t < 65:    return PHOS
    if t < 80:    return WARN
    return CRIT

# ── Primitivas ────────────────────────────────────────────────────────────────
def _ctr(d, cx, y, txt, font, col):
    bb = d.textbbox((0,0), txt, font=font)
    d.text((cx-(bb[2]-bb[0])//2, y), txt, font=font, fill=col)

def _right(d, rx, y, txt, font, col):
    bb = d.textbbox((0,0), txt, font=font)
    d.text((rx-(bb[2]-bb[0]), y), txt, font=font, fill=col)

def _hbar_phos(d, x, y, w, h, pct, col):
    d.rectangle([x,y,x+w,y+h], fill=PHOS_TRACK)
    fw = int(pct/100*w)
    if fw > 0:
        d.rectangle([x,y,x+fw,y+h], fill=col)

def _box(d, x, y, w, h):
    """Caja con bordes de línea fósforo."""
    d.line([(x,y),(x+w,y)],       fill=PHOS_DIM, width=1)
    d.line([(x,y+h),(x+w,y+h)],   fill=PHOS_DIM, width=1)
    d.line([(x,y),(x,y+h)],       fill=PHOS_DIM, width=1)
    d.line([(x+w,y),(x+w,y+h)],   fill=PHOS_DIM, width=1)

def _divider(d, x, y, w):
    d.line([(x,y),(x+w,y)], fill=PHOS_DIM, width=1)


# ── Render ────────────────────────────────────────────────────────────────────
def render(frame):
    if frame % 2 == 0:
        _update_net()
        _update_disk_io()

    img = Image.new('RGB', (W, H), BG)
    d   = ImageDraw.Draw(img)

    # Grilla de puntos
    for gx in range(0, W, 18):
        for gy in range(0, H, 18):
            d.point((gx, gy), fill=GRID)

    # Scanlines CRT (filas impares ligeramente más oscuras)
    for gy in range(0, H, 2):
        d.line([(0, gy),(W, gy)], fill=(0,3,0), width=1)

    # Scanlines animadas (desplazamiento hacia abajo)
    SCAN_COL = (0, 20, 0)
    scan_offset = (frame * 3) % 8
    for sy in range(scan_offset, H, 8):
        d.line([(0, sy), (W, sy)], fill=SCAN_COL, width=1)

    # Ruido de fósforo: píxeles brillantes aleatorios que cambian cada frame
    import random as _rnos
    _rnos.seed(frame * 31337)
    for _ in range(80):
        nx = _rnos.randint(0, W-1)
        ny = _rnos.randint(0, H-1)
        brightness = _rnos.randint(10, 40)
        d.point((nx, ny), fill=(0, brightness, 0))

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
    vu, vt = _vram()
    iface, ip = _net_info()

    # ── TOP BAR (54px) ────────────────────────────────────────────────────────
    TB = 54
    ts = now.strftime("%H:%M:%S")
    header = f"WEYLAND-YUTANI  ·  MU/TH/UR 6000  ·  {ts}"
    _ctr(d, W//2, 14, header, Fm(24), PHOS)
    d.line([(0,TB-1),(W,TB-1)], fill=PHOS_DIM, width=1)

    # ── LAYOUT ───────────────────────────────────────────────────────────────
    UY  = TB + 4
    LX  = 8
    LW  = 210
    RX  = W - LW - 8
    RW  = LW
    MX  = LX + LW + 8
    MW  = RX - MX - 8

    # ── PANEL IZQUIERDO — CREW LIFE SIGNS ────────────────────────────────────
    _box(d, LX, UY, LW, H - UY - 4)
    d.text((LX+4, UY+4), "CREW LIFE SIGNS", font=Fm(22), fill=PHOS)
    _divider(d, LX, UY+30, LW)

    py = UY + 36

    # PROC
    d.text((LX+4, py), f"PROC {cpu:5.1f}%", font=Fm(22), fill=PHOS)
    py += 28
    _hbar_phos(d, LX+4, py, LW-8, 14, cpu, PHOS)
    py += 20

    # TEMP
    if ct is not None:
        col_t = _tc(ct)
        d.text((LX+4, py), f"TEMP {ct:.1f}C", font=Fm(22), fill=col_t)
    else:
        d.text((LX+4, py), "TEMP N/A", font=Fm(22), fill=PHOS_DIM)
    py += 30

    # MEMORY
    ram = (mem.total-mem.available)/1024**3
    tot = mem.total/1024**3
    d.text((LX+4, py), f"MEM  {ram:.1f}G/{tot:.0f}G", font=Fm(22), fill=PHOS)
    py += 28
    _hbar_phos(d, LX+4, py, LW-8, 14, mem.percent, PHOS2)
    py += 20
    d.text((LX+4, py), f"     {mem.percent:.0f}%", font=Fm(20), fill=PHOS_DIM)
    py += 28

    # STORAGE
    if disk:
        dg = disk.used/1024**3
        dt = disk.total/1024**3
        d.text((LX+4, py), f"STOR {dg:.0f}G/{dt:.0f}G", font=Fm(22), fill=PHOS)
        py += 28
        _hbar_phos(d, LX+4, py, LW-8, 14, disk.percent, PHOS2)
        py += 20
        d.text((LX+4, py), f"     {disk.percent:.0f}%", font=Fm(20), fill=PHOS_DIM)
        py += 28
    else:
        d.text((LX+4, py), "STOR N/A", font=Fm(22), fill=PHOS_DIM)
        py += 30

    # NET
    tx_v = _ntx[-1]; rx_v = _nrx[-1]
    d.text((LX+4, py), f"NET  UP {_fmt(tx_v)}/s", font=Fm(22), fill=PHOS)
    py += 28
    d.text((LX+4, py), f"     DL {_fmt(rx_v)}/s", font=Fm(20), fill=PHOS_DIM)

    # ── CENTRO — GAUGE RECTANGULAR ───────────────────────────────────────────
    GX  = MX + 10
    GY  = UY + 10
    GW  = MW - 20
    GH  = 200

    # Rectángulo exterior
    d.rectangle([GX, GY, GX+GW, GY+GH], outline=PHOS, width=2)
    # Fondo oscuro dentro
    d.rectangle([GX+3, GY+3, GX+GW-3, GY+GH-3], fill=BG)

    # Número CPU grande centrado
    vs   = f"{cpu:.0f}"
    fsz  = 96
    vf   = Fo(fsz)
    gcx  = MX + MW//2
    bb   = d.textbbox((0,0), vs, font=vf)
    tw2, th = bb[2]-bb[0], bb[3]-bb[1]
    vx   = gcx - tw2//2 - bb[0]
    vy   = GY + GH//2 - th//2 - bb[1] - 10
    # Glow verde suave
    for off in [(1,1),(-1,1),(1,-1),(-1,-1)]:
        d.text((vx+off[0], vy+off[1]), vs, font=vf,
               fill=tuple(c//4 for c in PHOS))
    d.text((vx, vy), vs, font=vf, fill=PHOS)

    # Label debajo del número
    _ctr(d, gcx, GY+GH//2+60, "CPU LOAD", Fr(24), PHOS_DIM)

    # Líneas decorativas scanline dentro del rect
    for sy in range(GY+4, GY+GH-4, 6):
        d.line([(GX+4, sy),(GX+GW-4, sy)], fill=(0,8,2), width=1)

    # Info bajo el gauge rect
    info_y = GY + GH + 10
    freq_str = f"{freq.current/1000:.2f}GHz" if freq else "?.??GHz"
    temp_str = f"{ct:.1f}C" if ct else "?.?C"
    _ctr(d, gcx, info_y, f"TEMP {temp_str}  ·  {freq_str}", Fm(22), PHOS_DIM)

    # Mensaje parpadeante
    blink_msg = "MU/TH/UR: CREW STATUS HYPERSLEEP"
    if (frame % 20) < 14:
        _ctr(d, gcx, info_y + 28, blink_msg, Fm(20), PHOS_DIM)

    # ── PANEL DERECHO — SHIP SYSTEMS ─────────────────────────────────────────
    _box(d, RX, UY, RW, H - UY - 4)
    d.text((RX+4, UY+4), "SHIP SYSTEMS", font=Fm(22), fill=PHOS)
    _divider(d, RX, UY+30, RW)

    py = UY + 36

    # GPU
    if gpu is not None:
        d.text((RX+4, py), f"GPU  {gpu:.1f}%", font=Fm(22), fill=PHOS)
        py += 28
        _hbar_phos(d, RX+4, py, RW-8, 14, gpu, PHOS2)
        py += 20
        if vu is not None:
            d.text((RX+4, py), f"VRAM {vu:.1f}/{vt:.0f}G", font=Fm(20), fill=PHOS_DIM)
        py += 28
    else:
        d.text((RX+4, py), "GPU  N/A", font=Fm(22), fill=PHOS_DIM)
        py += 36

    # DISCO IO
    wr_now = _dwr[-1]; rd_now = _drr[-1]
    d.text((RX+4, py), f"IO   WR {_fmt(wr_now)}", font=Fm(22), fill=PHOS)
    py += 28
    d.text((RX+4, py), f"     RD {_fmt(rd_now)}", font=Fm(20), fill=PHOS_DIM)
    py += 30

    # COOLING
    if fan is not None:
        fc = PHOS if fan < 2500 else WARN if fan < 3500 else CRIT
        d.text((RX+4, py), f"COOL {fan} RPM", font=Fm(22), fill=fc)
    elif ct is not None:
        d.text((RX+4, py), f"COOL {ct:.1f}C", font=Fm(22), fill=_tc(ct))
    else:
        d.text((RX+4, py), "COOL N/A", font=Fm(22), fill=PHOS_DIM)
    py += 30

    # LOAD AVG
    la = os.getloadavg()
    nc2 = psutil.cpu_count() or 4
    lc = PHOS if la[0] < nc2*0.7 else WARN if la[0] < nc2 else CRIT
    d.text((RX+4, py), f"LOAD {la[0]:.2f}", font=Fm(22), fill=lc)
    py += 28
    d.text((RX+4, py), f"     {la[1]:.2f}  {la[2]:.2f}", font=Fm(20), fill=PHOS_DIM)
    py += 30

    # UPTIME
    uptime = now - datetime.datetime.fromtimestamp(psutil.boot_time())
    uh, um = divmod(int(uptime.total_seconds())//60, 60)
    prcs = len(psutil.pids())
    d.text((RX+4, py), f"UP   {uh}h{um:02d}m", font=Fm(22), fill=PHOS)

    return img
