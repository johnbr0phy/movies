"""mixdown.py: sound design + score -> out/audio/soundtrack.wav (48 kHz stereo, -16 LUFS, peak -1 dB).
Footsteps are placed from the same walk functions the shots use (held at 12 drawings a second), so every step lands
on the frame where a foot touches down."""
import os, sys, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import mix, sfx, sampler, score  # noqa: E402
from score import T, TOTAL, SR  # noqa: E402

OUT = os.path.join(HERE, '..', 'out', 'audio'); os.makedirs(OUT, exist_ok=True)
N = int((TOTAL + 2) * SR)
rng = np.random.default_rng(7)

def held(t): return math.floor(t * 12 + 1e-6) / 12
def steps_from(cyc, t0, t1, dt=1 / 24):
    """times where the walk phase (in cycles) passes a foot contact (0.25 + k/2), sampled on 12 fps held time"""
    out = []; prev = None; t = t0
    while t < t1:
        c = cyc(held(t))
        if prev is not None and c is not None and math.floor((c - 0.25) * 2) > math.floor((prev - 0.25) * 2): out.append(t)
        prev = c; t += dt
    return out
WC = lambda d: d / 0.68

# ------------------------------------------------------------------ synthesised sounds
def tock(f=900, dur=0.09, noise=0.6, seed=0, lp=6000):
    r = np.random.default_rng(seed); n = int(dur * SR); tt = np.arange(n) / SR
    y = np.sin(2 * np.pi * f * tt * (1 - 0.3 * tt / dur)) * np.exp(-tt * 70) + noise * r.standard_normal(n) * np.exp(-tt * 140)
    return mix.lowpass(y.astype(np.float32), lp) * 0.5
def swish(dur=0.22, lo=1800, hi=7000, seed=0):
    r = np.random.default_rng(seed); n = int(dur * SR); tt = np.arange(n) / SR
    y = mix.bandpass(r.standard_normal(n).astype(np.float32), lo, hi) * np.sin(np.pi * tt / dur) ** 2
    return y * 0.35
def whoosh(dur=0.9, seed=0, rev=False):
    r = np.random.default_rng(seed); n = int(dur * SR); tt = np.arange(n) / SR
    x = r.standard_normal(n).astype(np.float32); env = np.sin(np.pi * tt / dur) ** 1.5
    fc = 400 + 2600 * np.sin(np.pi * tt / dur); y = np.zeros(n, np.float32)
    for i0 in range(0, n, 2048):  # swept band: piecewise bandpass
        seg = x[i0:i0 + 2048 + 512]; f0 = float(fc[min(i0 + 1024, n - 1)])
        yy = mix.bandpass(seg, max(80, f0 * 0.5), min(20000, f0 * 1.8)); y[i0:i0 + 2048] += yy[:len(y[i0:i0 + 2048])]
    y = y * env * 0.6
    return y[::-1].copy() if rev else y
def squeak(dur=0.5, f0=1800, f1=2600, seed=0):
    n = int(dur * SR); tt = np.arange(n) / SR; f = f0 + (f1 - f0) * tt / dur + 60 * np.sin(2 * np.pi * 23 * tt)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * tt / dur) ** 0.5
    return (y * 0.15).astype(np.float32)
def pop(seed=0):
    r = np.random.default_rng(seed); n = int(0.12 * SR); tt = np.arange(n) / SR
    y = (r.standard_normal(n) * np.exp(-tt * 60) + 0.8 * np.sin(2 * np.pi * 180 * tt) * np.exp(-tt * 40)).astype(np.float32)
    return mix.lowpass(y, 5000) * 0.8
def thump(seed=0, f=70):
    n = int(0.35 * SR); tt = np.arange(n) / SR
    return (np.sin(2 * np.pi * f * tt * (1 - 0.4 * tt)) * np.exp(-tt * 14) * 0.8).astype(np.float32)
def plink(f=1400, dur=0.35):
    n = int(dur * SR); tt = np.arange(n) / SR; fr = f * (1 + 0.6 * np.exp(-tt * 40))
    return (np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.exp(-tt * 12) * 0.35).astype(np.float32)
