# CleanDaMacintosh ✦

> Free, open-source Mac cleaner — a better,free-er,amazinger alternative to CleanMyMac.  
> No subscription. No telemetry. No pip installs. Pure Python stdlib only.

![macOS](https://img.shields.io/badge/macOS-11%2B-blueviolet?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-pink?style=flat-square)
![Version](https://img.shields.io/badge/Version-2.0.0-purple?style=flat-square)

---

## What is it?

CleanDaMacintosh is a native-feeling macOS utility app built entirely with Python + tkinter. It scans your Mac for junk, privacy risks, large files, and performance issues — and lets you clean them up in seconds.

No Electron. No web views. No external dependencies. Just run it.

---

## Features

### Available Now
| Feature | Description |
|---|---|
| **Smart Care** | One-click full system scan with animated results |
| **System Junk** | App caches, Xcode derived data, old iOS backups, log files |
| **Mail & Downloads** | Mail attachments, large downloads, browser caches |
| **Trash Bins** | All trash locations including app-specific bins |
| **Malware Scan** | Launch agent analysis, suspicious extension detection |
| **Privacy** | Browser history, cookies, crash reports, quarantine DB |
| **Optimization** | Login items manager, launch agents viewer |
| **Uninstaller** | Remove apps + all leftover files and preferences |
| **Space Lens** | Interactive bubble chart — drill into your disk usage |
| **Large & Old Files** | Files over 100MB sorted by age, one-click trash |

### Coming in v3.0 ✦
These features are previewed in the app with full descriptions and are under active development:

- RAM Cleaner
- VPN Guard
- Battery Monitor
- App Updater
- Duplicate Finder
- Photo Cleaner
- Cloud Cleanup
- Network Monitor
- Disk Speed Test
- Menu Bar Widget
- File Vault
- Time Machine Helper

---

## Installation

### Option 1 — DMG (Recommended)
1. Download `CleanDaMacintosh.dmg`
2. Double-click to open
3. Drag **CleanDaMacintosh** → **Applications**
4. Launch from Applications or Spotlight

### Option 2 — Run directly
```bash
git clone https://github.com/harrytinklecloud/CleanDaMacintosh.git
cd CleanDaMacintosh
python3 CleanDaMacintosh.py
```

> **Requirement:** Python 3.10+ with tkinter.  
> On macOS with Homebrew: `brew install python-tk`

### Option 3 — Build the app yourself
```bash
git clone https://github.com/harrytinklecloud/CleanDaMacintosh.git
cd CleanDaMacintosh
bash build_app.sh
```

This generates `CleanDaMacintosh.app` and `CleanDaMacintosh.dmg` in the project folder.

---

## Requirements

- macOS 11 Big Sur or later
- Python 3.10+ with tkinter (`brew install python-tk`)
- No other dependencies — zero pip installs

---

## Project Structure

```
CleanDaMacintosh/
├── CleanDaMacintosh.py   # Main app (pure Python stdlib)
├── make_icon.py          # Generates AppIcon.icns (pure Python)
├── build_app.sh          # Builds .app bundle
├── build_dmg.sh          # Builds distributable .dmg
└── README.md
```

---

## Building from Source

```bash
# Build the .app and .dmg in one step
bash build_app.sh
```

The build script:
1. Creates the `.app` bundle structure
2. Copies the Python source into `Contents/Resources/`
3. Writes a smart launcher that finds Python + tkinter on the user's system
4. Generates a full `.icns` icon (all sizes + @2x Retina) using pure Python
5. Calls `build_dmg.sh` to produce a distributable `.dmg` with a custom background

---

## License

MIT License — free to use, modify, and distribute.  
© 2026 CleanDaMacintosh Foundation

---

## Contributing

Pull requests welcome. If you want to implement one of the v3.0 features, open an issue first so we can coordinate.

Star the repo if you find it useful — it helps a lot! ✦
