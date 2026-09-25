// S25 (8 s) The goldfish looks in through the glass. Tiny Barney walks up the curved inside of the bowl (his down is
// the glass) until he is face to face with it, and taps the glass. The fish taps back, nose to glass. We push into its
// eye until it fills the frame: in the black of it, a tiny upside-down boy. Cut to black on the second tap.
import { realSea, swayKelp, BOWL_R, BOWL_C } from '../sets/bowl.js';
import { makeActor, drive, walkCycles } from '../actor.js';
import { makeFish } from '../rig/fish.js';
export default {
  dur: 8,
  async setup(E) {
    const { THREE } = E;
    const scene = new THREE.Scene(); const R = realSea(); scene.add(R);
    const a = makeActor(scene, { fill: 0 });
    const F = makeFish(); scene.add(F.g); F.g.scale.setScalar(22);
    const camera = E.persp(34); camera.near = 0.01; camera.updateProjectionMatrix();
    E.G.uLight.value.set(0.25, 0.85, 0.45).normalize(); E.G.uShadowTint.value.set('#a7b4e6');
    E.POST.uHazeDist.value = 28; E.POST.uHaze.value.set('#1f45b0'); E.POST.uHazeMax.value = 0.92;
    return { scene, camera, a, F, R };
  },
  frame(t, s, E, dt) {
    const { THREE, v3, seg, ease, lerp } = E;
    swayKelp(s.R, t);
    // the fish outside the glass at +x, facing -x, its eye level with the bowl's equator
    const dir = v3(1, 0, 0.35).normalize(); // from bowl centre to the fish
    const tap1 = 3.6, tap2 = 7.0;
    const nose = BOWL_C.clone().add(dir.clone().multiplyScalar(BOWL_R + 0.15 + 0.35 * (1 - seg(t, tap1 + 0.2, tap1 + 0.6, ease.inOut)) + 0.1 * seg(t, tap1 + 0.9, 5.0)));
    const fwd = dir.clone().negate(); const up = v3(0, 1, 0); const z = new THREE.Vector3().crossVectors(fwd, up).normalize();
    const fp = nose.clone().sub(fwd.clone().multiplyScalar(0.036 * 22)).add(v3(0, -0.12, 0));
    s.F.g.position.copy(fp); s.F.g.quaternion.setFromRotationMatrix(new THREE.Matrix4().makeBasis(fwd, up, z)); s.F.set(t, 0.25);
    // Barney walks from the disc edge up the inside of the glass: his up is the inward normal
    const disc = BOWL_C.y - 1.1; const rimA = Math.acos(-1.1 / BOWL_R); // polar angle from +y of the disc edge
    const walk = seg(t, 0.3, 3.1); const pol = lerp(rimA, Math.PI / 2 + 0.02, walk);
    const n = v3(Math.sin(pol) * dir.x, Math.cos(pol), Math.sin(pol) * dir.z).normalize(); // outward normal at his feet
    let pos = BOWL_C.clone().add(n.clone().multiplyScalar(BOWL_R - 0.01));
    if (t < 0.3) pos = BOWL_C.clone().add(v3(dir.x * (BOWL_R * Math.sin(rimA) - 0.35), disc - BOWL_C.y, dir.z * (BOWL_R * Math.sin(rimA) - 0.35)));
    const bup = n.clone().negate(); const bfwd = v3(0, 1, 0).sub(bup.clone().multiplyScalar(bup.y)).normalize();
    const faceOut = seg(t, 3.1, 3.4, ease.inOut);
    drive(s.a, t, dt, { pos, up: t < 0.3 ? v3(0, 1, 0) : bup, fwd: t < 0.3 ? dir : bfwd.clone().lerp(dir, faceOut).normalize(), trueUp: v3(0, 1, 0), scale: 0.2, fill: 0, fish: false, bagHidden: true,
      pose: (th) => (th < 3.1 ? { walk: walkCycles(0.14 * th / 0.2) } : { armL: (Math.abs(th - tap1) < 0.15 || Math.abs(th - tap2) < 0.15) ? [1.45, -0.05, 0.1] : [1.2, -0.05, 0.4], headPitch: -0.1, mouth: th > tap1 + 0.4 ? 'grin' : 'o' }) });
    // camera: over the fish's shoulder onto Barney, then push into the fish's eye
    const eye = s.F.g.localToWorld(v3(0.02, 0.006, 0.0118));
    const u = seg(t, 4.3, 6.8, ease.inOut);
    const side = v3(-dir.z, 0, dir.x);
    const cp0 = BOWL_C.clone().add(dir.clone().multiplyScalar(BOWL_R * 0.95)).add(side.clone().multiplyScalar(-2.9)).add(v3(0, -0.35, 0));
    const ct0 = BOWL_C.clone().add(dir.clone().multiplyScalar(BOWL_R + 0.1)).add(v3(0, -0.45, 0));
    const eyeN = z.clone(); // eye faces the fish's side (+z of fish)
    const cp1 = eye.clone().add(eyeN.clone().multiplyScalar(0.22)).add(v3(0, 0.01, 0));
    const cp = cp0.clone().lerp(cp1, u), ct = ct0.clone().lerp(eye, Math.min(1, u * 1.6));
    E.aim(s.camera, cp, ct);
    // reflection of a tiny upside-down Barney in the eye (drawn over the frame at the eye's screen position)
    const pe = eye.clone().project(s.camera); const px = (pe.x * 0.5 + 0.5) * 1920, py = (-pe.y * 0.5 + 0.5) * 1080;
    const eyeR = 0.0045 * 22; const dist = s.camera.position.distanceTo(eye); const rPix = eyeR / dist / Math.tan(34 * Math.PI / 360) * 540;
    const black = t > tap2 + 0.05;
    return { bg: '#1f45b0', overlay: (c) => {
      if (u > 0.25 && !black) { const k = Math.min(1, (u - 0.25) / 0.3); const h = rPix * 0.62; c.save(); c.translate(px + rPix * 0.06, py); c.rotate(Math.PI); c.globalAlpha = 0.92 * k;
        const W = (x) => x * h; const ln = W(0.018);
        const rr = (x, y, w, hh, r, fill, stroke) => { c.beginPath(); c.roundRect(W(x), W(y), W(w), W(hh), W(r)); c.fillStyle = fill; c.fill(); if (stroke) { c.lineWidth = ln; c.strokeStyle = stroke; c.stroke(); } };
        // legs, socks, red shoes
        rr(-0.1, -0.2, 0.07, 0.2, 0.03, '#f5d4b9'); rr(0.03, -0.2, 0.07, 0.2, 0.03, '#f5d4b9');
        rr(-0.1, -0.09, 0.07, 0.09, 0.02, '#fbfaf6'); rr(0.03, -0.09, 0.07, 0.09, 0.02, '#fbfaf6');
        rr(-0.12, -0.01, 0.1, 0.05, 0.025, '#d42a2f'); rr(0.02, -0.01, 0.1, 0.05, 0.025, '#d42a2f');
        // shorts
        rr(-0.14, -0.3, 0.28, 0.12, 0.03, '#2a2833', '#cfd6e6');
        // marinière with stripes
        rr(-0.14, -0.56, 0.28, 0.27, 0.05, '#f2ece1');
        c.save(); c.beginPath(); c.roundRect(W(-0.14), W(-0.56), W(0.28), W(0.27), W(0.05)); c.clip(); c.fillStyle = '#1c2b52'; for (let j = 0; j < 6; j++) c.fillRect(W(-0.2), W(-0.54 + j * 0.045), W(0.4), W(0.02)); c.restore();
        // capelet
        c.beginPath(); c.moveTo(W(-0.1), W(-0.56)); c.lineTo(W(0.1), W(-0.56)); c.lineTo(W(0.2), W(-0.49)); c.lineTo(W(-0.2), W(-0.49)); c.closePath(); c.fillStyle = '#f7f3ea'; c.fill();
        // arm up with the bag (a thin ring and a pale drop)
        c.lineCap = 'round'; c.strokeStyle = '#f2ece1'; c.lineWidth = W(0.055); c.beginPath(); c.moveTo(W(0.13), W(-0.52)); c.lineTo(W(0.2), W(-0.72)); c.stroke();
        c.beginPath(); c.arc(W(0.21), W(-0.76), W(0.03), 0, Math.PI * 2); c.fillStyle = '#f5d4b9'; c.fill();
        c.strokeStyle = '#d42a2f'; c.lineWidth = ln; c.beginPath(); c.arc(W(0.21), W(-0.8), W(0.025), 0, Math.PI * 2); c.stroke();
        // head: face, black bob with fringe, outlined so it shows against the black eye
        c.beginPath(); c.arc(0, W(-0.74), W(0.17), 0, Math.PI * 2); c.fillStyle = '#f5d4b9'; c.fill();
        c.beginPath(); c.moveTo(W(-0.19), W(-0.62)); c.lineTo(W(-0.19), W(-0.78)); c.quadraticCurveTo(W(-0.19), W(-0.95), W(0), W(-0.95)); c.quadraticCurveTo(W(0.19), W(-0.95), W(0.19), W(-0.78)); c.lineTo(W(0.19), W(-0.62)); c.lineTo(W(0.12), W(-0.62)); c.lineTo(W(0.12), W(-0.76)); c.lineTo(W(-0.12), W(-0.76)); c.lineTo(W(-0.12), W(-0.62)); c.closePath();
        c.fillStyle = '#17151d'; c.fill(); c.lineWidth = ln; c.strokeStyle = '#cfd6e6'; c.stroke();
        c.fillStyle = '#121118'; c.beginPath(); c.ellipse(W(-0.06), W(-0.69), W(0.018), W(0.026), 0, 0, Math.PI * 2); c.ellipse(W(0.06), W(-0.69), W(0.018), W(0.026), 0, 0, Math.PI * 2); c.fill();
        c.fillStyle = '#f1a79a'; c.beginPath(); c.ellipse(W(-0.1), W(-0.64), W(0.025), W(0.015), 0, 0, Math.PI * 2); c.ellipse(W(0.1), W(-0.64), W(0.025), W(0.015), 0, 0, Math.PI * 2); c.fill();
        c.restore(); }
      if (black) { c.fillStyle = '#000'; c.fillRect(0, 0, 1920, 1080); }
    } };
  },
};
