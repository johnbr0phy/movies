// S16 (8 s) In Barney's frame: the tower face is his street, and he strolls "along" it (straight down the building).
// The camera takes his side, so the traffic pours vertically through the frame and the towers across the canyon hang
// overhead like a ceiling. The giant goldfish on the billboard turns its eye to follow the little one in the bag.
import { city, traffic, driveTraffic } from '../sets/city.js';
import { makeActor, drive, walkCycles } from '../actor.js';
export default {
  dur: 8,
  async setup(E) {
    const { THREE } = E;
    const scene = new THREE.Scene(); const C = city(); scene.add(C); const cars = traffic(scene, 44, (l) => l.y > 40 && l.y < 62 && l.z < 1.5);
    const a = makeActor(scene, { fill: 0.6 });
    const camera = E.persp(46);
    E.G.uLight.value.set(0.35, 0.6, 0.72).normalize(); E.G.uShadowTint.value.set('#8fb3bd');
    E.POST.uHazeDist.value = 60; E.POST.uHaze.value.set('#8fd0c8');
    return { scene, camera, a, C, cars };
  },
  frame(t, s, E, dt) {
    const { v3, seg, ease } = E;
    driveTraffic(s.cars, t + 28);
    const speed = 0.68; const y = 57.6 - speed * t;
    drive(s.a, t, dt, { pos: v3(0.4, y, -3.96), up: v3(0, 0, 1), fwd: v3(0, -1, 0), trueUp: v3(0, 1, 0),
      pose: (th) => ({ walk: walkCycles(speed * th), headYaw: -0.7 * seg(th, 3.0, 3.6) * (1 - seg(th, 6.2, 6.8)), headPitch: -0.35 * seg(th, 3.0, 3.6) * (1 - seg(th, 6.2, 6.8)), mouth: th > 3.2 && th < 6.4 ? 'o' : 'smile' }) });
    // billboard fish swims in place
    s.C.userData.bf.set(t * 0.4, 0.4);
    // camera: in his frame, ahead of him and to his right, his up is our up
    const b = v3(0.4, y, -3.96);
    E.aim(s.camera, b.clone().add(v3(-2.2, -3.4, 1.3)), b.clone().add(v3(0.3, -0.2, 0.9)), 0, v3(0, 0, 1));
    return { bg: '#8fd0c8' };
  },
};
