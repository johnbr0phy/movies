"""Assemble BARNEY: concatenate shots, mux the soundtrack, two-pass encodes sized for GitHub (<100 MB) and chat (<30 MB),
and a 4:5 vertical cut (per-shot pan-and-scan; title and credits letterboxed so no line is cut).
python3 assemble.py [all|main|vertical]"""
import json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, 'out'); DEL = os.path.join(HERE, 'deliverables'); os.makedirs(DEL, exist_ok=True)
shots = json.load(open(os.path.join(HERE, 'src/shots.json')))
CROP = {s['id']: (.5, .5) for s in shots}
CROP.update({'S03': (.5, .5), 'S04': (.72, .78), 'S05': (.45, .45), 'S07': (.42, .5), 'S09': (.42, .32), 'S10': (.5, .45), 'S11': (.47, .47), 'S12': (.45, .45),
             'S13': (.3, .3), 'S16': (.5, .5), 'S17': (.4, .45), 'S19': (.52, .52), 'S21': (.35, .45), 'S23': (.5, .5), 'S25': (.55, .52)})
LETTERBOX = {'S02', 'S26'}
MODE = sys.argv[1] if len(sys.argv) > 1 else 'all'
audio = os.path.join(OUT, 'audio', 'soundtrack.wav'); lst = os.path.join(OUT, 'concat.txt')
def run(a): print(' '.join(a[:6]), '...'); subprocess.run(a, check=True)
def concat(paths, dst):
    with open(lst, 'w') as f:
        for p in paths: f.write(f"file '{p}'\n")
    run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy', dst])
def encode(src, dst, vbit, abit='192k', vf=None):
    base = ['ffmpeg', '-y', '-loglevel', 'error', '-i', src, '-i', audio, '-map', '0:v', '-map', '1:a'] + (['-vf', vf] if vf else []) + ['-c:v', 'libx264', '-preset', 'slow', '-tune', 'animation', '-b:v', vbit, '-pix_fmt', 'yuv420p', '-profile:v', 'high']
    plog = os.path.join(OUT, 'x264pass')
    run(base + ['-pass', '1', '-passlogfile', plog, '-an', '-f', 'mp4', os.devnull])
    run(base + ['-pass', '2', '-passlogfile', plog, '-c:a', 'aac', '-b:a', abit, '-ar', '48000', '-movflags', '+faststart', '-shortest', dst])
if MODE in ('all', 'main'):
    pic = os.path.join(OUT, 'picture.mp4'); concat([os.path.join(OUT, 'shots', s['id'] + '.mp4') for s in shots], pic)
    encode(pic, os.path.join(DEL, 'barney_1080p.mp4'), '3300k')
    encode(pic, os.path.join(DEL, 'barney_preview_720p.mp4'), '900k', '96k', 'scale=1280:720:flags=lanczos')
if MODE in ('all', 'vertical'):
    parts = []; os.makedirs(os.path.join(OUT, 'vert'), exist_ok=True)
    for s in shots:
        a, b = CROP[s['id']]; d = s['dur']; src = os.path.join(OUT, 'shots', s['id'] + '.mp4'); dst = os.path.join(OUT, 'vert', s['id'] + '.mp4')
        x = f"max(0,min(1920-864,({a}+({b}-{a})*t/{d})*1920-432))"
        vf = "scale=1080:608:flags=lanczos,pad=1080:1350:0:371:color=0xefe8dc" if s['id'] in LETTERBOX else f"crop=864:1080:x='{x}':y=0,scale=1080:1350:flags=lanczos"
        run(['ffmpeg', '-y', '-loglevel', 'error', '-i', src, '-vf', vf, '-c:v', 'libx264', '-preset', 'medium', '-crf', '14', '-pix_fmt', 'yuv420p', dst]); parts.append(dst)
    vpic = os.path.join(OUT, 'picture_vert.mp4'); concat(parts, vpic)
    encode(vpic, os.path.join(DEL, 'barney_vertical_4x5.mp4'), '2600k')
print('done')
