"""NEWS P2b: historical King/F10 feature build = producer code replayed anchor by anchor (news_hist_features).
Shard queue: 100 anchors per shard, claimed with O_EXCL lock files; each shard written atomically with its sha.
Usage: python news_p2_build.py worker <worker_id>      (run N of these)
       python news_p2_build.py merge                   (after all shards exist)
"""
import os, sys, json, time, hashlib, traceback
import numpy as np

# ---- D10 stage 2 section 5: consumer-side gate on fund_replay.npz (news2 fund_replay_guard.py) ----
import hashlib as _hl
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_gp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fund_replay_guard.py")
with open(_gp, "rb") as _f:
    assert _hl.sha256(_f.read()).hexdigest() == "9113d28a49b858df83c916c295ce0bc8286950b1d28b767dd07b61c9047ced25", "fund_replay_guard.py drifted from the pinned sha"
from fund_replay_guard import require_clean_fund_replay, fund_replay_status
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import news_hist_features as H

W = H.W
OUT = f"{W}/work/p2_shards"; SHARD = 100
CACHE_SRC_SHA = "08bb295745e6df84cb42574ef073dc54817a19ad7754bf6319cfcb30bd9baa75"
HOLES = "/workspace/axis_0919/x0918r/inputs/holefix2r_cells_x0918r.npz"; HOLES_SHA = "d524f819280384694cff6a36d684569d98ce18fa3ff04ceee562a54022afa612"
MASK = "/workspace/axis_0919/x0918r/masks/member_mask_tradable_AND_live_W24H_cachegrid.npz"; MASK_SHA = "f752d8ae3bf92f001fcb5d6f83a7e4ae286d9f11f7548c2e965305615aa9ae51"
DEVICES = ["news_p2_build.py", "news_hist_features.py"]


def load():
    ax = np.load(f"{W}/work/cache_x0918r_axes.npz"); ts = ax["ts"].astype(np.int64)
    syms = [str(s) for s in ax["symbols"]]; chn = [str(c) for c in ax["ch"]]
    D = np.load(f"{W}/work/cache_x0918r_data.npy", mmap_mode="r")
    h = np.load(HOLES); o = np.lexsort((h["col"], h["row"])); holes = (h["row"][o].astype(np.int64), h["col"][o].astype(np.int64))
    mk = np.load(MASK); A = mk["ts"].astype(np.int64); legal = mk["mask"]
    cfg = json.load(open(f"{W}/inputs/bundle_config.json"))
    crypto = np.load(f"{W}/receipts/P1_members_2025H2on.npz")["crypto"]
    # ★ NO allow= ARGUMENT HERE, deliberately. This device writes fund_now into the F10 features, i.e. it is the
    # path by which the fund_replay defect reached trained models. A measurement device may name a dirty
    # state and proceed; a PRODUCER may not. It refuses until the artefact is stamped clean.
    require_clean_fund_replay(f"{W}/work/fund_replay.npz")
    fr = np.load(f"{W}/work/fund_replay.npz")
    assert np.array_equal(fr["anchors"], A) and [str(s) for s in fr["symbols"]] == syms
    return dict(ts=ts, syms=syms, chn=chn, D=D, holes=holes, A=A, legal=legal, cfg=cfg, crypto=crypto,
                ema=fr["ema_acc"], lft=fr["last_ft"], lrt=fr["last_rate"], liv=fr["last_iv"])


def fund_dicts(C, i):
    syms = C["syms"]
    ema = {syms[j]: {"acc": float(C["ema"][i, j])} for j in np.flatnonzero(np.isfinite(C["ema"][i]))}
    led = {syms[j]: [[int(C["lft"][i, j]), float(C["lrt"][i, j]), float(C["liv"][i, j])]] for j in np.flatnonzero(C["lft"][i] >= 0)}
    return ema, led


