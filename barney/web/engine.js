// BARNEY render engine: three.js in headless Chromium, drawn as ligne claire.
// Pass A renders opaque geometry at 2x into two targets: flat toon colour, and an aux buffer holding
// (view normal, linear depth, object id). Pass B renders transparent things (the bag, water, glass) into a
// colour target that shares pass A's depth. The post pass downsamples 2x2, inks every edge it finds in the aux
// buffer at a fixed pixel width, composites the transparent layer, then grades and adds paper grain.
import * as THREE from 'three';
export { THREE };

export const W = 1920, H = 1080, SS = 1.5;
export const PAL = {
  ink: '#16141b', bone: '#f2ece1', paper: '#efe8dc', navy: '#1c2b52', red: '#d42a2f', skin: '#f5d4b9', blush: '#f1a79a',
  fish: '#ff6a14', fishLight: '#ffb070', cobalt: '#2447b8', lemon: '#f3d21c', fuchsia: '#e0287a', tangerine: '#ff8a1c',
  grey: '#b9b7b3', greyDark: '#8f8d8a', teal: '#1f6f78', sodium: '#ff9b3d', sea: '#1d3fa3', mint: '#bfe6dc', black: '#1b1a20',
};

// shared uniforms: every material reads the same light and shadow tint, so a shot changes them in one place
export const G = {
  uLight: { value: new THREE.Vector3(-0.45, 0.8, 0.4).normalize() },
  uLightTh: { value: 0.12 },
  uShadowTint: { value: new THREE.Color('#b9bdd6') },
  uShadowMix: { value: 1.0 },
  uTime: { value: 0 },
};

let nextId = 1;
export function newId() { nextId = (nextId % 4000) + 1; return nextId; }

const VERT = /* glsl */`
out vec3 vObj; out vec3 vWorld; out vec3 vNWorld; out vec3 vNView; out vec2 vUv; out float vDepth; out vec3 vViewDir;
void main() {
  #ifdef USE_INSTANCING
    mat4 im = instanceMatrix;
  #else
    mat4 im = mat4(1.0);
  #endif
  vObj = position; vUv = uv;
  vec4 w = modelMatrix * im * vec4(position, 1.0); vWorld = w.xyz;
  mat3 nm = mat3(modelMatrix) * mat3(im);
  vNWorld = normalize(nm * normal);
  vNView = normalize(mat3(viewMatrix) * vNWorld);
  vec4 mv = viewMatrix * w; vDepth = -mv.z;
  vViewDir = isOrthographic ? normalize((inverse(viewMatrix) * vec4(0., 0., 1., 0.)).xyz) : normalize(cameraPosition - w.xyz);
  gl_Position = projectionMatrix * mv;
}`;