def tink(f=2637, dur=2.0):
    n = int(dur * SR); tt = np.arange(n) / SR; y = np.zeros(n)
    for k, a, d in [(1, 1, 3), (2.76, 0.5, 6), (5.4, 0.25, 11), (8.9, 0.1, 16)]: y += a * np.sin(2 * np.pi * f * k * tt) * np.exp(-tt * d)
    return (y * np.minimum(1, tt / 0.001) * 0.25).astype(np.float32)
def car_pass(dur=1.6, f=140, seed=0):
    r = np.random.default_rng(seed); n = int(dur * SR); tt = np.arange(n) / SR; x = (tt - dur / 2) / (dur / 2)
    dop = 1 + 0.12 * (-np.tanh(x * 3)); hum = np.sin(2 * np.pi * np.cumsum(f * dop) / SR) + 0.4 * np.sin(4 * np.pi * np.cumsum(f * dop) / SR)
    air = mix.lowpass(r.standard_normal(n).astype(np.float32), 2500) * 0.5
    env = 1 / (1 + 12 * x * x)
    return ((hum * 0.5 + air) * env * 0.5).astype(np.float32)
def horn(f=330, dur=0.5):
    n = int(dur * SR); tt = np.arange(n) / SR; y = sum(np.sign(np.sin(2 * np.pi * f * k * tt)) / k for k in (1, 1.26))
    return (mix.lowpass(y.astype(np.float32), 1800) * np.minimum(1, tt / 0.02) * np.minimum(1, (dur - tt) / 0.05) * 0.15)
def bed(kind, dur, seed=0):
    r = np.random.default_rng(seed); n = int(dur * SR)
    if kind == 'room': x = mix.lowpass(sfx.pink(n, r).astype(np.float32), 900) * 0.05
    elif kind == 'city': x = mix.lowpass(sfx.brown(n, r).astype(np.float32), 400) * 0.25 + mix.bandpass(sfx.pink(n, r).astype(np.float32), 200, 1800) * 0.04
    elif kind == 'under': x = mix.lowpass(sfx.brown(n, r).astype(np.float32), 300) * 0.25
    elif kind == 'paper': x = mix.bandpass(sfx.pink(n, r).astype(np.float32), 300, 3000) * 0.015
    else: x = np.zeros(n, np.float32)
    return mix.fades(np.asarray(x, np.float32), 0.8, 0.8)


# ------------------------------------------------------------------ fully synthetic replacements (no CC BY-NC material)
def footstep(seed=0):
    """a small shoe on lacquered wood: heel tick + short body resonance + scuff"""
    r = np.random.default_rng(100 + seed); n = int(0.22 * SR); tt = np.arange(n) / SR
    tick = r.standard_normal(n) * np.exp(-tt * 180); body = sum(np.sin(2 * np.pi * f * tt) * np.exp(-tt * d) * a for f, d, a in [(180 + 15 * seed, 38, 0.8), (410, 55, 0.35), (920, 90, 0.2)])
    scuff = mix.bandpass(r.standard_normal(n).astype(np.float32), 1500, 6000) * np.exp(-((tt - 0.03) / 0.02) ** 2) * 0.25
    return (mix.lowpass((tick * 0.5 + body + scuff).astype(np.float32), 7000) * 0.45).astype(np.float32)
def drip(seed=0):
    """a water drop: a rising sine 'plip' with a tiny splash"""
    r = np.random.default_rng(200 + seed); n = int(0.16 * SR); tt = np.arange(n) / SR; f0 = 900 + 250 * r.random()
    f = f0 * (1 + 1.6 * (1 - np.exp(-tt * 60))); y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 38)
    y += mix.highpass(r.standard_normal(n).astype(np.float32), 3000) * np.exp(-tt * 200) * 0.15
    return (y * 0.35).astype(np.float32)
