// S09 (9 s) The runway. The Pleats walk it in lockstep, flat to the audience, sliding sideways like a frieze.
// Barney walks in from the left at a different rhythm, watches, and falls into step with them. The camera tracks.
import { runway, makePleats } from '../sets/runway.js';
import { makeActor, drive, walkCycles } from '../actor.js';
export default {
  dur: 9,
  async setup(E) {
    const { THREE } = E;
    const scene = new THREE.Scene(); scene.add(runway());
    const P = makePleats(scene, 8);
    const a = makeActor(scene, { fill: 0.6 });
    const camera = E.persp(32);
    E.G.uLight.value.set(-0.3, 0.8, 0.6).normalize();
    E.G.uShadowTint.value.set('#c4c3d8');
    return { scene, camera, a, P };
  },
  frame(t, s, E, dt) {
    const { v3, seg, ease, held } = E;
    const speed = 0.68; // Pleats move 0.68 m/s, the same as Barney's walk
    const th = held(t);
    s.P.forEach((p, i) => {
      const x = -8 + i * 2.1 + speed * t;
      const ph = th * 2; // two steps a second
      p.position.set(x, 0.0 + 0.05 * Math.abs(Math.sin(ph * Math.PI)), -0.4);
      p.rotation.set(0, 0, 0.04 * Math.sin(ph * Math.PI));
    });
    // Barney: enters at a hurry, slows into step between Pleats 3 and 4
    const bx = -3.2 + speed * t + 0.9 * (1 - seg(t, 0, 3.2, ease.out));
    const inStep = seg(t, 3.2, 4.2);
    drive(s.a, t, dt, { pos: v3(bx, 0, 0.75), up: v3(0, 1, 0), fwd: v3(1, 0, 0), trueUp: v3(0, 1, 0),
      pose: (h) => ({ walk: walkCycles(speed * h) + 0.3 * (1 - inStep), headYaw: -0.6 * seg(h, 1.2, 2.2) * (1 - seg(h, 6.5, 7.4)), mouth: h > 4 ? 'grin' : 'o', twist: 0 }) });
    const cx = -1.6 + speed * t;
    E.aim(s.camera, v3(cx, 1.35, 9.5), v3(cx, 1.45, 0));
    return { bg: '#e4e1db' };
  },
};
