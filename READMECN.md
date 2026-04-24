# QRCode Gen

跨平台二维码生成器,界面原生清爽。支持多种内容类型、模块风格、带独立透明通道的渐变色、中心 Icon,以及**真矢量 SVG 导出**。纯离线,不联网。

[English](README.md)

---

## 功能

- **内容类型** —— URL、文本、Wi-Fi、邮箱、电话 / 短信、名片(vCard)
- **模块风格** —— 方块 / 圆点 / 圆角方块 / 横条 / 竖条,以及自定义 PNG 形状
- **自研颜色选择器** —— HSV 方形 + 色相条 + **独立 alpha 透明度条** + Hex(`#RRGGBB` / `#RRGGBBAA`)+ RGBA 数值输入 + 最近使用色历史
- **全链路透明度** —— 前景色、渐变两端、背景色均可独立调透明度。背景 alpha = 0 可导出真透明底 PNG,适合贴纸 / 水印素材。
- **渐变** —— 平滑线性渐变,两端均支持 alpha
- **中心 Icon** —— 叠加任意图片到中心,附白色圆角底板(自动锁容错级别为 H)
- **图片质量** —— 低 / 中 / 高 / 超高(≥ 1044 px)
- **导出** —— PNG(RGBA) + **真矢量 SVG**(原生 `<rect>` / `<circle>` / `<linearGradient>`,放大不失真)
- **语言** —— 自动检测系统语言(简体中文 / English)
- **离线** —— 所有处理都在本地,不需要联网

## 下载

从 [Releases](../../releases/latest) 下载最新版本。

| 平台 | 文件 | 说明 |
|---|---|---|
| **Windows x64** | `QRCode Gen Setup vX.Y.Z.exe` | 双击安装器,双语向导 |
| **macOS(Apple Silicon)** | `QRCode Gen.pkg` | 标准 .pkg 安装包 |
| **macOS(完整分发包)** | `QRCode Gen vX.Y.Z macOS.zip` | pkg + 首启动修复脚本 + 说明文档 |

### 首次启动说明

- **Windows**:SmartScreen 可能会警告(安装器未代码签名),点「更多信息」→「仍要运行」即可。
- **macOS**:Gatekeeper 可能会阻止首次启动。方案一:运行 zip 包内的「如果无法打开 · If App Won't Open.command」脚本(它会 `sudo xattr -cr` 清除隔离属性);方案二:到「系统设置 → 隐私与安全性」中点「仍要打开」。

## 系统要求

- **Windows**:Windows 10 或更新,x64 架构
- **macOS**:macOS 11 或更新,Apple Silicon(arm64)。目前未打 Intel Mac 版本,可从源码自行构建。

## 从源码构建

### macOS

```bash
git clone https://github.com/JackyWilliam/QRCode-Gen.git
cd QRCode-Gen
pip3 install -r requirements.txt
bash build.sh
```

产物:`dist/QRCode Gen.pkg` + `dist/QRCode Gen vX.Y.Z macOS.zip`(分发 bundle)

需要用 [python.org](https://www.python.org) 的 Python 3.x(不是 Homebrew 的)。

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

产物:`dist/QRCode Gen/` onedir 目录。要把它封装成一键安装器,参考 [installer/README.md](installer/README.md) —— `makensis` 可以在 macOS / Linux 上编译 NSIS 脚本。

## 项目结构

| 文件 | 说明 |
|------|------|
| `app.py` | UI 主程序(CustomTkinter) |
| `qr_engine.py` | QR 生成引擎(Pillow)。原生矢量 SVG 导出。 |
| `color_picker.py` | 自研 HSV + alpha 颜色选择器模块。对外暴露 `ColorPicker` / `ColorTile` / `parse_hex` / `format_hex` / `render_swatch`。 |
| `i18n.py` | 国际化翻译表 |
| `build.sh` | macOS PyInstaller 一键打包脚本(.app → .pkg → 分发 zip) |
| `installer/` | Windows NSIS 安装器源码 —— 通过 `makensis` 在 macOS / Linux 上编译 |
| `fix_first_launch.command` | macOS 首启动修复脚本(清 Gatekeeper 隔离属性) |
| `.github/workflows/build.yml` | CI —— macOS + Windows 自动构建 |

## 协议

MIT 协议。Copyright © 2026 Yijie Ding.
