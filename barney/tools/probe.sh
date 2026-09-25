#!/bin/bash
# tools/probe.sh S01 0.5,2,4 [cols] -> renders probe frames and tiles them to the scratchpad
ID=$1; T=$2; C=${3:-3}; cd /home/user/barney
rm -f out/probe/$ID/*.png
timeout 600 node render.js $ID --only $T 2>&1 | grep -v "0/" | tail -5
python3 tools/tile.py /tmp/claude-0/-home-user-bicycle/1d2d2dd5-d9cf-51ca-81f8-e69f2f437e17/scratchpad/probe_$ID.png out/probe/$ID/*.png --cols $C
