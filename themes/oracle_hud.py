"""
Tema: ORACLE HUD — Doble arc + paneles (phone-ui style)
Display 960x480
"""
import math, datetime, subprocess, random, socket, os, time as _time
import psutil
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 960, 480
_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_FD   = os.path.join(_BASE, "fonts")
_ASS  = os.path.join(_BASE, "assets")

_F_ORB = os.path.join(_FD, "Orbitron-Bold.ttf")
_F_TKO = os.path.join(_FD, "Teko-Medium.ttf")
_F_RAJ = os.path.join(_FD, "Rajdhani-SemiBold.ttf")
_F_DAT = os.path.join(_FD, "NotoSansMono-Bold.ttf")
_F_MON = os.path.join(_FD, "ShareTechMono.ttf")

_FT = {}
def _fnt(p, s):
    k = (p, s)
    if k not in _FT:
        try:    _FT[k] = ImageFont.truetype(p, s)
        except: _FT[k] = ImageFont.load_default()
    return _FT[k]

Fo = lambda s: _fnt(_F_ORB, s)
Ft = lambda s: _fnt(_F_TKO, s)
Fr = lambda s: _fnt(_F_RAJ, s)
Fd = lambda s: _fnt(_F_DAT, s)
Fm = lambda s: _fnt(_F_MON, s)

BG      = (0,   10,  24)
BG2     = (0,   16,  48)
PANEL   = (0,   14,  42)
TEXT    = (224, 240, 255)
TEXT2   = (112, 144, 192)
TEXT3   = (32,  64,  112)
TRACK   = (0,   32,  80)
TRACK2  = (0,   24,  64)
CYAN    = (0,   208, 240)
PURPLE  = (128, 64,  208)
GREEN   = (32,  176, 96)
AMBER   = (208, 144, 16)
RED     = (208, 48,  48)

_BG_IMG = None
def _load_bg():
    global _BG_IMG
    if _BG_IMG is not None: return _BG_IMG if _BG_IMG else None
    for p in ['hud_bg2.png', 'ryzen_bg.jpg']:
        try:
            raw = Image.open(os.path.join(_ASS, p)).convert('RGB')
            _BG_IMG = raw.resize((W, H), Image.LANCZOS)
            return _BG_IMG
        except: pass
    _BG_IMG = False
    return None

def _cores():
    try: return psutil.cpu_percent(percpu=True, interval=None)
    except: return [0.0]*4
def _cpu():
    try: return psutil.cpu_percent(interval=None)
    except: return 0.0
def _mem(): return psutil.virtual_memory()
def _temp():
    try:
        t = psutil.sensors_temperatures()
        for k in ['k10temp','coretemp','cpu_thermal','acpitz']:
            if k in t and t[k]: return t[k][0].current
    except: return None
def _gpu():
    for c in ['card1', 'card0']:
        try:
            r = subprocess.run(['cat', f'/sys/class/drm/{c}/device/gpu_busy_percent'],
                               capture_output=True, text=True, timeout=1)
            if r.returncode == 0: return float(r.stdout.strip())
        except: pass
    return None
def _gtemp():
    try:
        t = psutil.sensors_temperatures()
        for k in ['amdgpu','nvidia','radeon']:
            if k in t and t[k]: return t[k][0].current
    except: return None
def _freq():
    try: return psutil.cpu_freq()
    except: return None

_NET_PREV = {'t': 0., 'sent': 0, 'recv': 0, 'ul': 0., 'dl': 0.}
def _net_rate():
    global _NET_PREV
    try:
        now = _time.time()
        c = psutil.net_io_counters()
        dt = now - _NET_PREV['t']
        if dt > 0.05 and _NET_PREV['t'] > 0:
            _NET_PREV['ul'] = (c.bytes_sent - _NET_PREV['sent']) / dt / 1024
            _NET_PREV['dl'] = (c.bytes_recv - _NET_PREV['recv']) / dt / 1024
        _NET_PREV.update({'t': now, 'sent': c.bytes_sent, 'recv': c.bytes_recv})
        return max(0., _NET_PREV['ul']), max(0., _NET_PREV['dl'])
    except: return 0., 0.

_DIO = {'t': 0., 'w': 0, 'wr': 0., 'active': False}
def _disk_write():
    global _DIO
    try:
        now = _time.time()
        c = psutil.disk_io_counters()
        dt = now - _DIO['t']
        if dt > 0.05 and _DIO['t'] > 0:
            wr = (c.write_bytes - _DIO['w']) / dt
            _DIO['wr'] = wr / 1024
            _DIO['active'] = wr > 10240
        _DIO.update({'t': now, 'w': c.write_bytes})
        return _DIO['active'], _DIO['wr']
    except: return False, 0.

