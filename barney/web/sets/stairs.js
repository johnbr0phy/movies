// Penrose stairs, built for real. In an orthographic view along d = (1,1,1) a point moved along d does not move on screen.
// So the stair is an OPEN helix: 20 steps, each 0.12 m up, whose plan runs 7, 3, 3, 7 cells. The top of the last step is
// exactly 2.4 m along d from the first, so from the magic angle the ring closes and climbs forever; from anywhere else
// it is a spiral whose top hangs 4 m in the air above its bottom, with nothing in between.
import { THREE, toon, PAL } from '../engine.js';
import { V } from '../kit.js';

export function penrose(o = {}) {
  const g = new THREE.Group();
  const cell = 0.6, h = 0.12, sides = [7, 3, 3, 7];
  const dirs = [V(1, 0, 0), V(0, 0, -1), V(-1, 0, 0), V(0, 0, 1)];
  const cells = []; let p = V(0, 0, 0); let k = 0;
  for (let si = 0; si < 4; si++) for (let i = 0; i < sides[si]; i++) { cells.push({ p: p.clone(), side: si, k }); p.add(dirs[si].clone().multiplyScalar(cell)); k++; }
  const N = cells.length, S = N * h; // 2.4 = 4 cells
  const colsSide = [PAL.lemon, PAL.fuchsia, PAL.cobalt, '#2bb38a'];
  const topM = toon({ color: '#f6f3ec' });
  for (const c of cells) {
    const top = c.k * h, depth = 40;
    const m = toon({ color: colsSide[c.side], color2: '#ffffff', pattern: 'stripes', axis: V(0, 1, 0), freq: 1 / h, duty: 0.07, phase: -top / h });
    const b = new THREE.Mesh(new THREE.BoxGeometry(cell, depth, cell), [m, m, topM, m, m, m]);
    b.position.set(c.p.x, top - depth / 2, c.p.z); g.add(b);
    c.world = V(c.p.x, top, c.p.z);
  }
  const lo = V(0, 0, 0), hi = V(0, 0, 0); for (const c of cells) { lo.min(c.world); hi.max(c.world); }
  const center = lo.clone().add(hi).multiplyScalar(0.5);
  g.userData = { cells, N, cell, h, S, center, dirs, wrap: V(S, S, S) };
  return g;
}

// Barney's foot position at continuous step index u. Past the top step he continues onto a virtual step N, which is
// cell 0 moved along d: identical on screen from the magic angle. `true` coordinates wrap to cell 0 below.
export function onStairs(P, u, virtual = true) {
  const { cells, N, wrap } = P.userData;
  const lap = Math.floor(u / N); const n = u - lap * N; const i = Math.floor(n), f = n - i;
  const a = cells[i].world.clone(); const b = (i + 1 < N) ? cells[i + 1].world.clone() : cells[0].world.clone().add(virtual ? wrap : V(0, 0, 0));
  const pos = a.clone().lerp(b, f);
  const lift = f > 0.5 ? 1 : 0; pos.y = a.y + (b.y - a.y) * lift + 0.05 * Math.sin(f * Math.PI);
  const fwd = P.userData.dirs[cells[i].side].clone();
  return { pos, fwd, i, f };
}
