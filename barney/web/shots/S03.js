// S03 (9 s) The gallery, from the near end. A long Breton corridor with a colonnade and a red door at the end.
// Barney walks away from us, and instead of shrinking into the distance he GROWS against it: the gallery is forced
// perspective (7 m pretending to be 30). He reaches the knee-high door and looks back at us.
import { galleria } from '../sets/corridor.js';
import { makeActor, drive, walkCycles } from '../actor.js';
export default {
  dur: 9,
  async setup(E) {
    const { THREE } = E;
    const scene = new THREE.Scene(); const set = galleria(); scene.add(set);
    const a = makeActor(scene, { fill: 0.6 });
    const camera = E.persp(40);
    E.G.uLight.value.set(0.35, 0.8, 0.5).normalize();
    return { scene, camera, a, set };
  },
  frame(t, s, E, dt) {
    const { v3, seg, ease, lerp } = E;
    const speed = 0.74; const stopAt = 8.0; const tw = Math.min(t, stopAt);
    const z = 0.3 - speed * tw * (1 - 0.15 * seg(t, 7.2, 8.0));
    const u = (0.6 - z) / 7.6; const fl = s.set.userData.at(u).fl;
    const turn = seg(t, 8.0, 8.5, ease.inOut);
    drive(s.a, t, dt, { pos: v3(0, fl, z), up: v3(0, 1, 0), fwd: v3(0, 0, -1), trueUp: v3(0, 1, 0),
      pose: (th) => ({ walk: th < stopAt ? walkCycles(speed * th) : null, headYaw: Math.PI * 0.72 * turn, mouth: turn > 0.5 ? 'o' : 'smile', blink: (th % 2.7) > 2.6 ? 1 : 0 }) });
    E.aim(s.camera, v3(0, 1.3, 2.4), v3(0, 0.95, -7));
    return { bg: '#efe8dc' };
  },
};
