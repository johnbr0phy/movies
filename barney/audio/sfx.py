"""sfx.py - sound effects library for "The Bicycle" (48 kHz float32).

Every effect is a function returning a float32 array (mono (n,) or stereo (n,2)) at 48 kHz.
Real recordings come from ESC-50 (CC BY-NC, Freesound ids in catalogue.json / README),
the rest is synthesised here.

    import sfx
    x = sfx.get('bike_bell_ring')            # any catalogue name (reads lib/<name>.wav if built,
                                             #   else renders it)
    y = sfx.bike_bell_ring(kind='double')    # or call a generator directly with parameters
    m = sfx.motor_roll(4.0, speed=lambda t: min(1, t/1.5))
    h = sfx.hum_voice([(62, 0.0, 0.6), (64, 0.6, 0.6), (66, 1.2, 1.2)])

CLI:
    python sfx.py build            # render every catalogue entry to lib/<name>.wav + lib/catalogue.json
    python sfx.py list             # names + descriptions
    python sfx.py render NAME OUT.wav
"""
from __future__ import annotations

import csv
import json
import math
import os
import sys

import numpy as np
import soundfile as sf
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mix  # noqa: E402

SR = 48000
LIB = os.path.join(HERE, "lib")
ESC = "/home/user/refs/esc50"
ONESHOT_LUFS = -18.0   # one-shots: max momentary (400 ms) loudness
AMBIENCE_LUFS = -24.0  # loops / beds: integrated loudness
PEAK_CEIL_DB = -1.5

# ============================================================================ helpers


def _rng(seed):
    return np.random.default_rng(seed)


def _n(dur):
    return int(round(dur * SR))


def _t(dur):
    return np.arange(_n(dur)) / SR


def _lf(b, a, x):
    return signal.lfilter(b, a, x)


def smooth_rand(n, rate_hz, rng, sr=SR):
    """Band-limited random control signal, roughly in [-1, 1], changing at ~rate_hz."""
    k = max(4, int(n / sr * rate_hz) + 4)
    pts = rng.uniform(-1, 1, k)
    xs = np.linspace(0, n, k)
    from scipy.interpolate import CubicSpline
    return np.clip(CubicSpline(xs, pts)(np.arange(n)), -1.5, 1.5)


def pink(n, rng):
    X = np.fft.rfft(rng.standard_normal(n))
    f = np.arange(len(X))
    X[1:] /= np.sqrt(f[1:])
    X[0] = 0
    y = np.fft.irfft(X, n)
    return y / (np.std(y) + 1e-12)


def brown(n, rng):
    X = np.fft.rfft(rng.standard_normal(n))
    f = np.arange(len(X))
    X[1:] /= f[1:]
    X[0] = 0
    y = np.fft.irfft(X, n)
    return y / (np.std(y) + 1e-12)


def band_noise(n, lo, hi, rng, order=2):
    return mix.bandpass(rng.standard_normal(n), lo, hi, SR, order)


def resonator_bank(x, freqs, t60s, gains, sr=SR):
    """Parallel 2-pole resonators (modal synthesis). Impulse -> sum of decaying sines
    with peak amplitude ~gain."""
    x = np.asarray(x, dtype=np.float64)
    y = np.zeros_like(x)
    for f, t60, g in zip(freqs, t60s, gains):
        if f >= sr / 2 * 0.98 or g == 0:
            continue
        w = 2 * np.pi * f / sr
        r = math.exp(-6.9078 / (max(t60, 1e-3) * sr))
        y += signal.lfilter([g * math.sin(w)], [1, -2 * r * math.cos(w), r * r], x)
    return y


def klatt_res(x, f, bw, sr=SR, anti=False):
    """Klatt formant resonator (unity DC gain) or anti-resonator (anti=True)."""
    T = 1.0 / sr
    C = -math.exp(-2 * math.pi * bw * T)
    B = 2 * math.exp(-math.pi * bw * T) * math.cos(2 * math.pi * f * T)
    A = 1 - B - C
    if anti:
        return signal.lfilter([1 / A, -B / A, -C / A], [1.0], x)
    return signal.lfilter([A], [1, -B, -C], x)


def pulse(n_len, shape="hann"):
    if n_len <= 1:
        return np.ones(1)
    if shape == "half":
        return np.sin(np.pi * (np.arange(n_len) + 0.5) / n_len)
    return np.hanning(n_len + 2)[1:-1]


def impulses(dur, times, amps, width_ms=0.3):
    x = np.zeros(_n(dur))
    p = pulse(max(1, int(width_ms / 1000 * SR)))
    for t, a in zip(times, amps):
        i = int(t * SR)
        if 0 <= i < len(x):
            m = min(len(p), len(x) - i)
            x[i:i + m] += a * p[:m]
    return x


