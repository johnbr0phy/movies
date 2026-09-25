"""sampler.py - multisample instrument renderer + convolution reverb for "The Bicycle".

Quick use:
    import sampler
    ev = [dict(t=0.0, inst='piano', note='D5', vel=0.6, dur=1.0, pan=-0.2),
          dict(t=0.5, inst='strings', note=62, vel=0.5, dur=4.0, gain_db=-3)]
    y = sampler.render(ev, duration=6.0)          # stereo float32 (n, 2) at 48 kHz, dry
    y = sampler.hall(y, wet=0.25)                 # or sampler.reverb(y, wet, decay_s, ...)

CLI:
    python sampler.py list                         # instruments, ranges, layers
    python sampler.py render events.json out.wav [--duration S] [--reverb hall|room|none] [--wet 0.25]
    python sampler.py analyse                      # (re)build the per-sample analysis cache
    python sampler.py test                         # pitch-accuracy / click / coverage self test

Event dict keys (only t, inst, note are required):
    t        start time in seconds (the sample onset is trimmed so the attack lands on t)
    inst     instrument name (see INSTRUMENTS / `python sampler.py list`)
    note     MIDI int, float (microtonal) or name 'D5', 'F#4', 'Bb3' (C4 = 60, A4 = 440 Hz).
             For unpitched one-shots ('gong', 'marktree') note may be None = natural pitch.
    vel      0..1 (default 0.7): chooses the velocity layer and scales gain (vel curve ~ -37..0 dB)
    dur      seconds the key/bow is held (default: natural length for struck/plucked,
             1.0 s for sustained). A release fade (instrument default, override 'release')
             follows the note-off, so the sound lasts dur + release.
    pan      -1..1 constant-power (default 0)
    gain_db  extra gain in dB (default 0)
  optional:
    attack   seconds of fade-in (sustained instruments default to a soft bow/breath attack)
    release  seconds of release fade after dur
    width    stereo width of the (stereo) sample 0..1 (default 1)
    var      variant for one-shots: marktree 'asc'|'desc'|'fastasc'|'slowasc'|'slowdesc'|'random'
    ring     True -> ignore dur and let a struck/plucked note ring to its natural end
    detune   cents (float) added to note
"""
from __future__ import annotations

import glob
import json
import math
import os
import re
import sys
import threading
from collections import OrderedDict
from fractions import Fraction

import numpy as np
import soundfile as sf
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mix  # noqa: E402

SR = 48000
VCSL = "/home/user/sgossner/vcsl"
VSCO = "/home/user/sgossner/vsco-2-ce"
CACHE_DIR = os.path.join(HERE, "cache")
ANALYSIS_FILE = os.path.join(CACHE_DIR, "sample_analysis.json")

NOTE_BASE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def note_to_midi(n) -> float | None:
    """'D5' -> 74, 'F#4' -> 66, 'Bb3' -> 58, 62 -> 62. None -> None."""
    if n is None:
        return None
    if isinstance(n, (int, float, np.integer, np.floating)):
        return float(n)
    s = str(n).strip()
    m = re.fullmatch(r"([A-Ga-g])([#b]{0,2})(-?\d+)", s)
    if not m:
        try:
            return float(s)
        except ValueError:
            raise ValueError(f"bad note name {n!r}")
    v = NOTE_BASE[m.group(1).upper()] + m.group(2).count("#") - m.group(2).count("b")
    return float(v + 12 * (int(m.group(3)) + 1))


def midi_to_name(m: float) -> str:
    names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    r = int(round(m))
    return f"{names[r % 12]}{r // 12 - 1}"


def midi_to_hz(m):
    return 440.0 * 2.0 ** ((np.asarray(m, dtype=np.float64) - 69.0) / 12.0)


# ============================================================================ instrument registry
#
# Each spec:  paths (glob list), rx (regex with groups n = note name, l = layer, r = round robin),
#   octave: added to the octave number in the file name (VCSL/VSCO often name middle C "C3"
#   -> +1 octave; verified by measuring every library's fundamental),
#   layers: layer tokens soft -> loud, mode: 'decay' (struck/plucked, dur honoured with release),
#   'ring' (bells: ignore dur by default), 'sustain' (bowed/blown: loops for long notes),
#   'oneshot' (unpitched one-shot files), attack / release defaults (s), autotune: correct each
#   sample to its measured fundamental if within +-60 cents, gain_db: instrument trim so that
#   all instruments sit at a similar loudness for equal vel, range: comfortable sampled range.

