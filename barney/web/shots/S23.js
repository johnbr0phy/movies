// S23 (8 s) The two-shot, split by the surface: above the line the blue sea and the goldfish (upside down to us),
// below it the grey air and Barney (upside down to it), his palm flat against the water. The fish comes down and
// touches its nose to his hand. A ring spreads. It turns and swims away up into the blue. He holds the empty bag.
import { shore, openBottom, SURF, shoal, swimShoal, setBulge } from '../sets/sea.js';
import { makeActor, drive } from '../actor.js';
import { makeFish } from '../rig/fish.js';
export default {
  dur: 8,
  async setup(E) {
    const { THREE } = E;
    const scene = new THREE.Scene(); const W = shore(); scene.add(W); openBottom(W.userData.vol);
    const a = makeActor(scene, { fill: 0 });
    const F = makeFish(); scene.add(F.g);
    const S = shoal(scene, 600, { spread: 6, thick: 3 });
    const camera = E.persp(32);
    E.G.uLight.value.set(0.3, -0.5, 0.8).normalize(); E.G.uShadowTint.value.set('#aab4d8');
    W.userData.bulge.material.uniforms.uAlpha.value = 0.18; W.userData.bulge.material.uniforms.uBackAlpha.value = 0.12;
    return { scene, camera, a, W, F, S };
  },
  frame(t, s, E, dt) {
    const { THREE, v3, seg, ease } = E;
    const low = seg(t, 5.8, 6.8, ease.inOut);
    drive(s.a, t, dt, { pos: v3(0, 0.05, 0), up: v3(0, 1, 0), fwd: v3(0, 0, 1), trueUp: v3(0, -1, 0), fill: 0, fish: false,
      pose: (th) => ({ armL: [-2.75 + 1.9 * low, 0.05, 0.1 + 0.6 * low], bag: low > 0.5 ? 'hold' : 'high', headPitch: -0.6 * (1 - low) + 0.1, mouth: th > 3.4 && th < 5.6 ? 'grin' : 'smile', blink: th > 3.1 && th < 3.3 ? 1 : 0 }) });
    const palm = s.a.B.arms.L.hand.getWorldPosition(v3(0, 0, 0));
    const pr = 1 - low; setBulge(s.W, palm.x, palm.z, SURF - (SURF - palm.y - 0.035) * (low > 0 ? Math.max(0.05, pr) : 1));
    // fish: descends nose-first to the palm (touch at 3.0 s), holds, then turns and swims up and away
    const down = seg(t, 0.5, 3.0, ease.inOut), away = seg(t, 4.2, 7.5, ease.in);
    const touch = v3(palm.x, palm.y + 0.1, palm.z);
    let fp = v3(palm.x + 0.35, SURF + 0.7, palm.z - 0.1).lerp(touch, down);
    fp = fp.lerp(v3(palm.x - 1.4, SURF + 2.6, palm.z - 1.0), away);
    const fwd = v3(-0.25, -1, 0.05).normalize().lerp(v3(-0.6, 0.8, -0.3).normalize(), seg(t, 4.0, 4.8, ease.inOut)).normalize();
    const up = v3(0, 0, 1); const z = new THREE.Vector3().crossVectors(fwd, up).normalize(); const u2 = new THREE.Vector3().crossVectors(z, fwd);
    s.F.g.position.copy(fp.clone().add(fwd.clone().multiplyScalar(-0.035))); s.F.g.quaternion.setFromRotationMatrix(new THREE.Matrix4().makeBasis(fwd, u2, z)); s.F.set(t, t > 3 && t < 4.2 ? 0.3 : 1);
    s.F.g.scale.setScalar(1.6);
    swimShoal(s.S, t + 9, v3(-1, SURF + 3.5, -3), 1, {});
    s.W.userData.rings.forEach((r, i) => { const rt = t - (3.0 + i * 0.35); r.visible = rt > 0 && rt < 3; r.scale.setScalar(Math.max(0.01, 0.03 + rt * 0.35)); r.position.set(palm.x, SURF - 0.002, palm.z); });
    // camera level with the surface, square on to the two of them
    E.aim(s.camera, v3(0.24, 1.12, 1.25), v3(0.06, 1.13, 0));
    return { bg: '#c3c0ba' };
  },
};
