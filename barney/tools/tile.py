"""python3 tools/tile.py OUT.png img1 img2 ... [--cols 3] [--w 960]: tile probe frames into one review image."""
import sys
from PIL import Image
args = sys.argv[1:]; cols = 3; w = 960
if '--cols' in args: i = args.index('--cols'); cols = int(args[i + 1]); del args[i:i + 2]
if '--w' in args: i = args.index('--w'); w = int(args[i + 1]); del args[i:i + 2]
out, files = args[0], args[1:]
ims = [Image.open(f).convert('RGB') for f in files]; h = int(w * ims[0].height / ims[0].width)
rows = (len(ims) + cols - 1) // cols
o = Image.new('RGB', (w * min(cols, len(ims)), h * rows), 'white')
for k, im in enumerate(ims): o.paste(im.resize((w, h), Image.LANCZOS), ((k % cols) * w, (k // cols) * h))
o.save(out)
