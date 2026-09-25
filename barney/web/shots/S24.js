// S24 (12 s) One continuous move. We start close on the goldfish swimming away up into the blue, turn with it, and pull
// back and back: the grey plain, the boy on it waving, the sea overhead... all of it sits inside a glass bowl on the
// floor of a real sea. The goldfish, as big as his whole world, swims round and settles in front of the glass.
import { realSea, swayKelp, BOWL_R, BOWL_C } from '../sets/bowl.js';
import { makeActor, drive } from '../actor.js';
import { makeFish } from '../rig/fish.js';
import { shoal, swimShoal } from '../sets/sea.js';
export default {
  dur: 12,
  async setup(E) {
    const { THREE } = E;
    const scene = new THREE.Scene(); const R = realSea(); scene.add(R);
    const a = makeActor(scene, { noBag: false, fill: 0 });
    const F = makeFish(); scene.add(F.g); F.g.scale.setScalar(22);
    const S = shoal(scene, 90, { spread: 26, thick: 5, scale: 9 });
    const camera = E.persp(40); camera.near = 0.01; camera.updateProjectionMatrix();
    E.G.uLight.value.set(0.25, 0.85, 0.45).normalize(); E.G.uShadowTint.value.set('#a7b4e6');
    E.POST.uHazeDist.value = 28; E.POST.uHaze.value.set('#1f45b0'); E.POST.uHazeMax.value = 0.92;
    return { scene, camera, a, F, R, S };
  },
  frame(t, s, E, dt) {
    const { THREE, v3, seg, ease, lerp } = E;
    swayKelp(s.R, t);
    // Barney: tiny (scale 0.2), standing on the disc inside the bowl, waving up with the empty bag
    const bp = v3(0.3, BOWL_C.y - 1.1, 0.2);
    drive(s.a, t, dt, { pos: bp, up: v3(0, 1, 0), fwd: v3(0.2, 0, 1).normalize(), trueUp: v3(0, 1, 0), scale: 0.2, fill: 0, fish: false,
      pose: (th) => ({ armL: [-2.5 + 0.35 * Math.sin(th * 7), 0.3, 0.3], bag: 'hold', headPitch: -0.5, mouth: 'grin' }) });
    // the fish: circles out and round, then settles facing the bowl at 10 s
    const a = lerp(-0.6, 2.2, seg(t, 0, 10, ease.inOut));
    const R = lerp(1.2, 5.2, seg(t, 0, 7, ease.out));
    const fp = v3(Math.sin(a) * R, lerp(BOWL_C.y + 2.2, BOWL_C.y + 0.4, seg(t, 4, 10, ease.inOut)), Math.cos(a) * R);
    const tangent = v3(Math.cos(a), 0, -Math.sin(a)); const toBowl = BOWL_C.clone().sub(fp).setY(0).normalize();
    const fwd = tangent.lerp(toBowl, seg(t, 8.5, 10.5, ease.inOut)).normalize();
    const up = v3(0, 1, 0); const z = new THREE.Vector3().crossVectors(fwd, up).normalize();
    s.F.g.position.copy(fp); s.F.g.quaternion.setFromRotationMatrix(new THREE.Matrix4().makeBasis(fwd, up, z)); s.F.set(t, t > 10.3 ? 0.35 : 0.8);
    swimShoal(s.S, t, v3(0, 10, -22), 1, { dir: -1 });
    // camera: from right beside tiny Barney (inside the bowl) pull back through the glass, rising, to a wide of the sea floor
    const u = seg(t, 0.5, 11, ease.inOut);
    const near = bp.clone().add(v3(0.25, 0.18, 0.55)), far = v3(3.5, 4.2, 14);
    const cp = near.clone().lerp(far, Math.pow(u, 1.6));
    const ct = bp.clone().add(v3(0, 0.12, 0)).lerp(v3(1.5, 3.0, 0), Math.pow(u, 0.9));
    E.aim(s.camera, cp, ct);
    E.POST.uLine.value = 5.5;
    return { bg: '#1f45b0' };
  },
};
