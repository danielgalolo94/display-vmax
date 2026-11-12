# Themes Gallery

All available themes. Apply any with `bash tema.sh <name>` or the interactive menu.

---

## phantom

**Docstring:** PHANTOM — White HUD para gabinete blanco

A white-background HUD designed for white PC cases. Stats "emerge" from the background — colored accent bars and gauges appear over a pure white canvas, creating a stark contrast. Uses a dual-arc gauge for CPU % and temperature simultaneously.

- **Background:** Pure white
- **Accent colors:** Orange, blue, red (for warn/crit states)
- **Fonts:** Orbitron-Black (values), NotoSansMono-Bold (data)
- **Notable:** Double-arc gauge (outer = CPU %, inner = temp)
- **Assets used:** `fedora_logo.png`

---

## phantom_night

**Docstring:** PHANTOM NIGHT — Dark HUD nocturno

Dark companion to `phantom`. Same layout and gauge design but inverted to a deep black background with glowing colored halos on the arc gauges.

- **Background:** Near-black (`#050810`)
- **Accent colors:** Same position/logic as phantom, but with glow effects
- **Fonts:** Same as phantom
- **Notable:** Glow halos on arcs via temporary RGBA compositing

---

## hud_cyan

**Docstring:** HUD CYAN — Tactical System Monitor

A tactical cockpit HUD in cyan. Panels with corner-bracket decorations, animated scanline, and a central area for the main CPU gauge. Layout inspired by heads-up displays from sci-fi films.

- **Background:** Very dark navy
- **Primary color:** Cyan `(0, 218, 255)`
- **Secondary:** Magenta / pink accents
- **Notable:** Corner-bracket panel decoration, animated scanline sweep

---

## hud

**Docstring:** HUD — Blue tactical display

The blue variant of the HUD family. Slightly more data-dense than `hud_cyan`. Tuned for large readable text on a 5.5" panel (fonts sized up significantly).

- **Background:** Dark navy
- **Primary color:** Blue `(40, 120, 255)`
- **Notable:** Large fonts explicitly designed for small physical screen size

---

## starwars

**Docstring:** STAR WARS — Hyperspace

Hyperspace animation: white streaks emanating from the center, accelerating outward. Stats displayed in a translucent overlay on the lower portion. The streaks are 2x faster than the original Disney+ animation.

- **Background:** Black → hyperspace lines
- **Animation:** ~200 star streaks, length proportional to speed (frame-based)
- **Stats overlay:** CPU, GPU, RAM, temp in a semi-transparent bottom bar
- **Notable:** Pure procedural animation, no images required

---

## empire

**Docstring:** EMPIRE — Dark Side Imperial Command

Darth Vader silhouette in the rain. Dark atmospheric Imperial Command terminal aesthetic. Matrix-style vertical rain combined with a dramatic sci-fi composition.

- **Background:** Deep black with rain streaks
- **Color:** Dark red Imperial accent, cold grey text
- **Animation:** Falling rain drops (green-tinted, like corrupted data)
- **Notable:** Uses `starwars_battle.gif` asset (single frame) as base texture

---

## matrix

**Docstring:** MATRIX — Digital Rain Interface

The classic green Matrix digital rain, redesigned. Columns of falling Katakana/ASCII characters with brightness variation and trail fade. Stats displayed in bright green terminal-style text overlay.

- **Background:** Black
- **Color:** Matrix green `(0, 255, 70)` with dim trail `(0, 50, 0)`
- **Animation:** 80 independent rain columns with randomized speeds and character sets
- **Stats overlay:** CPU, GPU, RAM, net in terminal-style monospace
- **Notable:** DNS connectivity check in background thread (shows "ONLINE"/"OFFLINE")

---

## retrowave

**Docstring:** RETROWAVE / SYNTHWAVE

Full 80s synthwave scene: purple/magenta sky gradient, sun with horizontal scan lines, perspective grid converging to the horizon, and neon stat readouts. Pure PIL — no images, no URLs.

- **Background:** Deep purple → magenta gradient sky
- **Foreground:** Orange/yellow sun, teal/pink neon grid, hot pink horizon line
- **Animation:** Grid lines scroll toward viewer (Z-axis perspective effect)
- **Stats:** Neon-styled text panels for CPU, GPU, RAM, temp
- **Notable:** Entire scene is procedural geometry — no assets needed