// pattern ids: 0 flat, 1 stripes (object-space axis), 2 checker (object-space plane), 3 pleats (shaded folds), 4 bands (uv.y)
const FRAG = /* glsl */`
precision highp float;
in vec3 vObj; in vec3 vWorld; in vec3 vNWorld; in vec3 vNView; in vec2 vUv; in float vDepth; in vec3 vViewDir;
layout(location = 0) out vec4 oColor;
layout(location = 1) out vec4 oAux;
uniform vec3 uBase; uniform vec3 uColor2; uniform vec3 uBack; uniform float uBackOn;
uniform int uPattern; uniform vec3 uAxis; uniform vec3 uAxis2; uniform float uFreq; uniform float uFreq2; uniform float uDuty; uniform float uPhase;
uniform float uId; uniform float uFlat; uniform float uEmit;
uniform vec3 uLight; uniform float uLightTh; uniform vec3 uShadowTint; uniform float uShadowMix;
uniform vec4 uClip; uniform float uClipOn; uniform int uMask; uniform vec4 uMaskP;
float aastep(float e, float x) { float w = fwidth(x) * 0.75; return smoothstep(e - w, e + w, x); }
float stripe(float s, float duty) { float tri = abs(fract(s) - 0.5); return 1.0 - aastep(duty * 0.5, tri); }
float sq(float s) { return aastep(0.25, abs(fract(s) - 0.5)); }
void main() {
  if (uClipOn > 0.5 && dot(vec4(vWorld, 1.0), uClip) > 0.0) discard;
  // bob haircut: cut a face window and a straight hem out of a sphere
  if (uMask == 1) {
    vec3 p = vObj;
    if (p.y < uMaskP.x) discard;
    if (p.z > uMaskP.y && p.y < uMaskP.z && abs(p.x) < uMaskP.w) discard;
  }
  // the Pleats: robe, shoulders, neck, faceless head, brimmed cone hat (metres, in uv * size)
  if (uMask == 2) {
    vec2 m = vec2((vUv.x - 0.5) * uMaskP.x, vUv.y * uMaskP.y); float H = uMaskP.y / 3.3;
    bool inside = false;
    float y = m.y / H, x = m.x / H;
    if (y > 0.03 && y < 2.15 && abs(x) < mix(0.5, 0.2, y / 2.15)) inside = true;
    if (length((vec2(x, y) - vec2(0.0, 2.08)) / vec2(0.27, 0.13)) < 1.0) inside = true;
    if (abs(x) < 0.055 && y > 2.0 && y < 2.32) inside = true;
    if (length(vec2(x, y) - vec2(0.0, 2.4)) < 0.13) inside = true;
    if (uMaskP.z > 0.5) {
      if (y > 2.47 && y < 3.2 && abs(x) < 0.17 * (3.2 - y) / 0.73) inside = true;
      if (length((vec2(x, y) - vec2(0.0, 2.5)) / vec2(0.25, 0.035)) < 1.0) inside = true;
    }
    if (!inside) discard;
  }
  vec3 n = normalize(vNWorld); if (!gl_FrontFacing) n = -n;
  float lit = mix(aastep(uLightTh, dot(n, uLight)), 1.0, uFlat);
  vec3 c1 = uBase, c2 = uColor2;
  float p = 0.0;
  if (uPattern == 1) { p = stripe(dot(vObj, uAxis) * uFreq + uPhase, uDuty); }
  else if (uPattern == 2) { float a = sq(dot(vObj, uAxis) * uFreq + uPhase), b = sq(dot(vObj, uAxis2) * uFreq); p = a * (1.0 - b) + (1.0 - a) * b; }
  else if (uPattern == 3) { float s = dot(vObj, uAxis) * uFreq + uPhase; float face = aastep(0.5, fract(s)) * (1.0 - aastep(0.97, fract(s)));
    c1 = mix(uBase, uBase * uColor2, face); }
  else if (uPattern == 4) { p = stripe(vUv.y * uFreq + uPhase, uDuty); }
  else if (uPattern == 5) { float s = vUv.x * uFreq + uPhase; float face = aastep(0.5, fract(s));
    c1 = mix(uBase, uBase * uColor2, face); }
  else if (uPattern == 6) { p = stripe(vUv.x * uFreq + uPhase, uDuty); }
  else if (uPattern == 7) { float a = sq(vUv.x * uFreq + uPhase), b = sq(vUv.y * uFreq2); p = a * (1.0 - b) + (1.0 - a) * b; }
  vec3 base = mix(c1, c2, p);
  if (!gl_FrontFacing && uBackOn > 0.5) base = uBack;
  vec3 shade = mix(base, base * uShadowTint, uShadowMix);
  vec3 col = mix(shade, base, lit);
  col = mix(col, base, uEmit);
  oColor = vec4(col, 1.0);
  vec3 nv = normalize(vNView); if (!gl_FrontFacing) nv = -nv;
  oAux = vec4(nv.xy * 0.5 + 0.5, vDepth, uId);
}`;

function col(c) { return c instanceof THREE.Color ? c : new THREE.Color(c); }

