#!/bin/sh
# Lay down the print room's production register as the earlier shifts left it.
set -eu
"${PYTHON:-python3}" press.py pull ../register/members-evening.csv --batch members-evening --new-frame --by "events desk" --note "place cards for the members evening"
"${PYTHON:-python3}" press.py pull ../register/day-proofs.csv --batch installation --new-frame --by "day shift" --note "proof pull for the naming meeting; proofs binned afterwards"