---

## pipboy

**Docstring:** PIP-BOY 3000 — rediseño

Fallout Pip-Boy 3000 terminal. Green phosphor monochrome readout with screen-scan effects and authentic Pip-Boy UI chrome. Uses the Falloutchiro background image.

- **Background:** Olive/dark green terminal
- **Color:** Single-color green phosphor `(0, 210, 60)` with bright highlights
- **Font:** Digital-7 for numbers, ShareTechMono for labels
- **Stats:** CPU, RAM, temp displayed as Pip-Boy "STAT" entries with bar meters
- **Notable:** Simulated CRT scanline overlay

---

## ryzen

**Docstring:** RYZEN — AMD HUD cyberpunk

AMD-branded cyberpunk HUD. Four circular arc gauges (CPU %, CPU GHz, CPU temp, GPU %) with glow effects. Left and right panels for network, RAM, date/time, and GPU VRAM. Bottom strip shows disk usage. Animated scanline over a photographic wallpaper base.

- **Background:** `ryzen_bg.jpg` wallpaper with translucent overlay
- **Primary color:** Cyan `(0, 218, 255)`, AMD red/orange for branding
- **Animation:** Scanline sweep, arc gauge pulse effect
- **Gauges:** 240° arc, segmented with gap ticks, gaussian glow layer
- **Notable:** Most complex theme — 4 gauges + 4 panels + disk strip + branding

---

## ryzen2

**Docstring:** RYZEN 2 — AMD HUD cargado de datos

Data-dense variant of the Ryzen HUD. More stats in the same space, slightly simplified visual design to accommodate the extra readouts. Shows per-core CPU bars, network sparklines, and more.

- **Background:** Dark navy/cyberpunk
- **Primary color:** Cyan, AMD red
- **Notable:** More data panels than ryzen, less whitespace

---

## ryzen9

**Docstring:** RYZEN 9 — AMD HUD rojo fuego

Red-fire variant of the AMD HUD. Same gauge layout as `ryzen` but the color palette shifts from cyan/blue to volcanic orange/red. Intended for a more aggressive gaming aesthetic.

- **Background:** Dark with red fire accents
- **Primary color:** AMD red `(220, 38, 0)`, orange `(255, 90, 10)`
- **Notable:** Same layout as ryzen but in the AMD red-fire brand palette

---

## music

**Docstring:** MUSIC VISUALIZER — 8 bandas retro 80s + panel datos PC

Real-time audio visualizer with 8-band EQ display on the left (ISO octave bands: SUB, BASS, L-MID, MID, U-MID, PRES, HIGH, AIR). Right panel shows PC stats. Audio captured from PipeWire/PulseAudio monitor sink via `parec`.

- **Background:** Deep navy `(6, 8, 35)`
- **EQ colors:** Green → yellow → orange → red (by level)
- **Left panel:** 8 segmented LED-style EQ bars + peak-hold dots
- **Right panel:** Song title (via `playerctl`), artist, clock, CPU/RAM/GPU gauges
- **Animation:** Per-band AGC (auto gain control), peak hold, energy pulse dot
- **Audio:** FFT on 4096-sample window, smoothed with asymmetric attack/decay
- **Notable:** Falls back to animated idle waves when no audio is playing

---

## music2

**Docstring:** MUSIC VISUALIZER 2 — retro synthwave / neon

Alternative audio visualizer with a retrowave visual style. Same audio capture mechanism as `music` but different aesthetic: dark purple-black background, neon-colored bars transitioning from blue to cyan to magenta, more minimal PC stats.

- **Background:** Near-black with purple tint
- **Colors:** Blue → cyan → magenta neon gradient on bars
- **Notable:** More visual, less data-dense than `music`

---

## Applying a theme

```bash
bash tema.sh <name>        # switch immediately
bash tema.sh               # interactive menu with descriptions
bash tema.sh autostart <name>   # set this theme to load on login
```

See [[tema-sh-Reference]] for full command reference, [[Creating-a-Theme]] to build your own.
