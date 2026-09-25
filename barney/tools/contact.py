"""python3 tools/contact.py S01 S02 ... -> out/review/SXX.png (4 frames per shot)"""
import json, os, subprocess, sys
from PIL import Image
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = {s['id']: s for s in json.load(open(os.path.join(HERE, 'src/shots.json')))}
os.makedirs(os.path.join(HERE, 'out/review'), exist_ok=True)
for sid in sys.argv[1:]:
    d = S[sid]['dur']; ims = []
    for k, f in enumerate((0.08, 0.36, 0.64, 0.94)):
        p = f'/tmp/_c_{sid}_{k}.png'
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(d * f), '-i', os.path.join(HERE, 'out/shots', sid + '.mp4'), '-frames:v', '1', '-vf', 'scale=960:540', p], check=True); ims.append(Image.open(p))
    o = Image.new('RGB', (1920, 1080))
    for k, im in enumerate(ims): o.paste(im, ((k % 2) * 960, (k // 2) * 540))
    o.save(os.path.join(HERE, 'out/review', sid + '.png'))
