"""
Tema: EMPIRE — Dark Side Imperial Command
Darth Vader bajo la lluvia, noche oscura
Display landscape 960x480
"""
import math, random, datetime, time, urllib.request, io, subprocess
import psutil
from PIL import Image, ImageDraw, ImageFont

W, H   = 960, 480
import os
_BASE  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_FD    = os.path.join(_BASE, "fonts")
SPLIT  = 520

# fuentes: Teko (imperial/épico) + ShareTechMono (datos) + Orbitron (nums)
_F_MAIN = os.path.join(_FD, "Teko-Medium.ttf")
_F_MONO = os.path.join(_FD, "ShareTechMono.ttf")
_F_BIG  = os.path.join(_FD, "Orbitron-Bold.ttf")
_F_RAJ  = os.path.join(_FD, "Rajdhani-SemiBold.ttf")
_F_NMB  = os.path.join(_FD, "NotoSansMono-Bold.ttf")

def fnt(size):
    try:    return ImageFont.truetype(_F_MAIN, size)
    except: return ImageFont.load_default()

def fnt_mono(size):
    try:    return ImageFont.truetype(_F_MONO, size)
    except: return fnt(size)

def fnt_big(size):
    try:    return ImageFont.truetype(_F_BIG, size)
    except: return fnt(size)

def fnt_raj(size):
    try:    return ImageFont.truetype(_F_RAJ, size)
    except: return fnt(size)

def fnt_nmb(size):
    try:    return ImageFont.truetype(_F_NMB, size)
    except: return fnt_big(size)

# ── Paleta Imperial ───────────────────────────────────────────────────────────
BG     = (4,   3,   8)
RED    = (210,  12,  12)
DRED   = (80,   0,   0)
BRED   = (255,  60,  60)
ORANGE = (255, 130,   0)
STEEL  = (148, 148, 162)
DSTEEL = (58,  58,  72)
PANEL  = (6,   4,  12)

# ── GIF: Darth Vader ─────────────────────────────────────────────────────────
_gif_frames = []
_gif_done   = False

GIF_URLS = [
    "https://media.giphy.com/media/dYQK1pswWvwA3ayLEh/giphy.gif",
    "https://media.giphy.com/media/l1KuhBCqxOoJyr0m4/giphy.gif",
    "https://media.giphy.com/media/4YQQuTvNiLJSPP3gdS/giphy.gif",
    "https://media.giphy.com/media/3o7abBYVSmAEgBOUyA/giphy.gif",
    "https://media.giphy.com/media/LqU7iJHZZ5OAVLYjXj/giphy.gif",
    "https://media.giphy.com/media/xUA7aSfMIosbMgpSKc/giphy.gif",
]

def _load_gif():
    global _gif_frames, _gif_done
    if _gif_done: return
    _gif_done = True
    for url in GIF_URLS:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as r:
                data = r.read()
            gif = Image.open(io.BytesIO(data))
            for i in range(getattr(gif, 'n_frames', 1)):
                gif.seek(i)
                _gif_frames.append(
                    gif.convert('RGB').resize((SPLIT, H), Image.Resampling.LANCZOS).copy()
                )
            if _gif_frames:
                print(f"[empire] {len(_gif_frames)} frames de {url}")
                return
        except Exception as e:
            print(f"[empire] {url}: {e}")

# ── Lluvia ────────────────────────────────────────────────────────────────────
_drops = []
def _init_rain():
    global _drops
    _drops = []
    for _ in range(220):
        _drops.append([
            random.uniform(0, SPLIT),
            random.uniform(0, H),
            random.uniform(14, 32),
            random.randint(10, 26),
        ])
_init_rain()

def _update_rain():
    for dr in _drops:
        dr[1] += dr[2]
        dr[0] -= dr[2] * 0.16
        if dr[1] > H + dr[3]:
            dr[0] = random.uniform(0, SPLIT + 40)
            dr[1] = random.uniform(-50, -5)
            dr[2] = random.uniform(14, 32)
            dr[3] = random.randint(10, 26)

def _draw_rain(d):
    for dr in _drops:
        x, y, spd, lng = dr
        bri = random.randint(35, 100)
        d.line([(x - lng*0.16, y - lng), (x, y)],
               fill=(bri, bri + 18, bri + 28), width=1)

