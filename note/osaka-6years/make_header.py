"""note見出し画像（1280x670）: 【大阪に来て6年。大阪の人は優しい】

実行: python3 note/osaka-6years/make_header.py → 同じフォルダに header.png（上書き）
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1280, 670
HERE = Path(__file__).resolve().parent
FONT = HERE.parent.parent / "thumbnail" / "fonts" / "NotoSerifJP-Black.ttf"

BG_TOP, BG_BOTTOM = (252, 236, 214), (246, 196, 150)  # 夕焼けっぽい暖色
INK = (58, 38, 30)
ACCENT = (200, 70, 50)
CITY = (92, 60, 52)


def gradient() -> Image.Image:
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / (H - 1)
        d.line([(0, y), (W, y)], fill=tuple(round(a + (b - a) * t) for a, b in zip(BG_TOP, BG_BOTTOM)))
    return img


def skyline(d: ImageDraw.ImageDraw, base: int):
    """下端に大阪の街並み（真ん中右寄りに通天閣）"""
    import random
    rnd = random.Random(6)
    cx = 1080
    x = 0
    while x < W:
        w = rnd.randint(40, 90)
        h = rnd.randint(30, 90)
        if not (cx - 110 < x + w and x < cx + 110):  # 通天閣のまわりは空ける
            d.rectangle([x, base - h, x + w, H], fill=CITY)
            for _ in range(w * h // 900):  # 窓のあかり（ビルの中だけ）
                wx, wy = rnd.randint(x + 6, x + w - 12), rnd.randint(base - h + 10, H - 14)
                d.rectangle([wx, wy, wx + 5, wy + 7], fill=(255, 214, 140))
        x += w + rnd.randint(0, 6)
    # 通天閣
    d.polygon([(cx - 70, H), (cx - 18, base - 120), (cx + 18, base - 120), (cx + 70, H)], fill=CITY)
    d.rectangle([cx - 30, base - 170, cx + 30, base - 120], fill=CITY)       # 展望台
    d.rectangle([cx - 38, base - 178, cx + 38, base - 168], fill=CITY)
    d.rectangle([cx - 14, base - 230, cx + 14, base - 178], fill=CITY)       # 塔の上部
    d.ellipse([cx - 20, base - 252, cx + 20, base - 222], fill=CITY)         # てっぺん
    d.line([(cx, base - 270), (cx, base - 250)], fill=CITY, width=4)          # アンテナ
    # 足元のアーチ
    d.pieslice([cx - 34, base - 60, cx + 34, base + 8], 180, 360, fill=BG_BOTTOM)


def draw_text_centered(d, y, text, size, fill, spacing=0):
    font = ImageFont.truetype(str(FONT), size)
    widths = [d.textlength(c, font=font) for c in text]
    total = sum(widths) + spacing * (len(text) - 1)
    x = (W - total) / 2
    for c, w in zip(text, widths):
        d.text((x, y), c, font=font, fill=fill)
        x += w + spacing
    return font


def build() -> Path:
    img = gradient()
    d = ImageDraw.Draw(img)

    # 夕日
    sun = Image.new("L", (W, H), 0)
    ImageDraw.Draw(sun).ellipse([960, 420, 1200, 660], fill=255)
    img.paste((250, 150, 100), (0, 0), sun.filter(ImageFilter.GaussianBlur(2)))

    skyline(d, H - 40)

    # 文字（影つき）
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    draw_text_centered(sd, 121, "大阪に来て6年。", 84, (120, 60, 30, 90), 4)
    draw_text_centered(sd, 233, "大阪の人は優しい", 108, (120, 60, 30, 90), 6)
    img.paste(shadow, (0, 0), shadow.filter(ImageFilter.GaussianBlur(6)))

    d = ImageDraw.Draw(img)
    draw_text_centered(d, 70, "OSAKA  ESSAY", 26, ACCENT, 8)
    draw_text_centered(d, 118, "大阪に来て6年。", 84, INK, 4)
    draw_text_centered(d, 230, "大阪の人は優しい", 108, ACCENT, 6)
    d.line([(W / 2 - 60, 385), (W / 2 + 60, 385)], fill=INK, width=3)

    out = HERE / "header.png"
    img.save(out)
    return out


if __name__ == "__main__":
    print(build())
