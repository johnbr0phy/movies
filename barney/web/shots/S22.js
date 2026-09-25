// S22 (9 s) Inside the sea, the right way up for a fish: the surface is overhead and Barney hangs upside down beyond it,
// his hand raised to the water. The goldfish turns and looks back at him. Then the blue fills with goldfish, hundreds,
// then thousands, blooming out of the dark and wheeling around the little one.
import { shore, openBottom, shoal, swimShoal, setBulge, SURF } from '../sets/sea.js';
import { makeActor, drive } from '../actor.js';
import { makeFish } from '../rig/fish.js';
export default {
  dur: 9,
  async setup(E) {
    const { THREE } = E;
    const scene = new THREE.Scene(); const W = shore(); scene.add(W); openBottom(W.userData.vol);
    const a = makeActor(scene, { fill: 0 });
    const F = makeFish(); scene.add(F.g);
    const S = shoal(scene, 1400, { spread: 9, thick: 6 });
    const camera = E.persp(44);
    E.G.uLight.value.set(0.3, -0.7, 0.6).normalize(); E.G.uShadowTint.value.set('#b9a9c9');
    E.POST.uHazeDist.value = 16; E.POST.uHaze.value.set('#1f45b0'); E.POST.uHazeMax.value = 0.9;
    return { scene, camera, a, F, S, W };
  },
  frame(t, s, E, dt) {
    const { THREE, v3, seg, ease } = E;
    drive(s.a, t, dt, { pos: v3(0, 0.05, 0), up: v3(0, 1, 0), fwd: v3(1, 0, 0.15).normalize(), trueUp: v3(0, -1, 0), fill: 0, fish: false,
      pose: () => ({ armL: [-2.6, 0.2, 0.2], bag: 'high', headPitch: -0.75, mouth: 'grin' }) });
    { const g = s.a.B.arms.R.grip.getWorldPosition(v3(0, 0, 0)); setBulge(s.W, g.x, g.z, g.y + 0.02); }
    // the goldfish: hovers 0.5 m above the surface, turns from rising to face down at Barney, then circles
    const turn = seg(t, 0.4, 2.2, ease.inOut);
    const fp = v3(0.55 + 0.4 * Math.sin(t * 0.5), SURF + 0.55 + 0.1 * Math.sin(t * 1.3), 0.2);
    const fwd = v3(0.4, 1, 0.1).normalize().lerp(v3(-0.3, -1, 0.05).normalize(), turn).normalize();
    const up = v3(-1, 0.2, 0).normalize(); const z = new THREE.Vector3().crossVectors(fwd, up).normalize(); const u2 = new THREE.Vector3().crossVectors(z, fwd);
    s.F.g.position.copy(fp); s.F.g.quaternion.setFromRotationMatrix(new THREE.Matrix4().makeBasis(fwd, u2, z)); s.F.set(t, 1);
    // the shoal blooms from 3.2 s
    swimShoal(s.S, t, v3(0.5, SURF + 4.2, 0), seg(t, 3.0, 7.5), { dir: 1 });
    // camera inside the sea, a little above the fish, looking down through the surface at Barney; sea-up is world -y
    const u = seg(t, 3.0, 9, ease.inOut);
    const cp = v3(1.9, SURF + 1.6, 1.4).lerp(v3(3.2, SURF + 3.2, 3.6), u);
    const ct = fp.clone().lerp(v3(0.4, SURF + 1.8, 0), u);
    E.aim(s.camera, cp, ct, 0, v3(0, -1, 0));
    return { bg: '#1f45b0' };
  },
};
