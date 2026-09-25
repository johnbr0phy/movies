// S26 (12 s) Credits on bone paper. A small Barney walks along a ruled line under the credits, carrying the empty bag,
// and at the right-hand edge of the frame simply turns the corner and walks up it and out.
import { makeActor, drive, walkCycles } from '../actor.js';
export default {
  dur: 12,
  async setup(E) {
    await E.loadFonts();
    const { THREE } = E; const scene = new THREE.Scene();
    const a = makeActor(scene, { fill: 0 });
    const camera = E.ortho(4.0);
    E.G.uLight.value.set(0.3, 0.8, 0.6).normalize();
    E.POST.uPaper.value = 0.5;
    return { scene, camera, a };
  },
  frame(t, s, E, dt) {
    const { v3, seg, ease } = E;
    const halfW = 4.0 * 16 / 9 / 2; const lineY = -1.25; const sc = 0.55; const speed = 0.66; // reaches the right edge at ~8 s, then walks up and out
    const d = -halfW - 0.3 + speed * t; // distance along the line then up the edge
    const edge = halfW - 0.02;
    let pos, up, fwd;
    if (d < edge) { pos = v3(d, lineY, 0); up = v3(0, 1, 0); fwd = v3(1, 0, 0); }
    else { const k = Math.min(1, (d - edge) / 0.12); pos = v3(edge, lineY + (d - edge), 0); up = v3(0, 1, 0).lerp(v3(-1, 0, 0), k).normalize(); fwd = v3(1, 0, 0).lerp(v3(0, 1, 0), k).normalize(); }
    drive(s.a, t, dt, { pos, up, fwd, trueUp: v3(0, 1, 0), scale: sc, fill: 0, fish: false, pose: (th) => ({ walk: walkCycles(speed / sc * th), mouth: 'smile', headYaw: -0.4 * Math.max(0, Math.sin((th - 2) * 0.8)) }) });
    E.aim(s.camera, v3(0, 0, 20), v3(0, 0, 0));
    const lines = [
      ['BARNEY', 'Bodoni', 700, 92, '#16141b'],
      ['written, designed, animated and scored by Claude', 'BodoniItalic', 400, 34, '#1c2b52'],
      ['for anyone who ever carried something small and alive a long way, carefully', 'BodoniItalic', 400, 26, '#3a3844'],
      ['', 'Jost', 400, 12, '#16141b'],
      ['instrument samples  Versilian Community Sample Library (CC0)', 'Jost', 400, 21, '#3a3844'],
      ['type  Bodoni Moda, Jost (SIL Open Font License)   ·   drawn with three.js', 'Jost', 400, 21, '#3a3844'],
    ];
    return { bg: '#efe8dc', overlay: (c) => {
      const a = Math.min(1, t / 1.0) * (1 - seg(t, 11.2, 12));
      c.save(); c.globalAlpha = a; c.textAlign = 'center';
      let y = 250; for (const [txt, fam, w, sz, col] of lines) { if (txt === 'BARNEY') { E.stripedText(c, txt, 960, y + sz * 0.35, sz, { stripe: '#f2ece1', period: sz / 11, duty: 0.38 }); y += sz * 0.9; continue; }
        c.font = `${fam === 'BodoniItalic' ? 'italic ' : ''}${w} ${sz}px ${fam}`; c.fillStyle = col; c.fillText(txt, 960, y); y += sz * 1.9; }
      // the ruled line he walks on
      const ly = 540 - lineY / 4.0 * 1080; c.strokeStyle = '#16141b'; c.lineWidth = 3; c.beginPath(); c.moveTo(0, ly); c.lineTo(1920, ly); c.stroke();
      c.restore();
    } };
  },
};
