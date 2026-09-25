// S14 (7 s) He slides UP. Slow at first, then faster and faster up the pleated lemon tube, bag held high, delighted.
// The camera rides behind him, then lets him go: he shoots out of the top of the slide into the sky and away.
import { playground, slideFrame } from '../sets/playground.js';
import { makeActor, drive } from '../actor.js';
export default {
  dur: 7,
  async setup(E) {
    const { THREE } = E;
    const scene = new THREE.Scene(); const P = playground(); scene.add(P);
    const a = makeActor(scene, { fill: 0.6 });
    const camera = E.persp(46);
    E.G.uLight.value.set(0.45, 0.8, 0.5).normalize(); E.G.uShadowTint.value.set('#b7bed8');
    return { scene, camera, a, P };
  },
  frame(t, s, E, dt) {
    const { v3, seg, ease, lerp } = E;
    const cv = s.P.userData.curve;
    // accelerating: u(t) from 0.006 to 1 by 5.2 s, then free flight
    const k = seg(t, 0.3, 5.2); const u = 0.006 + 0.994 * (k * k * (1.4 - 0.4 * k));
    let pos, up, fwd;
    if (t <= 5.2) { const f = slideFrame(cv, Math.min(1, u)); pos = f.p.clone().add(f.N.clone().multiplyScalar(0.53)); up = f.N.clone().negate(); fwd = f.T.clone(); }
    else { const f = slideFrame(cv, 1); const tt = t - 5.2; const v = f.T.clone().multiplyScalar(14);
      pos = f.p.clone().add(f.N.clone().multiplyScalar(0.53)).add(v.multiplyScalar(tt)); up = f.N.clone().negate().applyAxisAngle(v3(1, 0, 0), tt * 2.4); fwd = f.T.clone().applyAxisAngle(v3(1, 0, 0), tt * 2.4); }
    drive(s.a, t, dt, { pos, up, fwd, trueUp: v3(0, 1, 0), pose: (th) => (th < 0.4 ? { sit: true, bag: 'lap', mouth: 'o' } : { slide: true, bag: 'high', mouth: 'grin', headPitch: -0.2 }) });
    // camera: chase from below/behind along the slide, then hold as he flies off and tilt up to the sky
    const uc = Math.max(0.0, Math.min(0.93, u - 0.07));
    const fc = slideFrame(cv, uc);
    const camChase = fc.p.clone().add(fc.N.clone().multiplyScalar(-0.6)).add(fc.X.clone().multiplyScalar(1.6)).add(fc.T.clone().multiplyScalar(-1.2));
    const hold = seg(t, 4.6, 5.6, ease.inOut);
    const camEnd = v3(3.5, 17, -4.5);
    const cp = camChase.lerp(camEnd, hold);
    const ct = pos.clone().lerp(pos.clone().add(v3(0, 8, 0)), seg(t, 6.0, 7, ease.inOut));
    E.aim(s.camera, cp, ct, 0, v3(0, 1, 0));
    return { bg: '#d9ecf2' };
  },
};
