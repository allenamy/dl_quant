"""FX-TRAIN fact-table device (TRN-02), READ-ONLY: for each (cache, raw_patch) pair, the set of clip candidates
{(row, col): isfinite(ch0) and ch0 == +-float16(0.3)} versus the patch's (row, col) pairs, plus addressing checks
(CTS[row] == ts, symbols[col] == symbol, ch0[row, col] bitwise == clip16). Writes one JSON receipt; never writes a cache or a patch.
usage: python fx_trn02_measure_patch_coverage.py <out.json> <label>=<cache.npz>,<patch.npz> [...]"""
import hashlib, json, os, sys, time
import numpy as np
out = sys.argv[1]; res = {"device": os.path.abspath(__file__), "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "pairs": {}}
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""): h.update(ch)
    return h.hexdigest()
res["self_sha256"] = sha(os.path.abspath(__file__))
C16 = np.float16(0.3)
for arg in sys.argv[2:]:
    lab, rest = arg.split("=", 1); cp, pp = rest.split(",", 1); t0 = time.time()
    Z = np.load(cp, allow_pickle=True); CTS = Z["ts"].astype(np.int64); syms = [str(s) for s in Z["symbols"]]
    ch0 = Z["data"][:, :, 0].copy(); TT, NW = ch0.shape
    cand = np.isfinite(ch0) & ((ch0 == C16) | (ch0 == -C16)); cr, cc = np.nonzero(cand)
    P = np.load(pp, allow_pickle=True); pr = P["row"].astype(np.int64); pc = P["col"].astype(np.int64)
    inb = (pr >= 0) & (pr < TT) & (pc >= 0) & (pc < NW)
    ck = set(zip(cr.tolist(), cc.tolist())); pk = set(zip(pr.tolist(), pc.tolist()))
    uncovered = sorted(ck - pk); not_candidate = sorted(pk - ck)
    ts_ok = bool(inb.all() and np.array_equal(CTS[pr[inb]], P["ts"].astype(np.int64)[inb]))
    sym_ok = bool(inb.all() and all(syms[c] == str(s) for c, s in zip(pc[inb], P["symbol"][inb])))
    clip_ok = bool(inb.all() and np.array_equal(ch0[pr[inb], pc[inb]].view(np.uint16), P["clip16"].astype(np.float16)[inb].view(np.uint16)))
    def U(t): return time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(t)))
    res["pairs"][lab] = {"cache": cp, "cache_bytes": os.path.getsize(cp), "patch": pp, "patch_sha256": sha(pp), "TT": int(TT), "NW": int(NW),
        "cache_end_utc": U(CTS[-1]), "n_candidates": int(len(cr)), "n_patch": int(len(pr)), "n_patch_in_bounds": int(inb.sum()),
        "n_candidates_not_in_patch": len(uncovered), "n_patch_not_candidate": len(not_candidate),
        "candidates_not_in_patch": [{"row": r, "col": c, "ts": U(CTS[r]), "symbol": syms[c], "ch0": float(ch0[r, c])} for r, c in uncovered[:200]],
        "patch_not_candidate": [{"row": r, "col": c} for r, c in not_candidate[:50]],
        "patch_ts_addresses_rows": ts_ok, "patch_symbol_addresses_cols": sym_ok, "patch_clip16_bitwise_equals_cache": clip_ok, "wall_s": round(time.time() - t0, 1)}
    print(lab, json.dumps({k: v for k, v in res["pairs"][lab].items() if k not in ("candidates_not_in_patch", "patch_not_candidate")}), flush=True)
    print(lab, "candidates_not_in_patch (first 20):", res["pairs"][lab]["candidates_not_in_patch"][:20], flush=True)
    del Z, ch0, cand
res["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
json.dump(res, open(out, "w"), indent=1); print("FX_TRN02_MEASURE_DONE", out, flush=True)
