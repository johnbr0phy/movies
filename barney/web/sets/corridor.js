// Two corridors.
// mirrorCorridor: floor and ceiling are the same chequer, the walls are Breton stripes, doors hang at mid-height,
//   so nothing but the water (and one pendant lamp) tells you which way is down.
// galleria: a forced-perspective gallery in the manner of Borromini's Galleria Spada: it narrows, its floor rises
//   and its ceiling drops, so a 7 m corridor reads as 30 m, and a small boy grows as he walks away.
import { THREE, toon, PAL } from '../engine.js';
import { V, quad, box, cyl, door, mats } from '../kit.js';

export function mirrorCorridor(o = {}) {
  const g = new THREE.Group();
  const hw = 1.25, h = 3.0, z0 = o.z0 || -26, z1 = o.z1 || 8;
  const floorM = toon({ color: '#f3eee4', color2: '#1f1e27', pattern: 'checker', axis: V(1, 0, 0), axis2: V(0, 0, 1), freq: 1.25 });
  const ceilM = toon({ color: '#f3eee4', color2: '#1f1e27', pattern: 'checker', axis: V(1, 0, 0), axis2: V(0, 0, 1), freq: 1.25 });
  const wallM = mats.breton({ freq: 4.2, duty: 0.42, side: THREE.DoubleSide });
  g.add(quad(V(-hw, 0, z1), V(hw, 0, z1), V(-hw, 0, z0), V(hw, 0, z0), floorM, 2, 2));
  g.add(quad(V(-hw, h, z0), V(hw, h, z0), V(-hw, h, z1), V(hw, h, z1), ceilM, 2, 2));
  g.add(quad(V(-hw, 0, z0), V(-hw, 0, z1), V(-hw, h, z0), V(-hw, h, z1), wallM, 2, 2));
  g.add(quad(V(hw, 0, z1), V(hw, 0, z0), V(hw, h, z1), V(hw, h, z0), wallM, 2, 2));
  // red doors at mid-height on both walls: no clue to up or down
  for (let z = z1 - 3; z > z0 + 2; z -= 5.5) for (const sx of [-1, 1]) {
    const d = door(0.9, 1.6, PAL.red); d.position.set(sx * (hw - 0.03), 0.7, z + (sx > 0 ? 0 : 0.9)); d.rotation.y = sx > 0 ? -Math.PI / 2 : Math.PI / 2; g.add(d);
  }
  // end wall far away, a navy disc like an eye
  g.add(box(hw * 2, h, 0.1, toon({ color: '#f3eee4' }), V(0, h / 2, z0 - 0.05)));
  const eye = new THREE.Mesh(new THREE.CircleGeometry(0.55, 48), toon({ color: PAL.navy, flat: 1 })); eye.position.set(0, h / 2, z0 + 0.01); g.add(eye);
  // the one honest object: a pendant lamp hanging from the TRUE ceiling
  const lamps = [];
  for (const lz of (o.lamps || [-1.5, -9])) {
    const lamp = new THREE.Group(); lamp.position.set(-0.35, h, lz);
    lamp.add(cyl(0.006, 0.006, 0.7, toon({ color: PAL.ink }), V(0, -0.35, 0), 8));
    const shade = new THREE.Mesh(new THREE.ConeGeometry(0.16, 0.16, 32, 1, true), toon({ color: PAL.red, side: THREE.DoubleSide })); shade.position.y = -0.76; lamp.add(shade);
    const bulb = new THREE.Mesh(new THREE.SphereGeometry(0.05, 16, 12), toon({ color: '#fff4c9', emit: 1, flat: 1 })); bulb.position.y = -0.84; lamp.add(bulb);
    g.add(lamp); lamps.push(lamp);
  }
  g.userData = { hw, h, lamps };
  return g;
}

