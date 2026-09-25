// node render.js S03 [--only 0.5,2,4] [--fps 24] [--from t] [--to t]
// Renders a shot in headless Chromium (SwiftShader WebGL) and encodes out/shots/S03.mp4 (or probe PNGs with --only).
const { chromium } = require(require('child_process').execSync('npm root -g').toString().trim() + '/playwright');
const http = require('http'), fs = require('fs'), path = require('path'), { spawnSync } = require('child_process');
const WEB = path.join(__dirname, 'web'), OUT = path.join(__dirname, 'out');
const args = process.argv.slice(2); const id = args[0];
const opt = {}; for (let i = 1; i < args.length; i++) if (args[i].startsWith('--')) { opt[args[i].slice(2)] = args[i + 1]; i++; }
const shots = JSON.parse(fs.readFileSync(path.join(__dirname, 'src/shots.json')));
const meta = shots.find(s => s.id === id) || { dur: Number(opt.dur || 4) };
const fps = Number(opt.fps || 24);
const types = { '.js': 'text/javascript', '.html': 'text/html', '.png': 'image/png', '.ttf': 'font/ttf', '.woff2': 'font/woff2', '.json': 'application/json' };
function serve() { return new Promise(res => { const s = http.createServer((q, r) => { const f = path.join(WEB, decodeURIComponent(q.url.split('?')[0]));
  if (!fs.existsSync(f)) { r.writeHead(404); return r.end(); } r.writeHead(200, { 'Content-Type': types[path.extname(f)] || 'application/octet-stream', 'Cache-Control': 'no-store' }); fs.createReadStream(f).pipe(r); });
  s.listen(0, () => res(s)); }); }
(async () => {
  const srv = await serve(); const port = srv.address().port;
  const b = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--disable-gpu-sandbox'] });
  const p = await b.newPage({ viewport: { width: 1920, height: 1080 } });
  p.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') console.log('[page]', m.text().slice(0, 400)); });
  p.on('pageerror', e => console.log('[pageerror]', e.message));
  await p.goto(`http://localhost:${port}/index.html`); await p.waitForFunction(() => window.ready, null, { timeout: 30000 });
  const t0 = Date.now();
  await p.evaluate(id => window.App.load(id), id);
  let times;
  if (opt.only) times = opt.only.split(',').map(Number);
  else { const a = Number(opt.from || 0), z = Number(opt.to || meta.dur); times = []; for (let i = Math.round(a * fps); i < Math.round(z * fps); i++) times.push(i / fps); }
  const dir = path.join(OUT, opt.only ? 'probe' : 'frames', id); fs.mkdirSync(dir, { recursive: true });
  if (!opt.only) for (const f of fs.readdirSync(dir)) fs.unlinkSync(path.join(dir, f));
  for (const [i, t] of times.entries()) {
    const url = await p.evaluate(t => window.App.frame(t), t);
    const file = opt.only ? path.join(dir, `${id}_${t.toFixed(2)}.png`) : path.join(dir, String(i).padStart(5, '0') + '.png');
    fs.writeFileSync(file, Buffer.from(url.split(',')[1], 'base64'));
    if (i % 24 === 0) process.stdout.write(`${id} ${i}/${times.length} ${((Date.now() - t0) / (i + 1)).toFixed(0)}ms/f\n`);
  }
  console.log(`${id} ${times.length} frames in ${((Date.now() - t0) / 1000).toFixed(1)} s`);
  await b.close(); srv.close();
  if (!opt.only) {
    fs.mkdirSync(path.join(OUT, 'shots'), { recursive: true });
    const r = spawnSync('ffmpeg', ['-y', '-loglevel', 'error', '-framerate', String(fps), '-i', path.join(dir, '%05d.png'), '-c:v', 'libx264', '-preset', 'medium', '-crf', '12', '-pix_fmt', 'yuv420p', path.join(OUT, 'shots', id + '.mp4')], { stdio: 'inherit' });
    if (r.status !== 0) process.exit(1);
    fs.rmSync(dir, { recursive: true, force: true });
    console.log(`${id} encoded`);
  }
})().catch(e => { console.error(e); process.exit(1); });
