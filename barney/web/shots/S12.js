// S12 (7 s) The camera slides off the magic angle. The endless stair unwinds into what it really is: a spiral whose top
// hangs in the air metres above its own bottom. Barney, on the top step, looks down the drop, looks at us, and jumps it.
import { penrose, onStairs } from '../sets/stairs.js';
import { ISO } from './S11.js';
import { makeActor, drive } from '../actor.js';
export default {
  dur: 7,
  async setup(E) {
    const { THREE } = E;
    const scene = new THREE.Scene(); const P = penrose(); scene.add(P);
    const a = makeActor(scene, { fill: 0.6 });
    const camera = E.ortho(6.2);
    E.G.uLight.value.set(0.35, 0.85, 0.55).normalize(); E.G.uShadowTint.value.set('#9ea0c8');
    return { scene, camera, a, P };
  },
  frame(t, s, E, dt) {
    const { v3, seg, ease, held, lerp } = E;
    const th = held(t); const U = s.P.userData; const top = U.N - 1;
    let pos, fwd, pose;
    const tWalkEnd = 1.5; // walks the last three steps
    if (th < tWalkEnd) { const st = onStairs(s.P, top - 3 + th * 2, false); pos = st.pos; fwd = st.fwd; pose = { walk: th, stride: 0.7 }; }
    else if (t < 4.6) { const st = onStairs(s.P, top, false); pos = st.pos; fwd = st.fwd; const lk = seg(t, 2.8, 3.3) * (1 - seg(t, 3.9, 4.3));
      pose = { lean: 0.3 * seg(t, 1.8, 2.3), headPitch: 0.55 * seg(t, 1.8, 2.3) - 0.85 * lk, headYaw: -1.0 * lk, mouth: lk > 0.5 ? 'flat' : 'o' }; }
    else { const a0 = U.cells[top].world, a1 = U.cells[0].world; const k = seg(t, 4.6, 5.9, ease.inOut);
      pos = a0.clone().lerp(a1, k); pos.y += Math.sin(k * Math.PI) * 0.9; fwd = a1.clone().sub(a0).setY(0).normalize();
      pose = k < 1 ? { lean: -0.15, armL: [-2.4, 0.4, 0.2], bag: 'high', mouth: 'grin', walk: 0.25 } : { mouth: 'grin', walk: null }; }
    drive(s.a, t, dt, { pos, up: v3(0, 1, 0), fwd, trueUp: v3(0, 1, 0), pose: () => pose });
    const c = ISO(E, s.P); const u = seg(t, 0.3, 3.2, ease.inOut);
    const d = v3(1, 1, 1).normalize().applyAxisAngle(v3(0, 1, 0), -0.9 * u); d.y *= lerp(1, 0.35, u); d.normalize();
    const mid = U.cells[top].world.clone().add(U.cells[0].world).multiplyScalar(0.5).add(v3(0, -0.4, 0)); const tg = c.tgt.clone().lerp(mid, u);
    E.aim(s.camera, tg.clone().add(d.multiplyScalar(40)), tg);
    E.orthoSize(s.camera, lerp(6.6, 8.5, u));
    return { bg: '#ecebe6' };
  },
};
