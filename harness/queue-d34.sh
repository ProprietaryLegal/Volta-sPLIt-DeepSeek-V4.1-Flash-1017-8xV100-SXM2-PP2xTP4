#!/bin/bash
# queue-d34.sh (the owner session, 11-03): chained after QUEUE-D33 done. expdiet1103 (v41pkg/expdiet1103
# f5bb57ebb on 8a08e60a5): VLLM_V41_EXPERT_DIET (read once by v41k.so; bit 1 gate_up_diet, bit 2 down_rows_diet, bit 4
# smem activations; acts only with EXPERT_FAST=1). v41k.cu base = 84fd6fa = the source of prod v41k.so aad82b0f
# (v41k-gu1103 build); lane: all 194 old kernels byte-identical SASS, so knob off = prod. .so only (envs.py entry not
# needed: the .so reads the env itself). Steps, server down: build v41k-diet1103 (nice, MAX_JOBS=4), expert_diet_check
# (bitwise + timing) and compute-sanitizer memcheck/racecheck/synccheck on GPU 0 (Board B). Only if all pass: swap
# prod v41k.so atomically (backup v41k.so.pre-diet1103), ABBA DT-OFF / DT-ON (DIET=3) / DT-ON2 / DT-OFF2 on the
# recommended stack (+ MIX_STREAM if D33 left it on). Final boot keeps DIET=3 only on WIN (own kernel, not upstream).
B=${ENGINE_HOME}; O=$B/bench5; D=$B/src-pp2/benchmarks/deepseek_v41; cd $B
st() { echo "$(date -u +%FT%TZ) QUEUE-D34 $*" >> $O/pp2-go.state; }
FULL="VLLM_V41_INDEX_REDUCE=1 VLLM_V41_DMV_X=1 VLLM_V41_COUPLED_DRAFTS=1 VLLM_V41_COUPLED_DRAFT_TEMP=1.0 VLLM_V41_MARKOV_SHARD=1 VLLM_V41_COUPLED_SHARD=1 VLLM_V41_COUPLED_LOCAL=1 VLLM_V41_PLAN_FUSE=1 VLLM_V41_PP_KEEP_BATCH=1 VLLM_V41_EXPERT_FAST=1 VLLM_V41_FUSE_ATTN_PREP=1 VLLM_V41_FUSE_ATTN_POST=1"
DT="VLLM_V41_EXPERT_DIET=3"
NEWLIB=$D/v41k-diet1103/build/v41k.so; LIB=$D/v41k/build/v41k.so; PY=$B/.venv-pp2/bin/python; CS=/usr/local/cuda-12.8/bin/compute-sanitizer
until /usr/bin/grep -q "QUEUE-D33 done" $O/pp2-go.state; do sleep 30; done
/usr/bin/grep -q "QUEUE-D33 server up: REC + VLLM_V41_MIX_STREAM=1" $O/pp2-go.state && FULL="$FULL VLLM_V41_MIX_STREAM=1"
back() { KEEP_LOCK=1 bash $O/stop-pp2.sh >> $O/warm-d34.log 2>&1; sleep 10; env $FULL $1 PROFILE=serve-v41pkg-pp2.yaml bash $O/serve-pp2.sh >> $O/warm-d34.log 2>&1 && st "server up: REC${1:+ + $1} ($(sha256sum $LIB | cut -c1-16))" || st "boot FAILED"; }
st "start: stop server, build diet1103 v41k.so, expert_diet_check + sanitizers (base env: $(echo $FULL | /usr/bin/grep -o 'MIX_STREAM=1' || echo 'no MIX_STREAM'))"
KEEP_LOCK=1 bash $O/stop-pp2.sh > $O/d34-stop.log 2>&1; sleep 15
CUDA_VISIBLE_DEVICES= TORCH_CUDA_ARCH_LIST=7.0 MAX_JOBS=4 nice -n 19 $PY -I $D/v41k-diet1103/build.py > $O/v41k-diet1103-build.log 2>&1; echo "EXIT $?" >> $O/v41k-diet1103-build.log
if ! /usr/bin/grep -q "EXIT 0" $O/v41k-diet1103-build.log || [ ! -s $NEWLIB ]; then st "diet1103 build FAILED: $(tail -3 $O/v41k-diet1103-build.log | tr '\n' ' ' | cut -c1-300)"; back ""; st "done"; exit 1; fi
st "diet1103 v41k.so built $(sha256sum $NEWLIB | cut -c1-16) ($(stat -c %s $NEWLIB) B)"
G="CUDA_DEVICE_ORDER=PCI_BUS_ID CUDA_VISIBLE_DEVICES=0"
env -u VLLM_V41_EXPERT_DIET $G timeout 30m $PY -I $O/expert_diet_check.py --lib $NEWLIB > $O/edc.json 2> $O/edc.err; rc=$?
st "expert_diet_check rc=$rc: $(/usr/bin/python3 -I -c "
import json
r=json.load(open('$O/edc.json'))
print('ok', r.get('ok'), 'failing', r.get('failing_trials'), '|', json.dumps(r.get('gtype'))[:600])" 2>&1 | tail -1 | cut -c1-700)"
san=0
for tool in memcheck racecheck synccheck; do t=2; [ $tool = memcheck ] && t=6
  env -u VLLM_V41_EXPERT_DIET $G timeout 30m $CS --tool $tool --error-exitcode 9 $PY -I $O/expert_diet_check.py --lib $NEWLIB --no-time --trials $t > $O/edc-$tool.out 2>&1; r=$?
  st "sanitizer $tool rc=$r: $(/usr/bin/grep -E "ERROR SUMMARY|RACECHECK SUMMARY|errors" $O/edc-$tool.out | tail -1 | cut -c1-160)"; [ $r = 0 ] || san=1
