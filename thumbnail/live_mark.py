"""ライブ配信用サムネイル：写真の左上に LIVE マークを入れ、明るさを見本に合わせる

使い方:
    python3 thumbnail/live_mark.py thumbnail/<フォルダ名>

フォルダに次を置く。
    photo.jpg（png/webp も可）: 元の写真
    config.json : {"brightness": 185}   # 仕上がりの平均の明るさ（0〜255）。省略すると明るさはそのまま
出力: フォルダ内の thumbnail.png（作り直すたびに上書きする）
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

RED = (228, 52, 39)
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
SS = 4  # なめらかに描くための拡大倍率


def match_brightness(img: Image.Image, target: float) -> Image.Image:
    """白飛びしにくいガンマ補正で、平均の明るさを target に合わせる"""
    a = np.asarray(img).astype(float) / 255
    lum = lambda x: (x @ [0.299, 0.587, 0.114]).mean() * 255
    lo, hi = 0.2, 1.0
    for _ in range(30):
        g = (lo + hi) / 2
        if lum(a ** g) > target:
            lo = g
        else:
            hi = g
    return Image.fromarray((a ** g * 255).round().astype(np.uint8))


def draw_live_mark(img: Image.Image) -> Image.Image:
    """見本サムネ（横幅 1080 px 基準）と同じ位置・大きさで LIVE マークを描く"""
    s = img.width / 1080
    layer = Image.new("RGBA", (img.width * SS, img.height * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    k = s * SS
    cx, cy = 113 * k, 107 * k
    ring_r, ring_w, circle_r = 96 * k, 4 * k, 62 * k
    d.ellipse((cx - ring_r, cy - ring_r, cx + ring_r, cy + ring_r), outline=RED, width=round(ring_w))
    d.ellipse((cx - circle_r, cy - circle_r, cx + circle_r, cy + circle_r), fill=RED)
    d.polygon([(95 * k, 80 * k), (95 * k, 134 * k), (141 * k, 107 * k)], fill="white")
    box = (41 * k, 150 * k, 185 * k, 210 * k)
    d.rectangle(box, fill=RED)
    font = ImageFont.truetype(FONT, round(46 * k))
    l, t, r, b = d.textbbox((0, 0), "LIVE", font=font)
    tx = (box[0] + box[2]) / 2 - (l + r) / 2
    ty = (box[1] + box[3]) / 2 - (t + b) / 2
    d.text((tx, ty), "LIVE", font=font, fill="white")
    layer = layer.resize(img.size, Image.LANCZOS)
    return Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")


def build(folder: Path) -> Path:
    config = json.loads((folder / "config.json").read_text(encoding="utf-8"))
    photo = next(p for p in sorted(folder.glob("photo.*")) if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"})
    img = Image.open(photo).convert("RGB")
    if "brightness" in config:
        img = match_brightness(img, config["brightness"])
    out = folder / "thumbnail.png"
    draw_live_mark(img).save(out, optimize=True)
    return out


if __name__ == "__main__":
    print(build(Path(sys.argv[1])))
