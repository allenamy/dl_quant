#!/usr/bin/env python3
"""FAST-GATE v2 (15:4xZ): fast_exec.py v2 (= v1 + gc.collect() and malloc_trim(0) BETWEEN anchors, memory report) must reproduce the same
52 anchors of FAST-GATE v1 (receipts/FAST_GATE.json, PASS 52/52) bit for bit:
  - the 24 anchors whose reference is the A0_main P2 shard (standard path): full f10 array bitwise + sha256 equal + members + model sha;
  - the 28 anchors scored by the standard path inside v1 (2022 / 2025 / 2026): sha256 of the f10 bytes must start with v1's recorded 64-bit
    prefix of the standard path's sha (v1 stored 16 hex digits), and members / count equal.
Two executors run in parallel (own sandboxes). Records per-anchor wall time and executor VmRSS / VmHWM after each anchor.
VERDICT PASS <=> 52/52 equal. Writes receipts/FAST_GATE_v2.json.  usage: as fast_gate.py"""
import os, sys, json, time, shutil, subprocess, hashlib, threading, calendar
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import b_lib as BL
import b_driver as BD
import b_scorer as BS
from fast_gate import prep, read, fsha, WENV

R = BD.R; PY = BD.VENV_PY; ROOT = "/dev/shm/object_b_fastgate2"


def main():
    t_all = time.time(); v1 = json.load(open(f"{R}/receipts/FAST_GATE.json")); assert v1["VERDICT"] == "PASS"
    G = BD.Globals(load_cache=True); P = BS.load_p1(f"{R}/work/A0_main/P1"); idx = {int(a): k for k, a in enumerate(P["anchor"])}
    fea_src, reader_src, man = BD.stage_sources()
    refs = {}
    for f in sorted(os.listdir(f"{R}/work/A0_main/p2")):
        if f.startswith("shard_") and f.endswith(".npz") and not f.endswith(".tmp.npz"): refs.update(BS.as_dict(f"{R}/work/A0_main/p2/{f}"))
    rows_v1 = v1["rows"]; shutil.rmtree(ROOT, ignore_errors=True); out_rows = [None] * len(rows_v1); lock = threading.Lock()

    def lane(k):
        ws = BL.make_sandbox(f"{ROOT}/l{k}", fea_src, BD.SRC["bundle_config"][0], PY)
        ex = subprocess.Popen([PY, "-B", f"{HERE}/fast_exec.py"], env={**WENV, "HOME": f"{ROOT}/l{k}"}, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
        assert json.loads(ex.stdout.readline())["ready"]
        for j in range(k, len(rows_v1), 2):
            r1 = rows_v1[j]; A = calendar.timegm(time.strptime(r1["anchor"], "%Y-%m-%dT%H:%M:%SZ"))
            Y = int(r1["fold"])
            with lock: pm = prep(G, P, idx[A], A, Y, ws)
            out = f"{ROOT}/l{k}/score.npz"
            if os.path.exists(out): os.remove(out)
            env = {**WENV, "HOME": f"{ROOT}/l{k}", "WIDE_SHADOW_HOME": ws, "F10_SCORE_OUT": out}
            ex.stdin.write(json.dumps({"cwd": f"{ws}/fea171", "env": env}) + "\n"); ex.stdin.flush(); res = json.loads(ex.stdout.readline())
            row = {"anchor": r1["anchor"], "fold": Y, "t_fast": res["dt"], "rc": res["rc"], "mem_gb": res.get("mem_gb")}
            if res["rc"] != 0:
                row["equal"] = False; row["log"] = res["log"]
            else:
                got = read(out); s = fsha(got["f10"])
                if r1["ref"] == "A0_main P2 shard":
                    ref = refs[A]; eq = bool(got["need"] and np.array_equal(got["pm"], ref["pm"]) and np.array_equal(got["f10"], ref["f10"], equal_nan=True)
                                             and s == fsha(ref["f10"]) and got["model_sha"] == ref["model_sha"]); row["ref"] = "A0_main P2 shard (full array)"
                else:
                    eq = bool(got["need"] and s.startswith(r1["sha_ref"]) and len(got["pm"]) == r1["n_members"] and int(got["okf"].sum()) == r1["n_scored"])
                    row["ref"] = "v1 standard-path sha256 prefix (64 bit)"
                row.update({"equal": eq, "sha": s[:16]})
            out_rows[j] = row; print(json.dumps(row), flush=True)
        ex.stdin.close(); ex.wait()

    th = [threading.Thread(target=lane, args=(k,)) for k in (0, 1)]
    for t in th: t.start()
    for t in th: t.join()
    rows = [r for r in out_rows if r is not None]
    doc = {"gate": "FAST-GATE v2", "comparison_type": "(3) packaging / scorer-path parity — not a return", "v1_receipt_sha256": BL.sha(f"{R}/receipts/FAST_GATE.json"),
           "n_anchors": len(rows), "n_equal": sum(1 for r in rows if r.get("equal")), "VERDICT": "PASS" if (len(rows) == len(rows_v1) and all(r.get("equal") for r in rows)) else "FAIL",
           "t_fast_median_s": float(np.median([r["t_fast"] for r in rows])), "rss_gb_max": max((r["mem_gb"] or {}).get("VmRSS", 0) for r in rows),
           "hwm_gb_max": max((r["mem_gb"] or {}).get("VmHWM", 0) for r in rows), "rows": rows,
           "devices_sha256": {"fast_exec.py": BL.sha(f"{HERE}/fast_exec.py"), "f10_scorer_3520d363.py": BL.sha(f"{HERE}/f10_scorer_3520d363.py"), "self": BL.sha(os.path.abspath(__file__))},
           "wall_s": round(time.time() - t_all, 1), "utc": BL.iso(time.time())}
    json.dump(doc, open(f"{R}/receipts/FAST_GATE_v2.json", "w"), indent=1)
    print(json.dumps({k: doc[k] for k in ("n_anchors", "n_equal", "VERDICT", "t_fast_median_s", "rss_gb_max", "hwm_gb_max", "wall_s")}), flush=True)
    shutil.rmtree(ROOT, ignore_errors=True)


if __name__ == "__main__":
    main()
