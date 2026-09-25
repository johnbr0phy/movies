// S18 (9 s) Extreme wide, locked. A grey pleated plain under a grey sky. A tiny grey boy crosses it; the only colour in
// the world is the orange fish in his bag. Behind him, a line of dark spots where the drips have fallen.
import { plain, setSpots, greyWorld } from '../sets/plain.js';
import { makeActor, drive, walkCycles } from '../actor.js';
export default {
  dur: 9,
  async setup(E) {
    const { THREE } = E;
    const scene = new THREE.Scene(); const P = plain(); scene.add(P);
    const a = makeActor(scene, { fill: 0.45 });
    greyWorld(scene, a.bag.fish.g);
    const camera = E.persp(30);
    E.G.uLight.value.set(0.2, 0.9, 0.35).normalize(); E.G.uShadowTint.value.set('#c2c2c6'); E.G.uShadowMix.value = 0.6;
    E.POST.uSat.value = 1.0; E.POST.uVignette.value = 0.35;
    return { scene, camera, a, P };
  },
  frame(t, s, E, dt) {
    const { v3, held } = E;
    const speed = 0.6; const x = -5 + speed * t;
    drive(s.a, t, dt, { pos: v3(x, 0, 0), up: v3(0, 1, 0), fwd: v3(1, 0, 0), trueUp: v3(0, 1, 0), fill: 0.45 - 0.02 * t / 9,
      pose: (th) => ({ walk: walkCycles(speed * th), stride: 0.8, headPitch: 0.25, mouth: 'flat' }) });
    // spots every 0.55 s along the path behind him (one fresh drip lands under the bag each time)
    const pts = []; for (let k = 0; -5 + speed * k * 0.55 < x - 0.15; k++) pts.push(v3(-5 + speed * k * 0.55 - 0.05, 0, -0.12 + 0.03 * Math.sin(k * 7)));
    // drips that happened before the shot began
    for (let k = 1; k < 30; k++) pts.push(v3(-5 - k * speed * 0.55, 0, -0.12 + 0.03 * Math.sin(k * 3)));
    setSpots(s.P, pts);
    E.aim(s.camera, v3(-1.2, 1.1, 13), v3(-1.2, 1.4, 0));
    return { bg: '#c9c8c4' };
  },
};
