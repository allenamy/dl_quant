"""NC training-feature build on pod2 (DESIGN §A9): pass 1 (King block, every anchor) -> member history -> pass 2 (F10 mini pipeline,
anchors with >= 50 members) -> NC_FEATURES.npz in the NEWS_FEATURES format (+ extras). Sharded by worker; every shard records the
device and tree shas; a shard is written atomically and re-used only if its receipt matches the current devices.
usage: python nc_p2_build.py p1 <shard> <nshard> | merge1 | p2 <shard> <nshard> | merge2
env:  NC_W (root), NC_TREE (patched tree), NC_WS (dir holding venv -> the replay interpreter), NC_CFG (bundle config.json)"""
import os, sys, json, time, hashlib, traceback
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import nc_hist_features as H

W = os.environ.get("NC_W", "/dev/shm/nc_2026-09-23"); TREE = os.environ.get("NC_TREE", f"{W}/tree"); CFG = os.environ.get("NC_CFG", f"{W}/inputs/bundle_config.json")
OUT = f"{W}/work"


def sha(p): return H.sha(p)


def devices():
    return {os.path.basename(p): sha(p) for p in (os.path.abspath(__file__), H.__file__)}


def shard_of(items, k, n):
    return [x for i, x in enumerate(items) if i % n == k]


def p1(k, n):
    H.set_tree(TREE); cfg = json.load(open(CFG)); P = cfg["params"]
    I = H.Inputs(); kb = H._king_block()
    todo = shard_of(list(I.anchors), k, n); t0 = time.time()
    rec = {"anchor": [], "mcount": [], "m_all": [], "king": [], "skip": {}}
    K = {"m": [], "X78": [], "fe_v": [], "fn_v": [], "iv_v": [], "qvm": [], "rev24": [], "n_legal": [], "n_cand": []}
    base_i, base_v, base_n = [], [], []
    for A in todo:
        try:
            r = H.pass1_anchor(I, int(A), P, cfg, kb)
        except AssertionError as e:
            if "btcv" in str(e): rec["skip"][int(A)] = str(e)[:200]; continue
            raise
        m_all = r["members"] if r["members"] is not None else np.zeros(0, np.int64)
        rec["anchor"].append(int(A)); rec["mcount"].append(len(m_all)); rec["m_all"].append(m_all.astype(np.int16))
        has = "m" in r
        rec["king"].append(has)
        if has:
            for key in ("m", "fe_v", "fn_v", "iv_v", "qvm", "rev24"): K[key].append(np.asarray(r[key]))
            K["X78"].append(np.asarray(r["king_X78"], np.float32)); K["n_legal"].append(r["n_legal"]); K["n_cand"].append(r["n_cand"])
            bi = [I.syms.index(s) for s in r["base_vals"]]; base_i.append(np.array(bi, np.int16)); base_v.append(np.array(list(r["base_vals"].values()), np.float64)); base_n.append(len(bi))
        else:
            rec["skip"].setdefault(int(A), "; ".join(json.dumps(x)[:120] for x in r["skip"]) or "no King features")
    o = f"{OUT}/p1_shards/p1_{k:03d}_{n:03d}.npz"; os.makedirs(os.path.dirname(o), exist_ok=True)
    kc = np.array([len(x) for x in K["m"]], np.int64)
    np.savez(o + ".tmp.npz", anchor=np.array(rec["anchor"], np.int64), mcount=np.array(rec["mcount"], np.int64),
             m_all=np.concatenate(rec["m_all"]) if rec["m_all"] else np.zeros(0, np.int16), king=np.array(rec["king"], bool), kcount=kc,
             m=np.concatenate(K["m"]).astype(np.int16) if K["m"] else np.zeros(0, np.int16),
             X78=np.concatenate(K["X78"]) if K["X78"] else np.zeros((0, 78), np.float32),
             **{key: (np.concatenate(K[key]) if K[key] else np.zeros(0)) for key in ("fe_v", "fn_v", "iv_v", "qvm", "rev24")},
             n_legal=np.array(K["n_legal"], np.int64), n_cand=np.array(K["n_cand"], np.int64),
             base_n=np.array(base_n, np.int64), base_i=np.concatenate(base_i) if base_i else np.zeros(0, np.int16),
             base_v=np.concatenate(base_v) if base_v else np.zeros(0))
    os.replace(o + ".tmp.npz", o)
    json.dump({"shard": k, "nshard": n, "devices": devices(), "tree_receipt_sha256": sha(f"{TREE}/PATCH_RECEIPT.json"), "king_span": H.KING_SPAN,
               "anchors": len(rec["anchor"]), "king": int(sum(rec["king"])), "skip": rec["skip"], "seconds": round(time.time() - t0, 1),
               "numpy": np.__version__, "npy_disable": os.environ.get("NPY_DISABLE_CPU_FEATURES"), "sha256": sha(o)}, open(o + ".json", "w"), indent=1)
    print("P1_SHARD_DONE", k, len(rec["anchor"]), int(sum(rec["king"])), round(time.time() - t0, 1), flush=True)


