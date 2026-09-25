#!/bin/bash
# JOBS=3 ./render_all.sh S01 S02 ...   (default: every shot in src/shots.json)
cd "$(dirname "$0")"; mkdir -p out/logs
IDS="$@"; [ -z "$IDS" ] && IDS=$(python3 -c "import json;print(' '.join(s['id'] for s in json.load(open('src/shots.json'))))")
echo $IDS | tr ' ' '\n' | xargs -P ${JOBS:-3} -I{} sh -c 'node render.js {} > out/logs/{}.log 2>&1 && echo "done {}" || echo "FAIL {}"'
