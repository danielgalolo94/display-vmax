"""
Tema: JARVIS HUD — Iron Man Interface (Enhanced)
Display landscape 960x480
Panel de diagnóstico radial con brackets, anillos rotativos,
partículas holográficas y tipografía film-accurate.
"""
import math, datetime, subprocess, random, socket, os
import psutil
from PIL import Image, ImageDraw, ImageFont

W, H = 960, 480
_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_FD   = os.path.join(_BASE, "fonts")

_F_ORB = os.path.join(_FD, "Orbitron-Bold.ttf")
_F_OBK = os.path.join(_FD, "Orbitron-Black.ttf")
_F_TKO = os.path.join(_FD, "Teko-Medium.ttf")
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

Fo = lambda s: _fnt(_F_ORB, s)
Fb = lambda s: _fnt(_F_OBK, s)
Ft = lambda s: _fnt(_F_TKO, s)
Fr = lambda s: _fnt(_F_RAJ, s)
Fd = lambda s: _fnt(_F_DAT, s)
Fm = lambda s: _fnt(_F_MON, s)

# ── Paleta JARVIS ──────────────────────────────────────────────────────────────
BG    = (5,   8,  20)
BG2   = (3,   5,  14)
CY    = (0,   180, 255)
CY2   = (20,  100, 200)
CY3   = (5,   30,  80)
CY4   = (0,   60,  130)
GOLD  = (255, 170, 50)
GOLD2 = (180, 120, 30)
WHITE = (200, 220, 250)
INK   = (180, 210, 240)
INK2  = (100, 140, 190)
INK3  = (40,  70,  120)
DIVL  = (15,  30,  60)
TRACK = (8,   18,  40)
GREEN = (50,  210, 100)
WARN  = (255, 170, 20)
RED   = (255, 60,  60)

# ── Sensores ──────────────────────────────────────────────────────────────────
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

def _fan():
    try:
        f = psutil.sensors_fans()
        for v in f.values():
            if v: return int(v[0].current)
    except: return None

def _vram():
    try:
        u = int(open('/sys/class/drm/card0/device/mem_info_vram_used').read().strip())
        t = int(open('/sys/class/drm/card0/device/mem_info_vram_total').read().strip())
        return u/1024**3, t/1024**3
    except: return None, None

_HN = socket.gethostname()[:12]

_nt  = [0, 0]
_ntx = [0] * 40
_nrx = [0] * 40
_dt  = [0, 0]
_dwr = [0] * 40
_drr = [0] * 40

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

def _fmt(b):
    if b > 1_000_000: return f"{b/1_000_000:.1f}M"
    if b > 1_000:     return f"{b/1_000:.0f}K"
    return f"{int(b)}B"

_RNG = random.Random(42)
_PARTICLES = [(int(_RNG.random()*W), int(_RNG.random()*H),
               _RNG.random()*0.6+0.1, (_RNG.random()-0.5)*0.3,
               int(_RNG.random()*3)+1) for _ in range(120)]

def _vc(v):
    if v < 70: return CY
    if v < 90: return WARN
    return RED

def _tc(t):
    if t is None: return INK2
    if t < 65: return CY
    if t < 80: return WARN
    return RED

