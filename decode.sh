#!/usr/bin/env bash

set -e

(cd rlmeta && ./make.py)

python rlmeta/rlmeta.py \
    --support \
    --compile qoi.rlmeta \
    --copy main.py \
    > qoi.py

python qoi.py "$1"
