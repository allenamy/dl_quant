#!/bin/bash
# NEW-02 mutants: mutate the FIX (never the test), confirm the suite goes red, restore, verify the restore is
# byte-identical. A mutant that leaves the suite green is an uncovered branch, not a pass.
set -uo pipefail
TREE=/Users/haosiyu/cc_tmp/fx_exec
W=/Users/haosiyu/cc_tmp/fx_exec_work/new02
MUT="$W/mutants"; mkdir -p "$MUT"
RUN1=/Users/haosiyu/Desktop/quant_research/docs/fixprogram_2026-09-13/FX_EXEC/receipts/common/run1.sh
VF="$TREE/live/venue_fills.py"; BF="$TREE/ops/backfill_fills.py"
cp "$VF" "$MUT/.vf.orig"; cp "$BF" "$MUT/.bf.orig"
VF0=$(shasum -a 256 "$VF" | cut -d' ' -f1); BF0=$(shasum -a 256 "$BF" | cut -d' ' -f1)
echo "# NEW-02 mutants  $(date -u +%Y-%m-%dT%H:%M:%SZ)  head=$(git -C "$TREE" rev-parse HEAD)"
echo "# baseline venue_fills=$VF0  backfill_fills=$BF0"

run_one () {  # $1 = id, $2 = description, $3 = python mutation script
  /usr/bin/python3 - "$VF" "$BF" <<PYEOF
import sys
vf, bf = sys.argv[1], sys.argv[2]
$3
PYEOF
  if [ $? -ne 0 ]; then echo "MUT $1  SETUP-FAILED (mutation did not apply) — $2"; cp "$MUT/.vf.orig" "$VF"; cp "$MUT/.bf.orig" "$BF"; return; fi
  bash "$RUN1" "$TREE" live/tests_flatten_fee_backfill.py "$MUT/mut_$1.log" >/dev/null 2>&1
  RC=$?
  NRED=$(grep -c '^  FAIL' "$MUT/mut_$1.log")
  CRASH=$(grep -cE 'Traceback|AttributeError|TypeError: ' "$MUT/mut_$1.log")
  echo "MUT $1  rc=$RC  red_cells=$NRED  crashy_lines=$CRASH  $( [ "$RC" -ne 0 ] && echo CAUGHT || echo '*** NOT CAUGHT ***')  — $2"
  grep '^  FAIL' "$MUT/mut_$1.log" | sed 's/  — .*//' | sed 's/^/        /' | head -8
  cp "$MUT/.vf.orig" "$VF"; cp "$MUT/.bf.orig" "$BF"
  A=$(shasum -a 256 "$VF" | cut -d' ' -f1); B=$(shasum -a 256 "$BF" | cut -d' ' -f1)
  [ "$A" = "$VF0" ] && [ "$B" = "$BF0" ] || echo "        !!! RESTORE MISMATCH"
}

run_one M1 "drop the 36-char truncation guard in attempt_from_client_id" \
's=open(vf,encoding="utf-8").read(); o="    if not cid or len(cid) >= 36:"; assert s.count(o)==1; open(vf,"w",encoding="utf-8").write(s.replace(o,"    if not cid:"))'

run_one M2 "parse the attempt by splitting on the last dash (ignore the rebalance-id/symbol shape)" \
's=open(vf,encoding="utf-8").read(); o="""    pre = f"{rebalance_id}-{symbol}-"
    if not cid.startswith(pre):
        return None
    tail = cid[len(pre):]"""; assert s.count(o)==1; open(vf,"w",encoding="utf-8").write(s.replace(o,"    tail = cid.rsplit(\"-\", 1)[-1]"))'

run_one M3 "attribute_trades stops carrying the leg attempt onto the trade row" \
's=open(vf,encoding="utf-8").read(); o="""            if info.get("attempt_idx") is not None:
                row["attempt_idx"] = int(info["attempt_idx"])"""; assert s.count(o)==1; open(vf,"w",encoding="utf-8").write(s.replace(o,"            pass"))'

run_one M4 "unresolvable flatten falls back to 2 again (the original defect value)" \
's=open(vf,encoding="utf-8").read(); o="""            elif otype == "protective_flatten":
                _attempt = 1"""; assert s.count(o)==1; open(vf,"w",encoding="utf-8").write(s.replace(o,"""            elif otype == "protective_flatten":
                _attempt = 2"""))'

run_one M5 "keep the leg-type proxy for maker legs (ignore a resolved attempt of 2)" \
's=open(vf,encoding="utf-8").read(); o="""            if _leg_attempt is not None:
                _attempt = int(_leg_attempt)"""; assert s.count(o)==1; open(vf,"w",encoding="utf-8").write(s.replace(o,"""            if _leg_attempt is not None and otype != "maker":
                _attempt = int(_leg_attempt)"""))'

run_one M6 "find_gaps stops emitting attempt_by_client_id" \
's=open(bf,encoding="utf-8").read(); o="""                b["attempt_by_client_id"][str(o["client_id"])] = int(o.get("attempt_idx") or 1)"""; assert s.count(o)==1; open(bf,"w",encoding="utf-8").write(s.replace(o,"                pass"))'

run_one M7 "backfill_batch stops passing the map to order_legs_from_venue" \
's=open(bf,encoding="utf-8").read(); o="""                                        attempt_by_client_id=gap.get("attempt_by_client_id"))"""; assert s.count(o)==1; open(bf,"w",encoding="utf-8").write(s.replace(o,"                                        )"))'

run_one M8 "drop the isdigit guard (a non-numeric tail becomes an exception, not an absence)" \
's=open(vf,encoding="utf-8").read(); o="""    if not tail.isdigit():
        return None"""; assert s.count(o)==1; open(vf,"w",encoding="utf-8").write(s.replace(o,"    pass"))'

run_one M9 "order_legs_from_venue ignores the caller map and parses the id instead" \
's=open(vf,encoding="utf-8").read(); o="""                _att = (_att_by_cid.get(cid) if _att_by_cid
                        else attempt_from_client_id(cid, rebalance_id, r.get("symbol") or sym))"""; assert s.count(o)==1; open(vf,"w",encoding="utf-8").write(s.replace(o,"                _att = cid.rsplit(\"-\", 1)[-1]"))'

echo "# restored: venue_fills=$(shasum -a 256 "$VF" | cut -d' ' -f1)  backfill_fills=$(shasum -a 256 "$BF" | cut -d' ' -f1)"
rm -f "$MUT/.vf.orig" "$MUT/.bf.orig"
