// Set-building kit: patterned boxes, bilinear (tapered) walls, columns, doors, the Pleats.
import { THREE, toon, film, PAL, newId } from './engine.js';
export const V = (x, y, z) => new THREE.Vector3(x, y, z);

export function box(w, h, d, mat, pos, rot) { const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat); if (pos) m.position.copy(pos); if (rot) m.rotation.set(rot.x, rot.y, rot.z); return m; }
export function cyl(rt, rb, h, mat, pos, seg = 32) { const m = new THREE.Mesh(new THREE.CylinderGeometry(rt, rb, h, seg), mat); if (pos) m.position.copy(pos); return m; }

// A quad between four corners (p00 = u0v0, p10 = u1v0, p01 = u0v1, p11 = u1v1), subdivided so patterns in uv follow any taper.
export function quad(p00, p10, p01, p11, mat, nu = 24, nv = 12) {
  const pos = [], uv = [], idx = [];
  for (let j = 0; j <= nv; j++) for (let i = 0; i <= nu; i++) {
    const u = i / nu, v = j / nv;
    const a = p00.clone().lerp(p10, u), b = p01.clone().lerp(p11, u); const p = a.lerp(b, v);
    pos.push(p.x, p.y, p.z); uv.push(u, v);
  }
  for (let j = 0; j < nv; j++) for (let i = 0; i < nu; i++) { const a = j * (nu + 1) + i, b = a + 1, c = a + nu + 1, d = c + 1; idx.push(a, b, d, a, d, c); }
  const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); g.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2)); g.setIndex(idx); g.computeVertexNormals();
  return new THREE.Mesh(g, mat);
}

export const mats = {
  breton: (o = {}) => toon(Object.assign({ color: PAL.bone, color2: PAL.navy, pattern: 'stripes', axis: V(0, 1, 0), freq: 5, duty: 0.42 }, o)),
  bands: (o = {}) => toon(Object.assign({ color: PAL.bone, color2: PAL.navy, pattern: 'bands', freq: 12, duty: 0.42 }, o)),
  bandsU: (o = {}) => toon(Object.assign({ color: PAL.bone, color2: PAL.navy, pattern: 'bandsU', freq: 12, duty: 0.42 }, o)),
  checker: (o = {}) => toon(Object.assign({ color: '#f4efe6', color2: '#1d1c24', pattern: 'checker', axis: V(1, 0, 0), axis2: V(0, 0, 1), freq: 1.6 }, o)),
  flat: (c, o = {}) => toon(Object.assign({ color: c }, o)),
  pleat: (c, o = {}) => toon(Object.assign({ color: c, color2: '#d6d7e0', pattern: 'pleats', axis: V(1, 0, 0), freq: 8 }, o)),
};

// a panelled door; hinge at local x=0, opening angle `open` (radians); width w, height h
export function door(w, h, color = PAL.red, o = {}) {
  const g = new THREE.Group();
  const leafG = new THREE.Group(); g.add(leafG);
  const leaf = box(w, h, 0.05, toon({ color }), V(w / 2, h / 2, 0)); leafG.add(leaf);
  for (const y of [0.28, 0.68]) leafG.add(box(w * 0.64, h * 0.3, 0.02, toon({ color: new THREE.Color(color).multiplyScalar(0.86) }), V(w / 2, h * y, 0.03)));
  const knob = new THREE.Mesh(new THREE.SphereGeometry(Math.max(0.018, w * 0.045), 16, 12), toon({ color: '#e6b84a' })); knob.position.set(w * 0.84, h * 0.47, 0.06); leafG.add(knob);
  const frameM = toon({ color: o.frame || PAL.ink });
  g.add(box(0.06, h + 0.06, 0.1, frameM, V(-0.03, h / 2, 0)), box(0.06, h + 0.06, 0.1, frameM, V(w + 0.03, h / 2, 0)), box(w + 0.12, 0.06, 0.1, frameM, V(w / 2, h + 0.03, 0)));
  g.userData.leaf = leafG; g.userData.w = w; g.userData.h = h;
  return g;
}

// The Pleats: tall flat paper people. A single double-sided plane, cut out in the shader, pleated vertically.
// They exist only face-on; seen edge-on they are a line.
export function pleat(color, o = {}) {
  const w = o.w || 1.3, h = o.h || 3.3;
  const g = new THREE.PlaneGeometry(w, h, 1, 1); g.translate(0, h / 2, 0);
  const m = toon({ color, color2: o.fold || '#c9cad6', pattern: 'pleatsU', freq: o.pleats || 18, side: THREE.DoubleSide, mask: 2, maskP: new THREE.Vector4(w, h, o.hat === undefined ? 1 : o.hat, 0), flat: 0.35 });
  const mesh = new THREE.Mesh(g, m); mesh.userData.mat = m;
  return mesh;
}