def pour(dur=2.0, seed=0):
    """a pour of water: bubbly band noise with random resonant glugs"""
    r = np.random.default_rng(300 + seed); n = int(dur * SR); tt = np.arange(n) / SR
    y = mix.bandpass(r.standard_normal(n).astype(np.float32), 400, 3500) * 0.25
    for k in range(int(dur * 40)):
        t0 = r.random() * dur; f = 500 + 1500 * r.random(); m = int(0.04 * SR); s0 = int(t0 * SR)
        if s0 + m < n: tb = np.arange(m) / SR; y[s0:s0 + m] += np.sin(2 * np.pi * f * (1 + 3 * tb) * tb) * np.exp(-tb * 90) * 0.2
    env = np.minimum(1, tt / 0.05) * np.minimum(1, (dur - tt) / 0.3)
    return np.stack([y * env, np.roll(y, 37) * env], 1).astype(np.float32) * 0.7
def creak(dur=1.0, seed=0):
    """a small door hinge: a slow stick-slip pulse train through a wooden resonance"""
    r = np.random.default_rng(400 + seed); n = int(dur * SR); x = np.zeros(n, np.float32); t = 0.0
    while t < dur: rate = 35 + 60 * np.sin(np.pi * t / dur) + 10 * r.random(); x[int(t * SR)] = 1.0; t += 1 / rate
    y = sum(mix.bandpass(x, f * 0.85, f * 1.15) * a for f, a in [(420, 1.0), (1100, 0.6), (2300, 0.3)])
    return (y * 3.0 * np.sin(np.pi * np.arange(n) / n) ** 0.5).astype(np.float32)
def birds(dur=20.0, seed=0):
    """distant small birds: sparse chirps (fast FM sweeps) in two layers of distance"""
    r = np.random.default_rng(500 + seed); n = int(dur * SR); y = np.zeros((n, 2), np.float32)
    for k in range(int(dur * 3)):
        t0 = r.random() * (dur - 0.5); m = int((0.05 + 0.08 * r.random()) * SR); tb = np.arange(m) / SR
        f = (3200 + 1800 * r.random()) * (1 + 0.4 * np.sin(2 * np.pi * (18 + 10 * r.random()) * tb)) * (1 - 0.3 * tb / tb[-1] * r.random())
        c = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * tb / tb[-1]) * (0.3 if r.random() < 0.5 else 0.12)
        for rep in range(1 + int(r.random() * 3)):
            s0 = int((t0 + rep * 0.09) * SR); p = r.random() * 2 - 1
            if s0 + m < n: y[s0:s0 + m, 0] += c * np.sqrt(0.5 * (1 - p)); y[s0:s0 + m, 1] += c * np.sqrt(0.5 * (1 + p))
    return y

def lib(name):
    x = sfx.get(name); return np.asarray(x, np.float32)

