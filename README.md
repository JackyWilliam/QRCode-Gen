# QRCode Gen

A cross-platform QR code generator with a clean, native-feeling UI. Supports multiple content types, custom module styles, gradient colors with an independent alpha channel, center icons, and true vector SVG export. Fully offline.

[中文文档](READMECN.md)

---

## Features

- **Content types** — URL, plain text, Wi-Fi, Email, Phone / SMS, vCard
- **Module styles** — Square, Circle, Rounded, H-Bars, V-Bars, plus custom PNG shapes
- **In-house color picker** — HSV square + hue slider + **independent alpha slider** + hex (`#RRGGBB` / `#RRGGBBAA`) + RGBA numeric inputs + recent-colors history
- **Full alpha support** — foreground color, gradient stops (both ends), and background are each independently transparency-controlled. Export truly transparent-background PNGs for stickers/watermarks.
- **Gradient** — Smooth linear gradient with alpha on both stops
- **Center icon** — Overlay any image at the center on a white rounded plate (auto-locks error correction to H)
- **Image quality** — Low / Medium / High / Ultra (≥ 1044 px)
- **Export** — PNG (RGBA) and **true vector SVG** (native `<rect>` / `<circle>` / `<linearGradient>`, infinitely scalable)
- **Language** — Auto-detects system language (English / Simplified Chinese)
- **Offline** — All processing is local; no internet connection needed

## Downloads

Grab the latest release from [Releases](../../releases/latest).

| Platform | File | Notes |
|---|---|---|
| **Windows x64** | `QRCode Gen Setup vX.Y.Z.exe` | Double-click installer, bilingual wizard |
| **macOS (Apple Silicon)** | `QRCode Gen.pkg` | Standard .pkg installer |
| **macOS (bundle)** | `QRCode Gen vX.Y.Z macOS.zip` | pkg + first-launch helper + docs |

### First-launch notes

- **Windows**: SmartScreen may warn on first run (installer is not code-signed). Click "More info" → "Run anyway".
- **macOS**: Gatekeeper may block on first launch. Either run the bundled `如果无法打开 · If App Won't Open.command` script (runs `sudo xattr -cr` to clear the quarantine attribute), or go to **System Settings → Privacy & Security** and click **Open Anyway**.

## Requirements

- **Windows**: Windows 10 or later, x64
- **macOS**: macOS 11 or later, Apple Silicon (arm64). Intel Mac support is not currently packaged; build from source is possible.

## Build from Source

### macOS

```bash
git clone https://github.com/JackyWilliam/QRCode-Gen.git
cd QRCode-Gen
pip3 install -r requirements.txt
bash build.sh
```

Output: `dist/QRCode Gen.pkg` + `dist/QRCode Gen vX.Y.Z macOS.zip` (distribution bundle).

Requires Python 3.x from [python.org](https://www.python.org) (not Homebrew).

### Windows

```bash
pip install -r requirements.txt
pyinstaller --name "QRCode Gen" --windowed --onedir --clean ^
  --add-data "Logo.png;." ^
  --add-data "i18n.py;." ^
  --add-data "qr_engine.py;." ^
  --add-data "color_picker.py;." ^
  --hidden-import "PIL._tkinter_finder" ^
  --hidden-import "qrcode.image.styledpil" ^
  --hidden-import "qrcode.image.styles.moduledrawers.pil" ^
  --icon "Logo.png" ^
  app.py
```

Output: `dist/QRCode Gen/` onedir. To wrap it in a one-click installer, see [installer/README.md](installer/README.md) — `makensis` can compile the NSIS script on macOS or Linux.

## Project Structure

| File | Description |
|------|-------------|
| `app.py` | Main UI (CustomTkinter) |
| `qr_engine.py` | QR generation engine (Pillow). Native vector SVG export. |
| `color_picker.py` | In-house HSV + alpha color picker module. Exports `ColorPicker`, `ColorTile`, `parse_hex`, `format_hex`, `render_swatch`. |
| `i18n.py` | Internationalization |
| `build.sh` | macOS PyInstaller build script (.app → .pkg → bundle) |
| `installer/` | Windows NSIS installer source — compiles on macOS/Linux via `makensis` |
| `fix_first_launch.command` | macOS helper to clear Gatekeeper quarantine |
| `.github/workflows/build.yml` | CI — macOS + Windows builds |

## License

MIT License. Copyright © 2026 Yijie Ding.
