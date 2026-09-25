// S21 (8 s) In Barney's frame, the colour back. The sea hangs overhead like a ceiling, its surface just out of reach.
// He stands on tiptoe, lifts the bag to the surface and unties it. The water pours UP out of the bag into the sea,
// and the goldfish goes with it.
import { shore, openBottom, setBulge, SURF } from '../sets/sea.js';
import { makeActor, drive, walkCycles } from '../actor.js';
import { makeFish } from '../rig/fish.js';
import { makeDrops, updateDrops } from '../drops.js';
export default {
  dur: 8,
  async setup(E) {
    const { THREE } = E;
    const scene = new THREE.Scene(); const W = shore(); scene.add(W); openBottom(W.userData.vol);
    const a = makeActor(scene, { fill: 0.34 });
    const F = makeFish(); scene.add(F.g); F.g.visible = false;
    const D = makeDrops(scene, 60, '#8fd7ff');
    const camera = E.persp(46);
    E.G.uLight.value.set(0.3, -0.6, 0.7).normalize(); E.G.uShadowTint.value.set('#aab4d8');
    E.POST.uHazeDist.value = 0;
    return { scene, camera, a, W, F, D };
  },
  frame(t, s, E, dt) {
    const { THREE, v3, seg, ease, lerp } = E;
    const speed = 0.6; const x = -1.2 + speed * Math.min(t, 2.0);
    const lift = seg(t, 2.4, 3.6, ease.inOut); const untie = 4.4; const pour = seg(t, untie, untie + 1.6);
    const fill = 0.34 * (1 - pour);
    const tip = lift > 0.5;
    const info = drive(s.a, t, dt, { pos: v3(x, 0.05 * lift, 0), up: v3(0, 1, 0), fwd: v3(1, 0, 0.15).normalize(), trueUp: v3(0, -1, 0), fill,
      fish: t < untie + 0.5, fishAt: t > untie ? null : undefined,
      pose: (th) => (th < 2.0 ? { walk: walkCycles(speed * th), headPitch: -0.3, mouth: 'o' } :
        { bag: tip ? 'high' : undefined, armL: th > 3.8 ? [-2.6, 0.2, 0.2] : undefined, headPitch: -0.75 * seg(th, 2.0, 2.6), mouth: th > untie + 0.8 ? 'grin' : 'o', lean: -0.05 }) });
    // the sea reaches down to meet the bag
    const grip = s.a.B.arms.R.grip.getWorldPosition(v3(0, 0, 0));
    const reach = seg(t, 2.8, 4.2, ease.inOut);
    setBulge(s.W, grip.x, grip.z, SURF - (SURF - grip.y - 0.02) * reach, reach > 0);
    // the tie comes undone
    s.a.bag.g.children.forEach(c => { if (c.geometry && (c.geometry.type === 'ConeGeometry' || c.geometry.type === 'TorusGeometry')) c.visible = t < untie; });
    // the fish leaves the neck and rises through the surface
    const neck = s.a.bag.g.localToWorld(v3(0, 0.02, 0));
    const k = seg(t, untie + 0.5, untie + 2.2, ease.inOut);
    s.F.g.visible = t >= untie + 0.5;
    if (s.F.g.visible) { const p = neck.clone().lerp(v3(neck.x + 0.15, SURF + 0.7, neck.z + 0.1), k); const fwd = v3(0.15, 1, 0.05).normalize();
      s.F.g.position.copy(p); s.F.g.quaternion.setFromRotationMatrix(new THREE.Matrix4().makeBasis(fwd, v3(-1, 0.3, 0).normalize(), new THREE.Vector3().crossVectors(fwd, v3(-1, 0.3, 0).normalize()).normalize())); s.F.set(t, 1.5); }
    // water pours upward from the neck
    if (!s.D.list.length) for (let i = 0; i < 50; i++) s.D.list.push({ t0: untie + 0.05 + i * 0.03, v0: v3((i % 5 - 2) * 0.08, 0.4, ((i * 7) % 5 - 2) * 0.06), size: 1.5, life: 1.2 });
    for (const d of s.D.list) if (!d.p0 || t < d.t0) d.p0 = neck.clone();
    updateDrops(s.D, t, v3(0, 9.8, 0));
    // ripple rings where the water and the fish meet the surface
    s.W.userData.rings.forEach((r, i) => { const rt = t - (untie + 0.3 + i * 0.5); r.visible = rt > 0 && rt < 2.5; const rr = 0.05 + rt * 0.45; r.scale.setScalar(Math.max(0.01, rr)); r.position.x = neck.x; r.position.z = neck.z; });
    // camera: low, looking up past him at the water ceiling
    E.aim(s.camera, v3(0.35, 0.45, 2.6), v3(0.3, 1.2, 0));
    return { bg: '#c3c0ba' };
  },
};
