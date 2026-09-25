// S04 (5 s) The gallery side on, orthographic, near wall removed: it is a short funnel. Barney, his real size, stoops
// under the low far end and kneels at the little red door.
import { galleria } from '../sets/corridor.js';
import { makeActor, drive } from '../actor.js';
export default {
  dur: 5,
  async setup(E) {
    const { THREE } = E;
    const scene = new THREE.Scene(); const set = galleria(); scene.add(set);
    set.traverse(o => { if (o.name === 'nearWall' || o.name === 'nearCol' || o.name === 'ceil') o.visible = false; });
    const a = makeActor(scene, { fill: 0.6 });
    const camera = E.ortho(4.6);
    E.G.uLight.value.set(0.6, 0.75, 0.3).normalize();
    return { scene, camera, a, set };
  },
  frame(t, s, E, dt) {
    const { v3, seg, ease } = E;
    const z = -6.25; const fl = s.set.userData.at((0.6 - z) / 7.6).fl;
    const k = seg(t, 1.2, 2.4, ease.inOut);
    drive(s.a, t, dt, { pos: v3(0, fl, z), up: v3(0, 1, 0), fwd: v3(0, 0, -1), trueUp: v3(0, 1, 0),
      pose: (th) => (k > 0.5 ? { kneel: true, headPitch: -0.1, bag: 'hold', armL: [1.3 * seg(th, 2.6, 3.4), 0.1, 0.3] } : { walk: null, lean: 0.35 * k, headPitch: 0.2 * k }) });
    E.aim(s.camera, v3(10, 4.2, -3.0), v3(0, 1.3, -3.0));
    return { bg: '#efe8dc' };
  },
};