INSTRUMENTS: dict[str, dict] = {
    "piano": dict(  # VCSL Yamaha upright - clean noise floor, 3 layers x 2 RR, C/G sampled
        paths=[f"{VCSL}/Chordophones/Zithers/Upright Piano, Yamaha/Sustains/*.wav"],
        rx=r"Upright1_Sus_(?P<n>[A-G]#?-?\d)_vl(?P<l>\d)_rr(?P<r>\d)", octave=1,
        layers=["1", "2", "3"], mode="decay", release=0.35, autotune=False, gain_db=4.5,
        desc="Yamaha upright (VCSL), sustain-pedal samples, 3 vel layers, 2 round robins"),
    "grand": dict(  # VCSL Steinway B, close mics, whole-tone sampled, long sustains
        paths=[f"{VCSL}/Chordophones/Zithers/Grand Piano, Steinway B/Sus/*.wav"],
        rx=r"JHPiano_Sus_Close_(?P<n>[A-G]#?-?\d)_vl(?P<l>\d)_rr(?P<r>\d)", octave=0,
        layers=["2", "3", "4"], mode="decay", release=0.4, autotune=False, gain_db=4.0,
        desc="Steinway B grand (VCSL), close mics, whole-tone sampled, 3 layers"),
    "zither": dict(
        paths=[f"{VCSL}/Chordophones/Zithers/Dan Tranh/Normal/*.wav"],
        rx=r"^(?P<n>[A-Ga-g]#?\d)_(?P<l>mf|ff|f)_(?P<r>\d)", octave=1,
        layers=["mf", "f", "ff"], mode="decay", release=0.5, autotune=True, gain_db=2.0,
        desc="Dan Tranh (Vietnamese 16-string zither, koto-like) normal plucks (VCSL)"),
    "ocarina": dict(
        paths=[f"{VCSL}/Aerophones/Edge-blown Aerophones/Ocarina, Typical/Sustains/Sus/*.wav"],
        rx=r"StdOcarina_Sus_(?P<n>[A-G]#?\d)", octave=1, layers=[""], mode="sustain",
        attack=0.06, release=0.25, autotune=True, gain_db=1.0, xfade=0.25,
        desc="Alto ocarina (VCSL) straight-tone sustains, looped for long notes"),
    "ocarina_vib": dict(
        paths=[f"{VCSL}/Aerophones/Edge-blown Aerophones/Ocarina, Typical/Sustains/SusVib/*.wav"],
        rx=r"StdOcarina_SusVib_(?P<n>[A-G]#?\d)", octave=1, layers=[""], mode="sustain",
        attack=0.06, release=0.25, autotune=True, gain_db=3.0, xfade=0.35,
        desc="Alto ocarina with vibrato (VCSL)"),
    "harp": dict(
        paths=[f"{VCSL}/Chordophones/Composite Chordophones/Folk Harp/*.wav"],
        rx=r"EWHarp_Normal_(?P<n>[A-G]#?\d)_v(?P<l>\d)_RR(?P<r>\d)", octave=1,
        layers=["2", "3"], mode="decay", release=0.6, autotune=True, gain_db=4.0,
        desc="Folk (lever) harp (VCSL), whole-tone sampled, 2 layers"),
    "concert_harp": dict(
        paths=[f"{VCSL}/Chordophones/Composite Chordophones/Concert Harp/*.wav"],
        rx=r"KSHarp_(?P<n>[A-G]#?\d)_(?P<l>p|mp|mf|f)(?P<r>\d)", octave=0,
        layers=["mf", "f"], layer_alias={"p": "mf", "mp": "mf"}, mode="decay", release=0.6,
        autotune=True, gain_db=1.5, desc="Concert harp (VCSL), sparse sampling"),
    "violins": dict(
        paths=[f"{VSCO}/Strings/Violin Section/susVib/*.wav"],
        rx=r"VlnEns_susVib_(?P<n>[A-G]#?\d)_v(?P<l>\d)", octave=1, layers=["1", "2"],
        mode="sustain", attack=0.35, release=0.6, autotune=True, gain_db=4.5, xfade=0.6,
        desc="Violin section sustain vibrato (VSCO2 CE)"),
    "violas": dict(
        paths=[f"{VSCO}/Strings/Viola Section/susvib/*.wav"],
        rx=r"ViolaEns_susvib_(?P<n>[A-G]#?\d)_v(?P<l>\d)_(?P<r>\d)", octave=1, layers=["1", "2"],
        mode="sustain", attack=0.35, release=0.6, autotune=True, gain_db=-1.0, xfade=0.6,
        desc="Viola section sustain vibrato (VSCO2 CE)"),
    "cellos": dict(
        paths=[f"{VSCO}/Strings/Cello Section/susvib/*.wav"],
        rx=r"^susvib_(?P<n>[A-G]#?\d)_v(?P<l>\d)_(?P<r>\d)", octave=1, layers=["1", "3"],
        mode="sustain", attack=0.35, release=0.6, autotune=True, gain_db=2.0, xfade=0.6,
        desc="Cello section sustain vibrato (VSCO2 CE)"),
    "violin": dict(
        paths=[f"{VSCO}/Strings/Solo Violin/Arco Vib/*.wav"],
        rx=r"LLVln_ArcoVib_(?P<n>[A-G]#?\d)_(?P<l>p|f)", octave=0, layers=["p", "f"],
        mode="sustain", attack=0.12, release=0.35, autotune=True, gain_db=-1.0, xfade=0.5,
        desc="Solo violin arco vibrato (VSCO2 CE)"),
    "pizz": dict(
        paths=[f"{VSCO}/Strings/Violin Section/Pizz/*.wav"],
        rx=r"VlnEns_Pizz_(?P<n>[A-G]#?\d)_v(?P<l>\d)_rr(?P<r>\d)", octave=1, layers=["1", "2"],
        mode="decay", release=0.2, autotune=True, gain_db=1.5,
        desc="Violin section pizzicato (VSCO2 CE)"),
    "flute": dict(
        paths=[f"{VSCO}/Woodwinds/Flute/susvib/*.wav"],
        rx=r"LDFlute_susvib_(?P<n>[A-G]#?\d)_v(?P<l>\d)_(?P<r>\d)", octave=1, layers=["1"],
        mode="sustain", attack=0.08, release=0.3, autotune=True, gain_db=2.0, xfade=0.4,
        desc="Flute sustain vibrato (VSCO2 CE)"),
    "flute_nv": dict(
        paths=[f"{VSCO}/Woodwinds/Flute/susNV/*.wav"],
        rx=r"LDFlute_susNV_(?P<n>[A-G]#?\d)_v(?P<l>\d)_(?P<r>\d)", octave=1, layers=["1", "2", "3"],
        mode="sustain", attack=0.08, release=0.3, autotune=True, gain_db=0.0, xfade=0.3,
        desc="Flute straight tone (VSCO2 CE)"),
    "glock": dict(
        paths=[f"{VCSL}/Idiophones/Struck Idiophones/Glockenspiel/*.wav"],
        rx=r"glock_(?P<l>soft|medium|loud)_(?P<n>[A-G]#?\d)_(?P<r>\d+)", octave=1,
        layers=["soft", "medium", "loud"], mode="ring", release=0.3, autotune=True, gain_db=0.0,
        desc="Glockenspiel (VCSL), sounding G5-C8"),
    "chimes": dict(
        paths=[f"{VCSL}/Idiophones/Struck Idiophones/Hand Chimes/*.wav"],
        rx=r"sus_(?P<n>[A-G]#?\d)_r(?P<r>\d+)", octave=1, layers=[""], mode="ring",
        release=0.5, autotune=True, gain_db=1.5, desc="Hand chimes (VCSL)"),
    "tubular": dict(
        paths=[f"{VCSL}/Idiophones/Struck Idiophones/Tubular Bells 2/*.wav"],
        rx=r"TB_hit_(?P<n>[A-G]#?\d)_v(?P<l>\d)_(?P<r>\d)", octave=0, layers=["2", "4"],
        mode="ring", release=1.0, autotune=False, gain_db=1.5,
        desc="Tubular bells (VCSL set 2), pitch = strike note"),
    "vibes": dict(
        paths=[f"{VCSL}/Idiophones/Struck Idiophones/Vibraphone/Soft Mallets/*.wav"],
        rx=r"Vibes_soft_(?P<n>[A-G]#?\d)_v(?P<l>\d)_rr(?P<r>\d)", octave=1, layers=["1", "2"],
        mode="decay", release=0.8, autotune=True, gain_db=-0.5,
        desc="Vibraphone, soft mallets, no motor (VCSL)"),
    "gong": dict(
        paths=[f"{VCSL}/Idiophones/Struck Idiophones/Gong 1/*.wav"],
        rx=r"^gong_(?P<r>2_)?(?P<l>p|mp|mf|f|fff)\.wav", octave=0,
        layers=["p", "mf", "f", "fff"], layer_alias={"mp": "p"}, mode="oneshot",
        root=49.2, release=2.0, autotune=False, gain_db=3.0,
        desc="Gong 1 (VCSL), 4 layers; note shifts relative to its natural ~140 Hz (C#3)"),
    "marktree": dict(
        paths=[f"{VCSL}/Idiophones/Struck Idiophones/Mark Trees/Legacy/*.wav"],
        rx=r"windchimes_(?P<v>\w+)\.wav", octave=0, layers=[""], mode="oneshot", root=None,
        release=1.0, autotune=False, gain_db=-1.0,
        desc="Mark tree glisses (VCSL legacy). var = asc|desc|fastasc|slowasc|slowdesc|random"),
    "harpsichord": dict(
        paths=[f"{VCSL}/Chordophones/Zithers/Harpsichord, French/Sustains/*.wav"],
        rx=r"Harpsi2_Normal_(?P<n>[A-G]#?-?\d)_rr(?P<r>\d)_Main", octave=1, layers=[""], mode="decay",
        release=0.25, autotune=True, gain_db=0.0, desc="French harpsichord (VCSL)"),
    "marimba": dict(
        paths=[f"{VCSL}/Idiophones/Struck Idiophones/Marimba/*.wav"],
        rx=r"Marimba_hit_Outrigger_(?P<n>[A-G]#?\d)_(?P<l>soft|med|loud)_(?P<r>\d+)", octave=1,
        layers=["soft", "med", "loud"], mode="decay", release=0.3, autotune=True, gain_db=0.0, desc="Marimba (VCSL)"),
    "glass": dict(
        paths=[f"{VCSL}/Idiophones/Friction Idiophones/Wine Glasses/Sustains/Slow/*.wav"],
        rx=r"glass\d_(?P<n>[A-G]#?\d)_Slow_(?P<r>\d)_Main", octave=1, layers=[""], mode="sustain",
        attack=0.35, release=1.2, autotune=True, gain_db=2.0, desc="Rubbed wine glasses (VCSL), a glass harmonica"),
    "psaltery": dict(
        paths=[f"{VCSL}/Chordophones/Zithers/Psaltery, Bowed and Plucked/LongBow/*.wav"],
        rx=r"BowedPsaltery_(?P<n>[A-G]#?\d)_Main_LongBow_rr(?P<r>\d)", octave=1, layers=[""], mode="sustain",
        attack=0.25, release=0.9, autotune=True, gain_db=0.0, desc="Bowed psaltery (VCSL)"),
    "organ": dict(
        paths=[f"{VCSL}/Aerophones/Edge-blown Aerophones/Pipe Organ/Quiet/*.wav"],
        rx=r"NT5_Man3Quiet_(?P<n>[A-G]#?\d)_rr(?P<r>\d)", octave=1, layers=[""], mode="sustain",
        attack=0.12, release=0.6, autotune=True, gain_db=-2.0, desc="Pipe organ, quiet manual (VCSL)"),
}