# ── NET delta tracking ────────────────────────────────────────────────────────
_nt    = [0, 0]   # [bytes_sent, bytes_recv] previous snapshot
_nt_up = 0        # KB/s upload
_nt_dn = 0        # KB/s download
_nt_last = 0.0    # timestamp of last update

def _update_net():
    global _nt, _nt_up, _nt_dn, _nt_last
    now = time.monotonic()
    try:
        nc = psutil.net_io_counters()
        dt = now - _nt_last if _nt_last > 0 else 1.0
        if dt > 0 and _nt_last > 0:
            _nt_up = max(0, (nc.bytes_sent - _nt[0]) / dt / 1024)
            _nt_dn = max(0, (nc.bytes_recv - _nt[1]) / dt / 1024)
        _nt[0] = nc.bytes_sent
        _nt[1] = nc.bytes_recv
    except:
        pass
    _nt_last = now

# ── Sistema ───────────────────────────────────────────────────────────────────
def _cpu():  return psutil.cpu_percent(interval=None)
def _mem():  return psutil.virtual_memory()
def _temp():
    try:
        t = psutil.sensors_temperatures()
        for k in ['k10temp', 'coretemp', 'cpu_thermal', 'acpitz']:
            if k in t: return t[k][0].current
    except: pass
    return None

def _gpu():
    try:
        r = subprocess.run(['cat', '/sys/class/drm/card1/device/gpu_busy_percent'],
                           capture_output=True, text=True, timeout=1)
        if r.returncode == 0: return int(r.stdout.strip())
    except: pass
    return None

def _gtemp():
    try:
        t = psutil.sensors_temperatures()
        for k in ['amdgpu', 'nvidia', 'radeon']:
            if k in t: return t[k][0].current
    except: pass
    return None

def _disk():
    try:    return psutil.disk_usage('/home')
    except: return psutil.disk_usage('/')

def _uptime_str():
    try:
        secs = int(time.time() - psutil.boot_time())
        h, rem = divmod(secs, 3600)
        m = rem // 60
        return f"{h}h {m:02d}m"
    except:
        return "--"

def _proc_count():
    try:    return len(psutil.pids())
    except: return 0

def _val_col(v):
    if v < 70: return RED
    if v < 90: return ORANGE
    return BRED

def _temp_col(t):
    if t is None: return DRED
    if t < 65:   return RED
    if t < 80:   return ORANGE
    return BRED

