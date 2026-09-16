#!/bin/bash
set -uo pipefail
TREE=/Users/haosiyu/cc_tmp/fx_exec
W=/Users/haosiyu/cc_tmp/fx_exec_work/new02
MUT="$W/mutants_gc"; mkdir -p "$MUT"
RUN1=/Users/haosiyu/Desktop/quant_research/docs/fixprogram_2026-09-13/FX_EXEC/receipts/common/run1.sh
GC="$TREE/ops/gate_coverage.py"
cp "$GC" "$MUT/.gc.orig"; GC0=$(shasum -a 256 "$GC" | cut -d' ' -f1)
echo "# gate_coverage mutants  $(date -u +%Y-%m-%dT%H:%M:%SZ)  head=$(git -C "$TREE" rev-parse HEAD)"
echo "# baseline gate_coverage=$GC0"
run_one () {
  /usr/bin/python3 - "$GC" <<PYEOF
import sys
gc = sys.argv[1]
$3
PYEOF
  if [ $? -ne 0 ]; then echo "GM $1  SETUP-FAILED — $2"; cp "$MUT/.gc.orig" "$GC"; return; fi
  bash "$RUN1" "$TREE" live/tests_external_book.py "$MUT/gm_$1.log" >/dev/null 2>&1; RC=$?
  GRC=$(/usr/bin/python3 "$GC" >/dev/null 2>&1; echo $?)
  echo "GM $1  suite_rc=$RC  gate_rc=$GRC  $( [ "$RC" -ne 0 ] && echo CAUGHT || echo '*** NOT CAUGHT ***')  — $2"
  grep '^  FAIL' "$MUT/gm_$1.log" | sed 's/  — .*//' | sed 's/^/        /' | head -4
  grep -c 'Traceback' "$MUT/gm_$1.log" | sed 's/^/        tracebacks=/'
  cp "$MUT/.gc.orig" "$GC"
  [ "$(shasum -a 256 "$GC" | cut -d' ' -f1)" = "$GC0" ] || echo "        !!! RESTORE MISMATCH"
}

run_one GM1 "duplicate_literal_keys always returns {}" \
's=open(gc,encoding="utf-8").read(); o="    path = path or os.path.abspath(__file__)"; assert s.count(o)==1; open(gc,"w",encoding="utf-8").write(s.replace(o,"    return {}\n    path = path or os.path.abspath(__file__)"))'

run_one GM2 "scan only the FIRST dict literal (stop after one)" \
's=open(gc,encoding="utf-8").read(); o="""        for val, lines in seen.items():
            if len(lines) > 1:
                out.setdefault(val, []).extend(lines)"""; assert s.count(o)==1; open(gc,"w",encoding="utf-8").write(s.replace(o,o+"\n        break"))'

run_one GM3 "verify() stops consulting the checker" \
's=open(gc,encoding="utf-8").read(); o="    for key, lines in sorted(duplicate_literal_keys(self_path).items(), key=lambda kv: str(kv[0])):"; assert s.count(o)==1; open(gc,"w",encoding="utf-8").write(s.replace(o,"    for key, lines in []:"))'

run_one GM4 "sort the duplicates without str() (mixed int/str keys ⇒ TypeError)" \
's=open(gc,encoding="utf-8").read(); o=", key=lambda kv: str(kv[0])):"; assert s.count(o)==1; open(gc,"w",encoding="utf-8").write(s.replace(o,"):"))'

run_one GM5 "ignore int keys (only string keys count as duplicates)" \
's=open(gc,encoding="utf-8").read(); o="            if not isinstance(k, ast.Constant):"; assert s.count(o)==1; open(gc,"w",encoding="utf-8").write(s.replace(o,"            if not isinstance(k, ast.Constant) or not isinstance(k.value, str):"))'

run_one GM6 "re-insert the stale duplicate SUITE_SCOPE entry (the defect itself)" \
'
s=open(gc,encoding="utf-8").read()
lines=s.split("\n")
i=[n for n,l in enumerate(lines) if l.startswith("    \"tests_external_book\":")]
assert len(i)==1, i
lines.insert(i[0], "    \"tests_external_book\": \"STALE pre-universe text (w/gross_norm, shadow_loop_v2, six blind spots)\",")
open(gc,"w",encoding="utf-8").write("\n".join(lines))
'

echo "# restored: $(shasum -a 256 "$GC" | cut -d' ' -f1)"
rm -f "$MUT/.gc.orig"
