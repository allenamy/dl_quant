#!/usr/bin/env python3
"""Object B pass P2 — F10 scores for every producer member at every anchor (PREREG §3 S6), with the production 171 pipeline:
the scorer device f10_scorer_3520d363.py = production combo_stage.py lines 1..176 verbatim (+ WS from env) + a dump epilogue, run in a clean
sandbox per anchor (mini/ emptied ⇒ need=True). Inputs per anchor are exactly what the scorer reads from aux.json (prev_rec; ema acc; last
funding rate) — recorded by pass P1 — plus the 40-day live-equivalent cache tail and the F10 fold chosen by the F10 rule (b_lib.f10_fold_for).
Workers are forked from the launcher (cache shared copy-on-write); each keeps a resumable shard.  Same scorer code as GATE F."""
import os, sys, json, time, shutil, glob
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import b_lib as BL
import b_driver as BD


def load_p1(p1_prefix):
    Z = np.load(f"{p1_prefix}.vec.npz"); P = {k: Z[k] for k in Z.files}
    return P


def p1_inputs(P, i, syms, A):
    pm = P["pm"][P["pm_off"][i]:P["pm_off"][i + 1]].astype(np.int64)
    lz = P["legz"][P["legz_off"][i]:P["legz_off"][i + 1]].reshape(3, len(pm))
    sm = P["sm"][P["sm_off"][i]:P["sm_off"][i + 1]]; smi = P["sm_idx"][P["sm_idx_off"][i]:P["sm_idx_off"][i + 1]].astype(np.int64)
    prev_rec = {"anchor_ts": int(A), "members": [int(x) for x in pm], "legz": {l: [float(x) for x in lz[k]] for k, l in enumerate(("king", "rev24", "fund"))},
                "sm": [float(x) for x in sm], "sm_idx": [int(x) for x in smi]}
    fe = P["fe"][i]; fn = P["fn"][i]
    ema = {syms[j]: {"acc": float(fe[j])} for j in np.where(np.isfinite(fe))[0]}
    led = {syms[j]: [[int(A), float(fn[j]), 8.0]] for j in np.where(np.isfinite(fn))[0]}
    return pm, {"prev_close": {}, "H": {}, "last_anchor": int(A), "ema": ema, "ledger_tail": led, "base_syms": [], "prev_rec": prev_rec}


def same_inputs(P, i, Q, k):
    """every scorer input recorded by P1 for P's anchor i equals Q's anchor k bitwise (members, leg z, seat vector, fund ema acc, last rate)."""
    for key in ("pm", "legz", "sm", "sm_idx"):
        a = P[key][P[key + "_off"][i]:P[key + "_off"][i + 1]]; b = Q[key][Q[key + "_off"][k]:Q[key + "_off"][k + 1]]
        if a.dtype != b.dtype or not np.array_equal(a, b): return False
    return bool(np.array_equal(P["fe"][i], Q["fe"][k], equal_nan=True) and np.array_equal(P["fn"][i], Q["fn"][k], equal_nan=True))


def jobs_from_p1(G, P):
    jobs = []
    for i, A in enumerate(P["anchor"]):
        Y = BL.f10_fold_for(int(A), G.f10)
        if Y is not None: jobs.append((int(A), i, int(Y)))
    return jobs


def save_shard(path, res):
    if not res: return
    A = np.array([r[0] for r in res], np.int64); Y = np.array([r[1] for r in res], np.int64)
    lens = [len(r[2]) for r in res]; off = np.concatenate([[0], np.cumsum(lens)]).astype(np.int64)
    pm = np.concatenate([r[2] for r in res]).astype(np.int16); f10 = np.concatenate([r[3] for r in res]).astype(np.float64)
    ms = np.array([r[4] for r in res]); sec = np.array([r[5] for r in res]); okf = np.array([r[6] for r in res], np.int64)
    tmp = path + ".tmp.npz"; np.savez(tmp, anchor=A, fold=Y, pm_off=off, pm=pm, f10=f10, model_sha=ms, s=sec, okf=okf); os.replace(tmp, path)


def load_shard(path):
    if not os.path.exists(path): return []
    z = np.load(path); out = []
    for k in range(len(z["anchor"])):
        a, b = z["pm_off"][k], z["pm_off"][k + 1]
        out.append((int(z["anchor"][k]), int(z["fold"][k]), z["pm"][a:b].astype(np.int64), z["f10"][a:b], str(z["model_sha"][k]), float(z["s"][k]), int(z["okf"][k])))
    return out


