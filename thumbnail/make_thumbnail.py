"""YouTubeサムネイル生成（4分割写真＋中央に半透明帯＋明朝体タイトル）

使い方:
    python3 thumbnail/make_thumbnail.py thumbnail/andante

フォルダ内に 1〜4 の写真（拡張子は jpg/png/webp など何でも可）と config.json を置く。
    1 = 左上 / 2 = 右上 / 3 = 左下 / 4 = 右下
config.json の例:
    {"title": "旅と暮らしの本屋 アンダンテ",
     "crops": {"2": [0.12, 0.27, 0.853, 1.0]}}
    crops は写真ごとの切り抜き範囲（元画像に対する割合: 左, 上, 右, 下）。指定なしは中央基準
    0〜1 の外を指定すると写真を縮めて入れ、はみ出した部分は写真の上端の色で埋める
出力: フォルダ内の thumbnail.png（1280x720）。作り直すたびに上書きする
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageEnhance

W, H = 1280, 720
HERE = Path(__file__).resolve().parent
FONT = HERE / "fonts" / "NotoSerifJP-Black.ttf"

MAX_FONT = 110
MAX_TEXT_W = 1160
BRIGHTNESS = 1.18  # 写真の明るさ（1.0 = 元のまま）

def find_photo(folder: Path, n: int):
    for p in sorted(folder.glob(f"{n}.*")):
        if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
            return p
    return None


def cover(img: Image.Image, w: int, h: int) -> Image.Image:
    """中央基準でトリミングして w x h を埋める"""
    s = max(w / img.width, h / img.height)
    img = img.resize((round(img.width * s), round(img.height * s)), Image.LANCZOS)
    l, t = (img.width - w) // 2, (img.height - h) // 2
    return img.crop((l, t, l + w, t + h))


def crop_with_fill(img: Image.Image, box) -> Image.Image:
    """割合で切り抜く。範囲が写真の外にはみ出した部分は、写真の上端の色（店内なら白い天井色）で埋める"""
    l, t, r, b = (round(v * n) for v, n in zip(box, (img.width, img.height) * 2))
    if l >= 0 and t >= 0 and r <= img.width and b <= img.height:
        return img.crop((l, t, r, b))
    top = img.crop((0, 0, img.width, max(1, img.height // 50))).resize((1, 1), Image.BOX)
    bg = Image.new("RGB", (r - l, b - t), top.getpixel((0, 0)))
    bg.paste(img, (-l, -t))
    return bg


def placeholder(n: int, w: int, h: int) -> Image.Image:
    img = Image.new("RGB", (w, h), (90 + n * 20, 80 + n * 15, 70 + n * 10))
    ImageDraw.Draw(img).text((20, 20), f"PHOTO {n}", fill="white",
                             font=ImageFont.truetype(str(FONT), 40))
    return img


def build(folder: Path) -> Path:
    config = json.loads((folder / "config.json").read_text(encoding="utf-8"))
    title = config["title"]
    crops = {int(k): v for k, v in config.get("crops", {}).items()}

    canvas = Image.new("RGB", (W, H))
    cw, ch = W // 2, H // 2
    for i, (x, y) in enumerate([(0, 0), (cw, 0), (0, ch), (cw, ch)], start=1):
        p = find_photo(folder, i)
        if p:
            img = Image.open(p).convert("RGB")
            if i in crops:
                img = crop_with_fill(img, crops[i])
            tile = cover(img, cw, ch)
        else:
            tile = placeholder(i, cw, ch)
        # 参考サムネと同じく少しだけ鮮やかに
        tile = ImageEnhance.Brightness(tile).enhance(BRIGHTNESS)
        tile = ImageEnhance.Color(tile).enhance(1.12)
        tile = ImageEnhance.Contrast(tile).enhance(1.05)
        canvas.paste(tile, (x, y))

    # 文字サイズを横幅に収まるよう自動調整
    size = MAX_FONT
    while True:
        font = ImageFont.truetype(str(FONT), size)
        l, t, r, b = font.getbbox(title)
        if r - l <= MAX_TEXT_W or size <= 40:
            break
        size -= 2
    tw, th = r - l, b - t

    # 半透明の黒い帯（文字幅＋余白）
    pad_x, pad_y = 30, 34
    bw, bh = tw + pad_x * 2, th + pad_y * 2
    bx, by = (W - bw) // 2, (H - bh) // 2
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(overlay).rectangle((bx, by, bx + bw, by + bh), fill=(0, 0, 0, 150))
    canvas = Image.alpha_composite(canvas.convert("RGBA"), overlay)

    tx, ty = (W - tw) // 2 - l, (H - th) // 2 - t

    # ぼかした影で文字を浮かせる
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).text((tx + 5, ty + 6), title, font=font, fill=(0, 0, 0, 230))
    shadow = shadow.filter(ImageFilter.GaussianBlur(6))
    canvas = Image.alpha_composite(canvas, shadow)

    d = ImageDraw.Draw(canvas)
    d.text((tx, ty), title, font=font, fill="white",
           stroke_width=2, stroke_fill=(30, 30, 30))

    out = folder / "thumbnail.png"
    canvas.convert("RGB").save(out, optimize=True)
    return out


if __name__ == "__main__":
    folder = Path(sys.argv[1] if len(sys.argv) > 1 else HERE / "andante")
    print(build(folder))
