#!/bin/bash
set -uo pipefail
TREE=/Users/haosiyu/cc_tmp/fx_exec
W=/Users/haosiyu/cc_tmp/fx_exec_work/new02
MUT="$W/mutants_exe04"; mkdir -p "$MUT"
RUN1=/Users/haosiyu/Desktop/quant_research/docs/fixprogram_2026-09-13/FX_EXEC/receipts/common/run1.sh
F="$TREE/live/reconcile_carry.py"
cp "$F" "$MUT/.orig"; F0=$(shasum -a 256 "$F" | cut -d' ' -f1)
echo "# EXE-04 core mutants  $(date -u +%Y-%m-%dT%H:%M:%SZ)  head=$(git -C "$TREE" rev-parse HEAD)"
echo "# baseline reconcile_carry=$F0"
run_one () {
  /usr/bin/python3 - "$F" <<PYEOF
import sys
f = sys.argv[1]
$3
PYEOF
  if [ $? -ne 0 ]; then echo "EM $1  SETUP-FAILED — $2"; cp "$MUT/.orig" "$F"; return; fi
  bash "$RUN1" "$TREE" live/tests_reconcile_carry.py "$MUT/em_$1.log" >/dev/null 2>&1; RC=$?
  echo "EM $1  rc=$RC  red=$(grep -c '^  FAIL' "$MUT/em_$1.log")  tracebacks=$(grep -c Traceback "$MUT/em_$1.log")  $( [ "$RC" -ne 0 ] && echo CAUGHT || echo '*** NOT CAUGHT ***')  — $2"
  grep '^  FAIL' "$MUT/em_$1.log" | sed 's/:.*//;s/  — .*//' | sed 's/^/        /' | head -5
  cp "$MUT/.orig" "$F"
  [ "$(shasum -a 256 "$F" | cut -d' ' -f1)" = "$F0" ] || echo "        !!! RESTORE MISMATCH"
}

run_one EM1 "drop the monotone constraint (b)" \
's=open(f,encoding="utf-8").read(); o="                if v + 1e-12 < prev:                          # (b) monotone\n                    continue"; assert s.count(o)==1; open(f,"w",encoding="utf-8").write(s.replace(o,"                if False:\n                    continue"))'

run_one EM2 "drop post-terminal constancy (c)" \
's=open(f,encoding="utf-8").read(); o="            if pinned:"; assert s.count(o)==1; open(f,"w",encoding="utf-8").write(s.replace(o,"            if False:"))'

run_one EM3 "drop the birth-zero constraint (a)" \
's=open(f,encoding="utf-8").read(); o="        if t < self.birth:\n            return [0.0]"; assert s.count(o)==1; open(f,"w",encoding="utf-8").write(s.replace(o,"        if False:\n            return [0.0]"))'

run_one EM4 "let feasible_exact fall back to the UNSOUND marginal method instead of refusing" \
's=open(f,encoding="utf-8").read(); o="            return {\"status\": \"unmeasurable\", \"why\": \"too many joint trajectories to enumerate \""; assert s.count(o)==1; open(f,"w",encoding="utf-8").write(s.replace(o,"            return {\"status\": \"ok\", \"admitted\": [], \"excluded\": [], \"distance\": 0.0, \"predicted\": [0.0], \"history_unresolved\": False, \"n_trajectories\": None, \"why\": \"too many joint trajectories to enumerate \""))'

run_one EM5 "form the prediction AFTER admitting the current anchor's own equation" \
's=open(f,encoding="utf-8").read(); o="        if obs is None or k == _n:\n            continue"; assert s.count(o)==1; open(f,"w",encoding="utf-8").write(s.replace(o,"        if obs is None:\n            continue"))'

run_one EM6 "revisit admitted equations (maximum cardinality instead of chronological admission)" \
's=open(f,encoding="utf-8").read(); o="        kept = [tr for tr in live if abs(_sum_at(reqs, tr, k) - obs) <= 1e-9]"; assert s.count(o)==1; open(f,"w",encoding="utf-8").write(s.replace(o,"        kept = [tr for tr in pool if abs(_sum_at(reqs, tr, k) - obs) <= 1e-9]"))'

run_one EM7 "apply the credible terminal total at EVERY anchor, not from d_i onward" \
's=open(f,encoding="utf-8").read(); o="        if self.exact is not None and self.terminal is not None and t >= self.terminal:"; assert s.count(o)==1; open(f,"w",encoding="utf-8").write(s.replace(o,"        if self.exact is not None:"))'

run_one EM8 "stop reporting hard contradictions as unmeasurable (treat them as an empty-but-ok set)" \
's=open(f,encoding="utf-8").read(); o="        if self.contradiction():\n            return []"; assert s.count(o)==1; open(f,"w",encoding="utf-8").write(s.replace(o,"        if False:\n            return []"))'

run_one EM9 "pin the FIRST post-terminal anchor too (forbid the fills that closed the request)" \
's=open(f,encoding="utf-8").read(); o="            is_post = r.terminal is not None and t >= r.terminal"; assert s.count(o)==1; open(f,"w",encoding="utf-8").write(s.replace(o,"            is_post = r.terminal is not None and t >= r.terminal\n            if is_post and sofar:\n                walk(k + 1, sofar + (prev,), True); return"))'

echo "# restored: $(shasum -a 256 "$F" | cut -d' ' -f1)"
rm -f "$MUT/.orig"
