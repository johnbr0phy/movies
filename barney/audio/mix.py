"""mix.py - mixing / mastering helpers for "The Bicycle".

All buffers are float32 numpy arrays at 48 kHz.  Mono = shape (n,), stereo = shape (n, 2).

CLI:
    python mix.py loudness FILE.wav [...]         # integrated LUFS, true-ish peak, DC, clicks
    python mix.py normalize IN.wav OUT.wav -16    # normalise to LUFS then limit to -1 dBFS
"""
from __future__ import annotations

import math
import sys

import numpy as np
import soundfile as sf
from scipy import signal
from scipy.ndimage import minimum_filter1d, maximum_filter1d

SR = 48000

# ----------------------------------------------------------------------------- basics


def db2amp(db):
    return 10.0 ** (np.asarray(db, dtype=np.float64) / 20.0)


def amp2db(a, floor=1e-12):
    return 20.0 * np.log10(np.maximum(np.abs(a), floor))


def as_stereo(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=np.float32)
    if x.ndim == 1:
        return np.stack([x, x], axis=1)
    if x.shape[1] == 1:
        return np.repeat(x, 2, axis=1)
    return x[:, :2]


def as_mono(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=np.float32)
    return x if x.ndim == 1 else x.mean(axis=1).astype(np.float32)


def silence(dur_s: float, sr: int = SR, stereo: bool = True) -> np.ndarray:
    n = int(round(dur_s * sr))
    return np.zeros((n, 2) if stereo else n, dtype=np.float32)


def pan_gains(pan: float):
    """Constant-power pan law. pan -1 (left) .. +1 (right). Centre = 1/sqrt2 each (-3 dB)."""
    p = float(np.clip(pan, -1.0, 1.0))
    th = (p + 1.0) * math.pi / 4.0
    return math.cos(th), math.sin(th)


def pan_stereo(x: np.ndarray, pan: float = 0.0, width: float = 1.0) -> np.ndarray:
    """Pan mono or stereo material with a constant-power law.

    Mono input: classic constant-power pan (centre -3 dB per side, equal power everywhere).
    Stereo input: width scales the side signal (0 = mono fold), then a constant-power
    balance is applied scaled by sqrt(2) so that pan=0 leaves the stereo image untouched.
    """
    x = np.asarray(x, dtype=np.float32)
    gl, gr = pan_gains(pan)
    if x.ndim == 1:
        return np.stack([x * gl, x * gr], axis=1).astype(np.float32)
    x = as_stereo(x)
    if width != 1.0:
        m = 0.5 * (x[:, 0] + x[:, 1])
        s = 0.5 * (x[:, 0] - x[:, 1]) * width
        x = np.stack([m + s, m - s], axis=1)
    k = math.sqrt(2.0)
    return np.stack([x[:, 0] * gl * k, x[:, 1] * gr * k], axis=1).astype(np.float32)


def place(buf: np.ndarray, clip: np.ndarray, t: float, gain_db: float = 0.0,
          pan: float = 0.0, sr: int = SR, width: float = 1.0) -> np.ndarray:
    """Mix `clip` into stereo `buf` (in place) starting at t seconds. Returns buf.

    Mono clips are panned with the constant-power law; stereo clips are balanced.
    Parts outside the buffer are silently cropped (negative t allowed)."""
    if clip is None or len(clip) == 0:
        return buf
    c = pan_stereo(clip, pan, width) * float(db2amp(gain_db))
    start = int(round(t * sr))
    s0, c0 = start, 0
    if s0 < 0:
        c0 = -s0
        s0 = 0
    n = min(len(c) - c0, len(buf) - s0)
    if n > 0:
        if buf.ndim == 1:
            buf[s0:s0 + n] += c[c0:c0 + n].mean(axis=1)
        else:
            buf[s0:s0 + n] += c[c0:c0 + n]
    return buf


# ----------------------------------------------------------------------------- fades


