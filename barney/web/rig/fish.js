// The goldfish: tangerine body, pale tail and fins, black eye with a white ring. Faces +x, its up is +y.
import { THREE, toon, PAL, newId } from '../engine.js';

export function makeFish(o = {}) {
  const idBody = newId(), idFin = newId(), idEye = newId(), idRing = newId();
  const body = toon({ color: o.color || PAL.fish, id: idBody });
  const fin = toon({ color: o.fin || PAL.fishLight, id: idFin, side: THREE.DoubleSide, color2: '#ffd9b3', pattern: 'stripes', axis: new THREE.Vector3(1, 0, 0), freq: 90, duty: 0.25 });
  const eye = toon({ color: '#101014', id: idEye, flat: 1 });
  const ring = toon({ color: '#fff6ea', id: idRing, flat: 1 });
  const g = new THREE.Group(); g.name = 'fish';
  // body: a lathe along +y rotated to +x, 7 cm long, flattened sideways
  const prof = [[0, 0.036], [0.008, 0.034], [0.014, 0.028], [0.018, 0.018], [0.02, 0.006], [0.019, -0.006], [0.015, -0.017], [0.009, -0.026], [0.005, -0.031], [0.0001, -0.033]]
    .map(([r, y]) => new THREE.Vector2(r, y));
  const bg = new THREE.LatheGeometry(prof, 32); bg.rotateZ(-Math.PI / 2); bg.scale(1, 1.05, 0.72);
  const bm = new THREE.Mesh(bg, body); g.add(bm);
  // tail: two lobes fanned from the tail root
  const tailRoot = new THREE.Group(); tailRoot.position.x = -0.031; g.add(tailRoot);
  const ts = new THREE.Shape(); ts.moveTo(0, 0); ts.bezierCurveTo(-0.02, 0.012, -0.04, 0.03, -0.046, 0.026); ts.bezierCurveTo(-0.036, 0.012, -0.034, 0.0, -0.03, -0.002);
  ts.bezierCurveTo(-0.036, -0.008, -0.04, -0.022, -0.046, -0.028); ts.bezierCurveTo(-0.03, -0.024, -0.016, -0.012, 0, 0);
  const tail = new THREE.Mesh(new THREE.ShapeGeometry(ts, 12), fin); tailRoot.add(tail);
  // dorsal fin
  const ds = new THREE.Shape(); ds.moveTo(0.012, 0); ds.bezierCurveTo(0.008, 0.012, -0.004, 0.02, -0.016, 0.016); ds.lineTo(-0.02, 0); ds.lineTo(0.012, 0);
  const dorsal = new THREE.Mesh(new THREE.ShapeGeometry(ds, 8), fin); dorsal.position.set(0.0, 0.018, 0); g.add(dorsal);
  // pectoral and pelvic fins
  const ps = new THREE.Shape(); ps.moveTo(0, 0); ps.bezierCurveTo(-0.006, -0.006, -0.016, -0.012, -0.02, -0.008); ps.bezierCurveTo(-0.014, -0.002, -0.006, 0.0, 0, 0);
  const pects = [];
  for (const sz of [1, -1]) { const p = new THREE.Mesh(new THREE.ShapeGeometry(ps, 8), fin); p.position.set(0.008, -0.008, 0.012 * sz); p.rotation.x = 0.6 * sz; g.add(p); pects.push(p); }
  for (const sz of [1, -1]) { const e = new THREE.Mesh(new THREE.SphereGeometry(1, 40, 28), eye); e.position.set(0.02, 0.006, 0.0118 * sz); e.scale.set(0.0045, 0.0045, 0.002); g.add(e);
    const r = new THREE.Mesh(new THREE.SphereGeometry(1, 40, 28), ring); r.position.set(0.02, 0.006, 0.011 * sz); r.scale.set(0.0068, 0.0068, 0.002); g.add(r); }
  const F = { g, tailRoot, dorsal, pects, M: { body, fin } };
  F.set = (t, speed = 1) => { // swim cycle, called with held time
    tailRoot.rotation.y = 0.45 * Math.sin(t * Math.PI * 2 * 2.4 * speed);
    bm.rotation.y = -0.08 * Math.sin(t * Math.PI * 2 * 2.4 * speed + 0.8);
    for (const [i, p] of pects.entries()) p.rotation.y = 0.4 * Math.sin(t * Math.PI * 2 * 3 + i * Math.PI);
  };
  if (o.scale) g.scale.setScalar(o.scale);
  return F;
}

// orient a fish: nose along `fwd`, back along `up` (true up)
export function orientFish(F, pos, fwd, up) {
  const u = up.clone().normalize(); const f = fwd.clone().sub(u.clone().multiplyScalar(fwd.dot(u))).normalize();
  const z = new THREE.Vector3().crossVectors(f, u);
  F.g.quaternion.setFromRotationMatrix(new THREE.Matrix4().makeBasis(f, u, z)); F.g.position.copy(pos);
}
