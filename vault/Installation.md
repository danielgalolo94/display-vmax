# Installation

Complete setup guide for the XYZ Display engine on Linux.

## Requirements

### Python packages

```bash
pip install --user pillow psutil pyusb
```

### System packages (Fedora / RPM)

```bash
sudo dnf install python3 python3-pillow python3-psutil lm_sensors alsa-utils
```

For Debian/Ubuntu:

```bash
sudo apt install python3 python3-pil python3-psutil lm-sensors alsa-utils
```

> [!NOTE]
> `lm_sensors` is needed for CPU/GPU temperature readings. `alsa-utils` is only needed for the `music` and `music2` themes (they use `parec` from PulseAudio/PipeWire, which is separate, but alsa-utils gives you `aplay`/`amixer` for debugging).

### USB access without root

Add a udev rule so your user can write to the display:

```bash
sudo tee /etc/udev/rules.d/99-xyz-display.rules <<'EOF'
SUBSYSTEM=="usb", ATTR{idVendor}=="33c3", ATTR{idProduct}=="f101", MODE="0666"
EOF
sudo udevadm control --reload-rules && sudo udevadm trigger
```

---

## Clone

```bash
git clone <repo-url> ~/display
cd ~/display
```

---

## Fonts

All fonts live in `/home/dg/display/fonts/`. They must be present for themes to render correctly. If a font is missing, themes fall back to PIL's built-in default (ugly but functional).

| File | Family | Used in |
|---|---|---|
| `Orbitron-Black.ttf` | Orbitron Black | Most themes — main values |
| `Orbitron-Bold.ttf` | Orbitron Bold | ryzen, phantom |
| `Rajdhani-SemiBold.ttf` | Rajdhani | Labels, subtitles |
| `ShareTechMono.ttf` | Share Tech Mono | Data readouts |
| `Teko-Medium.ttf` | Teko | HUD labels, EQ labels |
| `NotoSansMono-Bold.ttf` | Noto Sans Mono | phantom, phantom_night |
| `Quantico-Bold.ttf` | Quantico | Accent text |
| `Exo2-Bold.ttf` | Exo 2 | Secondary display text |
| `CaskaydiaMonoNF-SemiBold.ttf` | Caskaydia Mono NF | Code-style readouts |
| `FiraCodeNerdFont-Medium.ttf` | Fira Code Nerd Font | ryzen data panels |
| `JetBrainsMono-Bold.ttf` | JetBrains Mono | Terminal-style themes |
| `digital7.ttf` | Digital-7 | Seven-segment clock displays |

> [!TIP]
> Orbitron and Rajdhani are on Google Fonts (free). The Nerd Font variants (Caskaydia, FiraCode) are from [nerdfonts.com](https://www.nerdfonts.com).

---

## Assets

Located in `/home/dg/display/assets/`:

| File | Used by |
|---|---|
| `fedora_logo.png` | phantom, phantom_night |
| `fedora_logo2.png` | alternate phantom variant |
| `amd_ryzen_logo.png` | ryzen themes |
| `amd_logo.png` | ryzen themes |
| `hud_bg2.png` | hud, hud_cyan backgrounds |
| `ryzen_bg.jpg` | ryzen wallpaper base |
| `starwars_battle.gif` | starwars, empire (static frame used) |

---

## Running manually

```bash
# Run a specific theme directly
python3 display-engine.py ryzen

# Use the theme manager (interactive menu)
bash tema.sh

# Apply a theme by name
bash tema.sh phantom

# Stop
bash tema.sh stop
```

---

## systemd service

The display engine runs as a systemd **user** service (no root). The service is a template unit: `xyz-display@<theme>.service`.

### Service file

Place this at `~/.config/systemd/user/xyz-display@.service`:

```ini
[Unit]
Description=XYZ Display Engine (%i)
After=default.target

[Service]
ExecStart=/usr/bin/python3 /home/dg/display/display-engine.py %i
Restart=on-failure
RestartSec=3

[Install]
WantedBy=default.target
```

`%i` is the systemd instance specifier — it becomes the theme name.

### Enable and start

```bash
# Reload systemd after creating/editing the service file
systemctl --user daemon-reload

# Start immediately with a specific theme
systemctl --user start xyz-display@ryzen.service

# Enable autostart on login
systemctl --user enable xyz-display@ryzen.service

# Check status
systemctl --user status xyz-display@ryzen.service

# View logs
journalctl --user -u xyz-display@ryzen.service -f
```

> [!WARNING]
> Only enable one instance at a time. The `tema.sh autostart` command handles this correctly (it removes old symlinks before enabling a new one). If you enable manually, disable the old instance first.

### Autostart via tema.sh (recommended)

```bash
# Set ryzen as the boot theme
bash tema.sh autostart ryzen

# Check current autostart theme
bash tema.sh autostart
```

This is equivalent to the `[a]` option in the interactive menu.

---

## Verify it's working

```bash
# Check engine is running
bash tema.sh status

# Watch the log
tail -f /tmp/xyz-display.log
```

See [[tema-sh-Reference]] for the full command list.
