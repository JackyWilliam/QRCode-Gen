#!/bin/bash
# 在 macOS / Linux 本地编译 Windows NSIS 安装器。
#
# 前置：
#   brew install makensis        # macOS
#   sudo apt-get install nsis     # Linux
#   pip install Pillow            # 生成 Logo.ico
#   gh auth status                # 如需自动拉 CI artifact
#
# 用法：
#   bash installer/build.sh                              # 自动拉最新 CI Windows artifact
#   WIN_ZIP=dist/foo.zip bash installer/build.sh         # 使用本地已有的 Windows onedir zip

set -e
cd "$(dirname "$0")/.."

INSTALLER_DIR="installer"
WORK_DIR="$(mktemp -d -t qrgen-installer.XXXXXX)"
trap 'rm -rf "$WORK_DIR"' EXIT

VERSION=$(python3 -c "import re; print(re.search(r'VERSION\s*=\s*\"([^\"]+)\"', open('app.py').read()).group(1))")
echo ">>> Building installer for v${VERSION}"

# 1. 生成 Logo.ico
ICON="$WORK_DIR/Logo.ico"
python3 - <<PYEOF
from PIL import Image
src = Image.open("Logo.iconset/icon_512x512.png").convert("RGBA")
src.save("${ICON}", format="ICO", sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
PYEOF
echo ">>> Logo.ico -> $(du -h "$ICON" | cut -f1)"

# 2. 获取 Windows onedir（优先用 WIN_ZIP 环境变量，否则从 CI 最新成功 run 拉）
if [ -n "$WIN_ZIP" ]; then
  echo ">>> Using local Windows zip: $WIN_ZIP"
  cp "$WIN_ZIP" "$WORK_DIR/win.zip"
else
  echo ">>> Fetching latest successful Windows artifact via gh..."
  RUN_ID=$(gh run list --workflow=build.yml --json databaseId,conclusion,jobs \
           --jq '[.[] | select(.jobs[] | select(.name=="Windows (x64)" and .conclusion=="success"))] | .[0].databaseId')
  if [ -z "$RUN_ID" ] || [ "$RUN_ID" = "null" ]; then
    echo "ERROR: 未找到成功的 Windows CI run。请先跑 'gh workflow run build.yml --ref main' 或手动提供 WIN_ZIP=..." >&2
    exit 1
  fi
  echo ">>> Using run ID: $RUN_ID"
  gh run download "$RUN_ID" --name QRCode-Gen-Windows --dir "$WORK_DIR/"
  mv "$WORK_DIR/QRCode Gen-windows-x64.zip" "$WORK_DIR/win.zip"
fi

# 3. 解压 onedir
echo ">>> Extracting..."
unzip -q "$WORK_DIR/win.zip" -d "$WORK_DIR/extracted"
SOURCE_DIR="$WORK_DIR/extracted/QRCode Gen"
if [ ! -d "$SOURCE_DIR" ]; then
  echo "ERROR: 解压后未找到 'QRCode Gen' 目录，zip 结构异常" >&2
  ls -la "$WORK_DIR/extracted/" >&2
  exit 1
fi

# 4. 调用 makensis（OutFile 在 .nsi 里定义，产物会落在 installer/ 目录）
echo ">>> Compiling NSIS..."
makensis \
  -DAPP_VERSION="${VERSION}" \
  -DSOURCE_DIR="${SOURCE_DIR}" \
  -DICON_FILE="${ICON}" \
  "${INSTALLER_DIR}/installer.nsi"

SRC_EXE="${INSTALLER_DIR}/QRCode Gen Setup v${VERSION}.exe"
mkdir -p dist
OUT_EXE="dist/QRCode Gen Setup v${VERSION}.exe"
mv "$SRC_EXE" "$OUT_EXE"

if [ -f "$OUT_EXE" ]; then
  SIZE=$(du -h "$OUT_EXE" | cut -f1)
  echo ""
  echo "✅ Installer 生成成功"
  echo "   -> $OUT_EXE ($SIZE)"
else
  echo "ERROR: makensis 跑完但产物未找到" >&2
  exit 1
fi
