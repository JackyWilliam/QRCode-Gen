"""自研颜色选择器模块。

公共 API：
    - ColorPicker  —— HSV + alpha 弹窗
    - ColorTile    —— 可点击色块，点击唤起 ColorPicker
    - parse_hex    —— '#RRGGBB[AA]' → (r, g, b, a)
    - format_hex   —— (r, g, b, a) → '#RRGGBB' 或 '#RRGGBBAA'
    - render_swatch —— 生成带棋盘格的色块预览图

颜色字符串统一使用 '#RRGGBB' 或 '#RRGGBBAA'（alpha = 255 时省略）。
"""
from __future__ import annotations

import colorsys
import json
import os
import sys
import tkinter as tk
from pathlib import Path
from typing import Callable, Optional

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageTk

from i18n import t


__all__ = [
    "ColorPicker",
    "ColorTile",
    "parse_hex",
    "format_hex",
    "render_swatch",
]


def _user_data_dir() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library/Application Support/QRCodeGen"
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData/Roaming")
        return Path(base) / "QRCodeGen"
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "QRCodeGen"


def _mono_font_family() -> str:
    if sys.platform == "darwin":
        return "Menlo"
    if sys.platform == "win32":
        return "Consolas"
    return "DejaVu Sans Mono"


_RECENT_DIR = _user_data_dir()
_RECENT_FILE = _RECENT_DIR / "recent_colors.json"
_RECENT_MAX = 10
_MONO_FAMILY = _mono_font_family()

_CB_DARK = (204, 204, 204)
_CB_LIGHT = (255, 255, 255)


# ─── Hex 工具 ───────────────────────────────────────────────────────

def parse_hex(value: str) -> tuple[int, int, int, int]:
    s = value.strip().lstrip("#")
    if len(s) == 3:
        r, g, b = (int(c * 2, 16) for c in s)
        return r, g, b, 255
    if len(s) == 6:
        return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16), 255
    if len(s) == 8:
        return (
            int(s[0:2], 16),
            int(s[2:4], 16),
            int(s[4:6], 16),
            int(s[6:8], 16),
        )
    raise ValueError(f"invalid hex: {value}")


def format_hex(r: int, g: int, b: int, a: int = 255) -> str:
    if a == 255:
        return f"#{r:02X}{g:02X}{b:02X}"
    return f"#{r:02X}{g:02X}{b:02X}{a:02X}"


# ─── 图像生成 ───────────────────────────────────────────────────────

def _checkerboard(w: int, h: int, cell: int = 6) -> Image.Image:
    img = Image.new("RGB", (w, h), _CB_LIGHT)
    draw = ImageDraw.Draw(img)
    for yi, y in enumerate(range(0, h, cell)):
        y2 = min(y + cell, h) - 1
        for xi, x in enumerate(range(0, w, cell)):
            if (xi + yi) & 1:
                draw.rectangle((x, y, min(x + cell, w) - 1, y2), fill=_CB_DARK)
    return img


def _h_alpha_gradient_mask(w: int, h: int) -> Image.Image:
    """横向 0→255 的 alpha 灰度 mask（L 模式），高度 h。"""
    if w <= 1:
        return Image.new("L", (w, h), 255)
    row = bytes(min(255, max(0, round(x * 255 / (w - 1)))) for x in range(w))
    one_row = Image.frombytes("L", (w, 1), row)
    return one_row.resize((w, h), Image.NEAREST)


def _sv_image(hue: float, size: int) -> Image.Image:
    """饱和度×明度方块。横向：白→hue_rgb；纵向：顶 v=1 → 底 v=0。"""
    r_h, g_h, b_h = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
    r255, g255, b255 = int(r_h * 255), int(g_h * 255), int(b_h * 255)
    # 横向渐变：白 → hue_rgb
    row = Image.new("RGB", (size, 1))
    px = row.load()
    if size == 1:
        px[0, 0] = (r255, g255, b255)
    else:
        for x in range(size):
            t_s = x / (size - 1)
            px[x, 0] = (
                int(255 * (1 - t_s) + r255 * t_s),
                int(255 * (1 - t_s) + g255 * t_s),
                int(255 * (1 - t_s) + b255 * t_s),
            )
    base = row.resize((size, size), Image.NEAREST)
    # 纵向明度衰减：顶 v=1 (mask=255) → 底 v=0 (mask=0)
    col_bytes = bytes(
        int(255 * (1 - y / (size - 1))) if size > 1 else 255
        for y in range(size)
    )
    col = Image.frombytes("L", (1, size), col_bytes)
    value_mask = col.resize((size, size), Image.NEAREST)
    black = Image.new("RGB", (size, size), (0, 0, 0))
    return Image.composite(base, black, value_mask)


