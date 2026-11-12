# Display Engine — Guía rápida

## Hardware
- Panel físico: **480×960 portrait**, montado **90° CCW** → se ve como **960×480 landscape**
- El engine transpone automáticamente: `FLIP_TOP_BOTTOM + TRANSPOSE`
- Framerate: **5 FPS** (200ms por frame), JPEG quality 88, USB endpoint 0x02

## Estructura de archivos

```
display/
├── display-engine.py   # Motor principal (no modificar)
├── tema.sh             # Cambiar tema: ./tema.sh <nombre>
├── DISPLAY.md          # Esta guía
└── themes/
    ├── bttf.py         # DeLorean dashboard (flux capacitor, time circuits, métricas)
    ├── cyberpunk.py    # —
    ├── fallout.py      # Pip-Boy 3000 terminal verde
    ├── lofi.py         # Lo-Fi Tokyo Night con lluvia de kanji
    ├── matrix.py       # Matrix digital rain con GIF + stats grandes
    ├── music.py        # —
    ├── nasa.py         # —
    ├── pipboy.py       # —
    ├── retrowave.py    # Synthwave 80s / Back to the Future con GIF + grid
    └── starwars.py     # Hyperspace radial + stats estilo Comando Galáctico
```

## Cambiar tema

```bash
./tema.sh retrowave      # cambia en caliente (sin reiniciar engine)
./tema.sh list           # lista todos los temas disponibles
```

## Crear un tema nuevo

Crear `themes/mi_tema.py` con una función `render(frame) → PIL.Image`:

```python
from PIL import Image, ImageDraw, ImageFont
W, H = 960, 480
FONT = "/tmp/vmax_theme/Falloutchiro/font/Teko-Medium-3.ttf"

def fnt(size):
    try:    return ImageFont.truetype(FONT, size)
    except: return ImageFont.load_default()

def render(frame):
    img = Image.new('RGB', (W, H), (0, 0, 0))
    d   = ImageDraw.Draw(img)
    # ... dibujar aquí ...
    return img
```

- `frame` es un entero creciente (0, 1, 2 … a 5 FPS)
- El engine acepta imágenes 960×480 (landscape) y las transpone al hardware
- Todas las fuentes están en `fonts/` dentro del repo (rutas relativas, portable)

## Fuentes disponibles

| Fuente | Archivo | Uso |
|--------|---------|-----|
| Teko-Medium | `fonts/Teko-Medium.ttf` | Principal — números grandes en todos los temas |
| FiraCode Nerd Font | `fonts/FiraCodeNerdFont-Medium.ttf` | Iconos Nerd + texto técnico |
| CaskaydiaMono NF | `fonts/CaskaydiaMonoNF-SemiBold.ttf` | Mono + iconos Nerd, estilo terminal |
| Noto Sans CJK | `/usr/share/fonts/google-noto-sans-mono-cjk-vf-fonts/NotoSansMonoCJK-VF.ttc` | Kanji/katakana (lofi, matrix) |

En temas, usar rutas relativas al repo:
```python
import os
_BASE     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT      = os.path.join(_BASE, "fonts", "Teko-Medium.ttf")
FONT_NERD = os.path.join(_BASE, "fonts", "FiraCodeNerdFont-Medium.ttf")
FONT_MONO = os.path.join(_BASE, "fonts", "CaskaydiaMonoNF-SemiBold.ttf")
```

## Tamaños de fuente recomendados (para 960×480)

| Elemento | Tamaño | Contexto |
|----------|--------|---------|
| Valor principal (CPU %, RAM) | 100–160px | Sin GPU (espacio libre) |
| Valor principal (con GPU) | 80–110px | Tres valores en pantalla |
| Label de sección | 26–32px | Encima del valor |
| Temperatura | 36–44px | Al lado del label |
| Reloj | 80–100px | Panel lateral |
| Fecha / subtítulo | 18–22px | Debajo del reloj |
| Subvalor (ej: `/ 32G`) | 40–52px | Al lado del valor RAM |

## Cargar GIFs (patrón estándar)

```python
import urllib.request, io
from PIL import Image

_gif_frames = []
_gif_done   = False

def _load_gif():
    global _gif_frames, _gif_done
    if _gif_done: return
    _gif_done = True
    urls = ["https://media.giphy.com/media/XXXXX/giphy.gif", ...]
    for url in urls:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=8) as r:
                data = r.read()
            gif = Image.open(io.BytesIO(data))
            for i in range(getattr(gif, 'n_frames', 1)):
                gif.seek(i)
                _gif_frames.append(
                    gif.convert('RGB').resize((W, H), Image.Resampling.LANCZOS).copy()
                )
            if _gif_frames: return  # primer URL que funcione
        except Exception as e:
            print(f"[tema] {url}: {e}")

# En render():
def render(frame):
    _load_gif()   # lazy init, solo descarga una vez
    if _gif_frames:
        img.paste(_gif_frames[frame % len(_gif_frames)], (0,0))
```

## Leer métricas del sistema

```python
import psutil, subprocess

def _cpu():  return psutil.cpu_percent(interval=None)
def _mem():  return psutil.virtual_memory()   # .percent, .used, .total

def _temp():   # temperatura CPU
    t = psutil.sensors_temperatures()
    for k in ['k10temp','coretemp','cpu_thermal','acpitz']:
        if k in t: return t[k][0].current
    return None

def _gpu():    # ocupación GPU AMD
    r = subprocess.run(['cat','/sys/class/drm/card0/device/gpu_busy_percent'],
                       capture_output=True, text=True, timeout=1)
    return int(r.stdout.strip()) if r.returncode == 0 else None
```

## Efecto glow en texto

```python
def _glow(d, x, y, text, size, col, dim):
    for dx,dy in [(-2,-1),(2,-1),(-2,1),(2,1),(0,-2),(0,2)]:
        d.text((x+dx, y+dy), text, font=fnt(size), fill=dim)
    d.text((x, y), text, font=fnt(size), fill=col)
```

## Oscurecer GIF para leer texto encima

```python
dark    = Image.new('RGB', (W, H), (0, 0, 0))
blended = Image.blend(img.crop((0,0,W,H)), dark, alpha=0.55)
img.paste(blended, (0,0))
# alpha: 0.0 = GIF puro | 1.0 = negro total | 0.5–0.65 recomendado
```

## Temas actuales — resumen visual

| Tema | Layout | Animación |
|------|--------|-----------|
| `starwars` | izq: espacio 370px \| der: stats 590px | Hyperspace radial, 280 estrellas |
| `retrowave` | arriba: GIF+sol 238px \| abajo: stats 242px | Sol pulsante + grid perspectiva |
| `matrix` | izq: lluvia 580px \| der: stats 380px | Lluvia katakana + GIF tintado |
| `lofi` | izq: GIF+kanji 540px \| der: stats 420px | Kanji rain + pétalos + GIF |
| `bttf` | izq: Flux 370px \| der: time circuits+stats 590px | Flux pulsante + time circuits |
| `fallout` | portrait 480×960 | Scanlines + Vault Boy |