# 'strings' and 'cello are composites / aliases resolved at render time
COMPOSITES = {
    "strings": "String section pad: violins / violas / cellos blended by register, slow attack, looped",
    "cello": "Cello section (alias of 'cellos' with a slightly quicker attack)",
}

VEL_FLOOR = 0.12  # amplitude = (VEL_FLOOR + (1-VEL_FLOOR)*vel)^2  -> vel 0 = -37 dB


def vel_gain(vel: float) -> float:
    v = float(np.clip(vel, 0.0, 1.0))
    return (VEL_FLOOR + (1 - VEL_FLOOR) * v) ** 2


# ============================================================================ analysis

_lock = threading.Lock()
_analysis: dict | None = None
_raw_cache: "OrderedDict[str, tuple[np.ndarray,int]]" = OrderedDict()
_note_cache: "OrderedDict[tuple, np.ndarray]" = OrderedDict()
_NOTE_CACHE_BYTES = 600 * 1024 * 1024
_RAW_CACHE_BYTES = 800 * 1024 * 1024
_rr_state: dict = {}
_inst_files: dict = {}


def _load_raw(path):
    """Load a sample file as float32 stereo (n,2) at its native rate (cached)."""
    if path in _raw_cache:
        _raw_cache.move_to_end(path)
        return _raw_cache[path]
    x, fs = sf.read(path, dtype="float32", always_2d=True)
    if x.shape[1] == 1:
        x = np.repeat(x, 2, axis=1)
    x = x[:, :2]
    _raw_cache[path] = (x, fs)
    tot = sum(v[0].nbytes for v in _raw_cache.values())
    while tot > _RAW_CACHE_BYTES and len(_raw_cache) > 1:
        k, v = _raw_cache.popitem(last=False)
        tot -= v[0].nbytes
    return x, fs


def _env_db(m, fs, win=0.02):
    h = max(1, int(win * fs))
    n = len(m) // h
    if n == 0:
        return np.array([-120.0]), h
    e = np.sqrt((m[: n * h].reshape(n, h) ** 2).mean(axis=1) + 1e-20)
    return 20 * np.log10(e), h


def _measure_peak_freq(m, fs, f_nom, t0, t1):
    """Precise spectral peak within +-70 cents of f_nom using a long Hann window
    and parabolic interpolation on log magnitude. Returns (freq, prominence_db)."""
    a, b = int(t0 * fs), int(t1 * fs)
    seg = m[a:b]
    if len(seg) < int(0.08 * fs):
        return None, -99
    seg = seg * np.hanning(len(seg))
    nfft = 1 << int(math.ceil(math.log2(len(seg) * 8)))
    S = np.abs(np.fft.rfft(seg, nfft))
    fr = np.fft.rfftfreq(nfft, 1 / fs)
    lo, hi = f_nom * 2 ** (-0.7 / 12), f_nom * 2 ** (0.7 / 12)
    band = np.where((fr >= lo) & (fr <= hi))[0]
    if len(band) < 3:
        return None, -99
    j = band[np.argmax(S[band])]
    if 0 < j < len(S) - 1:
        la, lb, lc = np.log(S[j - 1] + 1e-12), np.log(S[j] + 1e-12), np.log(S[j + 1] + 1e-12)
        d = 0.5 * (la - lc) / (la - 2 * lb + lc) if (la - 2 * lb + lc) != 0 else 0.0
    else:
        d = 0.0
    f = (j + d) * fs / nfft
    prom = 20 * np.log10(S[j] / (S.max() + 1e-12))
    return float(f), float(prom)


