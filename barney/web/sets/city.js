// The vertical city: a canyon of towers with no top and no bottom, teal haze, sodium windows, layered flying traffic.
// Barney's tower faces the canyon at z = -4 (its face is his street). The canyon runs along x.
import { THREE, toon, PAL } from '../engine.js';
import { V, box } from '../kit.js';
import { makeFish } from '../rig/fish.js';

const FACADES = [
  () => toon({ color: '#16505a', color2: '#ff9b3d', pattern: 'checker', axis: V(1, 0, 0), axis2: V(0, 1, 0), freq: 1.1 }),
  () => toon({ color: '#e8dcc4', color2: '#1c2b52', pattern: 'stripes', axis: V(0, 1, 0), freq: 1.4, duty: 0.35 }),
  () => toon({ color: '#20343f', color2: '#ffc16b', pattern: 'checker', axis: V(1, 0, 0), axis2: V(0, 1, 0), freq: 0.8 }),
  () => toon({ color: '#b3462c', color2: '#f4e7cf', pattern: 'stripes', axis: V(1, 0, 0), freq: 1.2, duty: 0.3 }),
];

export function city() {
  const g = new THREE.Group();
  // Barney's tower: windows in a strict grid he can walk on
  const home = box(14, 400, 12, toon({ color: '#1d5963', color2: '#ffae52', pattern: 'checker', axis: V(1, 0, 0), axis2: V(0, 1, 0), freq: 1.6 }), V(0, 0, -10)); g.add(home);
  // window mullions as thin bars on the face (so his steps land on something)
  const mull = toon({ color: '#0f3238' });
  for (let x = -6.5; x <= 6.5; x += 1.25) g.add(box(0.06, 400, 0.08, mull, V(x, 0, -3.96)));
  // other towers: both sides of the canyon, receding
  let seed = 11; const r = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  const towers = [];
  for (let i = 0; i < 26; i++) {
    const side = i % 2 === 0 ? -1 : 1; const x = (i - 13) * 11 + (r() - 0.5) * 5; if (side < 0 && Math.abs(x) < 9) continue;
    const w = 7 + r() * 6, d = 7 + r() * 6; const z = side < 0 ? -10 - r() * 6 : 16 + r() * 14;
    const t = box(w, 400, d, FACADES[i % FACADES.length](), V(x, (r() - 0.5) * 40, z)); g.add(t); towers.push(t);
    // a band of lit lettering-free signage
    if (r() < 0.6) g.add(box(w * 0.8, 2.2, 0.3, toon({ color: [PAL.fuchsia, PAL.lemon, '#2bb38a', PAL.tangerine][i % 4], emit: 1, flat: 1 }), V(x, 10 + r() * 60, z + (side < 0 ? d / 2 + 0.2 : -d / 2 - 0.2))));
  }
  // the goldfish billboard across the canyon
  const bb = new THREE.Group(); bb.position.set(6, 64, 15.2);
  bb.add(box(16, 9, 0.4, toon({ color: PAL.cobalt, color2: '#2a58d8', pattern: 'stripes', axis: V(0, 1, 0), freq: 2, duty: 0.5 }), V(0, 0, 0)));
  bb.add(box(16.6, 0.4, 0.6, toon({ color: PAL.lemon }), V(0, 4.7, 0)), box(16.6, 0.4, 0.6, toon({ color: PAL.lemon }), V(0, -4.7, 0)));
  const bf = makeFish(); bf.g.scale.setScalar(130); bf.g.position.set(0, 0, -1.5); bf.g.rotation.y = Math.PI; bb.add(bf.g); g.add(bb);
  g.userData = { home, bb, bf };
  return g;
}

// flying cars: capsule pods with a tail fin; lanes at fixed heights and depths, looping along x
export function traffic(scene, n = 44, avoid = null) {
  const cols = [PAL.tangerine, '#e8dcc4', '#2bb38a', PAL.red, PAL.lemon, '#20343f'];
  const cars = [];
  let seed = 5; const r = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  for (let i = 0; i < n; i++) {
    const c = new THREE.Group(); const col = cols[i % cols.length];
    const body = new THREE.Mesh(new THREE.CapsuleGeometry(0.75, 2.6, 8, 20), toon({ color: col })); body.rotation.z = Math.PI / 2; c.add(body);
    const cab = new THREE.Mesh(new THREE.SphereGeometry(0.62, 20, 12, 0, Math.PI * 2, 0, Math.PI / 2), toon({ color: '#9fe3ec', flat: 0.4 })); cab.position.set(0.5, 0.45, 0); c.add(cab);
    const fin = box(0.9, 1.0, 0.08, toon({ color: col === PAL.tangerine ? PAL.lemon : PAL.tangerine }), V(-1.6, 0.8, 0)); c.add(fin);
    const lamp = box(0.12, 0.3, 1.1, toon({ color: '#fff3c0', emit: 1, flat: 1 }), V(2.05, 0, 0)); c.add(lamp);
    scene.add(c);
    let lane; do { lane = { y: -30 + r() * 140, z: -1.5 + r() * 14, v: (r() < 0.5 ? -1 : 1) * (8 + r() * 14), x0: r() * 240 - 120 }; } while (avoid && avoid(lane));
    cars.push({ c, lane });
  }
  return cars;
}
export function driveTraffic(cars, t) {
  for (const { c, lane } of cars) { let x = lane.x0 + lane.v * t; x = ((x + 120) % 240 + 240) % 240 - 120; c.position.set(x, lane.y + 0.3 * Math.sin(t * 1.3 + lane.x0), lane.z); c.rotation.y = lane.v > 0 ? 0 : Math.PI; }
}
