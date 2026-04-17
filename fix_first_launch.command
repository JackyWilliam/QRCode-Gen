#!/bin/bash
# 如果 QRCode Gen 无法打开，请双击此文件运行
# If QRCode Gen won't open, double-click this file to run

APP="/Applications/QRCode Gen.app"

echo "========================================"
echo "  QRCode Gen — 首次启动修复工具"
echo "  QRCode Gen — First Launch Fix"
echo "========================================"
echo ""

if [ ! -d "$APP" ]; then
    echo "未找到 QRCode Gen.app，请先运行 .pkg 安装包完成安装。"
    echo "QRCode Gen.app not found. Please install it via the .pkg file first."
    echo ""
    read -p "按回车键关闭 / Press Enter to close..."
    exit 1
fi

echo "正在移除系统隔离标记，需要输入开机密码："
echo "Removing system quarantine. Your login password is required:"
echo ""

sudo xattr -cr "$APP"

if [ $? -eq 0 ]; then
    echo ""
    echo "完成！现在可以直接双击打开 QRCode Gen 了。"
    echo "Done! You can now open QRCode Gen normally."
else
    echo ""
    echo "出错了，请尝试手动右键点击 App → 打开。"
    echo "Something went wrong. Try right-clicking the app and selecting Open."
fi

echo ""
read -p "按回车键关闭 / Press Enter to close..."
