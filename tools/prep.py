"""캐릭터 준비 — character/ 에 넣은 내 캐릭터 그림을 「색 층」으로 나누고, 로고 글자와 종이 결을 굽는다.

  python tools/prep.py
입력: character/<동작 이름>/*.png (또는 .webp) — 투명 바탕 · 동작마다 폴더 하나 · 폴더 안 그림 = 그 동작의 장(이름 순서대로 재생)
      fonts/ 안의 .ttf/.otf 하나(OFL 같은 재배포 가능한 글꼴) · config.json(word = 로고 글자 · sub = 아래 한 줄)
하는 일:
  1) 모든 그림의 색을 k-평균(k-means++ · 10묶음)으로 → 가장 어두운 묶음 = 선(ink) · 다음 어두운(진할 때만) = deep · 밝고 넓은 = 종이(paper)
     · 채도 0.3 이상 중 넓이 × 채도가 큰 순서 · 비슷한 색상은 하나만 = 키컬러 k1 · k2 · k3 (영상에서 한 색씩 돌아오는 색)
  2) 그림마다 픽셀을 가장 가까운 묶음으로 나눠 층(sil · ink · deep · k1 · k2 · k3)과 원본(full)을 PNG 로 저장(2배로 나눠 줄여 가장자리 부드럽게)
  3) 로고 글자(한 글자씩) · 아래 한 줄 · 종이 결
출력: build/ (masks.js · text.js · palette.js · poses.json · 그림 층) — 지워도 다시 만들 수 있음
"""
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
CH, OUT, FONTS = ROOT / "character", ROOT / "build", ROOT / "fonts"
CFG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
LAYERS = ["ink", "deep", "k1", "k2", "k3"]


def poses():
    ps = {}
    for d in sorted(p for p in CH.iterdir() if p.is_dir()):
        fs = sorted([*d.glob("*.png"), *d.glob("*.webp")])
        if fs:
            ps[d.name] = fs
    if not ps:
        raise SystemExit("character/ 에 동작 폴더가 없습니다 — character/README.md 를 보세요")
    return ps


def palette(ps):
    px = []
    for fs in ps.values():
        for f in fs[:4]:
            a = np.asarray(Image.open(f).convert("RGBA")).reshape(-1, 4)
            px.append(a[a[:, 3] > 200][:, :3])
    px = np.concatenate(px).astype(float)
    px = px[np.random.default_rng(0).choice(len(px), min(len(px), 200000), replace=False)]
    K = 10
    rng = np.random.default_rng(1)
    c = [px[rng.integers(len(px))]]
    for _ in range(K - 1):                                       # k-means++ 시작점(결정론 시드) — 밝은 털이 넓어도 진한 색이 묶음을 갖게
        d2 = np.min(((px[:, None] - np.array(c)[None]) ** 2).sum(2), 1)
        c.append(px[rng.choice(len(px), p=d2 / d2.sum())])
    c = np.array(c)
    for _ in range(30):
        lab = ((px[:, None] - c[None]) ** 2).sum(2).argmin(1)
        c = np.array([px[lab == j].mean(0) if (lab == j).any() else c[j] for j in range(K)])
    share = np.bincount(lab, minlength=K) / len(px)
    lum = c @ np.array([0.2126, 0.7152, 0.0722])
    mx, mn = c.max(1), c.min(1)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1), 0)
    hue = np.array([np.degrees(np.arctan2(np.sqrt(3) * (v[1] - v[2]), 2 * v[0] - v[1] - v[2])) % 360 for v in c])
    ink = int(np.argmin(lum))
    light = [j for j in range(K) if lum[j] > 0.8 * lum.max()]
    paper = max(light, key=lambda j: share[j])
    dark2 = [j for j in np.argsort(lum) if j not in (ink, paper) and lum[j] < 110]
    deep = int(dark2[0]) if dark2 else ink
    cand = sorted([j for j in range(K) if j not in (ink, paper, deep) and sat[j] >= 0.3 and share[j] > 0.005], key=lambda j: -share[j] * sat[j])
    keys = []
    for j in cand:                                               # 비슷한 색(색상 25° 안)은 하나만
        if all(min(abs(hue[j] - hue[k]), 360 - abs(hue[j] - hue[k])) > 25 for k in keys):
            keys.append(j)
    rest = sorted([j for j in range(K) if j not in (ink, paper, deep) and j not in keys], key=lambda j: -sat[j])
    keys = (keys + rest)[:3]
    hexc = lambda v: "#%02X%02X%02X" % tuple(int(round(x)) for x in v)
    role = {}
    for i, j in enumerate(keys):
        role[j] = f"k{i + 1}"
    role.update({ink: "ink", paper: "paper"})
    role.setdefault(deep, "deep")
    for j in range(K):                                           # 나머지 묶음 = 밝으면 종이 · 어두우면 선 · 가운데면 가장 가까운 키컬러
        if j not in role:
            role[j] = "paper" if lum[j] > 150 else ("ink" if lum[j] < 60 else role[min(keys, key=lambda k: ((c[j] - c[k]) ** 2).sum())])
    pal = dict(ink=hexc(c[ink]), deep=hexc(c[deep] if deep != ink else c[ink] * 0.6 + c[paper] * 0.4), paper=hexc(c[paper]), k1=hexc(c[keys[0]]), k2=hexc(c[keys[1]]), k3=hexc(c[keys[2]]),
               night="#1A0B05", night2="#2A130A", cream2="#F3E2CB")
    cen = [(role[j], c[j]) for j in range(K)]
    return pal, cen


