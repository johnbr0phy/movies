"""score.py: the music for BARNEY, timed to picture.

Tempo: quarter = 120, so an eighth is 0.25 s. The meter is 7/8 (2+2+3), a bar of 1.75 s. Barney walks at two steps a
second, so his feet and the bar only meet every two bars: the music limps and he doesn't.

The motif M is five notes in E Dorian: E5 G5 F#5 B4 E5. When the world turns over we hear it upside down (I, a melodic
inversion around E5: E5 C#5 D5 A5 E5); when he walks down stairs to go up, backwards (R); at the turn, both (RI). It is
heard whole, right way up and upside down together as a mirror canon, only once: when the goldfish goes home.
"""
import json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import sampler, mix  # noqa: E402

SR = 48000
SHOTS = json.load(open(os.path.join(HERE, '..', 'src', 'shots.json')))
START = {}; _t = 0.0
for s in SHOTS: START[s['id']] = _t; _t += s['dur']
TOTAL = _t
def T(sid, t=0.0): return START[sid] + t
E8 = 0.25
N = {'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3, 'E': 4, 'F': 5, 'F#': 6, 'Gb': 6, 'G': 7, 'G#': 8, 'Ab': 8, 'A': 9, 'A#': 10, 'Bb': 10, 'B': 11}
def m(name):
    p = name[:-1] if name[-1].isdigit() else name; o = int(name[len(p):]); return N[p] + 12 * (o + 1)

M = ['E5', 'G5', 'F#5', 'B4', 'E5']
I = ['E5', 'C#5', 'D5', 'A5', 'E5']
R = M[::-1]; RI = I[::-1]
RHY = [1, 1, 2, 1, 2]   # in eighths: short short long short long (7 eighths = one bar)

def phrase(ev, t0, notes, inst, vel=0.6, rhy=RHY, e8=E8, legato=1.0, pan=0.0, gain_db=0.0, octave=0):
    t = t0
    for n, r in zip(notes, rhy):
        ev.append(dict(t=t, inst=inst, note=m(n) + 12 * octave, vel=vel, dur=r * e8 * legato, pan=pan, gain_db=gain_db)); t += r * e8
    return t

# chords for the ostinato: (root, third, fifth, colour)
CH = {'Em': ('E', 'G', 'B', 'E'), 'C': ('C', 'E', 'G', 'B'), 'A': ('A', 'C#', 'E', 'A'), 'Bs': ('B', 'E', 'F#', 'B'), 'D': ('D', 'F#', 'A', 'D')}
LOOP = ['Em', 'Em', 'C', 'C', 'A', 'A', 'Bs', 'Bs']
def ostinato(ev, t0, t1, inst='harpsichord', vel=0.45, bass=True, bass_inst='marimba', loop=LOOP, gain_db=0.0, bass_gain=0.0, pan=-0.15):
    """harpsichord 7/8 figure: r3 5 r4 5 | 3 5 r4, grouped 2+2+3; marimba root on 1 and on the 3-group"""
    b = 0; t = t0
    while t < t1 - 0.01:
        r, th, f, c = CH[loop[b % len(loop)]]
        fig = [f'{r}3', f'{f}3', f'{r}4', f'{f}3', f'{th}4', f'{f}3', f'{c}4']
        for i, n in enumerate(fig):
            tt = t + i * E8
            if tt >= t1: break
            acc = 1.0 if i in (0, 2, 4) else 0.8
            ev.append(dict(t=tt, inst=inst, note=m(n), vel=vel * acc, dur=0.3, pan=pan, gain_db=gain_db))
        if bass:
            ev.append(dict(t=t, inst=bass_inst, note=m(f'{r}2'), vel=0.55, dur=0.6, pan=0.1, gain_db=bass_gain))
            if t + 4 * E8 < t1: ev.append(dict(t=t + 4 * E8, inst=bass_inst, note=m(f'{r}2') + 7, vel=0.42, dur=0.5, pan=0.1, gain_db=bass_gain))
        t += 7 * E8; b += 1

# ------------------------------------------------------------------ synth voices
def ondes(notes, sr=SR, vib=5.6, vib_c=18, glide=0.07, bright=0.25, palme=0.35):
    """An ondes Martenot: a sine with a ribbon glide between notes, vibrato, a little harmonic edge, and the
    'palme' diffuser (a bank of sympathetic metal strings) for the shimmer. notes: [(t, dur, midi, vel)] relative."""
    if not notes: return np.zeros((1, 2), np.float32)
    end = max(t + d for t, d, _, _ in notes) + 1.2; n = int(end * sr); tt = np.arange(n) / sr
    f = np.zeros(n); a = np.zeros(n)
    for i, (t, d, mid, v) in enumerate(notes):
        s, e = int(t * sr), int((t + d) * sr)
        f[s:] = 440.0 * 2 ** ((mid - 69) / 12)
        att = int(0.06 * sr); rel = int(0.35 * sr)
        env = np.ones(e - s); env[:att] = np.linspace(0, 1, min(att, len(env))) ** 1.5 if att <= len(env) else env[:att]
        a[s:e] = np.maximum(a[s:e], v * env)
        if e < n: r = min(rel, n - e); a[e:e + r] = np.maximum(a[e:e + r], v * np.linspace(1, 0, r) ** 2)
    # glide: smooth the pitch track (a one-pole in log domain)
    lf = np.log(np.maximum(f, 1)); k = np.exp(-1 / (glide * sr)); out = np.empty_like(lf); acc = lf[0]
    for i in range(n): acc = k * acc + (1 - k) * lf[i]; out[i] = acc
    vibr = 1 + (2 ** (vib_c / 1200) - 1) * np.sin(2 * np.pi * vib * tt) * np.clip(tt * 2, 0, 1)
    ph = 2 * np.pi * np.cumsum(np.exp(out) * vibr) / sr
    y = np.sin(ph) + bright * 0.35 * np.sin(2 * ph) + bright * 0.18 * np.sin(3 * ph)
    y = y * a
    # palme: comb resonators tuned to the E Dorian scale, decaying
    pal = np.zeros_like(y)
    for semi in (0, 3, 7, 12, 14, 19, 24):
        fr = 329.63 * 2 ** (semi / 12); D = int(sr / fr); g = 0.985
        buf = np.zeros(n)
        for i in range(D, n): buf[i] = y[i] * 0.02 + g * buf[i - D]
        pal += buf
    y = y + palme * pal / 7
    st = np.stack([y, np.roll(y, 23)], 1).astype(np.float32)
    return st * 0.35

def shepard_step(k, dur=0.48, up=True, sr=SR, base=110.0):
    """one step of a Shepard scale: 8 octave-spaced partials with a bell-shaped weight in log-frequency"""
    n = int(dur * sr); tt = np.arange(n) / sr; y = np.zeros(n)
    pc = (k % 12) / 12.0
    for o in range(8):
        f = base * 2 ** (o + pc - 2); lf = np.log2(f / 440.0)
        w = np.exp(-0.5 * (lf / 1.3) ** 2)
        y += w * np.sin(2 * np.pi * f * tt)
    env = np.minimum(1, tt / 0.01) * np.exp(-tt * 3.2)
    return (y * env * 0.12).astype(np.float32)

def glide_tone(f0, f1, dur, sr=SR, vib=0.0):
    n = int(dur * sr); tt = np.arange(n) / sr; f = f0 * (f1 / f0) ** (tt / dur)
    y = np.sin(2 * np.pi * np.cumsum(f) / sr) + 0.2 * np.sin(4 * np.pi * np.cumsum(f) / sr)
    env = np.minimum(1, tt / 0.3) * np.minimum(1, (dur - tt) / 0.8)
    return (y * env * 0.25).astype(np.float32)

# ------------------------------------------------------------------ the cue sheet
def build():
    ev = []          # sampled instruments (dry; reverb added per bus)
    synth = []       # (t, stereo buffer, gain_db, pan)

    # S01 the hook: one harpsichord note, then a glass tone swells under the roll
    ev.append(dict(t=T('S01', 0.25), inst='harpsichord', note=m('E4'), vel=0.55, dur=1.5))
    ev.append(dict(t=T('S01', 2.4), inst='glass', note=m('B4'), vel=0.5, dur=3.2, gain_db=-4))
    ev.append(dict(t=T('S01', 3.3), inst='glass', note=m('E5'), vel=0.45, dur=2.4, gain_db=-5))
    # S02 title: the first three notes of M on the ondes; a marimba plink as each letter lifts
    synth.append((T('S02', 0.5), ondes([(0, 0.45, m('E5'), 0.8), (0.5, 0.25, m('G5'), 0.8), (0.75, 1.1, m('F#5'), 0.8)]), -3, 0.0))
    for i, n in enumerate(['E6', 'G6', 'A6', 'B6', 'D7', 'E7']):
        ev.append(dict(t=T('S02', 2.3 + i * 0.24), inst='marimba', note=m(n) - 12, vel=0.5, dur=0.5, pan=-0.5 + i * 0.2))
    # S03-S05: the 7/8 ostinato arrives with the gallery
    ostinato(ev, T('S03', 0.5), T('S05', 6.8))
    # S04 marimba answers with M
    phrase(ev, T('S04', 0.6), M, 'marimba', vel=0.55, octave=-1, pan=0.3)
    # S05 the door: M upside down on the ondes, as the sideways plaza appears
    synth.append((T('S05', 3.4), ondes([(0.25 * sum(RHY[:k]), 0.25 * RHY[k] * 1.05, m(n), 0.85) for k, n in enumerate(I)]), -2, 0.1))
    # S06: the ostinato stops; an organ pedal swells under the roll; the ostinato returns in the plaza
    ev.append(dict(t=T('S06', 2.4), inst='organ', note=m('E2'), vel=0.55, dur=4.2))
    ev.append(dict(t=T('S06', 2.8), inst='organ', note=m('B2'), vel=0.45, dur=3.8))
    ev.append(dict(t=T('S06', 3.4), inst='organ', note=m('E3'), vel=0.4, dur=3.0))
    ostinato(ev, T('S06', 5.0), T('S08', 7.0))
    # S07/S08 plaza: M on the harpsichord an octave up as he walks up the wall; glass for the grin
    phrase(ev, T('S07', 5.6), M, 'harpsichord', vel=0.5, pan=0.25)
    ev.append(dict(t=T('S08', 2.5), inst='glass', note=m('E5'), vel=0.6, dur=0.9, gain_db=-1))
    ev.append(dict(t=T('S08', 3.25), inst='glass', note=m('G5'), vel=0.6, dur=1.6, gain_db=-1))
    # S09 the runway groove: ostinato with a stronger bass (claps and paper swishes are in the SFX)
    ostinato(ev, T('S09', 0.0), T('S10', 1.0), bass_gain=3)
    ev.append(dict(t=T('S09', 4.2), inst='vibes', note=m('B4'), vel=0.5, dur=1.0))
    phrase(ev, T('S09', 4.5), M, 'vibes', vel=0.55, pan=0.2)
    # S10: the music drops out as the Pleats vanish edge-on, and returns with the crane
    for i, n in enumerate(['E5', 'B5', 'E6']): ev.append(dict(t=T('S10', 5.4 + i * 0.5), inst='glass', note=m(n), vel=0.5, dur=1.4, gain_db=-4))
    ostinato(ev, T('S10', 5.8), T('S10', 8.0), vel=0.35, bass=False)
    # S11 Penrose stairs: a Shepard scale that climbs a semitone with every step he takes, forever
    for k in range(20):
        t = T('S11', 0.25 + k * 0.5)
        synth.append((t, shepard_step(k), -2, 0.0))
        ev.append(dict(t=t, inst='harpsichord', note=m('E4') + (k % 12), vel=0.35, dur=0.3, pan=-0.2))
    # he looks at us (silence), then walks down: M backwards on the ondes, the Shepard falls
    synth.append((T('S11', 11.0), ondes([(0.25 * sum(RHY[:k]), 0.25 * RHY[k], m(n) - 12, 0.85) for k, n in enumerate(R)]), -2, 0.0))
    for k in range(2): synth.append((T('S11', 11.25 + k * 0.5), shepard_step(19 - k), -4, 0.0))
    # S12: a long held note while the trick is revealed, then nothing until he jumps
    ev.append(dict(t=T('S12', 0.3), inst='psaltery', note=m('B4'), vel=0.45, dur=3.8, gain_db=-4))
    # S13/S14 playground: music-box M on the glock; then the slide: an accelerating run up the marimba, the ondes launch
    phrase(ev, T('S13', 2.8), M, 'glock', vel=0.4, octave=1, gain_db=-6)
    run = []; tt = 0.0; k = 0
    while tt < 4.6: run.append(tt); tt += max(0.06, 0.32 * (1 - tt / 5.2)); k += 1
    scale = [0, 2, 3, 5, 7, 9, 10]
    for i, t in enumerate(run):
        deg = scale[i % 7] + 12 * (i // 7)
        ev.append(dict(t=T('S14', 0.5 + t), inst='marimba', note=m('E3') + deg, vel=0.45 + 0.3 * i / len(run), dur=0.3, pan=-0.4 + 0.8 * i / len(run)))
    synth.append((T('S14', 5.0), ondes([(0, 0.2, m('E5'), 0.9), (0.2, 1.6, m('E6'), 0.9)], glide=0.25), -1, 0.0))
    # S15-S16 the city: the ostinato with organ bass underneath; the billboard sings M on the glock
    ostinato(ev, T('S15', 3.4), T('S17', 1.9), bass_inst='organ', bass_gain=-2)
    phrase(ev, T('S16', 3.2), M, 'glock', vel=0.45, octave=1, pan=0.4, gain_db=-4)
    # S17 the puncture: the music cuts to one sustained ondes note
    synth.append((T('S17', 1.95), ondes([(0, 4.0, m('B4'), 0.6)], vib_c=10), -6, 0.0))
    # S18 silence. S19: one glass note that rises in pitch with the drop
    synth.append((T('S19', 4.6), glide_tone(659.3, 1318.5, 4.4), -9, 0.0))
    # S20 the turn: organ and glass swell; RI (backwards and upside down) on the glass; the ondes enters
    for n, t0, d in [('E3', 1.5, 6.5), ('B3', 2.0, 6.0), ('E4', 2.6, 5.4), ('G4', 3.4, 4.6)]:
        ev.append(dict(t=T('S20', t0), inst='organ', note=m(n), vel=0.4, dur=d, gain_db=-3))
    phrase(ev, T('S20', 3.5), RI, 'glass', vel=0.6, e8=0.5, legato=1.1, gain_db=-1)
    synth.append((T('S20', 6.2), ondes([(0, 1.8, m('B4'), 0.7)]), -5, 0.0))
    # S21: glass harmonica pad; bowed psaltery shimmer
    for n, t0, d in [('E5', 0.0, 8.0), ('B5', 1.0, 7.0)]: ev.append(dict(t=T('S21', t0), inst='glass', note=m(n), vel=0.45, dur=d, gain_db=-6))
    ev.append(dict(t=T('S21', 4.4), inst='psaltery', note=m('E5'), vel=0.45, dur=3.0, gain_db=-5))
    # S22 release: the mirror canon, M on the ondes and I on the glass together, twice, over the ostinato and strings
    ostinato(ev, T('S22', 0.0), T('S23', 1.75), vel=0.4, loop=['Em', 'C', 'A', 'Bs'])
    for rep in range(2):
        t0 = T('S22', 1.75 + rep * 3.5)
        synth.append((t0, ondes([(0.5 * sum(RHY[:k]), 0.5 * RHY[k] * 1.02, m(n), 0.95) for k, n in enumerate(M)]), -1, -0.15))
        phrase(ev, t0, I, 'glass', vel=0.75, e8=0.5, legato=1.05, pan=0.2)
    for n in ['E3', 'B3', 'G4', 'D5']: ev.append(dict(t=T('S22', 1.5), inst='strings', note=m(n), vel=0.5, dur=10.0, gain_db=-6))
    # S23: the canon resolves to E major (the only major chord in the film) as the fish touches his hand
    for n in ['E3', 'B3', 'G#4', 'E5']: ev.append(dict(t=T('S23', 2.9), inst='strings', note=m(n), vel=0.5, dur=5.0, gain_db=-5))
    ev.append(dict(t=T('S23', 3.0), inst='glock', note=m('E7'), vel=0.5, dur=1.0, gain_db=-4))
    ev.append(dict(t=T('S23', 3.05), inst='glass', note=m('G#5'), vel=0.55, dur=3.5, gain_db=-4))
    # S24: the music thins to glass
    ev.append(dict(t=T('S24', 0.0), inst='glass', note=m('E5'), vel=0.4, dur=9.0, gain_db=-8))
    ev.append(dict(t=T('S24', 2.0), inst='glass', note=m('B4'), vel=0.35, dur=8.0, gain_db=-9))
    # S26 credits: M on solo harpsichord, twice, slowly
    phrase(ev, T('S26', 1.0), M, 'harpsichord', vel=0.5, e8=0.4)
    phrase(ev, T('S26', 4.6), I, 'harpsichord', vel=0.45, e8=0.4)
    phrase(ev, T('S26', 8.2), M, 'harpsichord', vel=0.4, e8=0.5)
    return ev, synth

def render(out_path=None):
    ev, synth = build()
    n = int((TOTAL + 2) * SR)
    y = sampler.render(ev, duration=TOTAL + 2)
    y = sampler.hall(y, wet=0.28)
    sy = np.zeros((n, 2), np.float32)
    for t, buf, g, pan in synth: mix.place(sy, buf, t, gain_db=g, pan=pan)
    sy = sampler.hall(sy, wet=0.35)
    music = y[:n] + sy[:n]
    if out_path: mix.write_wav(out_path, music, check_peak=False)
    return music

if __name__ == '__main__':
    os.makedirs(os.path.join(HERE, '..', 'out', 'audio'), exist_ok=True)
    render(os.path.join(HERE, '..', 'out', 'audio', 'music.wav'))
    print('music done', TOTAL)
