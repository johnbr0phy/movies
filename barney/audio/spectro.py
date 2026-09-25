"""spectro.py - spectrogram / waveform PNGs for inspecting audio without listening.

    python spectro.py in.wav [out.png] [--fmax 12000] [--log]
    spectro.spectrogram_png(x, 'out.png', title='...', fmax=12000, sr=48000, marks=[(t,'label')])
"""
from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mix  # noqa: E402

SR = 48000


def stft_db(x, sr=SR, nfft=2048, hop=None):
    m = mix.as_mono(x).astype(np.float64)
    hop = hop or nfft // 4
    if len(m) < nfft:
        m = np.pad(m, (0, nfft - len(m)))
    n = 1 + (len(m) - nfft) // hop
    idx = np.arange(nfft)[None, :] + hop * np.arange(n)[:, None]
    w = np.hanning(nfft)
    S = np.abs(np.fft.rfft(m[idx] * w, axis=1)) / (w.sum() / 2)
    return 20 * np.log10(S + 1e-10).T, np.fft.rfftfreq(nfft, 1 / sr), (np.arange(n) * hop + nfft / 2) / sr


def spectrogram_png(x, path, title="", fmax=16000, sr=SR, db_range=90, log_freq=False,
                    marks=None, nfft=None, width=14, height=None):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    x = np.asarray(x, dtype=np.float32)
    dur = len(x) / sr
    if nfft is None:
        nfft = 4096 if fmax <= 3000 else 2048
    S, f, t = stft_db(x, sr, nfft, nfft // 8 if dur < 4 else nfft // 4)
    top = S.max()
    height = height or 6
    fig, (a0, a1) = plt.subplots(2, 1, figsize=(width, height), sharex=True,
                                 gridspec_kw=dict(height_ratios=[1, 3.2]))
    m = mix.as_mono(x)
    # envelope (peak per pixel column) in dBFS
    cols = 1400
    hop = max(1, len(m) // cols)
    k = len(m) // hop
    env = np.abs(m[: k * hop]).reshape(k, hop).max(axis=1) if k else np.zeros(1)
    te = (np.arange(len(env)) + 0.5) * hop / sr
    a0.plot(te, 20 * np.log10(env + 1e-9), lw=0.6, color="k")
    a0.set_ylim(-80, 0)
    a0.set_ylabel("peak dBFS")
    a0.grid(alpha=0.3)
    lu = mix.lufs(x, sr) if len(x) > 0.4 * sr else float("nan")
    a0.set_title(f"{title}   dur {dur:.2f}s  peak {mix.amp2db(np.abs(x).max()):.1f} dBFS  {lu:.1f} LUFS", fontsize=9)
    a1.pcolormesh(t, f, S, vmin=top - db_range, vmax=top, shading="auto", cmap="magma")
    a1.set_ylim(20 if log_freq else 0, fmax)
    if log_freq:
        a1.set_yscale("log")
    a1.set_ylabel("Hz")
    a1.set_xlabel("s")
    if marks:
        for tm, lab in marks:
            a1.axvline(tm, color="c", lw=0.5, alpha=0.6)
            a1.text(tm, fmax * 0.97, lab, color="c", fontsize=7, rotation=90, va="top")
    fig.tight_layout()
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    fig.savefig(path, dpi=80)
    plt.close(fig)
    return path


def spectrum_png(x, path, title="", fmax=6000, sr=SR, t0=None, t1=None, marks_hz=None):
    """Long-term average spectrum (Welch) in dB, useful for timbre checks."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from scipy import signal

    m = mix.as_mono(x)
    if t0 is not None:
        m = m[int(t0 * sr): int(t1 * sr) if t1 else None]
    f, P = signal.welch(m, sr, nperseg=8192)
    P = 10 * np.log10(P + 1e-20)
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(f, P - P.max(), lw=0.8)
    ax.set_xlim(0, fmax)
    ax.set_ylim(-90, 3)
    ax.grid(alpha=0.3)
    ax.set_title(title, fontsize=9)
    ax.set_xlabel("Hz")
    ax.set_ylabel("dB rel. max")
    if marks_hz:
        for fr, lab in marks_hz:
            ax.axvline(fr, color="r", lw=0.5)
            ax.text(fr, -5, lab, fontsize=7, rotation=90, color="r")
    fig.tight_layout()
    fig.savefig(path, dpi=80)
    plt.close(fig)
    return path


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("wav")
    ap.add_argument("png", nargs="?")
    ap.add_argument("--fmax", type=float, default=16000)
    ap.add_argument("--log", action="store_true")
    a = ap.parse_args()
    x = mix.read_wav(a.wav)
    out = a.png or os.path.splitext(a.wav)[0] + ".png"
    spectrogram_png(x, out, os.path.basename(a.wav), a.fmax, log_freq=a.log)
    print(out)