done
if [ $rc != 0 ] || [ $san != 0 ]; then st "DIET gate FAILED (check rc=$rc, sanitizers $san): not deployed"; back ""; st "done"; exit 1; fi
cp -p $LIB $LIB.pre-diet1103 && cp $NEWLIB $LIB.new && mv $LIB.new $LIB && st "DIET .so deployed $(sha256sum $LIB | cut -c1-16) (backup v41k.so.pre-diet1103 $(sha256sum $LIB.pre-diet1103 | cut -c1-16))" || { st "DIET .so deploy FAILED"; back ""; st "done"; exit 1; }
lines() { local L=$O/serve-pp2-D34-$1.log; cp $B/run-pp2/state/serve-pp2.log $L; st "$1 lines: ef-active $(/usr/bin/grep -c 'VLLM_V41_EXPERT_FAST=1: routed-expert down' $L), mix-stream $(/usr/bin/grep -c 'VLLM_V41_MIX_STREAM=1: MIX on side stream' $L), diet-mentions $(/usr/bin/grep -ci 'EXPERT_DIET' $L), tracebacks $(/usr/bin/grep -c Traceback $L)"; }
bash $O/ab-arm-t1.sh DT-OFF $FULL; lines DT-OFF
bash $O/ab-arm-t1.sh DT-ON $FULL $DT; lines DT-ON
SKIP_GREEDY=1 bash $O/ab-arm-t1.sh DT-ON2 $FULL $DT; lines DT-ON2
SKIP_GREEDY=1 bash $O/ab-arm-t1.sh DT-OFF2 $FULL; lines DT-OFF2
P=$(/usr/bin/python3 -I $O/pairs_arms.py $O DT-OFF DT-ON DT-OFF2 DT-ON2 DT-OFF DT-OFF2 2>&1)
st "DT pairs: $(echo "$P" | tr '\n' ';' | cut -c1-700)"; W=$(echo "$P" | /usr/bin/python3 -I $O/win.py); st "DT verdict: $W"
st "DT-ON greedy: $(/usr/bin/grep -h 'GREEDY rc' $(ls -t $O/ab-DT-ON-2026*.log | head -1) | cut -c1-300)"
case "$W" in WIN*) back "$DT";; *) back "";; esac
st "done (diet .so stays deployed; inert with VLLM_V41_EXPERT_DIET unset)"
