// World 1: the gallery and, beyond its little red door, the plaza turned on its side (its up is world +x).
import { THREE } from '../engine.js';
import { galleria } from './corridor.js';
import { plaza } from './plaza.js';
export const PLAZA_X = -0.23; // world x of the plaza floor (the left jamb of the door)
export function world1(o = {}) {
  const g = new THREE.Group();
  const gal = galleria(); g.add(gal);
  const pz = plaza({ open: 'near' });
  const holder = new THREE.Group(); holder.add(pz);
  // plaza local -> world: local up (+y) becomes world +x, local x becomes world -y; near edge (local z = +13) at the gallery's far wall
  holder.rotation.z = -Math.PI / 2; holder.position.set(PLAZA_X, 0.74, -7.1 - 13);
  g.add(holder);
  g.userData = { gal, pz, holder };
  return g;
}
// plaza local vector/point -> world
export function pzToWorld(W, v, isPoint = true) { W.userData.holder.updateMatrixWorld(true); return isPoint ? v.clone().applyMatrix4(W.userData.holder.matrixWorld) : v.clone().transformDirection(W.userData.holder.matrixWorld); }
