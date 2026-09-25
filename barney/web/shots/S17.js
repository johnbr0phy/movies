// S17 (6 s) Close, in Barney's frame. An orange taxi pod skims the facade and its fin nicks the bag. The bag jolts, a
// jet of water squirts out and falls "forward" along his street (which is straight down the tower). He pinches the
// hole with his other hand. It still drips.
import { city, traffic, driveTraffic } from '../sets/city.js';
import { makeActor, drive, walkCycles } from '../actor.js';
import { makeDrops, updateDrops } from '../drops.js';
export default {
  dur: 6,
  async setup(E) {
    const { THREE, PAL, toon, v3 } = E;
    const scene = new THREE.Scene(); const C = city(); scene.add(C); const cars = traffic(scene, 30, (l) => l.y > 40 && l.y < 62 && l.z < 3);
    const a = makeActor(scene, { fill: 0.6 });
    // the taxi
    const taxi = new THREE.Group();
    const body = new THREE.Mesh(new THREE.CapsuleGeometry(0.75, 2.6, 8, 20), toon({ color: PAL.tangerine })); body.rotation.z = Math.PI / 2; taxi.add(body);
    const cab = new THREE.Mesh(new THREE.SphereGeometry(0.62, 20, 12, 0, Math.PI * 2, 0, Math.PI / 2), toon({ color: '#9fe3ec' })); cab.position.set(0.5, 0.45, 0); taxi.add(cab);
    const fin = new THREE.Mesh(new THREE.BoxGeometry(0.34, 0.05, 1.5), toon({ color: PAL.lemon })); fin.position.set(-1.7, 0, 1.3); taxi.add(fin);
    const chk = new THREE.Mesh(new THREE.CylinderGeometry(0.77, 0.77, 0.3, 24, 1, true), toon({ color: '#16141b', color2: '#f4efe6', pattern: 'checker', axis: v3(1, 0, 0), axis2: v3(0, 1, 0), freq: 6, side: THREE.DoubleSide })); chk.rotation.z = Math.PI / 2; chk.position.x = 0.2; taxi.add(chk);
    scene.add(taxi);
    const D = makeDrops(scene, 90);
    const camera = E.persp(40);
    E.G.uLight.value.set(0.35, 0.6, 0.72).normalize(); E.G.uShadowTint.value.set('#8fb3bd');
    E.POST.uHazeDist.value = 60; E.POST.uHaze.value.set('#8fd0c8');
    return { scene, camera, a, C, cars, taxi, D };
  },
  frame(t, s, E, dt) {
    const { v3, seg, ease } = E;
    driveTraffic(s.cars, t + 36);
    const hit = 1.9; const speed = 0.68;
    const walkT = Math.min(t, hit + 0.1) + Math.max(0, t - 3.6) * 0.6; const y = 52.2 - speed * walkT;
    const jolt = t > hit ? Math.exp(-(t - hit) * 4) * Math.sin((t - hit) * 30) : 0;
    const bagDir = t > hit && t < hit + 1.2 ? v3(0, 0, -1).add(v3(0.9 * jolt, 0, 0)).normalize() : null;
    const fill = 0.6 - 0.08 * seg(t, hit, 6);
    const info = drive(s.a, t, dt, { pos: v3(0.4, y, -3.96), up: v3(0, 0, 1), fwd: v3(0, -1, 0), trueUp: v3(0, 1, 0), fill, bagDir,
      pose: (th) => (th < hit + 0.1 ? { walk: walkCycles(speed * th), mouth: 'smile' } : { walk: th > 3.6 ? walkCycles(speed * walkT) : null, mouth: th < 2.6 ? 'o' : 'flat', lean: -0.2 * seg(th, hit, hit + 0.3) * (1 - seg(th, 2.6, 3.2)),
        armL: th > 2.5 ? [0.85, -0.8, 0.95] : [1.4, 0.2, 0.4], headPitch: 0.35 * seg(th, 2.3, 2.8), headYaw: -0.35 * seg(th, 2.3, 2.8) }) });
    // taxi: flies along -x past him, its fin skimming the bag at t = hit
    const bagP = s.a.bag.g.localToWorld(v3(0, -0.15, 0));
    s.taxi.position.set(bagP.x - 1.7 + 16 * (hit - t), bagP.y - 0.1, bagP.z + 1.75); s.taxi.rotation.set(0, Math.PI, 0);
    // drops: a jet at the hit, then a steady drip from the hole; they fall along the true down (-y)
    if (!s.D.list.length) {
      for (let i = 0; i < 26; i++) s.D.list.push({ t0: hit + i * 0.012, v0: v3(-1.4 - i * 0.05, 0.8, 0.5 + (i % 5) * 0.1), rel: true, size: 1.2 });
      for (let i = 0; i < 40; i++) s.D.list.push({ t0: hit + 0.8 + i * 0.12 + (i % 3) * 0.02, v0: v3(0, 0, 0.05), rel: true, size: 0.9 });
    }
    const hole = s.a.bag.g.localToWorld(v3(0.06, -0.19, 0.03));
    for (const d of s.D.list) if (!d.p0 || (d.rel && t < d.t0 + 0.001)) d.p0 = hole.clone();
    updateDrops(s.D, t, v3(0, -9.8, 0));
    // camera: his frame, closer, with a handheld kick at the hit
    const b = v3(0.4, y, -3.96);
    const shake = v3(0.04 * jolt, 0.03 * Math.sin(t * 41) * Math.abs(jolt), 0.02 * jolt);
    E.aim(s.camera, b.clone().add(v3(-1.6, -2.3, 1.0)).add(shake), b.clone().add(v3(0.1, -0.1, 0.55)), 0, v3(0, 0, 1));
    return { bg: '#8fd0c8' };
  },
};
