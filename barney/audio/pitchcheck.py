import sys, glob, re, numpy as np, soundfile as sf
NAMES = {'C':0,'C#':1,'D':2,'D#':3,'E':4,'F':5,'F#':6,'G':7,'G#':8,'A':9,'A#':10,'B':11}
def hps_f0(x, fs):
    x = x[int(0.05*fs):int(0.05*fs)+int(0.5*fs)]; x = x * np.hanning(len(x))
    n = 1 << 18; X = np.abs(np.fft.rfft(x, n)); f = np.fft.rfftfreq(n, 1/fs)
    h = X.copy()
    for k in (2, 3, 4): h[:len(X)//k] *= X[::k][:len(X)//k]
    lo = np.searchsorted(f, 30); hi = np.searchsorted(f, 3000)
    return f[lo + np.argmax(h[lo:hi])]
for pat in sys.argv[1:]:
    for p in sorted(glob.glob(pat))[:6]:
        m = re.search(r'_([A-G]#?)(-?\d)_', p.split('/')[-1] + '_')
        if not m: continue
        midi = NAMES[m.group(1)] + 12 * (int(m.group(2)) + 1)
        x, fs = sf.read(p, always_2d=True); f0 = hps_f0(x.mean(1), fs)
        est = 69 + 12 * np.log2(f0 / 440)
        print(f"{p.split('/')[-1][:48]:48s} name {midi:3d}  est {est:6.2f}  diff {est-midi:+.2f}")