def merge1():
    """Concatenate the pass-1 shards in anchor order WITHOUT per-anchor python objects (the first version pickled an object array of
    10k dicts and was OOM-killed): p1_merged.npz (flat arrays + offsets) and members_hist_all.npz."""
    import glob
    fs = sorted(glob.glob(f"{OUT}/p1_shards/p1_*.npz")); assert fs
    parts = []
    for f in fs:
        j = json.load(open(f + ".json")); assert j["sha256"] == sha(f)
        with np.load(f) as z: parts.append({k: z[k] for k in z.files})     # materialise once (NpzFile re-reads on every access)
    A = np.concatenate([z["anchor"] for z in parts]); order = np.argsort(A, kind="stable"); A = A[order]
    assert len(np.unique(A)) == len(A)
    # per-anchor slices in every shard, then gathered in anchor order
    def gather(count_key, key, flag=None):
        chunks = []
        for z in parts:
            cnt = z[count_key]; off = np.concatenate([[0], np.cumsum(cnt)])
            if flag is None:
                chunks.append([z[key][off[i]:off[i + 1]] for i in range(len(cnt))])
            else:
                fl = z[flag]; ki = np.cumsum(fl) - 1
                chunks.append([(z[key][off[ki[i]]:off[ki[i] + 1]] if fl[i] else None) for i in range(len(fl))])
        flat = [x for c in chunks for x in c]
        return [flat[i] for i in order]
    m_all = gather("mcount", "m_all")
    king = np.concatenate([z["king"] for z in parts])[order]
    np.savez(f"{OUT}/members_hist_all.npz", anchors=A, off=np.concatenate([[0], np.cumsum([len(x) for x in m_all])]).astype(np.int64),
             idx=np.concatenate(m_all).astype(np.int16))
    out = {"anchors": A, "king": king}
    for key in ("m", "X78", "fe_v", "fn_v", "iv_v", "qvm", "rev24"):
        g = gather("kcount", key, flag="king"); gk = [x for x in g if x is not None]
        out[key] = np.concatenate(gk); out["kcount"] = np.array([len(x) for x in gk], np.int64)
    gb_i = gather("base_n", "base_i", flag="king"); gb_v = gather("base_n", "base_v", flag="king")
    out["base_n"] = np.array([len(x) for x in gb_i if x is not None], np.int64)
    out["base_i"] = np.concatenate([x for x in gb_i if x is not None]); out["base_v"] = np.concatenate([x for x in gb_v if x is not None])
    for key in ("n_legal", "n_cand"):
        v = []
        for z in parts:
            fl = z["king"]; ki = np.cumsum(fl) - 1; v.append([int(z[key][ki[i]]) if fl[i] else -1 for i in range(len(fl))])
        out[key] = np.array([x for c in v for x in c], np.int64)[order]
    np.savez(f"{OUT}/p1_merged.npz", **out)
    print("MERGE1_DONE anchors", len(A), "with King features", int(king.sum()), "pairs", int(out["kcount"].sum()), flush=True)


