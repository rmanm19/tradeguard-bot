#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
سازندهٔ بنرهای تبلیغاتی TradeGuard (۱۰۸۰×۱۰۸۰).

سه کریتیو آماده برای تبلیغ کانال/ربات در تلگرام و توییتر ساخته می‌شود.
هر تصویر بدون هیچ عددِ ساختگی و بدون وعدهٔ سود است؛ فقط همان چیزی را
می‌گوید که در محصول واقعاً وجود دارد.

اجرا:
    python3 tools/make_ads.py            # همه
    python3 tools/make_ads.py ad_radar   # فقط یکی

خروجی: docs/assets/ads/*.png
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import arabic_reshaper
from bidi.algorithm import get_display
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
PRO = HERE.parent
DOCS = PRO.parent / "docs"
OUT = DOCS / "assets" / "ads"
FONTS = PRO / "assets" / "fonts"
LOGO = PRO / "bot_avatar.png"

W = H = 1080
BG_TOP = (7, 12, 22)
BG_BOT = (10, 34, 40)
MINT = (56, 224, 178)
MINT_SOFT = (120, 240, 205)
WHITE = (244, 250, 248)
GREY = (150, 172, 172)

F_BLACK = FONTS / "Vazirmatn-Black.ttf"
F_BOLD = FONTS / "Vazirmatn-Bold.ttf"
F_MED = FONTS / "Vazirmatn-Medium.ttf"


def rtl(text: str) -> str:
    """متن فارسی را برای رندر در Pillow آماده می‌کند."""
    return get_display(arabic_reshaper.reshape(text))


def font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size)


def gradient(size: tuple[int, int]) -> Image.Image:
    """گرادیان عمودی تیره + هالهٔ سبز گوشهٔ بالا-راست."""
    w, h = size
    img = Image.new("RGB", (w, h), BG_TOP)
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / max(h - 1, 1)
        # آسانسور نرم برای اینکه پایین تصویر سبزِ عمیق شود
        t = t ** 1.25
        d.line(
            [(0, y), (w, y)],
            fill=(
                int(BG_TOP[0] + (BG_BOT[0] - BG_TOP[0]) * t),
                int(BG_TOP[1] + (BG_BOT[1] - BG_TOP[1]) * t),
                int(BG_TOP[2] + (BG_BOT[2] - BG_TOP[2]) * t),
            ),
        )
    # هالهٔ نور
    glow = Image.new("RGB", (w, h), (0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse([w * 0.45, -h * 0.35, w * 1.35, h * 0.55], fill=(18, 96, 84))
    glow = glow.filter(ImageFilter.GaussianBlur(140))
    return Image.blend(img, Image.blend(img, glow, 0.55), 0.65)


def radar(d: ImageDraw.ImageDraw, cx: float, cy: float, rmax: float, alpha: int = 26) -> None:
    """حلقه‌های رادار + خطوط ساعت."""
    for i in range(1, 5):
        r = rmax * i / 4
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(56, 224, 178, alpha), width=2)
    for k in range(12):
        a = math.radians(k * 30)
        x1, y1 = cx + math.cos(a) * rmax * 0.16, cy + math.sin(a) * rmax * 0.16
        x2, y2 = cx + math.cos(a) * rmax, cy + math.sin(a) * rmax
        d.line([(x1, y1), (x2, y2)], fill=(56, 224, 178, alpha // 2), width=1)


def wrap_fa(text: str, f: ImageFont.FreeTypeFont, max_w: int) -> list[str]:
    """شکستن خط فارسی بر اساس کلمه (عرض واقعی رندرشده)."""
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if f.getlength(rtl(trial)) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def pill(d: ImageDraw.ImageDraw, xy, text: str, f, fg=(6, 26, 22), bg=MINT, pad_x=44, pad_y=24):
    x, y = xy
    tw = f.getlength(rtl(text))
    box = [x, y, x + tw + pad_x * 2, y + f.size + pad_y * 2]
    d.rounded_rectangle(box, radius=(box[3] - box[1]) // 2, fill=bg)
    d.text((box[0] + pad_x, y + pad_y), rtl(text), font=f, fill=fg)
    return box


def logo_badge(size: int = 190) -> Image.Image:
    """لوگوی برند را دایره‌ای و با حلقهٔ نئونی برمی‌گرداند (RGBA)."""
    src = Image.open(LOGO).convert("RGBA").resize((size, size), Image.LANCZOS)
    mask = Image.new("L", (size * 4, size * 4), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, size * 4 - 1, size * 4 - 1], fill=255)
    mask = mask.resize((size, size), Image.LANCZOS)
    out = Image.new("RGBA", (size + 24, size + 24), (0, 0, 0, 0))
    ring = Image.new("RGBA", out.size, (0, 0, 0, 0))
    ImageDraw.Draw(ring).ellipse([0, 0, out.size[0] - 1, out.size[1] - 1], outline=MINT + (255,), width=6)
    out.paste(src, (12, 12), mask)
    return Image.alpha_composite(out, ring)


def compose(name: str, kicker: str, title: str, lines: list[str], cta: str, *, cmd: str = "", badge=True, show_radar=True):
    img = gradient((W, H)).convert("RGBA")
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    if show_radar:
        radar(d, W * 0.78, H * 0.20, W * 0.46)
    img = Image.alpha_composite(img, layer)

    d = ImageDraw.Draw(img)
    y = 96
    if badge:
        b = logo_badge()
        img.alpha_composite(b, (W - b.size[0] - 84, y - 24))
        d = ImageDraw.Draw(img)

    # برند بالای تصویر (چپ)
    f_brand = font(F_BOLD, 40)
    d.text((84, y), "TradeGuard", font=f_brand, fill=WHITE)
    d.text((84, y + 54), rtl("رادار ریسک بازار"), font=font(F_MED, 30), fill=MINT_SOFT)

    y = 356
    d.text((84, y), rtl(kicker), font=font(F_BOLD, 34), fill=MINT)
    y += 74
    f_title = font(F_BLACK, 104 if len(title) <= 18 else 92)
    for ln in wrap_fa(title, f_title, W - 168):
        d.text((84, y), rtl(ln), font=f_title, fill=WHITE)
        y += int(f_title.size * 1.34)

    y += 34
    f_body = font(F_MED, 40)
    for ln in lines:
        for part in wrap_fa(ln, f_body, W - 240):
            d.text((84, y), rtl(part), font=f_body, fill=GREY)
            y += 64
        y += 8

    if cmd:
        # دستور انگلیسی باید چپ‌به‌راست رندر شود، وگرنه حروف جابه‌جا می‌شوند
        f_cmd = font(F_BOLD, 36)
        box = pill(d, (84, y + 16), cmd, f_cmd, fg=(6, 26, 22), bg=(230, 255, 246), pad_x=36, pad_y=18)
        d.text((box[2] + 24, y + 30), rtl("در ربات بزن"), font=font(F_MED, 32), fill=(120, 200, 180))

    pill(d, (84, H - 210), cta, font(F_BOLD, 40))
    d.text((84, H - 106), "t.me/tradeguard1", font=font(F_MED, 32), fill=(96, 130, 130))

    # نوار پایین
    d.line([(0, H - 8), (W, H - 8)], fill=MINT, width=8)

    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{name}.png"
    img.convert("RGB").save(path, quality=92, optimize=True)
    print(f"✅ {path.relative_to(PRO.parent)}")
    return path


CREATIVES = {
    "ad_radar": dict(
        kicker="داخل تلگرام، بدون نصب چیزی",
        title="رادار زندهٔ بازار",
        lines=["فاندینگ، آپن‌اینترست و ترس و طمع — هر ۳ ساعت یک گزارش کوتاه"],
        cta="شروع رایگان",
        cmd="/scan",
    ),
    "ad_risk": dict(
        kicker="قانون طلایی مدیریت ریسک",
        title="قانون ۱ درصد",
        lines=["ریسک هر معامله ۱٪؛ حتی پنج ضرر پشت‌سرهم فقط ۵٪ حساب است"],
        cta="محاسبهٔ حجم",
        cmd="/lot",
    ),
    "ad_reward": dict(
        kicker="هدیهٔ عضویت کانال",
        title="۷ روز پرو، هدیه",
        lines=["عضو کانال شو، بعد در ربات این دستور را بزن"],
        cta="دریافت هدیه",
        cmd="/checkjoin",
    ),
}


def main(argv: list[str]) -> int:
    names = argv[1:] or list(CREATIVES)
    for n in names:
        if n not in CREATIVES:
            print(f"❓ کریتیو ناشناخته: {n} (موجود: {', '.join(CREATIVES)})")
            return 2
        compose(n, **CREATIVES[n])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
