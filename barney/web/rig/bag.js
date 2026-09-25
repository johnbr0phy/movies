// The plastic bag. It hangs from Barney's hand by HIS gravity (a damped pendulum), but the water inside obeys the
// TRUE down: every frame the water level is solved by volume against the true up, and the fish swims in what is wet.
import { THREE, film, toon, PAL, newId, mesh } from '../engine.js';
import { makeFish, orientFish } from './fish.js';

const PROFILE = [[0.002, 0.03], [0.006, 0.016], [0.011, 0.0], [0.02, -0.02], [0.036, -0.045], [0.058, -0.078], [0.076, -0.115], [0.085, -0.155], [0.083, -0.19], [0.07, -0.222], [0.045, -0.243], [0.018, -0.252], [0.0005, -0.254]];
function radiusAt(y) { // interior radius at height y (bag local)
  for (let i = 1; i < PROFILE.length; i++) { const [r0, y0] = PROFILE[i - 1], [r1, y1] = PROFILE[i]; if (y <= y0 && y >= y1) return r0 + (r1 - r0) * (y - y0) / (y1 - y0); }
  return 0;
}

export function makeBag(o = {}) {
  const g = new THREE.Group(); g.name = 'bag';
  const prof = PROFILE.map(([r, y]) => new THREE.Vector2(r, y));
  const bagG = new THREE.LatheGeometry(prof, 40);
  // crinkle: small irregular radial dents so it reads as plastic, not glass
  const pa = bagG.attributes.position; const rnd = (i) => Math.sin(i * 12.9898) * 43758.5453 % 1;
  for (let i = 0; i < pa.count; i++) { const x = pa.getX(i), z = pa.getZ(i), y = pa.getY(i); const a = Math.atan2(z, x);
    const k = 1 + 0.035 * Math.sin(a * 5 + y * 40) + 0.02 * Math.sin(a * 11 - y * 70); pa.setX(i, x * k); pa.setZ(i, z * k); }
  bagG.computeVertexNormals();
  const bagM = film({ tint: '#e8f6ff', alpha: 0.1, backAlpha: 0.05, rimW: 0.12, hi: 0.9 });
  const bag = mesh(bagG, bagM); g.add(bag);
  const waterG = new THREE.LatheGeometry(prof.map(v => new THREE.Vector2(v.x * 0.965, v.y)), 40);
  const waterM = film({ tint: o.water || '#6fcfff', alpha: 0.3, backTint: o.surface || '#c6f0ff', backAlpha: 0.55, rimW: 0.05, rim: 0.7, lineAtClip: true, hi: 0.5 });
  const water = mesh(waterG, waterM); g.add(water);
  // the tie: a twist of red plastic above the knot
  const tie = new THREE.Mesh(new THREE.ConeGeometry(0.012, 0.04, 12), toon({ color: PAL.red })); tie.position.y = 0.035; tie.rotation.x = Math.PI; g.add(tie);
  const loop = new THREE.Mesh(new THREE.TorusGeometry(0.018, 0.0035, 6, 18), toon({ color: PAL.red })); loop.position.y = 0.062; g.add(loop);
  // interior samples for the volume solve (uniform in volume)
  const pts = []; let seed = 7; const rr = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  while (pts.length < 1600) { const y = -0.254 + rr() * 0.28; const r = radiusAt(y) * 0.95; if (r <= 0) continue; const x = (rr() * 2 - 1) * 0.09, z = (rr() * 2 - 1) * 0.09; if (x * x + z * z < r * r) pts.push(new THREE.Vector3(x, y, z)); }
  const fish = makeFish(); g.add(fish.g); // fish lives in bag space but is oriented with the true up
  const B = { g, bag, water, bagM, waterM, pts, fish, fill: o.fill === undefined ? 0.62 : o.fill, level: 0, wet: [] };
  // pendulum state
  B.sim = { dir: null, vel: new THREE.Vector3(), last: null };
  return B;
}

