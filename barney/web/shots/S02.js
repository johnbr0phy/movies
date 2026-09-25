// S02 (5 s) Title. BARNEY in a Didone, its letters filled with Breton stripes, on bone paper. It holds; then the letters
// fall UP out of the frame one by one, the way the water in the bag falls: towards a down that isn't ours.
export default {
  dur: 5,
  async setup(E) {
    await E.loadFonts();
    const scene = new E.THREE.Scene(); const camera = E.persp(30);
    return { scene, camera };
  },
  frame(t, s, E) {
    const word = 'BARNEY'; const size = 230;
    return { bg: '#efe8dc', overlay: (c) => {
      c.font = `700 ${size}px Bodoni`; const widths = [...word].map(ch => c.measureText(ch).width); const tot = widths.reduce((a, b) => a + b, 0) + 22 * (word.length - 1);
      let x = 960 - tot / 2;
      [...word].forEach((ch, i) => {
        const t0 = 2.3 + i * 0.24; const dt = Math.max(0, t - t0); const dy = -0.5 * 2600 * dt * dt; const rot = (i % 2 ? 1 : -1) * 0.25 * dt * dt;
        const fadeIn = Math.min(1, t / 0.6);
        c.save(); c.globalAlpha = fadeIn; c.translate(x + widths[i] / 2, 560 + dy); c.rotate(rot);
        E.stripedText(c, ch, 0, size * 0.35, size, { color: '#16141b', stripe: '#f2ece1', period: size / 11, duty: 0.38, phase: 0 });
        c.restore(); x += widths[i] + 22;
      });
      // a small italic line under it, which does not fall
      c.save(); c.globalAlpha = Math.min(1, t / 0.8) * (1 - Math.min(1, Math.max(0, t - 4.2) / 0.6)); c.fillStyle = '#1c2b52'; c.font = `italic 400 34px BodoniItalic`; c.textAlign = 'center';
      c.fillText('a boy, a goldfish, and which way is down', 960, 700); c.restore();
    } };
  },
};
