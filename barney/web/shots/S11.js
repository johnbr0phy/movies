// S11 (10 s) Isometric, orthographic, locked. Barney climbs the stairs all the way round, sixteen steps up, and arrives
// where he began. He stops, looks straight at us, turns round and walks down... and arrives where he began again.
import { penrose, onStairs } from '../sets/stairs.js';
import { makeActor, drive } from '../actor.js';
export const ISO = (E, P) => { const c = P.userData.center.clone().add(E.v3(0, 0.3, 0)); return { pos: c.clone().add(E.v3(1, 1, 1).normalize().multiplyScalar(40)), tgt: c }; };
export default {
  dur: 12,
  async setup(E) {
    const { THREE } = E;
    const scene = new THREE.Scene(); const P = penrose(); scene.add(P);
    const a = makeActor(scene, { fill: 0.6 });
    const camera = E.ortho(6.6);
    E.G.uLight.value.set(0.35, 0.85, 0.55).normalize(); E.G.uShadowTint.value.set('#9ea0c8');
    return { scene, camera, a, P };
  },
  frame(t, s, E, dt) {
    const { v3, seg, ease, held } = E;
    const th = held(t);
    // 2 steps a second: up 16 steps in 8 s, pause, then down
    let u, back = false;
    if (th < 10) u = th * 2; else if (th < 11) u = 20; else { u = 20 - (th - 11) * 2; back = true; }
    const st = onStairs(s.P, u);
    const look = seg(t, 10.0, 10.4) * (1 - seg(t, 10.7, 11.0));
    const fwd = back ? st.fwd.clone().negate() : st.fwd;
    drive(s.a, t, dt, { pos: st.pos, up: v3(0, 1, 0), fwd, trueUp: v3(0, 1, 0),
      pose: (h) => ({ walk: (h < 10 || h >= 11) ? (u / 2) : null, stride: 0.7, headYaw: 0.9 * look, headPitch: -0.3 * look, mouth: look > 0.5 ? 'flat' : 'smile', blink: look > 0.5 && h > 10.5 && h < 10.6 ? 1 : 0 }) });
    const c = ISO(E, s.P); E.aim(s.camera, c.pos, c.tgt);
    return { bg: '#ecebe6' };
  },
};
