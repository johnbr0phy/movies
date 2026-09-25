// Character sheet: Barney. Turnaround, poses, expressions. Orthographic, on bone paper.
import { makeActor, drive } from '../actor.js';
export default {
  dur: 1,
  async setup(E) {
    await E.loadFonts();
    const { THREE } = E; const scene = new THREE.Scene();
    const A = []; for (let i = 0; i < 18; i++) A.push(makeActor(scene, { fill: 0.6 }));
    const camera = E.ortho(6.2);
    E.G.uLight.value.set(-0.4, 0.8, 0.6).normalize();
    E.POST.uLine.value = 4.5;
    return { scene, camera, A };
  },
  frame(t, s, E) {
    const { v3 } = E; const up = v3(0, 1, 0);
    const yaw = (a) => v3(Math.sin(a), 0, Math.cos(a));
    // row 1: turnaround
    [0, 0.8, Math.PI / 2, 2.4, Math.PI].forEach((a, i) => drive(s.A[i], 0.5, 0, { pos: v3(-4.2 + i * 1.5, 0.9, 0), up, fwd: yaw(a), pose: { mouth: 'smile' }, fish: true }));
    // row 2: poses
    const poses = [{ walk: 0.25 }, { walk: 0.0 }, { walk: 0.25, bag: 'high', mouth: 'grin' }, { sit: true, bag: 'lap', mouth: 'sad', headPitch: 0.4 }, { kneel: true, bag: 'hold', mouth: 'o' }, { slide: true, bag: 'high', mouth: 'grin' }];
    poses.forEach((p, i) => drive(s.A[5 + i], 0.5, 0, { pos: v3(-4.2 + i * 1.5, -1.45, 0), up, fwd: yaw(0.9), pose: p, fill: i === 3 ? 0.35 : 0.6 }));
    for (let i = 11; i < 18; i++) { s.A[i].B.root.visible = false; if (s.A[i].bag) s.A[i].bag.g.visible = false; }
    E.aim(s.camera, v3(0, 0.25, 20), v3(0, 0.25, 0));
    return { bg: '#efe8dc', overlay: (c) => {
      c.fillStyle = '#16141b'; c.font = '700 64px Bodoni'; c.fillText('BARNEY', 60, 92); c.font = 'italic 400 28px BodoniItalic'; c.fillStyle = '#1c2b52'; c.fillText('character sheet', 330, 90);
      c.font = '400 20px Jost'; c.fillStyle = '#3a3844';
      c.fillText('TURNAROUND  front · three-quarter · side · three-quarter back · back', 60, 150);
      c.fillText('POSES  contact · passing · bag high · sitting (low point) · kneeling · sliding up', 60, 545);
      c.font = '400 17px Jost';
      const notes = ['Head is 1/3 of his height. Bob: blunt fringe, flat hem at the jaw.', 'Marinière: bone and navy, 30 stripes per metre, never a gradient.', 'Pleated bone capelet. Black shorts, white socks, red T-bar shoes.', 'Eyes are two black ovals with a white glint, never pupils or whites.', 'Always one hard shadow band. Line weight is fixed in pixels.'];
      notes.forEach((n, i) => c.fillText(n, 1420, 250 + i * 30));
    } };
  },
};
