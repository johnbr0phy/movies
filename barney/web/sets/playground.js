// The playground: a pale disc of ground under a pale sky, striped Gaultier cones of every size, and one pleated
// lemon slide that doesn't come down from anywhere: it rises from the ground, curls up and keeps going into the sky.
import { THREE, toon, PAL } from '../engine.js';
import { V, cyl } from '../kit.js';

export function slideCurve() {
  return new THREE.CatmullRomCurve3([V(0, 0.32, 0.6), V(0, 0.34, -1.2), V(0, 0.9, -3.6), V(0, 2.6, -6.2), V(0, 5.4, -8.0), V(0, 9.2, -8.8), V(0, 14, -8.6), V(0, 20, -7.4), V(0, 27, -5.2)], false, 'centripetal');
}
// frame along the curve: T tangent, N points to the inside bottom of the pipe (where the rider's back/seat is), X side
export function slideFrame(curve, u) {
  const p = curve.getPointAt(u), T = curve.getTangentAt(u).normalize(); const X = V(1, 0, 0);
  const N = new THREE.Vector3().crossVectors(T, X).normalize(); // for T ~ -z: T x X = (0,-1,0)... points down
  return { p, T, N, X };
}
export function halfPipe(curve, r = 0.55, mat) {
  const nu = 220, nv = 18, pos = [], uv = [], idx = [];
  for (let i = 0; i <= nu; i++) {
    const u = i / nu; const { p, N, X } = slideFrame(curve, u);
    for (let j = 0; j <= nv; j++) { const a = -Math.PI / 2 - 0.15 + (Math.PI + 0.3) * j / nv; // around the bottom, a little past the sides
      const q = p.clone().add(X.clone().multiplyScalar(Math.sin(a) * r)).add(N.clone().multiplyScalar(-Math.cos(a) * r * -1));
      pos.push(q.x, q.y, q.z); uv.push(u, j / nv); }
  }
  for (let i = 0; i < nu; i++) for (let j = 0; j < nv; j++) { const a = i * (nv + 1) + j, b = a + nv + 1; idx.push(a, b, a + 1, b, b + 1, a + 1); }
  const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); g.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2)); g.setIndex(idx); g.computeVertexNormals();
  return new THREE.Mesh(g, mat);
}

export function playground() {
  const g = new THREE.Group();
  const ground = new THREE.Mesh(new THREE.CircleGeometry(60, 96), toon({ color: '#e9efe6', color2: '#d3dccf', pattern: 'stripes', axis: V(1, 0, 0.3), freq: 0.8, duty: 0.3 }));
  ground.rotation.x = -Math.PI / 2; g.add(ground);
  const curve = slideCurve();
  const slide = halfPipe(curve, 0.55, toon({ color: PAL.lemon, color2: '#c9a20e', pattern: 'pleatsU', freq: 120, side: THREE.DoubleSide }));
  g.add(slide);
  // a striped lip at the bottom
  // cones: striped, Gaultier; x, z, height, radius, colours
  const cones = [[-3.2, -2.5, 3.2, 0.9, PAL.fuchsia, PAL.bone], [3.6, -4.2, 5.2, 1.3, PAL.navy, PAL.bone], [-6.5, -7.5, 7, 1.8, PAL.cobalt, PAL.lemon], [6.8, -1.0, 2.2, 0.7, PAL.red, PAL.bone],
    [-2.2, 2.4, 1.3, 0.45, PAL.tangerine, PAL.bone], [9.5, -9, 9, 2.2, PAL.fuchsia, PAL.lemon], [-11, -3, 4, 1.1, '#2bb38a', PAL.bone], [2.2, 3.2, 0.9, 0.32, PAL.navy, PAL.bone]];
  for (const [x, z, h, r, c1, c2] of cones) {
    const m = new THREE.Mesh(new THREE.ConeGeometry(r, h, 48, 1), toon({ color: c2, color2: c1, pattern: 'stripes', axis: V(0, 1, 0), freq: 7 / h * 1.5, duty: 0.5 }));
    m.position.set(x, h / 2, z); g.add(m);
  }
  // a pair of balls
  for (const [x, z, r, c] of [[-1.2, -5.5, 0.5, PAL.red], [4.8, 1.6, 0.35, PAL.lemon]]) { const b = new THREE.Mesh(new THREE.SphereGeometry(r, 32, 20), toon({ color: c })); b.position.set(x, r, z); g.add(b); }
  // flat paper clouds
  const cm = toon({ color: '#ffffff', color2: '#e5eaf2', pattern: 'stripes', axis: V(0, 1, 0), freq: 3, duty: 0.2, side: THREE.DoubleSide });
  for (const [x, y, z, s] of [[-8, 14, -20, 3], [7, 20, -18, 4], [-2, 28, -12, 3.5], [10, 32, -6, 2.5], [-9, 36, -2, 3]]) {
    const c = new THREE.Group(); for (const [dx, dy, rr] of [[0, 0, 1], [0.9, 0.2, 0.75], [-0.9, 0.1, 0.7], [0.3, 0.6, 0.6]]) { const d = new THREE.Mesh(new THREE.CircleGeometry(rr, 32), cm); d.position.set(dx, dy, 0); c.add(d); }
    c.position.set(x, y, z); c.scale.setScalar(s); g.add(c);
  }
  g.userData = { curve, slide };
  return g;
}