// Toon material. o: {color, color2, pattern:'flat'|'stripes'|'checker'|'pleats'|'bands', axis, axis2, freq, duty, phase,
// back, flat, emit, id, mask, maskP, side}
export function toon(o = {}) {
  const pat = { flat: 0, stripes: 1, checker: 2, pleats: 3, bands: 4, pleatsU: 5, bandsU: 6, checkUV: 7 }[o.pattern || 'flat'];
  const m = new THREE.ShaderMaterial({
    glslVersion: THREE.GLSL3, vertexShader: VERT, fragmentShader: FRAG,
    side: o.side === undefined ? THREE.FrontSide : o.side,
    uniforms: {
      uBase: { value: col(o.color || PAL.bone) }, uColor2: { value: col(o.color2 || PAL.navy) },
      uBack: { value: col(o.back || '#000') }, uBackOn: { value: o.back ? 1 : 0 },
      uPattern: { value: pat }, uAxis: { value: (o.axis || new THREE.Vector3(0, 1, 0)).clone().normalize() },
      uAxis2: { value: (o.axis2 || new THREE.Vector3(1, 0, 0)).clone().normalize() },
      uFreq: { value: o.freq || 10 }, uFreq2: { value: o.freq2 || o.freq || 10 }, uDuty: { value: o.duty === undefined ? 0.5 : o.duty }, uPhase: { value: o.phase || 0 },
      uId: { value: o.id || newId() }, uFlat: { value: o.flat || 0 }, uEmit: { value: o.emit || 0 },
      uClip: { value: new THREE.Vector4(0, 1, 0, 0) }, uClipOn: { value: 0 },
      uMask: { value: o.mask || 0 }, uMaskP: { value: o.maskP || new THREE.Vector4() },
      uLight: G.uLight, uLightTh: G.uLightTh, uShadowTint: G.uShadowTint, uShadowMix: G.uShadowMix,
    },
  });
  m.userData.kind = 'toon';
  return m;
}

// transparent film (bag, glass, water): tint + fresnel ink rim + a streak highlight; renders in pass B
const TFRAG = /* glsl */`
precision highp float;
in vec3 vObj; in vec3 vWorld; in vec3 vNWorld; in vec3 vNView; in vec2 vUv; in float vDepth; in vec3 vViewDir;
layout(location = 0) out vec4 oColor;
uniform vec3 uTint; uniform float uAlpha; uniform vec3 uBackTint; uniform float uBackAlpha; uniform float uRim; uniform float uRimW;
uniform vec3 uInk; uniform vec4 uClip; uniform float uClipOn; uniform float uLineAtClip; uniform float uHi; uniform vec3 uHiDir;
void main() {
  float dClip = dot(vec4(vWorld, 1.0), uClip);
  if (uClipOn > 0.5 && dClip > 0.0) discard;
  vec3 n = normalize(vNWorld); vec3 v = normalize(vViewDir);
  bool front = gl_FrontFacing; if (!front) n = -n;
  float fr = 1.0 - abs(dot(n, v));
  float w = fwidth(fr) * 1.2 + 0.002;
  float rim = uRim * smoothstep(1.0 - uRimW - w, 1.0 - uRimW + w, fr);
  vec3 c = front ? uTint : uBackTint; float a = front ? uAlpha : uBackAlpha;
  // highlight streak: a thin band where the normal faces the highlight direction
  float h = dot(n, normalize(uHiDir)); float hw = fwidth(h) + 0.003;
  float hi = uHi * (smoothstep(0.93 - hw, 0.93 + hw, h) - smoothstep(0.975 - hw, 0.975 + hw, h)) * (front ? 1.0 : 0.0);
  float surf = 0.0;
  if (uLineAtClip > 0.5 && uClipOn > 0.5) { float fw = fwidth(dClip) * 1.6 + 0.0005; surf = 1.0 - smoothstep(0.0, fw, -dClip); }
  vec3 col = c * a;
  float alpha = a;
  col = mix(col, vec3(1.0), hi); alpha = max(alpha, hi);
  float ink = max(rim, surf);
  col = mix(col, uInk, ink); alpha = mix(alpha, 1.0, ink);
  oColor = vec4(col, alpha);
}`;

