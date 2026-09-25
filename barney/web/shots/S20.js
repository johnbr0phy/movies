// S20 (8 s) The turn. Drops rise from the bag one after another; Barney gets up and follows them. As he walks the
// camera rolls right over, 180 degrees, and the grey sky deepens to blue: it was never the sky. It is the sea, and it is
// below us now; Barney walks upside down across the top of the frame on the underside of his grey world.
import { plain, setSpots, greyWorld } from '../sets/plain.js';
import { makeActor, drive, walkCycles } from '../actor.js';
import { makeDrops, updateDrops } from '../drops.js';
export default {
  dur: 8,
  async setup(E) {
    const { THREE } = E;
    const scene = new THREE.Scene(); const P = plain({ skyY: 6 }); scene.add(P);
    const a = makeActor(scene, { fill: 0.34 });
    greyWorld(scene, a.bag.fish.g);
    const D = makeDrops(scene, 30, '#d0d0ce');
    const camera = E.persp(40);
    E.G.uLight.value.set(0.2, 0.9, 0.35).normalize(); E.G.uShadowTint.value.set('#c2c2c6'); E.G.uShadowMix.value = 0.6;
    return { scene, camera, a, P, D, THREE };
  },
  frame(t, s, E, dt) {
    const { THREE, v3, seg, ease, lerp } = E;
    const speed = 0.6; const x = speed * Math.max(0, t - 0.8);
    const u = seg(t, 2.5, 7.0, ease.inOut);
    // the true up swings from +y to -y as the world turns over: the water in the bag slides to the sky side
    const trueUp = v3(0, 1, 0).applyAxisAngle(v3(0, 0, 1), Math.PI * u);
    drive(s.a, t, dt, { pos: v3(x, 0, 0), up: v3(0, 1, 0), fwd: v3(1, 0, 0), trueUp, fill: 0.34,
      pose: (th) => (th < 0.8 ? { sit: false, kneel: true, bag: 'hold', headPitch: -0.6 } : { walk: walkCycles(speed * (th - 0.8)), headPitch: -0.55 + 0.3 * seg(th, 4, 7), mouth: th > 5 ? 'smile' : 'o' }) });
    // drops rise from the hole every 0.45 s towards the sky/sea
    if (!s.D.list.length) for (let i = 0; i < 20; i++) s.D.list.push({ t0: -1.5 + i * 0.45, v0: v3(0.2, 0.1, 0), size: 1.3, life: 5 });
    const hole = s.a.bag.g.localToWorld(v3(0.06, -0.19, 0.03));
    for (const d of s.D.list) if (!d.p0 || t < d.t0) d.p0 = hole.clone().add(v3(0.6 * Math.min(0, d.t0 - t), 0, 0));
    updateDrops(s.D, t, v3(0, 1.1, 0));
    // the sky becomes the sea: grey -> ultramarine, pleats become waves that move
    const k = seg(t, 2.8, 7.5, ease.inOut);
    s.P.userData.skyM.uniforms.uBase.value.copy(new THREE.Color('#c9c8c4').lerp(new THREE.Color('#1f45b0'), k));
    s.P.userData.skyM.uniforms.uColor2.value.copy(new THREE.Color('#aeb4c0').lerp(new THREE.Color('#9fc4ff'), k));
    s.P.userData.skyM.uniforms.uPhase.value = t * 0.35;
    // camera: behind and beside him, rolling over the top: world up -> world down
    const b = v3(x, 0.6, 0);
    E.aim(s.camera, b.clone().add(v3(-2.6, 0.7 + 1.6 * Math.sin(Math.PI * u), 1.6)), b.clone().add(v3(1.2, 1.8 * Math.sin(Math.PI * u) + 0.2, 0)), 0,
      v3(0, 1, 0).applyAxisAngle(v3(1, 0, 0), Math.PI * u));
    return { bg: new THREE.Color('#c9c8c4').lerp(new THREE.Color('#1f45b0'), k).getStyle() };
  },
};