def _p1_view():
    """p1_merged.npz as {anchor: dict} for the anchors with King features (arrays are views, not copies)."""
    with np.load(f"{OUT}/p1_merged.npz") as zz: z = {k: zz[k] for k in zz.files}
    A = z["anchors"]; king = z["king"]; kc = z["kcount"]; off = np.concatenate([[0], np.cumsum(kc)]); bn = z["base_n"]; boff = np.concatenate([[0], np.cumsum(bn)])
    rows = {}; ki = 0
    for i, a in enumerate(A):
        if not king[i]: continue
        s = slice(off[ki], off[ki + 1])
        rows[int(a)] = {"A": int(a), "king": True, "m": z["m"][s].astype(np.int64), "X78": z["X78"][s],
                        **{kk: z[kk][s] for kk in ("fe_v", "fn_v", "iv_v", "qvm", "rev24")},
                        "base_i": z["base_i"][boff[ki]:boff[ki + 1]].astype(np.int64), "base_v": z["base_v"][boff[ki]:boff[ki + 1]]}
        ki += 1
    return rows


def p2(k, n):
    H.set_tree(TREE); I = H.Inputs(); code = H._mini_block(); cf = H._combo_funcs()
    king_anchors = sorted(_p1_view())
    mh = np.load(f"{OUT}/members_hist_all.npz"); MH = {int(a): mh["idx"][mh["off"][i]:mh["off"][i + 1]].astype(np.int64) for i, a in enumerate(mh["anchors"])}
    todo = shard_of(king_anchors, k, n); t0 = time.time()
    out = {"anchor": [], "X82": [], "X89": [], "btcv": [], "mh_missing": [], "n_keep": []}; fails = {}
    work = f"{W}/scratch/p2_{k:03d}"; os.makedirs(work, exist_ok=True)
    for A in todo:
        try:
            r = H.pass2_anchor(I, int(A), MH, work, code, cf)
        except AssertionError as e:
            if "btcv" in str(e): fails[int(A)] = str(e)[:200]; continue
            raise
        out["anchor"].append(int(A)); out["X82"].append(np.asarray(r["X82"])); out["X89"].append(np.asarray(r["X89"], np.float32))
        out["btcv"].append(r["btcv_anchor"]); out["mh_missing"].append(r["mh_missing"]); out["n_keep"].append(r["n_keep"])
    o = f"{OUT}/p2_shards/p2_{k:03d}_{n:03d}.npz"; os.makedirs(os.path.dirname(o), exist_ok=True)
    cnt = np.array([len(x) for x in out["X82"]], np.int64)
    np.savez(o + ".tmp.npz", anchor=np.array(out["anchor"], np.int64), count=cnt,
             X82=np.concatenate(out["X82"]) if out["X82"] else np.zeros((0, 82), np.float32),
             X89=np.concatenate(out["X89"]) if out["X89"] else np.zeros((0, 89), np.float32),
             btcv=np.array(out["btcv"]), mh_missing=np.array(out["mh_missing"]), n_keep=np.array(out["n_keep"]))
    os.replace(o + ".tmp.npz", o)
    json.dump({"shard": k, "nshard": n, "devices": devices(), "tree_receipt_sha256": sha(f"{TREE}/PATCH_RECEIPT.json"), "mini_span": H.MINI_SPAN,
               "anchors": len(out["anchor"]), "fails": fails, "seconds": round(time.time() - t0, 1), "numpy": np.__version__,
               "npy_disable": os.environ.get("NPY_DISABLE_CPU_FEATURES"), "sha256": sha(o)}, open(o + ".json", "w"), indent=1)
    print("P2_SHARD_DONE", k, len(out["anchor"]), round(time.time() - t0, 1), flush=True)