def build():
    fx = np.zeros((N, 2), np.float32); amb = np.zeros((N, 2), np.float32)
    def put(buf, clip, t, g=0.0, pan=0.0): mix.place(buf, clip, t, gain_db=g, pan=pan)
    # ---- ambience beds
    put(amb, bed('room', T('S06', 2.5) + 1, 1), 0.0, -2)                      # corridors and gallery
    put(amb, mix.loop_to(lib('water_channel'), T('S09') - T('S05', 2.5)), T('S05', 2.5), -20, 0.2)   # the fountain
    put(amb, bed('paper', T('S13') - T('S09') + 0.5, 2), T('S09'), 0)
    put(amb, birds(T('S15') - T('S13')), T('S13'), -10, 0)
    put(amb, bed('city', T('S18') - T('S15') + 0.5, 3), T('S15'), -15)
    put(amb, mix.loop_to(lib('wind_soft'), T('S21') - T('S18')), T('S18'), -18)
    put(amb, bed('under', T('S26') - T('S21'), 4), T('S21'), -16)
    put(amb, bed('paper', 12, 5), T('S26'), 0)
    # ---- footsteps (per shot walk functions, mirroring the shots)
    fs = [footstep(i) for i in (1, 2, 3, 4)]
    def feet(times, g=-14, pan=0.0, kind='wood', seed=0):
        for i, t in enumerate(times):
            if kind == 'wood': clip = fs[i % 4]
            elif kind == 'stone': clip = tock(700 + 60 * (i % 3), seed=i)
            elif kind == 'glass': clip = tock(2400, dur=0.05, noise=0.2, seed=i, lp=9000)
            elif kind == 'soft': clip = tock(500, dur=0.07, noise=0.8, seed=i, lp=2500)
            else: clip = fs[i % 4]
            put(fx, clip, t, g + rng.uniform(-1.5, 1.5), pan)
    feet([T('S01') + t for t in steps_from(lambda h: WC(0.68 * h), 0, 6)], -15)
    feet([T('S03') + t for t in steps_from(lambda h: WC(0.74 * h) if h < 8 else None, 0, 8)], -15)
    feet([T('S06') + t for t in steps_from(lambda h: WC(0.5 * (h - 1.0)) if 1.0 <= h < 3.3 else (WC(0.5 * 1.7 + 0.7 * (h - 3.3)) if h >= 3.3 else None), 0, 8)], -15)
    feet([T('S07') + t for t in steps_from(lambda h: WC(0.7 * h), 0, 9)], -16, 0.1, 'stone')
    feet([T('S08') + t for t in steps_from(lambda h: WC(0.55 * h), 0, 7)], -15, 0, 'stone')
    feet([T('S09') + t for t in steps_from(lambda h: WC(0.68 * h), 0, 9)], -17, -0.1, 'soft')
    feet([T('S10') + t for t in steps_from(lambda h: WC(0.68 * (h + 9)), 0, 8)], -17, -0.1, 'soft')
    feet([T('S11', 0.25 + k * 0.5) for k in range(20)] + [T('S11', 11.25 + k * 0.5) for k in range(2)], -15, 0, 'stone')
    feet([T('S12', 0.25 + k * 0.5) for k in range(3)], -15, 0, 'stone')
    feet([T('S13') + t for t in steps_from(lambda h: WC(0.68 * h) if h < 2.6 else None, 0, 2.6)], -17, 0, 'soft')
    feet([T('S16') + t for t in steps_from(lambda h: WC(0.68 * h), 0, 8)], -17, 0, 'glass')
    feet([T('S17') + t for t in steps_from(lambda h: WC(0.68 * h) if h < 2.0 else (WC(0.68 * (2.0 + (h - 3.6) * 0.6)) if h > 3.6 else None), 0, 6)], -17, 0, 'glass')
    feet([T('S18') + t for t in steps_from(lambda h: WC(0.6 * h), 0, 9)], -22, 0, 'soft')
    feet([T('S20') + t for t in steps_from(lambda h: WC(0.6 * (h - 0.8)) if h > 0.8 else None, 0, 8)], -20, 0, 'soft')
    feet([T('S21') + t for t in steps_from(lambda h: WC(0.6 * h) if h < 2.0 else None, 0, 2.0)], -20, 0, 'soft')
    feet([T('S25') + t for t in steps_from(lambda h: (0.7 * h / 0.68) if 0.3 < h < 3.1 else None, 0, 3.1)], -24, 0.2, 'glass')
    feet([T('S26') + t for t in steps_from(lambda h: WC(0.66 / 0.55 * h), 0, 11.5)], -26, 0, 'soft')
    # ---- the bag: a crinkle and a slosh here and there
    for t, g in [(T('S01', 0.4), -20), (T('S03', 2.0), -24), (T('S06', 3.0), -20), (T('S08', 2.6), -18), (T('S14', 0.4), -20), (T('S19', 0.6), -22)]:
        put(fx, lib('plastic_bag'), t, g, -0.2)
    # ---- spot effects
    put(fx, creak(1.4), T('S05', 1.6), -14, 0.1); put(fx, tock(1600, 0.05, 0.3), T('S05', 1.5), -14)
    put(fx, whoosh(1.2, 1), T('S06', 2.6), -18)
    for i in range(24): put(fx, swish(seed=i), T('S09', 0.02 + i * 0.5), -16, rng.uniform(-0.5, 0.5))   # Pleats' paper steps
    for i in range(18): put(fx, swish(seed=40 + i), T('S10', 0.02 + i * 0.5), -18 - 1.2 * max(0, i - 2), rng.uniform(-0.5, 0.5))
    put(fx, lib('plastic_bag_2'), T('S10', 4.5), -14, 0.3)                                               # the fold
    for i in range(10): put(fx, swish(0.08, 3000, 9000, seed=90 + i), T('S10', 5.4 + i * 0.26), -20 - i, 0.4)   # crane wings
    put(fx, tock(2600, 0.04, 0.1), T('S12', 1.6), -16)
    put(fx, whoosh(1.4, 2), T('S12', 4.5), -12); put(fx, thump(f=90), T('S12', 5.9), -12)
    put(fx, squeak(0.4, 900, 700), T('S13', 3.3), -22)                                                 # sitting on the slide
    put(fx, squeak(4.4, 1500, 2600)[::-1].copy(), T('S14', 0.6), -12, 0.1)                               # a reversed slide squeak
    put(fx, whoosh(4.8, 3, rev=True), T('S14', 0.4), -8)
    put(fx, whoosh(1.6, 4), T('S14', 5.0), -10)
    put(fx, whoosh(3.2, 5), T('S15', 0.0), -12); put(fx, thump(f=60), T('S15', 3.4), -8)
    for i, (t, f) in enumerate([(0.6, 130), (2.1, 160), (3.9, 110), (5.2, 150), (6.8, 125)]):
        put(fx, car_pass(1.8, f, i), T('S15', t), -19, [-0.6, 0.6][i % 2]); put(fx, car_pass(1.8, f * 1.1, i + 9), T('S16', t + 0.4), -21, [0.6, -0.6][i % 2])
    for t in (1.4, 4.7): put(fx, horn(330), T('S15', t), -20, -0.5); put(fx, horn(392), T('S16', t + 1.5), -22, 0.5)
    put(fx, car_pass(0.9, 200, 20), T('S17', 1.45), -6, 0.3); put(fx, pop(), T('S17', 1.9), -6)
    put(fx, pour(0.7, 1), T('S17', 1.92), -12)
    for i in range(12): put(fx, drip(i), T('S17', 2.7 + i * 0.12 + (i % 3) * 0.02), -20)
    for k in range(17): put(fx, drip(k + 20), T('S18', 0.3 + k * 0.55), -18 - k * 0.3, -0.1)
    put(fx, plink(1200), T('S19', 4.6), -12)
    for i in range(20):
        t = T('S20', -1.5 + i * 0.45)
        if t >= T('S20'): put(fx, plink(1100 + 90 * i), t, -18 - 0.2 * i)
    put(fx, pour(2.0, 2)[::-1].copy(), T('S21', 4.3), -10)                   # the water pours UP
    for i in range(3): put(fx, tink(1760 * (1 + 0.25 * i), 1.5), T('S21', 4.7 + i * 0.5), -20)          # ripples
    put(fx, plink(900, 0.6), T('S22', 0.4), -18)
    put(fx, tink(2637, 2.5), T('S25', 3.6), -6, 0.2)                                                  # Barney taps the glass
    put(fx, tink(1975, 2.5), T('S25', 4.2), -7, -0.1)                                                 # the fish taps back
    put(fx, tink(2637, 1.2), T('S25', 7.0), -5, 0.2)                                                  # second tap: cut to black
    put(fx, tink(2637, 2.5), T('S26', 11.0), -10, 0.0)
    return fx, amb

if __name__ == '__main__':
    music = score.render(os.path.join(OUT, 'music.wav'))
    fx, amb = build()
    mix.write_wav(os.path.join(OUT, 'fx.wav'), fx, check_peak=False); mix.write_wav(os.path.join(OUT, 'amb.wav'), amb, check_peak=False)
    # silence after the second tap in S25 (the cut to black): only the tink's ring survives
    cut = int(T('S25', 7.0) * SR); gate = np.ones(N, np.float32); fadeN = int(0.02 * SR)
    for buf in (music, amb):
        buf[cut:cut + fadeN] *= np.linspace(1, 0, fadeN)[:, None]; buf[cut + fadeN:int(T('S26') * SR)] = 0
    full = music * mix.db2amp(-1.0) + sampler.room(fx, wet=0.18) + amb
    full = full[: int(TOTAL * SR)]
    full = mix.compress(full, threshold_db=-20, ratio=2.0)
    full = mix.normalise_to(full, target_lufs=-16.0, peak_ceiling_db=-1.0)
    mix.write_wav(os.path.join(OUT, 'soundtrack.wav'), full)
    print('LUFS', round(mix.lufs(full), 2), 'peak dB', round(20 * np.log10(np.abs(full).max()), 2), 'len', len(full) / SR)
