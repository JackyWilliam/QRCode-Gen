from __future__ import annotations

import base64
import io
from pathlib import Path
from xml.sax.saxutils import escape

import qrcode
from PIL import Image, ImageChops, ImageColor, ImageDraw, ImageOps
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers.pil import (
    CircleModuleDrawer,
    HorizontalBarsDrawer,
    RoundedModuleDrawer,
    SquareModuleDrawer,
    VerticalBarsDrawer,
)


class QRCodeEngine:
    """Generate styled QR code images and save them as PNG or SVG."""

    _STYLE_DRAWERS = {
        "square": lambda box_size: SquareModuleDrawer(),
        "round": lambda box_size: CircleModuleDrawer(),
        "rounded_square": lambda box_size: RoundedModuleDrawer(radius_ratio=0.3),
        "horizontal": lambda box_size: HorizontalBarsDrawer(),
        "vertical": lambda box_size: VerticalBarsDrawer(),
    }

    _CUSTOM_STYLE = "custom"

    _ERROR_LEVELS = {
        "L": qrcode.constants.ERROR_CORRECT_L,
        "M": qrcode.constants.ERROR_CORRECT_M,
        "Q": qrcode.constants.ERROR_CORRECT_Q,
        "H": qrcode.constants.ERROR_CORRECT_H,
    }

    def generate(
        self,
        data: str,
        style: str,
        fg_color: str,
        bg_color: str,
        icon_path: str | None,
        icon_size_ratio: float = 0.2,
        error_correction: str = "H",
        box_size: int = 10,
        border: int = 4,
        shape_path: str | None = None,
    ) -> Image.Image:
        if not data:
            raise ValueError("data must not be empty")

        if style != self._CUSTOM_STYLE and style not in self._STYLE_DRAWERS:
            raise ValueError(f"unsupported style: {style}")

        if style == self._CUSTOM_STYLE and not shape_path:
            raise ValueError("custom style requires shape_path")

        if not 0.0 <= icon_size_ratio <= 0.3:
            raise ValueError("icon_size_ratio must be between 0.0 and 0.3")

        if box_size <= 0:
            raise ValueError("box_size must be greater than 0")

        if border < 0:
            raise ValueError("border must be greater than or equal to 0")

        level = error_correction.upper()
        if level not in self._ERROR_LEVELS:
            raise ValueError("error_correction must be one of: L, M, Q, H")

        if icon_path and level != "H":
            raise ValueError("icon overlay requires error_correction='H'")

        qr = qrcode.QRCode(
            version=None,
            error_correction=self._ERROR_LEVELS[level],
            box_size=box_size,
            border=border,
        )
        qr.add_data(data)
        qr.make(fit=True)

        if style == self._CUSTOM_STYLE:
            image = self._render_custom_shape(
                qr=qr,
                shape_path=shape_path,
                box_size=box_size,
                border=border,
            )
        else:
            drawer = self._STYLE_DRAWERS[style](box_size)
            base = qr.make_image(
                image_factory=StyledPilImage,
                module_drawer=drawer,
            )
            image = base.get_image().convert("RGBA")

        image = self._redraw_eyes(
            image,
            modules_count=qr.modules_count,
            box_size=box_size,
            border=border,
        )

        fg_colors = self._parse_fg_colors(fg_color)
        bg_rgba = self._parse_color(bg_color)
        image = self._apply_colors(image, fg_colors=fg_colors, bg_color=bg_rgba)

        if icon_path:
            image = self._overlay_icon(
                image=image,
                icon_path=icon_path,
                icon_size_ratio=icon_size_ratio,
            )

        # Store generation metadata on the image so save() can reconstruct exports.
        image.info["qr_engine_meta"] = {
            "data": data,
            "style": style,
            "fg_color": fg_color,
            "bg_color": bg_color,
            "icon_path": icon_path,
            "icon_size_ratio": icon_size_ratio,
            "error_correction": level,
            "box_size": box_size,
            "border": border,
            "shape_path": shape_path,
        }
        return image

    def save(self, image: Image.Image, path: str, format: str = "PNG") -> None:
        output_format = format.upper()
        destination = Path(path).expanduser()
        destination.parent.mkdir(parents=True, exist_ok=True)

        if output_format == "PNG":
            image.save(destination, format="PNG")
            return

        if output_format != "SVG":
            raise ValueError("format must be PNG or SVG")

        svg_markup = self._image_to_svg(image)
        destination.write_text(svg_markup, encoding="utf-8")

    def _render_custom_shape(
        self,
        qr,
        shape_path: str,
        box_size: int,
        border: int,
    ) -> Image.Image:
        shape_source = Path(shape_path).expanduser()
        if not shape_source.exists():
            raise FileNotFoundError(f"shape not found: {shape_source}")

        shape = Image.open(shape_source)
        if shape.mode != "RGBA":
            shape = shape.convert("RGBA")
        if shape.getchannel("A").getextrema() == (255, 255):
            raise ValueError("shape must be a PNG with a transparent background")

        shape = shape.resize((box_size, box_size), Image.Resampling.LANCZOS)
        stamp = Image.new("RGBA", (box_size, box_size))
        stamp.putalpha(shape.getchannel("A"))

        modules_count = qr.modules_count
        total_size = (modules_count + 2 * border) * box_size
        image = Image.new("RGBA", (total_size, total_size), (255, 255, 255, 255))

        matrix = qr.get_matrix()
        for r, row in enumerate(matrix):
            y = r * box_size
            for c, on in enumerate(row):
                if on:
                    x = c * box_size
                    image.alpha_composite(stamp, (x, y))

        return image

    def _redraw_eyes(
        self,
        image: Image.Image,
        modules_count: int,
        box_size: int,
        border: int,
        corner_ratio: float = 0.25,
    ) -> Image.Image:
        result = image.copy()
        draw = ImageDraw.Draw(result)

        eye_modules = 7
        eye_size_px = eye_modules * box_size
        inner_dot_modules = 3
        inner_dot_px = inner_dot_modules * box_size

        outer_radius = int(eye_size_px * corner_ratio)
        cutout_radius = max(0, outer_radius - box_size)
        dot_radius = int(inner_dot_px * corner_ratio)

        positions = (
            (border, border),
            (border + modules_count - eye_modules, border),
            (border, border + modules_count - eye_modules),
        )

        for mx, my in positions:
            x0 = mx * box_size
            y0 = my * box_size
            x1 = x0 + eye_size_px
            y1 = y0 + eye_size_px

            draw.rectangle((x0, y0, x1 - 1, y1 - 1), fill=(255, 255, 255, 255))
            draw.rounded_rectangle(
                (x0, y0, x1 - 1, y1 - 1),
                radius=outer_radius,
                fill=(0, 0, 0, 255),
            )
            draw.rounded_rectangle(
                (x0 + box_size, y0 + box_size, x1 - box_size - 1, y1 - box_size - 1),
                radius=cutout_radius,
                fill=(255, 255, 255, 255),
            )
            dot_x0 = x0 + 2 * box_size
            dot_y0 = y0 + 2 * box_size
            draw.rounded_rectangle(
                (dot_x0, dot_y0, dot_x0 + inner_dot_px - 1, dot_y0 + inner_dot_px - 1),
                radius=dot_radius,
                fill=(0, 0, 0, 255),
            )

        return result

    def _apply_colors(
        self,
        image: Image.Image,
        fg_colors: tuple[tuple[int, int, int, int], ...],
        bg_color: tuple[int, int, int, int],
    ) -> Image.Image:
        gray = image.convert("L")
        alpha = ImageOps.invert(gray)
        alpha = ImageChops.multiply(alpha, image.getchannel("A"))

        background = Image.new("RGBA", image.size, bg_color)
        foreground = (
            self._build_gradient(image.size, fg_colors)
            if len(fg_colors) == 2
            else Image.new("RGBA", image.size, fg_colors[0])
        )
        background.paste(foreground, (0, 0), alpha)
        return background

    def _overlay_icon(
        self,
        image: Image.Image,
        icon_path: str,
        icon_size_ratio: float,
    ) -> Image.Image:
        icon_source = Path(icon_path).expanduser()
        if not icon_source.exists():
            raise FileNotFoundError(f"icon not found: {icon_source}")

        qr_size = image.width
        icon_size = max(1, int(qr_size * icon_size_ratio))
        padding = max(2, int(icon_size * 0.15))
        plate_size = icon_size + padding * 2
        plate_radius = max(4, int(plate_size * 0.22))

        icon = Image.open(icon_source).convert("RGBA")
        icon.thumbnail((icon_size, icon_size), Image.Resampling.LANCZOS)

        plate = Image.new("RGBA", (plate_size, plate_size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(plate)
        draw.rounded_rectangle(
            (0, 0, plate_size - 1, plate_size - 1),
            radius=plate_radius,
            fill=(255, 255, 255, 255),
        )

        icon_x = (plate_size - icon.width) // 2
        icon_y = (plate_size - icon.height) // 2
        plate.alpha_composite(icon, (icon_x, icon_y))

        result = image.copy()
        paste_x = (result.width - plate_size) // 2
        paste_y = (result.height - plate_size) // 2
        result.alpha_composite(plate, (paste_x, paste_y))
        return result

    def _build_gradient(
        self,
        size: tuple[int, int],
        colors: tuple[tuple[int, int, int, int], tuple[int, int, int, int]],
    ) -> Image.Image:
        width, height = size
        top, bottom = colors
        gradient = Image.new("RGBA", size)
        draw = ImageDraw.Draw(gradient)

        for y in range(height):
            ratio = 0 if height <= 1 else y / (height - 1)
            color = tuple(
                int(top[channel] + (bottom[channel] - top[channel]) * ratio)
                for channel in range(4)
            )
            draw.line((0, y, width, y), fill=color)

        return gradient

    def _parse_fg_colors(self, fg_color: str) -> tuple[tuple[int, int, int, int], ...]:
        parts = [part.strip() for part in fg_color.split(",") if part.strip()]
        if len(parts) not in {1, 2}:
            raise ValueError("fg_color must be one hex color or two comma-separated hex colors")
        return tuple(self._parse_color(part) for part in parts)

    def _parse_color(self, value: str) -> tuple[int, int, int, int]:
        try:
            rgb = ImageColor.getrgb(value)
        except ValueError as exc:
            raise ValueError(f"invalid color: {value}") from exc

        if len(rgb) == 4:
            return rgb
        return rgb[0], rgb[1], rgb[2], 255

    def _image_to_svg(self, image: Image.Image) -> str:
        meta = image.info.get("qr_engine_meta")
        if meta is None:
            return self._fallback_png_svg(image)
        return self._render_svg_vector(meta)

    def _render_svg_vector(self, meta: dict) -> str:
        qr = qrcode.QRCode(
            version=None,
            error_correction=self._ERROR_LEVELS[meta["error_correction"]],
            box_size=meta["box_size"],
            border=meta["border"],
        )
        qr.add_data(meta["data"])
        qr.make(fit=True)

        modules_count = qr.modules_count
        matrix = qr.get_matrix()
        box_size = meta["box_size"]
        border = meta["border"]
        canvas = (modules_count + 2 * border) * box_size

        fg_colors = self._parse_fg_colors(meta["fg_color"])
        bg_rgba = self._parse_color(meta["bg_color"])

        eye_corners = (
            (border, border),
            (border + modules_count - 7, border),
            (border, border + modules_count - 7),
        )

        defs: list[str] = []
        body: list[str] = []

        body.append(
            f'<rect width="{canvas}" height="{canvas}" '
            f'fill="{self._rgba_to_css(bg_rgba)}"/>'
        )

        if len(fg_colors) == 2:
            defs.append(self._build_gradient_def("qrFg", fg_colors, canvas))
            fg_fill = "url(#qrFg)"
        else:
            fg_fill = self._rgba_to_css(fg_colors[0])

        style = meta["style"]
        shape_path = meta.get("shape_path")
        if style == self._CUSTOM_STYLE and shape_path:
            symbol_def, mask_def, module_rect = self._build_custom_svg(
                matrix=matrix,
                eye_corners=eye_corners,
                shape_path=shape_path,
                box_size=box_size,
                canvas=canvas,
                fg_fill=fg_fill,
            )
            defs.append(symbol_def)
            defs.append(mask_def)
            body.append(module_rect)
        else:
            body.extend(
                self._draw_builtin_modules(
                    matrix=matrix,
                    eye_corners=eye_corners,
                    style=style,
                    box_size=box_size,
                    fg_fill=fg_fill,
                )
            )

        body.extend(
            self._draw_eyes_svg(
                corners=eye_corners,
                box_size=box_size,
                fg_fill=fg_fill,
                bg_rgba=bg_rgba,
            )
        )

        icon_path = meta.get("icon_path")
        if icon_path:
            body.extend(
                self._draw_icon_svg(
                    icon_path=icon_path,
                    canvas_size=canvas,
                    icon_size_ratio=meta["icon_size_ratio"],
                )
            )

        defs_block = (
            "  <defs>\n    " + "\n    ".join(defs) + "\n  </defs>\n"
            if defs
            else ""
        )
        body_block = "  " + "\n  ".join(body)

        return (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{canvas}" '
            f'height="{canvas}" viewBox="0 0 {canvas} {canvas}" '
            'role="img" aria-label="Generated QR Code">\n'
            f'{defs_block}{body_block}\n'
            '</svg>\n'
        )

    def _build_gradient_def(
        self,
        gradient_id: str,
        fg_colors: tuple[tuple[int, int, int, int], ...],
        canvas: int,
    ) -> str:
        top = fg_colors[0]
        bottom = fg_colors[1]
        return (
            f'<linearGradient id="{gradient_id}" gradientUnits="userSpaceOnUse" '
            f'x1="0" y1="0" x2="0" y2="{canvas}">'
            f'{self._color_stop(top, "0%")}'
            f'{self._color_stop(bottom, "100%")}'
            '</linearGradient>'
        )

    def _color_stop(self, rgba: tuple[int, int, int, int], offset: str) -> str:
        r, g, b, a = rgba
        return (
            f'<stop offset="{offset}" stop-color="rgb({r},{g},{b})" '
            f'stop-opacity="{a / 255:.3f}"/>'
        )

    def _draw_builtin_modules(
        self,
        matrix,
        eye_corners,
        style: str,
        box_size: int,
        fg_fill: str,
    ) -> list[str]:
        elements: list[str] = []
        size = len(matrix)
        for r in range(size):
            for c in range(size):
                if not matrix[r][c]:
                    continue
                if self._in_eye_region(r, c, eye_corners):
                    continue
                elements.append(
                    self._module_shape_svg(
                        style=style,
                        x=c * box_size,
                        y=r * box_size,
                        box_size=box_size,
                        fg_fill=fg_fill,
                    )
                )
        return elements

    def _in_eye_region(self, r: int, c: int, corners) -> bool:
        for mx, my in corners:
            if my <= r < my + 7 and mx <= c < mx + 7:
                return True
        return False

    def _module_shape_svg(
        self, style: str, x: int, y: int, box_size: int, fg_fill: str
    ) -> str:
        bs = box_size
        if style == "square":
            return (
                f'<rect x="{x}" y="{y}" width="{bs}" height="{bs}" '
                f'fill="{fg_fill}"/>'
            )
        if style == "round":
            cx = x + bs / 2
            cy = y + bs / 2
            return (
                f'<circle cx="{cx}" cy="{cy}" r="{bs / 2}" '
                f'fill="{fg_fill}"/>'
            )
        if style == "rounded_square":
            rx = bs * 0.3
            return (
                f'<rect x="{x}" y="{y}" width="{bs}" height="{bs}" '
                f'rx="{rx:.3f}" ry="{rx:.3f}" fill="{fg_fill}"/>'
            )
        if style in ("horizontal", "vertical"):
            pad = bs * 0.1
            thickness = bs - 2 * pad
            rx = thickness / 2
            if style == "horizontal":
                return (
                    f'<rect x="{x}" y="{y + pad:.3f}" width="{bs}" '
                    f'height="{thickness:.3f}" rx="{rx:.3f}" ry="{rx:.3f}" '
                    f'fill="{fg_fill}"/>'
                )
            return (
                f'<rect x="{x + pad:.3f}" y="{y}" width="{thickness:.3f}" '
                f'height="{bs}" rx="{rx:.3f}" ry="{rx:.3f}" '
                f'fill="{fg_fill}"/>'
            )
        raise ValueError(f"unsupported style for svg: {style}")

    def _draw_eyes_svg(
        self,
        corners,
        box_size: int,
        fg_fill: str,
        bg_rgba: tuple[int, int, int, int],
    ) -> list[str]:
        elements: list[str] = []
        eye_px = 7 * box_size
        inner_px = 3 * box_size
        outer_r = eye_px * 0.25
        cutout_r = max(0.0, outer_r - box_size)
        dot_r = inner_px * 0.25
        bg_css = self._rgba_to_css(bg_rgba)
        for mx, my in corners:
            x = mx * box_size
            y = my * box_size
            elements.append(
                f'<rect x="{x}" y="{y}" width="{eye_px}" height="{eye_px}" '
                f'rx="{outer_r:.3f}" ry="{outer_r:.3f}" fill="{fg_fill}"/>'
            )
            elements.append(
                f'<rect x="{x + box_size}" y="{y + box_size}" '
                f'width="{eye_px - 2 * box_size}" '
                f'height="{eye_px - 2 * box_size}" '
                f'rx="{cutout_r:.3f}" ry="{cutout_r:.3f}" fill="{bg_css}"/>'
            )
            elements.append(
                f'<rect x="{x + 2 * box_size}" y="{y + 2 * box_size}" '
                f'width="{inner_px}" height="{inner_px}" '
                f'rx="{dot_r:.3f}" ry="{dot_r:.3f}" fill="{fg_fill}"/>'
            )
        return elements

    def _draw_icon_svg(
        self,
        icon_path: str,
        canvas_size: int,
        icon_size_ratio: float,
    ) -> list[str]:
        icon_source = Path(icon_path).expanduser()
        if not icon_source.exists():
            raise FileNotFoundError(f"icon not found: {icon_source}")

        icon_size = max(1, int(canvas_size * icon_size_ratio))
        padding = max(2, int(icon_size * 0.15))
        plate_size = icon_size + 2 * padding
        plate_radius = max(4, int(plate_size * 0.22))

        icon = Image.open(icon_source).convert("RGBA")
        icon.thumbnail((icon_size, icon_size), Image.Resampling.LANCZOS)

        buf = io.BytesIO()
        icon.save(buf, format="PNG")
        icon_b64 = base64.b64encode(buf.getvalue()).decode("ascii")

        plate_x = (canvas_size - plate_size) // 2
        plate_y = (canvas_size - plate_size) // 2
        icon_x = plate_x + (plate_size - icon.width) // 2
        icon_y = plate_y + (plate_size - icon.height) // 2

        return [
            f'<rect x="{plate_x}" y="{plate_y}" width="{plate_size}" '
            f'height="{plate_size}" rx="{plate_radius}" ry="{plate_radius}" '
            f'fill="#FFFFFF"/>',
            f'<image x="{icon_x}" y="{icon_y}" width="{icon.width}" '
            f'height="{icon.height}" preserveAspectRatio="none" '
            f'href="data:image/png;base64,{icon_b64}"/>',
        ]

    def _build_custom_svg(
        self,
        matrix,
        eye_corners,
        shape_path: str,
        box_size: int,
        canvas: int,
        fg_fill: str,
    ) -> tuple[str, str, str]:
        shape_source = Path(shape_path).expanduser()
        if not shape_source.exists():
            raise FileNotFoundError(f"shape not found: {shape_source}")
        shape_b64 = base64.b64encode(shape_source.read_bytes()).decode("ascii")

        symbol_def = (
            f'<symbol id="qrShape" width="{box_size}" height="{box_size}" '
            f'viewBox="0 0 {box_size} {box_size}">'
            f'<image width="{box_size}" height="{box_size}" '
            f'preserveAspectRatio="none" '
            f'href="data:image/png;base64,{shape_b64}"/>'
            '</symbol>'
        )

        uses: list[str] = []
        size = len(matrix)
        for r in range(size):
            for c in range(size):
                if not matrix[r][c]:
                    continue
                if self._in_eye_region(r, c, eye_corners):
                    continue
                uses.append(
                    f'<use href="#qrShape" x="{c * box_size}" '
                    f'y="{r * box_size}" width="{box_size}" '
                    f'height="{box_size}"/>'
                )

        uses_block = "\n      ".join(uses)
        mask_def = (
            '<mask id="qrShapeMask" maskUnits="userSpaceOnUse" '
            'mask-type="alpha" '
            f'x="0" y="0" width="{canvas}" height="{canvas}">\n      '
            f'{uses_block}\n    </mask>'
        )
        module_rect = (
            f'<rect width="{canvas}" height="{canvas}" fill="{fg_fill}" '
            'mask="url(#qrShapeMask)"/>'
        )
        return symbol_def, mask_def, module_rect

    def _rgba_to_css(self, rgba: tuple[int, int, int, int]) -> str:
        r, g, b, a = rgba
        if a == 255:
            return f'#{r:02X}{g:02X}{b:02X}'
        return f'rgba({r},{g},{b},{a / 255:.3f})'

    def _fallback_png_svg(self, image: Image.Image) -> str:
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
        width, height = image.size
        title = "Generated QR Code"

        return (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title)}">\n'
            f'  <image width="{width}" height="{height}" '
            f'href="data:image/png;base64,{encoded}"/>\n'
            "</svg>\n"
        )