def _fmtnet(k):
    if k < 1: return "0"
    if k < 1024: return f"{k:.0f}K"
    return f"{k/1024:.1f}M"

def _vc(v):
    if v < 70: return GREEN
    if v < 90: return AMBER
    return RED
def _tc(t):
    if t is None: return TEXT2
    if t < 65: return GREEN
    if t < 80: return AMBER
    return RED

def _ctr(d, cx, y, txt, fnt, col):
    bb = d.textbbox((0, 0), txt, font=fnt)
    d.text((cx - (bb[2]-bb[0])//2, y), txt, font=fnt, fill=col)

# ── PHONE-STYLE ARC GAUGE ──────────────────────────────────────
def _arc(img, cx, cy, r, pct, val_txt, label, unit, color, frame=0):
    pct = max(0, min(100, pct))
    S, SPAN = -210, 240
    AW = 18
    d = ImageDraw.Draw(img)

    # Outer subtle ring glow
    gl = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(gl)
    gd.arc([cx-r-10, cy-r-10, cx+r+10, cy+r+10], S, S+SPAN,
           fill=(*color, 8), width=AW+16)
    gd.arc([cx-r-6, cy-r-6, cx+r+6, cy+r+6], S, S+SPAN,
           fill=(*color, 4), width=AW+12)
    gl = gl.filter(ImageFilter.GaussianBlur(radius=4))
    b = img.convert('RGBA')
    b.alpha_composite(gl)
    img = b.convert('RGB')
    d = ImageDraw.Draw(img)

    # Tick marks
    N = 25
    for i in range(N+1):
        a = math.radians(S + SPAN*i/N)
        big = (i % (N//5) == 0)
        r1 = r - (8 if big else 3)
        r2 = r - 1
        col = tuple(max(0, c*3//4) for c in (color if big else TRACK))
        d.line([(cx+r1*math.cos(a), cy+r1*math.sin(a)),
                (cx+r2*math.cos(a), cy+r2*math.sin(a))],
               fill=color if big else TEXT3, width=(2 if big else 1))

    # Track arc
    IR = r - 2
    d.arc([cx-IR, cy-IR, cx+IR, cy+IR], S, S+SPAN, fill=TRACK, width=AW)

    # Fill arc
    arc_pct = int(SPAN * pct / 100)
    if arc_pct > 0:
        d.arc([cx-IR, cy-IR, cx+IR, cy+IR], S, S+arc_pct, fill=color, width=AW)
        tip_a = math.radians(S + arc_pct)
        tx, ty = cx + IR*math.cos(tip_a), cy + IR*math.sin(tip_a)
        g2 = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        gd2 = ImageDraw.Draw(g2)
        gd2.ellipse([tx-10, ty-10, tx+10, ty+10], fill=(*color, 60))
        g2 = g2.filter(ImageFilter.GaussianBlur(radius=4))
        b = img.convert('RGBA')
        b.alpha_composite(g2)
        img = b.convert('RGB')
        d = ImageDraw.Draw(img)
        d.ellipse([tx-4, ty-4, tx+4, ty+4], fill=color)
        d.ellipse([tx-2, ty-2, tx+2, ty+2], fill=TEXT)

    # Inner circle
    NR = r - AW - 4
    d.ellipse([cx-NR, cy-NR, cx+NR, cy+NR], fill=BG2)

    # Value text
    vs = str(val_txt)
    fsz = min(90 if len(vs) < 3 else 70, int(NR * 1.6))
    vf = Ft(fsz)
    bb = d.textbbox((0, 0), vs, font=vf)
    tw, th = bb[2]-bb[0], bb[3]-bb[1]
    vx = cx - tw//2 - bb[0]
    vy = cy - th//2 - bb[1]
    dim = tuple(c//5 for c in color)
    for off in [(2,2), (-2,2), (2,-2), (-2,-2)]:
        d.text((vx+off[0], vy+off[1]), vs, font=vf, fill=dim)
    d.text((vx, vy), vs, font=vf, fill=TEXT)

    # Unit
    if unit:
        d.text((cx+tw//2+4, vy+fsz//2), unit, font=Fr(int(fsz*0.3)), fill=color)

    # Label
    _ctr(d, cx, cy-NR-6, label, Fr(20), color)

    return img

# ── PANEL WITH LEFT ACCENT BAR ─────────────────────────────────
def _panel(img, x, y, w, h, accent, title, draw_fn=None):
    d = ImageDraw.Draw(img)
    d.rectangle([x, y, x+w, y+h], fill=PANEL)
    d.rectangle([x, y, x+3, y+h], fill=accent)
    d.text((x+12, y+8), title, font=Fm(12), fill=TEXT3)
    d.line([(x+12, y+26), (x+w-12, y+26)], fill=(*TRACK, 100), width=1)
    df = d
    if draw_fn:
        draw_fn(d, x+12, y+32)
    return img

def _prow(d, x, y, w, label, value, color, bar_pct=None):
    d.text((x, y+6), label, font=Fr(15), fill=TEXT3)
    bb = d.textbbox((0, 0), value, font=Fd(26))
    d.text((x+w-bb[2]+bb[0], y+6), value, font=Fd(26), fill=color)
    if bar_pct is not None:
        d.rectangle([x, y+24, x+w, y+27], fill=TRACK2)
        fw = int(w * bar_pct)
        if fw > 0:
            d.rectangle([x, y+24, x+fw, y+27], fill=color)

# ── RENDER ──────────────────────────────────────────────────────
def render(frame):
    cores = _cores()
    cpu_v = sum(cores)/len(cores) if cores else 0.0
    mem   = _mem()
    ct    = _temp()
    gt    = _gtemp()
    gpu_v = _gpu() or 0
    freq  = _freq()
    now   = datetime.datetime.now()
    ram_gb = (mem.total - mem.available) / 1024**3
    uptime_s = int(_time.time() - psutil.boot_time())
    uh, um = divmod(uptime_s // 60, 60)
    ul, dl = _net_rate()
    dw_active, dw_kbs = _disk_write()

    img = Image.new('RGB', (W, H), BG)
    bg = _load_bg()
    if bg:
        img.paste(bg, (0, 0))
        ov = Image.new('RGBA', (W, H), (*BG, 160))
        b = img.convert('RGBA')
        b.alpha_composite(ov)
        img = b.convert('RGB')

    # Subtle radial glow
    gl = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(gl)
    for r in range(300, 100, -20):
        a = int(6 * (1 - r/300))
        gd.ellipse([240-r, 160-r, 240+r, 160+r], fill=(*CYAN, a))
    gl = gl.filter(ImageFilter.GaussianBlur(radius=30))
    b = img.convert('RGBA')
    b.alpha_composite(gl)
    img = b.convert('RGB')

    d = ImageDraw.Draw(img)

    # ── TOP BAR ────────────────────────────────────────────────
    d.rectangle([0, 0, W, 36], fill=(0, 16, 48))
    d.line([(0, 36), (W, 36)], fill=(0, 208, 240, 60), width=1)
    d.text((16, 10), "ORACLE", font=Fo(16), fill=CYAN)
    d.text((16, 24), "NEXUS", font=Fm(10), fill=TEXT3)
    cname = socket.gethostname()[:12]
    d.text((W-16, 10), cname, font=Fr(18), fill=TEXT, anchor="ra")
    if ct is not None:
        d.text((W-16, 26), f"{ct:.0f}°", font=Fd(16), fill=_tc(ct), anchor="ra")

    # ── GAUGES ─────────────────────────────────────────────────
    GCY = 155
    img = _arc(img, 240, GCY, 125, cpu_v, f"{cpu_v:.0f}", "CPU", "%", CYAN, frame)
    img = _arc(img, 490, GCY, 88,  gpu_v, f"{gpu_v:.0f}", "GPU", "%", PURPLE, frame)
    img = _arc(img, 665, GCY, 65,  mem.percent, f"{ram_gb:.1f}", "MEM", "G", GREEN, frame)
    d = ImageDraw.Draw(img)

    # ── BOTTOM PANELS ──────────────────────────────────────────
    PY, PH = 275, 155

    def _temp_panel(d, x, y):
        items = [
            (ct if ct is not None else -1, "CPU", ct),
            (gt if gt is not None else -1, "GPU", gt),
            (None, "MEM", None),
        ]
        rows = []
        if ct is not None:
            rows.append((_tc(ct), "CPU", f"{ct:.0f}°", ct/100 if ct else 0))
        else:
            rows.append((TEXT3, "CPU", "--°", 0))
        if gt is not None:
            rows.append((_tc(gt), "GPU", f"{gt:.0f}°", gt/100 if gt else 0))
        else:
            rows.append((TEXT3, "GPU", "--°", 0))
        rows.append((TEXT3, "MEM", "--°", 0))
        for i, (col, lbl, val, bp) in enumerate(rows):
            yy = y + i*36
            d.rectangle([x, yy, x+2, yy+24], fill=col)
            d.text((x+10, yy+4), lbl, font=Fr(15), fill=TEXT3)
            d.text((x+10, yy+24), val, font=Fd(28), fill=col, anchor="rd")
            d.rectangle([x+65, yy+16, x+200, yy+18], fill=TRACK2)
            d.rectangle([x+65, yy+16, x+65+int(135*bp), yy+18], fill=col)

    def _storage_panel(d, x, y):
        mounts = []
        for m in ['/', '/home']:
            try:
                u = psutil.disk_usage(m)
                mounts.append((m, u.percent, _vc(u.percent)))
            except:
                mounts.append((m, 0, TEXT3))
        for i, (m, pct, col) in enumerate(mounts):
            yy = y + i*24
            d.text((x, yy+4), m, font=Fr(15), fill=TEXT3)
            d.text((x+260, yy+4), f"{pct:.0f}%", font=Fd(22), fill=col, anchor="ra")
            d.rectangle([x+60, yy+20, x+260, yy+22], fill=TRACK2)
            fw = int(200 * pct / 100)
            if fw > 0:
                d.rectangle([x+60, yy+20, x+60+fw, yy+22], fill=col)

        d.line([(x, y+55), (x+260, y+55)], fill=(*TRACK, 100), width=1)

        d.text((x, y+60), "UL", font=Fr(15), fill=TEXT3)
        d.text((x+260, y+60), _fmtnet(ul), font=Fd(22), fill=CYAN, anchor="ra")
        d.text((x, y+82), "DL", font=Fr(15), fill=TEXT3)
        d.text((x+260, y+82), _fmtnet(dl), font=Fd(22), fill=CYAN, anchor="ra")

    def _sys_panel(d, x, y):
        d.text((x, y+2), "MEMORY", font=Fm(12), fill=TEXT3)
        d.text((x, y+18), f"{ram_gb:.1f}", font=Ft(36), fill=GREEN)
        d.text((x+58, y+18), "G", font=Fr(18), fill=GREEN)
        d.text((x+260, y+18), f"{mem.percent:.0f}%", font=Fd(24), fill=TEXT, anchor="ra")
        d.rectangle([x, y+42, x+260, y+46], fill=TRACK2)
        fw = int(260 * mem.percent / 100)
        if fw > 0:
            d.rectangle([x, y+42, x+fw, y+46], fill=GREEN)

        d.line([(x, y+56), (x+260, y+56)], fill=(*TRACK, 100), width=1)

        d.text((x, y+62), "UPTIME", font=Fm(12), fill=TEXT3)
        d.text((x+260, y+62), f"{uh:02d}:{um:02d}", font=Fd(26), fill=TEXT, anchor="ra")

        d.text((x+140, y+62), "FREQ", font=Fm(12), fill=TEXT3)
        d.text((x+260, y+82), f"{freq.current/1000:.1f}G" if freq else "--G", font=Fd(26), fill=TEXT, anchor="ra")

        d.line([(x, y+94), (x+260, y+94)], fill=(*TRACK, 100), width=1)

        d.text((x, y+100), "WRITE", font=Fm(12), fill=TEXT3)
        blink = CYAN if (dw_active and (frame % 6) < 4) else TEXT3
        d.ellipse([x, y+114, x+6, y+120], fill=blink, outline=CYAN, width=1)
        if dw_active:
            d.text((x+14, y+108), f"W {_fmtnet(dw_kbs)}/s", font=Fd(20), fill=CYAN)
        else:
            d.text((x+14, y+108), "W  --", font=Fd(20), fill=TEXT3)

    img = _panel(img, 20, PY, 280, PH, GREEN, "TEMPERATURES", _temp_panel)
    img = _panel(img, 318, PY, 290, PH, CYAN, "STORAGE & NET", _storage_panel)
    img = _panel(img, 626, PY, 310, PH, GREEN, "SYSTEM", _sys_panel)

    d = ImageDraw.Draw(img)

    # ── Branding ──────────────────────────────────────────────
    d.text((W//2, H-10), "ORACLE  NEXUS  ·  SYS v2.4", font=Fm(12), fill=TEXT3, anchor="ms")

    return img
