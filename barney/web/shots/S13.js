// S13 (6 s) Wide and symmetrical. The playground; the lemon slide rises out of the ground and curls into the sky.
// Barney walks in, looks up the length of it, and sits down at its bottom end, facing up the slope.
import { playground, slideFrame } from '../sets/playground.js';
import { makeActor, drive, walkCycles } from '../actor.js';
export default {
  dur: 6,
  async setup(E) {
    const { THREE } = E;
    const scene = new THREE.Scene(); const P = playground(); scene.add(P);
    const a = makeActor(scene, { fill: 0.6 });
    const camera = E.persp(40);
    E.G.uLight.value.set(0.45, 0.8, 0.5).normalize(); E.G.uShadowTint.value.set('#b7bed8');
    return { scene, camera, a, P };
  },
  frame(t, s, E, dt) {
    const { v3, seg, ease, lerp } = E;
    const f0 = slideFrame(s.P.userData.curve, 0.006); const seat = f0.p.clone().add(f0.N.clone().multiplyScalar(0.53));
    let pos, fwd, pose;
    if (t < 2.6) { const d = 0.68 * (2.6 - t); pos = seat.clone().add(v3(-d * 0.3, 0, d)).setY(0); fwd = v3(0.3, 0, -1).normalize(); pose = (th) => ({ walk: walkCycles(0.68 * th), headPitch: -0.3 * seg(th, 1.6, 2.4), mouth: 'o' }); }
    else if (t < 3.6) { pos = seat.clone().setY(0).lerp(seat, seg(t, 3.1, 3.6, ease.inOut)); fwd = v3(0, 0, -1); pose = (th) => ({ headPitch: -0.6 * (1 - seg(th, 2.9, 3.4)), mouth: 'o', sit: th > 3.3 }); }
    else { pos = seat; fwd = v3(0, 0, -1); pose = (th) => ({ sit: true, bag: 'lap', headPitch: -0.35, mouth: th > 4.6 ? 'grin' : 'smile', blink: th > 5.0 && th < 5.1 ? 1 : 0 }); }
    drive(s.a, t, dt, { pos, up: v3(0, 1, 0), fwd, trueUp: v3(0, 1, 0), pose });
    E.aim(s.camera, v3(8.6 - 0.8 * seg(t, 0, 6, ease.sine), 1.2, 7.2), v3(-0.4, 4.4, -2.6));
    s.camera.fov = 50; s.camera.updateProjectionMatrix();
    return { bg: '#d9ecf2' };
  },
};
