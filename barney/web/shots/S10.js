// S10 (8 s) The camera orbits 90 degrees round the procession. As it swings edge-on the Pleats thin to lines and vanish:
// they are paper. Barney, who is not paper, is left walking alone in a line of hairlines. The last Pleat folds itself
// into a crane and flies off over the curtain.
import { runway, makePleats, crane, flap, PLEAT_COLS } from '../sets/runway.js';
import { makeActor, drive, walkCycles } from '../actor.js';
export default {
  dur: 8,
  async setup(E) {
    const { THREE } = E;
    const scene = new THREE.Scene(); scene.add(runway());
    const P = makePleats(scene, 8);
    const a = makeActor(scene, { fill: 0.6 });
    const C = crane(PLEAT_COLS[5]); C.visible = false; scene.add(C);
    const camera = E.persp(34);
    E.G.uLight.value.set(-0.3, 0.8, 0.6).normalize();
    return { scene, camera, a, P, C };
  },
  frame(t, s, E, dt) {
    const { v3, seg, ease, held, lerp } = E;
    const speed = 0.68; const T0 = 9; const tt = T0 + t; const th = held(tt);
    s.P.forEach((p, i) => {
      const x = -8 + i * 2.1 + speed * tt; const ph = th * 2;
      p.position.set(x, 0.05 * Math.abs(Math.sin(ph * Math.PI)), -0.4); p.rotation.set(0, 0, 0.04 * Math.sin(ph * Math.PI));
      p.visible = true;
    });
    // the red Pleat (index 5) folds into a crane at 5.2 s and flies off
    const fold = seg(t, 4.6, 5.4, ease.inOut); const fp = s.P[5];
    fp.scale.set(1 - 0.85 * fold, 1 - 0.8 * fold, 1);
    if (t > 5.4) { fp.visible = false; s.C.visible = true; const k = t - 5.4;
      s.C.position.set(fp.position.x + k * 1.6, 1.4 + k * 1.1 + 0.1 * Math.sin(k * 6), -0.4 - k * 1.2); s.C.rotation.set(0, 0.5, 0.25); s.C.scale.setScalar(0.55); flap(s.C, tt); }
    const bx = -3.2 + speed * tt;
    drive(s.a, tt, dt, { pos: v3(bx, 0, 0.75), up: v3(0, 1, 0), fwd: v3(1, 0, 0), trueUp: v3(0, 1, 0),
      pose: (h) => ({ walk: walkCycles(speed * h), headYaw: -0.5 * seg(h - T0, 2.6, 3.4) + 0.9 * seg(h - T0, 5.4, 6.2), headPitch: -0.35 * seg(h - T0, 5.4, 6.4), mouth: (h - T0) > 2.8 ? 'o' : 'grin' }) });
    // orbit from front (along -z) to end-on (along -x, looking back up the line) over 1.0..4.2 s
    const u = seg(t, 1.0, 4.2, ease.inOut); const ang = lerp(0, Math.PI / 2, u);
    const c = v3(bx + 1.6, 1.3, 0.2); const R = lerp(9.5, 11, u);
    const pos = c.clone().add(v3(Math.sin(ang) * R, 0.2 + 0.6 * u, Math.cos(ang) * R));
    E.aim(s.camera, pos, c.clone().add(v3(0, 0.15 + 0.6 * seg(t, 5.4, 7.5), 0)));
    return { bg: '#e4e1db' };
  },
};
