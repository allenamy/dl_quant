"""Regenerate receipts/v4_scripts_sha_full.json from a PER-FILE walk of this archive (round 3, review 31fa3e4e §5).

★ WHY: the previous manifest carried hand-maintained top-level counters (n_scripts / n_match_pod2 / n_r1_snapshots) that drifted from the
  per-entry rows, listed 75 of the 78 files, kept a stale MATCH for pod_export_bundle_v4.py (archive b5b6cd19 vs pod 23b1a5c7) and mapped the
  round-1 g3 judge receipt to the CURRENT judge. Counts are now derived from the rows, never typed.

Status per file (one of):
  MATCH_POD2        archive sha == pod2 sha (pod2 shas supplied via POD2_SHA_FILE, one "<sha256> <name>" per line, "MISSING <name>" if absent)
  POD2_DIFFERS      both present, different
  NOT_ON_POD2       no pod2 copy (all snapshots are expected here; a live script here is a sync gap)
  SNAPSHOT_r0/r1/r2/r3  by actual filename prefix (.r0_<sha8>., .r1_, .r2_, .r3_): receipt-producing versions kept alongside (判决装置与结论同寿命)
Usage: POD2_SHA_FILE=<file> python make_sha_manifest.py [out.json]   (default out: receipts/v4_scripts_sha_full.json)
"""
import hashlib, json, os, re, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "receipts", "v4_scripts_sha_full.json")
SNAP = re.compile(r"\.r([0-3])_[0-9a-f]{8}\.")

# receipt -> the source version that PRODUCED it (round 3: g3 s2027 judge receipt -> the r2 judge, not the current one)
RECEIPT_TO_SOURCE = {
    "V3P_RAW.json": "v4_leakcheck.r0_bb7f14ac.py",
    "V3P_CLIP.json": "v4_leakcheck.r0_bb7f14ac.py",
    "V3P_RAW_mwf_v4b.json": "v4_leakcheck.r0_bb7f14ac.py",
    "V3P_CLIP_mwf_v4b.json": "v4_leakcheck.r0_bb7f14ac.py",
    "V3P_RAW_mwf_v4b_amd6.json": "v4_leakcheck.r1_b19a588e.py",
    "V3P_CLIP_mwf_v4b_amd6.json": "v4_leakcheck.r1_b19a588e.py",
    "V3P_RAW_mwf_v4s_amd6_s42.json": "v4_leakcheck.r1_b19a588e.py",
    "V3P_RAW_mwf_v4s_amd6_s2027.json": "v4_leakcheck.py",
    "JUDGE_v4.json": "judge_v4.r1_23c2cda7.py",
    "JUDGE_v4_g3_s2027.json": "judge_v4.r2_17b562fd.py",              # round 3 fix: the 14-cell judge of round 1, not the 18-cell current one
    "JUDGE_v4e_informational.json": "judge_v4.r3_8b2c13b7.py",       # produced before the round-3 judge hardening
    "JUDGE_v4e_hardened.json": "judge_v4.r3_8b2c13b7.py",
    "G1_king_clock_parity.json": "v4e_gate_parity.r3_c69b3322.py",   # produced before the round-3 axis-clause change
    "G1_king_clock_parity_run1_FAIL.json": "v4e_gate_parity.r3_c69b3322.py",
    "G2_closure_stable_hardened.json": "v4_gate_closure.py",
    "G4_king_quant.json": "v4e_gate_quant.py",
    "guard_decompose_v4e.json": "guard_decompose_v4e.py",
    "guard_decompose_v4e_v2extpanel.json": "guard_decompose_v4e.py",
    "align_v4e.json": "align_king_v4e.py",
}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    pod2 = {}
    pf = os.environ.get("POD2_SHA_FILE")
    if pf and os.path.exists(pf):
        for line in open(pf):
            line = line.strip()
            if not line:
                continue
            a, b = line.split(" ", 1)
            pod2[b.strip()] = None if a == "MISSING" else a
    files = sorted(f for f in os.listdir(HERE) if f.endswith((".py", ".sh")) and os.path.isfile(os.path.join(HERE, f)))
    rows = {}
    for f in files:
        s = sha(os.path.join(HERE, f)); m = SNAP.search(f); p2 = pod2.get(f) if pf else "UNQUERIED"
        if m:
            st = f"SNAPSHOT_r{m.group(1)}"
        elif p2 == "UNQUERIED":
            st = "POD2_UNQUERIED"
        elif p2 is None:
            st = "NOT_ON_POD2"
        else:
            st = "MATCH_POD2" if p2 == s else "POD2_DIFFERS"
        rows[f] = {"archive_sha256": s, "pod2_sha256": (None if p2 in (None, "UNQUERIED") else p2), "status": st}
    counts = {}
    for r in rows.values():
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    missing_sources = sorted({v for v in RECEIPT_TO_SOURCE.values() if v not in rows})
    missing_receipts = sorted(k for k in RECEIPT_TO_SOURCE if not os.path.exists(os.path.join(HERE, "receipts", k)))
    out = {"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "archive_dir": HERE, "pod2_path": "/workspace/review_scratch/",
           "pod2_sha_file": pf, "n_files": len(files), "counts_by_status": dict(sorted(counts.items())),
           "generator": "make_sha_manifest.py (per-file walk; counts derived from rows, never typed)",
           "scripts": rows, "receipt_to_source": RECEIPT_TO_SOURCE,
           "receipt_to_source_missing_sources": missing_sources, "receipt_to_source_missing_receipts": missing_receipts,
           "note": ("*.rN_<sha8>.* are the versions that produced receipts (判决装置与结论同寿命); a live script NOT_ON_POD2 or POD2_DIFFERS is a "
                    "sync gap between this archive and /workspace/review_scratch and must be resolved by syncing, not by editing this file. "
                    "Round-3 (review 31fa3e4e §5): the previous hand-typed counters (75/50/0/6) are replaced by these derived counts.")}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(out, open(OUT, "w"), indent=1)
    print(json.dumps({"n_files": out["n_files"], "counts": out["counts_by_status"], "missing_sources": missing_sources, "missing_receipts": missing_receipts, "out": OUT}, indent=0))
    return 0 if not missing_sources else 2


if __name__ == "__main__":
    sys.exit(main())