def split(im, cen):
    big = im.resize((im.width * 2, im.height * 2), Image.LANCZOS)
    a = np.asarray(big).astype(float)
    C = np.array([v for _, v in cen])
    lab = np.array([r for r, _ in cen])[((a[:, :, None, :3] - C[None, None]) ** 2).sum(-1).argmin(-1)]
    al = a[..., 3] / 255
    out = {"sil": al, **{k: (lab == k) * al for k in LAYERS}}
    return {k: Image.fromarray((m * 255).astype(np.uint8)).resize(im.size, Image.BOX) for k, m in out.items()}


def white(mask):
    return Image.merge("RGBA", (Image.new("L", mask.size, 255),) * 3 + (mask,))


def glyph(text, font, size, SS=3):
    f = ImageFont.truetype(str(font), size * SS)
    l, t, r, b = f.getbbox(text)
    pad = 6 * SS
    im = Image.new("L", (r - l + 2 * pad, b - t + 2 * pad), 0)
    ImageDraw.Draw(im).text((pad - l, pad - t), text, font=f, fill=255)
    im = im.resize((im.width // SS, im.height // SS), Image.LANCZOS)
    return white(im), f.getlength(text) / SS


def main():
    OUT.mkdir(exist_ok=True)
    ps = poses()
    pal, cen = palette(ps)
    pal.update({k: v for k, v in CFG.get("palette", {}).items() if k in pal})   # config.json 의 palette 로 색만 바꿔 끼우기(층 나누기는 그대로)
    mk = {}
    for name, fs in ps.items():
        ims = [Image.open(f).convert("RGBA") for f in fs]
        u = None
        for im in ims:
            bb = im.getchannel("A").point(lambda v: 255 if v > 40 else 0).getbbox()
            u = bb if u is None else (min(u[0], bb[0]), min(u[1], bb[1]), max(u[2], bb[2]), max(u[3], bb[3]))
        box = (max(0, u[0] - 6), max(0, u[1] - 6), min(ims[0].width, u[2] + 6), min(ims[0].height, u[3] + 6))
        (OUT / "mask" / name).mkdir(parents=True, exist_ok=True)
        src = []
        for i, im in enumerate(ims):
            cr = im.crop(box)
            cr.save(OUT / "mask" / name / f"{i:02d}_full.png")
            for k, m in split(cr, cen).items():
                white(m).save(OUT / "mask" / name / f"{i:02d}_{k}.png")
            src.append(f"build/mask/{name}/{i:02d}")
        ms = CFG.get("frame_ms", 100)
        mk[name] = dict(n=len(ims), w=box[2] - box[0], h=box[3] - box[1], src=src, ms=[ms] * len(ims), loop_ms=ms * len(ims))
        print(f"{name}: {len(ims)}장")
    font = next(iter(sorted([*FONTS.glob("*.ttf"), *FONTS.glob("*.otf")])), None)
    if font is None:
        raise SystemExit("fonts/ 에 .ttf 또는 .otf 글꼴을 하나 넣으세요(재배포 가능한 OFL 글꼴 권장)")
    (OUT / "txt").mkdir(exist_ok=True)
    txt = {"logo": [], "sub": None}
    for i, ch in enumerate(CFG["word"]):
        im, adv = glyph(ch, font, 300)
        im.save(OUT / "txt" / f"logo_{i}.png")
        txt["logo"].append(dict(src=f"build/txt/logo_{i}.png", w=im.width, h=im.height, adv=round(adv, 1)))
    im, _ = glyph(CFG.get("sub", " "), font, 54)
    im.save(OUT / "txt" / "sub.png")
    txt["sub"] = dict(src="build/txt/sub.png", w=im.width, h=im.height)
    g = np.random.default_rng(11).normal(0, 1, (512, 512))
    Image.merge("RGBA", (Image.new("L", (512, 512), 40),) * 3 + (Image.fromarray(np.clip(np.abs(g) * 14, 0, 40).astype(np.uint8)),)).save(OUT / "grain.png")
    (OUT / "masks.js").write_text("window.MK = " + json.dumps(mk, ensure_ascii=False) + ";\n", encoding="utf-8")
    (OUT / "text.js").write_text("window.TXT = " + json.dumps(txt, ensure_ascii=False) + ";\n", encoding="utf-8")
    (OUT / "palette.js").write_text("window.PALX = " + json.dumps(pal) + ";\n", encoding="utf-8")
    (OUT / "poses.json").write_text(json.dumps(list(ps)), encoding="utf-8")
    print("팔레트", pal)


if __name__ == "__main__":
    main()
