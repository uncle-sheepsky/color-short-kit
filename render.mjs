// 렌더러 — comp.html(1080×1920) 을 프레임마다 시크해 캔버스 픽셀을 굽는다. 래스터 = SwiftShader(소프트웨어 · 결정론) · 판정 = 페이지 안 원시 픽셀 해시.
// 사용:
//   node render.mjs --spot 0,100,450 [--out spot]          : 지정 프레임만 PNG 로(확인용)
//   node render.mjs --video out/video.mp4                  : 전 프레임 → ffmpeg(H.264) + 프레임별 픽셀 해시 gates/sha_fwd.json
//   node render.mjs --sha-only --order rev --name sha_rev  : 해시만 역순(같은 프레임이 같은 픽셀인지 두 번 대조)
import http from 'http';
import fs from 'fs';
import path from 'path';
import { spawn } from 'child_process';
import { fileURLToPath, pathToFileURL } from 'url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const EP = HERE;
const pw = await import(pathToFileURL(path.join(HERE, 'node_modules', 'playwright', 'index.js')).href);
const { chromium } = pw.default ?? pw;

const arg = (k, d) => { const i = process.argv.indexOf(k); return i > 0 ? process.argv[i + 1] : d; };
const has = k => process.argv.includes(k);
const TL = JSON.parse(fs.readFileSync(path.join(HERE, 'build', 'timeline.json'), 'utf8'));
const TOTAL = TL.meta.total_frames, FPS = TL.meta.fps, [VW, VH] = TL.meta.stage;
const SPOT = arg('--spot', null), VIDEO = arg('--video', null), SHA_ONLY = has('--sha-only');
const ORDER = arg('--order', 'fwd'), FROM = +arg('--from', 0), TO = +arg('--to', TOTAL - 1);

const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.png': 'image/png', '.jpg': 'image/jpeg', '.json': 'application/json' };
const srv = http.createServer((req, res) => {
  const p = path.join(EP, decodeURIComponent(new URL(req.url, 'http://x').pathname));
  if (!p.startsWith(EP) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); res.end(); return; }
  res.writeHead(200, { 'content-type': MIME[path.extname(p)] || 'application/octet-stream' });
  fs.createReadStream(p).pipe(res);
});
await new Promise(r => srv.listen(0, '127.0.0.1', r));
const PORT = srv.address().port;

const FLAGS = ['--disable-lcd-text', '--disable-font-subpixel-positioning', '--force-color-profile=srgb', '--disable-partial-raster',
  '--disable-skia-runtime-opts', '--disable-gpu-rasterization', '--use-gl=angle', '--use-angle=swiftshader', '--disable-gpu'];
const browser = await chromium.launch({ args: FLAGS });
const page = await browser.newPage({ viewport: { width: VW, height: VH }, deviceScaleFactor: 1 });
const errs = [];
page.on('pageerror', e => errs.push(e.message));
page.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
await page.goto(`http://127.0.0.1:${PORT}/comp.html`, { waitUntil: 'load' });
await page.waitForFunction('window.__ready === true || window.__err', null, { timeout: 180000 });
const loadErr = await page.evaluate('window.__err || null');
if (loadErr) { console.error('로드 오류:', loadErr); await browser.close(); srv.close(); process.exit(2); }
if (errs.length) { console.error('페이지 오류:', errs); process.exit(2); }
const t0 = Date.now();

if (SPOT) {
  const out = path.join(HERE, arg('--out', 'spot')); fs.mkdirSync(out, { recursive: true });
  for (const f of SPOT.split(',').map(Number)) {
    const b64 = await page.evaluate(ff => { window.__seekF(ff); return document.getElementById('cv').toDataURL('image/png').split(',')[1]; }, f);
    fs.writeFileSync(path.join(out, `f${String(f).padStart(4, '0')}.png`), Buffer.from(b64, 'base64'));
  }
  console.log(`스팟 ${SPOT.split(',').length}장 · ${((Date.now() - t0) / 1000).toFixed(1)}s → ${out}`);
} else {
  let frames = []; for (let f = FROM; f <= TO; f++) frames.push(f);
  if (ORDER === 'rev') frames.reverse();
  let ff = null;
  if (VIDEO && !SHA_ONLY) {
    fs.mkdirSync(path.dirname(path.join(HERE, VIDEO)), { recursive: true });
    ff = spawn('ffmpeg', ['-v', 'error', '-y', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'png', '-i', '-',
      '-vf', 'scale=in_range=full:out_range=tv:out_color_matrix=bt709,format=yuv420p', '-c:v', 'libx264', '-preset', 'slow', '-crf', '15',
      '-profile:v', 'high', '-level', '4.2', '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-color_range', 'tv',
      '-r', String(FPS), path.join(HERE, VIDEO)], { stdio: ['pipe', 'inherit', 'inherit'] });
  }
  const shas = {};
  for (let k = 0; k < frames.length; k++) {
    const f = frames[k];
    if (ff) {
      const r = await page.evaluate(x => { window.__seekF(x); return [window.__hash(), document.getElementById('cv').toDataURL('image/png').split(',')[1]]; }, f);
      shas[f] = r[0];
      if (!ff.stdin.write(Buffer.from(r[1], 'base64'))) await new Promise(res => ff.stdin.once('drain', res));
    } else {
      shas[f] = await page.evaluate(x => { window.__seekF(x); return window.__hash(); }, f);
    }
    if (k % 120 === 0) process.stdout.write(`  ${k}/${frames.length} f${f} ${((Date.now() - t0) / 1000).toFixed(0)}s\n`);
  }
  if (ff) { ff.stdin.end(); await new Promise(res => ff.on('close', res)); }
  fs.mkdirSync(path.join(HERE, 'gates'), { recursive: true });
  const name = arg('--name', `sha_${ORDER}`);
  fs.writeFileSync(path.join(HERE, 'gates', `${name}.json`), JSON.stringify(shas));
  console.log(`완료 ${frames.length}프레임 · ${((Date.now() - t0) / 1000).toFixed(1)}s · gates/${name}.json`);
}
await browser.close(); srv.close();
if (errs.length) { console.error('페이지 오류:', errs); process.exit(2); }
