// Barney: seven, big round head, black bob with a blunt fringe, navy/bone marinière, bone pleated capelet,
// black shorts, white socks, red T-bar shoes. Built from primitives so he is the same boy from every angle.
// Local frame: feet at the origin, +y is HIS up (whatever he stands on), facing +z. His right hand (-x) carries the bag.
import { THREE, toon, PAL, newId } from '../engine.js';

const V = (x, y, z) => new THREE.Vector3(x, y, z);

function capsule(r, len, mat, seg = 16) { const g = new THREE.CapsuleGeometry(r, len, 6, seg); g.translate(0, -len / 2, 0); return new THREE.Mesh(g, mat); }

export function makeBarney(o = {}) {
  const id = { skin: newId(), hair: newId(), top: newId(), cape: newId(), shorts: newId(), sock: newId(), shoe: newId(), eye: newId(), mouth: newId(), cheek: newId(), glint: newId() };
  const M = {
    skin: toon({ color: PAL.skin, id: id.skin }),
    face: toon({ color: PAL.skin, id: id.skin, flat: 1 }),
    hair: toon({ color: '#17151d', id: id.hair, mask: 1, maskP: new THREE.Vector4(-0.2, 0.0, 0.036, 0.112), side: THREE.DoubleSide }),
    top: toon({ color: PAL.bone, color2: PAL.navy, pattern: 'stripes', axis: V(0, 1, 0), freq: 30, duty: 0.44, id: id.top }),
    sleeve: toon({ color: PAL.bone, color2: PAL.navy, pattern: 'stripes', axis: V(0, 1, 0), freq: 30, duty: 0.44, id: id.top }),
    cape: toon({ color: '#f7f3ea', color2: '#d9d9e2', pattern: 'pleatsU', freq: 26, id: id.cape, side: THREE.DoubleSide }),
    shorts: toon({ color: '#1d1c24', id: id.shorts }),
    sock: toon({ color: '#fbfaf6', id: id.sock }),
    shoe: toon({ color: PAL.red, id: id.shoe }),
    eye: toon({ color: '#121118', id: id.eye, flat: 1 }),
    glint: toon({ color: '#ffffff', id: id.glint, flat: 1 }),
    cheek: toon({ color: PAL.blush, id: id.cheek, flat: 1 }),
    mouth: toon({ color: '#3a1f24', id: id.mouth, flat: 1 }),
  };
  const root = new THREE.Group(); root.name = 'barney';
  const pelvis = new THREE.Group(); pelvis.position.y = 0.4; root.add(pelvis);

  // legs: hip joint -> thigh -> knee -> shin/sock -> ankle -> shoe
  const legs = {};
  for (const side of ['L', 'R']) {
    const sx = side === 'L' ? 1 : -1;
    const hip = new THREE.Group(); hip.position.set(0.055 * sx, 0, 0); pelvis.add(hip);
    const thigh = capsule(0.034, 0.15, M.skin); hip.add(thigh);
    const knee = new THREE.Group(); knee.position.y = -0.17; hip.add(knee);
    const shin = capsule(0.031, 0.06, M.skin); knee.add(shin);
    const kneeCap = new THREE.Mesh(new THREE.SphereGeometry(0.034, 16, 12), M.skin); knee.add(kneeCap);
    const sock = capsule(0.034, 0.075, M.sock); sock.position.y = -0.075; knee.add(sock);
    const ankle = new THREE.Group(); ankle.position.y = -0.165; knee.add(ankle);
    const shoeG = new THREE.CapsuleGeometry(0.038, 0.085, 6, 16); shoeG.rotateX(Math.PI / 2); shoeG.scale(1.05, 0.8, 1); shoeG.translate(0, -0.018, 0.03);
    const shoe = new THREE.Mesh(shoeG, M.shoe); ankle.add(shoe);
    const strap = new THREE.Mesh(new THREE.TorusGeometry(0.036, 0.006, 6, 20, Math.PI), M.shoe); strap.rotation.set(0, Math.PI / 2, 0); strap.position.set(0, -0.004, 0.02); ankle.add(strap);
    legs[side] = { hip, knee, ankle };
  }
  // shorts
  const shortsG = new THREE.CylinderGeometry(0.118, 0.13, 0.13, 32); const shorts = new THREE.Mesh(shortsG, M.shorts); shorts.position.y = 0.02; pelvis.add(shorts);
  for (const sx of [1, -1]) { const cuff = new THREE.Mesh(new THREE.CylinderGeometry(0.052, 0.058, 0.08, 20), M.shorts); cuff.position.set(0.058 * sx, -0.06, 0); pelvis.add(cuff); legs[sx > 0 ? 'L' : 'R'].cuff = cuff; }

  // torso
  const chest = new THREE.Group(); chest.position.y = 0.075; pelvis.add(chest);
  const torsoG = new THREE.CylinderGeometry(0.104, 0.126, 0.27, 40, 1); torsoG.translate(0, 0.135, 0);
  const torso = new THREE.Mesh(torsoG, M.top); chest.add(torso);
  const shoulderTop = new THREE.Mesh(new THREE.SphereGeometry(0.104, 32, 12, 0, Math.PI * 2, 0, Math.PI / 2), M.top); shoulderTop.scale.set(1, 0.35, 1); shoulderTop.position.y = 0.27; chest.add(shoulderTop);
  // capelet: a flared pleated collar
  const capeG = new THREE.CylinderGeometry(0.075, 0.17, 0.1, 72, 1, true); capeG.translate(0, -0.05, 0);
  const cape = new THREE.Mesh(capeG, M.cape); cape.position.y = 0.3; chest.add(cape);
  // neck and head
  const neck = new THREE.Mesh(new THREE.CylinderGeometry(0.038, 0.042, 0.06, 16), M.skin); neck.position.y = 0.3; chest.add(neck);
  const head = new THREE.Group(); head.position.y = 0.33; chest.add(head);
  const skull = new THREE.Mesh(new THREE.SphereGeometry(0.15, 48, 32), M.face); skull.position.y = 0.12; skull.scale.set(1, 0.97, 0.98); head.add(skull);
  // bob: a lathed helmet with a slight flare at the hem; the face window is cut out in the shader
  const bobProf = [[0.0005, 0.172], [0.05, 0.168], [0.1, 0.152], [0.137, 0.118], [0.157, 0.07], [0.164, 0.02], [0.166, -0.03], [0.172, -0.072], [0.176, -0.088], [0.16, -0.094], [0.15, -0.088]]
    .map(([r, y]) => new THREE.Vector2(r, y));
  const hair = new THREE.Mesh(new THREE.LatheGeometry(bobProf, 64), M.hair); hair.position.set(0, 0.12, -0.006); head.add(hair);
  const face = new THREE.Group(); face.position.y = 0.12; head.add(face);
  const onFace = (x, y, r = 0.149) => { const d = V(x, y, Math.sqrt(Math.max(0, 1 - x * x - y * y))).normalize(); return { p: d.clone().multiplyScalar(r), n: d }; };
  const eyes = [];
  for (const sx of [1, -1]) {
    const e = new THREE.Mesh(new THREE.SphereGeometry(1, 16, 12), M.eye); const f = onFace(0.33 * sx, -0.06);
    e.position.copy(f.p); e.lookAt(f.p.clone().add(f.n)); e.scale.set(0.017, 0.026, 0.01); face.add(e);
    const gl = new THREE.Mesh(new THREE.SphereGeometry(1, 8, 6), M.glint); gl.position.set(-0.35, 0.45, 0.8); gl.scale.setScalar(0.28); e.add(gl);
    const ch = new THREE.Mesh(new THREE.SphereGeometry(1, 16, 8), M.cheek); const fc = onFace(0.56 * sx, -0.3, 0.146);
    ch.position.copy(fc.p); ch.lookAt(fc.p.clone().add(fc.n)); ch.scale.set(0.024, 0.016, 0.006); face.add(ch);
    eyes.push(e);
  }
  const mouths = {
    smile: new THREE.Mesh(new THREE.TorusGeometry(0.016, 0.0036, 6, 18, Math.PI), M.mouth),
    grin: new THREE.Mesh(new THREE.TorusGeometry(0.024, 0.0045, 6, 20, Math.PI), M.mouth),
    o: new THREE.Mesh(new THREE.TorusGeometry(0.009, 0.004, 6, 16), M.mouth),
    flat: new THREE.Mesh(new THREE.CapsuleGeometry(0.0035, 0.018, 4, 8), M.mouth),
    sad: new THREE.Mesh(new THREE.TorusGeometry(0.014, 0.0034, 6, 18, Math.PI), M.mouth),
  };
  const fm = onFace(0, -0.34, 0.148);
  for (const [k, m] of Object.entries(mouths)) {
    m.position.copy(fm.p); m.lookAt(fm.p.clone().add(fm.n));
    if (k === 'smile' || k === 'grin') m.rotateZ(Math.PI);
    if (k === 'flat') m.rotateZ(Math.PI / 2);
    face.add(m); m.visible = false;
  }

  // arms: shoulder -> upper arm -> elbow -> forearm -> hand
  const arms = {};
  for (const side of ['L', 'R']) {
    const sx = side === 'L' ? 1 : -1;
    const sh = new THREE.Group(); sh.position.set(0.118 * sx, 0.255, 0); chest.add(sh);
    const upper = capsule(0.033, 0.11, M.sleeve); sh.add(upper);
    const elbow = new THREE.Group(); elbow.position.y = -0.13; sh.add(elbow);
    const fore = capsule(0.03, 0.1, M.sleeve); elbow.add(fore);
    const hand = new THREE.Group(); hand.position.y = -0.125; elbow.add(hand);
    const palm = new THREE.Mesh(new THREE.SphereGeometry(0.036, 16, 12), M.skin); palm.scale.set(0.9, 1.05, 0.8); hand.add(palm);
    const grip = new THREE.Object3D(); grip.position.set(0, -0.025, 0.0); hand.add(grip);
    arms[side] = { sh, elbow, hand, grip };
  }

  const B = { root, pelvis, chest, head, face, legs, arms, eyes, mouths, M, id, cape };
  B.set = (p) => pose(B, p);
  B.set({});
  return B;
}