export function film(o = {}) {
  const m = new THREE.ShaderMaterial({
    glslVersion: THREE.GLSL3, vertexShader: VERT, fragmentShader: TFRAG, side: THREE.DoubleSide,
    transparent: true, depthWrite: false,
    blending: THREE.CustomBlending, blendSrc: THREE.OneFactor, blendDst: THREE.OneMinusSrcAlphaFactor,
    blendSrcAlpha: THREE.OneFactor, blendDstAlpha: THREE.OneMinusSrcAlphaFactor,
    uniforms: {
      uTint: { value: col(o.tint || '#dff3ff') }, uAlpha: { value: o.alpha === undefined ? 0.12 : o.alpha },
      uBackTint: { value: col(o.backTint || o.tint || '#dff3ff') }, uBackAlpha: { value: o.backAlpha === undefined ? (o.alpha === undefined ? 0.08 : o.alpha) : o.backAlpha },
      uRim: { value: o.rim === undefined ? 1 : o.rim }, uRimW: { value: o.rimW || 0.1 }, uInk: { value: col(o.ink || PAL.ink) },
      uClip: { value: new THREE.Vector4(0, 1, 0, 0) }, uClipOn: { value: 0 }, uLineAtClip: { value: o.lineAtClip ? 1 : 0 },
      uHi: { value: o.hi === undefined ? 0.8 : o.hi }, uHiDir: { value: (o.hiDir || new THREE.Vector3(-0.5, 0.6, 0.6)).clone() },
    },
  });
  m.userData.kind = 'film';
  return m;
}

export function mesh(geo, mat, layer) { const m = new THREE.Mesh(geo, mat); if (mat.userData.kind === 'film' || layer === 1) m.layers.set(1); return m; }