def _bar(d, x, y, w, h, pct, col):
    segs = 22
    sw   = max(1, (w - segs) // segs)
    for i in range(segs):
        sx = x + i * (sw + 1)
        c  = col if (i / segs) * 100 < pct else (18, 6, 8)
        d.rectangle([sx, y, sx + sw, y + h], fill=c)

def _glow(d, x, y, text, size, col, dim, font_fn=None):
    f = (font_fn or fnt)(size)
    for dx, dy in [(-2,-1),(2,-1),(-2,1),(2,1),(0,-2),(0,2)]:
        d.text((x+dx, y+dy), text, font=f, fill=dim)
    d.text((x, y), text, font=f, fill=col)

def _imperial_emblem(d, cx, cy, pulse):
    rings = [(34, DRED), (22, (35, 0, 0)), (10, RED)]
    for r, col in rings:
        br = int(col[0] * (0.5 + pulse * 0.5))
        d.ellipse([cx-r, cy-r, cx+r, cy+r], outline=(br, col[1], col[2]), width=2)
    d.ellipse([cx-3, cy-3, cx+3, cy+3], fill=RED)
    for ang in range(0, 360, 60):
        rad = math.radians(ang)
        d.line([
            (cx + int(10*math.cos(rad)), cy + int(10*math.sin(rad))),
            (cx + int(28*math.cos(rad)), cy + int(28*math.sin(rad)))
        ], fill=DRED, width=1)

def _fmt_net(kbps):
    if kbps >= 1024:
        return f"{kbps/1024:.1f}M/s"
    return f"{kbps:.0f}K/s"

# ── Render ────────────────────────────────────────────────────────────────────
def render(frame):
    _update_rain()
    _load_gif()
    if frame % 2 == 0:
        _update_net()

    img = Image.new('RGB', (W, H), BG)
    d   = ImageDraw.Draw(img)

    # ── Panel izquierdo: Vader ────────────────────────────────────────────────
    if _gif_frames:
        img.paste(_gif_frames[frame % len(_gif_frames)], (0, 0))
        dark    = Image.new('RGB', (SPLIT, H), BG)
        blended = Image.blend(img.crop((0, 0, SPLIT, H)), dark, alpha=0.38)
        img.paste(blended, (0, 0))
    else:
        for y in range(H):
            v = max(4, int(18 * math.sin(math.pi * y / H)))
            d.line([(0, y), (SPLIT, y)], fill=(v, 0, 0))

    d = ImageDraw.Draw(img)
    _draw_rain(d)

    # Vignette lateral derecha del panel (transición suave)
    for x in range(SPLIT - 60, SPLIT):
        alpha = (x - (SPLIT - 60)) / 60
        for y in range(H):
            px_col = img.getpixel((x, y))
            blended_px = tuple(int(c * (1-alpha) + bg * alpha)
                               for c, bg in zip(px_col, PANEL))
            img.putpixel((x, y), blended_px)

    d = ImageDraw.Draw(img)

    # Emblema Imperial - arriba izquierda
    pulse = abs(math.sin(frame * 0.10))
    _imperial_emblem(d, 44, 44, pulse)

    # Títulos - abajo izquierda
    now = datetime.datetime.now()
    d.text((14, H - 114), "GALACTIC", font=fnt(40), fill=DRED)
    _glow(d, 14, H - 74, "EMPIRE", 72, RED, DRED)
    d.text((14, H - 14), now.strftime("%H:%M   %d / %m / %Y"), font=fnt(16), fill=DSTEEL)

    # Scanlines sutiles
    for y in range(0, H, 5):
        d.line([(0, y), (SPLIT, y)], fill=(0, 0, 0, 25))

    # ── Separador pulsante ────────────────────────────────────────────────────
    sep_r = int(60 + pulse * 160)
    d.line([(SPLIT,   0), (SPLIT,   H)], fill=(sep_r, 0, 0), width=3)
    d.line([(SPLIT+5, 0), (SPLIT+5, H)], fill=DRED,          width=1)

    # ── Panel derecho: stats ──────────────────────────────────────────────────
    d.rectangle([SPLIT + 7, 0, W - 1, H - 1], fill=PANEL)

    cpu  = _cpu()
    mem  = _mem()
    ct   = _temp()
    gpu  = _gpu()
    gt   = _gtemp()
    disk = _disk()

    px   = SPLIT + 14
    pw   = W - px - 10     # ~416px
    py   = 8

    # ── Header ────────────────────────────────────────────────────────────────
    d.text((px, py), "IMPERIAL COMMAND", font=fnt(30), fill=DRED)
    if frame % 10 < 7:
        d.ellipse([W - 24, py + 5, W - 8, py + 21], fill=RED)
    py += 36
    d.line([(px, py), (W - 10, py)], fill=DRED, width=1)
    py += 8

    # ── CPU block (~105px) ────────────────────────────────────────────────────
    cc = _val_col(cpu)
    ct_str = f"{ct:.0f}C" if ct is not None else "--C"
    ct_col = _temp_col(ct)
    # Label row: PROCESSOR  CPU      45C
    d.text((px, py), "PROCESSOR", font=fnt(22), fill=DSTEEL)
    d.text((px + 116, py + 2), "CPU", font=fnt_raj(18), fill=STEEL)
    _glow(d, px + pw - 56, py, ct_str, 22, ct_col, DRED, fnt_big)
    py += 26
    # Value: big number + bar
    _glow(d, px, py, f"{cpu:.0f}%", 52, cc, DRED, fnt_big)
    _bar(d, px + 110, py + 8, pw - 114, 10, cpu, cc)
    py += 36
    d.line([(px, py), (px + pw, py)], fill=DRED, width=1)
    py += 6

    # ── GPU block (~68px) ─────────────────────────────────────────────────────
    gpu_val  = gpu if gpu is not None else 0
    gpu_str  = f"{gpu_val:.0f}%" if gpu is not None else "--"
    gc       = _val_col(gpu_val) if gpu is not None else DSTEEL
    gt_str   = f"{gt:.0f}C" if gt is not None else "--C"
    gt_col   = _temp_col(gt)
    d.text((px, py), "GRAPHICS", font=fnt(22), fill=DSTEEL)
    d.text((px + 104, py + 2), "GPU", font=fnt_raj(18), fill=STEEL)
    _glow(d, px + pw - 56, py, gt_str, 22, gt_col, DRED, fnt_big)
    py += 26
    _glow(d, px, py, gpu_str, 52, gc, DRED, fnt_big)
    _bar(d, px + 110, py + 8, pw - 114, 10, gpu_val, gc)
    py += 36
    d.line([(px, py), (px + pw, py)], fill=DRED, width=1)
    py += 6

    # ── RAM block (~62px) ─────────────────────────────────────────────────────
    ram_gb = (mem.total - mem.available) / 1024**3
    tot_gb = mem.total / 1024**3
    rc     = _val_col(mem.percent)
    d.text((px, py), "MEMORY", font=fnt(22), fill=DSTEEL)
    d.text((px + 90, py + 2), "RAM", font=fnt_raj(18), fill=STEEL)
    d.text((px + pw - 46, py + 2), f"{mem.percent:.0f}%", font=fnt_raj(18), fill=rc)
    py += 26
    _glow(d, px, py, f"{ram_gb:.1f}G", 36, rc, DRED, fnt_big)
    d.text((px + 86, py + 6), f"/ {tot_gb:.0f}G", font=fnt_raj(22), fill=DSTEEL)
    _bar(d, px + 180, py + 6, pw - 184, 10, mem.percent, rc)
    py += 30
    d.line([(px, py), (px + pw, py)], fill=DRED, width=1)
    py += 6

    # ── DISK block (~56px) ───────────────────────────────────────────────────
    du_gb  = disk.used  / 1024**3
    dt_gb  = disk.total / 1024**3
    dp     = disk.percent
    dc     = _val_col(dp)
    d.text((px, py), "STORAGE", font=fnt(22), fill=DSTEEL)
    d.text((px + 96, py + 2), "/home", font=fnt_raj(18), fill=STEEL)
    d.text((px + pw - 46, py + 2), f"{dp:.0f}%", font=fnt_raj(18), fill=dc)
    py += 26
    _glow(d, px, py, f"{du_gb:.0f}G", 36, dc, DRED, fnt_big)
    d.text((px + 86, py + 6), f"/ {dt_gb:.0f}G", font=fnt_raj(22), fill=DSTEEL)
    _bar(d, px + 180, py + 6, pw - 184, 10, dp, dc)
    py += 30
    d.line([(px, py), (px + pw, py)], fill=DRED, width=1)
    py += 6

    # ── NETWORK section (~38px) ───────────────────────────────────────────────
    d.text((px, py), "NETWORK", font=fnt(22), fill=DSTEEL)
    net_str = f"UP {_fmt_net(_nt_up)}   DL {_fmt_net(_nt_dn)}"
    d.text((px + 96, py + 4), net_str, font=fnt_mono(14), fill=STEEL)
    py += 28
    d.line([(px, py), (px + pw, py)], fill=DRED, width=1)
    py += 6

    # ── UPTIME section (~38px) ────────────────────────────────────────────────
    procs  = _proc_count()
    up_str = _uptime_str()
    d.text((px, py), "UPTIME", font=fnt(22), fill=DSTEEL)
    d.text((px + 84, py + 4), up_str, font=fnt_mono(14), fill=STEEL)
    d.text((px + 84 + 80, py + 4), f"  {procs} PROC", font=fnt_mono(14), fill=DSTEEL)
    py += 28
    d.line([(px, py), (px + pw, py)], fill=DRED, width=1)
    py += 6

    # ── Clock + CPU temp bar section (~56px) ──────────────────────────────────
    time_str = now.strftime("%H:%M")
    date_str = now.strftime("%a %d/%m")
    _glow(d, px, py, time_str, 42, RED, DRED, fnt_big)
    d.text((px, py + 46), date_str, font=fnt_raj(16), fill=DSTEEL)
    # CPU temp readout + mini bar on the right
    temp_label_x = px + 160
    d.text((temp_label_x, py), "CPU TEMP", font=fnt_raj(14), fill=DSTEEL)
    if ct is not None:
        _glow(d, temp_label_x, py + 16, ct_str, 28, ct_col, DRED, fnt_big)
        _bar(d, temp_label_x, py + 46, pw - 164, 8, min(ct, 100), ct_col)
    else:
        d.text((temp_label_x, py + 16), "--C", font=fnt_big(28), fill=DSTEEL)
    py += 58

    # ── Footer parpadeante ────────────────────────────────────────────────────
    if frame % 20 < 14:
        d.text((px, H - 18), "> DARK SIDE ONLINE_", font=fnt(14), fill=DRED)

    return img
