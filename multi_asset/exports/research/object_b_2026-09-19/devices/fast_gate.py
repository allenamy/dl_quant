#!/usr/bin/env python3
"""FAST-GATE (lead request 14:4xZ; comparison type (3), no returns): the warm executor fast_exec.py must reproduce the standard P2 scorer path
(b_scorer.worker: `python -B f10_scorer_3520d363.py` with two child interpreters) BIT FOR BIT before any use.
Anchors (>= 50, spread over years): 2023-2024 anchors already scored by the running A0_main P2 (reference = its shard, i.e. the standard path);
2025, 2026 and 2022 anchors scored here by the standard path first (2022 has no admissible F10 fold: the 2023 fold is used ONLY to exercise the
code path, never for object B). Then the same inputs are re-written into a separate sandbox and scored by the fast executor.
Per anchor: pm equal, f10_pm bitwise equal (NaN positions equal), sha256 of the f10_pm bytes equal, okf equal, model sha equal, need_ran true.
VERDICT PASS <=> every anchor equal; one difference => FAIL and the fast path is abandoned. Paired wall times (standard vs fast) are recorded.
Writes receipts/FAST_GATE.json.  usage: env -i PATH=/usr/bin:/bin HOME=/root LC_CTYPE=C.UTF-8 nice -n 10 /workspace/venv/bin/python -B fast_gate.py"""
import os, sys, json, time, shutil, subprocess, hashlib, calendar
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import b_lib as BL
import b_driver as BD
import b_scorer as BS

R = BD.R; PY = BD.VENV_PY; ROOT = "/dev/shm/object_b_fastgate"
WENV = {"PATH": "/usr/bin:/bin", "LC_CTYPE": "C.UTF-8", "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"}


def fsha(a): return hashlib.sha256(np.ascontiguousarray(a, np.float64).tobytes()).hexdigest()


def prep(G, P, i, A, Y, ws):
    BL.clear_mini(f"{ws}/fea171")
    for f in ("rolling.npz", "aux.json", "leg_returns_live.json"):
        if os.path.exists(f"{ws}/state/{f}"): os.remove(f"{ws}/state/{f}")
    shutil.copy2(G.f10[Y]["np"], f"{ws}/fea171/f10_live_s42_np.npz")
    live = G.live_names(A); lm = np.zeros(829, bool); lm[[G.col[s] for s in live]] = True
    ts, cd = G.cache_tail(A, lm); np.savez(f"{ws}/state/rolling.npz", ts=ts, data=cd); del cd
    pm, aux = BS.p1_inputs(P, i, G.SYMS, A)
    json.dump(aux, open(f"{ws}/state/aux.json", "w")); json.dump({"king": [], "rev24": [], "fund": []}, open(f"{ws}/state/leg_returns_live.json", "w"))
    return pm


def read(out):
    z = np.load(out); return {"pm": z["pm"].astype(np.int64), "f10": z["f10_pm"].astype(np.float64), "okf": z["okf"].astype(bool), "model_sha": str(z["model_sha"]), "need": bool(z["need_ran"])}