// ---------------------------------------------------------------------------------------------- post
const POST_FRAG = /* glsl */`
precision highp float;
in vec2 vUv;
layout(location = 0) out vec4 oColor;
uniform sampler2D tColor; uniform sampler2D tAux; uniform sampler2D tTrans;
uniform vec2 uSrc; uniform float uLineScale; uniform float uLine; uniform vec3 uInk; uniform float uNormTh; uniform float uDepthTh;
uniform vec3 uLift; uniform vec3 uGain; uniform float uSat; uniform float uGrain; uniform float uPaper; uniform float uSeed;
uniform float uVignette; uniform vec3 uPaperCol; uniform float uLineFade; uniform float uFade; uniform vec3 uFadeCol; uniform vec3 uHaze; uniform float uHazeDist; uniform float uHazeMax;
float hash(vec2 p) { p = fract(p * vec2(123.34, 456.21)); p += dot(p, p + 45.32); return fract(p.x * p.y); }
float vnoise(vec2 p) { vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
  return mix(mix(hash(i), hash(i + vec2(1, 0)), f.x), mix(hash(i + vec2(0, 1)), hash(i + vec2(1, 1)), f.x), f.y); }
float edgeAt(vec2 uv) {
  vec4 c = texture(tAux, uv);
  vec3 nc = vec3(c.xy * 2.0 - 1.0, 0.0); nc.z = sqrt(max(0.0, 1.0 - dot(nc.xy, nc.xy)));
  float e = 0.0;
  if (c.w < 0.5) return 0.0;                     // background never inks; the object side does
  float ic = 1.0 / max(c.z, 1e-4);
  for (int i = 0; i < 4; i++) {
    float a = float(i) * 0.785398;
    vec2 o = vec2(cos(a), sin(a)) * uLine * uLineScale / uSrc;
    vec4 s1 = texture(tAux, uv + o), s2 = texture(tAux, uv - o);
    bool d1 = abs(s1.w - c.w) > 0.5, d2 = abs(s2.w - c.w) > 0.5;
    if (d1 && (s1.w < 0.5 || c.z <= s1.z + 0.0001)) e = 1.0;
    if (d2 && (s2.w < 0.5 || c.z <= s2.z + 0.0001)) e = 1.0;
    if (!d1 && !d2) {
      // planes have zero laplacian in 1/z; a step (self-occlusion) does not. Ink only the nearer side.
      float lap = 1.0 / max(s1.z, 1e-4) + 1.0 / max(s2.z, 1e-4) - 2.0 * ic;
      if (lap < -uDepthTh * ic) e = 1.0;
    }
    for (int k = 0; k < 2; k++) {
      vec4 h = texture(tAux, uv + (k == 0 ? o : -o) * 0.5);
      if (abs(h.w - c.w) > 0.5) continue;
      vec3 nh = vec3(h.xy * 2.0 - 1.0, 0.0); nh.z = sqrt(max(0.0, 1.0 - dot(nh.xy, nh.xy)));
      if (dot(nc, nh) < uNormTh) e = 1.0;
    }
  }
  // thin lines far away
  float fade = c.w > 0.5 ? clamp(1.0 - (c.z - uLineFade) / (uLineFade * 3.0 + 0.001), 0.25, 1.0) : 1.0;
  if (uLineFade <= 0.0) fade = 1.0;
  return e * fade;
}
void main() {
  vec3 acc = vec3(0.0);
  for (int j = 0; j < 2; j++) for (int i = 0; i < 2; i++) {
    vec2 uv = vUv + (vec2(float(i), float(j)) - 0.5) / uSrc;
    vec3 c = texture(tColor, uv).rgb;
    float e = edgeAt(uv);
    c = mix(c, uInk, e);
    if (uHazeDist > 0.0) { vec4 ax = texture(tAux, uv); if (ax.w > 0.5) c = mix(c, uHaze, uHazeMax * (1.0 - exp(-ax.z / uHazeDist))); }
    vec4 t = texture(tTrans, uv);
    c = c * (1.0 - t.a) + t.rgb;
    acc += c;
  }
  vec3 c = acc * 0.25;
  // grade
  c = uLift + c * (uGain - uLift);
  float l = dot(c, vec3(0.299, 0.587, 0.114)); c = mix(vec3(l), c, uSat);
  // paper: fibrous low-frequency tone and fine tooth, multiplied like ink on stock
  vec2 px = vUv * vec2(1920.0, 1080.0);
  float fib = vnoise(px * 0.012) * 0.6 + vnoise(px * 0.05) * 0.3 + vnoise(px * 0.35) * 0.1;
  float tooth = hash(floor(px));
  c *= mix(vec3(1.0), uPaperCol, uPaper * (0.55 + 0.45 * fib));
  c *= 1.0 - uPaper * 0.05 * tooth;
  c += (hash(px + uSeed) - 0.5) * uGrain;
  // vignette
  vec2 q = vUv - 0.5; c *= 1.0 - uVignette * dot(q, q) * 1.6;
  c = mix(c, uFadeCol, uFade);
  oColor = vec4(clamp(c, 0.0, 1.0), 1.0);
}`;
const POST_VERT = /* glsl */`out vec2 vUv; void main() { vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }`;

export const POST = {
  uLine: { value: 5.5 }, uInk: { value: new THREE.Color(PAL.ink) }, uNormTh: { value: 0.72 }, uDepthTh: { value: 0.25 },
  uLift: { value: new THREE.Vector3(0.015, 0.012, 0.02) }, uGain: { value: new THREE.Vector3(1, 1, 1) }, uSat: { value: 1.0 },
  uGrain: { value: 0.028 }, uPaper: { value: 0.35 }, uPaperCol: { value: new THREE.Color('#e9dcc6') }, uSeed: { value: 0 },
  uVignette: { value: 0.25 }, uLineFade: { value: 0 }, uHaze: { value: new THREE.Color('#9fd3d0') }, uHazeDist: { value: 0 }, uHazeMax: { value: 0.85 }, uFade: { value: 0 }, uFadeCol: { value: new THREE.Color('#000') },
};