def _fade_curve(n: int, shape: str = "cos"):
    if n <= 0:
        return np.ones(0, dtype=np.float32)
    t = (np.arange(n) + 0.5) / n
    if shape == "lin":
        c = t
    elif shape == "exp":
        c = (np.exp(4 * t) - 1) / (np.exp(4) - 1)
    elif shape == "sqrt":  # equal-power
        c = np.sin(t * np.pi / 2)
    else:  # raised cosine
        c = 0.5 - 0.5 * np.cos(np.pi * t)
    return c.astype(np.float32)


def fade_in(x: np.ndarray, dur_s: float, sr: int = SR, shape: str = "cos") -> np.ndarray:
    x = np.array(x, dtype=np.float32, copy=True)
    n = min(len(x), int(round(dur_s * sr)))
    c = _fade_curve(n, shape)
    x[:n] *= c if x.ndim == 1 else c[:, None]
    return x


def fade_out(x: np.ndarray, dur_s: float, sr: int = SR, shape: str = "cos") -> np.ndarray:
    x = np.array(x, dtype=np.float32, copy=True)
    n = min(len(x), int(round(dur_s * sr)))
    c = _fade_curve(n, shape)[::-1]
    if n:
        x[-n:] *= c if x.ndim == 1 else c[:, None]
    return x


def fades(x: np.ndarray, fin: float = 0.005, fout: float = 0.01, sr: int = SR,
          shape: str = "cos") -> np.ndarray:
    return fade_out(fade_in(x, fin, sr, shape), fout, sr, shape)


def crossfade_concat(a: np.ndarray, b: np.ndarray, xf_s: float, sr: int = SR,
                     power: bool = True) -> np.ndarray:
    """Concatenate a and b with an overlap of xf_s seconds.
    power=True -> equal-power (uncorrelated material), False -> equal-gain (coherent)."""
    n = int(round(xf_s * sr))
    n = min(n, len(a), len(b))
    if n == 0:
        return np.concatenate([a, b]).astype(np.float32)
    t = (np.arange(n) + 0.5) / n
    if power:
        fi, fo = np.sin(t * np.pi / 2), np.cos(t * np.pi / 2)
    else:
        fi = 0.5 - 0.5 * np.cos(np.pi * t)
        fo = 1 - fi
    if a.ndim == 2:
        fi, fo = fi[:, None], fo[:, None]
    mid = a[-n:] * fo + b[:n] * fi
    return np.concatenate([a[:-n], mid, b[n:]]).astype(np.float32)


def make_loopable(x: np.ndarray, xf_s: float = 0.5, sr: int = SR) -> np.ndarray:
    """Return a clip of len(x)-xf samples that loops seamlessly (tail crossfaded into head)."""
    n = int(round(xf_s * sr))
    if n <= 0 or 2 * n >= len(x):
        return np.asarray(x, dtype=np.float32)
    body = np.array(x[:-n], dtype=np.float32, copy=True)
    tail = x[-n:]
    t = (np.arange(n) + 0.5) / n
    fi, fo = np.sin(t * np.pi / 2), np.cos(t * np.pi / 2)
    if x.ndim == 2:
        fi, fo = fi[:, None], fo[:, None]
    body[:n] = body[:n] * fi + tail * fo
    return body


