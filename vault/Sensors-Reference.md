# Sensors Reference

All sensor calls used across the theme library, with working code patterns.

> [!NOTE]
> Always call `psutil.cpu_percent(interval=None)` in `render()` — never with `interval=1` or any positive value, which would block for a full second. Prime it once at startup: `psutil.cpu_percent(interval=None)` — the engine already does this before entering the frame loop.

---

## CPU

### Percent (total)

```python
import psutil
cpu = psutil.cpu_percent(interval=None)   # float, 0.0–100.0
```

### Percent (per-core)

```python
cores = psutil.cpu_percent(interval=None, percpu=True)   # list of floats
# e.g. [12.5, 87.3, 5.0, 45.1, ...]
```

### Frequency

```python
freq = psutil.cpu_freq()
if freq:
    ghz     = freq.current / 1000   # current GHz
    ghz_max = freq.max / 1000       # max GHz
```

### Core count

```python
physical = psutil.cpu_count(logical=False)
logical  = psutil.cpu_count(logical=True)
```

### Model name

```python
def _cpu_name():
    try:
        for line in open('/proc/cpuinfo'):
            if 'model name' in line:
                return line.split(':')[1].strip()
    except:
        pass
    return 'Unknown'
```

---

## Memory

### RAM

```python
mem = psutil.virtual_memory()
mem.total    # bytes
mem.used     # bytes
mem.percent  # float 0–100

# Human-readable
gb_used  = mem.used  / 1024**3
gb_total = mem.total / 1024**3
mb_used  = mem.used  // (1024 * 1024)
```

### Swap

```python
swap = psutil.swap_memory()
swap.total
swap.used
swap.percent
```

---

## Disk

### Single mount point

```python
disk = psutil.disk_usage('/')
disk.total    # bytes
disk.used     # bytes
disk.free     # bytes
disk.percent  # float 0–100
```

### All mounts (pattern used in ryzen theme)

```python
def _disks():
    seen, res = set(), []
    for p in psutil.disk_partitions(all=False):
        if p.mountpoint in {'/', '/home'} and p.mountpoint not in seen:
            seen.add(p.mountpoint)
            try:
                u = psutil.disk_usage(p.mountpoint)
                res.append((p.mountpoint, u.used, u.total, u.percent))
            except:
                pass
    return sorted(res)
```

---

## Network

### Instantaneous delta (KB/s)

The engine runs at ~5fps, so deltas between frames are meaningful. Cache previous counters:

```python
import time as _time
_NET_ST = {'t': 0.0, 'sent': 0, 'recv': 0, 'ul': 0.0, 'dl': 0.0}

def _net():
    global _NET_ST
    try:
        now = _time.time()
        c   = psutil.net_io_counters()
        dt  = now - _NET_ST['t']
        if dt > 0.05 and _NET_ST['t'] > 0:
            _NET_ST['ul'] = (c.bytes_sent - _NET_ST['sent']) / dt / 1024
            _NET_ST['dl'] = (c.bytes_recv - _NET_ST['recv']) / dt / 1024
        _NET_ST.update({'t': now, 'sent': c.bytes_sent, 'recv': c.bytes_recv})
        return max(0.0, _NET_ST['ul']), max(0.0, _NET_ST['dl'])
    except:
        return 0.0, 0.0

# Returns (upload_kbs, download_kbs)
ul, dl = _net()

def _fmt_net(kbs):
    if kbs < 1:    return "0.0 K"
    if kbs < 1024: return f"{kbs:.1f} K"
    return f"{kbs/1024:.1f} M"
```

### Per-interface

```python
per_iface = psutil.net_io_counters(pernic=True)
eth0 = per_iface.get('eth0') or per_iface.get('enp6s0')
if eth0:
    eth0.bytes_sent
    eth0.bytes_recv
```

---

## Temperatures

### CPU — AMD (k10temp) and Intel (coretemp)

```python
def _temp():
    try:
        t = psutil.sensors_temperatures()
        for k in ['k10temp', 'coretemp', 'cpu_thermal', 'acpitz']:
            if k in t:
                return t[k][0].current   # float, Celsius
    except:
        pass
    return None
```

