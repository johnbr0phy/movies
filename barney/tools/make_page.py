"""Build the Barney web page (for GitHub Pages) into SITE/barney/: player, stills, the prompt, sheets, credits."""
import html, json, os, shutil, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
SITE = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'site')
D = os.path.join(SITE, 'barney'); os.makedirs(os.path.join(D, 'assets', 'stills'), exist_ok=True); os.makedirs(os.path.join(D, 'assets', 'sheets'), exist_ok=True); os.makedirs(os.path.join(D, 'film'), exist_ok=True)
FILM = os.path.join(ROOT, 'deliverables', 'barney_1080p.mp4'); VERT = os.path.join(ROOT, 'deliverables', 'barney_vertical_4x5.mp4')
REPO = 'https://github.com/johnbr0phy/movies/tree/main/barney'
PROMPT = ("This movie was great and I want to create something new.\n\n"
          "I want the movie to be kinda mind bending - it should confuse the watcher with stranger perspectives and illusions, it should feel incredibly styalized and artistic. "
          "Think Jean pa gautier, issey miake and the fifth element. It should be about a little boy called Barney. Walking through a world that deforms and confuses us. "
          "Every step we think we know what’s coming but it never ends up the way we should it would. Doors open to a flat plan on a different horizontal angle. "
          "He walks up a wall and slides up a slide. It should be an interesting watch. Something that would win an award at Cannes.")
STILLS = [(3.5, 'A goldfish in a bag, and the water pooled at the top.'), (18.8, 'The gallery: he grows as he walks away.'), (48.4, 'He walks up the wall. The fountain falls sideways.'),
          (61.0, 'The Pleats walk the runway in lockstep.'), (80.0, 'The stairs that climb forever.'), (101.0, 'Sliding up the slide.'),
          (107.5, 'The vertical city.'), (131.0, 'The grey plain. Only the fish is orange.'), (151.5, 'The sky was the sea.'),
          (166.0, 'Home.'), (188.5, 'The bowl on the floor of the sea.'), (195.6, 'Who was carrying whom.')]
def ff(*a): subprocess.run(['ffmpeg', '-v', 'error', '-y', *a], check=True)
if os.path.exists(FILM):
    ff('-ss', '8.0', '-i', FILM, '-frames:v', '1', '-q:v', '3', os.path.join(D, 'assets', 'poster.jpg'))
    for i, (t, _) in enumerate(STILLS): ff('-ss', str(t), '-i', FILM, '-frames:v', '1', '-vf', 'scale=960:-1', '-q:v', '4', os.path.join(D, 'assets', 'stills', f'still_{i + 1:02d}.jpg'))
    shutil.copy(FILM, os.path.join(D, 'film', 'barney_1080p.mp4'))
    if os.path.exists(VERT): shutil.copy(VERT, os.path.join(D, 'film', 'barney_vertical_4x5.mp4'))
from PIL import Image
SHEETS = [('style_sheet', 'Style sheet', 'palettes by act, surfaces, line, the two gravities, and what not to do'), ('char_barney', 'Barney', 'turnaround and poses'),
          ('char_barney_expressions', 'Expressions', 'smile, grin, o, flat, sad, blink'), ('char_fish_bag_pleats', 'The goldfish, the bag, the Pleats', 'and the rule of the bag')]
for f, _, _ in SHEETS:
    im = Image.open(os.path.join(ROOT, 'sheets', f + '.png')).convert('RGB'); im = im.resize((1600, int(im.height * 1600 / im.width)), Image.LANCZOS); im.save(os.path.join(D, 'assets', 'sheets', f + '.jpg'), quality=85)