def _hue_strip(w: int, h: int) -> Image.Image:
    """色相条：每列一个 hue（0→1）。"""
    row = Image.new("RGB", (w, 1))
    px = row.load()
    for x in range(w):
        hue = x / (w - 1) if w > 1 else 0.0
        r, g, b = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
        px[x, 0] = (int(r * 255), int(g * 255), int(b * 255))
    return row.resize((w, h), Image.NEAREST)


def _alpha_strip(rgb: tuple[int, int, int], w: int, h: int) -> Image.Image:
    cb = _checkerboard(w, h, cell=max(4, h // 3))
    overlay = Image.new("RGBA", (w, h), (*rgb, 255))
    overlay.putalpha(_h_alpha_gradient_mask(w, h))
    cb_rgba = cb.convert("RGBA")
    cb_rgba.alpha_composite(overlay)
    return cb_rgba.convert("RGB")


def _swatch_image(rgba: tuple[int, int, int, int], w: int, h: int) -> Image.Image:
    cb = _checkerboard(w, h, cell=max(4, h // 3)).convert("RGBA")
    r, g, b, a = rgba
    overlay = Image.new("RGBA", (w, h), (r, g, b, a))
    cb.alpha_composite(overlay)
    return cb.convert("RGB")


def render_swatch(
    rgba: tuple[int, int, int, int],
    width: int,
    height: int,
    corner_radius: int = 0,
) -> Image.Image:
    """棋盘格底 + 指定 RGBA 合成的预览色块。corner_radius > 0 则圆角裁切。

    返回 RGBA Image；alpha = 255 的区域不透明，外圆角之外为透明。
    """
    base = _swatch_image(rgba, width, height).convert("RGBA")
    if corner_radius <= 0:
        return base
    mask = Image.new("L", (width, height), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, width - 1, height - 1),
        radius=corner_radius,
        fill=255,
    )
    base.putalpha(mask)
    return base


# ─── Recent colors 持久化 ───────────────────────────────────────────

def load_recent() -> list[str]:
    try:
        return json.loads(_RECENT_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return []


def push_recent(color_hex: str) -> list[str]:
    recent = load_recent()
    if color_hex in recent:
        recent.remove(color_hex)
    recent.insert(0, color_hex)
    recent = recent[:_RECENT_MAX]
    try:
        _RECENT_DIR.mkdir(parents=True, exist_ok=True)
        _RECENT_FILE.write_text(
            json.dumps(recent, ensure_ascii=False), encoding="utf-8"
        )
    except OSError:
        pass
    return recent


# ─── 主组件 ────────────────────────────────────────────────────────

class ColorPicker(ctk.CTkToplevel):
    """HSV + alpha 颜色选择器弹窗。支持 '#RRGGBB' 和 '#RRGGBBAA'。"""

    SV_SIZE = 176
    STRIP_W = 176
    STRIP_H = 14

    def __init__(
        self,
        parent,
        initial: str,
        on_change: Callable[[str], None],
        anchor_widget=None,
        title: Optional[str] = None,
    ):
        super().__init__(parent)
        self.title(title if title is not None else t("cp_title"))
        self.resizable(False, False)
        self.configure(fg_color="#1e1e1e")
        try:
            self.transient(parent.winfo_toplevel())
        except Exception:
            pass
        self.attributes("-topmost", True)

        self._on_change = on_change
        self._original_hex = initial
        r, g, b, a = parse_hex(initial)
        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        self._hue = h
        self._sat = s
        self._val = v
        self._alpha = a
        self._cached_sv_hue = -1.0
        self._sv_photo: Optional[ImageTk.PhotoImage] = None
        self._hue_photo: Optional[ImageTk.PhotoImage] = None
        self._alpha_photo: Optional[ImageTk.PhotoImage] = None
        self._swatch_photo: Optional[ImageTk.PhotoImage] = None
        self._alpha_cb_cache: Optional[Image.Image] = None
        self._swatch_cb_cache: Optional[Image.Image] = None
        self._emit_after_id: Optional[str] = None
        self._suppress_entry_commit = False

        self._build_ui()
        self._render_all()
        if anchor_widget is not None:
            self._position_near(anchor_widget)

        self.bind("<Escape>", lambda _e: self._cancel())
        self.bind("<Return>", lambda _e: self._confirm())
        self.protocol("WM_DELETE_WINDOW", self._confirm)
        self.after(80, self._grab_focus)

    # ─── 布局 ───────────────────────────────────────────────

    def _build_ui(self):
        pad = ctk.CTkFrame(self, fg_color="#1e1e1e")
        pad.pack(padx=10, pady=10)

        self._sv_canvas = tk.Canvas(
            pad,
            width=self.SV_SIZE,
            height=self.SV_SIZE,
            bd=0,
            highlightthickness=1,
            highlightbackground="#333",
            cursor="crosshair",
        )
        self._sv_canvas.grid(row=0, column=0, columnspan=4, pady=(0, 6))
        self._sv_canvas.bind("<Button-1>", self._on_sv_event)
        self._sv_canvas.bind("<B1-Motion>", self._on_sv_event)

        self._hue_canvas = tk.Canvas(
            pad,
            width=self.STRIP_W,
            height=self.STRIP_H,
            bd=0,
            highlightthickness=1,
            highlightbackground="#333",
            cursor="sb_h_double_arrow",
        )
        self._hue_canvas.grid(row=1, column=0, columnspan=4, pady=2)
        self._hue_canvas.bind("<Button-1>", self._on_hue_event)
        self._hue_canvas.bind("<B1-Motion>", self._on_hue_event)

        self._alpha_canvas = tk.Canvas(
            pad,
            width=self.STRIP_W,
            height=self.STRIP_H,
            bd=0,
            highlightthickness=1,
            highlightbackground="#333",
            cursor="sb_h_double_arrow",
        )
        self._alpha_canvas.grid(row=2, column=0, columnspan=4, pady=2)
        self._alpha_canvas.bind("<Button-1>", self._on_alpha_event)
        self._alpha_canvas.bind("<B1-Motion>", self._on_alpha_event)

        preview_row = ctk.CTkFrame(pad, fg_color="transparent")
        preview_row.grid(row=3, column=0, columnspan=4, pady=(6, 2), sticky="ew")
        self._swatch_canvas = tk.Canvas(
            preview_row,
            width=40,
            height=24,
            bd=0,
            highlightthickness=1,
            highlightbackground="#444",
        )
        self._swatch_canvas.pack(side="left", padx=(0, 8))
        self._hex_var = tk.StringVar()
        self._hex_entry = ctk.CTkEntry(
            preview_row,
            textvariable=self._hex_var,
            width=120,
            height=24,
            corner_radius=5,
            font=ctk.CTkFont(family=_MONO_FAMILY, size=11),
        )
        self._hex_entry.pack(side="left")
        self._hex_entry.bind("<Return>", lambda _e: self._commit_hex())
        self._hex_entry.bind("<FocusOut>", lambda _e: self._commit_hex())

        rgba_row = ctk.CTkFrame(pad, fg_color="transparent")
        rgba_row.grid(row=4, column=0, columnspan=4, pady=2)
        self._rgba_vars: dict[str, tk.StringVar] = {}
        for i, key in enumerate(("R", "G", "B", "A")):
            cell = ctk.CTkFrame(rgba_row, fg_color="transparent")
            cell.grid(row=0, column=i, padx=2)
            ctk.CTkLabel(
                cell,
                text=key,
                font=ctk.CTkFont(size=9),
                text_color="#9ca3af",
                height=12,
            ).pack()
            var = tk.StringVar()
            self._rgba_vars[key] = var
            entry = ctk.CTkEntry(
                cell,
                textvariable=var,
                width=40,
                height=22,
                corner_radius=4,
                font=ctk.CTkFont(size=10),
            )
            entry.pack()
            entry.bind("<Return>", lambda _e: self._commit_rgba())
            entry.bind("<FocusOut>", lambda _e: self._commit_rgba())

        self._recent_list = load_recent()
        self._recent_row = ctk.CTkFrame(pad, fg_color="transparent")
        self._recent_row.grid(row=5, column=0, columnspan=4, pady=(6, 2))
        self._render_recent()

        btn_row = ctk.CTkFrame(pad, fg_color="transparent")
        btn_row.grid(row=6, column=0, columnspan=4, pady=(6, 0), sticky="ew")
        btn_row.columnconfigure((0, 1), weight=1)
        ctk.CTkButton(
            btn_row,
            text=t("cp_cancel"),
            width=80,
            height=24,
            corner_radius=5,
            fg_color=("gray80", "#3a3a3a"),
            hover_color=("gray70", "#4a4a4a"),
            text_color=("black", "white"),
            command=self._cancel,
        ).grid(row=0, column=0, padx=(0, 4), sticky="ew")
        ctk.CTkButton(
            btn_row,
            text=t("cp_confirm"),
            width=80,
            height=24,
            corner_radius=5,
            command=self._confirm,
        ).grid(row=0, column=1, padx=(4, 0), sticky="ew")

    def _render_recent(self):
        for child in self._recent_row.winfo_children():
            child.destroy()
        if not self._recent_list:
            return
        for color_hex in self._recent_list[:_RECENT_MAX]:
            try:
                rgba = parse_hex(color_hex)
            except ValueError:
                continue
            cvs = tk.Canvas(
                self._recent_row,
                width=20,
                height=20,
                bd=0,
                highlightthickness=1,
                highlightbackground="#333",
                cursor="hand2",
            )
            cvs.pack(side="left", padx=2)
            img = _swatch_image(rgba, 20, 20)
            photo = ImageTk.PhotoImage(img)
            cvs._photo = photo  # anti-GC
            cvs.create_image(0, 0, image=photo, anchor="nw")
            cvs.bind("<Button-1>", lambda _e, c=color_hex: self._apply_hex(c))

    # ─── 渲染 ───────────────────────────────────────────────

    def _render_all(self):
        self._render_sv()
        self._render_hue()
        self._render_alpha()
        self._render_swatch()
        self._render_entries()

    def _render_sv(self):
        if self._cached_sv_hue != self._hue:
            img = _sv_image(self._hue, self.SV_SIZE)
            self._sv_photo = ImageTk.PhotoImage(img)
            self._cached_sv_hue = self._hue
        self._sv_canvas.delete("all")
        self._sv_canvas.create_image(0, 0, image=self._sv_photo, anchor="nw")
        cx = int(self._sat * (self.SV_SIZE - 1))
        cy = int((1.0 - self._val) * (self.SV_SIZE - 1))
        r = 6
        ring_color = "#000000" if self._val > 0.5 else "#FFFFFF"
        self._sv_canvas.create_oval(
            cx - r, cy - r, cx + r, cy + r, outline=ring_color, width=2
        )
        self._sv_canvas.create_oval(
            cx - r + 1, cy - r + 1, cx + r - 1, cy + r - 1,
            outline="#FFFFFF" if ring_color == "#000000" else "#000000",
            width=1,
        )

    def _render_hue(self):
        if self._hue_photo is None:
            img = _hue_strip(self.STRIP_W, self.STRIP_H)
            self._hue_photo = ImageTk.PhotoImage(img)
        self._hue_canvas.delete("all")
        self._hue_canvas.create_image(0, 0, image=self._hue_photo, anchor="nw")
        x = int(self._hue * (self.STRIP_W - 1))
        self._hue_canvas.create_rectangle(
            x - 2, 0, x + 2, self.STRIP_H, outline="#FFFFFF", width=1
        )
        self._hue_canvas.create_rectangle(
            x - 1, 0, x + 1, self.STRIP_H, outline="#000000", width=1
        )

    def _render_alpha(self):
        r, g, b = self._current_rgb()
        if self._alpha_cb_cache is None:
            self._alpha_cb_cache = _checkerboard(
                self.STRIP_W, self.STRIP_H, cell=max(4, self.STRIP_H // 3)
            ).convert("RGBA")
        base = self._alpha_cb_cache.copy()
        overlay = Image.new("RGBA", (self.STRIP_W, self.STRIP_H), (r, g, b, 255))
        overlay.putalpha(_h_alpha_gradient_mask(self.STRIP_W, self.STRIP_H))
        base.alpha_composite(overlay)
        self._alpha_photo = ImageTk.PhotoImage(base)
        self._alpha_canvas.delete("all")
        self._alpha_canvas.create_image(0, 0, image=self._alpha_photo, anchor="nw")
        x = int((self._alpha / 255.0) * (self.STRIP_W - 1))
        self._alpha_canvas.create_rectangle(
            x - 2, 0, x + 2, self.STRIP_H, outline="#FFFFFF", width=1
        )
        self._alpha_canvas.create_rectangle(
            x - 1, 0, x + 1, self.STRIP_H, outline="#000000", width=1
        )

    def _render_swatch(self):
        r, g, b = self._current_rgb()
        w, h = 40, 24
        if self._swatch_cb_cache is None:
            self._swatch_cb_cache = _checkerboard(
                w, h, cell=max(4, h // 3)
            ).convert("RGBA")
        base = self._swatch_cb_cache.copy()
        overlay = Image.new("RGBA", (w, h), (r, g, b, self._alpha))
        base.alpha_composite(overlay)
        self._swatch_photo = ImageTk.PhotoImage(base.convert("RGB"))
        self._swatch_canvas.delete("all")
        self._swatch_canvas.create_image(0, 0, image=self._swatch_photo, anchor="nw")

    def _render_entries(self):
        self._suppress_entry_commit = True
        r, g, b = self._current_rgb()
        self._hex_var.set(format_hex(r, g, b, self._alpha))
        self._rgba_vars["R"].set(str(r))
        self._rgba_vars["G"].set(str(g))
        self._rgba_vars["B"].set(str(b))
        self._rgba_vars["A"].set(str(self._alpha))
        self._suppress_entry_commit = False

    # ─── 交互 ───────────────────────────────────────────────

    def _on_sv_event(self, event):
        x = max(0, min(self.SV_SIZE - 1, int(event.x)))
        y = max(0, min(self.SV_SIZE - 1, int(event.y)))
        self._sat = x / (self.SV_SIZE - 1)
        self._val = 1.0 - y / (self.SV_SIZE - 1)
        self._render_sv()
        self._render_alpha()
        self._render_swatch()
        self._render_entries()
        self._emit()

    def _on_hue_event(self, event):
        x = max(0, min(self.STRIP_W - 1, int(event.x)))
        self._hue = x / (self.STRIP_W - 1)
        self._render_sv()
        self._render_hue()
        self._render_alpha()
        self._render_swatch()
        self._render_entries()
        self._emit()

    def _on_alpha_event(self, event):
        x = max(0, min(self.STRIP_W - 1, int(event.x)))
        self._alpha = int(round(x / (self.STRIP_W - 1) * 255))
        self._render_alpha()
        self._render_swatch()
        self._render_entries()
        self._emit()

    def _commit_hex(self):
        if self._suppress_entry_commit:
            return
        try:
            rgba = parse_hex(self._hex_var.get())
        except ValueError:
            self._render_entries()
            return
        self._apply_rgba(rgba, emit=True)

    def _commit_rgba(self):
        if self._suppress_entry_commit:
            return
        try:
            r = int(self._rgba_vars["R"].get())
            g = int(self._rgba_vars["G"].get())
            b = int(self._rgba_vars["B"].get())
            a = int(self._rgba_vars["A"].get())
        except ValueError:
            self._render_entries()
            return
        r = max(0, min(255, r))
        g = max(0, min(255, g))
        b = max(0, min(255, b))
        a = max(0, min(255, a))
        self._apply_rgba((r, g, b, a), emit=True)

    def _apply_hex(self, hex_str: str):
        try:
            self._apply_rgba(parse_hex(hex_str), emit=True)
        except ValueError:
            pass

    def _apply_rgba(self, rgba: tuple[int, int, int, int], emit: bool):
        r, g, b, a = rgba
        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        if s > 0 or v > 0:
            self._hue = h
        self._sat = s
        self._val = v
        self._alpha = a
        self._render_all()
        if emit:
            self._emit()

    def _current_rgb(self) -> tuple[int, int, int]:
        r, g, b = colorsys.hsv_to_rgb(self._hue, self._sat, self._val)
        return int(round(r * 255)), int(round(g * 255)), int(round(b * 255))

    def _current_hex(self) -> str:
        r, g, b = self._current_rgb()
        return format_hex(r, g, b, self._alpha)

    def _emit(self):
        try:
            self._on_change(self._current_hex())
        except Exception:
            pass

    # ─── 关闭 / 定位 ────────────────────────────────────────

    def _position_near(self, widget):
        try:
            self.update_idletasks()
            widget.update_idletasks()
            x = widget.winfo_rootx()
            y = widget.winfo_rooty() + widget.winfo_height() + 6
            w = self.winfo_reqwidth()
            h = self.winfo_reqheight()
            screen_w = self.winfo_screenwidth()
            screen_h = self.winfo_screenheight()
            x = max(8, min(screen_w - w - 8, x))
            y = max(8, min(screen_h - h - 8, y))
            self.geometry(f"+{x}+{y}")
        except Exception:
            pass

    def _grab_focus(self):
        try:
            self.focus_force()
        except Exception:
            pass

    def _confirm(self):
        final = self._current_hex()
        push_recent(final)
        self._cleanup()

    def _cancel(self):
        try:
            self._on_change(self._original_hex)
        except Exception:
            pass
        self._cleanup()

    def _cleanup(self):
        try:
            self.destroy()
        except Exception:
            pass


# ─── ColorTile ─────────────────────────────────────────────────────

class ColorTile(ctk.CTkFrame):
    """可点击色块，点击唤起 ColorPicker。颜色以 '#RRGGBB' 或 '#RRGGBBAA' 存取。"""

    def __init__(
        self,
        master,
        color: str,
        on_change: Callable[[str], None],
        size: int = 44,
        corner_radius: int = 8,
        title: Optional[str] = None,
        **kw,
    ):
        super().__init__(
            master,
            width=size,
            height=size,
            corner_radius=corner_radius,
            cursor="hand2",
            **kw,
        )
        self.pack_propagate(False)
        self._color = color
        self._on_change = on_change
        self._size = size
        self._corner_radius = corner_radius
        self._title = title
        self._photo: Optional[ImageTk.PhotoImage] = None
        self._picker: Optional[ColorPicker] = None
        self._canvas = tk.Canvas(
            self, width=size, height=size, bd=0, highlightthickness=0, bg="#2a2a2a"
        )
        self._canvas.pack(fill="both", expand=True)
        self._canvas.bind("<Button-1>", lambda _e: self.open_picker())
        self.after(10, self._paint)

    def _paint(self):
        try:
            rgba = parse_hex(self._color)
        except ValueError:
            rgba = (0, 0, 0, 255)
        img = render_swatch(rgba, self._size, self._size, self._corner_radius)
        self._photo = ImageTk.PhotoImage(img)
        self._canvas.delete("all")
        self._canvas.create_image(0, 0, image=self._photo, anchor="nw")

    def open_picker(self):
        if self._picker is not None and self._picker.winfo_exists():
            try:
                self._picker.lift()
            except Exception:
                pass
            return
        self._picker = ColorPicker(
            parent=self.winfo_toplevel(),
            initial=self._color,
            on_change=self._handle_change,
            anchor_widget=self,
            title=self._title,
        )

    def _handle_change(self, c: str):
        self._color = c
        self._paint()
        self._on_change(c)

    @property
    def color(self) -> str:
        return self._color

    def set_color(self, c: str):
        self._color = c
        self._paint()

    def set_enabled(self, on: bool):
        self._canvas.configure(cursor="hand2" if on else "arrow")
