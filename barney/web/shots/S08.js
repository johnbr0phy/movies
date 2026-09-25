// S08 (7 s) Close on Barney walking up the pier, the camera taking HIS side: he looks upright, the plaza floor is a
// wall behind him, the fountain sprays straight "down" past him. He lifts the bag and grins at the fish. The water sits
// sideways in the bag, level with the true world.
import { plaza, fountain } from '../sets/plaza.js';
import { makeActor, drive, walkCycles } from '../actor.js';
export default {
  dur: 7,
  async setup(E) {
    const { THREE } = E;
    const scene = new THREE.Scene(); const P = plaza({ open: 'near' }); scene.add(P);
    const a = makeActor(scene, { fill: 0.6 });
    const camera = E.persp(34);
    E.G.uLight.value.set(0.4, 0.8, 0.45).normalize();
    return { scene, camera, a, P };
  },
  frame(t, s, E, dt) {
    const { v3, seg, ease } = E;
    const speed = 0.55; const y = 2.2 + speed * t; const wallZ = -12.98;
    const lift = seg(t, 2.2, 3.2, ease.inOut) * (1 - seg(t, 6.0, 6.8, ease.inOut));
    drive(s.a, t, dt, { pos: v3(0, y, wallZ), up: v3(0, 0, 1), fwd: v3(0, 1, 0), trueUp: v3(-1, 0, 0),
      pose: (th) => ({ walk: walkCycles(speed * th), stride: 0.8, bag: lift > 0.5 ? 'up' : undefined, headPitch: -0.25 * lift, headYaw: 0.35 * lift, mouth: lift > 0.5 ? 'grin' : 'smile', blink: (th % 2.4) > 2.3 ? 1 : 0 }) });
    fountain(s.P, t, v3(1, 0, 0));
    // camera in Barney's frame: his up is +z, he walks towards +y; we are in front of him and to his left, a little above
    const b = v3(0, y + 0.35, wallZ);
    E.aim(s.camera, b.clone().add(v3(0.55, 1.35, 0.95)), b.clone().add(v3(0.0, 0.1, 0.6)), 0, v3(0, 0, 1));
    return { bg: '#dfe9e6' };
  },
};
