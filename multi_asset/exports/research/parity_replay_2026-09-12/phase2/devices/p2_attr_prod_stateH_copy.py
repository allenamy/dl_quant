#!/usr/bin/env python3
"""ATTR input copy (PREREG_combo_chain_residual_attribution_2026-09-13 AMENDMENT 1): READ-ONLY copy of the producer's per-anchor combo states
~/wide_shadow/fea171/state_H_{f10,kc,fc}_<A>.npz into a scratch staging dir (then shipped to pod2 P2/work/live_ro/prod_stateH_attr/).
Each file is hashed with the t6_sha_guard rule (no APFS dataless flag; bytes read == st_size; sha256(empty) for a non-empty file refused) before AND after
the copy (source unchanged) and the staged copy is hashed again (copy equal). Writes: staging dir under cc_tmp, SHA256SUMS (basenames) + JSON manifest
into phase2/receipts/. Never writes under ~/wide_shadow.
usage: python3 p2_attr_prod_stateH_copy.py <staging_dir>"""
import os, sys, re, stat, json, time, shutil, hashlib
SF_DATALESS = getattr(stat, "SF_DATALESS", 0x40000000); EMPTY = hashlib.sha256(b"").hexdigest()
SRC = os.path.expanduser("~/wide_shadow/fea171"); HERE = os.path.dirname(os.path.abspath(__file__)); RC = os.path.join(os.path.dirname(HERE), "receipts")
STG = os.path.abspath(sys.argv[1]); assert STG.startswith("/Users/haosiyu/cc_tmp/"), STG; assert not os.path.realpath(STG).startswith(os.path.realpath(os.path.expanduser("~/wide_shadow")))
def guarded(p):
    st = os.stat(p)
    if st.st_flags & SF_DATALESS: raise SystemExit("REFUSE dataless %s" % p)
    h = hashlib.sha256(); n = 0
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b); n += len(b)
    if n != st.st_size: raise SystemExit("REFUSE short read %s %d/%d" % (p, n, st.st_size))
    d = h.hexdigest()
    if st.st_size > 0 and d == EMPTY: raise SystemExit("REFUSE empty sha for non-empty %s" % p)
    return d, n
pat = re.compile(r"^state_H_(f10|kc|fc)_(\d{10})\.npz$")
files = sorted(f for f in os.listdir(SRC) if pat.match(f))
os.makedirs(STG, exist_ok=True); rows = []; bad = []
for f in files:
    s0, n = guarded(f"{SRC}/{f}"); shutil.copyfile(f"{SRC}/{f}", f"{STG}/{f}"); s1, _ = guarded(f"{SRC}/{f}"); s2, _ = guarded(f"{STG}/{f}")
    if not (s0 == s1 == s2): bad.append(f)
    rows.append({"file": f, "tag": pat.match(f).group(1), "anchor": int(pat.match(f).group(2)), "bytes": n, "sha256": s0, "src_mtime_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(os.stat(f"{SRC}/{f}").st_mtime))})
sums = os.path.join(RC, "ATTR_prod_stateH_SHA256SUMS.txt"); open(sums, "w").write("".join("%s  %s\n" % (r["sha256"], r["file"]) for r in rows))
man = {"device": os.path.basename(__file__), "self_sha256": guarded(os.path.abspath(__file__))[0], "source_dir": SRC, "staging_dir": STG, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
       "n_files": len(rows), "n_by_tag": {t: sum(1 for r in rows if r["tag"] == t) for t in ("f10", "kc", "fc")}, "anchor_min": min(r["anchor"] for r in rows), "anchor_max": max(r["anchor"] for r in rows),
       "copy_mismatch": bad, "sums_file_sha256": guarded(sums)[0], "files": rows}
mp = os.path.join(RC, "ATTR_prod_stateH_manifest.json"); json.dump(man, open(mp, "w"), indent=1)
print("ATTR_PROD_STATEH_COPY n=%d by_tag=%s anchors=%d..%d copy_mismatch=%d sums_sha=%s manifest_sha=%s" % (len(rows), man["n_by_tag"], man["anchor_min"], man["anchor_max"], len(bad), man["sums_file_sha256"], guarded(mp)[0]))
sys.exit(1 if bad else 0)