def decorrelate(x, seed=5, taps=384):
    """Two decorrelated copies (flat magnitude random-phase FIRs) -> stereo."""
    rng = _rng(seed)
    out = []
    for ch in range(2):
        ph = rng.uniform(-np.pi, np.pi, taps // 2 + 1)
        ph[0] = 0
        ph[-1] = 0
        h = np.fft.irfft(np.exp(1j * ph), taps)
        h *= np.hanning(taps)
        h /= math.sqrt((h ** 2).sum())
        out.append(signal.fftconvolve(x, h)[: len(x)])
    return np.stack(out, axis=1)


def stereo_from_mono(x, width=0.5, seed=5):
    """Mono -> stereo: centre + width * decorrelated side."""
    x = np.asarray(x, dtype=np.float64)
    d = decorrelate(x, seed)
    side = (d[:, 0] - d[:, 1]) * 0.5
    return np.stack([x + width * side, x - width * side], axis=1)


def distant(x, lp=5000.0, hp=80.0, wet=0.35, decay=1.4, predelay=25.0, preset=None, keep_tail=True):
    """Distance treatment: air absorption low-pass, reverb, stereo."""
    import sampler
    y = mix.lowpass(mix.highpass(x, hp, SR, 2), lp, SR, 2)
    if preset:
        p = dict(sampler.PRESETS[preset])
        p["predelay_ms"] = predelay
        p["decay_s"] = decay
        return sampler.reverb(y, wet=wet, keep_tail=keep_tail, **p)
    return sampler.reverb(y, wet=wet, decay_s=decay, predelay_ms=predelay, lowcut=hp,
                          highcut=min(lp * 1.2, 16000), size=0.7, damping=0.6, keep_tail=keep_tail)


def trim_silence(x, thr_db=-65.0, pad=0.01):
    m = np.abs(mix.as_mono(x))
    pk = m.max() + 1e-12
    idx = np.where(m > pk * 10 ** (thr_db / 20))[0]
    if len(idx) == 0:
        return x
    a = max(0, idx[0] - int(pad * SR))
    b = min(len(x), idx[-1] + int(pad * SR))
    return x[a:b]


def finish(x, kind="oneshot", fin=0.002, fout=0.02, target=None, dc=True, trim=True):
    """Final polish: DC removal, (trim), fades, loudness normalisation with a peak ceiling."""
    x = np.asarray(x, dtype=np.float32)
    if dc and kind == "loop":
        # circular (wrap-padded) filtering keeps the loop seam continuous
        pad = min(len(x) - 1, SR)
        xp = np.concatenate([x[-pad:], x, x[:pad]])
        x = mix.highpass(xp - xp.mean(axis=0), 18.0, SR, 2)[pad:pad + len(x)]
    elif dc:
        x = mix.highpass(x - x.mean(axis=0), 18.0, SR, 2)
    if trim and kind == "oneshot":
        x = trim_silence(x)
    x = mix.fades(x, fin, fout, SR)
    return normalise(x, kind, target)


def momentary_max(x):
    """Max momentary loudness (400 ms window, 100 ms hop) in LUFS (K-weighted)."""
    xx = np.asarray(x, dtype=np.float64)
    if xx.ndim == 1:
        xx = xx[:, None]
    y = signal.sosfilt(mix._k_weight_sos(SR), xx, axis=0)
    blk = int(0.4 * SR)
    if len(y) < blk:
        y = np.concatenate([y, np.zeros((blk - len(y), y.shape[1]))])
    cs = np.concatenate([np.zeros((1, y.shape[1])), np.cumsum(y ** 2, axis=0)])
    idx = np.arange(0, len(y) - blk + 1, int(0.05 * SR))
    z = ((cs[idx + blk] - cs[idx]) / blk).sum(axis=1)
    return float(-0.691 + 10 * np.log10(max(z.max(), 1e-30)))


def normalise(x, kind="oneshot", target=None):
    x = np.asarray(x, dtype=np.float32)
    if kind == "oneshot":
        L = momentary_max(x)
        tgt = ONESHOT_LUFS if target is None else target
    else:
        L = mix.lufs(x)
        tgt = AMBIENCE_LUFS if target is None else target
    if not np.isfinite(L):
        return x
    g = 10 ** ((tgt - L) / 20)
    pk = np.abs(x).max() * g
    ceil = 10 ** (PEAK_CEIL_DB / 20)
    if pk > ceil:
        g *= ceil / pk
    return (x * g).astype(np.float32)


# ============================================================================ ESC-50 picks
# Chosen by tools/esc50_survey.py + tools/esc50_events.py (RMS/peak/flatness/onset counts,
# per-event SNR, f0, centroid, clipping) and by viewing spectrograms (see README).
# fields: file, t0, t1 (s, in the original clip), hp/lp (Hz), gate (dB below peak for a soft
# downward expander, None = off), kind ('oneshot' | 'loop'), loop_s (length of a built loop),
# desc.

ESC_PICKS = {
    # ---- dog (medium-small dog, f0 ~450-520 Hz, one animal, clean single barks with short room tail)
    "dog_bark_1": dict(file="4-191687-A-0.wav", t0=1.745, t1=2.40, hp=120, gate=-42, desc="single bark, medium-small dog (f0~445 Hz)"),
    "dog_bark_2": dict(file="4-191687-A-0.wav", t0=2.815, t1=3.46, hp=120, gate=-42, desc="single bark, same dog, variation"),
    "dog_bark_3": dict(file="4-191687-A-0.wav", t0=4.295, t1=4.985, hp=120, gate=-42, desc="single bark, same dog, bigger"),
    "dog_yip_1": dict(file="3-157695-A-0.wav", t0=2.425, t1=2.66, hp=150, desc="short excited yip, small dog (f0~550 Hz)"),
    "dog_yip_2": dict(file="3-157695-A-0.wav", t0=3.73, t1=3.96, hp=150, desc="short yip, variation"),
    "dog_yip_3": dict(file="3-157695-A-0.wav", t0=4.03, t1=4.26, hp=150, desc="short yip, variation"),
    "dog_whine": dict(file="5-217158-A-0.wav", t0=0.22, t1=3.60, hp=150, desc="pleading whine/whimper (f0~600 Hz), ~3.4 s"),
    "dog_pant": dict(file="3-112557-A-23.wav", t0=2.53, t1=5.0, hp=150, kind="loop", loop_s=8.0,
                     desc="rhythmic panting breaths (~2.8/s), loop (breathing category)"),
    "dog_sniff_1": dict(file="5-234335-A-23.wav", t0=1.64, t1=2.37, hp=300, gate=-40, desc="quick sniffing bursts"),
    "dog_sniff_2": dict(file="5-234335-A-23.wav", t0=2.42, t1=3.46, hp=300, gate=-40, desc="sniffing, longer"),
    # ---- cat (one cat, natural contours)
    "cat_meow_1": dict(file="4-161303-A-5.wav", t0=0.07, t1=0.92, hp=150, desc="meow, falling contour, ~1 s"),
    "cat_meow_2": dict(file="4-161303-A-5.wav", t0=2.14, t1=2.74, hp=150, desc="meow, same cat, shorter"),
    "cat_meow_3": dict(file="4-161303-A-5.wav", t0=3.90, t1=4.52, hp=150, desc="meow, same cat, higher"),
    "cat_meow_long": dict(file="1-56380-A-5.wav", t0=2.60, t1=4.40, hp=150, desc="long insistent meow (other cat)"),
    # ---- birds
    "crow_caw_1": dict(file="4-188287-A-9.wav", t0=3.06, t1=3.82, hp=200, desc="single crow caw (slightly distant)"),
    "crow_caws": dict(file="4-188287-A-9.wav", t0=0.0, t1=3.85, hp=200, desc="crow 'kaa kaa kaa' series (6 caws)"),
    "crow_caw_2": dict(file="1-96950-B-9.wav", t0=4.06, t1=4.72, hp=200, desc="single caw, other crow"),
    "sparrows": dict(file="2-108761-A-14.wav", t0=0.0, t1=5.0, hp=1500, kind="loop", loop_s=20.0,
                     desc="morning small-bird chirps (sparrow-like 5-9 kHz), stereo loop"),
    "birds_morning": dict(file="3-155583-A-14.wav", t0=0.0, t1=5.0, hp=1000, kind="loop", loop_s=20.0,
                          desc="busier chirping birds bed, stereo loop"),
    # ---- footsteps (soft steps, isolated, quiet room)
    "footstep_1": dict(file="4-198962-A-25.wav", t0=0.23, t1=0.62, hp=60, gate=-45, desc="soft single step"),
    "footstep_2": dict(file="4-198962-A-25.wav", t0=1.66, t1=2.05, hp=60, gate=-45, desc="soft single step"),
    "footstep_3": dict(file="4-198962-A-25.wav", t0=2.34, t1=2.80, hp=60, gate=-45, desc="soft single step, firmer"),
    "footstep_4": dict(file="4-198962-A-25.wav", t0=2.915, t1=3.33, hp=60, gate=-45, desc="soft single step"),
    # ---- doors / water / weather
    "door_creak_1": dict(file="5-173568-A-33.wav", t0=0.0, t1=1.06, hp=100, desc="wooden door creak, rising pitch, 1 s"),
    "door_creak_2": dict(file="1-51805-B-33.wav", t0=0.38, t1=1.90, hp=100, desc="slow tonal door creak, 1.5 s"),
    "door_creak_3": dict(file="2-87780-A-33.wav", t0=0.0, t1=2.75, hp=80, desc="low wooden creak with knocks, 2.7 s"),
    "water_drop_1": dict(file="3-156907-A-15.wav", t0=0.335, t1=0.62, hp=150, gate=-45, desc="single water drop 'plink'"),
    "water_drop_2": dict(file="3-156907-A-15.wav", t0=1.305, t1=1.60, hp=150, gate=-45, desc="single water drop"),
    "water_drop_3": dict(file="3-156907-A-15.wav", t0=2.145, t1=2.47, hp=150, gate=-45, desc="single water drop"),
    "pouring_water": dict(file="3-161500-A-17.wav", t0=0.0, t1=5.0, hp=100, kind="loop", loop_s=20.0,
                          desc="steady splashing pour into water, stereo loop (stone channel bed)"),
    "rain_light": dict(file=["5-198321-A-10.wav", "4-164206-A-10.wav"], t0=0.0, t1=5.0, hp=120, kind="loop", loop_s=30.0,
                       desc="light steady rain, fine droplets, no thunder, stereo loop"),
    "rain_heavy": dict(file="1-50060-A-10.wav", t0=0.0, t1=5.0, hp=100, kind="loop", loop_s=30.0,
                       desc="heavier dense rain, no thunder, stereo loop"),
    "crickets_night": dict(file="5-215172-A-13.wav", t0=0.0, t1=5.0, hp=1500, kind="loop", loop_s=30.0,
                           desc="night crickets, steady ~7 kHz trill + 3 kHz pulses, stereo loop"),
    "crickets_night_b": dict(file="3-129678-A-13.wav", t0=0.0, t1=5.0, hp=1500, kind="loop", loop_s=30.0,
                             desc="night insects chorus (3.5 + 6.5 kHz bands), stereo loop"),
    "insects_buzz": dict(file="3-110913-B-7.wav", t0=0.0, t1=5.0, hp=100, desc="fly buzzing past (daytime insect)"),
    "church_bell_distant": dict(file="3-87936-B-46.wav", t0=0.0, t1=5.0, hp=150, lp=3500, distant=True,
                                desc="distant tolling bell (western), extra distance treatment; see temple_bell for a bonsho"),
    "train_distant": dict(file="2-262579-A-45.wav", t0=0.0, t1=5.0, hp=60, lp=2500, kind="pass", loop_s=14.0, distant=True,
                          desc="distant train passing: rumble swells in and out over 14 s"),
}


def _esc_meta():
    meta = {}
    with open(f"{ESC}/meta/esc50.csv") as f:
        for r in csv.DictReader(f):
            meta[r["filename"]] = r
    return meta


def _gate(x, thr_db, range_db=18.0, att=0.004, rel=0.08):
    """Soft downward expander: attenuates (up to range_db) parts below thr_db re. peak."""
    m = np.abs(mix.as_mono(x))
    pk = m.max() + 1e-12
    h = int(0.002 * SR)
    k = int(math.ceil(len(m) / h))
    mm = np.zeros(k * h)
    mm[:len(m)] = m
    env = 20 * np.log10(mm.reshape(k, h).max(axis=1) / pk + 1e-9)
    tgt = np.clip((env - thr_db) * 1.5, -range_db, 0.0)
    out = np.empty_like(tgt)
    g = tgt[0]
    ca, cr = math.exp(-h / (att * SR)), math.exp(-h / (rel * SR))
    for i, v in enumerate(tgt):
        c = ca if v > g else cr
        g = c * g + (1 - c) * v
        out[i] = g
    gl = 10 ** (np.interp(np.arange(len(m)), np.arange(k) * h + h / 2, out) / 20)
    return x * (gl if x.ndim == 1 else gl[:, None])


def esc_clip(name):
    """Render an ESC-50 pick (see ESC_PICKS) -> mono (one-shots) or stereo (loops)."""
    p = ESC_PICKS[name]
    files = p["file"] if isinstance(p["file"], list) else [p["file"]]
    segs = []
    for fn in files:
        x = mix.read_wav(os.path.join(ESC, "audio", fn), SR).astype(np.float64)
        x = x[int(p["t0"] * SR): int(p["t1"] * SR)]
        x = x - x.mean()
        if p.get("hp"):
            x = mix.highpass(x, p["hp"], SR, 4)
        if p.get("lp"):
            x = mix.lowpass(x, p["lp"], SR, 4)
        if p.get("gate") is not None:
            x = _gate(x, p["gate"])
        segs.append(np.asarray(x, dtype=np.float64))
    kind = p.get("kind", "oneshot")
    if kind == "oneshot":
        y = mix.fades(segs[0], 0.003, 0.04, SR)
        if p.get("distant"):
            y = distant(y, lp=p.get("lp", 5000), hp=p.get("hp", 80), wet=0.4, decay=2.2, predelay=50)
            y = mix.fade_out(y, 0.8, SR)
        return finish(y, "oneshot", 0.002, 0.03 if not p.get("distant") else 0.5)
    # loops: build a long bed by chaining crossfaded pieces from random offsets of the source(s)
    import zlib
    rng = _rng(zlib.crc32(name.encode()))
    L = p.get("loop_s", 20.0)
    xf = 0.6

    def chain(seed_off):
        r = _rng(seed_off)
        out = np.zeros(0)
        while len(out) < _n(L + 2 * xf + 0.1):
            s = segs[r.integers(len(segs))]
            ln = int(r.uniform(0.55, 0.95) * len(s))
            a = int(r.integers(0, max(1, len(s) - ln)))
            piece = s[a:a + ln]
            out = piece.copy() if len(out) == 0 else mix.crossfade_concat(out, piece, xf, SR, power=True)
        return out

    left = chain(rng.integers(1 << 30))
    right = chain(rng.integers(1 << 30))
    n = min(len(left), len(right))
    st = np.stack([left[:n], right[:n]], axis=1)
    # keep some centre image: mix 25 % of each side into the other
    st = np.stack([st[:, 0] * 0.87 + st[:, 1] * 0.5 * 0.5, st[:, 1] * 0.87 + st[:, 0] * 0.5 * 0.5], axis=1)
    if kind == "pass":
        st = st[: _n(L)]
        t = np.linspace(0, 1, len(st))
        env = np.sin(np.pi * np.clip(t, 0, 1)) ** 1.6
        st *= env[:, None]
        if p.get("distant"):
            st = distant(st, lp=p.get("lp", 3000), hp=p.get("hp", 60), wet=0.35, decay=2.0, predelay=40, keep_tail=False)
        return finish(st, "oneshot", 0.05, 0.3, trim=False)
    loop = mix.make_loopable(st[: _n(L) + _n(xf)], xf, SR)
    return finish(loop, "loop", 0.0, 0.0, trim=False)


# ============================================================================ synthesis: insects


def _moving_band(n, fc, bw, rng):
    """Noise band that follows fc(t) (array): low-passed noise ring-modulated to fc."""
    base = mix.lowpass(rng.standard_normal(n), bw / 2, SR, 4)
    base2 = mix.lowpass(rng.standard_normal(n), bw / 2, SR, 4)
    ph = 2 * np.pi * np.cumsum(fc) / SR
    return base * np.cos(ph) + base2 * np.sin(ph)


def _syllable_track(total, sylls, rng, pulse_rate=160.0):
    """sylls: list of dict(t, d, f0, f1, amp, noise, att, rel, swell). Returns mono signal."""
    n = _n(total)
    fc = np.full(n, 6000.0)
    amp = np.zeros(n)
    noise_mix = np.zeros(n)
    for s in sylls:
        a, b = _n(s["t"]), min(n, _n(s["t"] + s["d"]))
        if b <= a:
            continue
        k = b - a
        u = np.linspace(0, 1, k)
        fc[a:b] = s["f0"] + (s["f1"] - s["f0"]) * (u ** s.get("curve", 1.0))
        e = np.ones(k)
        na, nr = max(1, _n(s.get("att", 0.008))), max(1, _n(s.get("rel", 0.015)))
        e[:na] *= np.linspace(0, 1, na)
        e[-nr:] *= np.linspace(1, 0, nr)
        if s.get("swell"):
            e *= (0.35 + 0.65 * np.sin(np.pi * u) ** s["swell"])
        amp[a:b] = np.maximum(amp[a:b], e * s["amp"])
        noise_mix[a:b] = s.get("noise", 0.5)
    # tymbal pulse modulation (buzz) with slight rate jitter
    pr = pulse_rate * (1 + 0.05 * smooth_rand(n, 3, rng))
    ph = np.cumsum(pr) / SR
    tym = (0.5 + 0.5 * np.cos(2 * np.pi * ph)) ** 3
    band = _moving_band(n, fc, 1400.0, rng)
    band /= np.std(band) + 1e-9
    tone = np.sin(2 * np.pi * np.cumsum(fc) / SR) + 0.25 * np.sin(2 * np.pi * np.cumsum(fc * 1.52) / SR)
    carrier = noise_mix * band + (1 - noise_mix) * tone
    return carrier * tym * amp


def cicada_tsukutsuku(seed=0, dist=1.0):
    """Tsukutsukuboushi (Meimuna opalifera): intro buzz, accelerating 'tsuku-tsuku-boushi'
    motifs, 'ui-oos' ending and fading buzz. ~9.5 s, band 5-8 kHz, distant."""
    rng = _rng(seed)
    sy = []
    t = 0.15
    sy.append(dict(t=t, d=1.25, f0=5800, f1=6300, amp=0.55, noise=0.65, att=0.35, rel=0.05, swell=0.5))
    t += 1.35
    nm = 9 + int(rng.integers(0, 3))
    for i in range(nm):
        P = 0.92 - 0.30 * (i / (nm - 1)) ** 0.8  # accelerating
        s = P / 0.92
        a = 0.75 + 0.25 * min(1, i / 3)
        sy += [
            dict(t=t + 0.00 * s, d=0.055 * s, f0=7300, f1=7100, amp=a * 0.8, noise=0.45),
            dict(t=t + 0.085 * s, d=0.06 * s, f0=6500, f1=6300, amp=a * 0.7, noise=0.45),
            dict(t=t + 0.18 * s, d=0.055 * s, f0=7300, f1=7100, amp=a * 0.8, noise=0.45),
            dict(t=t + 0.265 * s, d=0.06 * s, f0=6500, f1=6300, amp=a * 0.7, noise=0.45),
            dict(t=t + 0.37 * s, d=0.25 * s, f0=5400, f1=6900, amp=a, noise=0.35, att=0.03, rel=0.03, swell=1.0, curve=0.7),
            dict(t=t + 0.64 * s, d=0.13 * s, f0=7700, f1=7400, amp=a * 0.75, noise=0.7, att=0.01, rel=0.05),
        ]
        t += P
    for k in range(2):  # 'ui-oos'
        sy.append(dict(t=t, d=0.42, f0=7200, f1=5600, amp=0.8 - 0.15 * k, noise=0.4, att=0.03, rel=0.08, swell=0.8))
        t += 0.5
    sy.append(dict(t=t, d=1.1, f0=6200, f1=5700, amp=0.45, noise=0.7, att=0.05, rel=0.9))
    total = t + 1.4
    x = _syllable_track(total, sy, rng, pulse_rate=150 + 20 * rng.random())
    x = mix.bandpass(x, 3800, 9500, SR, 2)
    y = distant(x, lp=9000 - 2500 * dist, hp=2500, wet=0.15 + 0.15 * dist, decay=1.0, predelay=20 + 30 * dist)
    return finish(y, "oneshot", 0.01, 0.4)


def higurashi(seed=0, dur=6.5, dist=1.0):
    """Higurashi (Tanna japonensis) evening 'kana-kana-kana': pulsed tonal call ~5.4 -> 4.6 kHz,
    pulse rate slowing 11 -> 7 Hz, swell then fade. Melancholy, distant forest reverb."""
    rng = _rng(seed)
    f_hi = 5450 + rng.uniform(-150, 150)
    f_lo = 4550 + rng.uniform(-100, 100)
    t = 0.05
    sy = []
    while t < dur - 0.2:
        u = t / dur
        rate = 11.0 - 4.0 * u
        per = 1.0 / rate
        f = f_hi + (f_lo - f_hi) * u ** 0.8
        env = min(1.0, t / 0.9) * (1 - max(0.0, (u - 0.45) / 0.55)) ** 1.3
        env *= 0.85 + 0.15 * rng.random()
        sy.append(dict(t=t, d=per * 0.45, f0=f * 1.03, f1=f * 0.96, amp=env, noise=0.15, att=0.005, rel=0.025, swell=0.8))
        t += per * (1 + 0.03 * rng.standard_normal())
    x = _syllable_track(dur + 0.3, sy, rng, pulse_rate=260)
    x = mix.bandpass(x, 3000, 8000, SR, 2)
    y = distant(x, lp=8000 - 2000 * dist, hp=2000, wet=0.2 + 0.12 * dist, decay=1.8, predelay=30 + 30 * dist)
    return finish(y, "oneshot", 0.01, 0.6)


def suzumushi(seed=0, dur=10.0, n_chirps=None):
    """Bell cricket 'riiin': ~4.3 kHz chirps of 0.3-0.5 s (fast pulse roughness), every ~1-1.6 s."""
    rng = _rng(seed)
    n = _n(dur)
    x = np.zeros(n)
    t = 0.2 + rng.uniform(0, 0.3)
    f = 4300 + rng.uniform(-150, 150)
    while t < dur - 0.6:
        d = rng.uniform(0.28, 0.5)
        tt = np.arange(_n(d)) / SR
        fr = f * (1 + 0.012 * np.minimum(1, tt / 0.05)) * (1 - 0.004 * tt / d)
        ph = 2 * np.pi * np.cumsum(fr) / SR
        pul = (0.55 + 0.45 * np.cos(2 * np.pi * 42 * tt)) ** 2
        e = np.minimum(1, tt / 0.012) * np.exp(-tt / (d * 1.6)) * np.minimum(1, (d - tt) / 0.03)
        s = (np.sin(ph) + 0.12 * np.sin(2 * ph)) * pul * e * rng.uniform(0.7, 1.0)
        a = _n(t)
        x[a:a + len(s)] += s[: n - a]
        t += d + rng.uniform(0.6, 1.2)
    y = distant(x, lp=9000, hp=1500, wet=0.3, decay=1.2, predelay=15)
    return finish(y, "oneshot", 0.01, 0.4)


# ============================================================================ synthesis: robot


def _beep_note(dur, f_start, f_end, amp=1.0, att=0.012, rel=0.04, glide="exp", warble=12.0,
               wrate=7.0, tri=0.3, seed=0, bend_end=0.0):
    tt = np.arange(_n(dur)) / SR
    u = tt / max(dur, 1e-6)
    if glide == "exp":
        f = f_start * (f_end / f_start) ** u
    elif glide == "late":
        f = f_start * (f_end / f_start) ** (u ** 3)
    elif glide == "early":
        f = f_start * (f_end / f_start) ** (1 - (1 - u) ** 3)
    else:
        f = f_start + (f_end - f_start) * u
    if bend_end:
        f = f * 2 ** (bend_end / 12 * np.clip((u - 0.6) / 0.4, 0, 1) ** 2)
    f = f * 2 ** (warble / 1200 * np.sin(2 * np.pi * wrate * tt + seed))
    ph = 2 * np.pi * np.cumsum(f) / SR
    w = (1 - tri) * np.sin(ph) + tri * (np.sin(ph) - np.sin(3 * ph) / 9 + np.sin(5 * ph) / 25) * 0.9
    na, nr = max(1, _n(att)), max(1, _n(rel))
    e = np.ones(len(tt))
    e[:na] *= np.sin(np.linspace(0, np.pi / 2, na)) ** 2
    e[-nr:] *= np.cos(np.linspace(0, np.pi / 2, nr)) ** 2
    return w * e * amp


def _speaker(x):
    """Small robot speaker: band-limit 350 Hz..5 kHz, gentle presence bump, soft saturation."""
    y = mix.highpass(x, 350, SR, 2)
    y = mix.lowpass(y, 5200, SR, 3)
    y = mix.peaking_eq(y, 1800, 2.5, 0.9, SR)
    y = np.tanh(1.4 * y / (np.abs(y).max() + 1e-9)) / np.tanh(1.4)
    return y


def _seq(parts, tail=0.08):
    """parts: list of (t_start, array). Returns mono sum."""
    end = max(t + len(a) / SR for t, a in parts) + tail
    out = np.zeros(_n(end))
    for t, a in parts:
        i = _n(t)
        out[i:i + len(a)] += a[: len(out) - i]
    return out


ROBOT_BEEPS = {
    "query": "rising two-note question",
    "yes": "bright two-note up",
    "no": "two-note down, soft",
    "sad": "slow falling glide",
    "curious": "rise - dip - rise with a tiny trill",
    "happy": "little trill ending high",
    "tired": "slow falling wobble",
    "startle": "quick upward chirp + blip",
    "lowbat": "three soft descending blips",
    "powerup": "four rising ticks + soft chime (~1.5 s)",
    "powerdown": "descending glide that fades (~2 s)",
    "hello": "three-note greeting",
}


def robot_beep(kind="query", seed=0):
    """Gentle robot vocabulary (see ROBOT_BEEPS). Sine/triangle, soft attack, FM warble,
    speaker band-limit. Returns mono."""
    r = _rng(seed)
    j = 2 ** (r.uniform(-0.3, 0.3) / 12)  # tiny per-seed transposition for variations
    B = lambda *a, **k: _beep_note(*a, seed=seed, **k)  # noqa: E731
    if kind == "query":
        x = _seq([(0, B(0.10, 880 * j, 880 * j, 0.8)), (0.13, B(0.20, 1175 * j, 1175 * j, 1.0, bend_end=2.5, glide="lin"))])
    elif kind == "yes":
        x = _seq([(0, B(0.075, 1047 * j, 1047 * j, 0.8, att=0.006)), (0.095, B(0.14, 1568 * j, 1568 * j, 1.0, att=0.006, rel=0.07))])
    elif kind == "no":
        x = _seq([(0, B(0.12, 988 * j, 988 * j, 0.9)), (0.16, B(0.2, 740 * j, 700 * j, 0.8, rel=0.09))])
    elif kind == "sad":
        x = _seq([(0, B(0.75, 988 * j, 587 * j, 0.9, att=0.03, rel=0.25, glide="late", warble=20, wrate=5.0))])
    elif kind == "curious":
        x = _seq([(0, B(0.16, 784 * j, 1100 * j, 0.8, glide="early")), (0.18, B(0.12, 1047 * j, 932 * j, 0.7)),
                  (0.32, B(0.22, 988 * j, 1319 * j, 0.9, glide="late", warble=35, wrate=16))])
    elif kind == "happy":
        notes = [1319, 1568, 1319, 1568, 1760, 2093]
        parts = [(i * 0.055, B(0.05 if i < 5 else 0.16, f * j, f * j, 0.75 + 0.05 * i, att=0.004, rel=0.02 if i < 5 else 0.08)) for i, f in enumerate(notes)]
        x = _seq(parts)
    elif kind == "tired":
        x = _seq([(0, B(1.15, 700 * j, 400 * j, 0.9, att=0.05, rel=0.35, glide="lin", warble=45, wrate=4.5, tri=0.15))])
        x *= np.linspace(1.0, 0.6, len(x))
    elif kind == "startle":
        x = _seq([(0, B(0.07, 600 * j, 1900 * j, 1.0, att=0.003, rel=0.02, glide="exp")), (0.09, B(0.06, 2100 * j, 2100 * j, 0.7, att=0.003))])
    elif kind == "lowbat":
        x = _seq([(0, B(0.12, 880 * j, 870 * j, 0.7)), (0.21, B(0.12, 740 * j, 730 * j, 0.6)), (0.42, B(0.18, 587 * j, 570 * j, 0.5, rel=0.1))])
        x = mix.lowpass(x, 2500, SR, 2)
    elif kind == "powerup":
        parts = [(i * 0.17, B(0.03, f * j, f * j, 0.6 + 0.08 * i, att=0.002, rel=0.015, tri=0.5)) for i, f in enumerate([523, 659, 784, 1047])]
        tt = np.arange(_n(0.85)) / SR
        ch = (np.sin(2 * np.pi * 2093 * j * tt) + 0.35 * np.sin(2 * np.pi * 3136 * j * tt) + 0.15 * np.sin(2 * np.pi * 4186 * j * tt))
        ch *= np.minimum(1, tt / 0.004) * np.exp(-tt / 0.25) * 0.8
        parts.append((0.68, ch))
        x = _seq(parts)
    elif kind == "powerdown":
        tt = np.arange(_n(2.0)) / SR
        f = 1200 * j * (150 / 1200) ** ((tt / 2.0) ** 0.8)
        ph = 2 * np.pi * np.cumsum(f * 2 ** (10 / 1200 * np.sin(2 * np.pi * 6 * tt))) / SR
        w = np.sin(ph) + 0.25 * np.sin(2 * ph)
        e = np.minimum(1, tt / 0.02) * (1 - tt / 2.0) ** 1.5
        x = mix.lowpass(w * e, 3000, SR, 2)
    elif kind == "hello":
        x = _seq([(0, B(0.09, 784 * j, 784 * j, 0.8)), (0.11, B(0.09, 1047 * j, 1047 * j, 0.85)),
                  (0.22, B(0.2, 1319 * j, 1397 * j, 1.0, rel=0.1, warble=20))])
    else:
        raise KeyError(kind)
    y = _speaker(x)
    return finish(y, "oneshot", 0.003, 0.02)


def servo(dur=0.3, f0=380.0, f1=620.0, seed=0, wobble=0.0):
    """Small servo whine: gear harmonics following a pitch glide, band-limited, quiet ticks."""
    r = _rng(seed)
    tt = np.arange(_n(dur)) / SR
    u = tt / dur
    f = f0 + (f1 - f0) * (0.5 - 0.5 * np.cos(np.pi * u))
    if wobble:
        f *= 1 + wobble * np.sin(2 * np.pi * 3.0 * tt)
    f *= 1 + 0.01 * smooth_rand(len(tt), 30, r)
    ph = 2 * np.pi * np.cumsum(f) / SR
    w = sum((1.0 / k) * np.sin(k * ph + r.uniform(0, 6)) for k in range(1, 9))
    w += 0.25 * np.sin(11 * ph) + 0.15 * np.sin(17 * ph)
    w += 0.2 * band_noise(len(tt), 1500, 6000, r)
    e = np.minimum(1, tt / 0.02) * np.minimum(1, (dur - tt) / 0.035)
    x = w * e
    x = mix.bandpass(x, 300, 6500, SR, 2)
    ticks = impulses(dur, [0.004, dur - 0.012], [0.8, 0.5], 0.25)
    ticks = resonator_bank(ticks, [2400, 3700, 5200], [0.02, 0.015, 0.01], [1, 0.6, 0.4])
    x = x / (np.abs(x).max() + 1e-9) + 0.5 * ticks / (np.abs(ticks).max() + 1e-9)
    return finish(x, "oneshot", 0.002, 0.01, target=-24.0)


def motor_roll(duration=4.0, speed=1.0, seed=0, gravel=1.0, seams=1.0, loop=False):
    """Small electric motor + rubber wheels on stone.
    speed: float 0..1, array (resampled over the duration), or callable f(t_seconds)->0..1.
    Motor hum pitch follows speed (70 -> 300 Hz fundamental + harmonics + faint controller
    whine), wheel texture and paving-seam bumps scale with speed. Returns mono.
    loop=True (constant speed only): returns a seamless loop of `duration` seconds."""
    r = _rng(seed)
    xf = 0.5
    if loop:
        duration = duration + xf
    n = _n(duration)
    tt = np.arange(n) / SR
    if callable(speed):
        s = np.array([float(speed(t)) for t in tt[:: 480]])
        s = np.interp(tt, tt[:: 480], s)
    elif np.ndim(speed) == 0 and loop:
        s = np.full(n, float(speed))
    elif np.ndim(speed) == 0:
        s = np.full(n, float(speed))
        ramp = min(n // 4, _n(0.25))
        s[:ramp] *= np.linspace(0, 1, ramp)
        s[-ramp:] *= np.linspace(1, 0, ramp)
    else:
        sp = np.asarray(speed, dtype=float)
        s = np.interp(tt, np.linspace(0, duration, len(sp)), sp)
    s = np.clip(s, 0, 1.5)
    s = mix.lowpass(s, 8, SR, 1)
    fm = 70 + 230 * s
    ph = 2 * np.pi * np.cumsum(fm) / SR
    amps = [1, 0.55, 0.35, 0.22, 0.12, 0.08]
    hum = sum(a * np.sin((k + 1) * ph + r.uniform(0, 6)) for k, a in enumerate(amps))
    hum *= (1 + 0.08 * smooth_rand(n, 12, r))
    whine = 0.05 * np.sin(2 * np.pi * np.cumsum(1900 + 1400 * s) / SR)
    motor = (hum + whine) * (s / (s.max() + 1e-9)) ** 0.8
    wheel = mix.lowpass(r.standard_normal(n), 900, SR, 2) * 0.6
    wheel *= s * (1 + 0.3 * smooth_rand(n, 20, r))
    # gravel: sparse tiny ticks
    rate = 45 * s * gravel
    p = rate / SR
    hits = r.random(n) < p
    g = np.zeros(n)
    g[hits] = r.lognormal(-1, 0.6, hits.sum())
    g = resonator_bank(g, [1300, 2200, 3400], [0.012, 0.01, 0.008], [1, 0.8, 0.5]) * 0.5
    # seams: soft bumps
    sp = np.cumsum(2.2 * s / SR) * seams
    seam_idx = np.where(np.diff(np.floor(sp)) > 0)[0]
    bump = np.zeros(n)
    bump[seam_idx] = r.uniform(0.6, 1.0, len(seam_idx)) * s[seam_idx]
    bump = resonator_bank(bump, [110, 180, 420], [0.06, 0.05, 0.03], [1, 0.6, 0.3]) * 2.0
    x = 0.55 * motor / (np.abs(motor).max() + 1e-9) + 0.35 * wheel / (np.abs(wheel).max() + 1e-9) \
        + 0.25 * g / (np.abs(g).max() + 1e-9) + 0.4 * bump / (np.abs(bump).max() + 1e-9)
    x = mix.lowpass(mix.highpass(x, 45, SR, 2), 8000, SR, 2)
    if loop:
        return finish(mix.make_loopable(x, xf, SR), "loop", 0.0, 0.0, target=-24.0, trim=False)
    return finish(x, "loop", 0.02, 0.05, target=-24.0, trim=False)


# ============================================================================ synthesis: bells


def bike_bell_clack(seed=0, double=None):
    """The broken bell: dull muted metallic tick, no ring (heavily damped dome modes + click)."""
    r = _rng(seed)
    double = bool(r.random() < 0.5) if double is None else double
    times = [0.005] + ([0.005 + r.uniform(0.045, 0.07)] if double else [])
    amps = [1.0] + ([0.45] if double else [])
    dur = 0.3
    ex = impulses(dur, times, amps, 0.4)
    k = r.uniform(0.97, 1.03)
    modes = resonator_bank(ex, [1150 * k, 2480 * k, 3620 * k, 5100 * k], [0.05, 0.035, 0.025, 0.015], [1, 0.7, 0.45, 0.25])
    click = mix.bandpass(impulses(dur, times, amps, 0.15) + 0.05 * r.standard_normal(_n(dur)) * np.exp(-np.arange(_n(dur)) / (0.004 * SR)), 1500, 7000, SR, 2)
    thud = resonator_bank(ex, [320 * k], [0.03], [0.6])
    x = modes / (np.abs(modes).max() + 1e-9) + 0.5 * click / (np.abs(click).max() + 1e-9) + 0.3 * thud / (np.abs(thud).max() + 1e-9)
    x = mix.lowpass(x, 6000, SR, 2)
    return finish(x, "oneshot", 0.0005, 0.02)


def bike_bell_ring(kind="ring", seed=0):
    """Clean, bright classic bicycle bell. kind: 'ding' (one strike), 'ring' (rotary trill of
    ~10 clapper strikes at ~21/s, then a ~1.3 s ring), 'double' (ring-ring).
    Modal synthesis: inharmonic doublet partials ~2.36 kHz and ~3.51 kHz (+ weak 5.2 / 6.7 kHz),
    slow beating from the doublets, stereo via two slightly different 'mic' mode weightings."""
    r = _rng(seed)
    if kind == "ding":
        strikes = [(0.01, 1.0)]
    else:
        n_s = 10
        base = [(0.01 + i / 21.0 + r.uniform(-0.003, 0.003), (0.78 + 0.22 * r.random()) * (1.0 if i else 0.9)) for i in range(n_s)]
        strikes = list(base)
        if kind == "double":
            strikes += [(t + 0.62, a * 0.95) for t, a in base]
    dur = strikes[-1][0] + 1.9
    ex = impulses(dur, [s[0] for s in strikes], [s[1] for s in strikes], 0.22)
    f = np.array([2362.0, 2366.8, 3508.0, 3515.5, 5185.0, 6730.0, 1178.0])
    t60 = np.array([1.75, 1.6, 1.3, 1.2, 0.6, 0.35, 0.9])
    gl = np.array([1.0, 0.75, 0.62, 0.5, 0.22, 0.10, 0.06])
    gr = gl * np.array([0.8, 0.95, 0.75, 0.62, 0.27, 0.12, 0.05])
    L = resonator_bank(ex, f, t60, gl)
    R = resonator_bank(ex, f * 1.0003, t60, gr)
    # tiny, clean clapper 'tink' transient
    tink = mix.bandpass(impulses(dur, [s[0] for s in strikes], [s[1] for s in strikes], 0.08), 4000, 12000, SR, 2)
    tink /= np.abs(tink).max() + 1e-9
    st = np.stack([L, R], axis=1)
    st /= np.abs(st).max() + 1e-9
    st += 0.05 * tink[:, None]
    st = mix.highpass(st, 300, SR, 2)
    return finish(st, "oneshot", 0.0005, 0.25, trim=False)


def temple_bell(seed=0, dist=1.0, f0=None, dur=12.0):
    """Bonsho: large bronze temple bell struck with a wooden log. Low hum ~70-90 Hz,
    inharmonic partials with doublet beating ('uwaaan'), 10-12 s decay, soft wooden 'gon'
    thump, distant low-passed reverberant treatment. Returns stereo."""
    r = _rng(seed)
    f0 = f0 or r.uniform(76, 86)
    ratios = np.array([1.0, 1.58, 2.10, 2.73, 3.36, 4.12, 4.95, 5.85, 6.9, 8.1, 9.4])
    amps = np.array([0.75, 1.0, 0.85, 0.6, 0.45, 0.33, 0.24, 0.16, 0.10, 0.07, 0.04])
    t60 = np.array([13, 11.5, 9.5, 7.5, 6.0, 5.0, 4.0, 3.2, 2.5, 2.0, 1.6]) * (dur / 12.0)
    split = np.array([0.35, 0.55, 0.8, 1.0, 1.3, 1.6, 1.9, 2.2, 2.6, 3.0, 3.3])
    ex = impulses(dur, [0.02], [1.0], 2.5)
    freqs, t6, gs = [], [], []
    for rt, a, t, sp in zip(ratios, amps, t60, split):
        fr = f0 * rt * r.uniform(0.995, 1.005)
        freqs += [fr, fr + sp]
        t6 += [t, t * 0.92]
        gs += [a, a * 0.8]
    x = resonator_bank(ex, freqs, t6, gs)
    x /= np.abs(x).max() + 1e-9
    thump = mix.bandpass(r.standard_normal(_n(0.12)) * np.exp(-np.arange(_n(0.12)) / (0.025 * SR)), 90, 700, SR, 2)
    thump = np.concatenate([np.zeros(_n(0.02)), thump, np.zeros(len(x) - len(thump) - _n(0.02))])
    x = x + 0.25 * thump / (np.abs(thump).max() + 1e-9)
    y = distant(x, lp=2600 - 900 * dist, hp=45, wet=0.3 + 0.2 * dist, decay=3.5, predelay=40 + 50 * dist)
    y = y[: _n(dur)]
    return finish(y, "oneshot", 0.002, 1.5, trim=False)


def fumikiri(dur=6.0, seed=0, dist=1.0):
    """Railway crossing bell 'kan-kan': two alternating electronic bell tones (~750/695 Hz),
    ~2 strikes per second, short metallic decay, distant street treatment. Stereo."""
    r = _rng(seed)
    per = 0.5 + r.uniform(-0.02, 0.02)
    times = np.arange(0.02, dur - 0.3, per)
    n = _n(dur)
    x = np.zeros(n)
    for i, t in enumerate(times):
        f = 752.0 if i % 2 == 0 else 694.0
        tt = np.arange(_n(0.45)) / SR
        w = (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(2 * np.pi * 3 * f * tt) + 0.18 * np.sin(2 * np.pi * 2.41 * f * tt)
             + 0.1 * np.sin(2 * np.pi * 5 * f * tt))
        e = np.minimum(1, tt / 0.002) * np.exp(-tt / 0.11) * (0.25 + 0.75 * np.exp(-tt / 0.03))
        a = _n(t)
        seg = (w * e)[: n - a]
        x[a:a + len(seg)] += seg
    x = mix.bandpass(x, 350, 4500, SR, 2)
    y = distant(x, lp=3500 - 800 * dist, hp=300, wet=0.35 + 0.15 * dist, decay=1.3, predelay=25 + 20 * dist, keep_tail=False)
    return finish(y, "oneshot", 0.01, 0.3, trim=False)


def shutter_roll(dur=3.0, seed=0, dist=1.0):
    """Shopkeeper rolling up a corrugated metal shutter: slat rattle whose rate and brightness
    rise, spring-drum rumble, final clunk; distant. Stereo."""
    r = _rng(seed)
    n = _n(dur)
    tt = np.arange(n) / SR
    u = tt / dur
    rate = 11 + 20 * u ** 0.7
    ph = np.cumsum(rate / SR)
    hit_idx = np.where(np.diff(np.floor(ph + r.uniform(0, 1))) > 0)[0]
    ex = np.zeros(n)
    ex[hit_idx] = r.uniform(0.4, 1.0, len(hit_idx)) * (0.6 + 0.4 * u[hit_idx])
    # add small secondary rattles
    for i in hit_idx:
        for k in range(r.integers(1, 3)):
            j = i + int(r.uniform(0.004, 0.02) * SR)
            if j < n:
                ex[j] += r.uniform(0.1, 0.35)
    x = np.zeros(n)
    grp = r.integers(0, 4, n)
    for gi in range(4):
        fr_ = np.sort(r.uniform(250, 5200, 7)) * (1 + 0.1 * gi)
        t6 = r.uniform(0.04, 0.16, 7)
        x += resonator_bank(np.where(grp == gi, ex, 0.0), fr_, t6, r.uniform(0.3, 1.0, 7))
    x += 0.15 * mix.highpass(ex * r.standard_normal(n), 2000, SR, 2)
    x /= np.abs(x).max() + 1e-9
    rumble = mix.bandpass(brown(n, r), 50, 350, SR, 2) * (0.4 + 0.6 * u)
    rumble /= np.abs(rumble).max() + 1e-9
    clunk = resonator_bank(impulses(dur, [dur - 0.18], [1.0], 6.0), [95, 160, 410, 760], [0.25, 0.2, 0.15, 0.1], [1, 0.8, 0.5, 0.3])
    clunk = mix.lowpass(clunk, 1500, SR, 2)
    clunk /= np.abs(clunk).max() + 1e-9
    y = 0.7 * x + 0.4 * rumble + 0.6 * clunk
    y *= np.minimum(1, tt / 0.15) * np.clip((dur - tt) / 0.12, 0, 1)
    y = distant(y, lp=5000 - 1500 * dist, hp=60, wet=0.3 + 0.15 * dist, decay=1.2, predelay=20 + 20 * dist)
    return finish(y, "oneshot", 0.01, 0.4, trim=False)


# ============================================================================ synthesis: household / small


def plastic_bag(dur=2.0, seed=0):
    """Plastic bag crinkle: bursty sparse crackles (lognormal amplitudes) through bright
    resonances plus a soft rustle bed. Mono."""
    r = _rng(seed)
    n = _n(dur)
    act = np.clip(0.55 + 0.6 * smooth_rand(n, 3.0, r), 0, 1.3) ** 2
    act *= np.minimum(1, np.arange(n) / _n(0.05)) * np.minimum(1, (n - np.arange(n)) / _n(0.12))
    p = 220 * act / SR
    hits = r.random(n) < p
    ex = np.zeros(n)
    ex[hits] = r.lognormal(-1.2, 0.9, hits.sum()) * np.sign(r.standard_normal(hits.sum()))
    ker = r.standard_normal(_n(0.003)) * np.exp(-np.arange(_n(0.003)) / (0.0008 * SR))
    cr = signal.fftconvolve(ex, ker)[:n]
    cr = mix.highpass(cr, 1200, SR, 2)
    cr = cr + 0.5 * resonator_bank(ex, [2900, 4700, 7300], [0.01, 0.008, 0.006], [0.3, 0.3, 0.2])
    rustle = band_noise(n, 2500, 11000, r) * act * 0.08
    x = cr / (np.abs(cr).max() + 1e-9) + rustle
    return finish(x, "oneshot", 0.005, 0.05)


def vending_hum(dur=10.0, seed=0):
    """Vending machine at night: 60 Hz mains (Kyoto) hum + 120 Hz transformer buzz, compressor
    motor rumble (57.5 Hz rotor beating against 60 Hz), faint fluorescent buzz. Seamless loop:
    every tonal frequency has an integer number of cycles in dur (10 s default). Stereo."""
    r = _rng(seed)
    n = _n(dur)
    tt = np.arange(n) / SR
    tone = (0.5 * np.sin(2 * np.pi * 60 * tt) + 1.0 * np.sin(2 * np.pi * 120 * tt + 0.3)
            + 0.35 * np.sin(2 * np.pi * 180 * tt + 1.1) + 0.45 * np.sin(2 * np.pi * 240 * tt + 2.0)
            + 0.15 * np.sin(2 * np.pi * 360 * tt) + 0.08 * np.sin(2 * np.pi * 480 * tt))
    rotor = 0.6 * np.sin(2 * np.pi * 57.5 * tt) + 0.25 * np.sin(2 * np.pi * 115 * tt)
    fl = sum((1 / k) * np.sin(2 * np.pi * 120 * k * tt + r.uniform(0, 6)) for k in range(3, 26, 2))
    fl = mix.highpass(fl, 1500, SR, 2) * 0.05
    xf = 1.0
    nz = brown(n + _n(xf), r)
    nz = mix.bandpass(nz, 40, 900, SR, 2)
    nz = mix.make_loopable(nz, xf, SR)[:n]
    nz *= 0.25 / (np.std(nz) + 1e-9) * 0.35
    hiss = mix.make_loopable(band_noise(n + _n(xf), 2000, 9000, r), xf, SR)[:n]
    hiss *= 0.02 / (np.std(hiss) + 1e-9) * 0.2
    x = tone * 0.45 + rotor * 0.35 + fl + nz + hiss
    st = np.stack([x, 0.92 * x + 0.08 * np.roll(nz, n // 3)], axis=1)
    pad = SR
    stp = np.concatenate([st[-pad:], st, st[:pad]])
    stp = mix.highpass(stp - stp.mean(0), 25, SR, 2)[pad:pad + n]
    return normalise(stp, "loop")


def _bubbles(n, rate, rng, fmin=400, fmax=3000, amp_scale=1.0):
    x = np.zeros(n)
    count = int(rate * n / SR)
    for _ in range(count):
        f = math.exp(rng.uniform(math.log(fmin), math.log(fmax)))
        tau = 0.012 * (1000 / f) ** 0.8 + 0.003
        L = int(6 * tau * SR)
        tt = np.arange(L) / SR
        fr = f * (1 + 0.12 * tt / tau)
        b = np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.exp(-tt / tau) * np.minimum(1, tt / 0.0005)
        a = rng.integers(0, max(1, n - L))
        x[a:a + L] += b * amp_scale * rng.lognormal(-0.5, 0.6) * (1000 / f) ** 0.4
    return x


def water_channel(dur=20.0, seed=0):
    """Gentle water trickling in a stone channel: ESC-50 pouring-water bed (low level) +
    synthesised bubbles/plinks + trickle noise. Seamless stereo loop."""
    r = _rng(seed)
    xf = 1.0
    n = _n(dur + xf)
    chans = []
    for ch in range(2):
        rr = _rng(seed * 10 + ch + 1)
        b = _bubbles(n, 55, rr, 450, 2800)
        b += 0.6 * _bubbles(n, 12, rr, 180, 500)
        tr = band_noise(n, 300, 3500, rr) * (0.6 + 0.4 * smooth_rand(n, 0.7, rr)) * 0.08
        chans.append(b / (np.abs(b).max() + 1e-9) * 0.7 + tr)
    x = np.stack(chans, axis=1)
    try:
        bed = esc_clip("pouring_water")
        bed = mix.loop_to(bed, (n) / SR, 0.5, SR, fade_edges=False)
        bed = mix.lowpass(bed, 5000, SR, 2)
        x = x + bed[:n] * (0.35 * np.std(x) / (np.std(bed) + 1e-9))
    except Exception as e:  # pragma: no cover
        print("water_channel: no ESC bed:", e, file=sys.stderr)
    x = mix.highpass(x, 120, SR, 2)
    import sampler
    x = sampler.reverb(x, wet=0.18, decay_s=0.6, predelay_ms=5, lowcut=200, highcut=8000, size=0.2, damping=0.5)
    loop = mix.make_loopable(x, xf, SR)
    return normalise(loop, "loop")


def wind_soft(dur=30.0, seed=0):
    """Soft wind: three noise bands with independent slow gusts, no whistle. Seamless stereo loop."""
    xf = 2.0
    n = _n(dur + xf)
    chans = []
    for ch in range(2):
        r = _rng(seed * 7 + ch)
        g = 0.6 + 0.4 * smooth_rand(n, 0.12, _rng(seed * 7 + 99))  # shared gust
        y = np.zeros(n)
        for lo, hi, lvl, rate in [(80, 300, 1.0, 0.2), (250, 900, 0.6, 0.3), (700, 2200, 0.25, 0.45)]:
            b = mix.bandpass(pink(n, r), lo, hi, SR, 2)
            b /= np.std(b) + 1e-9
            y += lvl * b * np.clip(g + 0.35 * smooth_rand(n, rate, r), 0.05, 2)
        chans.append(y)
    x = np.stack(chans, axis=1)
    x = mix.lowpass(mix.highpass(x, 60, SR, 2), 3500, SR, 2)
    return normalise(mix.make_loopable(x, xf, SR), "loop")


# ============================================================================ voice engine


def _rosenberg(phase, oq=0.65, sq=2.2):
    """Rosenberg glottal flow for phase in [0,1)."""
    tp = oq * sq / (1 + sq)
    tn = oq / (1 + sq)
    g = np.zeros_like(phase)
    a = phase < tp
    g[a] = 0.5 * (1 - np.cos(np.pi * phase[a] / tp))
    b = (phase >= tp) & (phase < tp + tn)
    g[b] = np.cos(np.pi * (phase[b] - tp) / (2 * tn))
    return g


def _glottal(f0, sr, oq=0.65, sq=2.2, rng=None, breath=0.0):
    """Differentiated glottal flow (radiation included) for an f0 array at rate sr,
    plus flow-modulated aspiration noise. Returns (excitation, flow)."""
    ph = np.cumsum(f0) / sr
    phase = ph - np.floor(ph)
    g = _rosenberg(phase, oq, sq)
    dg = np.diff(g, prepend=g[0]) * sr / np.maximum(f0, 1) * 0.1
    if np.any(np.asarray(breath) > 0) and rng is not None:
        nz = mix.highpass(rng.standard_normal(len(g)), 400, sr, 2)
        dg = dg + breath * nz * (0.25 + g)
    return dg, g


def hum_voice(notes, sr=SR, seed=3, breath=0.035, vib_rate=5.1, vib_cents=22.0, scoop_cents=80.0,
              legato_gap=0.09, tail=0.7, gain_db=0.0, murmur_hz=None, final_fall_cents=70.0,
              oq=0.58, murmur_bw=300.0, lp_hz=750.0):
    """Old woman's gentle closed-mouth humming ('mmm').

    notes: list of (midi_note, start_s, dur_s). Returns mono float32 at `sr` (48 kHz).
    Source: Rosenberg glottal pulses (soft phonation: open quotient .65) with jitter/shimmer,
    breathiness (flow-modulated aspiration), natural vibrato (~5 Hz, +-16 cents, delayed onset),
    pitch scoops into each note (from below, or legato glides), phrase-final pitch fall and fade.
    Filter: nasal murmur resonance (~280 Hz, raised towards f0 for high notes), antiformant
    ~1 kHz, weak nasal formants 1.35/2.3/3.0 kHz and a steep roll-off above ~1 kHz, so energy
    sits in the fundamental and first few harmonics. Loudness normalised to -18 LUFS (momentary
    max) + gain_db. For a natural older female voice keep notes around G3..A4 (190-440 Hz)."""
    rng = _rng(seed)
    notes = sorted([(float(m), float(s), float(d)) for m, s, d in notes], key=lambda z: z[1])
    if not notes:
        return np.zeros(0, np.float32)
    os_ = 2
    fs = sr * os_
    total = max(s + d for _, s, d in notes) + tail
    n = int(total * fs)
    t = np.arange(n) / fs
    m = np.full(n, np.nan)
    amp = np.zeros(n)
    brv = np.zeros(n)
    for i, (note, s, d) in enumerate(notes):
        prev = notes[i - 1] if i else None
        nxt = notes[i + 1] if i + 1 < len(notes) else None
        legato_in = prev is not None and s - (prev[1] + prev[2]) < legato_gap
        final = nxt is None or nxt[1] - (s + d) >= legato_gap
        a = int(s * fs)
        b = int((s + d) * fs) if not final else min(n, int((s + d + 0.12) * fs))
        k = b - a
        u = np.arange(k) / fs
        pitch = np.full(k, note)
        # onset: scoop from below or legato glide from previous pitch
        if legato_in:
            g = 0.085
            src = prev[0]
            w = np.clip(u / g, 0, 1)
            w = w * w * (3 - 2 * w)
            over = 0.08 * np.sign(note - src) * np.exp(-((u - g) / 0.05) ** 2) * (u > g * 0.7)
            pitch = src + (note - src) * w + over
        else:
            g = 0.13
            w = np.clip(u / g, 0, 1)
            pitch = note - scoop_cents / 100 * (1 - w) ** 2
        # vibrato (delayed onset)
        vr = vib_rate * (1 + 0.04 * rng.standard_normal())
        ve = np.clip((u - 0.18) / 0.3, 0, 1) * vib_cents / 100
        pitch = pitch + ve * np.sin(2 * np.pi * vr * u + rng.uniform(0, 6))
        # phrase-final fall
        e = np.ones(k)
        if final:
            fl = np.clip((u - 0.6 * d) / (0.4 * d + 0.12), 0, 1)
            pitch = pitch - final_fall_cents / 100 * fl ** 2
            e *= (1 - fl) ** 1.6
            brv[a:b] = np.maximum(brv[a:b], fl * 0.8)
        if not legato_in:
            att = np.clip(u / 0.09, 0, 1)
            e *= np.sin(att * np.pi / 2) ** 2
        else:
            e *= 1 - 0.12 * np.exp(-((u - 0.03) / 0.04) ** 2)
        # gentle intra-note swell
        e *= 0.9 + 0.1 * np.sin(np.pi * np.clip(u / max(d, 0.1), 0, 1))
        m[a:b] = pitch
        amp[a:b] = np.maximum(amp[a:b], e)
    # fill unvoiced gaps with held pitch (amplitude is zero there anyway)
    idx = np.where(~np.isnan(m))[0]
    m = np.interp(np.arange(n), idx, m[idx])
    # jitter / drift / shimmer
    m = m + 0.06 * smooth_rand(n, 1.5, rng, fs) + 0.035 * smooth_rand(n, 25, rng, fs)
    f0 = 440.0 * 2 ** ((m - 69) / 12)
    amp = amp * (1 + 0.05 * smooth_rand(n, 18, rng, fs))
    amp = mix.lowpass(amp, 40, fs, 1)
    amp = np.clip(amp, 0, None)
    exc, flow = _glottal(f0, fs, oq=oq, sq=2.4, rng=rng, breath=breath * (1 + 1.5 * brv))
    x = exc * amp
    med = float(np.median(f0[amp > 0.3])) if np.any(amp > 0.3) else 220.0
    fm = murmur_hz or float(np.clip(max(280.0, 0.95 * med), 250, 650))
    y = klatt_res(x, fm, murmur_bw or (110 + 0.15 * fm), fs)
    y = klatt_res(y, 1020, 200, fs, anti=True)
    # weak upper nasal formants (plain Klatt cascade: each resonator has unity gain at DC)
    y = klatt_res(y, 1350, 450, fs)
    y = klatt_res(y, 2300, 650, fs)
    y = klatt_res(y, 3000, 750, fs)
    if lp_hz:
        y = mix.lowpass(y, lp_hz, fs, 1, zero_phase=False)
    y = mix.highpass(y, 110, fs, 2)
    y = signal.resample_poly(y, 1, os_)
    y = mix.remove_dc(y, sr)
    y = mix.fades(y, 0.005, 0.1, sr)
    y = normalise(y, "oneshot", ONESHOT_LUFS + gain_db)
    return y.astype(np.float32)


def _voice_segmented(n, sr, f0, amp, segs, rng):
    """Babble voice: glottal source filtered by per-syllable vowel formants (overlap-add)."""
    exc, flow = _glottal(f0, sr, oq=0.6, sq=2.5, rng=rng, breath=0.03)
    out = np.zeros(n)
    for a, b, (F1, F2, F3) in segs:
        a0 = max(0, a - int(0.02 * sr))
        b0 = min(n, b + int(0.02 * sr))
        chunk = exc[a0:b0] * amp[a0:b0]
        y = klatt_res(chunk, F1, 90, sr)
        y = klatt_res(y, F2, 130, sr)
        y = klatt_res(y, F3, 200, sr)
        w = np.ones(b0 - a0)
        ramp = int(0.02 * sr)
        w[:ramp] = np.linspace(0, 1, ramp)[: len(w)]
        w[-ramp:] = np.minimum(w[-ramp:], np.linspace(1, 0, ramp))
        out[a0:b0] += y * w
    return out


def market_murmur(dur=30.0, n_voices=26, seed=0):
    """Wordless market crowd bed: many synthetic babbling voices (random formants, prosody,
    no phonology -> no intelligible words), each low-passed by distance, panned, reverberant,
    plus soft footstep/cart noise. Seamless stereo loop."""
    r = _rng(seed)
    vs = 16000
    xf = 2.0
    total = dur + xf
    n = int(total * vs)
    mixL = np.zeros(n)
    mixR = np.zeros(n)
    vowels = [(300, 870, 2240), (400, 2000, 2550), (530, 1840, 2480), (660, 1720, 2410), (730, 1090, 2440),
              (570, 840, 2410), (440, 1020, 2240), (300, 2300, 3000), (490, 1350, 1690), (640, 1190, 2390)]
    for v in range(n_voices):
        female = r.random() < 0.5
        base = r.uniform(175, 250) if female else r.uniform(95, 140)
        f0 = np.full(n, base)
        amp = np.zeros(n)
        segs = []
        t = r.uniform(0, 2.0)
        while t < total:
            plen = r.uniform(1.2, 3.5)
            pe = min(total, t + plen)
            a0 = int(t * vs)
            b0 = int(pe * vs)
            if b0 <= a0:
                break
            u = np.linspace(0, 1, b0 - a0)
            f0[a0:b0] = base * (1.12 - 0.22 * u) * (1 + 0.06 * np.sin(2 * np.pi * r.uniform(1.5, 3) * u * plen))
            st = t
            while st < pe:
                sd = r.uniform(0.12, 0.28)
                a = int(st * vs)
                b = min(int((st + sd) * vs), b0)
                if b - a > 40:
                    segs.append((a, b, vowels[r.integers(len(vowels))]))
                    k = b - a
                    w = np.sin(np.pi * np.linspace(0, 1, k)) ** 0.8
                    amp[a:b] = np.maximum(amp[a:b], w * r.uniform(0.5, 1.0))
                st += sd + r.uniform(0.02, 0.08)
            t = pe + r.uniform(0.3, 1.6)
        vo = _voice_segmented(n, vs, f0, amp, segs, r)
        cons = mix.bandpass(r.standard_normal(n), 2500, 6000, vs, 2) * (np.abs(np.diff(amp, prepend=0)) * vs > 3) * 0.02
        vo = vo + cons
        dist = r.uniform(0.2, 1.0)
        vo = mix.lowpass(vo, 3200 - 2000 * dist, vs, 2)
        vo *= 10 ** (-(dist * 12) / 20) / (np.std(vo) + 1e-9)
        pan = r.uniform(-0.9, 0.9)
        gl, gr = mix.pan_gains(pan)
        mixL += vo * gl
        mixR += vo * gr
    st = np.stack([mixL, mixR], axis=1)
    st = signal.resample_poly(st, SR // 1000, vs // 1000, axis=0)
    import sampler
    st = sampler.reverb(st, wet=0.45, **sampler.PRESETS["street"])
    # soft shuffles / cart wheels bed
    rr = _rng(seed + 1)
    bed = mix.bandpass(pink(len(st), rr), 150, 1500, SR, 2) * 0.12 * np.std(st)
    st = st + np.stack([bed, np.roll(bed, SR // 3)], axis=1)
    st = mix.lowpass(mix.highpass(st, 120, SR, 2), 3500, SR, 2)
    return normalise(mix.make_loopable(st, xf, SR), "loop")


def dog_growl(dur=1.6, seed=0):
    """Soft low growl (small dog): rough low voice (f0 ~120 Hz, strong jitter + 25 Hz flutter),
    throat formants ~500/1400 Hz. Synthesised (no clean growl in ESC-50)."""
    r = _rng(seed)
    fs = SR * 2
    n = int(dur * fs)
    t = np.arange(n) / fs
    f0 = 120 * (1 + 0.08 * smooth_rand(n, 3, r, fs) + 0.05 * smooth_rand(n, 40, r, fs))
    exc, flow = _glottal(f0, fs, oq=0.5, sq=3.0, rng=r, breath=0.15)
    flutter = 0.6 + 0.4 * np.abs(np.sin(2 * np.pi * 24 * t + 2 * smooth_rand(n, 5, r, fs)))
    env = np.minimum(1, t / 0.15) * np.minimum(1, (dur - t) / 0.25) * (0.8 + 0.2 * smooth_rand(n, 2, r, fs))
    x = exc * flutter * env
    y = klatt_res(x, 520, 180, fs)
    y = klatt_res(y, 1400, 300, fs) * 0.6 + 0.4 * y
    y = klatt_res(y, 2600, 500, fs) * 0.4 + 0.6 * y
    y = mix.lowpass(mix.highpass(y, 80, fs, 2), 3500, fs, 2)
    y = signal.resample_poly(y, 1, 2)
    return finish(y, "oneshot", 0.01, 0.1)


def cat_mrrp(seed=0):
    """Cat 'mrrp' greeting trill: short voiced sound (f0 ~420 -> 620 Hz) with ~28 Hz rolling
    amplitude flutter, closed-mouth nasal formants opening at the end. ~0.35 s. Synthesised."""
    r = _rng(seed)
    fs = SR * 2
    dur = r.uniform(0.3, 0.42)
    n = int(dur * fs)
    t = np.arange(n) / fs
    u = t / dur
    f0 = (420 + 200 * u ** 1.5) * (1 + 0.02 * smooth_rand(n, 20, r, fs)) * r.uniform(0.92, 1.08)
    exc, _ = _glottal(f0, fs, oq=0.55, sq=2.5, rng=r, breath=0.05)
    trill = 0.35 + 0.65 * (0.5 + 0.5 * np.cos(2 * np.pi * 28 * t)) ** 1.5
    trill = np.where(u < 0.7, trill, 1.0)
    env = np.sin(np.pi * np.clip(u, 0, 1)) ** 0.6
    x = exc * trill * env
    # mouth opens at the end: crossfade between closed (F1 520) and open (F1 850) filterings
    w = np.clip((u - 0.5) / 0.35, 0, 1)
    w = w * w * (3 - 2 * w)
    ys = []
    for f1 in (520, 850):
        seg = klatt_res(x, f1, 150, fs)
        seg = klatt_res(seg, 1700, 300, fs)
        seg = klatt_res(seg, 3300, 500, fs)
        ys.append(seg)
    y = (1 - w) * ys[0] + w * ys[1]
    y = mix.highpass(y, 250, fs, 2)
    y = signal.resample_poly(y, 1, 2)
    return finish(y, "oneshot", 0.005, 0.04)


def cat_hiss(seed=0, dur=0.9):
    """Cat hiss: fast attack, breathy noise with 2.5-7 kHz emphasis, slight spit onset."""
    r = _rng(seed)
    n = _n(dur)
    t = np.arange(n) / SR
    nz = r.standard_normal(n)
    y = klatt_res(nz, 3200, 900) + 0.7 * klatt_res(nz, 5600, 1400) + 0.3 * klatt_res(nz, 1600, 500)
    env = np.minimum(1, t / 0.015) * np.exp(-t / (dur * 0.9)) * (1 + 0.15 * smooth_rand(n, 12, r))
    spit = impulses(dur, [0.008], [3.0], 0.5)
    y = y * env + mix.highpass(spit, 1500, SR, 2)
    y = mix.highpass(y, 900, SR, 2)
    return finish(y, "oneshot", 0.002, 0.08)


# ============================================================================ synthesis: foley


def slipper_step(seed=0, weight=0.6):
    """Soft slipper on stone: soft sole slap (short 300 Hz-4 kHz burst), low pat, and a light
    short scuff; darker than shoes, no heel click."""
    r = _rng(seed)
    dur = 0.4
    n = _n(dur)
    t = np.arange(n) / SR
    t0 = 0.004
    pat = resonator_bank(impulses(dur, [t0], [1.0], 4.0), [95, 170, 330], [0.06, 0.05, 0.035], [1, 0.7, 0.35])
    pat /= np.abs(pat).max() + 1e-9
    slap_env = np.where(t >= t0, np.exp(-(t - t0) / r.uniform(0.006, 0.01)), 0.0)
    slap = mix.bandpass(r.standard_normal(n), 300, 4000, SR, 2) * slap_env
    slap /= np.abs(slap).max() + 1e-9
    sc_t0 = t0 + r.uniform(0.005, 0.03)
    sc_d = r.uniform(0.04, 0.08)
    sc_env = np.exp(-((t - sc_t0 - sc_d / 2) / (sc_d / 2.5)) ** 2)
    scuff = band_noise(n, 800, 5000, r) * sc_env
    scuff /= np.abs(scuff).max() + 1e-9
    x = weight * pat + 0.8 * slap + 0.25 * scuff * r.uniform(0.5, 1.0)
    x = mix.lowpass(x, 6000, SR, 2)
    return finish(x, "oneshot", 0.001, 0.03)


def puddle_splash(seed=0):
    """Soft 'puff' splash of a wheel through a puddle: low thump, splash burst, droplets falling back."""
    r = _rng(seed)
    dur = 1.0
    n = _n(dur)
    t = np.arange(n) / SR
    thump = resonator_bank(impulses(dur, [0.01], [1.0], 4.0), [85, 150], [0.08, 0.06], [1, 0.5])
    thump /= np.abs(thump).max() + 1e-9
    burst = band_noise(n, 500, 7000, r) * np.minimum(1, t / 0.006) * np.exp(-t / 0.09)
    burst /= np.abs(burst).max() + 1e-9
    drops = _bubbles(n, 0, r)
    for _ in range(int(r.integers(12, 22))):
        tt0 = r.uniform(0.08, 0.6)
        f = r.uniform(900, 3500)
        L = _n(0.03)
        tt = np.arange(L) / SR
        d = np.sin(2 * np.pi * f * (1 + 2 * tt) * tt) * np.exp(-tt / 0.006) * r.uniform(0.2, 0.6)
        a = _n(tt0)
        drops[a:a + L] += d[: n - a]
    drops /= np.abs(drops).max() + 1e-9
    x = 0.8 * thump + 0.7 * burst + 0.35 * drops
    x = mix.lowpass(x, 9000, SR, 2)
    return finish(x, "oneshot", 0.001, 0.1)


def metal_clatter(seed=0):
    """Small bell (broken bicycle bell) dropped on stone: 4-6 bounces with shrinking gaps,
    damped metal modes + stone clicks, final little rattle."""
    r = _rng(seed)
    gaps = [0.23, 0.15, 0.10, 0.065, 0.04, 0.028]
    times = [0.02]
    for g in gaps[: r.integers(4, 7)]:
        times.append(times[-1] + g * r.uniform(0.85, 1.15))
    amps = [1.0 * 0.62 ** i * r.uniform(0.8, 1.1) for i in range(len(times))]
    dur = times[-1] + 0.6
    ex = impulses(dur, times, amps, 0.3)
    k = r.uniform(0.97, 1.03)
    modes = resonator_bank(ex, np.array([1150, 2480, 3620, 5100, 6900]) * k, [0.22, 0.15, 0.1, 0.07, 0.05], [1, .8, .6, .4, .25])
    stone = mix.bandpass(ex + 0.02 * r.standard_normal(len(ex)) * (ex > 0.001), 2000, 9000, SR, 2)
    rattle_t = np.cumsum(r.uniform(0.012, 0.03, 10)) + times[-1] + 0.02
    rat = resonator_bank(impulses(dur, rattle_t, r.uniform(0.02, 0.06, 10), 0.2), np.array([2480, 3620]) * k, [0.05, 0.04], [1, 0.6])
    x = modes / (np.abs(modes).max() + 1e-9) + 0.4 * stone / (np.abs(stone).max() + 1e-9) + rat / (np.abs(modes).max() + 1e-9)
    return finish(x, "oneshot", 0.0005, 0.1)


def gripper_click(seed=0):
    """Robot gripper: tiny servo whir then two plastic/metal latch clicks."""
    r = _rng(seed)
    wh = servo(0.12, 700, 950, seed=seed)
    dur = 0.3
    cl = resonator_bank(impulses(dur, [0.0, 0.018 + r.uniform(0, 0.01)], [1.0, 0.6], 0.15), [2300, 3900, 6100], [0.02, 0.015, 0.01], [1, 0.7, 0.4])
    cl /= np.abs(cl).max() + 1e-9
    out = np.zeros(_n(0.12 + dur))
    out[: len(wh)] += 0.4 * wh / (np.abs(wh).max() + 1e-9)
    a = _n(0.11)
    out[a:a + len(cl)] += cl[: len(out) - a]
    return finish(out, "oneshot", 0.001, 0.02)


def door_slide(seed=0, dur=1.3, kind="open"):
    """Wooden lattice (koshi-do) door sliding on its wooden track: friction rumble with
    stick-slip grain, lattice rattle, soft wooden bump at the end (kind 'open'/'close')."""
    r = _rng(seed)
    n = _n(dur)
    t = np.arange(n) / SR
    u = t / dur
    spd = np.sin(np.pi * np.clip(u / 0.92, 0, 1)) ** 0.7
    fr = mix.bandpass(brown(n, r) * 0.6 + r.standard_normal(n) * 0.4, 90, 1600, SR, 2)
    grain_rate = 35 + 25 * spd
    gph = np.cumsum(grain_rate / SR)
    grain = 0.7 + 0.3 * np.sin(2 * np.pi * gph) ** 2
    fr = fr * spd * grain * (1 + 0.3 * smooth_rand(n, 15, r))
    fr /= np.abs(fr).max() + 1e-9
    rt = np.sort(r.uniform(0.05, dur * 0.85, int(r.integers(6, 12))))
    rat = resonator_bank(impulses(dur, rt, r.uniform(0.2, 0.6, len(rt)), 0.3), [820, 1450, 2300], [0.03, 0.025, 0.02], [1, 0.7, 0.4])
    rat /= np.abs(rat).max() + 1e-9
    bump_t = dur * 0.93
    bump = resonator_bank(impulses(dur + 0.4, [bump_t], [1.0], 1.5), [150, 310, 640, 1200], [0.12, 0.09, 0.06, 0.04], [1, 0.8, 0.5, 0.3])
    bump /= np.abs(bump).max() + 1e-9
    x = np.zeros(_n(dur + 0.4))
    x[:n] += 0.7 * fr + 0.35 * rat
    x += (0.9 if kind == "close" else 0.5) * bump
    x = mix.lowpass(x, 3500, SR, 2)
    return finish(x, "oneshot", 0.01, 0.1)


def kettle_creak(seed=0, dur=0.8):
    """Metal kettle (handle / lid) creak: stick-slip pulse train with gliding rate exciting
    metallic resonances."""
    r = _rng(seed)
    n = _n(dur)
    t = np.arange(n) / SR
    rate = 40 + 90 * (0.5 - 0.5 * np.cos(np.pi * t / dur)) * r.uniform(0.8, 1.2)
    rate *= 1 + 0.15 * smooth_rand(n, 8, r)
    ph = np.cumsum(rate / SR)
    idx = np.where(np.diff(np.floor(ph)) > 0)[0]
    ex = np.zeros(n)
    env = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 0.5
    ex[idx] = env[idx] * r.uniform(0.6, 1.0, len(idx))
    x = resonator_bank(ex, [1230, 2870, 4310, 6100], [0.09, 0.07, 0.05, 0.03], [1, 0.8, 0.5, 0.3])
    x = mix.lowpass(mix.highpass(x, 500, SR, 2), 7000, SR, 2)
    return finish(x, "oneshot", 0.005, 0.05)


def dog_shake(seed=0, dur=1.3):
    """Wet dog shaking: fur whooshes oscillating at ~5 Hz (speeding up then slowing), water
    spray droplets, ear flaps near the end."""
    r = _rng(seed)
    n = _n(dur)
    t = np.arange(n) / SR
    u = t / dur
    rate = 4.0 + 3.0 * np.sin(np.pi * u)
    ph = np.cumsum(rate / SR)
    osc = (0.5 + 0.5 * np.cos(2 * np.pi * ph)) ** 2
    env = np.sin(np.pi * np.clip(u, 0, 1)) ** 0.5
    fur = band_noise(n, 300, 5000, r) * osc * env
    fur /= np.abs(fur).max() + 1e-9
    spray = np.zeros(n)
    k = int(900 * dur)
    pos = r.integers(0, n, k)
    spray[pos] = r.lognormal(-2, 0.7, k) * env[pos] * osc[pos]
    spray = resonator_bank(spray, [2500, 4200, 6800], [0.006, 0.005, 0.004], [1, .8, .6])
    spray /= np.abs(spray).max() + 1e-9
    flaps_t = np.arange(0.62, 0.95, 0.075) * dur
    flaps = resonator_bank(impulses(dur, flaps_t, r.uniform(0.5, 1.0, len(flaps_t)), 2.0), [180, 420, 900], [0.03, 0.02, 0.015], [1, .6, .3])
    flaps /= np.abs(flaps).max() + 1e-9
    x = 0.8 * fur + 0.45 * spray + 0.35 * flaps
    return finish(x, "oneshot", 0.01, 0.1)


def dog_sniff_synth(seed=0, n=None):
    """Quick dog sniffing: 3-6 short nasal inhales at ~6-7 per second (band noise with nasal
    resonances), slight exhale at the end."""
    r = _rng(seed)
    n = n or int(r.integers(3, 7))
    per = 1 / r.uniform(6.0, 7.5)
    dur = n * per + 0.35
    out = np.zeros(_n(dur))
    for i in range(n):
        L = _n(per * r.uniform(0.45, 0.6))
        tt = np.arange(L) / SR
        b = r.standard_normal(L)
        b = klatt_res(b, r.uniform(2300, 2900), 900) + 0.6 * klatt_res(b, r.uniform(4800, 5600), 1400)
        e = np.sin(np.pi * tt / (L / SR)) ** 1.5 * r.uniform(0.6, 1.0)
        a = _n(0.01 + i * per * r.uniform(0.95, 1.05))
        out[a:a + L] += (b * e)[: len(out) - a]
    L = _n(0.22)
    tt = np.arange(L) / SR
    ex = mix.bandpass(r.standard_normal(L), 600, 4000, SR, 2) * np.sin(np.pi * tt / 0.22) ** 2 * 0.35
    a = _n(0.02 + n * per)
    out[a:a + L] += ex[: len(out) - a]
    out = mix.lowpass(mix.highpass(out, 600, SR, 2), 7000, SR, 2)
    return finish(out, "oneshot", 0.003, 0.05)


def dog_lick(seed=0, n_licks=None):
    """Dog lick: 2-3 wet tongue slurps (low filtered noise swell + wet clicks)."""
    r = _rng(seed)
    n_licks = n_licks or int(r.integers(2, 4))
    dur = 0.24 * n_licks + 0.3
    n = _n(dur)
    x = np.zeros(n)
    for i in range(n_licks):
        t0 = 0.02 + i * r.uniform(0.18, 0.24)
        L = _n(0.16)
        tt = np.arange(L) / SR
        sl = band_noise(L, 400, 3500, r) * np.sin(np.pi * tt / 0.16) ** 2
        sl = klatt_res(sl, r.uniform(900, 1400), 400)
        clicks = resonator_bank(impulses(0.16, np.sort(r.uniform(0.02, 0.14, 4)), r.uniform(0.3, 1, 4), 0.2), [1800, 3000], [0.008, 0.006], [1, .6])
        s = sl / (np.abs(sl).max() + 1e-9) + 0.5 * clicks / (np.abs(clicks).max() + 1e-9)
        a = _n(t0)
        x[a:a + L] += s[: n - a] * r.uniform(0.7, 1.0)
    x = mix.highpass(x, 200, SR, 2)
    return finish(x, "oneshot", 0.003, 0.05)


def whoosh_soft(seed=0, dur=0.9):
    """Soft whoosh: noise with a band sweeping 300 -> 2000 -> 600 Hz, swell, moving L->R."""
    r = _rng(seed)
    n = _n(dur)
    t = np.arange(n) / SR
    u = t / dur
    fc = 300 * (2000 / 300) ** np.sin(np.pi * np.clip(u / 0.9, 0, 1)) ** 1.2
    nz = _moving_band(n, fc, 900, r) + 0.5 * mix.lowpass(pink(n, r), 500, SR, 2)
    env = np.sin(np.pi * u) ** 2.2
    x = nz * env
    pan = np.clip(-0.7 + 1.4 * u, -1, 1)
    th = (pan + 1) * np.pi / 4
    st = np.stack([x * np.cos(th), x * np.sin(th)], axis=1) * math.sqrt(2)
    return finish(st, "oneshot", 0.01, 0.05, trim=False)


def kite_cry(seed=0, dist=1.0):
    """Black kite (tobi) 'piii-hyororo': sustained ~3 kHz whistle, then a descending warbling
    trill (~11 Hz, +-7 %) 3.0 -> 2.1 kHz; weak 2nd harmonic, breathy; distant sky reverb."""
    r = _rng(seed)
    k = r.uniform(0.95, 1.05)
    d1 = r.uniform(0.45, 0.6)
    g = 0.06
    d2 = r.uniform(1.1, 1.4)
    tt1 = np.arange(_n(d1)) / SR
    f1 = k * (2900 + 250 * np.minimum(1, tt1 / 0.12)) * (1 + 0.004 * np.sin(2 * np.pi * 6 * tt1))
    e1 = np.minimum(1, tt1 / 0.05) * np.minimum(1, (d1 - tt1) / 0.06)
    tt2 = np.arange(_n(d2)) / SR
    u2 = tt2 / d2
    f2 = k * 3050 * (2050 / 3050) ** (u2 ** 0.9) * (1 + 0.07 * np.sin(2 * np.pi * 11 * tt2) * np.minimum(1, tt2 / 0.1))
    e2 = np.minimum(1, tt2 / 0.03) * (1 - u2) ** 1.2 * (0.7 + 0.3 * (0.5 + 0.5 * np.cos(2 * np.pi * 11 * tt2)))
    f = np.concatenate([f1, np.full(_n(g), f1[-1]), f2])
    e = np.concatenate([e1, np.zeros(_n(g)), e2 * 0.85])
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = (np.sin(ph) + 0.12 * np.sin(2 * ph)) * e
    x += 0.04 * _moving_band(len(x), f, 400, r) * e
    y = distant(np.concatenate([np.zeros(_n(0.02)), x]), lp=7000 - 1500 * dist, hp=800, wet=0.3 + 0.15 * dist,
                decay=2.4, predelay=30 + 40 * dist)
    return finish(y, "oneshot", 0.005, 0.8, trim=False)


# ============================================================================ catalogue

SYNTH = {
    # name: (callable, kwargs, kind, desc)
    "cicada_tsukutsuku_1": (cicada_tsukutsuku, dict(seed=1), "oneshot", "tsukutsukuboushi cicada phrase ~9.5 s, distant"),
    "cicada_tsukutsuku_2": (cicada_tsukutsuku, dict(seed=2, dist=1.4), "oneshot", "tsukutsukuboushi, variation, further"),
    "cicada_tsukutsuku_3": (cicada_tsukutsuku, dict(seed=3, dist=0.6), "oneshot", "tsukutsukuboushi, variation, nearer"),
    "higurashi_1": (higurashi, dict(seed=1), "oneshot", "higurashi evening 'kana-kana' ~6.5 s, distant"),
    "higurashi_2": (higurashi, dict(seed=2, dur=7.5, dist=1.4), "oneshot", "higurashi, longer, further"),
    "higurashi_3": (higurashi, dict(seed=3, dur=5.0, dist=0.8), "oneshot", "higurashi, shorter, nearer"),
    "suzumushi": (suzumushi, dict(seed=1), "oneshot", "bell cricket 'riiin' chirps ~4.3 kHz, 10 s"),
    "suzumushi_2": (suzumushi, dict(seed=2), "oneshot", "bell cricket, variation"),
    "servo_short": (servo, dict(dur=0.28, f0=420, f1=640, seed=1), "oneshot", "small head servo whine, 0.28 s, rising"),
    "servo_short_down": (servo, dict(dur=0.28, f0=640, f1=420, seed=2), "oneshot", "small servo whine, falling"),
    "servo_long": (servo, dict(dur=0.9, f0=380, f1=560, seed=3, wobble=0.04), "oneshot", "servo whine 0.9 s (arm)"),
    "servo_long_2": (servo, dict(dur=1.3, f0=520, f1=360, seed=4, wobble=0.03), "oneshot", "servo whine 1.3 s, falling"),
    "motor_roll_loop": (motor_roll, dict(duration=8.0, speed=0.7, seed=1, loop=True), "loop", "motor + wheels at constant speed 0.7 (use sfx.motor_roll for envelopes)"),
    "motor_roll_start_stop": (motor_roll, dict(duration=5.0, speed=[0, 0.4, 0.9, 1.0, 1.0, 0.9, 0.5, 0.0], seed=2), "oneshot", "motor roll: starts, cruises, stops (5 s)"),
    "bike_bell_clack_1": (bike_bell_clack, dict(seed=1, double=False), "oneshot", "broken bell: single dull muted tick"),
    "bike_bell_clack_2": (bike_bell_clack, dict(seed=2, double=True), "oneshot", "broken bell: double tick (clapper bounce)"),
    "bike_bell_clack_3": (bike_bell_clack, dict(seed=3, double=False), "oneshot", "broken bell: single tick, variation"),
    "bike_bell_ring": (bike_bell_ring, dict(kind="ring", seed=1), "oneshot", "THE bell: clean bright rotary 'rrring', ~2.3 s"),
    "bike_bell_ring_double": (bike_bell_ring, dict(kind="double", seed=2), "oneshot", "bell 'ring-ring', ~2.9 s"),
    "bike_bell_ding": (bike_bell_ring, dict(kind="ding", seed=3), "oneshot", "single clean bell strike 'ding', ~1.9 s"),
    "temple_bell": (temple_bell, dict(seed=1), "oneshot", "bonsho temple bell, distant, 12 s"),
    "temple_bell_far": (temple_bell, dict(seed=2, dist=1.6), "oneshot", "bonsho, further away"),
    "fumikiri": (fumikiri, dict(seed=1), "oneshot", "railway crossing 'kan-kan', distant, 6 s"),
    "shutter_roll": (shutter_roll, dict(seed=1), "oneshot", "metal shop shutter rolling up, distant, 3 s"),
    "shutter_roll_2": (shutter_roll, dict(seed=2, dist=1.4), "oneshot", "shutter, further"),
    "plastic_bag": (plastic_bag, dict(seed=1), "oneshot", "plastic bag crinkle 2 s"),
    "plastic_bag_2": (plastic_bag, dict(seed=2, dur=1.2), "oneshot", "plastic bag crinkle 1.2 s"),
    "vending_hum": (vending_hum, dict(seed=1), "loop", "vending machine hum (60 Hz), seamless 10 s loop"),
    "water_channel": (water_channel, dict(seed=1), "loop", "water trickling in a stone channel, seamless 20 s stereo loop"),
    "wind_soft": (wind_soft, dict(seed=1), "loop", "soft wind, seamless 30 s stereo loop"),
    "market_murmur": (market_murmur, dict(seed=1), "loop", "wordless market crowd murmur, seamless 30 s stereo loop"),
    "kite_cry_1": (kite_cry, dict(seed=1), "oneshot", "black kite 'piii-hyororo', distant"),
    "kite_cry_2": (kite_cry, dict(seed=2, dist=1.4), "oneshot", "black kite, further"),
    "kite_cry_3": (kite_cry, dict(seed=3, dist=0.7), "oneshot", "black kite, nearer"),
    "dog_growl": (dog_growl, dict(seed=1), "oneshot", "soft low growl (synth), 1.6 s"),
    "cat_mrrp_1": (cat_mrrp, dict(seed=1), "oneshot", "cat 'mrrp' greeting trill (synth)"),
    "cat_mrrp_2": (cat_mrrp, dict(seed=2), "oneshot", "cat 'mrrp', variation"),
    "cat_hiss": (cat_hiss, dict(seed=1), "oneshot", "cat hiss (synth)"),
    "slipper_step_1": (slipper_step, dict(seed=1), "oneshot", "soft slipper step on stone (synth)"),
    "slipper_step_2": (slipper_step, dict(seed=2, weight=0.5), "oneshot", "slipper step, variation"),
    "slipper_step_3": (slipper_step, dict(seed=3, weight=0.7), "oneshot", "slipper step, variation"),
    "slipper_step_4": (slipper_step, dict(seed=4, weight=0.4), "oneshot", "slipper step, lighter"),
    "puddle_splash_1": (puddle_splash, dict(seed=1), "oneshot", "wheel into puddle: soft puff splash"),
    "puddle_splash_2": (puddle_splash, dict(seed=2), "oneshot", "puddle splash, variation"),
    "metal_clatter_1": (metal_clatter, dict(seed=1), "oneshot", "small bell dropped on stone, bounces"),
    "metal_clatter_2": (metal_clatter, dict(seed=2), "oneshot", "metal clatter, variation"),
    "gripper_click_1": (gripper_click, dict(seed=1), "oneshot", "robot gripper whir + latch click"),
    "gripper_click_2": (gripper_click, dict(seed=2), "oneshot", "gripper, variation"),
    "door_slide_open": (door_slide, dict(seed=1, kind="open"), "oneshot", "wooden lattice door sliding open"),
    "door_slide_close": (door_slide, dict(seed=2, kind="close", dur=1.1), "oneshot", "wooden lattice door sliding shut (bump)"),
    "kettle_creak_1": (kettle_creak, dict(seed=1), "oneshot", "kettle handle/lid metal creak"),
    "kettle_creak_2": (kettle_creak, dict(seed=2, dur=0.5), "oneshot", "kettle creak, short"),
    "dog_sniff_synth_1": (dog_sniff_synth, dict(seed=1), "oneshot", "quick sniffing (synth, ~6.5 sniffs/s)"),
    "dog_sniff_synth_2": (dog_sniff_synth, dict(seed=2, n=6), "oneshot", "quick sniffing, 6 sniffs (synth)"),
    "dog_shake": (dog_shake, dict(seed=1), "oneshot", "wet dog shaking off water, 1.3 s"),
    "dog_lick_1": (dog_lick, dict(seed=1), "oneshot", "dog licks (2-3 slurps)"),
    "dog_lick_2": (dog_lick, dict(seed=2), "oneshot", "dog licks, variation"),
    "whoosh_soft_1": (whoosh_soft, dict(seed=1), "oneshot", "soft whoosh L->R 0.9 s"),
    "whoosh_soft_2": (whoosh_soft, dict(seed=2, dur=1.4), "oneshot", "soft whoosh, slower"),
    "hum_phrase_demo": (lambda: hum_voice([(62, 0.0, 0.6), (64, 0.6, 0.6), (66, 1.2, 0.6), (69, 1.8, 0.6), (66, 2.4, 0.6), (64, 3.0, 0.6), (62, 3.6, 1.0)]),
                        {}, "oneshot", "hum voice, D4 E4 F#4 A4 F#4 E4 D4 (natural register)"),
}
for _k in ROBOT_BEEPS:
    SYNTH[f"robot_beep_{_k}"] = (robot_beep, dict(kind=_k, seed=0), "oneshot", f"robot beep: {ROBOT_BEEPS[_k]}")
for _k in ("query", "yes", "happy", "sad", "curious"):
    SYNTH[f"robot_beep_{_k}_b"] = (robot_beep, dict(kind=_k, seed=7), "oneshot", f"robot beep: {ROBOT_BEEPS[_k]} (variation)")


ALIASES = {
    "bike_bell_clack": "bike_bell_clack_1", "cicada_tsukutsuku": "cicada_tsukutsuku_1", "higurashi": "higurashi_1",
    "kite_cry": "kite_cry_1", "dog_bark": "dog_bark_1", "dog_yip": "dog_yip_1", "cat_meow": "cat_meow_1",
    "cat_mrrp": "cat_mrrp_1", "crow_caw": "crow_caw_1", "dog_sniff": "dog_sniff_1", "door_creak": "door_creak_1",
    "water_drop": "water_drop_1", "footstep": "footstep_1", "slipper_step": "slipper_step_1",
    "puddle_splash": "puddle_splash_1", "metal_clatter": "metal_clatter_1", "gripper_click": "gripper_click_1",
    "door_slide": "door_slide_open", "kettle_creak": "kettle_creak_1", "dog_lick": "dog_lick_1",
    "whoosh_soft": "whoosh_soft_1", "servo": "servo_short", "motor_roll": "motor_roll_loop",
    "rain": "rain_light", "crickets": "crickets_night", "birds": "birds_morning",
}


def names():
    return sorted(list(ESC_PICKS) + list(SYNTH))


def _resolve(name):
    return ALIASES.get(name, name)


def render(name):
    """Render a catalogue entry fresh (no lib cache)."""
    name = _resolve(name)
    if name in ESC_PICKS:
        return esc_clip(name)
    fn, kw, kind, desc = SYNTH[name]
    return fn(**kw)


def get(name):
    """Load lib/<name>.wav if it exists, else render it. Accepts ALIASES (e.g. 'bike_bell_clack')."""
    name = _resolve(name)
    p = os.path.join(LIB, f"{name}.wav")
    if os.path.exists(p):
        x, sr = sf.read(p, dtype="float32")
        return x
    return render(name)


def build_library(only=None, verbose=True):
    os.makedirs(LIB, exist_ok=True)
    meta = _esc_meta()
    cat = {}
    catp = os.path.join(LIB, "catalogue.json")
    if only and os.path.exists(catp):
        with open(catp) as f:
            cat = json.load(f)
    for nm in names():
        if only and nm not in only:
            continue
        x = render(nm)
        x = np.asarray(x, dtype=np.float32)
        path = os.path.join(LIB, f"{nm}.wav")
        mix.write_wav(path, x)
        q = mix.check(x)
        ent = dict(file=f"lib/{nm}.wav", channels=1 if x.ndim == 1 else 2, dur_s=q["dur_s"], peak_dbfs=q["peak_dbfs"],
                   lufs_integrated=q["lufs"], lufs_momentary_max=round(momentary_max(x), 2))
        if nm in ESC_PICKS:
            p = ESC_PICKS[nm]
            files = p["file"] if isinstance(p["file"], list) else [p["file"]]
            ent.update(source="ESC-50", kind=p.get("kind", "oneshot"), desc=p["desc"],
                       esc50=[dict(file=f, category=meta[f]["category"], freesound_id=meta[f]["src_file"], take=meta[f]["take"],
                                   t0=p["t0"], t1=p["t1"]) for f in files],
                       license="CC BY-NC 3.0 (ESC-50, K. J. Piczak; Freesound.org clips)")
        else:
            fn, kw, kind, desc = SYNTH[nm]
            ent.update(source="synth", kind=kind, desc=desc, generator=getattr(fn, "__name__", "lambda"),
                       params={k: v for k, v in kw.items()})
        cat[nm] = ent
        if verbose:
            print(f"{nm:28s} {ent['dur_s']:6.2f}s ch{ent['channels']} peak {ent['peak_dbfs']:6.1f} "
                  f"LUFS {ent['lufs_integrated']} Mmax {ent['lufs_momentary_max']}")
    with open(catp, "w") as f:
        json.dump(cat, f, indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o))
    return cat


def _main(argv):
    if len(argv) < 2 or argv[1] in ("-h", "--help"):
        print(__doc__)
        return
    cmd = argv[1]
    if cmd == "build":
        build_library(argv[2:] or None)
    elif cmd == "list":
        for nm in names():
            d = ESC_PICKS[nm]["desc"] if nm in ESC_PICKS else SYNTH[nm][3]
            print(f"{nm:28s} {'ESC' if nm in ESC_PICKS else 'synth':5s} {d}")
    elif cmd == "render":
        x = render(argv[2])
        mix.write_wav(argv[3], x)
        print("wrote", argv[3])
    else:
        print(__doc__)


if __name__ == "__main__":
    _main(sys.argv)
