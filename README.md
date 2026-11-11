# color-short-kit — 내 캐릭터로 만드는 20초 숏폼 템플릿

**원하는 캐릭터 그림을 넣으면, 그 캐릭터의 색으로 20초 세로 숏폼(1080×1920 · 30fps)을 만들어 주는 템플릿입니다.**
유튜브 채널 「아낌없이 주는 두루」의 숏폼 「두루의 색」을 만든 구조 그대로이고, 캐릭터 자리만 여러분의 그림으로 채우게 열어 두었습니다.

## 무엇이 만들어지나
- 선만 있는 캐릭터에 **캐릭터 자신의 색이 하나씩 돌아오고**, 드롭에서 원본 색이 한꺼번에 터지는 20초(♩180 · 60박).
- 색은 여러분 그림에서 자동으로 뽑습니다(가장 어두운 색 = 선 · 가장 밝은 색 = 종이 · 채도 높은 색 세 가지 = 하나씩 돌아오는 색).
- 연출: 상징이 그려지며 모임 → 소용돌이 속으로 → 리본 와이프 · 화면 속 화면 · 거대 글자 · 망점 · 동그라미로 열림 · 하트 창 · 타일 · 빛점(음표) · 조각 어긋남 → 얼굴로 다가감 → 무음 한 박 → 드롭 → 로고.
- 음악 `music/duru_color_chip.wav` 은 이 구조에 맞춰 만든 곡입니다(파이썬으로 합성 · 샘플 없음 · CC0). 화면의 모든 사건이 이 곡의 박에 맞춰져 있습니다.

## 준비물
- Node.js 18+ · Python 3.10+ (`pip install numpy pillow`) · ffmpeg
- `npm install` (playwright · gsap) · 처음 한 번 `npx playwright install chromium`

## 만드는 순서
1. **캐릭터 넣기** — `character/<동작 이름>/00.png, 01.png …`(투명 바탕 PNG). 동작 폴더 여러 개 = 장면마다 돌려 씁니다. 자세한 건 [`character/README.md`](character/README.md).
2. **글꼴 넣기** — `fonts/` 에 로고용 글꼴 하나(.ttf/.otf · OFL 같은 재배포 가능한 글꼴).
3. **로고 글자** — `config.json` 의 `word`(큰 로고 · 한 글자씩 튀어나옴) · `sub`(아래 한 줄).
4. 실행
```bash
python tools/prep.py
python timeline.py
node render.mjs --spot 0,100,250,450,520 --out spot
node render.mjs --video out/video.mp4
node render.mjs --sha-only --order rev --name sha_rev
python tools/mux.py
```
`out/short.mp4` 가 완성본입니다(음악 −14 LUFS 기준). `spot/` 그림으로 먼저 확인하고 전체를 굽는 걸 권합니다.

## 바꿔 보기
- 뽑힌 색이 마음에 안 들면 `config.json` 에 `"palette": {"k1": "#E83437", "k3": "#E9A795"}` 처럼 적어 그 색만 바꿉니다(`python tools/prep.py` 가 뽑은 팔레트를 출력하니 보고 고치세요). 쓸 수 있는 이름 = `ink` · `deep` · `paper` · `k1` · `k2` · `k3`.
- 장면 순서 · 구도 · 상징 = `timeline.py`(값만 바꾸면 화면이 따라옴) · 그리는 방식 = `comp.html`.
- 모든 화면은 프레임 번호의 순수 함수입니다 — 같은 입력이면 같은 픽셀(`render.mjs` 가 정방향 · 역방향 해시로 대조).
- 번쩍임: 이 구조는 1초에 번쩍임(반대 방향 밝기 변화 한 쌍) 3번 이하로 맞춰져 있습니다. 장면을 크게 바꾸면 다시 확인하세요(WCAG 2.3.1).

## 라이선스
코드 · 음악 = CC0 1.0(마음대로 쓰세요). 여러분이 넣는 캐릭터 그림 · 글꼴의 권리는 각자의 것입니다.
화면 코드와 음악은 Claude(Anthropic)로 만들었습니다.