def loop_to(clip: np.ndarray, dur_s: float, crossfade: float = 0.25, sr: int = SR,
            fade_edges: bool = True) -> np.ndarray:
    """Loop `clip` to exactly dur_s seconds using equal-power crossfades at each seam."""
    target = int(round(dur_s * sr))
    clip = np.asarray(clip, dtype=np.float32)
    if len(clip) >= target:
        out = clip[:target].copy()
    else:
        xf = int(round(crossfade * sr))
        xf = min(xf, len(clip) // 3)
        out = clip.copy()
        while len(out) < target + xf:
            out = crossfade_concat(out, clip, xf / sr, sr, power=True)
        out = out[:target]
    if fade_edges:
        out = fades(out, 0.01, 0.05, sr)
    return out.astype(np.float32)


# ----------------------------------------------------------------------------- filters


def _sos(kind, freq, sr, order):
    nyq = sr / 2.0
    if kind == "bandpass":
        lo, hi = freq
        lo = max(1.0, lo)
        hi = min(hi, nyq * 0.999)
        return signal.butter(order, [lo / nyq, hi / nyq], btype="bandpass", output="sos")
    f = min(float(freq), nyq * 0.999)
    return signal.butter(order, f / nyq, btype=kind, output="sos")


def _apply(sos, x, zero_phase=True):
    x = np.asarray(x, dtype=np.float64)
    if len(x) < 64:
        return x.astype(np.float32)
    if zero_phase:
        y = signal.sosfiltfilt(sos, x, axis=0, padtype="odd", padlen=min(len(x) - 1, 3 * (2 * len(sos) + 1)))
    else:
        y = signal.sosfilt(sos, x, axis=0)
    return y.astype(np.float32)


def lowpass(x, freq, sr=SR, order=4, zero_phase=True):
    return _apply(_sos("lowpass", freq, sr, order), x, zero_phase)


def highpass(x, freq, sr=SR, order=4, zero_phase=True):
    return _apply(_sos("highpass", freq, sr, order), x, zero_phase)


def bandpass(x, lo, hi, sr=SR, order=2, zero_phase=True):
    return _apply(_sos("bandpass", (lo, hi), sr, order), x, zero_phase)


def peaking_eq(x, freq, gain_db, q=1.0, sr=SR):
    """RBJ peaking EQ biquad (zero-phase)."""
    A = 10 ** (gain_db / 40)
    w0 = 2 * np.pi * freq / sr
    al = np.sin(w0) / (2 * q)
    b = np.array([1 + al * A, -2 * np.cos(w0), 1 - al * A])
    a = np.array([1 + al / A, -2 * np.cos(w0), 1 - al / A])
    sos = signal.tf2sos(b / a[0], a / a[0])
    # zero-phase would double the gain; use single-pass sosfilt
    return _apply(sos, x, zero_phase=False)


def shelf(x, freq, gain_db, kind="high", sr=SR, s=1.0):
    """RBJ shelving filter (single pass)."""
    A = 10 ** (gain_db / 40)
    w0 = 2 * np.pi * freq / sr
    al = np.sin(w0) / 2 * np.sqrt((A + 1 / A) * (1 / s - 1) + 2)
    c = np.cos(w0)
    if kind == "high":
        b = [A * ((A + 1) + (A - 1) * c + 2 * np.sqrt(A) * al), -2 * A * ((A - 1) + (A + 1) * c),
             A * ((A + 1) + (A - 1) * c - 2 * np.sqrt(A) * al)]
        a = [(A + 1) - (A - 1) * c + 2 * np.sqrt(A) * al, 2 * ((A - 1) - (A + 1) * c),
             (A + 1) - (A - 1) * c - 2 * np.sqrt(A) * al]
    else:
        b = [A * ((A + 1) - (A - 1) * c + 2 * np.sqrt(A) * al), 2 * A * ((A - 1) - (A + 1) * c),
             A * ((A + 1) - (A - 1) * c - 2 * np.sqrt(A) * al)]
        a = [(A + 1) + (A - 1) * c + 2 * np.sqrt(A) * al, -2 * ((A - 1) + (A + 1) * c),
             (A + 1) + (A - 1) * c - 2 * np.sqrt(A) * al]
    b, a = np.array(b), np.array(a)
    return _apply(signal.tf2sos(b / a[0], a / a[0]), x, zero_phase=False)


def remove_dc(x, sr=SR, freq=12.0):
    """Remove DC / sub-sonic content (zero-phase 2nd-order HPF + mean subtraction)."""
    x = np.asarray(x, dtype=np.float32)
    x = x - x.mean(axis=0)
    return highpass(x, freq, sr, order=2)


# ----------------------------------------------------------------------------- dynamics


def _block_env(x, sr, block):
    """RMS per block of `block` samples (max over channels)."""
    m = x if x.ndim == 1 else np.max(np.abs(x), axis=1)
    n = int(math.ceil(len(m) / block))
    pad = np.zeros(n * block, dtype=np.float64)
    pad[:len(m)] = m.astype(np.float64) ** 2
    return np.sqrt(pad.reshape(n, block).mean(axis=1) + 1e-20)


def compress(x, threshold_db=-18.0, ratio=2.0, attack_ms=10.0, release_ms=150.0,
             knee_db=6.0, makeup_db=0.0, sr=SR):
    """Simple feed-forward RMS bus compressor (stereo-linked). Returns compressed copy."""
    x = np.asarray(x, dtype=np.float32)
    block = max(1, int(sr * 0.002))
    env = amp2db(_block_env(x, sr, block))
    ta = math.exp(-block / (sr * attack_ms / 1000))
    tr = math.exp(-block / (sr * release_ms / 1000))
    # static curve (soft knee) -> desired gain reduction per block
    over = env - threshold_db
    gr = np.where(over <= -knee_db / 2, 0.0,
                  np.where(over >= knee_db / 2, over * (1 - 1 / ratio),
                           (1 - 1 / ratio) * (over + knee_db / 2) ** 2 / (2 * max(knee_db, 1e-6))))
    sm = np.empty_like(gr)
    g = 0.0
    for i, v in enumerate(gr):
        c = ta if v > g else tr
        g = c * g + (1 - c) * v
        sm[i] = g
    t_blocks = (np.arange(len(sm)) + 0.5) * block
    gain_db = np.interp(np.arange(len(x)), t_blocks, -sm) + makeup_db
    gain = db2amp(gain_db).astype(np.float32)
    return (x * (gain if x.ndim == 1 else gain[:, None])).astype(np.float32)


def limit(x, ceiling_db=-1.0, lookahead_ms=3.0, release_ms=80.0, sr=SR):
    """Brickwall-ish look-ahead limiter (zero latency, offline). Guarantees |y| <= ceiling
    on every sample (sample peak), smooth gain with release."""
    x = np.asarray(x, dtype=np.float32)
    ceil = float(db2amp(ceiling_db))
    a = np.abs(x) if x.ndim == 1 else np.max(np.abs(x), axis=1)
    g = np.minimum(1.0, ceil / np.maximum(a, 1e-12))
    if g.min() >= 1.0:
        return x.copy()
    L = max(2, int(sr * lookahead_ms / 1000))
    B = 32
    nb = int(math.ceil(len(g) / B))
    gp = np.ones(nb * B + L)
    gp[:len(g)] = g
    # min over [block start, block end + L]
    fwd = minimum_filter1d(gp, size=B + L, origin=-((B + L) // 2))
    blk = fwd[0:nb * B:B]
    rel = math.exp(-B / (sr * release_ms / 1000))
    out = np.empty_like(blk)
    cur = 1.0
    for i, v in enumerate(blk):
        cur = v if v < cur else rel * cur + (1 - rel) * v
        cur = min(cur, v)
        out[i] = cur
    gs = np.repeat(out, B)[:len(g) + L]
    # causal moving average over L -> smooth attack that is still <= g
    k = np.ones(L) / L
    gsm = np.convolve(gs, k, mode="full")[:len(g)]
    gsm[:L] = np.minimum(gsm[:L], gs[:L])
    gsm = np.minimum(gsm, 1.0)
    y = x * (gsm if x.ndim == 1 else gsm[:, None]).astype(np.float32)
    # final safety (numerical)
    np.clip(y, -ceil, ceil, out=y)
    return y.astype(np.float32)


# ----------------------------------------------------------------------------- loudness (BS.1770-4)


def _k_weight_sos(sr):
    if sr == 48000:
        b1 = [1.53512485958697, -2.69169618940638, 1.19839281085285]
        a1 = [1.0, -1.69065929318241, 0.73248077421585]
        b2 = [1.0, -2.0, 1.0]
        a2 = [1.0, -1.99004745483398, 0.99007225036621]
    else:
        G, fc, Q = 3.999843853973347, 1681.974450955533, 0.7071752369554196
        A = 10 ** (G / 40)
        w0 = 2 * np.pi * fc / sr
        al = np.sin(w0) / (2 * Q)
        c = np.cos(w0)
        b1 = [A * ((A + 1) + (A - 1) * c + 2 * np.sqrt(A) * al), -2 * A * ((A - 1) + (A + 1) * c),
              A * ((A + 1) + (A - 1) * c - 2 * np.sqrt(A) * al)]
        a1 = [(A + 1) - (A - 1) * c + 2 * np.sqrt(A) * al, 2 * ((A - 1) - (A + 1) * c),
              (A + 1) - (A - 1) * c - 2 * np.sqrt(A) * al]
        fc, Q = 38.13547087602444, 0.5003270373238773
        w0 = 2 * np.pi * fc / sr
        al = np.sin(w0) / (2 * Q)
        c = np.cos(w0)
        b2 = [(1 + c) / 2, -(1 + c), (1 + c) / 2]
        a2 = [1 + al, -2 * c, 1 - al]
        b1, a1 = np.array(b1) / a1[0], np.array(a1) / a1[0]
        b2, a2 = np.array(b2) / a2[0], np.array(a2) / a2[0]
    return np.vstack([np.concatenate([b1, a1]), np.concatenate([b2, a2])])


def lufs(x, sr=SR, return_blocks=False):
    """Integrated loudness (LUFS) per ITU-R BS.1770-4: K-weighting, 400 ms blocks with
    75 % overlap, absolute gate -70 LUFS and relative gate -10 LU. Mono is treated as a
    single channel (G=1). Returns -inf for silence."""
    x = np.asarray(x, dtype=np.float64)
    if x.ndim == 1:
        x = x[:, None]
    sos = _k_weight_sos(sr)
    y = signal.sosfilt(sos, x, axis=0)
    blk = int(round(0.4 * sr))
    hop = int(round(0.1 * sr))
    if len(y) < blk:
        y = np.concatenate([y, np.zeros((blk - len(y), y.shape[1]))])
    n = 1 + (len(y) - blk) // hop
    cs = np.concatenate([np.zeros((1, y.shape[1])), np.cumsum(y ** 2, axis=0)])
    idx = np.arange(n) * hop
    z = (cs[idx + blk] - cs[idx]) / blk  # mean square per block per channel
    zs = z.sum(axis=1)
    lk = -0.691 + 10 * np.log10(np.maximum(zs, 1e-30))
    g1 = lk > -70.0
    if not np.any(g1):
        return -np.inf
    rel = -0.691 + 10 * np.log10(zs[g1].mean()) - 10.0
    g2 = g1 & (lk > rel)
    L = -0.691 + 10 * np.log10(zs[g2].mean())
    return (L, lk) if return_blocks else float(L)


def short_term_max(x, sr=SR):
    """Maximum short-term (3 s) loudness in LUFS - useful for short one-shots."""
    x = np.asarray(x, dtype=np.float64)
    if x.ndim == 1:
        x = x[:, None]
    y = signal.sosfilt(_k_weight_sos(sr), x, axis=0)
    blk = int(3.0 * sr)
    if len(y) <= blk:
        return -0.691 + 10 * np.log10(max((y ** 2).mean(axis=0).sum(), 1e-30))
    hop = int(0.1 * sr)
    cs = np.concatenate([np.zeros((1, y.shape[1])), np.cumsum(y ** 2, axis=0)])
    idx = np.arange(0, len(y) - blk + 1, hop)
    z = ((cs[idx + blk] - cs[idx]) / blk).sum(axis=1)
    return float(-0.691 + 10 * np.log10(max(z.max(), 1e-30)))


def normalise_to(buf, target_lufs=-23.0, sr=SR, peak_ceiling_db=-1.0, use_limiter=True):
    """Gain `buf` to the target integrated loudness. If the result would exceed the peak
    ceiling, a limiter (use_limiter=True) or plain peak clamp gain (False) is applied."""
    buf = np.asarray(buf, dtype=np.float32)
    L = lufs(buf, sr)
    if not np.isfinite(L):
        return buf.copy()
    out = buf * float(db2amp(target_lufs - L))
    pk = np.abs(out).max()
    ceil = float(db2amp(peak_ceiling_db))
    if pk > ceil:
        out = limit(out, peak_ceiling_db, sr=sr) if use_limiter else out * (ceil / pk)
    return out.astype(np.float32)


normalize_to = normalise_to  # US spelling alias


def peak_normalise(x, peak_db=-1.0):
    x = np.asarray(x, dtype=np.float32)
    pk = np.abs(x).max()
    return x if pk == 0 else (x * (db2amp(peak_db) / pk)).astype(np.float32)


# ----------------------------------------------------------------------------- QA


def check(x, sr=SR, name=""):
    """Return a dict of QA metrics: peak dBFS, DC, LUFS, max sample jump (click detector),
    edge values."""
    x = np.asarray(x, dtype=np.float32)
    m = x if x.ndim == 1 else x
    pk = float(np.abs(m).max()) if len(m) else 0.0
    dc = float(np.abs(m.mean(axis=0)).max()) if len(m) else 0.0
    # click detector: second difference outliers relative to local level (high-passed)
    hp = highpass(as_mono(m), 3000, sr, order=2) if len(m) > 1000 else as_mono(m)
    d = np.abs(np.diff(as_mono(m))) if len(m) > 1 else np.zeros(1)
    edge = float(max(np.abs(m[:1]).max(), np.abs(m[-1:]).max())) if len(m) else 0.0
    return {
        "name": name,
        "dur_s": round(len(m) / sr, 3),
        "peak_dbfs": round(float(amp2db(pk)), 2),
        "dc": round(dc, 6),
        "lufs": round(lufs(m, sr), 2) if len(m) > 0.1 * sr else None,
        "max_step": round(float(d.max()), 4),
        "hf_peak_db": round(float(amp2db(np.abs(hp).max())), 1),
        "edge_abs": round(edge, 5),
    }


def write_wav(path, x, sr=SR, subtype="PCM_24", check_peak=True):
    """Write float32 audio. Warns if the peak exceeds -1 dBFS. Creates parent dirs."""
    import os
    x = np.asarray(x, dtype=np.float32)
    d = os.path.dirname(os.path.abspath(path))
    os.makedirs(d, exist_ok=True)
    if check_peak:
        pk = np.abs(x).max() if len(x) else 0
        if pk > db2amp(-1.0) + 1e-6:
            print(f"[mix.write_wav] warning: {path} peak {amp2db(pk):.2f} dBFS > -1 dBFS", file=sys.stderr)
    sf.write(path, x, sr, subtype=subtype)
    return path


def read_wav(path, sr=SR):
    """Read a file as float32 and resample to `sr` if needed."""
    x, fs = sf.read(path, dtype="float32", always_2d=False)
    if fs != sr:
        from fractions import Fraction
        fr = Fraction(sr, fs).limit_denominator(1000)
        x = signal.resample_poly(x, fr.numerator, fr.denominator, axis=0).astype(np.float32)
    return x


def _main(argv):
    if len(argv) < 2 or argv[1] in ("-h", "--help"):
        print(__doc__)
        return
    cmd = argv[1]
    if cmd == "loudness":
        for p in argv[2:]:
            x = read_wav(p)
            print(check(x, name=p))
    elif cmd == "normalize" or cmd == "normalise":
        x = read_wav(argv[2])
        tgt = float(argv[4]) if len(argv) > 4 else -23.0
        y = normalise_to(x, tgt)
        write_wav(argv[3], y)
        print(f"{argv[3]}: {lufs(y):.2f} LUFS, peak {amp2db(np.abs(y).max()):.2f} dBFS")
    else:
        print(__doc__)


if __name__ == "__main__":
    _main(sys.argv)
