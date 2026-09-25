// The plaza (in its own frame: floor y=0, up +y). A square with arcaded Breton facades and red arches, a fountain
// whose jets obey the TRUE gravity (so they arc sideways when the plaza is on its side).
import { THREE, toon, film, PAL } from '../engine.js';
import { V, quad, box, cyl, mats } from '../kit.js';

function arcadeFacade(w, h, nArch, mat, archM) {
  // a facade slab with a row of arches cut through its ground floor and round windows above
  const s = new THREE.Shape(); s.moveTo(-w / 2, 0); s.lineTo(w / 2, 0); s.lineTo(w / 2, h); s.lineTo(-w / 2, h); s.lineTo(-w / 2, 0);
  const aw = w / nArch * 0.62, ah = 2.6;
  for (let i = 0; i < nArch; i++) {
    const cx = -w / 2 + (i + 0.5) * w / nArch; const hole = new THREE.Path();
    hole.moveTo(cx - aw / 2, 0.0001); hole.lineTo(cx + aw / 2, 0.0001); hole.lineTo(cx + aw / 2, ah - aw / 2); hole.absarc(cx, ah - aw / 2, aw / 2, 0, Math.PI, false); hole.lineTo(cx - aw / 2, 0.0001);
    s.holes.push(hole);
    for (const wy of [h * 0.62, h * 0.84]) if (wy + 0.5 < h) { const win = new THREE.Path(); win.absarc(cx, wy, 0.42, 0, Math.PI * 2, true); s.holes.push(win); }
  }
  const g = new THREE.ExtrudeGeometry(s, { depth: 0.5, bevelEnabled: false, curveSegments: 24 });
  const m = new THREE.Mesh(g, [mat, archM]);
  return m;
}

export function plaza(o = {}) {
  const g = new THREE.Group();
  const S = o.size || 26;
  // floor: bone with navy bands radiating like a compass
  const floorM = toon({ color: '#f2ece1', color2: '#1f2b52', pattern: 'checker', axis: V(1, 0, 0), axis2: V(0, 1, 0), freq: 0.8 });
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(S, S), floorM); floor.rotation.x = -Math.PI / 2; g.add(floor);
  // facades on four sides (arcade on the ground floor), Breton stripes, red soffits
  const facM = mats.breton({ freq: 3.2, duty: 0.4 }); const soffit = toon({ color: PAL.red });
  const H = o.h || 9;
  const sides = [[0, -S / 2, 0], [0, S / 2, Math.PI], [-S / 2, 0, Math.PI / 2], [S / 2, 0, -Math.PI / 2]];
  const facades = [];
  for (const [x, z, ry] of sides) {
    if (o.open === 'near' && z > 0) continue;
    const f = arcadeFacade(S, H, 6, facM, soffit); f.position.set(x, 0, z); f.rotation.y = ry; f.translateZ(-0.5); g.add(f); facades.push(f);
    // arcade ceiling behind the arches (a strip you can walk on upside down)
    const ceil = box(S, 0.2, 2.2, toon({ color: '#f2ece1', color2: PAL.red, pattern: 'stripes', axis: V(1, 0, 0), freq: 1.6, duty: 0.3 }), V(0, 2.7, -1.6));
    const back = box(S, 3, 0.2, toon({ color: PAL.navy }), V(0, 1.35, -2.8));
    const wrap = new THREE.Group(); wrap.position.set(x, 0, z); wrap.rotation.y = ry; wrap.add(ceil, back); g.add(wrap);
  }
  // fountain: a stepped round basin and a column; jets are drawn per frame (they know the true down)
  const basin = new THREE.Group();
  basin.add(cyl(2.2, 2.3, 0.45, toon({ color: '#f2ece1', color2: PAL.navy, pattern: 'stripes', axis: V(0, 1, 0), freq: 9, duty: 0.35 }), V(0, 0.225, 0), 64));
  basin.add(cyl(2.0, 2.0, 0.05, toon({ color: '#4fb4e8' }), V(0, 0.42, 0), 64));
  basin.add(cyl(0.22, 0.3, 1.8, toon({ color: PAL.red }), V(0, 0.9, 0), 24));
  basin.add(cyl(0.7, 0.4, 0.2, toon({ color: '#f2ece1' }), V(0, 1.85, 0), 32));
  g.add(basin);
  const jets = []; const jetM = toon({ color: '#9fdcff', flat: 1 });
  for (let i = 0; i < 10; i++) { const m = new THREE.Mesh(new THREE.SphereGeometry(0.06, 8, 6), jetM); g.add(m); jets.push(m); }
  const drops = new THREE.InstancedMesh(new THREE.SphereGeometry(0.045, 8, 6), jetM, 160); g.add(drops);
  g.userData = { S, H, jets, drops, facades };
  return g;
}

// animate the fountain: water leaves the top bowl radially and falls along `trueDownLocal` (plaza coords)
export function fountain(P, t, trueDownLocal) {
  const d = trueDownLocal.clone().normalize(); const m = new THREE.Matrix4(); let k = 0;
  for (let j = 0; j < 8; j++) {
    const a = j / 8 * Math.PI * 2; const v0 = V(Math.cos(a) * 1.4, 1.2, Math.sin(a) * 1.4);
    for (let i = 0; i < 20; i++) {
      const s = ((t * 1.2 + i / 20) % 1) * 1.3; // seconds along the arc
      const p = V(0, 1.95, 0).add(v0.clone().multiplyScalar(s)).add(d.clone().multiplyScalar(4.9 * s * s));
      m.makeTranslation(p.x, p.y, p.z); P.userData.drops.setMatrixAt(k++, m);
    }
  }
  P.userData.drops.instanceMatrix.needsUpdate = true;
}
