#!/bin/bash
set -e
cd "$(dirname "$0")"

echo ">>> 安装依赖..."
pip3 install -r requirements.txt -q

# 获取 customtkinter 资源路径
CTK_PATH=$(python3 -c "import customtkinter, os; print(os.path.dirname(customtkinter.__file__))")

echo ">>> 打包为 .app (native arch)..."
pyinstaller \
  --name "QRCode Gen" \
  --windowed \
  --onedir \
  --noconfirm \
  --clean \
  --add-data "${CTK_PATH}:customtkinter" \
  --add-data "Logo.png:." \
  --add-data "i18n.py:." \
  --add-data "qr_engine.py:." \
  --hidden-import "PIL._tkinter_finder" \
  --hidden-import "qrcode.image.styledpil" \
  --hidden-import "qrcode.image.styles.moduledrawers.pil" \
  --icon "Logo.png" \
  app.py

# 写入版本号和著作权到 Info.plist
APP_PLIST="dist/QRCode Gen.app/Contents/Info.plist"
VERSION=$(python3 -c "import re; print(re.search(r'VERSION\s*=\s*\"([^\"]+)\"', open('app.py').read()).group(1))")
_plist_set() { /usr/libexec/PlistBuddy -c "Set $1 $2" "${APP_PLIST}" 2>/dev/null \
               || /usr/libexec/PlistBuddy -c "Add $1 string $2" "${APP_PLIST}"; }
_plist_set ":CFBundleShortVersionString" "${VERSION}"
_plist_set ":CFBundleVersion"           "${VERSION}"
_plist_set ":NSHumanReadableCopyright"  "Copyright © 2026 Yijie Ding. MIT License."

# 打包为 .pkg 安装包
echo ">>> 生成 .pkg 安装包..."
pkgbuild \
  --component "dist/QRCode Gen.app" \
  --install-location /Applications \
  --version "${VERSION}" \
  --identifier "com.yijie.qrcodegen" \
  "dist/QRCode Gen.pkg"

# 给 .pkg 设置自定义 icon
python3 - <<'PYEOF'
from AppKit import NSWorkspace, NSImage
icon = NSImage.alloc().initWithContentsOfFile_("Logo.png")
NSWorkspace.sharedWorkspace().setIcon_forFile_options_(icon, "dist/QRCode Gen.pkg", 0)
PYEOF

ARCH=$(uname -m)
echo ""
echo "✅ 打包完成"
echo "   .app  → dist/QRCode Gen.app"
echo "   .pkg  → dist/QRCode Gen.pkg  (发给别人用这个)"
echo ""
echo "   架构：${ARCH}"
echo ""
echo "   收到方双击 .pkg → 按提示安装 → 在 /Applications 找到 QRCode Gen"