def worker(wid):
    C = load(); n = len(C["A"]); nsh = (n + SHARD - 1) // SHARD
    os.makedirs(OUT, exist_ok=True)
    dev = {d: H.sha(os.path.join(os.path.dirname(os.path.abspath(__file__)), d)) for d in DEVICES}
    for k in range(nsh):
        lock = f"{OUT}/shard_{k:04d}.lock"; fn = f"{OUT}/shard_{k:04d}.npz"
        if os.path.exists(fn): continue
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY); os.write(fd, f"{wid} {os.getpid()}".encode()); os.close(fd)
        except FileExistsError:
            continue
        t0 = time.time(); rows = range(k * SHARD, min((k + 1) * SHARD, n))
        rec = {"anchor": [], "skip": [], "m": [], "X78": [], "X82": [], "X89": [], "fe_v": [], "fn_v": [], "iv_v": [], "qvm": [], "rev24": []}
        base_val = np.full((len(rows), len(C["syms"])), np.nan)
        for r_i, i in enumerate(rows):
            A = int(C["A"][i]); cand = C["legal"][i] & C["crypto"]
            ema, led = fund_dicts(C, i)
            try:
                r = H.replay_anchor(A, C["D"], C["ts"], C["syms"], C["chn"], cand, ema, led, C["cfg"]["params"], C["cfg"], f"{W}/work", holes=C["holes"], cols="members")
            except AssertionError as ex:          # combo_stage L102 btcv assertion: production would abort combo_stage at this anchor (no F10 book)
                if "btcv" not in str(ex): raise
                r = {"skip": [f"btcv_degenerate(combo_stage L102 assertion; cache rows < 2017): {ex}"]}
            rec["anchor"].append(A)
            if "skip" in r:
                rec["skip"].append(json.dumps(r["skip"])[:300]); rec["m"].append(np.zeros(0, np.int16))
                for key, shp, dt in (("X78", 78, np.float32), ("X82", 82, np.float16), ("X89", 89, np.float32)): rec[key].append(np.zeros((0, shp), dt))
                for key in ("fe_v", "fn_v", "iv_v", "qvm", "rev24"): rec[key].append(np.zeros(0))
                continue
            rec["skip"].append("")
            rec["m"].append(r["m"].astype(np.int16)); rec["X78"].append(r["king_X78"].astype(np.float32)); rec["X82"].append(r["X82"]); rec["X89"].append(r["X89"])
            for key in ("fe_v", "fn_v", "iv_v", "qvm", "rev24"): rec[key].append(np.asarray(r[key], np.float64))
            for s, v in r["base_vals"].items(): base_val[r_i, C["syms"].index(s)] = v
        cnt = np.array([len(x) for x in rec["m"]], np.int64)
        tmp = fn + ".tmp.npz"
        np.savez(tmp, anchor=np.array(rec["anchor"], np.int64), skip=np.array(rec["skip"]), count=cnt,
                 m=np.concatenate(rec["m"]), X78=np.concatenate(rec["X78"]), X82=np.concatenate(rec["X82"]), X89=np.concatenate(rec["X89"]),
                 **{key: np.concatenate(rec[key]) for key in ("fe_v", "fn_v", "iv_v", "qvm", "rev24")}, base_val=base_val)
        os.replace(tmp, fn)
        json.dump({"shard": k, "worker": wid, "pid": os.getpid(), "anchors": [int(rec["anchor"][0]), int(rec["anchor"][-1])], "n": len(rows),
                   "skipped": int(sum(1 for s in rec["skip"] if s)), "seconds": round(time.time() - t0, 1), "sha256": H.sha(fn), "devices": dev,
                   "numpy": np.__version__, "npy_disable": os.environ.get("NPY_DISABLE_CPU_FEATURES")}, open(fn + ".json", "w"))
        print(time.strftime("%H:%M:%S", time.gmtime()), "shard", k, "done", round(time.time() - t0, 1), flush=True)


def merge():
    C = load(); n = len(C["A"]); nsh = (n + SHARD - 1) // SHARD
    parts = []; recs = []
    for k in range(nsh):
        fn = f"{OUT}/shard_{k:04d}.npz"; rj = json.load(open(fn + ".json"))
        assert H.sha(fn) == rj["sha256"], ("shard sha", k); recs.append(rj); parts.append(np.load(fn))
    anchor = np.concatenate([p["anchor"] for p in parts]); assert np.array_equal(anchor, C["A"])
    count = np.concatenate([p["count"] for p in parts]); off = np.concatenate([[0], np.cumsum(count)])
    out = f"{W}/work/NEWS_FEATURES.npz"
    arr = {key: np.concatenate([p[key] for p in parts]) for key in ("m", "X78", "X82", "X89", "fe_v", "fn_v", "iv_v", "qvm", "rev24")}
    assert len(arr["m"]) == off[-1] and np.isfinite(arr["X78"]).all() and np.isfinite(arr["X82"].astype(np.float32)).all() and np.isfinite(arr["X89"]).all()
    np.savez(out + ".tmp.npz", anchors=anchor, count=count, off=off, skip=np.concatenate([p["skip"] for p in parts]),
             base_val=np.concatenate([p["base_val"] for p in parts]), symbols=np.array(C["syms"]), **arr)
    os.replace(out + ".tmp.npz", out)
    rr = {"status": "P2_FEATURES_BUILT", "output": out, "sha256": H.sha(out), "anchors": int(n), "pairs": int(off[-1]),
          "skipped_anchors": int(sum(1 for s in np.concatenate([p["skip"] for p in parts]) if s)),
          "devices_by_shard_distinct": sorted({json.dumps(r["devices"], sort_keys=True) for r in recs}), "numpy": sorted({r["numpy"] for r in recs}), "npy_disable": sorted({str(r["npy_disable"]) for r in recs}),
          "worker_seconds_total": round(sum(r["seconds"] for r in recs), 1),
          "producer_sources": {H.SHADOW_SRC: H.SHADOW_SHA, H.COMBO_SRC: H.COMBO_SHA, H.DLW_SRC: H.DLW_SHA, H.F8_SRC: H.F8_SHA},
          "inputs": {"cache_npz_sha": CACHE_SRC_SHA, "cache_npy": f"{W}/work/cache_x0918r_data.npy", HOLES: HOLES_SHA, MASK: MASK_SHA,
                     "fund_replay": H.sha(f"{W}/work/fund_replay.npz"), "crypto_from": f"{W}/receipts/P1_members_2025H2on.npz"},
          "shards": [{k: r[k] for k in ("shard", "anchors", "skipped", "seconds", "sha256")} for r in recs]}
    json.dump(rr, open(f"{W}/receipts/P2B_FEATURES.json", "w"), indent=1)
    print("MERGED", json.dumps({k: rr[k] for k in ("anchors", "pairs", "skipped_anchors", "worker_seconds_total")}), flush=True)


if __name__ == "__main__":
    if sys.argv[1] == "worker": worker(int(sys.argv[2]))
    elif sys.argv[1] == "merge": merge()
