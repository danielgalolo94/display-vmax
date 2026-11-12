# XYZ Display

A USB-connected secondary display engine for Linux gaming and workstation PCs. Shows real-time system stats through animated themes rendered at 960×480 pixels.

## What it does

- Drives a small USB panel (960×480 px, physically mounted landscape)
- Renders animated themes in Python using PIL/Pillow
- Polls CPU, GPU, RAM, network, temps, and disk in real time
- Runs as a systemd user service — starts on login, survives theme changes without restart
- Theme switches happen hot: write the name, the engine picks it up within 200ms

## Quick start

```bash
# 1. Install dependencies
pip install --user pillow psutil pyusb

# 2. Run a theme immediately
python3 display-engine.py ryzen

# 3. Or use the interactive menu
bash tema.sh
```

> [!TIP]
> `tema.sh` is the main interface. It lists themes with descriptions, handles start/stop, and configures autostart — all from one interactive menu.

## What's in this repo

| Path | Purpose |
|---|---|
| `display-engine.py` | Main loop — loads themes, talks to USB hardware |
| `tema.sh` | Theme manager / interactive menu |
| `themes/` | One `.py` file per theme |
| `fonts/` | TTF fonts (Orbitron, Rajdhani, Teko, etc.) |
| `assets/` | Logo PNGs used by some themes |
| `vault/` | This documentation (Obsidian vault) |

## Vault index

- [[Installation]] — full install guide, systemd setup
- [[How-Themes-Work]] — technical architecture
- [[Creating-a-Theme]] — step-by-step guide with template
- [[Themes-Gallery]] — all themes with descriptions
- [[Sensors-Reference]] — all psutil/sysfs calls used
- [[tema-sh-Reference]] — full command reference
- [[GitHub-Export]] — preparing and publishing to GitHub

## Hardware

| Spec | Value |
|---|---|
| Resolution | 960×480 px |
| Connection | USB (VID `0x33c3`, PID `0xf101`) |
| Protocol | Raw JPEG frames over bulk endpoint |
| Framerate | ~5 fps (configurable in engine) |
| Physical orientation | Landscape (display mounted 90° CCW internally) |

> [!NOTE]
> The engine automatically handles the hardware's portrait buffer orientation. Themes always work in 960×480 landscape — the engine rotates before sending.
