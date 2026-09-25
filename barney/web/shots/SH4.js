// Expression close-ups: one Barney head per frame, t = 0..5 selects the expression.
import { makeActor, drive } from '../actor.js';
const F = [['smile', {}], ['grin', {}], ['o', {}], ['flat', {}], ['sad', { headPitch: 0.25 }], ['smile', { blink: 1 }]];
export default {
  dur: 6,
  async setup(E) { await E.loadFonts(); const scene = new E.THREE.Scene(); const a = makeActor(scene, { fill: 0.6 }); const camera = E.persp(22); E.G.uLight.value.set(-0.4, 0.8, 0.6).normalize(); E.POST.uLine.value = 4.5; return { scene, camera, a }; },
  frame(t, s, E) {
    const { v3 } = E; const [mouth, extra] = F[Math.min(5, Math.floor(t))];
    drive(s.a, 0.5, 0, { pos: v3(0, 0, 0), up: v3(0, 1, 0), fwd: v3(0.25, 0, 1).normalize(), bagHidden: true, pose: Object.assign({ mouth }, extra) });
    E.aim(s.camera, v3(0, 0.95, 2.2), v3(0, 0.9, 0));
    return { bg: '#efe8dc', overlay: (c) => { c.font = '400 44px Jost'; c.fillStyle = '#3a3844'; c.fillText(['smile', 'grin', 'o', 'flat', 'sad', 'blink'][Math.min(5, Math.floor(t))], 60, 1020); } };
  },
};
