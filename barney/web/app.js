// Page-side harness: load a shot module, render frame t, hand back a PNG data URL.
import * as E from './engine.js';
let shot = null, state = null, lastT = -1;
export async function load(id) {
  E.init();
  const mod = await import(`./shots/${id}.js?v=${Date.now()}`);
  shot = mod.default; state = await shot.setup(E);
  lastT = -1;
  return { dur: shot.dur || null };
}
export function frame(t) {
  E.G.uTime.value = t;
  E.POST.uSeed.value = (Math.floor(t * 24) % 97) * 1.37;
  const dt = lastT < 0 || t < lastT ? 0 : t - lastT;
  const r = shot.frame(t, state, E, dt) || {};
  E.render(r.scene || state.scene, r.camera || state.camera, r.bg || state.bg || '#efe8dc', r.overlay);
  lastT = t;
  return E.outCanvas().toDataURL('image/png');
}
