// The grey plain: an endless pleated grey floor under a flat grey sky. The sky is a plane too (it turns out to be the
// underside of the sea). greyWorld() drains the colour out of every toon material except the fish's.
import { THREE, toon, film } from '../engine.js';
import { V } from '../kit.js';

export function plain(o = {}) {
  const g = new THREE.Group();
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(900, 900), toon({ color: '#b9b7b3', color2: '#d3d2cf', pattern: 'pleats', axis: V(1, 0, 0.35), freq: 1.2 }));
  floor.rotation.x = -Math.PI / 2; g.add(floor);
  const skyM = toon({ color: '#c9c8c4', color2: '#aeb4c0', pattern: 'pleats', axis: V(1, 0, 0.2), freq: 0.35, side: THREE.DoubleSide, flat: 1 });
  const sky = new THREE.Mesh(new THREE.PlaneGeometry(900, 900), skyM); sky.rotation.x = Math.PI / 2; sky.position.y = o.skyY || 9; g.add(sky);
  // dark spots the drips leave behind
  const spotM = toon({ color: '#8f8d8a', flat: 1 });
  const spots = new THREE.InstancedMesh(new THREE.CircleGeometry(0.045, 16), spotM, 200); spots.count = 0; g.add(spots);
  g.userData = { floor, sky, skyM, spots };
  return g;
}
export function setSpots(P, pts) {
  const M = new THREE.Matrix4(); const q = new THREE.Quaternion().setFromEuler(new THREE.Euler(-Math.PI / 2, 0, 0));
  pts.forEach((p, i) => { M.compose(V(p.x, 0.004, p.z), q, V(1 + (i % 3) * 0.25, 1, 1)); P.userData.spots.setMatrixAt(i, M); });
  P.userData.spots.count = pts.length; P.userData.spots.instanceMatrix.needsUpdate = true;
}
export function greyWorld(root, keep) {
  const keepMats = new Set(); keep.traverse(o => { if (o.material) (Array.isArray(o.material) ? o.material : [o.material]).forEach(m => keepMats.add(m)); });
  const lum = (c) => { const l = c.r * 0.3 + c.g * 0.55 + c.b * 0.15; const v = 0.28 + l * 0.62; return new THREE.Color(v, v, v * 1.01); };
  root.traverse(o => { if (!o.material) return; (Array.isArray(o.material) ? o.material : [o.material]).forEach(m => {
    if (keepMats.has(m) || !m.uniforms) return;
    if (m.uniforms.uBase) { m.uniforms.uBase.value.copy(lum(m.uniforms.uBase.value)); m.uniforms.uColor2.value.copy(lum(m.uniforms.uColor2.value)); }
    if (m.uniforms.uTint) { m.uniforms.uTint.value.set('#e2e2e0'); m.uniforms.uBackTint.value.set('#d0d0ce'); }
  }); });
}
