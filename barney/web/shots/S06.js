// S06 (8 s) Through. Barney stands, ducks through the little door and steps out onto the plaza, which is on its side:
// his up swings from world +y to world +x as he steps onto it. The camera follows him through the doorway and rolls
// 90 degrees to agree with him. The water in the bag does not agree: it stays level with the gallery's world.
import { world1, pzToWorld, PLAZA_X } from '../sets/world1.js';
import { fountain } from '../sets/plaza.js';
import { makeActor, drive, walkCycles } from '../actor.js';
export default {
  dur: 8,
  async setup(E) {
    const { THREE } = E;
    const scene = new THREE.Scene(); const W = world1(); scene.add(W);
    W.userData.gal.userData.door.userData.leaf.rotation.y = -1.9;
    const a = makeActor(scene, { fill: 0.6 });
    const camera = E.persp(40);
    E.G.uLight.value.set(0.55, 0.7, 0.45).normalize();
    return { scene, camera, a, W };
  },
  frame(t, s, E, dt) {
    const { THREE, v3, seg, ease, lerp, kf } = E;
    const gal = s.W.userData.gal; const flAt = (z) => gal.userData.at((0.6 - z) / 7.6).fl;
    // Barney
    let pos, up, fwd = v3(0, 0, -1), pose;
    const rise = seg(t, 0, 0.9, ease.inOut);
    if (t < 2.7) {
      const z = lerp(-6.35, -7.15, seg(t, 1.0, 2.7, (x) => x));
      pos = v3(-0.02, flAt(Math.max(z, -7)), z); up = v3(0, 1, 0);
      pose = (th) => (rise < 0.6 ? { kneel: true, bag: 'hold' } : { walk: th > 1.0 ? walkCycles(0.5 * (th - 1.0)) : null, lean: 0.45 * seg(th, 1.0, 1.6), headPitch: 0.3 * seg(th, 1.0, 1.6), stride: 0.6 });
    } else if (t < 3.3) {
      const k = seg(t, 2.7, 3.3, ease.inOut);
      up = v3(0, 1, 0).lerp(v3(1, 0, 0), k).normalize();
      pos = v3(-0.02, 0.34, -7.15).lerp(v3(PLAZA_X, 0.62, -7.45), k);
      pose = (th) => ({ walk: walkCycles(0.5 * (th - 1.0)), lean: 0.45 * (1 - k), stride: 0.6 });
    } else {
      const d = 0.7 * (t - 3.3);
      pos = v3(PLAZA_X, 0.62, -7.45 - d); up = v3(1, 0, 0);
      pose = (th) => ({ walk: walkCycles(0.5 * 1.7 + 0.7 * Math.max(0, th - 3.3)), headYaw: 0.5 * seg(th, 5.8, 6.6, ease.inOut), mouth: 'smile' });
    }
    drive(s.a, t, dt, { pos, up, fwd, trueUp: v3(0, 1, 0), pose });
    fountain(s.W.userData.pz, t, v3(1, 0, 0));
    // camera: behind him in the gallery -> through the doorway -> in the plaza frame, rolled 90 degrees
    const endLocal = { pos: v3(1.25, 1.35, 13 - 7.45 - 0.7 * (8 - 3.3) + 3.4 - 20.1 + 20.1), tgt: v3(0.2, 0.6, 13 - 7.45 - 0.7 * (8 - 3.3) - 2.2) };
    const zl = (z) => z + 20.1; // world z -> plaza local z
    const bz = pos.z;
    const pEnd = pzToWorld(s.W, v3(1.3, 1.4, zl(bz) + 3.2)), tEnd = pzToWorld(s.W, v3(0.74 - pos.y, 0.55, zl(bz) - 2.4));
    const u = seg(t, 1.6, 5.8, ease.inOut);
    const pStart = v3(0.3, 1.15, -5.1), tStart = v3(-0.02, 0.74, -7.6);
    const pDoor = v3(0.02, 0.8, -6.95);
    const cp = u < 0.5 ? pStart.clone().lerp(pDoor, ease.inOut(u * 2)) : pDoor.clone().lerp(pEnd, ease.inOut((u - 0.5) * 2));
    const ct = tStart.clone().lerp(tEnd, ease.inOut(u));
    const cup = v3(0, 1, 0).lerp(v3(1, 0, 0), seg(t, 2.8, 6.2, ease.inOut)).normalize();
    E.aim(s.camera, cp, ct, 0, cup);
    return { bg: '#dfe9e6' };
  },
};