def worker(w, jobs, G, P, shard_path, log_path):
    fea_src, reader_src, man = BD.stage_sources()
    # sandbox per run tag (runs of different tags may score at the same time; the path is not an input of the score — gate F sandboxes differ too)
    tag = os.path.basename(os.path.dirname(os.path.dirname(os.path.abspath(shard_path))))
    root = f"/dev/shm/object_b_p2/{tag}/w{w}"; shutil.rmtree(root, ignore_errors=True)
    ws = BL.make_sandbox(root, fea_src, BD.SRC["bundle_config"][0], BD.VENV_PY)
    # resumable across a change of worker count: skip every anchor already scored in ANY shard of this run (own results kept in own shard)
    res = load_shard(shard_path); done = {r[0] for r in res}; cur_model = None
    for p_ in glob.glob(os.path.join(os.path.dirname(os.path.abspath(shard_path)), "shard_*.npz")):
        if os.path.abspath(p_) != os.path.abspath(shard_path) and not p_.endswith(".tmp.npz"): done |= {r[0] for r in load_shard(p_)}
    lf = open(log_path, "a"); t_start = time.time(); n_new = 0
    ex = None
    if os.environ.get("OBJB_FAST") == "1":   # FAST-GATE PASS required (b_launch asserts it): one warm executor per worker, same device text
        import subprocess as _sp
        ex = _sp.Popen([BD.VENV_PY, "-B", f"{HERE}/fast_exec.py"], stdin=_sp.PIPE, stdout=_sp.PIPE, text=True, bufsize=1,
                       env={"PATH": "/usr/bin:/bin", "HOME": root, "LC_CTYPE": "C.UTF-8", "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"})
        assert json.loads(ex.stdout.readline())["ready"]
    for (A, i, Y) in jobs:
        if A in done: continue
        BL.clear_mini(f"{ws}/fea171")
        for f in ("rolling.npz", "aux.json", "leg_returns_live.json"):
            if os.path.exists(f"{ws}/state/{f}"): os.remove(f"{ws}/state/{f}")
        if cur_model != Y:
            shutil.copy2(G.f10[Y]["np"], f"{ws}/fea171/f10_live_s42_np.npz"); cur_model = Y
        live = G.live_names(A); lmask = np.zeros(829, bool); lmask[[G.col[s] for s in live]] = True
        ts, cd = G.cache_tail(A, lmask); np.savez(f"{ws}/state/rolling.npz", ts=ts, data=cd); del cd
        pm, aux = p1_inputs(P, i, G.SYMS, A)
        json.dump(aux, open(f"{ws}/state/aux.json", "w")); json.dump({"king": [], "rev24": [], "fund": []}, open(f"{ws}/state/leg_returns_live.json", "w"))
        out = f"{root}/score.npz"
        if os.path.exists(out): os.remove(out)
        env = {"PATH": "/usr/bin:/bin", "HOME": root, "LC_CTYPE": "C.UTF-8", "WIDE_SHADOW_HOME": ws, "F10_SCORE_OUT": out,
               "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "_PY": BD.VENV_PY}
        if ex is None:
            rc, lines, dt = BL.run_device(f"{HERE}/f10_scorer_3520d363.py", f"{ws}/fea171", env, f"{root}/scorer.log")
        else:
            ex.stdin.write(json.dumps({"cwd": f"{ws}/fea171", "env": {k: v for k, v in env.items() if not k.startswith("_")}}) + "\n"); ex.stdin.flush()
            rr = json.loads(ex.stdout.readline()); rc, lines, dt = rr["rc"], rr["log"], rr["dt"]
        if rc != 0:
            lf.write(json.dumps({"anchor": A, "rc": rc, "tail": lines[-6:]}) + "\n"); lf.flush()
            save_shard(shard_path, res); raise RuntimeError(f"scorer rc={rc} at {BL.iso(A)}: {lines[-4:]}")
        z = np.load(out)
        assert int(z["anchor"]) == A and bool(z["need_ran"]), ("scorer did not run the pipeline for", A)
        assert np.array_equal(z["pm"].astype(np.int64), pm), ("scorer member set != P1 member set", A)
        assert str(z["model_sha"]) == G.f10[Y]["sha256"], ("scorer used a different model", A)
        res.append((A, Y, pm, z["f10_pm"].astype(np.float64), str(z["model_sha"]), dt, int(z["okf"].sum()))); n_new += 1
        if n_new % 20 == 0:
            save_shard(shard_path, res)
            lf.write(json.dumps({"w": w, "done": len(res), "of": len(jobs), "last": BL.iso(A), "s_last": dt, "elapsed_s": round(time.time() - t_start, 1)}) + "\n"); lf.flush()
    if ex is not None: ex.stdin.close(); ex.wait()
    save_shard(shard_path, res); lf.write(json.dumps({"w": w, "DONE": len(res), "elapsed_s": round(time.time() - t_start, 1), "fast": ex is not None}) + "\n"); lf.close()
    shutil.rmtree(root, ignore_errors=True)


def merge(shards, out_path, jobs):
    allr = {}; n_dup = 0; dup_unequal = []
    for p in shards:
        for r in load_shard(p):
            if r[0] in allr:   # the same anchor scored twice (worker-count change): the two scores must be identical
                n_dup += 1; q = allr[r[0]]
                if not (q[1] == r[1] and q[4] == r[4] and np.array_equal(q[2], r[2]) and np.array_equal(q[3], r[3], equal_nan=True)): dup_unequal.append(BL.iso(r[0]))
            allr[r[0]] = r
    assert not dup_unequal, ("an anchor scored twice with different results", dup_unequal[:5])
    want = {j[0] for j in jobs}; missing = sorted(want - set(allr))
    res = [allr[a] for a in sorted(allr)]
    save_shard(out_path, res)
    return {"n_scored_anchors": len(res), "n_jobs": len(want), "n_shards": len(shards), "n_anchor_scored_twice_identical": n_dup, "missing": [BL.iso(a) for a in missing[:20]], "n_missing": len(missing),
            "okf_min_median_max": [int(min(r[6] for r in res)), float(np.median([r[6] for r in res])), int(max(r[6] for r in res))] if res else None,
            "seconds_per_anchor_median": float(np.median([r[5] for r in res])) if res else None}


def as_dict(path):
    return {r[0]: {"pm": r[2], "f10": r[3], "fold": r[1], "model_sha": r[4]} for r in load_shard(path)}
