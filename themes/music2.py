"""
Tema: MUSIC VISUALIZER 2 — retro synthwave / neon
Fondo negro-violeta, barras segmentadas azul→cyan→magenta, peak dots.
Display landscape 960x480
"""
import subprocess, threading, math, datetime, shutil, time
import numpy as np
import psutil
from PIL import Image, ImageDraw, ImageFont

W, H = 960, 480
import os
_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT  = os.path.join(_BASE, "fonts", "Teko-Medium.ttf")

def fnt(size):
    try:    return ImageFont.truetype(FONT, size)
    except: return ImageFont.load_default()

# ── Layout ───────────────────────────────────────────────────────────────────
TOP_H    = 72
BOT_H    = 88
BASELINE = H - BOT_H
MAX_BAR  = BASELINE - TOP_H  # 320px

# ── Segmentos LED ─────────────────────────────────────────────────────────────
SEG_H   = 7
SEG_GAP = 2
STEP    = SEG_H + SEG_GAP
N_SEGS  = MAX_BAR // STEP

# ── Config audio ──────────────────────────────────────────────────────────────
N_BARS      = 32
SAMPLE_RATE = 48000
FFT_SIZE    = 4096
CHANNELS    = 2
BYTES_FRAME = 2 * CHANNELS

# ── Estado compartido ─────────────────────────────────────────────────────────
_lock     = threading.Lock()
_bars     = np.zeros(N_BARS)
_vu_l     = 0.0
_vu_r     = 0.0
_pk_l     = 0.0
_pk_r     = 0.0
_ok       = False
_src      = ""
_peaks    = np.zeros(N_BARS)
_band_max = np.full(N_BARS, 0.04)

def _find_active_monitor():
    try:
        si = subprocess.run(['pactl','list','sink-inputs','short'],
                            capture_output=True, text=True, timeout=2).stdout
        active_sink_ids = set()
        for line in si.splitlines():
            parts = line.split()
            if len(parts) >= 2:
                active_sink_ids.add(parts[1])
        if active_sink_ids:
            sinks = subprocess.run(['pactl','list','sinks','short'],
                                   capture_output=True, text=True, timeout=2).stdout
            for line in sinks.splitlines():
                parts = line.split()
                if len(parts) >= 2 and parts[0] in active_sink_ids:
                    return parts[1] + '.monitor'
        sources = subprocess.run(['pactl','list','sources','short'],
                                 capture_output=True, text=True, timeout=2).stdout
        for line in sources.splitlines():
            if 'monitor' in line and 'RUNNING' in line:
                return line.split()[1]
        for line in sources.splitlines():
            if 'monitor' in line:
                return line.split()[1]
    except Exception as e:
        print(f"[music2] pactl: {e}")
    return None

