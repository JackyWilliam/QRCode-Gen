# QRCode Gen

A macOS QR code generator with a clean, native-feeling UI. Supports multiple content types, custom styles, colors, gradients, and center icons. Fully offline — no network required.

[中文文档](READMECN.md)

---

## Features

- **Content types** — URL, plain text, Wi-Fi, Email, Phone / SMS, vCard
- **Module styles** — Square, Circle, Rounded, H-Bars, V-Bars
- **Colors** — Custom foreground / background, linear gradient
- **Center icon** — Overlay any image at the center (auto-locks error correction to H)
- **Image quality** — Low / Medium / High / Ultra (≥ 1044 px)
- **Export** — PNG and SVG
- **Language** — Auto-detects macOS system language (English / Chinese)
- **Offline** — All processing is local; no internet connection needed

## Requirements

- macOS 11 or later
- Apple Silicon (arm64)

## Installation

Download the latest `QRCode Gen.pkg` from [Releases](../../releases) and double-click to install. The app will be placed in `/Applications`.

> First launch: macOS may show a security prompt. Go to **System Settings → Privacy & Security** and click **Open Anyway**.

## Build from Source

```bash
git clone https://github.com/JackyWilliam/QRCode-Gen.git
cd QRCode-Gen
pip3 install -r requirements.txt
bash build.sh
```

Requires Python 3.x from [python.org](https://www.python.org) (not Homebrew).

## Project Structure

| File | Description |
|------|-------------|
| `app.py` | Main UI (CustomTkinter) |
| `qr_engine.py` | QR generation engine (Pillow) |
| `i18n.py` | Internationalization |
| `build.sh` | PyInstaller build script |
| `install_helper.cpp` | Helper to bypass Gatekeeper on first launch |
| `.github/workflows/build.yml` | CI — macOS universal2 + Windows builds |

## License

MIT License
