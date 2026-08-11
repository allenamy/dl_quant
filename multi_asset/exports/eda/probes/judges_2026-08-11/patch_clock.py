import os

p = "/Users/haosiyu/dl_quant_live/ops/start_dryrun_clock.sh"
s = open(p).read()

s = s.replace("""#   4. the state tree matches the mode""",
"""#   4. the state tree matches the mode
#   5. the machine will not sleep — INSTALLED AND OBSERVED, not asked of the operator. A sleeping
#      machine fails the gate either way: no catch-up run (anchor missed) or a late catch-up run
#      (not counted, and since 87e8409 it refuses to open). Measured on this machine: `pmset`
#      said `sleep 0` on AC while the log held 106 "Maintenance Sleep" entries in one day — so
#      this step reads the sleep LOG, not the settings.""")

for i in (1, 2, 3, 4):
    s = s.replace(f'echo "── {i}/5 ', f'echo "── {i}/6 ')

NEW = '''echo "── 5/6  the machine must not sleep (installed, then OBSERVED)"
bash "$REPO/ops/install_nosleep.sh" > "$REPO/state/_clock_start_nosleep.log" 2>&1 || {
  echo "   ✗ could not install/verify the anti-sleep agent — see state/_clock_start_nosleep.log"
  exit 1
}
"$PY" "$REPO/ops/check_nosleep.py" --lookback-h 24 --gate
[ $? -ne 0 ] && exit 1

echo "── 6/6  write the start date"'''
s = s.replace('echo "── 5/5  write the start date"', NEW)
s = s.replace('echo "── ABORTED at step 5."', 'echo "── ABORTED at step 6."')
open(p, "w").write(s)
print("patched")
