"""i18n — 系统语言检测 + 翻译表"""

from __future__ import annotations
import locale
import subprocess

_STRINGS: dict[str, dict[str, str]] = {
    # ── 通用 ──────────────────────────────────────────────────────
    "app_title":          {"zh": "QRCode Gen",       "en": "QRCode Gen"},
    "preview":            {"zh": "预览",              "en": "Preview"},
    "enter_content":      {"zh": "请填写内容",         "en": "Enter content"},
    "preview_updated":    {"zh": "✓ 预览已更新",       "en": "✓ Preview updated"},
    "error_prefix":       {"zh": "错误：",             "en": "Error: "},

    # ── 左侧标题 ──────────────────────────────────────────────────
    "content_type":       {"zh": "内容类型",           "en": "Content Type"},
    "module_style":       {"zh": "模块样式",           "en": "Module Style"},
    "colors":             {"zh": "颜色",               "en": "Colors"},
    "center_icon":        {"zh": "中心 Icon",          "en": "Center Icon"},
    "icon_size":          {"zh": "Icon 大小",          "en": "Icon Size"},
    "ec_level":           {"zh": "容错级别",           "en": "Error Correction"},
    "ec_locked":          {"zh": "  Icon 已选 → 已锁定为 H",
                           "en": "  Icon set → locked to H"},
    "export":             {"zh": "导出",               "en": "Export"},

    # ── 样式 ──────────────────────────────────────────────────────
    "style_square":       {"zh": "方块",               "en": "Square"},
    "style_round":        {"zh": "圆点",               "en": "Circle"},
    "style_rounded":      {"zh": "圆角方块",            "en": "Rounded"},
    "style_horizontal":   {"zh": "横条",               "en": "H-Bars"},
    "style_vertical":     {"zh": "竖条",               "en": "V-Bars"},

    # ── 颜色按钮 ──────────────────────────────────────────────────
    "fg_color":           {"zh": "前景色",             "en": "Foreground"},
    "gradient":           {"zh": "渐变色",             "en": "Gradient"},
    "gradient_end":       {"zh": "渐变终止色",          "en": "Gradient End"},
    "bg_color":           {"zh": "背景色",             "en": "Background"},

    # ── Icon ──────────────────────────────────────────────────────
    "choose_image":       {"zh": "选择图片",            "en": "Choose Image"},
    "clear":              {"zh": "清除",               "en": "Clear"},
    "not_selected":       {"zh": "未选择",             "en": "Not selected"},

    # ── 导出 ──────────────────────────────────────────────────────
    "save_png":           {"zh": "保存 PNG",           "en": "Save PNG"},
    "save_svg":           {"zh": "保存 SVG",           "en": "Save SVG"},
    "export_success":     {"zh": "导出成功",            "en": "Exported"},
    "export_saved_to":    {"zh": "已保存到：\n",        "en": "Saved to:\n"},
    "export_failed":      {"zh": "导出失败",            "en": "Export Failed"},
    "no_preview_yet":     {"zh": "请先生成二维码预览",   "en": "Generate a preview first"},
    "tip":                {"zh": "提示",               "en": "Notice"},

    # ── 图片质量 ──────────────────────────────────────────────────
    "image_quality":      {"zh": "图片质量",           "en": "Image Quality"},
    "quality_low":        {"zh": "低",                "en": "Low"},
    "quality_medium":     {"zh": "中",                "en": "Med"},
    "quality_high":       {"zh": "高",                "en": "High"},
    "quality_ultra":      {"zh": "超高",              "en": "Ultra"},

    # ── 标签页名 ──────────────────────────────────────────────────
    "tab_url":            {"zh": "网址",    "en": "URL"},
    "tab_text":           {"zh": "文字",    "en": "Text"},
    "tab_wifi":           {"zh": "WiFi",    "en": "WiFi"},
    "tab_email":          {"zh": "邮件",    "en": "Email"},
    "tab_phone":          {"zh": "电话",    "en": "Phone"},
    "tab_vcard":          {"zh": "名片",    "en": "vCard"},

    # ── URL 面板 ──────────────────────────────────────────────────
    "url_label":          {"zh": "网址",               "en": "URL"},
    "url_placeholder":    {"zh": "https://example.com","en": "https://example.com"},

    # ── 文字面板 ──────────────────────────────────────────────────
    "text_label":         {"zh": "文字内容",            "en": "Text content"},

    # ── WiFi 面板 ──────────────────────────────────────────────────
    "wifi_ssid":          {"zh": "网络名称",            "en": "Network"},
    "wifi_ssid_ph":       {"zh": "SSID",               "en": "SSID"},
    "wifi_pwd":           {"zh": "密码",               "en": "Password"},
    "wifi_pwd_ph":        {"zh": "password",           "en": "password"},
    "wifi_security":      {"zh": "加密",               "en": "Security"},
    "wifi_hidden":        {"zh": "隐藏网络",            "en": "Hidden network"},
    "wifi_none":          {"zh": "无",                 "en": "None"},

    # ── 邮件面板 ──────────────────────────────────────────────────
    "email_to":           {"zh": "收件人",             "en": "To"},
    "email_to_ph":        {"zh": "user@example.com",   "en": "user@example.com"},
    "email_subject":      {"zh": "主题",               "en": "Subject"},
    "email_body":         {"zh": "正文",               "en": "Body"},

    # ── 电话面板 ──────────────────────────────────────────────────
    "phone_number":       {"zh": "电话号码",            "en": "Phone number"},
    "phone_number_ph":    {"zh": "+86 138 0000 0000",  "en": "+1 555 000 0000"},
    "phone_call":         {"zh": "拨打电话",            "en": "Call"},
    "phone_sms":          {"zh": "发短信",             "en": "SMS"},
    "phone_msg_hint":     {"zh": "短信内容（仅短信模式）", "en": "Message (SMS only)"},

    # ── 名片面板 ──────────────────────────────────────────────────
    "vcard_name":         {"zh": "姓名",               "en": "Name"},
    "vcard_name_ph":      {"zh": "张三",               "en": "John Doe"},
    "vcard_phone":        {"zh": "电话",               "en": "Phone"},
    "vcard_email":        {"zh": "邮件",               "en": "Email"},
    "vcard_org":          {"zh": "公司",               "en": "Company"},
    "vcard_url":          {"zh": "网址",               "en": "URL"},
}


def _detect_lang() -> str:
    """检测系统语言，返回 'zh' 或 'en'。"""
    # macOS: 读取 AppleLanguages 偏好设置
    try:
        out = subprocess.run(
            ["defaults", "read", "-g", "AppleLanguages"],
            capture_output=True, text=True, timeout=2,
        ).stdout
        # 只取第一个语言项，避免次选语言干扰判断
        for token in out.split('"'):
            token = token.strip()
            if token and not token.startswith("(") and not token.startswith(","):
                return "zh" if token.lower().startswith("zh") else "en"
    except Exception:
        pass

    # 通用 fallback: locale
    try:
        code = locale.getdefaultlocale()[0] or ""
        if code.lower().startswith("zh"):
            return "zh"
    except Exception:
        pass

    return "en"


# 模块加载时确定一次，整个运行期间不变
LANG: str = _detect_lang()


def t(key: str) -> str:
    """返回当前系统语言对应的字符串，找不到 key 则原样返回 key。"""
    entry = _STRINGS.get(key)
    if entry is None:
        return key
    return entry.get(LANG, entry.get("en", key))
