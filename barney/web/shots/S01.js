// S01 (6 s) The hook. We open in Barney's frame of reference: everything looks upright, except the water, which has
// pooled at the TOP of the bag around the knot, and a lamp that grows up out of the floor like a stalk. Then we pull back
// and roll 180 degrees into the true frame: he is walking along the ceiling.
import { mirrorCorridor } from '../sets/corridor.js';
import { makeActor, drive, walkCycles } from '../actor.js';
export default {
  dur: 6,
  async setup(E) {
    const { THREE } = E;
    const scene = new THREE.Scene();
    const set = mirrorCorridor({ lamps: [-0.6, -8] }); scene.add(set);
    const a = makeActor(scene, { fill: 0.3 });
    const camera = E.persp(34);
    E.G.uLight.value.set(0.3, -0.5, 0.8).normalize(); // light from the camera side, slightly from "below" the true ceiling
    return { scene, camera, a, set };
  },
  frame(t, s, E, dt) {
    const { v3, kf, seg, ease } = E;
    const speed = 0.68; const z = -3.2 + speed * t;
    const up = v3(0, -1, 0);
    const info = drive(s.a, t, dt, { pos: v3(0.32, 3.0, z), up, fwd: v3(0, 0, 1), trueUp: v3(0, 1, 0),
      pose: (th) => ({ walk: walkCycles(speed * th), mouth: 'smile', blink: (th % 3.1) > 2.95 ? 1 : 0, headPitch: 0.12 }), swim: 0.8 });
    // camera: ECU on the bag in Barney's frame, then pull back and roll into the true frame
    const bagC = s.a.bag.g.localToWorld(v3(0, -0.08, 0));
    const u = seg(t, 1.3, 5.4, ease.inOut);
    const close = bagC.clone().add(v3(0.02, 0.0, 0.3));
    const far = v3(0.1, 1.55, z + 3.3);
    const pos = close.clone().lerp(far, u);
    const tgt = bagC.clone().lerp(v3(0.2, 2.05, z - 0.2), u);
    // roll: start with Barney's up (world -y), end with the true up
    E.aim(s.camera, pos, tgt, Math.PI * u, v3(0, -1, 0));
    s.camera.fov = 34 + 12 * u; s.camera.updateProjectionMatrix();
    E.POST.uVignette.value = 0.3;
    return { bg: '#efe8dc' };
  },
};
