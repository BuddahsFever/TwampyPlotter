#!/usr/bin/env bash
set -euo pipefail

TWAMPY="/home/misja/twampy/venv/bin/twampy"
TARGET="188.212.113.112:50000"
LOGDIR="/home/misja/twampy/logs"

DSCP="be"
PADDING="214"
INTERVAL="100"
COUNT="49999"

STOP_HOUR=14
STOP_MIN=0

mkdir -p "$LOGDIR"

LOGFILE="$LOGDIR/twampy-$(date +%F_%H-%M-%S).log"

echo "===== $(date -Is) START twampy monitor =====" >> "$LOGFILE"
echo "Using binary: $TWAMPY" >> "$LOGFILE"
echo "Target: $TARGET" >> "$LOGFILE"
echo "DSCP: $DSCP | Padding: $PADDING | Interval: $INTERVAL ms | Count: $COUNT" >> "$LOGFILE"
echo "=============================================" >> "$LOGFILE"

while true; do
    NOW_HM=$(date +%H%M)
    STOP_HM=$(printf "%02d%02d" "$STOP_HOUR" "$STOP_MIN")

    if (( 10#$NOW_HM >= 10#$STOP_HM )); then
        echo "===== $(date -Is) STOP time reached =====" >> "$LOGFILE"
        break
    fi

    echo "----- $(date -Is) New test run -----" >> "$LOGFILE"

    "$TWAMPY" sender "$TARGET" \
        --count "$COUNT" \
        --interval "$INTERVAL" \
        --dscp "$DSCP" \
        --padding "$PADDING" \
        --verbose \
        >> "$LOGFILE" 2>&1

    RC=$?
    echo "----- $(date -Is) Run finished rc=$RC -----" >> "$LOGFILE"

    sleep 5
done

echo "===== $(date -Is) END twampy monitor =====" >> "$LOGFILE"
