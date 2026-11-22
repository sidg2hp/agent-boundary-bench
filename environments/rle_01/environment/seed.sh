#!/bin/sh
# Lay down the release desk's ledger: its receipt for the Loom journal as the desk reviewed it.
set -eu
"${PYTHON:-python3}" digest.py publish loom-1.4-preview --manifest ../desk/reviewed.toml
