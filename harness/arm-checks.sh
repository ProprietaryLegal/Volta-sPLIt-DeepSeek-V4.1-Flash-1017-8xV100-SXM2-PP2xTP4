# arm-checks.sh: sourced by ab-arm.sh, ab-arm-t1.sh and ab-depth-arm.sh (main, 11-03; REVIEW1103 F1/F2/F5).
# Needs B, O, LABEL, LOG and log() from the caller.
#   alive          0 when the server answers /health
#   invalid REASON log "AB <label> INVALID: REASON" to the arm log and pp2-go.state, then exit 1
#   warm           untimed warm-up (one T=0 + one seeded T=1 request); INVALID on failure
#   need_line F P  INVALID unless file F has a line matching P and the server is still alive
alive() { /usr/bin/curl -sf -m 10 http://127.0.0.1:18042/health > /dev/null; }
invalid() {
  log "AB $LABEL INVALID: $*"
  echo "$(date -u +%FT%TZ) AB $LABEL INVALID: $*" >> $O/pp2-go.state
  exit 1
}
warm() {
  /usr/bin/python3 -I $O/warmup.py http://127.0.0.1:18042 > "$O/ab-$LABEL-warm.out" 2>&1
  cat "$O/ab-$LABEL-warm.out" >> "$LOG"
  /usr/bin/grep -q "^WARMUP OK" "$O/ab-$LABEL-warm.out" || invalid "warm-up failed"
}
need_line() {
  /usr/bin/grep -q "$2" "$1" || invalid "no '$2' line (bench crashed or the engine died)"
  alive || invalid "server not answering /health after the bench"
}
