#!/bin/bash
# stage 01b: sha256 manifest of every downloaded zip + list of 404 sentinels (input identity for the report) + zip integrity test (testzip on every file).
source /workspace/review_scratch/jpline_rebuild/lib.sh
cd $ROOT
run bash -c "find klines5m -name '*.zip' | sort | xargs -P 16 -n 200 sha256sum > logs/klines5m_SHA256SUMS.txt"
run bash -c "find klines5m -name '*.404' | sort > logs/klines5m_404.txt"
echo "manifest entries $(wc -l < logs/klines5m_SHA256SUMS.txt) 404s $(wc -l < logs/klines5m_404.txt)"
run $PY - <<'PY'
import zipfile, glob, sys, os
from concurrent.futures import ThreadPoolExecutor
fs = sorted(glob.glob("/workspace/review_scratch/jpline_rebuild/klines5m/*/*.zip"))
def chk(p):
    try:
        with zipfile.ZipFile(p) as z:
            bad = z.testzip(); n = len(z.namelist())
        return (p, "BAD:" + str(bad)) if bad or n != 1 or os.path.getsize(p) == 0 else None
    except Exception as e: return (p, repr(e))
with ThreadPoolExecutor(16) as ex: bad = [r for r in ex.map(chk, fs) if r]
open("/workspace/review_scratch/jpline_rebuild/logs/klines5m_badzips.txt", "w").write("\n".join(f"{p} {e}" for p, e in bad))
print(f"ZIP_INTEGRITY files {len(fs)} bad {len(bad)}"); print(bad[:10])
PY
run bash -c "sha256sum logs/klines5m_SHA256SUMS.txt logs/klines5m_404.txt logs/klines5m_badzips.txt"
[ -s logs/klines5m_badzips.txt ] && { echo "BAD ZIPS PRESENT — halting before the cache build (delete them and re-run stage 01 to re-pull)"; exit 5; }
exit 0
