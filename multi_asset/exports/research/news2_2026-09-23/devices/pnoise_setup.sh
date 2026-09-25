#!/usr/bin/env bash
# pnoise_setup.sh -- build the isolated experiment root for the perturbation-noise run (K=8).
#
# WHY A SEPARATE ROOT: news2_train_king.py and news2_train_f10.py hardcode
#   W = /dev/shm/news2_2026-09-23
# and King does out.mkdir(exist_ok=False). Running 8 perturbed chains in that workspace would
# displace the archived NC artifacts that are the BASELINE of this very comparison. So the
# experiment gets its own root; the NC workspace is opened READ-ONLY (hardlinks only).
#
# The two path-hardcoded devices are copied with EXACTLY ONE constant changed (the W root). Every
# other byte is identical; the diff is recorded in the receipt. The run_state=0 red control is what
# certifies this harness: if it does not reproduce the archived dbar bitwise, the harness is wrong
# and the experiment is void.
#
# Hardlinks cost no space (same tmpfs), so NEWS_FEATURES.npz (2.9 GB) is shared, not copied.
set -euo pipefail

SRC=/dev/shm/news2_2026-09-23
NC=/dev/shm/nc_2026-09-23
EXP=/dev/shm/pnoise_2026-09-24

mkdir -p "$EXP"/{work,receipts,logs,targets,runs,configs,inputs}

# devices: full copy (small), then repoint W in exactly the two files that hardcode it
cp -a "$SRC/devices/." "$EXP/devices/"
cp -a "$SRC/engine" "$EXP/engine" 2>/dev/null || true
cp -a "$SRC/inputs/." "$EXP/inputs/" 2>/dev/null || true

for f in news2_train_king.py news2_train_f10.py; do
  python3 - "$EXP/devices/$f" "$SRC" "$EXP" <<'PY'
import sys
p, src, exp = sys.argv[1], sys.argv[2], sys.argv[3]
s = open(p).read()
old = "pathlib.Path('%s')" % src
new = "pathlib.Path(os.environ.get('PNOISE_W', '%s'))" % exp
assert s.count(old) == 1, (p, s.count(old))
s = s.replace(old, new)
if "\nimport os" not in s and not s.startswith("import os"):
    s = s.replace("import ", "import os, ", 1)
open(p, "w").write(s)
print("repointed", p)
PY
done

# tree + static inputs the devices read
ln -sf "$SRC/treeNC5_deploy" "$EXP/treeNC5_deploy" 2>/dev/null || true
[ -e "$EXP/work/NEWS_FEATURES.npz" ] || ln "$SRC/work/NEWS_FEATURES.npz" "$EXP/work/NEWS_FEATURES.npz"
[ -e "$EXP/work/members_hist_all.npz" ] || ln "$SRC/work/members_hist_all.npz" "$EXP/work/members_hist_all.npz" 2>/dev/null || true
cp -a "$SRC/receipts/P2B_FEATURES.json" "$EXP/receipts/" 2>/dev/null || true

echo "--- root ready ---"
ls -la "$EXP" | head -12
echo "features inode shared with NC workspace:"
stat -c '%i %n' "$SRC/work/NEWS_FEATURES.npz" "$EXP/work/NEWS_FEATURES.npz"
df -h /dev/shm | tail -1
