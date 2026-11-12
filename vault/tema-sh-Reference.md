# tema.sh Reference

`tema.sh` is the main interface for the XYZ Display. It manages the engine process, applies themes, and configures systemd autostart.

---

## Commands

### Interactive menu (no arguments)

```bash
bash tema.sh
# or
./tema.sh
```

Shows a numbered list of all themes with their descriptions. Indicates the currently active theme (`►`) and the engine status (`● ACTIVO` / `○ detenido`).

Menu options:
- **Number** — apply that theme
- **[a]** — pick the autostart (boot) theme
- **[s]** — stop the display engine
- **[q]** — quit

---

### Apply a theme

```bash
bash tema.sh <theme-name>
```

- Validates that `themes/<name>.py` exists
- Writes the name to `~/.local/share/xyz-display/theme`
- If the engine is already running: hot-reloads the theme (no restart needed)
- If the engine is not running: starts it with `nohup python3 display-engine.py <name>`

```bash
bash tema.sh ryzen
bash tema.sh matrix
bash tema.sh music
```

---

### List themes

```bash
bash tema.sh list
```

Prints one theme name per line (sorted alphabetically). Excludes files starting with `__` or `_` (internal files).

---

### Stop the display

```bash
bash tema.sh stop
```

Sends `SIGTERM` to the display engine process via `pkill -f display-engine.py`.

> [!NOTE]
> This does not affect the systemd service. If the service is enabled, systemd will restart the engine (`Restart=on-failure`). To permanently stop it, run `systemctl --user stop xyz-display@<theme>.service`.

---

### Restart

```bash
bash tema.sh restart
```

Equivalent to `stop` + re-apply the current theme. Reads the current theme from `~/.local/share/xyz-display/theme`.

---

### Status

```bash
bash tema.sh status
```

Outputs either:
- `● activo: <theme-name>` — engine running, current theme
- `○ detenido` — engine not running

---

### Autostart — set

```bash
bash tema.sh autostart <theme-name>
```

Sets the given theme to launch automatically on login via systemd:

1. Removes any existing `xyz-display@*.service` symlinks from `default.target.wants`
2. Runs `systemctl --user enable xyz-display@<name>.service`

This creates a symlink so the service starts when the user's systemd target is reached (typically at graphical login).

---

### Autostart — show current

```bash
bash tema.sh autostart
```

With no second argument, shows which theme is currently set to autostart. It reads the symlinks in:

```
~/.config/systemd/user/default.target.wants/xyz-display@*.service
```

and extracts the theme name from the filename.

---

## How the systemd service works

The service is a **template unit** — a single `.service` file that can be instantiated with different parameters.

File: `~/.config/systemd/user/xyz-display@.service`

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

`%i` is the systemd **instance specifier** — it's the part of the unit name between `@` and `.service`.

So `xyz-display@matrix.service` passes `matrix` as `%i` → launches `display-engine.py matrix`.

### Managing the service directly

```bash
# Start a specific theme
systemctl --user start xyz-display@ryzen.service

# Stop
systemctl --user stop xyz-display@ryzen.service

# Enable autostart
systemctl --user enable xyz-display@ryzen.service

# Disable autostart
systemctl --user disable xyz-display@ryzen.service

# Check status
systemctl --user status xyz-display@ryzen.service

# View logs
journalctl --user -u xyz-display@ryzen.service -f

# After editing the .service file
systemctl --user daemon-reload
```

---

## How autostart detection works

`tema.sh` detects the autostart theme by listing symlinks:

```bash
ls ~/.config/systemd/user/default.target.wants/xyz-display@*.service 2>/dev/null \
    | head -1 \
    | sed 's/.*xyz-display@//; s/\.service//'
```

`systemctl --user enable` creates a symlink in `default.target.wants/` pointing to the actual service file. When the user's systemd session starts (at login), everything in `default.target.wants/` is activated.

> [!WARNING]
> Only one `xyz-display@` instance should be enabled at a time. `tema.sh autostart` handles this by deleting existing symlinks before enabling the new one. If you manually enable via `systemctl`, disable the previous instance first or you'll have two engines fighting over the USB display.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Engine not starting | Theme has a Python error | `python3 -c "from themes.X import render; render(0)"` to see the traceback |
| Display frozen | Engine crashed | `bash tema.sh restart` |
| Autostart shows `(ninguno)` | Symlinks missing or wrong name | `bash tema.sh autostart <theme>` to re-set |
| `pkill` finds nothing to stop | Engine already dead | Check `journalctl --user -u "xyz-display@*" -n 50` |

---

## Key file locations

| File | Purpose |
|---|---|
| `~/.local/share/xyz-display/theme` | Currently active theme name (hot-reload signal) |
| `~/.config/systemd/user/xyz-display@.service` | Service template |
| `~/.config/systemd/user/default.target.wants/xyz-display@*.service` | Autostart symlink |
| `/tmp/xyz-display.log` | Log when engine started via `nohup` (not systemd) |

See [[Installation]] for the full setup guide.
