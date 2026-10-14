"""完成済みサムネイルの真ん中の文字だけを差し替える（素材写真がないとき用）

使い方:
    python3 thumbnail/retitle.py thumbnail/<フォルダ名>

フォルダに次を置く。
    source.png  : 元のサムネイル（1280x720）
    config.json : {"title": "新しい文字", "band": [左, 上, 右, 下]}
                  band は元の半透明の帯の位置（ピクセル）
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
    # 消した跡が目立たないよう、帯を少しだけ濃くする
    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(overlay).rectangle((l, t, r - 1, b - 1), fill=(0, 0, 0, 90))
    canvas = Image.alpha_composite(canvas, overlay)

    # 帯の高さに合わせた文字サイズ（横幅に入りきらなければ縮める）
    target_h = round((b - t) * 0.5)
    size = 200
    while True:
        font = ImageFont.truetype(str(FONT), size)
        fl, ft, fr, fb = font.getbbox(title)
        if (fb - ft <= target_h and fr - fl <= (r - l) - 60) or size <= 30:
            break
        size -= 1
    tw, th = fr - fl, fb - ft
    tx = l + ((r - l) - tw) // 2 - fl
    ty = t + ((b - t) - th) // 2 - ft

    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).text((tx + 4, ty + 5), title, font=font, fill=(0, 0, 0, 230))
    canvas = Image.alpha_composite(canvas, shadow.filter(ImageFilter.GaussianBlur(5)))
    ImageDraw.Draw(canvas).text((tx, ty), title, font=font, fill="white",
                                stroke_width=2, stroke_fill=(30, 30, 30))

    out = folder / "thumbnail.png"
    canvas.convert("RGB").save(out, optimize=True)
    return out


if __name__ == "__main__":
    print(build(Path(sys.argv[1])))