// hang the bag from `anchor` (world), with Barney's local down `down`; dt for the pendulum (0 to snap)
export function hang(B, anchor, down, dt = 0, extra = null) {
  const d = down.clone().normalize();
  const s = B.sim;
  if (!s.dir || dt <= 0) { s.dir = d.clone(); s.vel.set(0, 0, 0); s.last = anchor.clone(); }
  else {
    // anchor acceleration pushes the bag back; spring towards local down; damping
    const vA = anchor.clone().sub(s.last).divideScalar(dt); s.prevVA = s.prevVA || vA.clone();
    const aA = vA.clone().sub(s.prevVA).divideScalar(dt); s.prevVA = vA; s.last = anchor.clone();
    const L = 0.16;
    const acc = d.clone().multiplyScalar(9.8).sub(aA).divideScalar(L);
    const tang = acc.sub(s.dir.clone().multiplyScalar(acc.dot(s.dir)));
    s.vel.add(tang.multiplyScalar(dt)).multiplyScalar(Math.exp(-3.2 * dt));
    s.dir.add(s.vel.clone().multiplyScalar(dt)).normalize();
  }
  const dir = extra ? extra.clone().normalize() : s.dir;
  B.g.position.copy(anchor);
  B.g.quaternion.setFromUnitVectors(new THREE.Vector3(0, -1, 0), dir);
  B.g.updateMatrixWorld(true);
}

// solve the water against the true up; place the fish; t is held time for the swim cycle
export function settle(B, trueUp, t, opts = {}) {
  const u = trueUp.clone().normalize();
  const mw = B.g.matrixWorld;
  const hs = B.pts.map(p => p.clone().applyMatrix4(mw)).map(w => ({ w, h: w.dot(u) }));
  hs.sort((a, b) => a.h - b.h);
  const n = Math.max(1, Math.floor(B.fill * hs.length));
  const level = n >= hs.length ? hs[hs.length - 1].h + 1 : hs[n - 1].h;
  B.level = level;
  const plane = new THREE.Vector4(u.x, u.y, u.z, -level);
  B.waterM.uniforms.uClip.value.copy(plane); B.waterM.uniforms.uClipOn.value = 1;
  B.water.visible = B.fill > 0.005;
  // fish: centre of the wet points, pulled a little below the surface, drifting in a slow loop
  const wet = hs.slice(0, n); let c = new THREE.Vector3(); for (const p of wet) c.add(p.w); c.divideScalar(Math.max(1, wet.length));
  const depth = level - c.dot(u);
  const side = new THREE.Vector3().crossVectors(u, Math.abs(u.y) < 0.9 ? new THREE.Vector3(0, 1, 0) : new THREE.Vector3(1, 0, 0)).normalize();
  const side2 = new THREE.Vector3().crossVectors(u, side);
  const a = t * (opts.swim === undefined ? 0.9 : opts.swim);
  const rad = Math.min(0.03, depth * 0.8) * (opts.roam === undefined ? 1 : opts.roam);
  const pos = c.clone().add(side.clone().multiplyScalar(Math.cos(a) * rad)).add(side2.clone().multiplyScalar(Math.sin(a) * rad * 0.6));
  if (opts.fishAt) pos.copy(opts.fishAt);
  const fwd = side.clone().multiplyScalar(-Math.sin(a)).add(side2.clone().multiplyScalar(Math.cos(a) * 0.6)).normalize();
  // fish is a child of the bag group: convert world pose into bag space
  const inv = new THREE.Matrix4().copy(mw).invert();
  const localPos = pos.clone().applyMatrix4(inv);
  const q = new THREE.Quaternion().setFromRotationMatrix(new THREE.Matrix4().makeBasis(fwd, u, new THREE.Vector3().crossVectors(fwd, u).normalize()));
  const bq = new THREE.Quaternion(); B.g.getWorldQuaternion(bq);
  B.fish.g.position.copy(localPos); B.fish.g.quaternion.copy(bq.clone().invert().multiply(q));
  B.fish.g.visible = opts.fish !== false;
  B.fish.set(t, 1);
  return { level, center: c, surfacePoint: c.clone().add(u.clone().multiplyScalar(depth)) };
}
