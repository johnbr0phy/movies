# BARNEY

A 3 minute 30 second animated short with no dialogue. A small boy carries a goldfish home through a world that will not stay the right way up. Written, designed, animated and scored by Claude from a one-paragraph prompt.

- **Watch:** `index.html` (GitHub Pages: https://johnbr0phy.github.io/movies/barney/), or `film/barney_1080p.mp4`, or the 4:5 cut at `film/barney_vertical_4x5.mp4`
- **Read:** [WRITEUP.md](WRITEUP.md), [docs/DECISIONS.md](docs/DECISIONS.md), [docs/STORY.md](docs/STORY.md), [docs/SHOTLIST.md](docs/SHOTLIST.md)
- **Sheets:** [sheets/](sheets/)

## Rebuild

- **Picture:** three.js in headless Chromium through SwiftShader. `npm install`, then `node render.js S01` renders one shot to `out/shots/S01.mp4`. `JOBS=3 ./render_all.sh` renders them all.
- **Sound:** `cd audio && python3 mixdown.py` writes `out/audio/soundtrack.wav`. It needs the CC0 Versilian Community Sample Library at the path set in `audio/sampler.py`.
- **Cut:** `python3 assemble.py` builds the 1080p, 720p and 4:5 files in `deliverables/`.