def _align_lag(x, fs, on):
    """Spaced-pair samples are sometimes near anti-phase at the fundamental (L/R correlation
    down to -0.9 -> the note vanishes in mono). Find the R-channel shift within +-1.2 ms that
    maximises L/R correlation over the first 0.8 s; returns (lag, c0, c_best)."""
    a = on + int(0.005 * fs)
    b = min(x.shape[0], a + int(0.8 * fs))
    L = x[a:b, 0].astype(np.float64)
    R = x[a:b, 1].astype(np.float64)
    if len(L) < int(0.05 * fs):
        return 0, 1.0, 1.0
    M = int(0.0012 * fs)
    Lc = L[M:len(L) - M]
    best, cb = 0, -2.0
    c0 = float(np.dot(Lc, R[M:len(R) - M]) / math.sqrt(np.dot(Lc, Lc) * np.dot(R[M:len(R) - M], R[M:len(R) - M]) + 1e-20))
    for lag in range(-M, M + 1):
        Rs = R[M + lag:len(R) - M + lag]
        c = float(np.dot(Lc, Rs) / math.sqrt(np.dot(Lc, Lc) * np.dot(Rs, Rs) + 1e-20))
        if c > cb:
            best, cb = lag, c
    return best, c0, cb


def analyse_file(path, nominal, mode, autotune):
    x, fs = _load_raw(path)
    # level / envelope from channel power (robust to anti-phase stereo), pitch from L+R aligned
    m = np.sqrt(0.5 * (x[:, 0].astype(np.float64) ** 2 + x[:, 1].astype(np.float64) ** 2)) * np.sign(x[:, 0] + x[:, 1] + 1e-12)
    a = np.abs(m)
    pk = float(a.max()) + 1e-12
    thr = pk * 10 ** (-40 / 20)
    on = int(np.argmax(a > thr))
    on = max(0, on - int(0.0015 * fs))
    env, h = _env_db(m, fs)
    emax = env.max()
    # tail: last frame above max-72 dB (or noise floor + 6 dB)
    floor = np.percentile(env[-max(3, len(env) // 20):], 50)
    cut_db = max(emax - 72, floor + 6)
    above = np.where(env > cut_db)[0]
    end = int(min(len(m), (above[-1] + 2) * h)) if len(above) else len(m)
    info = dict(onset=on, end=end, fs=fs, peak=pk, n=len(m))
    lag, c0, cb = _align_lag(x, fs, on)
    info["lr_corr"] = round(c0, 3)
    info["align"] = int(lag) if (c0 < 0.5 and cb - c0 > 0.2) else 0
    if info["align"]:
        info["lr_corr_aligned"] = round(cb, 3)
    R = np.roll(x[:, 1], -info["align"]) if info["align"] else x[:, 1]
    msig = x[:, 0].astype(np.float64) + R
    # level + steady region
    if mode == "sustain":
        fi0 = on // h
        seg = env[fi0: end // h]
        smax = seg.max()
        att = int(np.argmax(seg > smax - 4))
        med = np.median(seg[att:]) if len(seg) > att else smax
        good = np.where(seg[att:] > med - 5)[0]
        rel = att + (good[-1] if len(good) else len(seg) - att - 1)
        s0 = on + (att * h) + int(0.25 * fs)
        s1 = on + (rel * h) - int(0.25 * fs)
        if s1 - s0 < int(0.8 * fs):
            L = end - on
            s0, s1 = on + int(0.3 * L), on + int(0.8 * L)
        info["loop"] = [int(s0), int(s1)]
        # level over what typical notes (0.3 .. 2.5 s) actually play: soft layers often swell
        # slowly, so measuring the late steady part would make short soft notes too quiet
        a0, a1 = on + int(0.3 * fs), min(end, on + int(2.5 * fs))
        lvl = 20 * np.log10(np.sqrt((m[a0:a1] ** 2).mean()) + 1e-12)
        # tune on what is actually heard for typical note lengths: 0.35 .. 3.85 s after onset
        t0 = on / fs + 0.35
        t1 = max(t0 + 0.5, min(end / fs - 0.2, t0 + 3.5))
    elif mode == "oneshot":
        # loudest 0.4 s window (glisses / swells build up after the onset)
        w = int(0.4 * fs)
        cs = np.concatenate([[0.0], np.cumsum(m[on:end].astype(np.float64) ** 2)])
        if len(cs) > w + 1:
            ms = (cs[w:] - cs[:-w]) / w
            lvl = 10 * np.log10(ms.max() + 1e-20)
        else:
            lvl = 10 * np.log10((m[on:end] ** 2).mean() + 1e-20)
        t0, t1 = on / fs + 0.1, on / fs + 0.6
    else:
        seg = m[on: on + int(0.25 * fs)]
        lvl = 20 * np.log10(np.sqrt((seg ** 2).mean()) + 1e-12)
        # plucked/struck strings go sharp during the attack (tension modulation): measure the
        # settled pitch from 0.25 s on (or earlier for very short samples)
        L = (end - on) / fs
        t0 = on / fs + min(0.25, 0.2 * L)
        t1 = t0 + min(1.0, max(0.15, 0.5 * L))
    info["level_db"] = float(lvl)
    info["pitch"] = nominal
    info["tune_cents"] = 0.0
    if autotune and nominal is not None:
        f, prom = _measure_peak_freq(msig, fs, float(midi_to_hz(nominal)), t0, t1)
        if f is not None and prom > -30:
            cents = 1200 * math.log2(f / float(midi_to_hz(nominal)))
            if abs(cents) < 60:
                info["pitch"] = nominal + cents / 100.0
                info["tune_cents"] = round(cents, 2)
    return info


def _scan(name):
    """Return list of dicts {path, midi, layer, rr, var} for an instrument."""
    if name in _inst_files:
        return _inst_files[name]
    spec = INSTRUMENTS[name]
    rx = re.compile(spec["rx"])
    out = []
    for pat in spec["paths"]:
        for p in sorted(glob.glob(pat)):
            b = os.path.basename(p)
            mm = rx.search(b)
            if not mm:
                continue
            g = mm.groupdict()
            midi = None
            if g.get("n"):
                nm = g["n"]
                nn = re.fullmatch(r"([A-Ga-g])(#?)(-?\d)", nm)
                midi = NOTE_BASE[nn.group(1).upper()] + (1 if nn.group(2) else 0) + 12 * (int(nn.group(3)) + 1)
                midi += 12 * spec.get("octave", 0)
            elif spec.get("root") is not None:
                midi = spec["root"]
            layer = g.get("l") or ""
            layer = spec.get("layer_alias", {}).get(layer, layer)
            if layer not in spec["layers"]:
                continue
            out.append(dict(path=p, midi=midi, layer=layer, rr=g.get("r") or "1", var=g.get("v")))
    _inst_files[name] = out
    return out


def _load_analysis():
    global _analysis
    if _analysis is None:
        if os.path.exists(ANALYSIS_FILE):
            with open(ANALYSIS_FILE) as f:
                _analysis = json.load(f)
        else:
            _analysis = {}
    return _analysis


def _save_analysis():
    os.makedirs(CACHE_DIR, exist_ok=True)
    tmp = ANALYSIS_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(_analysis, f, indent=0)
    os.replace(tmp, ANALYSIS_FILE)


def instrument_samples(name):
    """List of analysed samples for an instrument (analysis cached on disk)."""
    spec = INSTRUMENTS[name]
    A = _load_analysis()
    files = _scan(name)
    dirty = False
    res = []
    for f in files:
        st = os.stat(f["path"])
        key = f"{name}|{f['path']}"
        rec = A.get(key)
        sig = f"{st.st_size}:{int(st.st_mtime)}"
        if rec is None or rec.get("sig") != sig:
            info = analyse_file(f["path"], f["midi"], spec["mode"], spec.get("autotune", False))
            info["sig"] = sig
            A[key] = info
            rec = info
            dirty = True
        r = dict(f)
        r.update(rec)
        res.append(r)
    if dirty:
        _save_analysis()
    # level normalisation: fit level trend vs pitch per instrument (all layers pooled after
    # removing per-layer means), correct each sample to trend (clip +-9 dB) and align layers.
    if "norm" not in spec:
        lv = np.array([r["level_db"] for r in res])
        pitches = np.array([r["pitch"] if r["pitch"] is not None else 60.0 for r in res])
        layers = np.array([r["layer"] for r in res])
        resid = lv.copy()
        for L in set(layers):
            k = layers == L
            resid[k] -= lv[k].mean()
        if len(set(pitches)) > 2:
            slope, icpt = np.polyfit(pitches, resid, 1)
            slope = float(np.clip(slope, -0.35, 0.35))
        else:
            slope, icpt = 0.0, 0.0
        trend = slope * (pitches - pitches.mean())
        ref = -20.0
        for r, l, t in zip(res, lv, trend):
            # target: -20 dBFS (steady / attack RMS) +- register trend; correction clipped
            corr = float(np.clip(ref + t - l, -30, 30))
            r["norm_db"] = corr
        spec["norm"] = {r["path"]: r["norm_db"] for r in res}
        spec["slope"] = slope
    else:
        for r in res:
            r["norm_db"] = spec["norm"][r["path"]]
    return res


# ============================================================================ note rendering


def _resample(x, fs_in, ratio_pitch, sr=SR):
    """Resample x (n,2) so that played at `sr` it is transposed by ratio_pitch."""
    q = (sr / fs_in) / ratio_pitch  # output samples per input sample
    if abs(q - 1.0) < 1e-9:
        return x.astype(np.float32)
    fr = Fraction(q).limit_denominator(1000)
    up, down = fr.numerator, fr.denominator
    y = signal.resample_poly(x, up, down, axis=0, window=("kaiser", 8.0))
    return y.astype(np.float32)


def _pick_sample(name, midi, vel, var=None):
    """Nearest sampled pitch first, then the available velocity layer closest to `vel`,
    then round-robin among the remaining takes."""
    samples = instrument_samples(name)
    spec = INSTRUMENTS[name]
    layers = spec["layers"]
    if var is not None:
        cand = [s for s in samples if s.get("var") and var.lower() in s["var"].lower()]
        if cand:
            samples = cand
    want = min(len(layers) - 1, int(float(np.clip(vel, 0, 1)) * len(layers) * 0.9999))
    if midi is not None and any(s["pitch"] is not None for s in samples):
        groups = {}
        for s in samples:
            groups.setdefault(s["midi"], []).append(s)
        key_m = min(groups, key=lambda g: (min(abs(s["pitch"] - midi) for s in groups[g]), g))
        pool = groups[key_m]
    else:
        pool = samples
    avail = sorted(set(layers.index(s["layer"]) for s in pool))
    li = min(avail, key=lambda a: (abs(a - want), -a))
    pool = [s for s in pool if layers.index(s["layer"]) == li]
    key = (name, li, pool[0]["midi"], var)
    i = _rr_state.get(key, -1) + 1
    _rr_state[key] = i
    return pool[i % len(pool)]


def _loop_extend(y, s0, s1, need, xf):
    """Extend y beyond s1 by repeatedly splicing copies of y[s0:s1] with correlation-aligned,
    power-compensated crossfades of xf samples. Returns array of length >= need."""
    if len(y) >= need or s1 - s0 < 3 * xf:
        if len(y) >= need:
            return y
        # fallback: simple repetition of the whole available body
        s0, s1 = int(len(y) * 0.3), int(len(y) * 0.8)
        xf = min(xf, (s1 - s0) // 3)
        if xf < 16:
            return np.concatenate([y, np.zeros((need - len(y), 2), np.float32)])
    out = y[:s1].copy()
    mono = y.mean(axis=1)
    seg_len = s1 - s0
    k = 0
    rng = np.random.default_rng(len(y))
    while len(out) < need:
        # choose a start inside the loop region (vary to avoid obvious repetition)
        max_start = s0 + max(0, (seg_len - 3 * xf) // 2)
        st = int(rng.integers(s0, max_start + 1))
        tail = out[-xf:].mean(axis=1)
        # align: search +-20 ms around st for max normalised correlation
        srch = int(0.02 * SR)
        a0 = max(s0, st - srch)
        a1 = min(s1 - xf, st + srch)
        best, bc = st, -2.0
        if a1 > a0:
            win = mono[a0:a1 + xf]
            c = signal.correlate(win, tail, mode="valid")
            e = np.sqrt(np.convolve(win ** 2, np.ones(xf), mode="valid") * (tail ** 2).sum() + 1e-20)
            nc = c / e
            j = int(np.argmax(nc))
            best, bc = a0 + j, float(nc[j])
        piece = y[best: s1]
        rho = float(np.clip(bc, 0.0, 1.0))
        t = (np.arange(xf) + 0.5) / xf
        fi = 0.5 - 0.5 * np.cos(np.pi * t)
        fo = 1 - fi
        g = 1.0 / np.sqrt(fi ** 2 + fo ** 2 + 2 * rho * fi * fo)
        mixed = (out[-xf:] * (fo * g)[:, None] + piece[:xf] * (fi * g)[:, None])
        out = np.concatenate([out[:-xf], mixed, piece[xf:]])
        k += 1
        if k > 400:
            break
    return out


def _cached_shift(s, midi_target, sr=SR):
    key = (s["path"], round(midi_target, 4) if midi_target is not None else None)
    if key in _note_cache:
        _note_cache.move_to_end(key)
        return _note_cache[key]
    x, fs = _load_raw(s["path"])
    lag = s.get("align", 0)
    if lag:
        # shift R by `lag` samples (R[n] <- R[n+lag]) to undo the spaced-pair delay
        x = x.copy()
        if lag > 0:
            x[:-lag, 1] = x[lag:, 1]
            x[-lag:, 1] = 0
        else:
            x[-lag:, 1] = x[:lag, 1]
            x[:-lag, 1] = 0
    x = x[s["onset"]: s["end"]]
    if midi_target is None or s["pitch"] is None:
        ratio = 1.0
    else:
        ratio = 2 ** ((midi_target - s["pitch"]) / 12.0)
    y = _resample(x, fs, ratio, sr)
    # 1 ms fade in (onset is already trimmed with 1.5 ms margin) + fade at the trimmed end
    y = mix.fade_in(y, 0.001, sr)
    y = mix.fade_out(y, min(0.05, len(y) / sr / 4), sr)
    y *= float(mix.db2amp(s["norm_db"]))
    _note_cache[key] = y
    tot = sum(v.nbytes for v in _note_cache.values())
    while tot > _NOTE_CACHE_BYTES and len(_note_cache) > 1:
        _, v = _note_cache.popitem(last=False)
        tot -= v.nbytes
    return y


def render_note(inst, note=None, vel=0.7, dur=None, sr=SR, attack=None, release=None,
                ring=False, var=None, detune=0.0):
    """Render one note (stereo float32, dry, not panned). Onset is at sample 0."""
    if inst == "cello":
        inst = "cellos"
        attack = 0.15 if attack is None else attack
    if inst == "strings":
        return _render_strings(note, vel, dur, sr, attack, release)
    if inst not in INSTRUMENTS:
        raise KeyError(f"unknown instrument {inst!r}; have {sorted(list(INSTRUMENTS) + list(COMPOSITES))}")
    spec = INSTRUMENTS[inst]
    midi = note_to_midi(note)
    if midi is not None:
        midi += detune / 100.0
    s = _pick_sample(inst, midi, vel, var)
    target = midi
    if spec["mode"] == "oneshot" and (midi is None or s["pitch"] is None):
        target = None
    y = _cached_shift(s, target, sr)
    ratio_len = sr / s["fs"] / (2 ** (((target if target is not None else (s["pitch"] or 0)) - (s["pitch"] or 0)) / 12))
    mode = spec["mode"]
    rel = spec.get("release", 0.3) if release is None else release
    att = spec.get("attack", 0.0) if attack is None else attack
    if mode == "sustain":
        d = 1.0 if dur is None else float(dur)
        need = int((d + rel) * sr) + 1
        lo, hi = s["loop"]
        l0 = int((lo - s["onset"]) * ratio_len)
        l1 = int((hi - s["onset"]) * ratio_len)
        l1 = min(l1, len(y))
        xf = int(spec.get("xfade", 0.4) * sr)
        y = _loop_extend(y, l0, l1, need, xf)[:need].copy()
        if att > 0:
            y = mix.fade_in(y, att, sr, "sqrt")
        y = _release(y, d, rel, sr)
    elif mode in ("decay", "ring", "oneshot"):
        if dur is None or ring or (mode in ("ring", "oneshot") and dur is None):
            y = y.copy()
        elif mode in ("ring", "oneshot"):
            # bells: dur only shortens if explicitly given AND shorter than natural ring
            y = _release(y[: int((float(dur) + rel) * sr)].copy(), float(dur), rel, sr)
        else:
            y = _release(y[: int((float(dur) + rel) * sr)].copy(), float(dur), rel, sr)
        if att > 0:
            y = mix.fade_in(y, att, sr, "sqrt")
    g = vel_gain(vel) * float(mix.db2amp(spec.get("gain_db", 0.0)))
    return (y * g).astype(np.float32)


def _release(y, dur, rel, sr):
    n0 = int(dur * sr)
    if n0 >= len(y):
        return mix.fade_out(y, min(0.05, len(y) / sr / 4), sr)
    nr = max(16, int(rel * sr))
    y = y[: n0 + nr].copy()
    k = len(y) - n0
    t = (np.arange(k) + 0.5) / nr
    # exponential-ish release (fast then tail) ending exactly at zero
    c = np.clip((np.exp(-4.0 * t) - np.exp(-4.0)) / (1 - np.exp(-4.0)), 0, 1)
    y[n0:] *= c[:, None]
    return y


def _render_strings(note, vel, dur, sr, attack, release):
    """Register-blended string section: weights cellos/violas/violins by pitch."""
    midi = note_to_midi(note)
    att = 0.45 if attack is None else attack
    rel = 0.9 if release is None else release
    w = {
        "cellos": float(np.clip((62 - midi) / 10, 0, 1)),
        "violas": float(max(0.0, 1 - abs(midi - 62) / 10)),
        "violins": float(np.clip((midi - 60) / 8, 0, 1)),
    }
    # hard limits of the sampled ranges
    if midi > 86:
        w["violas"] = 0
    if midi > 80:
        w["cellos"] = 0
    if midi < 55:
        w["violins"] = 0
    tot = math.sqrt(sum(v * v for v in w.values())) or 1.0
    out = None
    for inst, wt in w.items():
        if wt <= 1e-3:
            continue
        y = render_note(inst, midi, vel, dur, sr, attack=att, release=rel) * (wt / tot)
        if out is None:
            out = y
        else:
            n = max(len(out), len(y))
            o = np.zeros((n, 2), np.float32)
            o[: len(out)] += out
            o[: len(y)] += y
            out = o
    return out


def render(events, duration=None, sr=SR, verbose=False):
    """Render a list of event dicts to a dry stereo float32 buffer (n, 2).

    duration: seconds (default: end of the last note + 0.5 s). Notes are cropped at the end.
    """
    evs = list(events)
    notes = []
    end = 0.0
    for e in evs:
        y = render_note(e["inst"], e.get("note"), e.get("vel", 0.7), e.get("dur"), sr,
                        attack=e.get("attack"), release=e.get("release"), ring=e.get("ring", False),
                        var=e.get("var"), detune=e.get("detune", 0.0))
        y = mix.pan_stereo(y, e.get("pan", 0.0), e.get("width", 1.0))
        y *= float(mix.db2amp(e.get("gain_db", 0.0)))
        notes.append((float(e["t"]), y))
        end = max(end, float(e["t"]) + len(y) / sr)
    if duration is None:
        duration = end + 0.5
    buf = np.zeros((int(round(duration * sr)), 2), np.float32)
    for t, y in notes:
        s = int(round(t * sr))
        if s >= len(buf):
            continue
        a = max(0, -s)
        n = min(len(y) - a, len(buf) - max(s, 0))
        if n > 0:
            buf[max(s, 0): max(s, 0) + n] += y[a: a + n]
    if verbose:
        print(f"rendered {len(evs)} events, {duration:.2f}s, peak {mix.amp2db(np.abs(buf).max()):.1f} dBFS")
    return buf


# ============================================================================ reverb

_ir_cache: dict = {}


def make_ir(decay_s=2.0, predelay_ms=20.0, size=0.6, damping=0.5, lowcut=80.0, highcut=12000.0,
            sr=SR, seed=11, er_level=0.35):
    """Synthetic true-stereo impulse response set -> array (n, 4) = [LL, LR, RL, RR].

    Late tail: decorrelated noise split into octave bands, each decaying with its own RT60
    (damping shortens the highs: RT(f) = decay_s / (1 + damping*log2(f/1k)) above 1 kHz,
    lows slightly longer), with a density build-up of 10..60 ms depending on size.
    Early reflections: 6..22 low-passed taps spread over 4..(12+70*size) ms, alternating sides.
    Each IR is energy-normalised so the wet signal has roughly the dry signal's loudness."""
    key = (round(decay_s, 3), round(predelay_ms, 2), round(size, 3), round(damping, 3),
           round(lowcut, 1), round(highcut, 1), sr, seed, round(er_level, 3))
    if key in _ir_cache:
        return _ir_cache[key]
    rng = np.random.default_rng(seed)
    T = decay_s * 1.15 + 0.05
    n = int(T * sr)
    t = np.arange(n) / sr
    centers = [63, 125, 250, 500, 1000, 2000, 4000, 8000, 16000]
    irs = np.zeros((n, 4))
    build = (0.010 + 0.05 * size)
    for ch in range(4):
        noise = rng.standard_normal(n)
        tail = np.zeros(n)
        for fc in centers:
            lo, hi = fc / math.sqrt(2), min(fc * math.sqrt(2), sr / 2 * 0.98)
            if lo >= sr / 2 * 0.95:
                continue
            if fc == centers[0]:
                sos = signal.butter(2, hi / (sr / 2), "lowpass", output="sos")
            elif fc == centers[-1]:
                sos = signal.butter(2, lo / (sr / 2), "highpass", output="sos")
            else:
                sos = signal.butter(2, [lo / (sr / 2), hi / (sr / 2)], "bandpass", output="sos")
            b = signal.sosfilt(sos, noise)
            oct_ = math.log2(fc / 1000.0)
            rt = decay_s / (1 + damping * oct_) if oct_ > 0 else decay_s * (1 + 0.08 * (-oct_) * (1 - damping))
            rt = max(rt, 0.05)
            tail += b * np.exp(-6.9078 * t / rt)
        tail *= 1 - np.exp(-t / build)
        # early reflections
        er = np.zeros(n)
        k = int(6 + 16 * size)
        span = 0.004 + (0.012 + 0.07 * size)
        times = np.sort(rng.uniform(0.003, span, k))
        for i, tt in enumerate(times):
            side = (i + ch) % 2
            g = er_level * rng.uniform(0.5, 1.0) * math.exp(-tt / span) * (1.0 if side == 0 else 0.6)
            idx = int(tt * sr)
            if idx < n:
                er[idx] += g * (1 if rng.random() > 0.3 else -1)
        er = signal.sosfilt(signal.butter(2, min(6000 + 6000 * (1 - damping), sr / 2 * 0.9) / (sr / 2), output="sos"), er)
        ir = tail / math.sqrt((tail ** 2).sum() + 1e-20) + er * 1.0
        irs[:, ch] = ir
    # band limit
    sos = signal.butter(2, [max(lowcut, 10) / (sr / 2), min(highcut, sr / 2 * 0.95) / (sr / 2)], "bandpass", output="sos")
    irs = signal.sosfiltfilt(sos, irs, axis=0)
    # fade the very end
    fl = int(0.05 * sr)
    irs[-fl:] *= np.linspace(1, 0, fl)[:, None]
    for ch in range(4):
        irs[:, ch] /= math.sqrt((irs[:, ch] ** 2).sum() + 1e-20)
    pd = int(predelay_ms / 1000 * sr)
    irs = np.concatenate([np.zeros((pd, 4)), irs]).astype(np.float32)
    _ir_cache[key] = irs
    return irs


def reverb(x, wet=0.25, decay_s=2.0, predelay_ms=20.0, lowcut=100.0, highcut=9000.0,
           size=0.6, damping=0.5, cross=0.55, keep_tail=False, sr=SR, seed=11):
    """Convolution reverb with a synthetic stereo IR.

    x: mono or stereo. wet: 0..1 mix (out = (1-wet)*dry + wet*reverb; wet=1 -> reverb only,
    useful for send busses). decay_s: RT60 in seconds. predelay_ms. lowcut/highcut: IR band
    (Hz). size 0..1 (early reflection spread / density build-up). damping 0..1 (HF decays faster).
    cross: amount of L->R / R->L spread. keep_tail: if True, output is extended by the IR
    length; otherwise output has the input's length (render with room for the tail!)."""
    xs = mix.as_stereo(np.asarray(x, dtype=np.float32)).astype(np.float64)
    ir = make_ir(decay_s, predelay_ms, size, damping, lowcut, highcut, sr, seed).astype(np.float64)
    n_out = len(xs) + len(ir) - 1
    L = signal.oaconvolve(xs[:, 0], ir[:, 0]) + cross * signal.oaconvolve(xs[:, 1], ir[:, 2])
    R = signal.oaconvolve(xs[:, 1], ir[:, 3]) + cross * signal.oaconvolve(xs[:, 0], ir[:, 1])
    w = np.stack([L, R], axis=1) / math.sqrt(1 + cross ** 2)
    dry = np.zeros((n_out, 2))
    dry[: len(xs)] = xs
    out = (1 - wet) * dry + wet * w
    if not keep_tail:
        out = out[: len(xs)]
    return out.astype(np.float32)


PRESETS = {
    "room": dict(decay_s=0.7, predelay_ms=6.0, size=0.25, damping=0.6, lowcut=120.0, highcut=9000.0),
    "hall": dict(decay_s=2.6, predelay_ms=24.0, size=0.85, damping=0.45, lowcut=90.0, highcut=10000.0),
    "temple": dict(decay_s=3.8, predelay_ms=35.0, size=1.0, damping=0.55, lowcut=70.0, highcut=8000.0),
    "street": dict(decay_s=1.1, predelay_ms=12.0, size=0.5, damping=0.7, lowcut=150.0, highcut=7000.0),
    "plate": dict(decay_s=1.8, predelay_ms=10.0, size=0.4, damping=0.3, lowcut=150.0, highcut=12000.0),
}


def room(x, wet=0.2, keep_tail=False, sr=SR):
    return reverb(x, wet=wet, keep_tail=keep_tail, sr=sr, **PRESETS["room"])


def hall(x, wet=0.25, keep_tail=False, sr=SR):
    return reverb(x, wet=wet, keep_tail=keep_tail, sr=sr, **PRESETS["hall"])


def preset(x, name, wet=0.25, keep_tail=False, sr=SR):
    return reverb(x, wet=wet, keep_tail=keep_tail, sr=sr, **PRESETS[name])


# ============================================================================ info / tests


def instrument_names():
    return sorted(list(INSTRUMENTS) + list(COMPOSITES))


def instrument_info(name):
    if name in COMPOSITES:
        return dict(name=name, desc=COMPOSITES[name])
    spec = INSTRUMENTS[name]
    ss = instrument_samples(name)
    ps = sorted(set(round(s["pitch"], 2) for s in ss if s["pitch"] is not None))
    return dict(name=name, desc=spec.get("desc", ""), mode=spec["mode"], layers=spec["layers"],
                n_samples=len(ss), lowest=midi_to_name(ps[0]) if ps else None,
                highest=midi_to_name(ps[-1]) if ps else None,
                sampled_midi=sorted(set(int(round(p)) for p in ps)),
                max_tune_cents=max([abs(s["tune_cents"]) for s in ss] or [0]))


def estimate_f0(y, sr=SR, f_guess=None, win=1.0):
    """Fundamental estimate: autocorrelation (coarse) + interpolated FFT peak (fine)."""
    m = mix.as_mono(y).astype(np.float64)
    seg = m[int(0.15 * sr): int(0.15 * sr) + int(win * sr)]
    if f_guess is None:
        r = np.fft.irfft(np.abs(np.fft.rfft(seg, 2 * len(seg))) ** 2)[: len(seg)]
        lmin, lmax = int(sr / 3000), int(sr / 40)
        f_guess = sr / (lmin + np.argmax(r[lmin:lmax]))
    f, _ = _measure_peak_freq(seg, sr, f_guess, 0, len(seg) / sr)
    return f


def self_test():
    ok = True
    print("== pitch accuracy (render A4, expect 440 Hz within 5 cents)")
    for inst in ["piano", "grand", "zither", "ocarina", "harp", "strings", "cello", "violin", "flute", "vibes", "chimes"]:
        note = 69
        sus = inst in ("ocarina", "strings", "cello", "violin", "flute")
        y = render_note(inst, note, 0.7, 4.0 if sus else 2.0)
        f = estimate_f0(y[int(0.4 * SR):] if sus else y, SR, 440.0, 3.0 if sus else 1.0)
        c = 1200 * math.log2(f / 440.0)
        flag = "OK " if abs(c) < 5 else "BAD"
        ok &= abs(c) < 5
        print(f"  {flag} {inst:10s} {f:8.2f} Hz  {c:+.2f} cents")
    y = render_note("glock", 91, 0.7)
    f = estimate_f0(y, SR, float(midi_to_hz(91)))
    print(f"  glock G6 expect {midi_to_hz(91):.1f}: {f:.1f} ({1200*math.log2(f/midi_to_hz(91)):+.2f} c)")
    print("== coverage MIDI 48..96 (max shift in semitones from nearest sample)")
    for inst in sorted(INSTRUMENTS):
        ss = instrument_samples(inst)
        ps = [s["pitch"] for s in ss if s["pitch"] is not None]
        if not ps:
            print(f"  {inst:13s} unpitched one-shot")
            continue
        worst = max(min(abs(p - m) for p in ps) for m in range(48, 97))
        print(f"  {inst:13s} sampled {midi_to_name(min(ps)):>4s}..{midi_to_name(max(ps)):<4s} worst shift in 48-96: {worst:5.2f} st")
    print("== clicks/edges")
    for inst in instrument_names():
        y = render_note(inst, 62 if inst not in ("glock",) else 86, 0.8, 0.5)
        edge = float(np.abs(y[-1]).max())
        st = float(np.abs(np.diff(y, axis=0)).max())
        print(f"  {inst:13s} len {len(y)/SR:5.2f}s  end {edge:.2e}  start {float(np.abs(y[0]).max()):.2e} max step {st:.3f}")
    return ok


def _main(argv):
    if len(argv) < 2 or argv[1] in ("-h", "--help"):
        print(__doc__)
        return
    cmd = argv[1]
    if cmd == "list":
        for n in instrument_names():
            print(json.dumps(instrument_info(n)))
    elif cmd == "analyse":
        for n in INSTRUMENTS:
            instrument_samples(n)
        print("analysis cached ->", ANALYSIS_FILE)
    elif cmd == "test":
        self_test()
    elif cmd == "render":
        import argparse
        ap = argparse.ArgumentParser()
        ap.add_argument("events")
        ap.add_argument("out")
        ap.add_argument("--duration", type=float, default=None)
        ap.add_argument("--reverb", default="hall")
        ap.add_argument("--wet", type=float, default=0.25)
        a = ap.parse_args(argv[2:])
        with open(a.events) as f:
            ev = json.load(f)
        y = render(ev, a.duration, verbose=True)
        if a.reverb != "none":
            y = preset(y, a.reverb, a.wet)
        pk = np.abs(y).max()
        if pk > mix.db2amp(-1):
            y = mix.limit(y, -1.0)
        mix.write_wav(a.out, y)
        print("wrote", a.out)
    else:
        print(__doc__)


if __name__ == "__main__":
    _main(sys.argv)
