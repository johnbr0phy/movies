// S05 (7 s) Over Barney's shoulder as he kneels at the little red door and opens it. Beyond it a plaza lies on its
// side: its chequered ground is a wall on the left, its arcades hang sideways, its horizon is vertical.
import { world1 } from '../sets/world1.js';
import { fountain } from '../sets/plaza.js';
import { makeActor, drive } from '../actor.js';
export default {
  dur: 7,
  async setup(E) {
    const { THREE } = E;
    const scene = new THREE.Scene(); const W = world1(); scene.add(W);
    const a = makeActor(scene, { fill: 0.6 });
    const camera = E.persp(38);
    E.G.uLight.value.set(0.5, 0.75, 0.45).normalize();
    return { scene, camera, a, W };
  },
  frame(t, s, E, dt) {
    const { v3, seg, ease } = E;
    const gal = s.W.userData.gal; const z = -6.35; const fl = gal.userData.at((0.6 - z) / 7.6).fl;
    const open = seg(t, 1.6, 3.4, ease.inOut);
    gal.userData.door.userData.leaf.rotation.y = -1.9 * open;
    drive(s.a, t, dt, { pos: v3(-0.13, fl, z), up: v3(0, 1, 0), fwd: v3(0, 0, -1), trueUp: v3(0, 1, 0),
      pose: (th) => ({ kneel: true, bag: 'hold', armL: [1.25 - 0.4 * open, 0.25 * open, 0.35], headPitch: -0.05 - 0.1 * seg(th, 3.5, 4.5), headRoll: 0.25 * seg(th, 4.2, 5.2, ease.inOut), mouth: th > 3.6 ? 'o' : 'flat' }) });
    fountain(s.W.userData.pz, t, v3(1, 0, 0));
    const push = seg(t, 0, 7, ease.sine);
    E.aim(s.camera, v3(0.36, 1.2, -4.8 - 0.45 * push), v3(-0.02, 0.74, -7.6));
    s.camera.fov = 36; s.camera.updateProjectionMatrix();
    return { bg: '#dfe9e6' };
  },
};