let renderer, rtA, rtB, depthTex, postMesh, postScene, postCam, outCtx, glCanvas;
export function init() {
  glCanvas = document.getElementById('gl'); glCanvas.width = W; glCanvas.height = H;
  renderer = new THREE.WebGLRenderer({ canvas: glCanvas, antialias: false, preserveDrawingBuffer: true, alpha: false, premultipliedAlpha: false, powerPreference: 'high-performance' });
  renderer.setPixelRatio(1); renderer.setSize(W, H, false); renderer.autoClear = false;
  renderer.outputColorSpace = THREE.LinearSRGBColorSpace;
  THREE.ColorManagement.enabled = false;
  depthTex = new THREE.DepthTexture(Math.round(W * SS), Math.round(H * SS)); depthTex.type = THREE.UnsignedIntType;
  const opt = { type: THREE.HalfFloatType, minFilter: THREE.LinearFilter, magFilter: THREE.LinearFilter, depthBuffer: true, depthTexture: depthTex };
  rtA = new THREE.WebGLRenderTarget(Math.round(W * SS), Math.round(H * SS), Object.assign({ count: 2 }, opt));
  rtA.textures[1].minFilter = rtA.textures[1].magFilter = THREE.NearestFilter;
  rtB = new THREE.WebGLRenderTarget(Math.round(W * SS), Math.round(H * SS), Object.assign({}, opt, { type: THREE.HalfFloatType }));
  rtB.depthTexture = depthTex;
  const pm = new THREE.ShaderMaterial({ glslVersion: THREE.GLSL3, vertexShader: POST_VERT, fragmentShader: POST_FRAG, depthTest: false, depthWrite: false,
    uniforms: Object.assign({ tColor: { value: rtA.textures[0] }, tAux: { value: rtA.textures[1] }, tTrans: { value: rtB.texture }, uSrc: { value: new THREE.Vector2(W * SS, H * SS) }, uLineScale: { value: SS / 2 } }, POST) });
  postMesh = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), pm); postScene = new THREE.Scene(); postScene.add(postMesh);
  postCam = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
  outCtx = document.getElementById('out').getContext('2d');
  return renderer;
}

// sky / background colour for pass A (id 0, so silhouettes against it are inked)
export function render(scene, camera, bg = '#efe8dc', overlay) {
  scene.traverse(o => { if (o.isMesh && !Array.isArray(o.material) && o.material.userData.kind === 'film' && !o.layers.isEnabled(1)) o.layers.set(1); });
  renderer.setRenderTarget(rtA);
  renderer.setClearColor(new THREE.Color(bg), 0); renderer.clear(true, true, true);
  camera.layers.set(0); renderer.render(scene, camera);
  renderer.setRenderTarget(rtB);
  renderer.setClearColor(0x000000, 0); renderer.clear(true, false, false);
  camera.layers.set(1); renderer.render(scene, camera);
  camera.layers.set(0);
  renderer.setRenderTarget(null); renderer.clear(true, true, true);
  renderer.render(postScene, postCam);
  outCtx.setTransform(1, 0, 0, 1, 0, 0); outCtx.globalAlpha = 1; outCtx.globalCompositeOperation = 'source-over';
  outCtx.drawImage(glCanvas, 0, 0);
  if (overlay) overlay(outCtx);
}
export function outCanvas() { return document.getElementById('out'); }

