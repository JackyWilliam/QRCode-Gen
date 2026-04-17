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
  --icon "Logo.icns" \
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

# 组装分发包
echo ">>> 组装分发包..."
DIST_DIR="dist/QRCode Gen v${VERSION}"
rm -rf "${DIST_DIR}"
mkdir -p "${DIST_DIR}"
cp "dist/QRCode Gen.pkg"        "${DIST_DIR}/"
cp "fix_first_launch.command"   "${DIST_DIR}/如果无法打开 · If App Won't Open.command"
cp "README.md"                  "${DIST_DIR}/"
cp "READMECN.md"                "${DIST_DIR}/"

# 压缩
cd dist
zip -r "QRCode Gen v${VERSION} macOS.zip" "QRCode Gen v${VERSION}" --quiet
cd ..

ARCH=$(uname -m)
echo ""
echo "✅ 打包完成"
echo "   .pkg  → dist/QRCode Gen.pkg"
echo "   .zip  → dist/QRCode Gen v${VERSION} macOS.zip"
echo ""
echo "   架构：${ARCH}"