export function galleria(o = {}) {
  const g = new THREE.Group();
  const L = 7.0; // true length
  const n = { hw: 1.4, f: 0, c: 3.3, z: 0.6 }, f = { hw: 0.42, f: 0.34, c: 1.5, z: -L }; // near and far cross-sections
  const at = (u) => ({ hw: n.hw + (f.hw - n.hw) * u, fl: n.f + (f.f - n.f) * u, c: n.c + (f.c - n.c) * u, z: n.z + (f.z - n.z) * u });
  const floorM = toon({ color: '#f3eee4', color2: '#1f1e27', pattern: 'checkUV', freq: 16, freq2: 4, side: THREE.DoubleSide });
  const wallM = toon({ color: PAL.bone, color2: PAL.navy, pattern: 'bands', freq: 11, duty: 0.4 });
  const ceilM = toon({ color: PAL.bone, color2: PAL.navy, pattern: 'bandsU', freq: 16, duty: 0.18 });
  const P = (u, side, y) => { const a = at(u); return V(side * a.hw, y === 'f' ? a.fl : a.c, a.z); };
  const floor = quad(P(0, -1, 'f'), P(1, -1, 'f'), P(0, 1, 'f'), P(1, 1, 'f'), floorM, 32, 4); g.add(floor);
  const ceil = quad(P(0, 1, 'c'), P(1, 1, 'c'), P(0, -1, 'c'), P(1, -1, 'c'), ceilM, 32, 4); ceil.name = 'ceil'; g.add(ceil);
  const left = quad(P(0, -1, 'f'), P(1, -1, 'f'), P(0, -1, 'c'), P(1, -1, 'c'), wallM, 32, 16); left.material.side = THREE.DoubleSide; g.add(left);
  const right = quad(P(1, 1, 'f'), P(0, 1, 'f'), P(1, 1, 'c'), P(0, 1, 'c'), toon({ color: PAL.bone, color2: PAL.navy, pattern: 'bands', freq: 11, duty: 0.4, side: THREE.DoubleSide }), 32, 16);
  right.name = 'nearWall'; g.add(right);
  // colonnades that shrink with the gallery
  const colM = toon({ color: PAL.navy }), capM = toon({ color: PAL.bone });
  const cols = [];
  for (let i = 0; i < 8; i++) {
    const u = 0.04 + i * 0.13; const a = at(u); const hgt = a.c - a.fl; const r = 0.06 * hgt / 3.3 + 0.012;
    for (const sx of [-1, 1]) {
      const cg = new THREE.Group(); cg.position.set(sx * (a.hw - r * 1.6), a.fl, a.z);
      cg.add(cyl(r, r * 1.08, hgt * 0.86, colM, V(0, hgt * 0.07 + hgt * 0.43, 0), 24));
      cg.add(box(r * 3, hgt * 0.07, r * 3, capM, V(0, hgt * 0.035, 0)), box(r * 3.2, hgt * 0.07, r * 3.2, capM, V(0, hgt * 0.965, 0)));
      if (sx > 0) cg.name = 'nearCol'; g.add(cg); cols.push(cg);
    }
  }
  // end wall with a small red door (opening cut by building the wall around it)
  const e = at(1); const dw = 0.46, dh = 0.8, dx = -dw / 2; const wallE = toon({ color: PAL.bone, color2: PAL.navy, pattern: 'stripes', axis: V(0, 1, 0), freq: 11, duty: 0.4 });
  const ew = e.hw * 2, eh = e.c - e.fl;
  g.add(box((ew - dw) / 2, eh, 0.08, wallE, V(-e.hw + (ew - dw) / 4, e.fl + eh / 2, e.z - 0.04)));
  g.add(box((ew - dw) / 2, eh, 0.08, wallE, V(e.hw - (ew - dw) / 4, e.fl + eh / 2, e.z - 0.04)));
  g.add(box(dw, eh - dh, 0.08, wallE, V(0, e.fl + dh + (eh - dh) / 2, e.z - 0.04)));
  const d = door(dw, dh, PAL.red); d.position.set(dx, e.fl, e.z - 0.02); g.add(d);
  g.userData = { at, door: d, L, far: e };
  return g;
}
