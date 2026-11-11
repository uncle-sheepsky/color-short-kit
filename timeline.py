"""시간표(단일 값 파일) — 「두루의 색」 숏폼 구조를 내 캐릭터로. ♩180 · 60박 = 600프레임 = 20초 · 1박 = 10프레임.

  python timeline.py        (tools/prep.py 다음)
구조: 0~4박 상징이 그려지며 모임 → 소용돌이 속으로 → 선만 있는 캐릭터 → 키컬러 k1 · k2 · k3 이 한 색씩 돌아옴(8 · 16 · 24박)
      → 몰아치기(32) → 얼굴 더듬기 → 눈 속으로 → 무음 한 박(43) → 원본 색 드롭(44) → 로고(56).
동작은 character/ 폴더 이름 순서대로 자리마다 돌려 씀. 음악 = music/duru_color_chip.wav(이 구조에 맞춰 만든 곡) · 빛점 = music/notes.json.
출력: build/timeline.js · build/timeline.json
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
P = json.loads((ROOT / "build/poses.json").read_text(encoding="utf-8"))
NOTES = [dict(b=n["b"], m=n["m"]) for n in json.loads((ROOT / "music/notes.json").read_text(encoding="utf-8"))]
BPM, FPS, SR, FPB, BEATS = 180, 30, 48000, 10, 60
STOP_B, DROP_B, LOGO_B = 43, 44, 56
pick = lambda i: P[i % len(P)]

COLOR = [dict(b=0, colors=[]), dict(b=8, colors=["k1"]), dict(b=16, colors=["k2"]), dict(b=24, colors=["k3"])]
COLOR += [dict(b=32 + 0.5 * i, colors=[["k1", "k2", "k3"][i % 3]]) for i in range(8)]
COLOR += [dict(b=36 + i, colors=[["k1", "k2"][i % 2]]) for i in range(7)]
COLOR += [dict(b=STOP_B, colors=[]), dict(b=DROP_B, colors=[], full=True)]
SEG = [dict(b0=0, b1=4, kind="assemble"), dict(b0=4, b1=5, kind="zoomthru"), dict(b0=5, b1=8, kind="spiralfield"), dict(b0=8, b1=16, kind="c1"), dict(b0=16, b1=24, kind="c2"),
       dict(b0=24, b1=32, kind="c3"), dict(b0=32, b1=36, kind="strobe"), dict(b0=36, b1=STOP_B, kind="stutter"), dict(b0=STOP_B, b1=DROP_B, kind="stop"),
       dict(b0=DROP_B, b1=LOGO_B, kind="drop"), dict(b0=LOGO_B, b1=BEATS, kind="logo")]
S = []


def shot(cut, b0, b1, comp="full", **kw):
    S.append(dict(cut=cut, b0=b0, b1=b1, comp=comp, mode=kw.pop("mode", "loop"), **kw))


shot(None, 0, 5, "none")
shot(pick(0), 5, 6, "horn", mode="hold", frame=0)
shot(pick(0), 6, 8, "full", frame_bracket=True)
for b0, comps, k in ((8, ["full", "type", "pip", "face", "full", "type", "grid", "full"], 1), (16, ["iris", "halftone", "full", "face", "iris", "halftone", "pair", "full"], 4),
                     (24, ["full", "heart", "full", "tile3", "heart", "face", "tile4", "full"], 7)):
    for i, c in enumerate(comps):
        shot(pick(k + i // 2), b0 + i, b0 + i + 1, c)
SYMS = ["spiral", "cloud", "hoof", "heart", "scarf", "toggle", "blush", "star"]
for i in range(8):
    shot(pick(i), 32 + 0.5 * i, 32.5 + 0.5 * i, "full", sym=SYMS[i])
FACE = pick(len(P) // 2)
for i in range(16):
    shot(FACE, 36 + 0.25 * i, 36.25 + 0.25 * i, "face", mode="hold", frame=0, zstep=1 + 0.03 * i)
for i in range(20):
    shot(FACE, 40 + 0.125 * i, 40.125 + 0.125 * i, "face", mode="hold", frame=0, zstep=1.5 + 0.018 * i)
shot(FACE, 42.5, STOP_B, "eye", mode="hold", frame=0)
shot(None, STOP_B, DROP_B, "none")
b = DROP_B
for i, (comp, n) in enumerate([("full", 2), ("type", 1), ("tile4", 1), ("pip", 1), ("face", 1), ("pair", 1), ("halftone", 1), ("full", 2), ("tile3", 1), ("full", 1)]):
    shot(pick(i), b, b + n, comp, pop=(b == DROP_B))
    b += n
shot(pick(0), LOGO_B, BEATS, "logo")

CLAPS = [x + o for x in range(8, 43, 4) for o in (1, 3)] + [x + o for x in range(DROP_B, LOGO_B, 4) for o in (1, 3)]
PUNCH = [dict(b=float(x), k=0.035) for x in range(8, 32)] + [dict(b=DROP_B + x, k=0.05) for x in range(12)] + [dict(b=0.0, k=0.06), dict(b=5.0, k=0.1), dict(b=DROP_B, k=0.14)]
OUT = dict(meta=dict(bpm=BPM, fps=FPS, sr=SR, bpb=4, fpb=FPB, total_beats=BEATS, total_frames=BEATS * FPB, stage=[1080, 1920], stop_b=STOP_B, drop_b=DROP_B, logo_b=LOGO_B, kick16=[0, 6, 8, 12]),
           color=COLOR, seg=SEG, shots=S, notes=NOTES, claps=CLAPS, stamps=[16 + i for i in range(8)], punch=PUNCH, confetti=dict(b=DROP_B, n=56), logo=dict(b=LOGO_B, at=[540, 470]))
(ROOT / "build/timeline.json").write_text(json.dumps(OUT, ensure_ascii=False, indent=1), encoding="utf-8")
(ROOT / "build/timeline.js").write_text("window.TL = " + json.dumps(OUT, ensure_ascii=False) + ";\n", encoding="utf-8")
print(f"timeline: 600f · 샷 {len(S)} · 동작 {len(P)}")
