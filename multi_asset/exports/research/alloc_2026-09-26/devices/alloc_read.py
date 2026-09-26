#!/usr/bin/env python3
"""alloc_read.py — read ONE alloc engine cell against its same-seed NC reference cell with the FROZEN judge functions.

Imports news_stats.py (7141ba42) and calls its load_cell / seg_mask / full_days / dbar / boot unchanged (bt_tables 892ba66b,
bt_driver_lib ba3bc261 as it asserts). Segments = news_stats.SEG with 2026 extended to the X-axis end 2026-09-18T20Z (lead revision 3),
the frozen truncated 2026 reported alongside. Output per segment: dbar (bps/day), n_days, 30-day MBB 95% CI (news_stats.boot), iid SE,
and the maxDD 5m path mean of both cells.
usage: env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B alloc_read.py PATH,HOME,LC_CTYPE <arm_run_dir> <arm_tag_dir>
         <ref_run_dir> <ref_tag_dir> <out.json>
"""
import os, sys, json, math, hashlib, time
import numpy as np
ENG = "/dev/shm/news2_2026-09-23/engine"
NS_SHA = "7141ba42ab227b9f35b48acce62d5e2a2494f364fdf6a83189974cb2af67e03c"
sys.path.insert(0, ENG)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def main():
    WL = set(sys.argv[1].split(",")); extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
    for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"): os.environ[_k] = "1"
    arm_dir, arm_tag, ref_dir, ref_tag, out = sys.argv[2:7]
    assert sha(f"{ENG}/news_stats.py") == NS_SHA, "frozen judge drifted"
    import news_stats as S, bt_tables, bt_driver_lib
    for f, s in S.DEV.items(): assert sha(os.path.join(ENG, f)) == s, f"device sha {f}"
    S.BT, S.DL = bt_tables, bt_driver_lib
    pa, fa = S.load_cell(arm_dir, arm_tag); pr, fr = S.load_cell(ref_dir, ref_tag)
    A = pa[0]["A"]; assert np.array_equal(A, pr[0]["A"]), "axes differ"
    seg = dict(S.SEG); seg["2026_frozen_truncated"] = seg["2026"]; seg["2026"] = ("2026-01-01T00:00:00Z", "2026-09-18T20:00:00Z")
    res = {}
    for s, (a, b) in seg.items():
        m = S.seg_mask(A, a, b); days = S.full_days(A, m)
        x, D = S.dbar(pa, pr, m, days)
        bt = S.boot(x, S.BLOCK_MAIN)
        res[s] = {"n_days": int(len(x)), "dbar_bps_per_day": float(1e4 * x.mean()), "iid_se_bps": float(1e4 * x.std(ddof=1) / math.sqrt(len(x))),
                  "boot_30d": bt, "per_path_dbar_bps": [float(1e4 * v) for v in D.mean(1)],
                  "maxdd_5m_path_mean": {"arm": float(np.mean([bt_tables.maxdd_5m(p, m) for p in pa])),
                                         "ref": float(np.mean([bt_tables.maxdd_5m(p, m) for p in pr]))}}
        print(f"{s:24s} n={len(x):4d} dbar={1e4 * x.mean():+9.3f} bps/d  ci95={bt['ci95_bps']}", flush=True)
    rec = {"device": "alloc_read.py", "self_sha256": sha(os.path.abspath(__file__)), "frozen_judge_sha256": NS_SHA,
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "arm": {"dir": arm_dir, "tag": arm_tag, "facts": fa},
           "ref": {"dir": ref_dir, "tag": ref_tag, "facts": fr}, "segments": seg, "results": res}
    json.dump(rec, open(out + ".tmp", "w"), indent=1, default=float); os.replace(out + ".tmp", out)
    assert json.load(open(out))["self_sha256"] == rec["self_sha256"]
    print("written", out, sha(out)[:16], flush=True)


if __name__ == "__main__":
    main()
