"""完成済みサムネイルの真ん中の文字だけを差し替える（素材写真がないとき用）

使い方:
    python3 thumbnail/retitle.py thumbnail/<フォルダ名>

フォルダに次を置く。
    source.png  : 元のサムネイル（1280x720）
    config.json : {"title": "新しい文字", "band": [左, 上, 右, 下]}
                  band は元の半透明の帯の位置（ピクセル）
                  2 行にするときは title を "1行目\n2行目" にし、"band_height" で帯の高さを指定
出力: フォルダ内の thumbnail.png（作り直すたびに上書きする）
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
FONT = HERE / "fonts" / "NotoSerifJP-Black.ttf"


def erase_text(band: np.ndarray) -> np.ndarray:
    """帯の中の白い文字を、周りの暗い色でなじませて消す"""
    lum = band.mean(axis=2)
    mask = Image.fromarray(((lum > 90) * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(9))
    mask = np.asarray(mask) > 0
    out = band.astype(float)
    known = ~mask
    out[mask] = 0
    # 周りから少しずつ色を流し込む（簡易インペイント）
    for _ in range(400):
        pad = np.pad(out, ((1, 1), (1, 1), (0, 0)), mode="edge")
        kp = np.pad(known, 1, mode="edge").astype(float)
        s = (pad[:-2, 1:-1] * kp[:-2, 1:-1, None] + pad[2:, 1:-1] * kp[2:, 1:-1, None]
             + pad[1:-1, :-2] * kp[1:-1, :-2, None] + pad[1:-1, 2:] * kp[1:-1, 2:, None])
        n = kp[:-2, 1:-1] + kp[2:, 1:-1] + kp[1:-1, :-2] + kp[1:-1, 2:]
        fill = mask & (n > 0)
        out[fill] = s[fill] / n[fill][:, None]
        known = known | fill
    # 消した跡をなめらかに
    blurred = np.asarray(Image.fromarray(out.astype(np.uint8)).filter(ImageFilter.GaussianBlur(10))).astype(float)
    out[mask] = blurred[mask]
    return out.astype(np.uint8)


def build(folder: Path) -> Path:
    config = json.loads((folder / "config.json").read_text(encoding="utf-8"))
    title = config["title"]
    l, t, r, b = config["band"]
    img = Image.open(folder / "source.png").convert("RGB")

    arr = np.asarray(img).copy()
    arr[t:b, l:r] = erase_text(arr[t:b, l:r])
    canvas = Image.fromarray(arr).convert("RGBA")
    # 2 行以上のときは帯を上下に広げる（新しく広げた部分は元の帯と同じ濃さにする）
    lines = title.split("\n")
    nt, nb = t, b
    if "band_height" in config:
        cy = (t + b) // 2
        nt, nb = cy - config["band_height"] // 2, cy + config["band_height"] // 2
    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.rectangle((l, nt, r - 1, nb - 1), fill=(0, 0, 0, 185))
    # 消した跡が目立たないよう、元の帯の部分も少しだけ濃くする
    od.rectangle((l, t, r - 1, b - 1), fill=(0, 0, 0, 90))
    canvas = Image.alpha_composite(canvas, overlay)

    # 帯の高さに合わせた文字サイズ（横幅に入りきらなければ縮める）
    gap_ratio = 0.35  # 行と行のあいだ（文字の高さに対する割合）
    fill = 0.5 if len(lines) == 1 else 0.68  # 帯の高さのうち文字が占める割合
    target_h = round((nb - nt) * fill / (len(lines) + gap_ratio * (len(lines) - 1)))
    size = 200
    while True:
        font = ImageFont.truetype(str(FONT), size)
        boxes = [font.getbbox(line) for line in lines]
        line_h = max(fb - ft for _, ft, _, fb in boxes)
        widest = max(fr - fl for fl, _, fr, _ in boxes)
        if (line_h <= target_h and widest <= (r - l) - 60) or size <= 30:
            break
        size -= 1
    gap = round(line_h * gap_ratio)
    block_h = line_h * len(lines) + gap * (len(lines) - 1)
    y = nt + ((nb - nt) - block_h) // 2

    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    positions = []
    for line, (fl, ft, fr, fb) in zip(lines, boxes):
        tx = l + ((r - l) - (fr - fl)) // 2 - fl
        ty = y + (line_h - (fb - ft)) // 2 - ft
        positions.append((line, tx, ty))
        sd.text((tx + 4, ty + 5), line, font=font, fill=(0, 0, 0, 230))
        y += line_h + gap
    canvas = Image.alpha_composite(canvas, shadow.filter(ImageFilter.GaussianBlur(5)))
    d = ImageDraw.Draw(canvas)
    for line, tx, ty in positions:
        d.text((tx, ty), line, font=font, fill="white", stroke_width=2, stroke_fill=(30, 30, 30))

    out = folder / "thumbnail.png"
    canvas.convert("RGB").save(out, optimize=True)
    return out


if __name__ == "__main__":
    print(build(Path(sys.argv[1])))