def main():
    t_all = time.time(); G = BD.Globals(load_cache=True); P = BS.load_p1(f"{R}/work/A0_main/P1"); idx = {int(a): k for k, a in enumerate(P["anchor"])}
    fea_src, reader_src, man = BD.stage_sources()
    refs = {}
    for f in sorted(os.listdir(f"{R}/work/A0_main/p2")):
        if f.startswith("shard_") and f.endswith(".npz") and not f.endswith(".tmp.npz"): refs.update(BS.as_dict(f"{R}/work/A0_main/p2/{f}"))
    anchors = sorted(refs); yrs = lambda a: time.gmtime(a).tm_year
    pick = []
    have = [a for a in anchors if yrs(a) in (2023, 2024)]
    pick += [have[int(k)] for k in np.linspace(0, len(have) - 1, 24)]
    for Yr, n in ((2025, 12), (2026, 10), (2022, 6)):
        cand = [int(a) for a in P["anchor"] if yrs(int(a)) == Yr and (Yr != 2026 or int(a) <= calendar.timegm((2026, 8, 31, 0, 0, 0)))]
        pick += [cand[int(k)] for k in np.linspace(0, len(cand) - 1, n)]
    shutil.rmtree(ROOT, ignore_errors=True)
    ws_s = BL.make_sandbox(f"{ROOT}/std", fea_src, BD.SRC["bundle_config"][0], PY); ws_f = BL.make_sandbox(f"{ROOT}/fast", fea_src, BD.SRC["bundle_config"][0], PY)
    ex = subprocess.Popen([PY, "-B", f"{HERE}/fast_exec.py"], env={**WENV, "HOME": f"{ROOT}/fast"}, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
    assert json.loads(ex.stdout.readline())["ready"]
    rows = []; ok_all = True
    for A in pick:
        i = idx[A]; Y = BL.f10_fold_for(A, G.f10); note = None
        if Y is None: Y = 2023; note = "2022: no admissible fold; 2023 fold used only to exercise the code path"
        row = {"anchor": BL.iso(A), "fold": Y, "note": note}
        if A in refs and refs[A]["fold"] == Y:
            ref = {"pm": refs[A]["pm"], "f10": refs[A]["f10"], "model_sha": refs[A]["model_sha"]}; row["ref"] = "A0_main P2 shard"; row["t_std"] = None
        else:
            pm = prep(G, P, i, A, Y, ws_s); out = f"{ROOT}/std/score.npz"
            if os.path.exists(out): os.remove(out)
            env = {**WENV, "HOME": f"{ROOT}/std", "WIDE_SHADOW_HOME": ws_s, "F10_SCORE_OUT": out, "_PY": PY}
            rc, lines, dt = BL.run_device(f"{HERE}/f10_scorer_3520d363.py", f"{ws_s}/fea171", env, f"{ROOT}/std/scorer.log")
            assert rc == 0, (BL.iso(A), lines[-4:])
            ref = read(out); assert ref["need"] and np.array_equal(ref["pm"], pm); row["ref"] = "standard path here"; row["t_std"] = dt
        pm = prep(G, P, i, A, Y, ws_f); out = f"{ROOT}/fast/score.npz"
        if os.path.exists(out): os.remove(out)
        env = {**WENV, "HOME": f"{ROOT}/fast", "WIDE_SHADOW_HOME": ws_f, "F10_SCORE_OUT": out}
        ex.stdin.write(json.dumps({"cwd": f"{ws_f}/fea171", "env": env}) + "\n"); ex.stdin.flush(); res = json.loads(ex.stdout.readline())
        row["t_fast"] = res["dt"]; row["fast_rc"] = res["rc"]
        if res["rc"] != 0:
            row["equal"] = False; row["fast_log"] = res["log"]; ok_all = False; rows.append(row); print(json.dumps(row), flush=True); continue
        got = read(out)
        eq = bool(got["need"] and np.array_equal(got["pm"], ref["pm"]) and np.array_equal(got["f10"], ref["f10"], equal_nan=True)
                  and fsha(got["f10"]) == fsha(ref["f10"]) and got["model_sha"] == ref["model_sha"])
        row.update({"equal": eq, "sha_fast": fsha(got["f10"])[:16], "sha_ref": fsha(ref["f10"])[:16], "n_scored": int(got["okf"].sum()), "n_members": int(len(pm))})
        if not eq:
            ok_all = False; d = np.abs(got["f10"] - ref["f10"]); row["max_abs"] = float(np.nanmax(d)) if np.isfinite(d).any() else None
        rows.append(row); print(json.dumps(row), flush=True)
    ex.stdin.close(); ex.wait()
    ts_ = [r["t_std"] for r in rows if r.get("t_std")]; tf_ = [r["t_fast"] for r in rows if r.get("t_fast") is not None]
    pair = [(r["t_std"], r["t_fast"]) for r in rows if r.get("t_std") and r.get("t_fast") is not None]
    doc = {"gate": "FAST-GATE", "comparison_type": "(3) packaging / scorer-path parity — not a return", "n_anchors": len(rows),
           "by_year": {str(y): sum(1 for r in rows if r["anchor"].startswith(str(y))) for y in range(2022, 2027)},
           "n_equal": sum(1 for r in rows if r.get("equal")), "VERDICT": "PASS" if (ok_all and len(rows) >= 50) else "FAIL",
           "t_std_median_s": float(np.median(ts_)) if ts_ else None, "t_fast_median_s": float(np.median(tf_)) if tf_ else None,
           "paired_speedup_median": float(np.median([a / b for a, b in pair])) if pair else None, "n_paired": len(pair), "rows": rows,
           "devices_sha256": {"fast_exec.py": BL.sha(f"{HERE}/fast_exec.py"), "f10_scorer_3520d363.py": BL.sha(f"{HERE}/f10_scorer_3520d363.py"), "self": BL.sha(os.path.abspath(__file__))},
           "a0_p2_shards_used_as_reference": True, "wall_s": round(time.time() - t_all, 1), "utc": BL.iso(time.time())}
    json.dump(doc, open(f"{R}/receipts/FAST_GATE.json", "w"), indent=1)
    print(json.dumps({k: doc[k] for k in ("n_anchors", "by_year", "n_equal", "VERDICT", "t_std_median_s", "t_fast_median_s", "paired_speedup_median", "wall_s")}), flush=True)
    shutil.rmtree(ROOT, ignore_errors=True)


if __name__ == "__main__":
    main()
