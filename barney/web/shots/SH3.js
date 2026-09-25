// Style sheet: palettes by act, surface patterns, line and shadow, the two gravities, and what not to do.
export default {
  dur: 1,
  async setup(E) {
    await E.loadFonts();
    const { THREE, toon, PAL, v3 } = E; const scene = new THREE.Scene();
    const sw = [
      toon({ color: PAL.bone, color2: PAL.navy, pattern: 'stripes', axis: v3(0, 1, 0), freq: 5, duty: 0.42 }),
      toon({ color: '#f3eee4', color2: '#1f1e27', pattern: 'checker', axis: v3(1, 0, 0), axis2: v3(0, 1, 0), freq: 2.5 }),
      toon({ color: '#b9b7b3', color2: '#d3d2cf', pattern: 'pleats', axis: v3(1, 0, 0), freq: 6 }),
      toon({ color: PAL.lemon, color2: '#c9a20e', pattern: 'pleats', axis: v3(0, 1, 0), freq: 8 }),
    ];
    const tiles = sw.map((m, i) => { const q = new THREE.Mesh(new THREE.PlaneGeometry(1.1, 1.1), m); q.position.set(-4.6 + i * 1.35, -0.85, 0); scene.add(q); return q; });
    // toon spheres: one hard shadow band
    const cols = [PAL.bone, PAL.red, PAL.fish, PAL.cobalt, '#2bb38a'];
    cols.forEach((c, i) => { const sp = new THREE.Mesh(new THREE.SphereGeometry(0.42, 48, 32), toon({ color: c })); sp.position.set(1.2 + i * 1.0, -0.85, 0); scene.add(sp); });
    const camera = E.ortho(6.2);
    E.G.uLight.value.set(-0.5, 0.75, 0.5).normalize(); E.POST.uLine.value = 4.5;
    return { scene, camera };
  },
  frame(t, s, E) {
    E.aim(s.camera, E.v3(0, 0, 20), E.v3(0, 0, 0));
    const acts = [
      ['I  GALLERY, DOOR, PLAZA', ['#f2ece1', '#1c2b52', '#d42a2f', '#1f1e27', '#dfe9e6']],
      ['II  RUNWAY, STAIRS, SLIDE', ['#f3d21c', '#2447b8', '#e0287a', '#ff8a1c', '#2bb38a', '#ecebe6']],
      ['III  THE VERTICAL CITY', ['#16505a', '#ff9b3d', '#8fd0c8', '#20343f', '#e8dcc4']],
      ['IV  THE GREY PLAIN', ['#b9b7b3', '#d3d2cf', '#c9c8c4', '#8f8d8a', '#ff6a14']],
      ['V  THE SEA', ['#1f45b0', '#5b8cff', '#e7cf98', '#ff6a14', '#ffb070']],
    ];
    return { bg: '#efe8dc', overlay: (c) => {
      c.fillStyle = '#16141b'; c.font = '700 64px Bodoni'; c.fillText('BARNEY', 60, 92); c.font = 'italic 400 28px BodoniItalic'; c.fillStyle = '#1c2b52'; c.fillText('style sheet', 330, 90);
      c.font = '400 19px Jost'; c.fillStyle = '#3a3844';
      acts.forEach(([name, sws], r) => { const y = 150 + r * 64; c.fillStyle = '#3a3844'; c.fillText(name, 60, y + 30);
        sws.forEach((h, i) => { c.fillStyle = h; c.fillRect(420 + i * 70, y, 60, 44); c.strokeStyle = '#16141b'; c.lineWidth = 2; c.strokeRect(420 + i * 70, y, 60, 44); }); });
      c.fillStyle = '#3a3844';
      c.fillText('SURFACES  Breton stripe · chequer · Miyake pleat · lemon slide pleat', 60, 480);
      c.fillText('SHADING  flat colour + one hard shadow band. No gradients on anything that moves.', 1000, 480);
      c.fillText('LINE  ligne claire: one even ink weight, found from depth, normals and object edges.', 1000, 800);
      c.fillText('THE TWO GRAVITIES  Barney\'s down is whatever he stands on. The water in the bag keeps the true down.', 60, 1010);
      c.fillText('The camera takes his side late. When the water line is sideways in frame, the picture is lying.', 60, 1040);
      c.font = '700 22px Jost'; c.fillStyle = '#d42a2f'; c.fillText('DO NOT', 1000, 150);
      c.font = '400 19px Jost'; c.fillStyle = '#3a3844';
      ['no photoreal textures, no soft gradients, no bloom', 'no random surrealism: every illusion obeys the two gravities', 'no dialogue, no subtitles, no words except title and credits', 'no Pixar-style rounded 3D shading or rim lights', 'never tilt the water line with Barney; it only knows the true down', 'no copied characters, logos or garments: stripes, pleats, cones only'].forEach((l, i) => c.fillText('×  ' + l, 1000, 185 + i * 32));
      // line weights
      [1.5, 3, 5.5].forEach((w, i) => { c.strokeStyle = '#16141b'; c.lineWidth = w; c.beginPath(); c.moveTo(1000, 860 + i * 30); c.lineTo(1300, 860 + i * 30); c.stroke(); c.fillText(['far', 'mid', 'near (fixed 5.5 px at 2x)'][i], 1320, 866 + i * 30); });
    } };
  },
};
