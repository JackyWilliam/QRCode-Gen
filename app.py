"""QRCode Gen — Mac 二维码生成器"""

from __future__ import annotations

import sys
import threading
import tkinter as tk
import tkinter.filedialog as filedialog
import tkinter.messagebox as messagebox
from pathlib import Path
from typing import Optional

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageTk

from color_picker import ColorTile

from i18n import LANG, t
from qr_engine import QRCodeEngine

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

VERSION   = "1.2.0"
COPYRIGHT = "Copyright © 2026 Yijie Ding. MIT License."

QUALITY_KEYS  = ["quality_low", "quality_medium", "quality_high", "quality_ultra"]
QUALITY_SIZES = [6, 10, 16, 36]   # box_size 对应像素密度（超高保证最小 QR ≥1044px）

STYLES     = ["square", "round", "rounded_square", "horizontal", "vertical", "custom"]
STYLE_KEYS = ["style_square", "style_round", "style_rounded", "style_horizontal", "style_vertical", "style_custom"]
STYLE_ICONS = ["▪", "●", "◼", "≡", "⋮", "✦"]
EC_LEVELS  = ["L", "M", "Q", "H"]
EC_DESC    = {"L": "7 %", "M": "15 %", "Q": "25 %", "H": "30 %"}
TAB_KEYS   = ["tab_url", "tab_text", "tab_wifi", "tab_email", "tab_phone", "tab_vcard"]

SIDEBAR_W     = 300 if LANG == "zh" else 340
TAB_FONT_SIZE = 12 if LANG == "zh" else 11

# 色盘 —— light / dark 自适应
_CARD   = ("gray90",  "#2b2b2b")   # 卡片背景
_CARD2  = ("gray82",  "#333333")   # 次级卡片
_ACCENT = "#3B82F6"                # 强调蓝
_RED    = "#EF4444"


# ─── 通用小组件 ────────────────────────────────────────────────────────

def _card(parent, **kw) -> ctk.CTkFrame:
    """圆角卡片容器。"""
    return ctk.CTkFrame(parent, corner_radius=12, fg_color=_CARD, **kw)


def _label(parent, text_key: str, size: int = 13, bold: bool = False, **kw) -> ctk.CTkLabel:
    font = ctk.CTkFont(size=size, weight="bold" if bold else "normal")
    return ctk.CTkLabel(parent, text=t(text_key), font=font, **kw)


# ─── 内容类型面板 ──────────────────────────────────────────────────────

class _Row(ctk.CTkFrame):
    """标签 + 单行输入。"""
    def __init__(self, master, label: str, ph: str = "", trace=None, **kw):
        super().__init__(master, fg_color="transparent", **kw)
        ctk.CTkLabel(self, text=label, width=72, anchor="e",
                     font=ctk.CTkFont(size=12), text_color="gray").pack(side="left", padx=(0, 8))
        self.var = tk.StringVar()
        if trace:
            self.var.trace_add("write", lambda *_: trace())
        ctk.CTkEntry(self, textvariable=self.var, placeholder_text=ph,
                     height=30, corner_radius=8).pack(side="left", fill="x", expand=True)

    @property
    def value(self) -> str:
        return self.var.get().strip()


class URLPanel(ctk.CTkFrame):
    def __init__(self, master, on_change, **kw):
        super().__init__(master, fg_color="transparent", **kw)
        ctk.CTkEntry(self, textvariable=(v := tk.StringVar()),
                     placeholder_text=t("url_placeholder"),
                     height=36, corner_radius=8,
                     font=ctk.CTkFont(size=13)).pack(fill="x", pady=4)
        v.trace_add("write", lambda *_: on_change())
        self._var = v

    def get_data(self) -> str:
        v = self._var.get().strip()
        if v and not v.startswith(("http://", "https://", "ftp://")):
            v = "https://" + v
        return v


class TextPanel(ctk.CTkFrame):
    def __init__(self, master, on_change, **kw):
        super().__init__(master, fg_color="transparent", **kw)
        self._box = ctk.CTkTextbox(self, height=76, wrap="word",
                                    corner_radius=8, font=ctk.CTkFont(size=13))
        self._box.pack(fill="x", pady=4)
        self._box.bind("<KeyRelease>", lambda _: on_change())

    def get_data(self) -> str:
        return self._box.get("1.0", "end").strip()