> [!NOTE]
> On AMD Ryzen, `k10temp` gives the Tdie value (actual die temp). `acpitz` is the ACPI thermal zone and is often less accurate.

### GPU temperature — AMD / NVIDIA

```python
def _gtemp():
    try:
        t = psutil.sensors_temperatures()
        for k in ['amdgpu', 'nvidia', 'radeon']:
            if k in t:
                return t[k][0].current
    except:
        pass
    return None
```

### All sensors (debug)

```python
import pprint
pprint.pprint(psutil.sensors_temperatures())
```

---

## GPU (AMD sysfs)

AMD GPUs expose extra data via sysfs at `/sys/class/drm/card1/device/`.

> [!WARNING]
> The card number (`card1`) can vary. On most systems with a dedicated GPU + integrated GPU, the discrete card is `card1`. Check `ls /sys/class/drm/` to confirm.

### GPU busy percent

```python
import subprocess

def _gpu_pct():
    try:
        r = subprocess.run(
            ['cat', '/sys/class/drm/card1/device/gpu_busy_percent'],
            capture_output=True, text=True, timeout=1)
        if r.returncode == 0:
            return int(r.stdout.strip())
    except:
        pass
    return None
```

Or read directly:

```python
def _gpu_pct():
    try:
        return int(open('/sys/class/drm/card1/device/gpu_busy_percent').read().strip())
    except:
        return None
```

### VRAM usage

```python
def _gpu_vram():
    try:
        used  = int(open('/sys/class/drm/card1/device/mem_info_vram_used').read())
        total = int(open('/sys/class/drm/card1/device/mem_info_vram_total').read())
        return used // (1024 * 1024), total // (1024 * 1024)   # MB
    except:
        return None, None

vram_used_mb, vram_total_mb = _gpu_vram()
```

---

## Fan speeds

```python
fans = psutil.sensors_fans()
# dict of {label: [SensorFan(label, current)]}
for name, entries in fans.items():
    for entry in entries:
        print(f"{name} / {entry.label}: {entry.current} RPM")
```

---

## Uptime / boot time

```python
import datetime, psutil

boot_ts  = psutil.boot_time()                          # Unix timestamp
uptime_s = datetime.datetime.now().timestamp() - boot_ts

hours   = int(uptime_s // 3600)
minutes = int((uptime_s % 3600) // 60)

uptime_str = f"{hours}h {minutes:02d}m"
```

---

## Process count

```python
n_procs = len(psutil.pids())
```

---

## Voltage (via `sensors` CLI)

psutil doesn't expose voltages on most Linux systems. Use `lm_sensors` via subprocess:

```python
import subprocess

def _voltages():
    """Parse `sensors` output for voltage readings."""
    try:
        out = subprocess.run(['sensors'], capture_output=True, text=True, timeout=2).stdout
        volts = {}
        for line in out.splitlines():
            if 'V' in line and '+' in line:
                parts = line.split()
                if parts:
                    label = parts[0].rstrip(':')
                    for p in parts[1:]:
                        try:
                            v = float(p.lstrip('+').rstrip('V'))
                            volts[label] = v
                            break
                        except ValueError:
                            continue
        return volts
    except:
        return {}
```

> [!TIP]
> Run this in a background thread with caching — `sensors` is a subprocess that takes ~100ms.

---

## Color-coding by value

The standard helper used in most themes:

```python
def _val_col(v, warn=70, crit=90):
    """Green below warn, yellow/orange approaching crit, red above."""
    if v < warn:  return (28, 185, 95)     # green
    if v < crit:  return (215, 155, 15)    # amber
    return (215, 50, 50)                    # red

# Temperature variant (tighter thresholds)
def _tc(t):
    if t is None: return (0, 218, 255)     # cyan = unknown
    return (0, 210, 128) if t < 65 else ((255, 152, 20) if t < 80 else (255, 45, 45))
```

See [[Creating-a-Theme]] for how these integrate into a full theme.