still_html = '\n'.join(f'<figure><img src="assets/stills/still_{i + 1:02d}.jpg" alt="{html.escape(c)}" loading="lazy" width="960" height="540"><figcaption>{html.escape(c)}</figcaption></figure>' for i, (_, c) in enumerate(STILLS))
sheet_html = '\n'.join(f'<a class="sheet" href="{REPO}/sheets/{f}.png"><img src="assets/sheets/{f}.jpg" alt="{t}" loading="lazy"><span><b>{t}</b>{html.escape(d)}</span></a>' for f, t, d in SHEETS)
prompt_html = '\n'.join(f'<p>{html.escape(p)}</p>' for p in PROMPT.split('\n\n'))
page = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Barney</title>
<meta name="description" content="A 3 minute 30 second animated short with no dialogue. A small boy carries a goldfish through a world that will not stay the right way up. Written, designed, animated and scored by Claude.">
<meta property="og:title" content="BARNEY"><meta property="og:description" content="A boy, a goldfish, and which way is down. A short film made end to end by Claude.">
<meta property="og:image" content="https://johnbr0phy.github.io/movies/barney/assets/poster.jpg"><meta property="og:type" content="video.other"><meta name="twitter:card" content="summary_large_image">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Bodoni+Moda:ital,opsz,wght@0,6..96,400..900;1,6..96,400..700&family=Jost:wght@300..600&display=swap" rel="stylesheet">
<style>
:root {{ --paper:#efe8dc; --ink:#16141b; --soft:#57525e; --rule:#cdbfa8; --navy:#1c2b52; --red:#d42a2f; --card:#f6f1e7; --shadow:rgba(40,30,20,.12); }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ --paper:#12152a; --ink:#efe8dc; --soft:#b3aca2; --rule:#2d3354; --navy:#9fb4ff; --red:#ff6a5c; --card:#1a1e38; --shadow:rgba(0,0,0,.4); }} }}
:root[data-theme="dark"] {{ --paper:#12152a; --ink:#efe8dc; --soft:#b3aca2; --rule:#2d3354; --navy:#9fb4ff; --red:#ff6a5c; --card:#1a1e38; --shadow:rgba(0,0,0,.4); }}
* {{ box-sizing:border-box; }} html {{ -webkit-text-size-adjust:100%; }}
body {{ margin:0; background:var(--paper); color:var(--ink); font-family:"Jost",system-ui,sans-serif; font-weight:400; line-height:1.65; font-size:17px; }}
a {{ color:var(--navy); text-underline-offset:3px; }}
.wrap {{ max-width:1120px; margin:0 auto; padding:0 16px; }}
.stripes {{ height:14px; background:repeating-linear-gradient(180deg, var(--navy) 0 3px, transparent 3px 7px); opacity:.9; }}
header {{ text-align:center; padding:48px 0 22px; }}
h1 {{ font-family:"Bodoni Moda",serif; font-weight:800; font-size:clamp(64px,13vw,150px); letter-spacing:.08em; margin:0; line-height:1; color:var(--ink);
  background:repeating-linear-gradient(180deg, var(--ink) 0 .06em, transparent .06em .1em); -webkit-background-clip:text; background-clip:text; -webkit-text-fill-color:transparent; }}
.sub {{ font-family:"Bodoni Moda",serif; font-style:italic; font-size:clamp(18px,2.6vw,24px); color:var(--navy); margin:12px 0 0; }}
.log {{ max-width:640px; margin:18px auto 0; color:var(--soft); }}
.player {{ border-radius:4px; overflow:hidden; box-shadow:0 18px 50px var(--shadow), 0 0 0 1px var(--rule); background:#000; aspect-ratio:16/9; }}
.player video {{ width:100%; height:100%; display:block; }}
.meta {{ display:flex; flex-wrap:wrap; justify-content:space-between; gap:8px 20px; margin:12px 2px 0; color:var(--soft); font-size:15px; }}
.meta a {{ margin-left:14px; white-space:nowrap; }} .meta a:first-child {{ margin-left:0; }}
section {{ padding:56px 0 6px; }}
h2 {{ font-family:"Bodoni Moda",serif; font-weight:700; font-size:30px; margin:0 0 6px; }}
.lede {{ color:var(--soft); margin:0 0 22px; max-width:720px; }}
.stills {{ display:grid; grid-template-columns:repeat(3,1fr); gap:14px; }}
figure {{ margin:0; }} figure img {{ width:100%; height:auto; display:block; border-radius:3px; box-shadow:0 0 0 1px var(--rule); }}
figcaption {{ font-size:14px; color:var(--soft); margin-top:6px; }}
.seed {{ margin:0; padding:22px 26px; border-left:4px solid var(--red); background:var(--card); border-radius:0 4px 4px 0; box-shadow:0 0 0 1px var(--rule); font-size:19px; line-height:1.75; max-width:860px; }}
.seed p {{ margin:0 0 12px; }} .seed p:last-child {{ margin:0; }}
.rules {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(250px,1fr)); gap:14px 28px; }}
.rules div {{ border-top:1px solid var(--rule); padding-top:10px; }} .rules b {{ display:block; font-family:"Bodoni Moda",serif; font-size:18px; }} .rules span {{ color:var(--soft); font-size:15px; }}
.sheets {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(320px,1fr)); gap:16px; }}
.sheet {{ display:block; text-decoration:none; color:inherit; background:var(--card); border-radius:4px; overflow:hidden; box-shadow:0 0 0 1px var(--rule); transition:transform .2s; }}
.sheet:hover {{ transform:translateY(-2px); }} .sheet img {{ width:100%; aspect-ratio:16/9; object-fit:cover; display:block; }}
.sheet span {{ display:block; padding:10px 14px 12px; font-size:14px; color:var(--soft); }} .sheet b {{ display:block; color:var(--ink); font-size:16px; }}
.docs {{ display:flex; flex-wrap:wrap; gap:10px; margin-top:22px; }} .docs a {{ border:1px solid var(--rule); border-radius:999px; padding:6px 16px; text-decoration:none; color:var(--ink); font-size:15px; }}
footer {{ text-align:center; padding:64px 0 44px; color:var(--soft); font-size:15px; }} footer .ded {{ font-family:"Bodoni Moda",serif; font-style:italic; font-size:19px; color:var(--ink); }}
.theme {{ position:absolute; top:24px; right:16px; background:none; border:1px solid var(--rule); color:var(--soft); border-radius:999px; padding:4px 12px; font:inherit; font-size:13px; cursor:pointer; }}
@media (max-width:720px) {{ header {{ padding-top:64px; }} body {{ font-size:16px; }} .stills {{ grid-template-columns:1fr 1fr; gap:10px; }} .meta {{ flex-direction:column; }} .meta a {{ margin:0 14px 0 0; }} .seed {{ padding:16px 18px; font-size:17px; }} }}
@media (max-width:420px) {{ .stills {{ grid-template-columns:1fr; }} }}
</style></head>
<body>
<div class="stripes"></div>
<button class="theme" id="theme" type="button" aria-label="Toggle colour theme">day / night</button>
<header class="wrap"><h1>BARNEY</h1><p class="sub">a boy, a goldfish, and which way is down</p>
<p class="log">A small boy in a Breton top carries a goldfish home through a world that will not stay the right way up. By the end we find out who was carrying whom.</p></header>
<main class="wrap">
<div class="player"><video controls playsinline preload="metadata" poster="assets/poster.jpg"><source src="film/barney_1080p.mp4" type="video/mp4">Your browser can't play this video. <a href="film/barney_1080p.mp4">Download it.</a></video></div>
<div class="meta"><span>3 min 30 s · no dialogue · sound on</span><span><a href="film/barney_1080p.mp4" download>1080p MP4</a><a href="film/barney_vertical_4x5.mp4" download>4:5 vertical</a></span></div>
<section><h2>Frames</h2><p class="lede">Gaultier's stripes and cones, Miyake's pleats, the vertical city of The Fifth Element, drawn ligne claire: flat colour, one shadow, one even line.</p>
<div class="stills">
{still_html}
</div></section>
<section><h2>The prompt</h2><p class="lede">This is the whole brief, word for word. Everything else here (story, design, animation, score) was Claude's.</p>
<div class="seed">{prompt_html}</div></section>
<section><h2>The rules of the confusion</h2><p class="lede">Random surrealism wears an audience out in a minute. So the illusions have rules you can learn, and then the film overturns them.</p>
<div class="rules">
<div><b>Barney's down</b><span>is whatever he's standing on: a wall, a ceiling, the face of a tower. He never notices.</span></div>
<div><b>The water knows</b><span>the true down. It's your compass: when the water line is sideways in frame, the picture is lying.</span></div>
<div><b>The camera</b><span>takes his side late, rolling to agree with him a beat after he has changed his mind about gravity.</span></div>
<div><b>The music limps</b><span>in 7/8 against his steady two steps a second. The five-note motif turns upside down whenever the world does.</span></div>
</div>
<div class="docs"><a href="{REPO}/WRITEUP.md">Writeup</a><a href="{REPO}/docs/DECISIONS.md">Decisions</a><a href="{REPO}/docs/STORY.md">Beat sheet</a><a href="{REPO}/docs/SHOTLIST.md">Shot list</a><a href="{REPO}">Source</a></div></section>
<section><h2>Sheets</h2><p class="lede">The style sheet and the character sheets. Click a sheet to open the full-resolution PNG.</p><div class="sheets">
{sheet_html}
</div></section>
</main>
<footer class="wrap"><p class="ded">for anyone who ever carried something small and alive a long way, carefully</p>
<p>Written, designed, animated and scored by Claude. Instrument samples: Versilian Community Sample Library (CC0). All other sound synthesised. Type: Bodoni Moda, Jost (SIL OFL). Drawn with three.js.</p></footer>
<div class="stripes"></div>
<script>(function(){{var r=document.documentElement,k='barney-theme';try{{var s=localStorage.getItem(k);if(s)r.setAttribute('data-theme',s);}}catch(e){{}}
document.getElementById('theme').addEventListener('click',function(){{var d=r.getAttribute('data-theme')?r.getAttribute('data-theme')==='dark':matchMedia('(prefers-color-scheme: dark)').matches;var n=d?'light':'dark';r.setAttribute('data-theme',n);try{{localStorage.setItem(k,n);}}catch(e){{}}}});}})();</script>
</body></html>'''
open(os.path.join(D, 'index.html'), 'w').write(page)
print('page written', D)