def _audio_thread():
    global _bars, _vu_l, _vu_r, _pk_l, _pk_r, _ok, _src

    smooth  = np.zeros(N_BARS)
    proc    = None
    cur_mon = None

    while True:
        mon = _find_active_monitor()
        if mon != cur_mon:
            if proc:
                try: proc.terminate()
                except: pass
                proc = None
            cur_mon = mon
            _src = mon or ""

        if not mon:
            _ok = False
            time.sleep(3)
            continue

        if proc is None or proc.poll() is not None:
            try:
                proc = subprocess.Popen(
                    ['parec',
                     f'--device={mon}',
                     '--format=s16le',
                     f'--rate={SAMPLE_RATE}',
                     '--channels=2',
                     '--latency-msec=40'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL
                )
                _ok = True
                smooth[:] = 0
            except Exception as e:
                print(f"[music2] parec: {e}")
                _ok = False
                time.sleep(3)
                continue

        needed = FFT_SIZE * BYTES_FRAME
        try:
            raw = proc.stdout.read(needed)
        except Exception:
            raw = b''

        if len(raw) < needed:
            proc = None
            time.sleep(0.1)
            continue

        data   = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        stereo = data.reshape(-1, 2)
        L      = stereo[:, 0]
        R      = stereo[:, 1]

        rl = float(np.sqrt(np.mean(L**2)))
        rr = float(np.sqrt(np.mean(R**2)))

        mono = (L + R) * 0.5
        win  = mono * np.hanning(len(mono))
        fft  = np.abs(np.fft.rfft(win, n=FFT_SIZE))
        fft  = 20 * np.log10(np.maximum(fft, 1e-9))
        fft  = np.clip((fft + 90) / 90, 0, 1)
        fft  = fft ** 6.0

        freqs = np.fft.rfftfreq(FFT_SIZE, 1.0 / SAMPLE_RATE)
        bins  = np.logspace(np.log10(20), np.log10(20000), N_BARS + 1)
        b     = np.zeros(N_BARS)
        for i in range(N_BARS):
            mask = (freqs >= bins[i]) & (freqs < bins[i+1])
            if mask.any():
                b[i] = np.mean(fft[mask])

        _band_max[:] = np.maximum(_band_max * 0.9996, b)
        _band_max[:] = np.maximum(_band_max, 0.002)
        b_norm = b / _band_max

        smooth = np.where(b_norm > smooth,
                          b_norm * 0.85 + smooth * 0.15,
                          smooth * 0.50)

        with _lock:
            _bars  = smooth.copy()
            _vu_l  = rl
            _vu_r  = rr
            _pk_l  = max(_pk_l * 0.88, rl)
            _pk_r  = max(_pk_r * 0.88, rr)

threading.Thread(target=_audio_thread, daemon=True).start()

_song_cache = ("", "", 0.0)

def _get_song():
    global _song_cache
    title, artist, ts = _song_cache
    if time.monotonic() - ts < 2.0:
        return title, artist
    try:
        if shutil.which('playerctl'):
            t = subprocess.run(['playerctl','metadata','title'],
                               capture_output=True, text=True, timeout=1).stdout.strip()
            a = subprocess.run(['playerctl','metadata','artist'],
                               capture_output=True, text=True, timeout=1).stdout.strip()
        else:
            t = a = ""
    except:
        t = a = ""
    _song_cache = (t[:44], a[:32], time.monotonic())
    return t[:44], a[:32]

# ── Color LED synthwave ───────────────────────────────────────────────────────
def _seg_col(frac):
    """0=abajo azul → 0.45=cyan → 0.75=blanco → 1=magenta"""
    if frac < 0.42:
        t = frac / 0.42
        return (int(t * 10), int(80 + t * 165), 255)        # azul profundo → cyan
    elif frac < 0.68:
        t = (frac - 0.42) / 0.26
        return (int(t * 210), int(245 - t * 30), int(255 - t * 30))  # cyan → blanco
    elif frac < 0.88:
        t = (frac - 0.68) / 0.20
        return (int(210 + t * 45), int(215 - t * 185), int(225 - t * 70))  # → magenta
    else:
        t = (frac - 0.88) / 0.12
        return (255, int(30 + t * 20), int(155 + t * 80))   # magenta → hot pink

def _temp():
    try:
        t = psutil.sensors_temperatures()
        for k in ['k10temp', 'coretemp', 'cpu_thermal', 'acpitz']:
            if k in t: return t[k][0].current
    except: pass
    return None

def _gpu_pct():
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

def _val_col(v, warn=70, crit=90):
    if v < warn:  return (0, 220, 200)
    if v < crit:  return (200, 180, 0)
    return (255, 40, 120)

# ── Colores tema ──────────────────────────────────────────────────────────────
BG      = (8, 4, 28)
BG_BOT  = (12, 6, 40)
LINE    = (35, 20, 90)
TXT_DIM = (100, 80, 200)
TXT_BRT = (200, 180, 255)

# ── Render ────────────────────────────────────────────────────────────────────
def render(frame):
    global _peaks
    img = Image.new('RGB', (W, H), BG)
    d   = ImageDraw.Draw(img)

    with _lock:
        bars = _bars.copy()

    raw_energy   = float(bars.mean())
    now          = datetime.datetime.now()
    song, artist = _get_song()

    no_signal = (not _ok) or bars.max() < 0.005
    if no_signal:
        t2 = frame * 0.05
        for i in range(N_BARS):
            bars[i] = max(0, (math.sin(t2 + i * 0.45) * 0.22 + 0.26) *
                             (math.sin(t2 * 0.5 + i * 0.22) * 0.18 + 0.52))

    bars = np.clip(bars, 0, 1)
    if bars.max() > 0.12:
        floor = np.percentile(bars, 20) * 0.75
        bars  = np.clip((bars - floor) / max(1 - floor, 0.1), 0, 1)
    bars   = np.power(bars, 0.80)
    energy = float(bars.mean())

    for i in range(N_BARS):
        if bars[i] > _peaks[i]:
            _peaks[i] = bars[i]
        else:
            _peaks[i] = max(0, _peaks[i] - 0.010)

    # ── TOP ───────────────────────────────────────────────────────────────────
    if song:
        d.text((20, 2),  song,   font=fnt(52), fill=TXT_BRT)
        d.text((22, 54), artist, font=fnt(18), fill=TXT_DIM)
    else:
        lbl = "MUSIC VISUALIZER" if not no_signal else "SIN SEÑAL"
        d.text((20, 8), lbl, font=fnt(52), fill=TXT_BRT)

    d.text((W - 175, 4),  now.strftime("%H:%M"),    font=fnt(52), fill=TXT_DIM)
    d.text((W - 150, 54), now.strftime("%d/%m/%y"), font=fnt(18), fill=(60, 40, 140))

    d.line([(0, TOP_H), (W, TOP_H)], fill=LINE, width=1)

    # Grid sutil
    for gy in range(TOP_H + STEP * 5, BASELINE, STEP * 5):
        d.line([(0, gy), (W, gy)], fill=(18, 10, 52), width=1)

    # ── Barras segmentadas ────────────────────────────────────────────────────
    bar_slot = W / N_BARS
    bw       = max(1, int(bar_slot) - 4)

    for i, lvl in enumerate(bars):
        lvl      = min(float(lvl), 1.0)
        x        = int(i * bar_slot) + 2
        n_active = max(1, int(N_SEGS * lvl))

        for s in range(n_active):
            frac = s / max(N_SEGS - 1, 1)
            col  = _seg_col(frac)
            sy   = BASELINE - (s + 1) * STEP
            if sy < TOP_H:
                break
            d.rectangle([x, sy, x + bw - 1, sy + SEG_H - 1], fill=col)
            hl = tuple(min(255, int(c * 1.45)) for c in col)
            d.line([(x, sy), (x + bw - 1, sy)], fill=hl, width=1)

        pk = _peaks[i]
        if pk > 0.06:
            ps = min(N_SEGS - 1, int(N_SEGS * pk))
            py = BASELINE - (ps + 1) * STEP
            if py >= TOP_H:
                pf    = ps / max(N_SEGS - 1, 1)
                pcol  = _seg_col(pf)
                bright = tuple(min(255, c + 100) for c in pcol)
                d.rectangle([x, py, x + bw - 1, py + SEG_H - 1], fill=bright)

    d.line([(0, BASELINE), (W, BASELINE)], fill=LINE, width=1)

    # ── INFO INFERIOR ─────────────────────────────────────────────────────────
    info_top = BASELINE + 3
    d.rectangle([0, info_top, W, H], fill=BG_BOT)
    d.line([(0, info_top), (W, info_top)], fill=LINE, width=1)

    cpu = psutil.cpu_percent(interval=None)
    mem = psutil.virtual_memory()
    ct  = _temp()
    gpu = _gpu_pct()
    gt  = _gtemp()

    chips = []
    chips.append(("CPU", f"{cpu:.0f}%",              _val_col(cpu),        f"{ct:.0f}°C"  if ct  else ""))
    chips.append(("RAM", f"{(mem.total-mem.available)/1024**3:.1f}G",  _val_col(mem.percent), f"{mem.percent:.0f}%"))
    if gpu is not None:
        chips.append(("GPU", f"{gpu:.0f}%",           _val_col(gpu),        f"{gt:.0f}°C"  if gt  else ""))

    chip_w = W // max(len(chips), 3)
    ty     = info_top + 5

    for ci, (label, val, col_v, sub) in enumerate(chips):
        cx = ci * chip_w + 18
        d.rectangle([cx, ty, cx + chip_w - 32, ty + 3], fill=col_v)
        d.text((cx, ty + 6),  label, font=fnt(18), fill=TXT_DIM)
        d.text((cx, ty + 22), val,   font=fnt(46), fill=col_v)
        if sub:
            d.text((cx, ty + 64), sub, font=fnt(18), fill=TXT_DIM)

    for ci in range(1, len(chips)):
        sx = ci * chip_w
        d.line([(sx, info_top + 8), (sx, H - 8)], fill=LINE, width=1)

    if _src:
        src_lbl = _src.replace('alsa_output.', '').replace('.monitor', '')[:28]
        d.text((W - 240, ty + 6), src_lbl, font=fnt(14), fill=(60, 40, 130))

    e_r   = max(5, int(5 + energy * 16))
    ex    = W - 36
    ey    = info_top + (H - info_top) // 2
    e_col = _seg_col(min(1.0, energy * 2.5))
    if frame % 5 < 4:
        d.ellipse([ex - e_r, ey - e_r, ex + e_r, ey + e_r], fill=e_col)

    return img
