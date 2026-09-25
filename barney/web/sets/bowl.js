// The real sea: a sandy pleated floor, deep ultramarine water, striped coral cones, kelp ribbons; and on the floor a glass
// bowl holding Barney's whole world: a disc of grey pleated plain and, above it, a lens of sea. Barney is tiny in there.
import { THREE, toon, film, PAL } from '../engine.js';
import { V } from '../kit.js';

export const BOWL_R = 2.4, BOWL_C = V(0, 2.1, 0);
export function realSea() {
  const g = new THREE.Group();
  const sand = new THREE.Mesh(new THREE.PlaneGeometry(400, 400), toon({ color: '#e7cf98', color2: '#c9b27f', pattern: 'pleats', axis: V(1, 0, 0.4), freq: 1.4 }));
  sand.rotation.x = -Math.PI / 2; g.add(sand);
  // the bowl: a glass sphere with its top cut open (the open neck is ringed with a lip)
  const glass = film({ tint: '#e6f6ff', alpha: 0.16, backTint: '#bfe3ff', backAlpha: 0.1, rim: 1, rimW: 0.09, hi: 0.95, hiDir: V(-0.5, 0.7, 0.55) });
  const bowlG = new THREE.SphereGeometry(BOWL_R, 96, 64, 0, Math.PI * 2, 0.42, Math.PI - 0.42);
  const bowl = new THREE.Mesh(bowlG, glass); bowl.position.copy(BOWL_C); g.add(bowl);
  const lipR = BOWL_R * Math.sin(0.42); const lip = new THREE.Mesh(new THREE.TorusGeometry(lipR, 0.05, 12, 96), toon({ color: '#e9f6ff' })); lip.rotation.x = Math.PI / 2; lip.position.set(0, BOWL_C.y + BOWL_R * Math.cos(0.42), 0); g.add(lip);
  // inside: the grey world, a disc of plain at the bottom and a lens of sea-blue near the top (the sea overhead)
  const inner = new THREE.Group(); inner.position.copy(BOWL_C); g.add(inner);
  const plainR = Math.sqrt(BOWL_R ** 2 - 1.1 ** 2) - 0.02;
  const disc = new THREE.Mesh(new THREE.CircleGeometry(plainR, 96), toon({ color: '#c3c0ba', color2: '#d8d6d1', pattern: 'pleats', axis: V(1, 0, 0.35), freq: 14 }));
  disc.rotation.x = -Math.PI / 2; disc.position.y = -1.1; inner.add(disc);
  // his sky: the lens of sea near the top of the bowl, seen from below as a blue ceiling
  const capR = Math.sqrt(BOWL_R ** 2 - 1.25 ** 2) - 0.02;
  const cap = new THREE.Mesh(new THREE.CircleGeometry(capR, 96), film({ tint: '#3d6fe0', alpha: 0.55, backTint: '#3d6fe0', backAlpha: 0.55, rim: 0, hi: 0, lineAtClip: false }));
  cap.rotation.x = Math.PI / 2; cap.position.y = 1.25; inner.add(cap);
  const capRing = new THREE.Mesh(new THREE.TorusGeometry(capR, 0.012, 8, 96), toon({ color: '#1b2e7a' })); capRing.rotation.x = Math.PI / 2; capRing.position.y = 1.25; inner.add(capRing);
  // coral cones and kelp
  const cones = [[-6, -4, 2.2, 0.6, PAL.fuchsia], [5, -6, 3.4, 0.9, PAL.lemon], [-9, -10, 5, 1.2, PAL.tangerine], [8, 1.5, 1.4, 0.4, '#2bb38a'], [-4.5, 3, 1.0, 0.3, PAL.red], [11, -12, 6, 1.5, PAL.fuchsia], [-13, -2, 3, 0.8, PAL.lemon]];
  for (const [x, z, h, r, c] of cones) { const m = new THREE.Mesh(new THREE.ConeGeometry(r, h, 40), toon({ color: '#f4efe6', color2: c, pattern: 'stripes', axis: V(0, 1, 0), freq: 6 / h, duty: 0.5 })); m.position.set(x, h / 2, z); g.add(m); }
  const kelpM = toon({ color: '#2bb38a', color2: '#8fe0c0', pattern: 'pleatsU', freq: 6, side: THREE.DoubleSide });
  const kelp = []; for (let i = 0; i < 14; i++) { const h = 4 + (i % 4) * 2; const k = new THREE.Mesh(new THREE.PlaneGeometry(0.5, h, 1, 16), kelpM); k.geometry.translate(0, h / 2, 0); k.position.set(-14 + i * 2.1 + (i % 3), 0, -8 - (i % 5) * 1.6); k.rotation.y = i * 0.7; g.add(k); kelp.push(k); }
  g.userData = { bowl, inner, disc, kelp, lip };
  return g;
}
export function swayKelp(S, t) { for (const [i, k] of S.userData.kelp.entries()) { const p = k.geometry.attributes.position; if (!k.userData.base) k.userData.base = Float32Array.from(p.array);
  const b = k.userData.base; for (let j = 0; j < p.count; j++) { const y = b[j * 3 + 1]; p.setX(j, b[j * 3] + 0.25 * Math.sin(t * 0.9 + y * 0.6 + i) * y / 4); } p.needsUpdate = true; } }
