// The shore overhead (in Barney's frame): his grey plain below, the sea above as a ceiling whose surface is just above
// his raised hand. The true gravity points UP (+y), into the sea.
// seaVolume: an inverted box of deep blue (seen from inside) with no floor; the surface is a transparent film plane.
import { THREE, toon, film, PAL } from '../engine.js';
import { V } from '../kit.js';
import { makeFish } from '../rig/fish.js';

export const SURF = 1.5;
export function shore(o = {}) {
  const g = new THREE.Group();
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(3000, 3000), toon({ color: '#c3c0ba', color2: '#d8d6d1', pattern: 'pleats', axis: V(1, 0, 0.35), freq: 1.2 }));
  floor.rotation.x = -Math.PI / 2; g.add(floor);
  // sea volume: walls and "bottom" (at +y) of deep blue, visible from inside and from below through the surface
  const volM = toon({ color: '#1f45b0', color2: '#c9dcff', pattern: 'pleats', axis: V(1, 0, 0.3), freq: 0.9, side: THREE.BackSide, flat: 1 });
  const vol = new THREE.Mesh(new THREE.BoxGeometry(700, 150, 700), volM); vol.position.y = SURF + 75; g.add(vol);
  // hide the box's own bottom face by clipping: simplest is to lift the box so its bottom sits at the surface and rely on the film
  const surfM = film({ tint: '#5b8cff', alpha: 0.42, backTint: '#9cc2ff', backAlpha: 0.35, rim: 0, hi: 0 });
  const surf = new THREE.Mesh(new THREE.PlaneGeometry(700, 700, 1, 1), surfM); surf.rotation.x = Math.PI / 2; surf.position.y = SURF; g.add(surf);
  // ripple rings on the surface (flat ink circles), animated per shot
  const ringM = toon({ color: '#dfeaff', flat: 1, side: THREE.DoubleSide });
  const rings = []; for (let i = 0; i < 3; i++) { const r = new THREE.Mesh(new THREE.RingGeometry(0.97, 1, 64), ringM); r.rotation.x = Math.PI / 2; r.position.y = SURF - 0.002; r.visible = false; g.add(r); rings.push(r); }
  // the bulge: the sea reaching down to him, a hanging drop of water from the surface to his raised hand
  const prof = []; for (let i = 0; i <= 40; i++) { const u = i / 40; const y = -u; // 0 at the surface, -1 at the tip (scaled per frame)
    const r = u < 0.25 ? 0.1 + 0.3 * Math.pow(1 - u / 0.25, 2.2) : u < 0.8 ? 0.1 - 0.02 * Math.sin((u - 0.25) / 0.55 * Math.PI) : 0.1 * Math.sqrt(Math.max(0, 1 - Math.pow((u - 0.8) / 0.2, 2))) + 0.0005;
    prof.push(new THREE.Vector2(r, y)); }
  const bulgeM = film({ tint: '#5b8cff', alpha: 0.42, backTint: '#2a5ad0', backAlpha: 0.5, rim: 1, rimW: 0.08, hi: 0.7 });
  const bulge = new THREE.Mesh(new THREE.LatheGeometry(prof, 48), bulgeM); bulge.position.y = SURF; bulge.visible = false; g.add(bulge);
  g.userData = { floor, vol, surf, volM, rings, bulge };
  return g;
}
// the bottom face of the box would cover the surface: remove it from the index (faces 2,3 = +y/-y in BoxGeometry order)
// hang the bulge at (x, z) reaching down to height yTip; width scales a little with length
export function setBulge(W, x, z, yTip, on = true) { const b = W.userData.bulge; b.visible = on && yTip < SURF - 0.01; const L = SURF - yTip; b.position.set(x, SURF + 0.001, z); b.scale.set(1, L, 1); }
export function openBottom(vol) { const g = vol.geometry; const idx = Array.from(g.index.array); const grp = g.groups[3]; idx.splice(grp.start, grp.count); g.setIndex(idx); g.clearGroups(); }

// a shoal: body + tail instanced meshes sharing matrices; positions from a swirling flow around a centre
export function shoal(scene, n = 1400, o = {}) {
  const F = makeFish(); F.g.updateMatrixWorld(true);
  const parts = []; F.g.traverse(m => { if (m.isMesh && m.material.uniforms) parts.push(m); });
  const meshes = parts.map(p => { const geo = p.geometry.clone().applyMatrix4(p.matrixWorld); const im = new THREE.InstancedMesh(geo, p.material, n); im.frustumCulled = false; scene.add(im); return im; });
  let seed = 3; const r = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  const fish = []; for (let i = 0; i < n; i++) fish.push({ R: 1.5 + r() * (o.spread || 7), ph: r() * Math.PI * 2, h: (r() - 0.5) * (o.thick || 5), sp: 0.25 + r() * 0.35, s: (o.scale || 1) * (0.8 + r() * 0.5), wob: r() * 6, delay: r() });
  return { meshes, fish, n };
}
export function swimShoal(S, t, center, bloom = 1, o = {}) {
  const M = new THREE.Matrix4(), q = new THREE.Quaternion(), sc = new THREE.Vector3();
  S.fish.forEach((f, i) => {
    const b = Math.max(0, Math.min(1, (bloom - f.delay * 0.6) / 0.4));
    const a = f.ph + t * f.sp * (o.dir || 1);
    const R = f.R * (0.4 + 0.6 * b) + 0.3 * Math.sin(t * 0.7 + f.wob);
    const p = V(Math.cos(a) * R, f.h + 0.4 * Math.sin(t * 0.9 + f.wob) + (o.rise || 0) * t, Math.sin(a) * R).add(center);
    const fwd = V(-Math.sin(a), 0.1 * Math.cos(t + f.wob), Math.cos(a)).multiplyScalar(o.dir || 1).normalize();
    const up = V(0, 1, 0); const z = new THREE.Vector3().crossVectors(fwd, up).normalize(); const u2 = new THREE.Vector3().crossVectors(z, fwd);
    q.setFromRotationMatrix(new THREE.Matrix4().makeBasis(fwd, u2, z)); sc.setScalar(f.s * b * 1.0 + 1e-5);
    M.compose(p, q, sc); S.meshes.forEach(m => m.setMatrixAt(i, M));
  });
  S.meshes.forEach(m => { m.instanceMatrix.needsUpdate = true; });
}
