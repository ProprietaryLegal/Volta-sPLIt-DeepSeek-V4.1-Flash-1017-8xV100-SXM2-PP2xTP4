#!/bin/bash
# act-check-v2.sh OFF_LABEL ON_LABEL [STATE]: H3 (harness1103, 11-03; advrev H3). Compares the activation counts that
# ab-arm-t1-v2.sh / ab-depth-arm-v2.sh wrote ("AB <label> ACT n=<count> pat=<sha8> ...") for an OFF and an ON arm.
# An activation grep proves a knob ran only if its count differs between OFF and ON (AR's "sum2 22" did not, M5).
# Prints "ACT <OFF> n=a <ON> n=b pat=<sha8> DISCRIMINATING|NOT-DISCRIMINATING|MISSING|PATTERN-DIFFERS".
# Exit 0 discriminating, 1 not, 2 missing or mismatched pattern.
S=${3:-${BENCH_DIR}/pp2-go.state}
get() { /usr/bin/grep -E " AB $1 ACT n=[0-9]+ pat=" "$S" | tail -n 1; }
a=$(get "$1"); b=$(get "$2")
na=$(echo "$a" | sed -n 's/.* ACT n=\([0-9]*\) pat=\([0-9a-f]*\).*/\1/p'); pa=$(echo "$a" | sed -n 's/.* pat=\([0-9a-f]*\).*/\1/p')
nb=$(echo "$b" | sed -n 's/.* ACT n=\([0-9]*\) pat=\([0-9a-f]*\).*/\1/p'); pb=$(echo "$b" | sed -n 's/.* pat=\([0-9a-f]*\).*/\1/p')
if [ -z "$na" ] || [ -z "$nb" ]; then echo "ACT $1 n=${na:-?} $2 n=${nb:-?} MISSING"; exit 2; fi
if [ "$pa" != "$pb" ]; then echo "ACT $1 pat=$pa $2 pat=$pb PATTERN-DIFFERS"; exit 2; fi
if [ "$na" != "$nb" ]; then echo "ACT $1 n=$na $2 n=$nb pat=$pa DISCRIMINATING"; exit 0; fi
echo "ACT $1 n=$na $2 n=$nb pat=$pa NOT-DISCRIMINATING"; exit 1
