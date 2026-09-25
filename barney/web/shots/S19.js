// S19 (9 s) Close. Barney sits on the grey plain, the bag in his lap, half empty; the fish is cramped. He looks at it.
// Then a drop leaves the hole in the bag and falls UP. He watches it rise into the sky, and the camera goes with it.
import { plain, setSpots, greyWorld } from '../sets/plain.js';
import { makeActor, drive } from '../actor.js';
import { makeDrops, updateDrops } from '../drops.js';
export default {
  dur: 9,
  async setup(E) {
    const { THREE } = E;
    const scene = new THREE.Scene(); const P = plain(); scene.add(P);
    const a = makeActor(scene, { fill: 0.36 });
    greyWorld(scene, a.bag.fish.g);
    const D = makeDrops(scene, 4, '#d0d0ce');
    const camera = E.persp(34);
    E.G.uLight.value.set(0.2, 0.9, 0.35).normalize(); E.G.uShadowTint.value.set('#c2c2c6'); E.G.uShadowMix.value = 0.6;
    E.POST.uVignette.value = 0.4;
    return { scene, camera, a, P, D };
  },
  frame(t, s, E, dt) {
    const { v3, seg, ease, lerp } = E;
    const look = seg(t, 5.2, 5.8, ease.inOut);
    drive(s.a, t, dt, { pos: v3(0, 0, 0), up: v3(0, 1, 0), fwd: v3(0, 0, 1), trueUp: v3(0, 1, 0), fill: 0.36, swim: 0.3, roam: 0.4,
      pose: (th) => ({ sit: true, bag: 'lap', headPitch: 0.45 * (1 - look) - 0.9 * look, mouth: th > 5.6 ? 'o' : 'sad', blink: (th > 2.5 && th < 2.65) ? 1 : 0 }) });
    setSpots(s.P, [v3(-0.35, 0, 0.25), v3(0.3, 0, -0.4), v3(0.1, 0, 0.5)]);
    // the drop: leaves the bag at 4.6 s and accelerates upward
    const hole = s.a.bag.g.localToWorld(v3(0.06, -0.19, 0.03));
    if (!s.D.list.length) s.D.list.push({ t0: 4.6, v0: v3(0, 0.05, 0), size: 2.6, life: 6 });
    if (t <= 4.6 || !s.D.list[0].p0) s.D.list[0].p0 = hole.clone();
    updateDrops(s.D, t, v3(0, 1.1, 0));
    const dp = t > 4.6 ? s.D.list[0].p0.clone().add(v3(0, 0.05 * (t - 4.6) + 0.55 * (t - 4.6) ** 2, 0)) : hole;
    // camera: a low medium close-up, then tilts up and rises with the drop
    const u = seg(t, 5.4, 9, ease.inOut);
    const cp = v3(0.9, 0.75, 1.8).lerp(v3(0.5, 0.9, 1.3), u);
    const ct = v3(0, 0.45, 0).lerp(dp.clone().add(v3(0, 0.3, 0)), Math.min(1, u * 1.2));
    E.aim(s.camera, cp, ct);
    return { bg: '#c9c8c4' };
  },
};