class WiFiPanel(ctk.CTkFrame):
    def __init__(self, master, on_change, **kw):
        super().__init__(master, fg_color="transparent", **kw)
        self._ssid = _Row(self, t("wifi_ssid"), t("wifi_ssid_ph"), trace=on_change)
        self._ssid.pack(fill="x", pady=3)
        self._pwd  = _Row(self, t("wifi_pwd"), t("wifi_pwd_ph"), trace=on_change)
        self._pwd.pack(fill="x", pady=3)
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", pady=3)
        ctk.CTkLabel(row, text=t("wifi_security"), width=72, anchor="e",
                     font=ctk.CTkFont(size=12), text_color="gray").pack(side="left", padx=(0, 8))
        self._sec = ctk.CTkSegmentedButton(
            row, values=["WPA/WPA2", "WEP", t("wifi_none")],
            command=lambda _: on_change(), font=ctk.CTkFont(size=12))
        self._sec.set("WPA/WPA2")
        self._sec.pack(side="left")
        self._hidden = tk.BooleanVar()
        ctk.CTkCheckBox(self, text=t("wifi_hidden"), variable=self._hidden,
                        command=on_change, font=ctk.CTkFont(size=12)).pack(anchor="w", pady=4)

    def get_data(self) -> str:
        s = self._ssid.value
        if not s:
            return ""
        none_label = t("wifi_none")
        sec = {"WPA/WPA2": "WPA", "WEP": "WEP", none_label: "nopass"}.get(self._sec.get(), "WPA")
        return f"WIFI:T:{sec};S:{s};P:{self._pwd.value};H:{'true' if self._hidden.get() else 'false'};;"


class EmailPanel(ctk.CTkFrame):
    def __init__(self, master, on_change, **kw):
        super().__init__(master, fg_color="transparent", **kw)
        self._to  = _Row(self, t("email_to"), t("email_to_ph"), trace=on_change)
        self._to.pack(fill="x", pady=3)
        self._sub = _Row(self, t("email_subject"), "", trace=on_change)
        self._sub.pack(fill="x", pady=3)
        ctk.CTkLabel(self, text=t("email_body"), anchor="w",
                     font=ctk.CTkFont(size=12), text_color="gray").pack(anchor="w")
        self._body = ctk.CTkTextbox(self, height=48, wrap="word",
                                     corner_radius=8, font=ctk.CTkFont(size=12))
        self._body.pack(fill="x")
        self._body.bind("<KeyRelease>", lambda _: on_change())

    def get_data(self) -> str:
        to = self._to.value
        if not to:
            return ""
        import urllib.parse
        sub  = urllib.parse.quote(self._sub.value)
        body = urllib.parse.quote(self._body.get("1.0", "end").strip())
        return f"mailto:{to}?subject={sub}&body={body}"


class PhonePanel(ctk.CTkFrame):
    def __init__(self, master, on_change, **kw):
        super().__init__(master, fg_color="transparent", **kw)
        self._num = _Row(self, t("phone_number"), t("phone_number_ph"), trace=on_change)
        self._num.pack(fill="x", pady=3)
        self._mode = ctk.CTkSegmentedButton(
            self, values=[t("phone_call"), t("phone_sms")],
            command=lambda _: on_change(), font=ctk.CTkFont(size=12))
        self._mode.set(t("phone_call"))
        self._mode.pack(anchor="w", pady=6)
        ctk.CTkLabel(self, text=t("phone_msg_hint"), anchor="w",
                     font=ctk.CTkFont(size=11), text_color="gray").pack(anchor="w")
        self._msg = ctk.CTkTextbox(self, height=44, wrap="word",
                                    corner_radius=8, font=ctk.CTkFont(size=12))
        self._msg.pack(fill="x")
        self._msg.bind("<KeyRelease>", lambda _: on_change())

    def get_data(self) -> str:
        num = self._num.value
        if not num:
            return ""
        if self._mode.get() == t("phone_call"):
            return f"tel:{num}"
        return f"smsto:{num}:{self._msg.get('1.0', 'end').strip()}"


class VCardPanel(ctk.CTkFrame):
    def __init__(self, master, on_change, **kw):
        super().__init__(master, fg_color="transparent", **kw)
        fields = [
            (t("vcard_name"),  t("vcard_name_ph")),
            (t("vcard_phone"), ""),
            (t("vcard_email"), ""),
            (t("vcard_org"),   ""),
            (t("vcard_url"),   "https://"),
        ]
        self._rows: list[_Row] = []
        for lbl, ph in fields:
            r = _Row(self, lbl, ph, trace=on_change)
            r.pack(fill="x", pady=2)
            self._rows.append(r)

    def get_data(self) -> str:
        name = self._rows[0].value
        if not name:
            return ""
        keys = ["FN", "TEL", "EMAIL", "ORG", "URL"]
        lines = ["BEGIN:VCARD", "VERSION:3.0"]
        for key, row in zip(keys, self._rows):
            if row.value:
                lines.append(f"{key}:{row.value}")
        lines.append("END:VCARD")
        return "\n".join(lines)


