# QRCode Gen

macOS 原生风格二维码生成器。支持多种内容类型、自定义样式、颜色渐变与中心图标叠加。完全离线，无需网络。

[English](README.md)

---

## 功能

- **内容类型** — 网址、文字、Wi-Fi、邮件、电话 / 短信、名片（vCard）
- **模块样式** — 方块、圆点、圆角方块、横条、竖条
- **颜色** — 自定义前景色 / 背景色，支持线性渐变
- **中心图标** — 在二维码中心叠加任意图片（自动锁定容错级别为 H）
- **图片质量** — 低 / 中 / 高 / 超高（超高模式输出 ≥ 1044 px）
- **导出格式** — PNG 和 SVG
- **语言** — 自动识别 macOS 系统语言（中文 / 英文）
- **完全离线** — 所有计算均在本地完成，无任何网络请求

## 系统要求

- macOS 11 或更高版本
- Apple Silicon（arm64）芯片

## 安装

从 [Releases](../../releases) 下载最新的 `QRCode Gen.pkg`，双击按提示安装，App 会自动放入 `/Applications`。

> 首次启动时 macOS 可能提示安全警告，前往「系统设置 → 隐私与安全性」点击「仍要打开」即可，后续不再提示。

## 从源码构建

```bash
git clone https://github.com/JackyWilliam/QRCode-Gen.git
cd QRCode-Gen
pip3 install -r requirements.txt
bash build.sh
```

需要使用 [python.org](https://www.python.org) 提供的 Python 3.x（非 Homebrew 版本）。

## 文件说明

| 文件 | 说明 |
|------|------|
| `app.py` | UI 主程序（CustomTkinter） |
| `qr_engine.py` | 二维码生成引擎（Pillow） |
| `i18n.py` | 国际化翻译表 |
| `build.sh` | PyInstaller 打包脚本 |
| `install_helper.cpp` | 首次启动绕过 Gatekeeper 的安装助手 |
| `.github/workflows/build.yml` | CI — macOS universal2 + Windows 自动构建 |

## 许可证

MIT License
