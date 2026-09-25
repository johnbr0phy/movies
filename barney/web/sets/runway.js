// The runway: a long pale plinth in a void of pale grey, a vast cobalt pleated curtain behind, spotlights as flat discs.
// The Pleats walk it in lockstep, flat as paper, facing the audience, moving sideways like a frieze.
import { THREE, toon, PAL } from '../engine.js';
import { V, box, cyl, pleat } from '../kit.js';

export const PLEAT_COLS = [PAL.lemon, PAL.cobalt, PAL.fuchsia, PAL.tangerine, '#2bb38a', PAL.red, PAL.lemon, PAL.fuchsia];
export function runway(o = {}) {
  const g = new THREE.Group();
  const L = 80;
  g.add(box(L, 0.5, 3.2, toon({ color: '#f4f2ee', color2: '#dcdad4', pattern: 'stripes', axis: V(1, 0, 0), freq: 1.2, duty: 0.08 }), V(0, -0.25, 0)));
  g.add(box(L, 0.02, 3.4, toon({ color: PAL.ink }), V(0, -0.49, 0)));
  // floor of the void
  const fl = new THREE.Mesh(new THREE.PlaneGeometry(200, 60), toon({ color: '#e4e1db' })); fl.rotation.x = -Math.PI / 2; fl.position.y = -0.5; g.add(fl);
  // the curtain: a pleated cobalt wall, 14 m tall
  const cur = new THREE.Mesh(new THREE.PlaneGeometry(L, 16, 1, 1), toon({ color: PAL.cobalt, color2: '#aab3e0', pattern: 'pleatsU', freq: 160 })); cur.position.set(0, 7.5, -7); g.add(cur);
  // a band of paper audience silhouettes (flat, dark) in front of the curtain, far left and right
  const audM = toon({ color: '#2a2833', flat: 1 });
  for (let i = 0; i < 60; i++) { const x = -38 + i * 1.3; if (Math.abs(x) < 0.5) continue; const p = new THREE.Mesh(new THREE.CircleGeometry(0.28, 20), audM); p.position.set(x, 1.3 + (i % 2) * 0.05, -5.4); g.add(p);
    const b = new THREE.Mesh(new THREE.PlaneGeometry(0.8, 1.2), audM); b.position.set(x, 0.55, -5.4); g.add(b); }
  const rail = box(L, 0.9, 0.3, toon({ color: '#2a2833' }), V(0, -0.05, -5.1)); g.add(rail);
  return g;
}

export function makePleats(scene, n = 8) {
  const P = [];
  for (let i = 0; i < n; i++) { const m = pleat(PLEAT_COLS[i % PLEAT_COLS.length], { fold: '#c8c9d4', h: 3.1 + (i % 3) * 0.2, hat: i % 3 === 1 ? 0 : 1 }); scene.add(m); P.push(m); }
  return P;
}

// origami crane: a few flat triangles, wings flap about the body axis (+x)
export function crane(color) {
  const g = new THREE.Group(); const m = toon({ color, side: THREE.DoubleSide, color2: '#c8c9d4', pattern: 'pleatsU', freq: 6 });
  const tri = (a, b, c) => { const geo = new THREE.BufferGeometry(); geo.setAttribute('position', new THREE.Float32BufferAttribute([...a, ...b, ...c], 3)); geo.setAttribute('uv', new THREE.Float32BufferAttribute([0, 0, 1, 0, 0.5, 1], 2)); geo.computeVertexNormals(); return new THREE.Mesh(geo, m); };
  g.add(tri([-0.5, 0, 0], [0.5, 0, 0], [0, -0.35, 0]));                   // body keel
  g.add(tri([0.3, 0, 0], [0.9, 0.45, 0], [0.4, -0.1, 0]));                // neck
  g.add(tri([0.9, 0.45, 0], [1.05, 0.35, 0], [0.85, 0.38, 0]));           // head
  g.add(tri([-0.3, 0, 0], [-0.9, 0.4, 0], [-0.4, -0.1, 0]));              // tail
  const wl = new THREE.Group(), wr = new THREE.Group(); g.add(wl, wr);
  wl.add(tri([-0.35, 0, 0], [0.35, 0, 0], [0, 0, 0.95])); wr.add(tri([-0.35, 0, 0], [0.35, 0, 0], [0, 0, -0.95]));
  g.userData = { wl, wr };
  return g;
}
export function flap(c, t) { const a = 0.9 * Math.sin(t * 6); c.userData.wl.rotation.x = a; c.userData.wr.rotation.x = -a; }