// camera helpers: position, target, roll (radians, about the view axis), vertical fov
export function persp(fov = 35) { return new THREE.PerspectiveCamera(fov, W / H, 0.02, 400); }
export function ortho(h = 4) { const c = new THREE.OrthographicCamera(-h * W / H / 2, h * W / H / 2, h / 2, -h / 2, -200, 400); c.userData.h = h; return c; }
export function aim(cam, pos, target, roll = 0, up = new THREE.Vector3(0, 1, 0)) {
  cam.position.copy(pos); cam.up.copy(up); cam.lookAt(target);
  if (roll) cam.rotateZ(roll);
  cam.updateMatrixWorld(true);
}
export function orthoSize(cam, h) { cam.left = -h * W / H / 2; cam.right = h * W / H / 2; cam.top = h / 2; cam.bottom = -h / 2; cam.updateProjectionMatrix(); }

// easing and timing
export const ease = { inOut: (x) => x < 0.5 ? 2 * x * x : 1 - Math.pow(-2 * x + 2, 2) / 2, out: (x) => 1 - Math.pow(1 - x, 3), in: (x) => x * x * x,
  sine: (x) => -(Math.cos(Math.PI * x) - 1) / 2 };
export function seg(t, a, b, e = (x) => x) { return e(Math.min(1, Math.max(0, (t - a) / (b - a)))); }
export function lerp(a, b, t) { return a + (b - a) * t; }
export function v3(x, y, z) { return new THREE.Vector3(x, y, z); }
export function kf(t, keys, e = ease.inOut) { // keys [[t, value(number|Vector3)], ...]
  if (t <= keys[0][0]) return clone(keys[0][1]);
  for (let i = 1; i < keys.length; i++) if (t <= keys[i][0]) {
    const [t0, a] = keys[i - 1], [t1, b] = keys[i]; const u = e((t - t0) / (t1 - t0));
    return typeof a === 'number' ? a + (b - a) * u : a.clone().lerp(b, u);
  }
  return clone(keys[keys.length - 1][1]);
}
function clone(v) { return typeof v === 'number' ? v : v.clone(); }
export function held(t, fps = 12) { return Math.floor(t * fps + 1e-6) / fps; }
export function rng(seed) { let s = seed >>> 0 || 1; return () => { s = (Math.imul(s, 1664525) + 1013904223) >>> 0; return s / 4294967296; }; }

// fonts for overlays: Bodoni Moda (Didone) for titles, Jost for small type
let fontsLoaded = false;
export async function loadFonts() {
  if (fontsLoaded) return; fontsLoaded = true;
  for (const [fam, file, desc] of [['Bodoni', 'fonts/BodoniModa.ttf', { weight: '400 900' }], ['BodoniItalic', 'fonts/BodoniModa-Italic.ttf', { weight: '400 900', style: 'italic' }], ['Jost', 'fonts/Jost.ttf', { weight: '100 900' }]]) {
    const f = new FontFace(fam, `url(${file})`, desc); await f.load(); document.fonts.add(f);
  }
}
// fill text with Breton stripes: draws into ctx at (x, y) centred, returns width
export function stripedText(ctx, text, x, y, size, o = {}) {
  const font = `${o.weight || 700} ${size}px ${o.family || 'Bodoni'}`; ctx.save(); ctx.font = font; const w = ctx.measureText(text).width;
  const c = document.createElement('canvas'); c.width = Math.ceil(w + size); c.height = Math.ceil(size * 1.6); const x2 = c.getContext('2d');
  x2.font = font; x2.textBaseline = 'alphabetic'; x2.fillStyle = o.color || '#16141b'; x2.fillText(text, size / 2, size * 1.15);
  if (o.stripes !== false) { x2.globalCompositeOperation = 'source-atop'; x2.fillStyle = o.stripe || '#1c2b52'; const p = o.period || size / 9;
    for (let yy = (o.phase || 0) % p - p; yy < c.height; yy += p) x2.fillRect(0, yy, c.width, p * (o.duty || 0.42)); }
  ctx.drawImage(c, x - w / 2 - size / 2, y - size * 1.15);
  ctx.restore(); return w;
}
