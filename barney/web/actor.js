// Barney with his bag, driven per frame: place him by (pos, up, fwd), pose him at 12 drawings a second,
// hang the bag by his gravity and settle the water by the true gravity.
import { THREE, held } from './engine.js';
import { makeBarney, place, gripWorld } from './rig/barney.js';
import { makeBag, hang, settle } from './rig/bag.js';

export function makeActor(scene, o = {}) {
  const B = makeBarney(); scene.add(B.root);
  const bag = o.noBag ? null : makeBag({ fill: o.fill }); if (bag) scene.add(bag.g);
  return { B, bag };
}

// a = actor; s = { pos, up, fwd, pose, trueUp, scale, bagDir (override hang direction), fill, fishAt, swim, bagHidden }
export function drive(a, t, dt, s) {
  const th = held(t);
  const pose = typeof s.pose === 'function' ? s.pose(th) : (s.pose || {});
  a.B.set(pose);
  place(a.B, s.pos, s.up, s.fwd, s.scale || 1);
  if (a.bag) {
    if (s.fill !== undefined) a.bag.fill = s.fill;
    a.bag.g.visible = !s.bagHidden;
    a.bag.g.scale.setScalar(s.scale || 1);
    hang(a.bag, s.anchor || gripWorld(a.B, s.hand || 'R'), s.up.clone().negate(), dt, s.bagDir || null);
    return settle(a.bag, s.trueUp || new THREE.Vector3(0, 1, 0), th, { fishAt: s.fishAt, swim: s.swim, roam: s.roam, fish: s.fish });
  }
  return null;
}

// walk helper: distance along a path at 2 steps a second (stride 0.34 m per step), cycles for the walk pose
export const STEP = 0.34;
export function walkCycles(dist) { return dist / (STEP * 2); }
