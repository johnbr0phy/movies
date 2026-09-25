// S07 (9 s) The plaza, in its own frame. Barney walks at the far facade and straight up the pier between two arches
// without breaking stride. Through an arch on the left, a tangerine Pleat strolls upside down under the arcade.
// The fountain arcs sideways: the true down is plaza +x.
import { plaza, fountain } from '../sets/plaza.js';
import { pleat } from '../kit.js';
import { makeActor, drive, walkCycles } from '../actor.js';
export default {
  dur: 9,
  async setup(E) {
    const { THREE, PAL } = E;
    const scene = new THREE.Scene(); const P = plaza({ open: 'near' }); scene.add(P);
    const a = makeActor(scene, { fill: 0.6 });
    const pl = pleat(PAL.tangerine, { fold: '#d9c3b5' }); scene.add(pl);
    const camera = E.persp(42);
    E.G.uLight.value.set(0.4, 0.8, 0.45).normalize();
    return { scene, camera, a, P, pl };
  },
  frame(t, s, E, dt) {
    const { v3, seg, ease, lerp } = E;
    const speed = 0.7; const d = speed * t; // distance walked
    const z0 = -9.2, wallZ = -12.98, reach = z0 - wallZ; // flat run to the wall, then up it
    let pos, up, fwd;
    if (d < reach - 0.15) { pos = v3(0, 0, z0 - d); up = v3(0, 1, 0); fwd = v3(0, 0, -1); }
    else if (d < reach + 0.25) { const k = ease.inOut((d - (reach - 0.15)) / 0.4); up = v3(0, 1, 0).lerp(v3(0, 0, 1), k).normalize(); fwd = v3(0, 0, -1).lerp(v3(0, 1, 0), k).normalize(); pos = v3(0, 0.02 + 0.2 * k, lerp(wallZ + 0.15, wallZ, k)); }
    else { pos = v3(0, 0.22 + (d - reach - 0.25), wallZ); up = v3(0, 0, 1); fwd = v3(0, 1, 0); }
    drive(s.a, t, dt, { pos, up, fwd, trueUp: v3(-1, 0, 0), pose: (th) => ({ walk: walkCycles(speed * th), mouth: 'smile' }) });
    fountain(s.P, t, v3(1, 0, 0));
    // the upside-down Pleat under the left arcade (x = -13 side): walks along z, head down, hanging from the arcade ceiling
    s.pl.position.set(lerp(-6.8, -3.4, t / 9), 2.6, -14.3); s.pl.rotation.set(Math.PI, 0, 0);
    s.pl.position.y += 0.03 * Math.abs(Math.sin(t * Math.PI * 2));
    E.aim(s.camera, v3(4.4, 1.1, -7.6), v3(-0.9, 1.9, -13));
    return { bg: '#dfe9e6' };
  },
};
