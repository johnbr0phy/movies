// Water drops: an instanced pool of little spheres emitted from a point, falling along a direction (the TRUE down).
import { THREE, toon } from './engine.js';
export function makeDrops(scene, n = 60, color = '#8fd7ff') {
  const m = new THREE.InstancedMesh(new THREE.SphereGeometry(0.018, 10, 8), toon({ color, flat: 0.5 }), n);
  m.frustumCulled = false; scene.add(m);
  return { m, n, list: [] };
}
// emitters: [{ t0, p0: Vector3, v0: Vector3 }]; g: gravity vector (m/s^2); returns nothing
export function updateDrops(D, t, g, stretch = true) {
  const M = new THREE.Matrix4(); const q = new THREE.Quaternion(); const s = new THREE.Vector3();
  let k = 0;
  for (const d of D.list) {
    const dt = t - d.t0; if (dt < 0 || dt > (d.life || 3)) continue; if (k >= D.n) break;
    const p = d.p0.clone().add(d.v0.clone().multiplyScalar(dt)).add(g.clone().multiplyScalar(0.5 * dt * dt));
    const v = d.v0.clone().add(g.clone().multiplyScalar(dt)); const sp = v.length();
    q.setFromUnitVectors(new THREE.Vector3(0, 1, 0), sp > 1e-4 ? v.clone().normalize() : new THREE.Vector3(0, 1, 0));
    s.set(1, stretch ? 1 + Math.min(2.5, sp * 0.25) : 1, 1).multiplyScalar(d.size || 1);
    M.compose(p, q, s); D.m.setMatrixAt(k++, M);
  }
  for (; k < D.n; k++) { M.makeScale(0, 0, 0); D.m.setMatrixAt(k, M); }
  D.m.instanceMatrix.needsUpdate = true;
}
