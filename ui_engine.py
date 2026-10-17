"""
ui_engine.py — Ultra-Modern Vector & Glassmorphism UI Engine
Provides crystal-clear anti-aliased typography (TrueType Segoe UI),
smooth rounded cards, glassmorphic blur, neon glow, and dynamic interactive buttons.
"""

import os
from typing import Dict, Optional, Tuple

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


class UIEngine:
    """High-Definition Modern UI Engine for Computer Vision Applications."""

    # Font cache
    _fonts: Dict[Tuple[str, int], ImageFont.FreeTypeFont] = {}
    # Button render cache: (cache_key) -> np.ndarray (RGBA)
    _cache: Dict[str, np.ndarray] = {}

    @classmethod
    def get_font(cls, size: int = 16, bold: bool = True) -> ImageFont.FreeTypeFont:
        """Load and cache high-quality Windows TrueType fonts (Segoe UI / Arial)."""
        font_name = "segoeuib.ttf" if bold else "segoeui.ttf"
        cache_key = (font_name, size)
        if cache_key in cls._fonts:
            return cls._fonts[cache_key]

        font_paths = [
            f"C:\\Windows\\Fonts\\{font_name}",
            f"C:\\Windows\\Fonts\\{'arialbd.ttf' if bold else 'arial.ttf'}",
            font_name,
        ]

        for path in font_paths:
            if os.path.exists(path):
                try:
                    font = ImageFont.truetype(path, size)
                    cls._fonts[cache_key] = font
                    return font
                except Exception:
                    continue

        # Fallback to default
        font = ImageFont.load_default()
        cls._fonts[cache_key] = font
        return font

    @staticmethod
    def blend_rgba(bgr_canvas: np.ndarray, rgba_overlay: np.ndarray, pos: Tuple[int, int]) -> None:
        """Blend an RGBA (from PIL) image onto a BGR OpenCV canvas with full anti-aliasing."""
        x, y = int(pos[0]), int(pos[1])
        h_ov, w_ov = rgba_overlay.shape[:2]
        h_c, w_c = bgr_canvas.shape[:2]

        x1 = max(0, x)
        y1 = max(0, y)
        x2 = min(w_c, x + w_ov)
        y2 = min(h_c, y + h_ov)

        if x1 >= x2 or y1 >= y2:
            return

        ox1 = x1 - x
        oy1 = y1 - y
        ox2 = ox1 + (x2 - x1)
        oy2 = oy1 + (y2 - y1)

        sub_overlay = rgba_overlay[oy1:oy2, ox1:ox2]
        alpha = sub_overlay[:, :, 3:4].astype(np.float32) / 255.0
        # Convert RGB from PIL to BGR for OpenCV
        overlay_bgr = sub_overlay[:, :, [2, 1, 0]].astype(np.float32)
        canvas_bgr = bgr_canvas[y1:y2, x1:x2].astype(np.float32)

        bgr_canvas[y1:y2, x1:x2] = ((1.0 - alpha) * canvas_bgr + alpha * overlay_bgr).astype(np.uint8)

    @classmethod
    def draw_rounded_rect(cls, img: np.ndarray, pt1: Tuple[int, int], pt2: Tuple[int, int],
                          color: Tuple[int, int, int], thickness: int = -1, radius: int = 10,
                          filled: bool = True) -> None:
        """Draw an anti-aliased rounded rectangle."""
        x1, y1 = min(pt1[0], pt2[0]), min(pt1[1], pt2[1])
        x2, y2 = max(pt1[0], pt2[0]), max(pt1[1], pt2[1])
        w = x2 - x1
        h = y2 - y1
        if w <= 0 or h <= 0:
            return

        # BGR to RGB for PIL
        rgb_color = (int(color[2]), int(color[1]), int(color[0]))
        pil_img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(pil_img)

        safe_r = min(radius, w // 2, h // 2)
        if filled or thickness < 0:
            draw.rounded_rectangle([0, 0, w - 1, h - 1], radius=safe_r, fill=(*rgb_color, 255))
        else:
            draw.rounded_rectangle([0, 0, w - 1, h - 1], radius=safe_r, outline=(*rgb_color, 255), width=max(1, thickness))

        cls.blend_rgba(img, np.array(pil_img), (x1, y1))

    @classmethod
    def draw_glass_panel(cls, img: np.ndarray, pt1: Tuple[int, int], pt2: Tuple[int, int],
                         color: Tuple[int, int, int] = (20, 25, 38), alpha: float = 0.65,
                         radius: int = 14, border_color: Optional[Tuple[int, int, int]] = (100, 180, 255),
                         border_width: int = 1) -> None:
        """Render a silky-smooth anti-aliased glassmorphism panel."""
        x1, y1 = min(pt1[0], pt2[0]), min(pt1[1], pt2[1])
        x2, y2 = max(pt1[0], pt2[0]), max(pt1[1], pt2[1])
        w = x2 - x1
        h = y2 - y1
        if w <= 0 or h <= 0:
            return

        rgb_color = (int(color[2]), int(color[1]), int(color[0]))
        fill_alpha = int(max(0.0, min(1.0, alpha)) * 255)

        pil_img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(pil_img)
        safe_r = min(radius, w // 2, h // 2)

        outline_tuple = None
        if border_color is not None:
            rgb_border = (int(border_color[2]), int(border_color[1]), int(border_color[0]))
            outline_tuple = (*rgb_border, min(255, int(fill_alpha * 1.5)))

        draw.rounded_rectangle(
            [0, 0, w - 1, h - 1],
            radius=safe_r,
            fill=(*rgb_color, fill_alpha),
            outline=outline_tuple,
            width=border_width
        )

        cls.blend_rgba(img, np.array(pil_img), (x1, y1))

    @classmethod
    def draw_text_modern(cls, img: np.ndarray, text: str, pos: Tuple[int, int],
                         scale: float = 0.6, color: Tuple[int, int, int] = (255, 255, 255),
                         bg_color: Tuple[int, int, int] = (15, 20, 30), alpha: float = 0.75,
                         thick: int = 1, pad: int = 8, radius: int = 10) -> Tuple[int, int]:
        """Render crisp TrueType text with anti-aliasing on a sleek glass pill badge."""
        font_size = max(12, int(scale * 28))
        font = cls.get_font(font_size, bold=True)

        # Measure text using font bounding box
        bbox = font.getbbox(text)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]

        x, y = pos
        x1 = x - pad
        y1 = y - th - pad
        x2 = x + tw + pad
        y2 = y + pad

        w = x2 - x1
        h = y2 - y1
        if w <= 0 or h <= 0:
            return (x, y)

        pil_img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(pil_img)

        # Draw rounded glass pill
        rgb_bg = (int(bg_color[2]), int(bg_color[1]), int(bg_color[0]))
        fill_alpha = int(alpha * 255)
        rgb_col = (int(color[2]), int(color[1]), int(color[0]))

        safe_r = min(radius, w // 2, h // 2)
        draw.rounded_rectangle(
            [0, 0, w - 1, h - 1],
            radius=safe_r,
            fill=(*rgb_bg, fill_alpha),
            outline=(*rgb_col, int(fill_alpha * 0.8)),
            width=1
        )

        # Draw smooth text
        draw.text((pad, pad - bbox[1]), text, font=font, fill=(*rgb_col, 255))
        cls.blend_rgba(img, np.array(pil_img), (x1, y1))

        return (x2, y2)

    @classmethod
    def draw_modern_card_button(cls, img: np.ndarray, rect: Tuple[int, int, int, int],
                                title: str, key_hint: str, icon_text: str,
                                accent_color: Tuple[int, int, int],
                                hovered: bool = False, is_pinching: bool = False,
                                subtext: str = "") -> None:
        """Render an ultra-modern AAA gaming card button with glow and TrueType typography."""
        x1, y1, x2, y2 = rect
        w_b = x2 - x1
        h_b = y2 - y1
        if w_b <= 0 or h_b <= 0:
            return

        cache_key = f"{title}_{key_hint}_{icon_text}_{accent_color}_{hovered}_{is_pinching}_{w_b}_{h_b}_{subtext}"
        if cache_key in cls._cache:
            cls.blend_rgba(img, cls._cache[cache_key], (x1, y1))
            return

        # Render button via PIL with subpixel anti-aliasing
        btn_img = Image.new("RGBA", (w_b, h_b), (0, 0, 0, 0))
        draw = ImageDraw.Draw(btn_img)

        rgb_acc = (int(accent_color[2]), int(accent_color[1]), int(accent_color[0]))

        # Dynamic color schemes
        if is_pinching and hovered:
            # Active clicked/pinch state
            bg_fill = (*rgb_acc, 200)
            border_col = (255, 255, 255, 255)
            border_w = 3
            title_col = (255, 255, 255, 255)
            sub_col = (230, 240, 255, 240)
        elif hovered:
            # Glowing hover state
            bg_fill = (28, 38, 58, 240)
            border_col = (*rgb_acc, 255)
            border_w = 2
            title_col = (*rgb_acc, 255)
            sub_col = (220, 230, 245, 240)
        else:
            # Normal sleek glassmorphic state
            bg_fill = (16, 22, 34, 215)
            border_col = (*rgb_acc, 120)
            border_w = 1
            title_col = (245, 248, 255, 255)
            sub_col = (165, 180, 205, 210)

        # 1. Main Card Body
        draw.rounded_rectangle(
            [1, 1, w_b - 2, h_b - 2],
            radius=14,
            fill=bg_fill,
            outline=border_col,
            width=border_w
        )

        # 2. Subtle top-edge light reflection line
        if not (is_pinching and hovered):
            draw.line([(18, 3), (w_b - 18, 3)], fill=(255, 255, 255, 45 if not hovered else 90), width=1)

        # 3. Category Icon / Pill on the left
        icon_w = 42
        icon_h = h_b - 20
        draw.rounded_rectangle(
            [10, 10, 10 + icon_w, 10 + icon_h],
            radius=10,
            fill=(*rgb_acc, 50 if not hovered else 90),
            outline=(*rgb_acc, 180 if hovered else 90),
            width=1
        )
        font_icon = cls.get_font(11, bold=True)
        ibbox = font_icon.getbbox(icon_text)
        itw = ibbox[2] - ibbox[0]
        ith = ibbox[3] - ibbox[1]
        draw.text(
            (10 + (icon_w - itw) // 2, 10 + (icon_h - ith) // 2 - ibbox[1]),
            icon_text,
            font=font_icon,
            fill=(*rgb_acc, 255) if not (is_pinching and hovered) else (255, 255, 255, 255)
        )

        # 4. Text Content (Title & Subtext)
        font_title = cls.get_font(16, bold=True)
        draw.text((60, 13), title, font=font_title, fill=title_col)

        if subtext:
            font_sub = cls.get_font(11, bold=False)
            draw.text((60, 39), subtext, font=font_sub, fill=sub_col)

        # 5. Keyboard Shortcut Pill Badge on the right
        badge_w = 34
        badge_h = 28
        bx1 = w_b - badge_w - 12
        by1 = (h_b - badge_h) // 2
        draw.rounded_rectangle(
            [bx1, by1, bx1 + badge_w, by1 + badge_h],
            radius=7,
            fill=(25, 35, 52, 220),
            outline=(*rgb_acc, 200 if hovered else 100),
            width=1
        )
        font_badge = cls.get_font(13, bold=True)
        kbbox = font_badge.getbbox(key_hint)
        ktw = kbbox[2] - kbbox[0]
        kth = kbbox[3] - kbbox[1]
        draw.text(
            (bx1 + (badge_w - ktw) // 2, by1 + (badge_h - kth) // 2 - kbbox[1]),
            key_hint,
            font=font_badge,
            fill=(*rgb_acc, 255)
        )

        arr = np.array(btn_img)
        cls._cache[cache_key] = arr
        cls.blend_rgba(img, arr, (x1, y1))

    @classmethod
    def draw_modern_header(cls, img: np.ndarray, w: int, h: int,
                           title: str = "SCREEN SLICER",
                           subtitle: str = "AUGMENTED REALITY GESTURE HUB") -> None:
        """Render the top cyberpunk/arcade glassmorphism header banner."""
        banner_w = 520
        banner_h = 72
        x = (w - banner_w) // 2
        y = 35

        cache_key = f"header_{title}_{subtitle}_{banner_w}_{banner_h}"
        if cache_key not in cls._cache:
            hdr_img = Image.new("RGBA", (banner_w, banner_h), (0, 0, 0, 0))
            draw = ImageDraw.Draw(hdr_img)

            # Glass background with glowing cyan perimeter
            draw.rounded_rectangle(
                [1, 1, banner_w - 2, banner_h - 2],
                radius=18,
                fill=(14, 18, 30, 235),
                outline=(0, 240, 255, 180),
                width=2
            )

            # Top highlight reflection
            draw.line([(30, 3), (banner_w - 30, 3)], fill=(255, 255, 255, 70), width=1)

            # Title
            font_title = cls.get_font(26, bold=True)
            tbbox = font_title.getbbox(title)
            ttw = tbbox[2] - tbbox[0]
            tx = (banner_w - ttw) // 2
            # Glow / drop shadow
            draw.text((tx + 1, 12), title, font=font_title, fill=(0, 100, 150, 180))
            draw.text((tx, 11), title, font=font_title, fill=(0, 240, 255, 255))

            # Subtitle
            font_sub = cls.get_font(10, bold=True)
            sbbox = font_sub.getbbox(subtitle)
            stw = sbbox[2] - sbbox[0]
            sx = (banner_w - stw) // 2
            draw.text((sx, 46), subtitle, font=font_sub, fill=(180, 220, 255, 220))

            # Left and Right Glowing Accent Dots
            draw.circle((24, banner_h // 2), 5, fill=(0, 240, 255, 255))
            draw.circle((banner_w - 24, banner_h // 2), 5, fill=(0, 240, 255, 255))

            cls._cache[cache_key] = np.array(hdr_img)

        cls.blend_rgba(img, cls._cache[cache_key], (x, y))

    @classmethod
    def draw_modern_reticle(cls, img: np.ndarray, pos: Tuple[int, int], is_pinching: bool,
                            color: Tuple[int, int, int] = (0, 240, 255)) -> None:
        """Render a futuristic holographic targeting reticle cursor."""
        x, y = pos
        # Outer rotating / target brackets
        r = 14 if not is_pinching else 8
        ring_col = (0, 255, 100) if is_pinching else color

        # Glowing circles
        cv2.circle(img, (x, y), r + 4, (30, 30, 30), 2, cv2.LINE_AA)
        cv2.circle(img, (x, y), r, ring_col, 2, cv2.LINE_AA)
        cv2.circle(img, (x, y), 3, (255, 255, 255), cv2.FILLED, cv2.LINE_AA)

        # Crosshair ticks
        tick = 6
        cv2.line(img, (x - r - tick, y), (x - r + 1, y), ring_col, 2, cv2.LINE_AA)
        cv2.line(img, (x + r - 1, y), (x + r + tick, y), ring_col, 2, cv2.LINE_AA)
        cv2.line(img, (x, y - r - tick), (x, y - r + 1), ring_col, 2, cv2.LINE_AA)
        cv2.line(img, (x, y + r - 1), (x, y + r + tick), ring_col, 2, cv2.LINE_AA)

    @classmethod
    def draw_modern_status_bar(cls, img: np.ndarray, w: int, h: int, text: str = "") -> None:
        """Render an ultra-clean anti-aliased glass status bar at the bottom."""
        bar_w = min(740, w - 60)
        bar_h = 36
        x = (w - bar_w) // 2
        y = h - 45

        cls.draw_glass_panel(
            img, (x, y), (x + bar_w, y + bar_h),
            color=(12, 16, 26), alpha=0.88, radius=12,
            border_color=(0, 200, 255), border_width=1
        )

        font_bot = cls.get_font(12, bold=False)
        bbox = font_bot.getbbox(text)
        btw = bbox[2] - bbox[0]
        bth = bbox[3] - bbox[1]

        pil_bot = Image.new("RGBA", (btw + 10, bar_h), (0, 0, 0, 0))
        d_bot = ImageDraw.Draw(pil_bot)
        ty = (bar_h - bth) // 2 - bbox[1]
        d_bot.text((5, ty), text, font=font_bot, fill=(190, 215, 240, 240))

        cls.blend_rgba(img, np.array(pil_bot), (w // 2 - btw // 2 - 5, y))