# ─── 主应用 ────────────────────────────────────────────────────────────

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(t("app_title"))
        self.resizable(True, True)
        self.minsize(820, 600)
        # 启动时按屏幕 85% 居中显示
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        w  = int(sw * 0.85)
        h  = int(sh * 0.85)
        x  = (sw - w) // 2
        y  = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

        self._engine = QRCodeEngine()
        self._icon_path: Optional[str] = None
        self._shape_path: Optional[str] = None
        self._current_image: Optional[Image.Image] = None
        self._debounce_id: Optional[str] = None
        self._resize_id: Optional[str] = None

        self._fg1 = "#000000"
        self._fg2: Optional[str] = None
        self._bg  = "#FFFFFF"
        self._gradient_on = tk.BooleanVar(value=False)

        self._set_dock_icon()
        self._setup_about_menu()
        self._build_ui()
        self.update_idletasks()
        self._schedule_preview()

    # ── About 面板 ───────────────────────────────────────────────
    def _setup_about_menu(self):
        """拦截 macOS 应用菜单的 About 项，注入版本和版权信息。"""
        try:
            self.createcommand("::tk::mac::ShowAbout", self._show_about)
        except Exception:
            pass

    def _show_about(self):
        try:
            from AppKit import NSApplication
            NSApplication.sharedApplication().orderFrontStandardAboutPanelWithOptions_({
                "ApplicationName": "QRCode Gen",
                "ApplicationVersion": VERSION,
                "Version": VERSION,
                "Copyright": COPYRIGHT,
            })
        except Exception:
            messagebox.showinfo(
                "About QRCode Gen",
                f"QRCode Gen  v{VERSION}\n\n{COPYRIGHT}",
            )

    # ── 窗口/任务栏/Dock 图标 ────────────────────────────────────
    def _set_dock_icon(self):
        icon_path = Path(__file__).parent / "Logo.png"
        if not icon_path.exists() and hasattr(sys, "_MEIPASS"):
            candidate = Path(sys._MEIPASS) / "Logo.png"
            if candidate.exists():
                icon_path = candidate
        if not icon_path.exists():
            return
        # 跨平台：iconphoto 设窗口/任务栏图标（Tk 8.6+，Win/Linux/macOS 都生效）
        try:
            self._icon_photo = ImageTk.PhotoImage(Image.open(icon_path))
            self.iconphoto(True, self._icon_photo)
        except Exception:
            pass
        # macOS 额外：设置 Dock 图标（AppKit 仅 macOS 可用）
        if sys.platform == "darwin":
            try:
                from AppKit import NSApplication, NSImage
                img = NSImage.alloc().initWithContentsOfFile_(str(icon_path))
                NSApplication.sharedApplication().setApplicationIconImage_(img)
            except Exception:
                pass

    # ── 骨架 ─────────────────────────────────────────────────────
    def _build_ui(self):
        self.configure(padx=0, pady=0)
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        root = ctk.CTkFrame(self, fg_color=_CARD2, corner_radius=0)
        root.grid(row=0, column=0, sticky="nsew")
        root.rowconfigure(0, weight=1)
        root.columnconfigure(0, weight=0)
        root.columnconfigure(1, weight=1)

        # ── 左侧控制栏 ────────────────────────────────────────
        sidebar = ctk.CTkScrollableFrame(
            root, width=SIDEBAR_W, corner_radius=0,
            fg_color=("gray92", "#242424"),
            scrollbar_button_color=("gray75", "#444"),
        )
        sidebar.grid(row=0, column=0, sticky="ns")

        # 顶部 Logo 区
        header = ctk.CTkFrame(sidebar, fg_color="transparent", height=56)
        header.pack(fill="x", padx=16, pady=(16, 4))
        header.pack_propagate(False)
        ctk.CTkLabel(
            header, text="QRCode Gen",
            font=ctk.CTkFont(size=18, weight="bold"),
            anchor="w",
        ).pack(side="left", fill="y")
        ctk.CTkButton(
            header, text="ⓘ", width=28, height=28, corner_radius=14,
            fg_color="transparent", hover_color=("gray80", "#3a3a3a"),
            text_color=("gray40", "gray70"),
            font=ctk.CTkFont(size=16),
            command=self._show_about,
        ).pack(side="right")

        # 分割线
        ctk.CTkFrame(sidebar, height=1, fg_color=("gray80", "#383838")).pack(
            fill="x", padx=16, pady=(0, 12))

        self._build_sidebar(sidebar)

        # ── 右侧预览区 ────────────────────────────────────────
        preview_area = ctk.CTkFrame(root, fg_color=_CARD2, corner_radius=0)
        preview_area.grid(row=0, column=1, sticky="nsew")
        preview_area.rowconfigure(1, weight=1)
        preview_area.columnconfigure(0, weight=1)

        self._build_preview(preview_area)

    # ── 左侧内容 ──────────────────────────────────────────────────
    def _build_sidebar(self, parent):
        # ── 1. 内容类型 ───────────────────────────────────────
        self._section_label(parent, "content_type")
        tab_names = [t(k) for k in TAB_KEYS]
        self._tabs = ctk.CTkTabview(
            parent, height=190, corner_radius=10,
            fg_color=_CARD,
            segmented_button_fg_color=("gray82", "#333"),
        )
        self._tabs.pack(fill="x", padx=16, pady=(0, 16))
        for name in tab_names:
            self._tabs.add(name)
        try:
            self._tabs._segmented_button.configure(font=ctk.CTkFont(size=TAB_FONT_SIZE))
        except Exception:
            pass

        oc = self._schedule_preview
        self._panels: dict[str, object] = {
            t("tab_url"):   URLPanel(self._tabs.tab(t("tab_url")), oc),
            t("tab_text"):  TextPanel(self._tabs.tab(t("tab_text")), oc),
            t("tab_wifi"):  WiFiPanel(self._tabs.tab(t("tab_wifi")), oc),
            t("tab_email"): EmailPanel(self._tabs.tab(t("tab_email")), oc),
            t("tab_phone"): PhonePanel(self._tabs.tab(t("tab_phone")), oc),
            t("tab_vcard"): VCardPanel(self._tabs.tab(t("tab_vcard")), oc),
        }
        for panel in self._panels.values():
            panel.pack(fill="x", padx=6, pady=6)
        self._tabs.configure(command=lambda *_: self._schedule_preview())

        # ── 2. 模块样式 ───────────────────────────────────────
        self._section_label(parent, "module_style")
        style_card = _card(parent)
        style_card.pack(fill="x", padx=16, pady=(0, 16))

        self._style_var = tk.StringVar(value=STYLES[0])
        btn_row1 = ctk.CTkFrame(style_card, fg_color="transparent")
        btn_row1.pack(fill="x", padx=10, pady=(10, 4))
        btn_row2 = ctk.CTkFrame(style_card, fg_color="transparent")
        btn_row2.pack(fill="x", padx=10, pady=(0, 10))

        self._style_btns: list[ctk.CTkButton] = []
        for i, (s, icon, key) in enumerate(zip(STYLES, STYLE_ICONS, STYLE_KEYS)):
            row = btn_row1 if i < 3 else btn_row2
            btn = ctk.CTkButton(
                row, text=f"{icon}  {t(key)}",
                width=74, height=34, corner_radius=8,
                font=ctk.CTkFont(size=12),
                fg_color=_ACCENT if s == STYLES[0] else ("gray80", "#3a3a3a"),
                hover_color=(_ACCENT, _ACCENT),
                text_color=("white" if s == STYLES[0] else ("gray20", "gray80")),
                command=lambda val=s: self._on_style(val),
            )
            btn.pack(side="left", padx=3)
            self._style_btns.append(btn)

        self._shape_area = ctk.CTkFrame(style_card, fg_color="transparent")
        shape_btn_row = ctk.CTkFrame(self._shape_area, fg_color="transparent")
        shape_btn_row.pack(fill="x")
        ctk.CTkButton(
            shape_btn_row, text=t("choose_shape"),
            height=30, corner_radius=8, font=ctk.CTkFont(size=12),
            command=self._pick_shape,
        ).pack(side="left")
        ctk.CTkButton(
            shape_btn_row, text=t("clear"),
            width=56, height=30, corner_radius=8,
            fg_color=("gray75", "#3a3a3a"),
            hover_color=(_RED, _RED),
            font=ctk.CTkFont(size=12),
            command=self._clear_shape,
        ).pack(side="left", padx=(6, 0))

        self._shape_name_label = ctk.CTkLabel(
            self._shape_area, text=t("shape_hint"),
            font=ctk.CTkFont(size=11), text_color="gray", anchor="w")
        self._shape_name_label.pack(fill="x", pady=(4, 0))
        self._shape_thumb_label = ctk.CTkLabel(self._shape_area, text="")
        self._shape_thumb_label.pack(pady=(2, 0))

        # ── 3. 颜色 ───────────────────────────────────────────
        self._section_label(parent, "colors")
        color_card = _card(parent)
        color_card.pack(fill="x", padx=16, pady=(0, 16))

        color_inner = ctk.CTkFrame(color_card, fg_color="transparent")
        color_inner.pack(fill="x", padx=12, pady=12)

        # 前景 / 背景 色块行
        fg_bg_row = ctk.CTkFrame(color_inner, fg_color="transparent")
        fg_bg_row.pack(fill="x")

        # 二维码颜色
        fg_col = ctk.CTkFrame(fg_bg_row, fg_color="transparent")
        fg_col.pack(side="left", expand=True)
        ctk.CTkLabel(fg_col, text=t("fg_color"),
                     font=ctk.CTkFont(size=11), text_color="gray").pack()
        self._tile_fg = ColorTile(fg_col, self._fg1, self._on_fg1_change, size=52)
        self._tile_fg.pack(pady=(4, 0))

        # 渐变终止色（默认隐藏，紧邻二维码颜色）
        grad_col = ctk.CTkFrame(fg_bg_row, fg_color="transparent")
        grad_col.pack(side="left", expand=True)
        ctk.CTkLabel(grad_col, text=t("gradient_end"),
                     font=ctk.CTkFont(size=11), text_color="gray").pack()
        self._tile_fg2 = ColorTile(grad_col, "#3B82F6", self._on_fg2_change, size=52)
        self._tile_fg2.pack(pady=(4, 0))
        self._grad_col = grad_col   # 用于显示/隐藏

        # 背景
        bg_col = ctk.CTkFrame(fg_bg_row, fg_color="transparent")
        bg_col.pack(side="left", expand=True)
        ctk.CTkLabel(bg_col, text=t("bg_color"),
                     font=ctk.CTkFont(size=11), text_color="gray").pack()
        self._tile_bg = ColorTile(bg_col, self._bg, self._on_bg_change, size=52)
        self._tile_bg.pack(pady=(4, 0))
        self._bg_col = bg_col   # 用于渐变开启时 pack before 定位

        # 渐变开关 —— 与上方「渐变终止色」列对齐
        grad_toggle_row = ctk.CTkFrame(color_inner, fg_color="transparent")
        grad_toggle_row.pack(fill="x", pady=(12, 0))
        grad_toggle_row.columnconfigure(0, weight=1, uniform="col")
        grad_toggle_row.columnconfigure(1, weight=1, uniform="col")
        grad_toggle_row.columnconfigure(2, weight=1, uniform="col")

        sw_wrap = ctk.CTkFrame(grad_toggle_row, fg_color="transparent")
        sw_wrap.grid(row=0, column=1)

        ctk.CTkLabel(
            sw_wrap, text=t("gradient"),
            font=ctk.CTkFont(size=11), text_color="gray",
        ).pack(side="left", padx=(0, 8))
        ctk.CTkSwitch(
            sw_wrap, text="",
            variable=self._gradient_on,
            command=self._on_gradient_toggle,
            switch_width=40, switch_height=22,
            progress_color="#34C759",
            fg_color=("#D1D5DB", "#3a3a3a"),
            button_color="white",
            button_hover_color="white",
        ).pack(side="left")

        self._toggle_gradient_ui(False)

        # ── 4. 中心 Icon ──────────────────────────────────────
        self._section_label(parent, "center_icon")
        icon_card = _card(parent)
        icon_card.pack(fill="x", padx=16, pady=(0, 16))

        icon_inner = ctk.CTkFrame(icon_card, fg_color="transparent")
        icon_inner.pack(fill="x", padx=12, pady=12)

        icon_btn_row = ctk.CTkFrame(icon_inner, fg_color="transparent")
        icon_btn_row.pack(fill="x")
        ctk.CTkButton(
            icon_btn_row, text=t("choose_image"),
            height=32, corner_radius=8, font=ctk.CTkFont(size=12),
            command=self._pick_icon,
        ).pack(side="left")
        ctk.CTkButton(
            icon_btn_row, text=t("clear"),
            width=64, height=32, corner_radius=8,
            fg_color=("gray75", "#3a3a3a"),
            hover_color=(_RED, _RED),
            font=ctk.CTkFont(size=12),
            command=self._clear_icon,
        ).pack(side="left", padx=(8, 0))

        self._icon_name_label = ctk.CTkLabel(
            icon_inner, text=t("not_selected"),
            font=ctk.CTkFont(size=11), text_color="gray", anchor="w")
        self._icon_name_label.pack(fill="x", pady=(6, 0))

        # 缩略图
        self._icon_thumb_label = ctk.CTkLabel(icon_inner, text="")
        self._icon_thumb_label.pack(pady=(4, 0))

        ctk.CTkLabel(icon_inner, text=t("icon_size"),
                     font=ctk.CTkFont(size=11), text_color="gray", anchor="w").pack(
                         fill="x", pady=(8, 2))
        self._icon_ratio = ctk.CTkSlider(
            icon_inner, from_=0.10, to=0.30, number_of_steps=20,
            command=lambda _: self._schedule_preview())
        self._icon_ratio.set(0.20)
        self._icon_ratio.pack(fill="x")

        # ── 5. 容错级别 ───────────────────────────────────────
        ec_row = ctk.CTkFrame(parent, fg_color="transparent")
        ec_row.pack(fill="x", padx=16, pady=(0, 4))
        ctk.CTkLabel(ec_row, text=t("ec_level"),
                     font=ctk.CTkFont(size=13, weight="bold")).pack(side="left")
        self._ec_lock_label = ctk.CTkLabel(
            ec_row, text=t("ec_locked"),
            font=ctk.CTkFont(size=11), text_color="#f59e0b")

        ec_card = _card(parent)
        ec_card.pack(fill="x", padx=16, pady=(0, 16))
        ec_inner = ctk.CTkFrame(ec_card, fg_color="transparent")
        ec_inner.pack(fill="x", padx=12, pady=10)

        self._ec_var = tk.StringVar(value="H")
        self._ec_btns: list[ctk.CTkButton] = []
        for lvl in EC_LEVELS:
            btn = ctk.CTkButton(
                ec_inner,
                text=f"{lvl}\n{EC_DESC[lvl]}",
                width=54, height=44, corner_radius=8,
                font=ctk.CTkFont(size=11),
                fg_color=_ACCENT if lvl == "H" else ("gray80", "#3a3a3a"),
                hover_color=(_ACCENT, _ACCENT),
                text_color=("white" if lvl == "H" else ("gray20", "gray80")),
                command=lambda v=lvl: self._on_ec(v),
            )
            btn.pack(side="left", padx=3)
            self._ec_btns.append(btn)

        # ── 6. 图片质量 ───────────────────────────────────────
        self._section_label(parent, "image_quality")
        quality_card = _card(parent)
        quality_card.pack(fill="x", padx=16, pady=(0, 16))
        quality_inner = ctk.CTkFrame(quality_card, fg_color="transparent")
        quality_inner.pack(fill="x", padx=12, pady=10)

        self._quality_idx = 1   # 默认 Medium (box_size=10)
        self._quality_btns: list[ctk.CTkButton] = []
        for i, key in enumerate(QUALITY_KEYS):
            btn = ctk.CTkButton(
                quality_inner,
                text=t(key),
                width=54, height=34, corner_radius=8,
                font=ctk.CTkFont(size=12),
                fg_color=_ACCENT if i == 1 else ("gray80", "#3a3a3a"),
                hover_color=(_ACCENT, _ACCENT),
                text_color=("white" if i == 1 else ("gray20", "gray80")),
                command=lambda idx=i: self._on_quality(idx),
            )
            btn.pack(side="left", padx=3)
            self._quality_btns.append(btn)

        # ── 7. 导出 ───────────────────────────────────────────
        self._section_label(parent, "export")
        export_card = _card(parent)
        export_card.pack(fill="x", padx=16, pady=(0, 20))
        export_inner = ctk.CTkFrame(export_card, fg_color="transparent")
        export_inner.pack(fill="x", padx=12, pady=12)

        ctk.CTkButton(
            export_inner, text=t("save_png"),
            height=36, corner_radius=8,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=lambda: self._export("PNG"),
        ).pack(fill="x", pady=(0, 6))
        ctk.CTkButton(
            export_inner, text=t("save_svg"),
            height=36, corner_radius=8,
            fg_color=("gray75", "#3a3a3a"),
            hover_color=("gray60", "#505050"),
            font=ctk.CTkFont(size=13),
            command=lambda: self._export("SVG"),
        ).pack(fill="x")

    def _section_label(self, parent, key: str):
        ctk.CTkLabel(parent, text=t(key),
                     font=ctk.CTkFont(size=13, weight="bold"),
                     anchor="w").pack(fill="x", padx=16, pady=(4, 6))

    # ── 预览区 ────────────────────────────────────────────────────
    def _build_preview(self, parent):
        # 标题行
        top_bar = ctk.CTkFrame(parent, fg_color="transparent", height=52)
        top_bar.grid(row=0, column=0, sticky="ew", padx=24, pady=(16, 0))
        top_bar.pack_propagate(False)
        ctk.CTkLabel(top_bar, text=t("preview"),
                     font=ctk.CTkFont(size=16, weight="bold"),
                     anchor="w").pack(side="left", fill="y")
        self._status_label = ctk.CTkLabel(
            top_bar, text="", font=ctk.CTkFont(size=12),
            text_color="gray", anchor="e")
        self._status_label.pack(side="right", fill="y")

        # Canvas — 用 wrapper 撑满右侧，canvas_frame 正方形居中
        wrapper = ctk.CTkFrame(parent, fg_color="transparent", corner_radius=0)
        wrapper.grid(row=1, column=0, sticky="nsew", padx=24, pady=(8, 24))

        self._canvas_frame = ctk.CTkFrame(wrapper, corner_radius=16, fg_color=_CARD,
                                          width=400, height=400)
        self._canvas_frame.pack_propagate(False)

        self._preview_canvas = tk.Canvas(
            self._canvas_frame, bg="#18181b", highlightthickness=0)
        self._preview_canvas.pack(fill="both", expand=True, padx=2, pady=2)

        wrapper.bind("<Configure>", self._on_wrapper_resize)
        self._preview_canvas.bind("<Configure>", self._on_canvas_resize)
        self._set_preview_placeholder()

    # ── 事件 ──────────────────────────────────────────────────────
    def _on_style(self, val: str):
        self._style_var.set(val)
        for btn, s in zip(self._style_btns, STYLES):
            selected = (s == val)
            btn.configure(
                fg_color=_ACCENT if selected else ("gray80", "#3a3a3a"),
                text_color=("white" if selected else ("gray20", "gray80")),
            )
        if val == "custom":
            self._shape_area.pack(fill="x", padx=10, pady=(0, 10))
            if not self._shape_path:
                self._pick_shape()
                return
        else:
            self._shape_area.pack_forget()
        self._sync_ec_state()
        self._schedule_preview()

    def _on_ec(self, val: str):
        self._ec_var.set(val)
        for btn, lvl in zip(self._ec_btns, EC_LEVELS):
            selected = (lvl == val)
            btn.configure(
                fg_color=_ACCENT if selected else ("gray80", "#3a3a3a"),
                text_color=("white" if selected else ("gray20", "gray80")),
            )
        self._schedule_preview()

    def _on_quality(self, idx: int):
        self._quality_idx = idx
        for i, btn in enumerate(self._quality_btns):
            selected = (i == idx)
            btn.configure(
                fg_color=_ACCENT if selected else ("gray80", "#3a3a3a"),
                text_color=("white" if selected else ("gray20", "gray80")),
            )
        self._schedule_preview()

    def _on_fg1_change(self, c: str):
        self._fg1 = c
        self._schedule_preview()

    def _on_fg2_change(self, c: str):
        self._fg2 = c
        self._schedule_preview()

    def _on_bg_change(self, c: str):
        self._bg = c
        self._schedule_preview()

    def _on_gradient_toggle(self):
        self._toggle_gradient_ui(self._gradient_on.get())
        self._schedule_preview()

    def _toggle_gradient_ui(self, on: bool):
        if on:
            self._grad_col.pack(side="left", expand=True, before=self._bg_col)
            self._fg2 = self._tile_fg2.color
        else:
            self._grad_col.pack_forget()
            self._fg2 = None

    def _pick_icon(self):
        path = filedialog.askopenfilename(
            title=t("choose_image"),
            filetypes=[("Image", "*.png *.jpg *.jpeg *.gif *.bmp *.ico *.webp"),
                       ("All", "*.*")],
        )
        if not path:
            return
        self._icon_path = path
        self._icon_name_label.configure(text=Path(path).name)
        # 小缩略图
        try:
            thumb = Image.open(path).convert("RGBA")
            thumb.thumbnail((48, 48), Image.LANCZOS)
            self._thumb_photo = ImageTk.PhotoImage(thumb)
            self._icon_thumb_label.configure(image=self._thumb_photo, text="")
        except Exception:
            pass
        self._sync_ec_state()
        self._schedule_preview()

    def _clear_icon(self):
        self._icon_path = None
        self._icon_name_label.configure(text=t("not_selected"))
        self._icon_thumb_label.configure(image="", text="")
        self._sync_ec_state()
        self._schedule_preview()

    def _pick_shape(self):
        path = filedialog.askopenfilename(
            title=t("choose_shape"),
            filetypes=[("PNG", "*.png")],
        )
        if not path:
            return
        try:
            img = Image.open(path).convert("RGBA")
            if img.getchannel("A").getextrema() == (255, 255):
                messagebox.showerror(t("tip"), t("shape_invalid"))
                return
        except Exception as e:
            messagebox.showerror(t("tip"), str(e))
            return
        self._shape_path = path
        self._shape_name_label.configure(text=Path(path).name, text_color=("gray20", "gray80"))
        try:
            thumb = img.copy()
            thumb.thumbnail((48, 48), Image.LANCZOS)
            self._shape_thumb_photo = ImageTk.PhotoImage(thumb)
            self._shape_thumb_label.configure(image=self._shape_thumb_photo, text="")
        except Exception:
            pass
        self._sync_ec_state()
        self._schedule_preview()

    def _clear_shape(self):
        self._shape_path = None
        self._shape_name_label.configure(text=t("shape_hint"), text_color="gray")
        self._shape_thumb_label.configure(image="", text="")
        self._sync_ec_state()
        self._schedule_preview()

    def _sync_ec_state(self):
        has = bool(self._icon_path) or (
            self._style_var.get() == "custom" and bool(self._shape_path)
        )
        for btn, lvl in zip(self._ec_btns, EC_LEVELS):
            btn.configure(state="disabled" if (has and lvl != "H") else "normal")
        if has:
            self._ec_var.set("H")
            self._on_ec("H")
            self._ec_lock_label.pack(side="left", padx=(6, 0))
        else:
            self._ec_lock_label.pack_forget()

    def _get_current_data(self) -> str:
        tab = self._tabs.get()
        panel = self._panels.get(tab)
        return panel.get_data() if panel else ""

    # ── 预览生成 ──────────────────────────────────────────────────
    def _schedule_preview(self, *_):
        """合并同一时间段内的多次触发，最后一次后 120ms 才真正生成预览。"""
        if self._debounce_id is not None:
            try:
                self.after_cancel(self._debounce_id)
            except Exception:
                pass
        self._debounce_id = self.after(120, self._run_preview)

    def _run_preview(self):
        self._debounce_id = None
        threading.Thread(target=self._generate_preview, daemon=True).start()

    def _build_fg_color(self) -> str:
        if self._gradient_on.get() and self._fg2:
            return f"{self._fg1},{self._fg2}"
        return self._fg1

    def _canvas_size(self) -> int:
        w = self._preview_canvas.winfo_width()
        h = self._preview_canvas.winfo_height()
        return max(1, min(w, h) - 32)

    def _on_wrapper_resize(self, event):
        """让 canvas_frame 始终是正方形并居中于 wrapper。"""
        size = max(1, min(event.width, event.height))
        x = (event.width  - size) // 2
        y = (event.height - size) // 2
        self._canvas_frame.configure(width=size, height=size)
        self._canvas_frame.place(x=x, y=y)

    def _on_canvas_resize(self, _=None):
        if self._resize_id:
            self.after_cancel(self._resize_id)
        self._resize_id = self.after(80, self._redraw_current)

    def _redraw_current(self):
        if self._current_image:
            size = self._canvas_size()
            prev = self._current_image.copy()
            prev.thumbnail((size, size), Image.LANCZOS)
            self._draw_on_canvas(prev)
        else:
            self._set_preview_placeholder()

    def _generate_preview(self):
        data = self._get_current_data()
        if not data:
            self.after(0, self._set_preview_placeholder)
            return
        style = self._style_var.get()
        if style == "custom" and not self._shape_path:
            self.after(0, self._show_error, t("shape_required"))
            return
        try:
            img = self._engine.generate(
                data=data,
                style=style,
                fg_color=self._build_fg_color(),
                bg_color=self._bg,
                icon_path=self._icon_path,
                icon_size_ratio=self._icon_ratio.get(),
                error_correction=self._ec_var.get(),
                box_size=QUALITY_SIZES[self._quality_idx], border=4,
                shape_path=self._shape_path,
            )
            self._current_image = img
            size = self._canvas_size()
            prev = img.copy()
            prev.thumbnail((size, size), Image.LANCZOS)
            self.after(0, self._update_preview, prev)
        except Exception as e:
            self.after(0, self._show_error, str(e))

    def _draw_on_canvas(self, img: Image.Image):
        cw = self._preview_canvas.winfo_width()
        ch = self._preview_canvas.winfo_height()
        if cw < 2 or ch < 2:
            return
        # 白色圆角背景衬底
        bg = Image.new("RGBA", (cw, ch), (24, 24, 27, 255))
        pad = 20
        qr_w, qr_h = img.size
        # 白色底板
        plate_w = qr_w + pad * 2
        plate_h = qr_h + pad * 2
        plate = Image.new("RGBA", (plate_w, plate_h), (255, 255, 255, 255))
        # 圆角裁切
        mask = Image.new("L", (plate_w, plate_h), 0)
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle([0, 0, plate_w - 1, plate_h - 1], radius=16, fill=255)
        plate.putalpha(mask)
        qr_x = (cw - plate_w) // 2
        qr_y = (ch - plate_h) // 2
        bg.alpha_composite(plate, (qr_x, qr_y))
        bg.alpha_composite(img, (qr_x + pad, qr_y + pad))

        tk_img = ImageTk.PhotoImage(bg)
        self._preview_canvas.delete("all")
        self._preview_canvas.create_image(0, 0, anchor="nw", image=tk_img)
        self._preview_canvas._image = tk_img

    def _update_preview(self, img: Image.Image):
        self._draw_on_canvas(img)
        self._status_label.configure(text=t("preview_updated"), text_color="#4ade80")

    def _set_preview_placeholder(self):
        cw = max(1, self._preview_canvas.winfo_width())
        ch = max(1, self._preview_canvas.winfo_height())
        bg = Image.new("RGBA", (cw, ch), (24, 24, 27, 255))
        tk_img = ImageTk.PhotoImage(bg)
        self._preview_canvas.delete("all")
        self._preview_canvas.create_image(0, 0, anchor="nw", image=tk_img)
        self._preview_canvas._image = tk_img
        self._status_label.configure(text=t("enter_content"), text_color="gray")

    def _show_error(self, msg: str):
        self._status_label.configure(text=t("error_prefix") + msg, text_color=_RED)

    # ── 导出 ──────────────────────────────────────────────────────
    def _export(self, fmt: str):
        if self._current_image is None:
            messagebox.showwarning(t("tip"), t("no_preview_yet"))
            return
        path = filedialog.asksaveasfilename(
            defaultextension=f".{fmt.lower()}",
            filetypes=[(fmt, f"*.{fmt.lower()}"), ("All", "*.*")],
            initialfile=f"qrcode.{fmt.lower()}",
        )
        if not path:
            return
        try:
            self._engine.save(self._current_image, path, fmt)
            messagebox.showinfo(t("export_success"), t("export_saved_to") + path)
        except Exception as e:
            messagebox.showerror(t("export_failed"), str(e))


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