// pose: { walk: cycles (1 cycle = 2 steps), stride, sit, kneel, slide, headYaw, headPitch, headRoll, lookX, lookY,
//         blink (0..1), mouth, bag: 'hold'|'high'|'lap'|'out'|'tap', armL, armR ([x,z,elbow] overrides), lean, twist }
export function pose(B, p) {
  const TAU = Math.PI * 2;
  const { pelvis, chest, head, legs, arms } = B;
  const stride = p.stride === undefined ? 1 : p.stride;
  let bob = 0, twist = p.twist || 0, lean = p.lean || 0;
  const L = { hx: 0, knee: 0, ank: 0, hz: 0 }, R = { hx: 0, knee: 0, ank: 0, hz: 0 };
  let armL = [0.05, 0.06, 0.15], armR = [0.25, -0.05, 0.9];
  if (p.walk !== undefined && p.walk !== null) {
    const ph = p.walk * TAU;
    const sw = Math.sin(ph);
    L.hx = -0.44 * sw * stride; R.hx = 0.44 * sw * stride;
    L.knee = 0.75 * Math.pow(Math.max(0, Math.cos(ph)), 1.4) * stride + 0.06; R.knee = 0.75 * Math.pow(Math.max(0, -Math.cos(ph)), 1.4) * stride + 0.06;
    L.ank = -L.hx * 0.3 - L.knee * 0.5; R.ank = -R.hx * 0.3 - R.knee * 0.5;
    bob = 0.014 * Math.abs(Math.cos(ph)) * stride;
    twist += 0.07 * sw * stride;
    armL = [0.36 * sw * stride + 0.05, 0.06, 0.2 + 0.1 * Math.max(0, sw)];
    armR = [0.28 + 0.06 * sw, -0.05, 0.95];
  }
  if (p.sit) { // sitting on the ground, legs out straight, bag in the lap
    pelvis.position.y = 0.09; L.hx = R.hx = -1.5; L.knee = R.knee = 0.05; L.ank = R.ank = -0.2; L.hz = 0.06; R.hz = -0.06; lean += 0.12;
    armL = [0.75, -0.25, 1.1]; armR = [0.75, 0.25, 1.1];
  } else pelvis.position.y = 0.4 + bob;
  if (p.kneel) { pelvis.position.y = 0.24; L.hx = -1.4; L.knee = 1.45; L.ank = -0.05; R.hx = 0.1; R.knee = 1.9; R.ank = -0.25; lean += 0.25; }
  if (p.slide) { pelvis.position.y = 0.12; L.hx = R.hx = -1.45; L.knee = R.knee = 0.2; lean -= 0.2; armL = [-2.6, 0.3, 0.1]; armR = [-2.9, -0.2, 0.2]; }
  if (p.climb) { const ph = p.climb * TAU; const sw = Math.sin(ph); L.hx = -0.25 - 0.5 * Math.max(0, sw); R.hx = -0.25 - 0.5 * Math.max(0, -sw); L.knee = 0.4 + 0.7 * Math.max(0, sw); R.knee = 0.4 + 0.7 * Math.max(0, -sw); L.ank = -L.hx - L.knee * 0.5; R.ank = -R.hx - R.knee * 0.5; lean += 0.12; bob = 0; }
  if (p.bag === 'high') armR = [-2.7, -0.2, 0.15];
  if (p.bag === 'lap') armR = [0.75, 0.25, 1.1];
  if (p.bag === 'out') armR = [1.2, -0.1, 0.3];
  if (p.bag === 'up') armR = [-1.3, -0.1, 0.4];
  if (p.bag === 'tap') armR = [1.35, 0.05, 0.25];
  if (p.armL) armL = p.armL; if (p.armR) armR = p.armR;
  for (const [s, v] of [['L', L], ['R', R]]) {
    legs[s].hip.rotation.set(v.hx, 0, v.hz);
    legs[s].knee.rotation.set(v.knee, 0, 0);
    legs[s].ankle.rotation.set(v.ank, 0, 0);
    legs[s].cuff.rotation.set(v.hx, 0, v.hz);
  }
  for (const [s, a] of [['L', armL], ['R', armR]]) {
    const sx = s === 'L' ? 1 : -1;
    arms[s].sh.rotation.set(-a[0], 0, (0.12 + a[1]) * sx);
    arms[s].elbow.rotation.set(-a[2], 0, 0);
  }
  chest.rotation.set(lean, twist, 0);
  pelvis.rotation.set(0, -twist * 0.4, 0);
  head.rotation.set((p.headPitch || 0) - lean * 0.6, (p.headYaw || 0) - twist * 0.8, p.headRoll || 0, 'YXZ');
  // face
  const blink = p.blink || 0;
  for (const e of B.eyes) { e.scale.y = 0.026 * Math.max(0.12, 1 - blink); e.position.x = Math.sign(e.position.x) * Math.abs(e.position.x); }
  B.face.position.x = (p.lookX || 0) * 0.012; B.face.position.y = 0.12 + (p.lookY || 0) * 0.01;
  const m = p.mouth || 'smile'; for (const [k, mm] of Object.entries(B.mouths)) mm.visible = k === m;
}

// place Barney: feet at pos, his up along `up`, facing `fwd` (projected perpendicular to up)
export function place(B, pos, up, fwd, scale = 1) {
  const u = up.clone().normalize(); const f = fwd.clone().sub(u.clone().multiplyScalar(fwd.dot(u))).normalize();
  const r = new THREE.Vector3().crossVectors(u, f);
  const m = new THREE.Matrix4().makeBasis(r, u, f);
  B.root.quaternion.setFromRotationMatrix(m); B.root.position.copy(pos); B.root.scale.setScalar(scale);
  B.root.updateMatrixWorld(true);
}
export function gripWorld(B, side = 'R') { B.root.updateMatrixWorld(true); return B.arms[side].grip.getWorldPosition(new THREE.Vector3()); }
