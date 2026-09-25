// S15 (8 s) The canyon. We look down a vertical city with no ground. Barney drops in from the top of frame, tumbling,
// and lands feet-first on the face of a tower as if it were pavement. He stands, straightens his cape, looks about.
import { city, traffic, driveTraffic } from '../sets/city.js';
import { makeActor, drive } from '../actor.js';
export default {
  dur: 8,
  async setup(E) {
    const { THREE } = E;
    const scene = new THREE.Scene(); const C = city(); scene.add(C); const cars = traffic(scene, 44, (l) => l.y > 50 && l.y < 90 && l.z > 1.2);
    const a = makeActor(scene, { fill: 0.6 });
    const camera = E.persp(44);
    E.G.uLight.value.set(0.35, 0.6, 0.72).normalize(); E.G.uShadowTint.value.set('#8fb3bd');
    E.POST.uHazeDist.value = 60; E.POST.uHaze.value.set('#8fd0c8');
    return { scene, camera, a, C, cars };
  },
  frame(t, s, E, dt) {
    const { v3, seg, ease, lerp } = E;
    driveTraffic(s.cars, t + 20);
    const land = 3.4; const Y = 58;
    let pos, up, fwd, pose;
    if (t < land) { const k = t / land; pos = v3(0.4, Y + 30 * (1 - k) * (1 - k) + 0.3, -3.2 + 1.8 * Math.sin(k * 3)); const sp = t * 5.5;
      up = v3(0, 1, 0).applyAxisAngle(v3(1, 0, 0), sp).applyAxisAngle(v3(0, 1, 0), 0.4 * sp); fwd = v3(0, 0, 1).applyAxisAngle(v3(1, 0, 0), sp);
      pose = () => ({ slide: true, bag: 'high', mouth: 'o' }); }
    else { const k = seg(t, land, land + 0.5, ease.out); pos = v3(0.4, Y, -3.96); up = v3(0, 0, 1); fwd = v3(0, -1, 0);
      pose = (th) => (th < land + 0.6 ? { kneel: true, bag: 'hold', mouth: 'o' } : { headYaw: 0.8 * Math.sin((th - land) * 1.4) * seg(th, 5.2, 6.0), mouth: th > 6.6 ? 'smile' : 'o', armL: th > 4.6 && th < 5.4 ? [0.2, -0.9, 1.6] : undefined }); }
    drive(s.a, t, dt, { pos, up, fwd, trueUp: v3(0, 1, 0), pose });
    // crane down the canyon: from above looking down, ending level with the facade at Barney
    const u = seg(t, 0, land + 0.8, ease.inOut);
    const cp = v3(5.5, Y + 26, 9).lerp(v3(3.4, Y + 0.5, -1.6), u);
    const ct = v3(0, Y - 40, -4).lerp(v3(0.3, Y + 0.1, -3.4), u);
    E.aim(s.camera, cp, ct, 0, v3(0, 1, 0));
    return { bg: '#8fd0c8' };
  },
};