def merge2():
    import glob
    H.set_tree(TREE)
    rows = _p1_view()
    p2r = {}
    for f in sorted(glob.glob(f"{OUT}/p2_shards/p2_*.npz")):
        j = json.load(open(f + ".json")); assert j["sha256"] == sha(f)
        # read every member ONCE: an NpzFile re-reads (and re-allocates) the whole array on each key access, and a slice keeps its
        # base alive — the first merge2 (2026-09-23 22:22Z) pinned one full shard array per anchor and was OOM-killed (oom_kill 8->9)
        with np.load(f) as zz:
            z = {k: zz[k] for k in ("anchor", "count", "X82", "X89", "btcv", "mh_missing")}
        off = np.concatenate([[0], np.cumsum(z["count"])])
        for i, A in enumerate(z["anchor"]):
            p2r[int(A)] = (z["X82"][off[i]:off[i + 1]], z["X89"][off[i]:off[i + 1]], float(z["btcv"][i]), int(z["mh_missing"][i]))
    I = H.Inputs(); A_all = I.anchors
    anc, cnt, skip = [], [], []
    arr = {k: [] for k in ("m", "X78", "X82", "X89", "fe_v", "fn_v", "iv_v", "qvm", "rev24")}
    base_val = np.full((len(A_all), I.NW), np.nan); mh_missing = np.full(len(A_all), -1); btcv = np.full(len(A_all), np.nan)
    for i, A in enumerate(A_all):
        A = int(A); r = rows.get(A); anc.append(A)
        if r is None or not r["king"] or A not in p2r:
            cnt.append(0); skip.append(True)
            for key, w in (("X78", 78), ("X82", 82), ("X89", 89)): arr[key].append(np.zeros((0, w), np.float32))
            for key in ("m", "fe_v", "fn_v", "iv_v", "qvm", "rev24"): arr[key].append(np.zeros(0))
            continue
        x82, x89, bv, mhm = p2r[A]
        assert len(x82) == len(r["m"])
        cnt.append(len(r["m"])); skip.append(False)
        arr["m"].append(r["m"]); arr["X78"].append(r["X78"]); arr["X82"].append(x82); arr["X89"].append(x89)
        for key in ("fe_v", "fn_v", "iv_v", "qvm", "rev24"): arr[key].append(r[key])
        base_val[i, r["base_i"]] = r["base_v"]; mh_missing[i] = mhm; btcv[i] = bv
    cnt = np.array(cnt, np.int64); off = np.concatenate([[0], np.cumsum(cnt)])
    cat = {k: np.concatenate(v) for k, v in arr.items()}
    cat["m"] = cat["m"].astype(np.int16); cat["X82"] = cat["X82"].astype(np.float32)
    assert np.isfinite(cat["X78"]).all() and np.isfinite(cat["X82"]).all() and np.isfinite(cat["X89"]).all()
    o = f"{OUT}/NC_FEATURES.npz"
    np.savez(o + ".tmp.npz", anchors=np.array(anc, np.int64), count=cnt, off=off, skip=np.array(skip), base_val=base_val, symbols=np.array(I.syms),
             mh_missing=mh_missing, btcv=btcv, **cat)
    os.replace(o + ".tmp.npz", o)
    rec = {"status": "NC_FEATURES_BUILT", "output": o, "sha256": sha(o), "anchors": len(anc), "pairs": int(off[-1]),
           "anchors_with_features": int((~np.array(skip)).sum()), "tree_patch_receipt_sha256": sha(f"{TREE}/PATCH_RECEIPT.json"),
           "tree_outputs": H.REC["outputs"] if H.REC else None, "devices": devices(), "members_hist": {"path": f"{OUT}/members_hist_all.npz", "sha256": sha(f"{OUT}/members_hist_all.npz")},
           "mh_missing_max": int(mh_missing.max()), "note": "X82 stored float32 (D4); NEWS_FEATURES key layout"}
    json.dump(rec, open(f"{W}/receipts/NC_FEATURES.json", "w"), indent=1)
    print("MERGE2_DONE", json.dumps({k: rec[k] for k in ("sha256", "anchors", "pairs", "anchors_with_features", "mh_missing_max")}), flush=True)


if __name__ == "__main__":
    cmd = sys.argv[1]
    {"p1": lambda: p1(int(sys.argv[2]), int(sys.argv[3])), "merge1": merge1, "p2": lambda: p2(int(sys.argv[2]), int(sys.argv[3])), "merge2": merge2}[cmd]()