# ── Primitivas ────────────────────────────────────────────────────────────────
def _ctr(d, cx, y, txt, font, fill):
    bb = d.textbbox((0,0), txt, font=font)
    d.text((cx-(bb[2]-bb[0])//2, y), txt, font=font, fill=fill)

def _right(d, rx, y, txt, font, fill):
    bb = d.textbbox((0,0), txt, font=font)
    d.text((rx-(bb[2]-bb[0]), y), txt, font=font, fill=fill)

def _glow(d, x, y, txt, size, col, fn=None):
    f = (fn or Ft)(size)
    dim = tuple(c//4 for c in col)
    for dx,dy in [(-2,-2),(2,-2),(-2,2),(2,2)]:
        d.text((x+dx,y+dy), txt, font=f, fill=dim)
    d.text((x,y), txt, font=f, fill=col)

def _hbar(d, x, y, w, h, pct, col):
    d.rectangle([x,y,x+w,y+h], fill=TRACK)
    fw = int(pct/100*w)
    if fw < 1: return
    for i in range(fw):
        t = 0.5 + 0.5*(i/fw)
        d.line([(x+i,y),(x+i,y+h)],
               fill=(min(255,int(col[0]*t)), min(255,int(col[1]*t)), min(255,int(col[2]*t))))
    d.line([(x+fw-1,y),(x+fw-1,y+h)], fill=WHITE, width=2)

def _sparkline(d, x, y, w, h, data, col):
    if not any(data): return
    mx = max(data) or 1
    n  = len(data)
    pts = [(x + int(i*w/(n-1)), y+h - int(v/mx*h)) for i,v in enumerate(data)]
    if len(pts) > 1:
        d.line(pts, fill=col, width=1)

def _corner_bracket(d, x, y, w, h, col, l=14, g=2):
    corners = [
        (x,y,x+l,y),(x,y,x,y+l),
        (x+w-l,y,x+w,y),(x+w,y,x+w,y+l),
        (x,y+h-l,x,y+h),(x,y+h,x+l,y+h),
        (x+w-l,y+h,x+w,y+h),(x+w,y+h-l,x+w,y+h),
    ]
    gcol = tuple(min(255, c//3) for c in col)
    for x1,y1,x2,y2 in corners:
        d.line([(x1,y1),(x2,y2)], fill=gcol, width=g+2)
    for x1,y1,x2,y2 in corners:
        d.line([(x1,y1),(x2,y2)], fill=col, width=g)

def _panel(d, x, y, w, accent, label):
    d.rectangle([x, y, x+3, y+26], fill=accent)
    d.rectangle([x+3, y, x+7, y+26], fill=tuple(c//3 for c in accent))
    d.text((x+12, y+2), label, font=Fr(28), fill=accent)
    d.line([(x+7, y+26), (x+w-1, y+26)], fill=DIVL, width=1)

# ── Gauge ─────────────────────────────────────────────────────────────────────
def _gauge(d, cx, cy, r, cpu, temp, frame):
    S, SPAN = -210, 240
    AW = 20
    IR = r - 12
    TR = IR - AW - 14
    CR = TR - 18
    pulse = 0.7 + 0.3 * math.sin(frame * 0.08)

    a1_s = (frame * 0.4) % 360
    a1_e = (a1_s + 120) % 360
    d.arc([cx-r-8, cy-r-8, cx+r+8, cy+r+8], start=a1_s, end=a1_e, fill=CY3, width=1)

    a2_s = (360 - frame * 0.6) % 360
    a2_e = (a2_s + 180) % 360
    d.arc([cx-r-4, cy-r-4, cx+r+4, cy+r+4], start=a2_s, end=a2_e, fill=CY2, width=2)

    d.arc([cx-r, cy-r, cx+r, cy+r], start=0, end=360, fill=CY3, width=1)

    d.arc([cx-IR, cy-IR, cx+IR, cy+IR], start=S, end=S+SPAN, fill=TRACK, width=AW)

    arc_cpu = int(SPAN * max(cpu, 2) / 100)
    cpu_col = CY if cpu < 90 else RED
    halo = tuple(c//2 for c in cpu_col)

    d.arc([cx-IR-5, cy-IR-5, cx+IR+5, cy+IR+5],
          start=S, end=S+arc_cpu, fill=halo, width=AW+14)
    d.arc([cx-IR-2, cy-IR-2, cx+IR+2, cy+IR+2],
          start=S, end=S+arc_cpu, fill=cpu_col, width=AW+6)
    d.arc([cx-IR, cy-IR, cx+IR, cy+IR],
          start=S, end=S+arc_cpu, fill=cpu_col, width=AW)

    d.arc([cx-IR+AW//2-2, cy-IR+AW//2-2, cx+IR-AW//2+2, cy+IR-AW//2+2],
          start=S, end=S+arc_cpu,
          fill=tuple(min(255, c+40) for c in cpu_col), width=2)

    tip_a = math.radians(S + arc_cpu)
    tx, ty = cx+IR*math.cos(tip_a), cy+IR*math.sin(tip_a)
    d.ellipse([tx-14, ty-14, tx+14, ty+14], fill=halo)
    d.ellipse([tx-8, ty-8, tx+8, ty+8], fill=cpu_col)
    d.ellipse([tx-3, ty-3, tx+3, ty+3], fill=WHITE)

    N = 24
    for i in range(N+1):
        a = math.radians(S + SPAN*i/N)
        big = (i % (N//4) == 0)
        r1 = IR - (12 if big else 5)
        r2 = IR + 2
        x1,y1 = cx+r1*math.cos(a), cy+r1*math.sin(a)
        x2,y2 = cx+r2*math.cos(a), cy+r2*math.sin(a)
        d.line([(x1,y1),(x2,y2)], fill=INK if big else INK3, width=(2 if big else 1))
        if big and 0 < i < N:
            pv = int(100*i/N)
            nf = Fm(16)
            nb = d.textbbox((0,0), str(pv), font=nf)
            nx = cx+(IR+20)*math.cos(a)-(nb[2]-nb[0])//2
            ny = cy+(IR+20)*math.sin(a)-(nb[3]-nb[1])//2
            d.text((nx,ny), str(pv), font=nf, fill=INK3)

    d.arc([cx-TR, cy-TR, cx+TR, cy+TR], start=S, end=S+SPAN, fill=TRACK, width=10)
    if temp is not None:
        arc_t = int(SPAN * min(temp, 100) / 100)
        tcol = GOLD if temp < 80 else RED
        gcol = tuple(c//2 for c in tcol)
        d.arc([cx-TR-3, cy-TR-3, cx+TR+3, cy+TR+3],
              start=S, end=S+arc_t, fill=gcol, width=16)
        d.arc([cx-TR, cy-TR, cx+TR, cy+TR],
              start=S, end=S+arc_t, fill=tcol, width=10)
        tt_a = math.radians(S + arc_t)
        ttx, tty = cx+TR*math.cos(tt_a), cy+TR*math.sin(tt_a)
        d.ellipse([ttx-6, tty-6, ttx+6, tty+6], fill=tcol)

    d.ellipse([cx-CR, cy-CR, cx+CR, cy+CR], fill=BG)
    d.ellipse([cx-CR, cy-CR, cx+CR, cy+CR], fill=None, outline=INK3, width=1)

    vs = f"{cpu:.0f}"
    vf = Fo(86)
    bb = d.textbbox((0,0), vs, font=vf)
    tw, th = bb[2]-bb[0], bb[3]-bb[1]
    vx = cx - tw//2 - bb[0]
    vy = cy - th//2 - bb[1] - 6
    dim = tuple(c//5 for c in cpu_col)
    for off in [(2,2),(-2,2),(2,-2),(-2,-2)]:
        d.text((vx+off[0], vy+off[1]), vs, font=vf, fill=dim)
    d.text((vx, vy), vs, font=vf, fill=WHITE)
    _ctr(d, cx, vy+th+4, "%", Fr(28), cpu_col)
    _ctr(d, cx, cy+CR+12, "CPU LOAD", Fr(26), CY)

    if temp is not None:
        _ctr(d, cx, cy+CR+40, f"{temp:.0f}°C", Fd(28), _tc(temp))

    for angle in range(S, S+SPAN+1, SPAN//4):
        if angle == S+SPAN//2: continue
        a = math.radians(angle)
        sr = CR + 12
        for r2 in range(sr, IR-4, 8):
            px = cx + r2*math.cos(a)
            py = cy + r2*math.sin(a)
            d.point((int(px), int(py)), fill=CY3)

# ── Panel sections ────────────────────────────────────────────────────────────
def _draw_left(d, x, w, py, cpu, freq, ct, mem, la, frame):
    _panel(d, x, py, w, CY, "CPU STATUS")
    _glow(d, x+12, py+32, f"{cpu:.0f}", 80, _vc(cpu), Ft)
    if ct is not None:
        _right(d, x+w-12, py+36, f"{ct:.0f}°C", Fd(28), _tc(ct))
    if freq:
        d.text((x+12, py+114), f"{freq.current/1000:.3f}", font=Fo(32), fill=CY)
        d.text((x+12+138, py+122), "GHz", font=Fr(22), fill=INK2)
    _hbar(d, x+12, py+148, w-24, 14, cpu, _vc(cpu))
    py += 172

    _panel(d, x, py, w, GREEN, "MEMORY")
    ram = (mem.total-mem.available)/1024**3
    tot = mem.total/1024**3
    _glow(d, x+12, py+30, f"{ram:.1f}", 62, _vc(mem.percent), Ft)
    _right(d, x+w-12, py+46, f"/{tot:.0f}G", Fr(30), INK2)
    _hbar(d, x+12, py+104, w-24, 14, mem.percent, GREEN)
    py += 126

    _panel(d, x, py, w, INK2, "NETWORK")
    tx_v = _ntx[-1] if _ntx else 0
    rx_v = _nrx[-1] if _nrx else 0
    d.text((x+12, py+30), f"UP {_fmt(tx_v)}/s", font=Fd(24), fill=CY)
    d.text((x+12, py+62), f"DL {_fmt(rx_v)}/s", font=Fd(24), fill=INK2)
    _sparkline(d, x+12, py+88, w-24, 28, _ntx[-20:] if len(_ntx)>=20 else _ntx, CY)
    py += 126
    return py

def _draw_right(d, x, w, py, gpu, gpu_nm, gt, vu, vt, disk, dm, la, fan, frame):
    _panel(d, x, py, w, CY, "GRAPHICS")
    if gpu is not None:
        _glow(d, x+12, py+32, f"{gpu:.0f}", 80, _vc(gpu), Ft)
        if gt is not None:
            _right(d, x+w-12, py+36, f"{gt:.0f}°C", Fd(28), _tc(gt))
        _hbar(d, x+12, py+148, w-24, 14, gpu, _vc(gpu))
        if vu is not None:
            d.text((x+12, py+118), f"VRAM {vu:.1f}/{vt:.0f}G", font=Fd(22), fill=INK2)
    else:
        _glow(d, x+12, py+40, "--", 80, INK3, Ft)
    py += 172

    _panel(d, x, py, w, GOLD, "STORAGE")
    if disk:
        d.text((x+12, py+30), f"{disk.percent:.0f}%", font=Ft(62), fill=_vc(disk.percent))
        dg = disk.used/1024**3
        dt = disk.total/1024**3
        d.text((x+12, py+96), f"{dg:.0f}/{dt:.0f}G", font=Fd(24), fill=INK2)
        _hbar(d, x+12, py+122, w-24, 12, disk.percent, GOLD)
    py += 148

    _panel(d, x, py, w, WHITE, "SYSTEM")
    nc = psutil.cpu_count() or 4
    lc = GREEN if la[0] < nc*0.7 else WARN if la[0] < nc else RED
    d.text((x+12, py+30), f"{la[0]:.2f}", font=Fo(38), fill=lc)
    d.text((x+12, py+72), f"load {la[1]:.1f} {la[2]:.1f}", font=Fd(22), fill=INK2)
    d.text((x+12, py+98), f"{len(psutil.pids())} procs", font=Fd(22), fill=INK2)
    if fan is not None:
        fc = CY if fan < 2500 else WARN
        _right(d, x+w-12, py+36, f"{fan}RPM", Fm(22), fc)
    py += 126
    return py

# ── Render ────────────────────────────────────────────────────────────────────
def render(frame):
    if frame % 2 == 0:
        _update_net()
        _update_disk_io()

    cores = _cores()
    cpu   = sum(cores)/len(cores) if cores else 0.0
    mem   = _mem()
    ct    = _temp()
    gpu   = _gpu()
    gt    = _gtemp()
    disk, dm = _disk()
    freq  = _freq()
    fan   = _fan()
    vu, vt = _vram()
    now   = datetime.datetime.now()
    la    = os.getloadavg()
    ram   = (mem.total-mem.available)/1024**3
    tot   = mem.total/1024**3
    uptime = now - datetime.datetime.fromtimestamp(psutil.boot_time())
    uh, um = divmod(int(uptime.total_seconds())//60, 60)

    img = Image.new('RGB', (W, H), BG2)
    d   = ImageDraw.Draw(img)

    # ── Grid ───────────────────────────────────────────────────────────────────
    for x in range(0, W, 20):
        for y in range(0, H, 20):
            d.point((x, y), fill=(10, 16, 30))

    # ── Partículas ─────────────────────────────────────────────────────────────
    for px, py, vx, vy, sz in _PARTICLES:
        x = int(px + frame * vx) % W
        y = int(py + frame * vy) % H
        alpha = 40 + sz * 30
        col = (0, alpha, min(255, alpha + 80))
        d.ellipse([x-sz, y-sz, x+sz, y+sz], fill=col)

    # ── TOP BAR ────────────────────────────────────────────────────────────────
    TB = 54
    d.rectangle([0, 0, W, TB], fill=(3, 5, 13))
    d.line([(0, TB-2), (W, TB-2)], fill=CY4, width=1)
    d.line([(0, TB-1), (W, TB-1)], fill=CY, width=1)

    blink_on = (frame % 10) < 6
    blink_col = CY if blink_on else CY3
    d.ellipse([14, TB//2-10, 28, TB//2+4], fill=blink_col)
    d.text((34, TB//2-16), "J.A.R.V.I.S.", font=Fo(26), fill=GOLD)
    d.text((34, TB//2+12), "SYSTEM ONLINE", font=Fm(18), fill=CY if blink_on else INK3)

    _ctr(d, W//2, TB//2-14, now.strftime("%H:%M:%S"), Fb(50), WHITE)
    _ctr(d, W//2, TB//2+14, now.strftime("%a %d %b %Y"), Fr(22), INK2)

    # ── Gauge ──────────────────────────────────────────────────────────────────
    GCX = W // 2
    GCY = TB + (H - TB - 22) // 2
    GR  = 175
    _gauge(d, GCX, GCY, GR, cpu, ct, frame)

    # ── LEFTPANEL ──────────────────────────────────────────────────────────────
    LX, LW = 10, 178
    py = TB + 6
    py = _draw_left(d, LX, LW, py, cpu, freq, ct, mem, la, frame)

    # ── RIGHTPANEL ─────────────────────────────────────────────────────────────
    RX, RW = W - 10 - 178, 178
    py = TB + 6
    py = _draw_right(d, RX, RW, py, gpu, dm, gt, vu, vt, disk, dm, la, fan, frame)

    # ── BOTTOM BAR ─────────────────────────────────────────────────────────────
    BB = H - 28
    d.rectangle([0, BB, W, H], fill=(3, 5, 13))
    d.line([(0, BB), (W, BB)], fill=CY4, width=1)
    d.line([(0, BB+1), (W, BB+1)], fill=(2, 4, 12), width=1)

    bblink = GREEN if (frame % 12) < 8 else DIVL
    d.ellipse([8, BB+6, 18, BB+18], fill=bblink)
    d.text((24, BB+2), "ACTIVE", font=Fm(18), fill=INK if bblink == GREEN else INK3)

    sx = 86
    for label, val in [("CPU", ct), ("LOAD", la[0]), ("UP", f"{uh}h{um:02d}m"), ("MEM", mem.percent)]:
        txt = f"{label} {val:.0f}" if isinstance(val, (int, float)) else f"{label} {val}"
        d.text((sx, BB+2), txt, font=Fm(16), fill=INK2)
        sx += d.textbbox((0,0), txt, font=Fm(16))[2] - d.textbbox((0,0), txt, font=Fm(16))[0] + 24

    _right(d, W-10, BB+2, "STARK INDUSTRIES", Fm(16), INK3)

    # ── Scan line ──────────────────────────────────────────────────────────────
    sweep_y = (frame * 3) % H
    sw_a = int(14 + 8 * math.sin(frame * 0.1))
    d.line([(0, sweep_y), (W, sweep_y)], fill=(CY2[0], CY2[1], CY2[2], sw_a), width=1)

    for yy in range(0, H, 5):
        a = 2 + int(2 * math.sin((yy + frame * 2) * 0.05))
        d.line([(0, yy+a), (W, yy+a)], fill=(0, 0, 0, a), width=1)

    # ── Corner brackets ────────────────────────────────────────────────────────
    _corner_bracket(d, 6, 6, 12, 12, CY, 8, 1)
    _corner_bracket(d, W-18, 6, 12, 12, CY, 8, 1)
    _corner_bracket(d, 6, H-18, 12, 12, CY, 8, 1)
    _corner_bracket(d, W-18, H-18, 12, 12, CY, 8, 1)

    return img
