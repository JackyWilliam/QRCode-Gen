# Windows NSIS 安装器

本目录下的脚本可在 macOS / Linux 本地编译出 Windows 原生 `.exe` 安装器（NSIS 自解压格式）。

Windows 原生 `.exe` 可执行文件（PyInstaller 打包的部分）仍需由 Windows 机器或 GitHub Actions CI 构建，**此脚本只是把 CI 打出的 onedir zip 包装成一键安装器**。

## 前置依赖

```bash
# macOS
brew install makensis

# Linux
sudo apt-get install nsis

# 生成 Logo.ico 所需
pip install Pillow

# 自动拉取 CI artifact 需要
gh auth login   # 只需一次
```

## 使用

**方式 A — 自动拉最新 CI artifact**

```bash
bash installer/build.sh
```

脚本会调用 `gh run list` 找到 `build.yml` workflow 里最新一次 `Windows (x64)` job 成功的 run，
下载其 artifact，解压，生成 Logo.ico，最后调用 `makensis` 编译。

**方式 B — 指定本地 Windows zip**

```bash
WIN_ZIP=dist-release/QRCode\ Gen-windows-x64.zip bash installer/build.sh
```

## 产物

编译成功后输出到项目根目录的 `dist/`：

```
dist/QRCode Gen Setup v<VERSION>.exe
```

其中 `<VERSION>` 自动从 `app.py` 的 `VERSION` 常量读取。

## 安装器行为

- 双语向导（简体中文 / English）
- 默认安装路径 `C:\Program Files\QRCode Gen\`
- 三个组件（主程序必装、开始菜单快捷方式、桌面快捷方式）
- 注册「程序和功能」标准卸载项
- 自带 `Uninstall.exe`

## 脚本修改

`installer.nsi` 里 `APP_VERSION` / `SOURCE_DIR` / `ICON_FILE` 都可通过 `-D` 参数覆盖。`build.sh` 会自动注入这三个值。
