#!/usr/bin/env bash

set -e

(cd rlmeta && ./make.py)

python rlmeta/rlmeta.py \
    --support \
    --compile qoi.rlmeta \
    --copy main.py \
    > qoi.py

echo "Compiled QOI"

echo "Decoding..."

time python qoi.py "$1"

eog "$1.png"
