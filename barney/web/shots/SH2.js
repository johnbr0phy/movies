// Character sheet: the goldfish, the bag and its rule (the water always finds the true down), and the Pleats.
import { makeFish } from '../rig/fish.js';
import { makeBag, hang, settle } from '../rig/bag.js';
import { pleat } from '../kit.js';
import { crane, PLEAT_COLS } from '../sets/runway.js';
export default {
  dur: 1,
  async setup(E) {
    await E.loadFonts();
    const { THREE, v3 } = E; const scene = new THREE.Scene();
    // fish turnaround (scaled up 12x)
    const fish = []; for (let i = 0; i < 3; i++) { const f = makeFish(); f.g.scale.setScalar(12); scene.add(f.g); fish.push(f); }
    // bags: same bag, different true downs
    const bags = []; for (let i = 0; i < 4; i++) { const b = makeBag({ fill: 0.55 }); b.g.scale.setScalar(3.2); scene.add(b.g); bags.push(b); }
    // Pleats
    const P = []; for (let i = 0; i < 6; i++) { const p = pleat(PLEAT_COLS[i], { fold: '#c8c9d4', h: 1.6, w: 0.64, hat: i % 3 === 1 ? 0 : 1 }); scene.add(p); P.push(p); }
    const edge = pleat(PLEAT_COLS[2], { h: 1.6, w: 0.64 }); scene.add(edge);
    const C = crane(PLEAT_COLS[5]); C.scale.setScalar(0.5); scene.add(C);
    const camera = E.ortho(6.2);
    E.G.uLight.value.set(-0.4, 0.8, 0.6).normalize(); E.POST.uLine.value = 4.5;
    return { scene, camera, fish, bags, P, edge, C };
  },
  frame(t, s, E) {
    const { THREE, v3 } = E;
    const fq = (f, pos, yaw) => { f.g.position.copy(pos); f.g.rotation.set(0, yaw, 0); f.set(0.1, 0); };
    fq(s.fish[0], v3(-4.1, 1.7, 0), 0); fq(s.fish[1], v3(-2.6, 1.7, 0), Math.PI / 2); fq(s.fish[2], v3(-1.1, 1.7, 0), 0.9);
    const ups = [v3(0, 1, 0), v3(1, 0.4, 0).normalize(), v3(0, -1, 0), v3(-1, 0.2, 0).normalize()];
    s.bags.forEach((b, i) => { const anchor = v3(-4.3 + i * 1.2, 0.15, 0); hang(b, anchor, v3(0, -1, 0), 0); settle(b, ups[i], 0.3, { swim: 0 }); });
    s.P.forEach((p, i) => { p.position.set(0.9 + i * 0.72, -2.9, 0); p.rotation.set(0, 0, 0); });
    s.edge.position.set(0.9 + 6 * 0.72, -2.9, 0); s.edge.rotation.set(0, Math.PI / 2 - 0.02, 0);
    s.C.position.set(1.6, 1.6, 0); s.C.rotation.set(0.3, 0.6, 0.2);
    E.aim(s.camera, v3(0, 0, 20), v3(0, 0, 0));
    return { bg: '#efe8dc', overlay: (c) => {
      c.fillStyle = '#16141b'; c.font = '700 56px Bodoni'; c.fillText('THE GOLDFISH, THE BAG, THE PLEATS', 60, 88);
      c.font = '400 20px Jost'; c.fillStyle = '#3a3844';
      c.fillText('GOLDFISH  side · front · three-quarter. Tangerine body, pale striped fins, black eye in a white ring.', 60, 140);
      c.fillText('THE RULE OF THE BAG  it hangs by Barney\'s gravity; the water inside obeys the true down.', 60, 330);
      c.textAlign = 'center'; ['true down: down', 'sideways', 'up', 'the other way'].forEach((l, i) => c.fillText(l, (( -4.3 + i * 1.2) / 5.511 + 1) * 960, 690)); c.textAlign = 'left';
      c.fillText('THE PLEATS  flat paper people, pleated like Miyake. Seen edge-on they vanish.', 1000, 720);
      c.fillText('edge-on', 1790, 1040); c.fillText('a Pleat, folded', 1180, 180);
    } };
  },
};
