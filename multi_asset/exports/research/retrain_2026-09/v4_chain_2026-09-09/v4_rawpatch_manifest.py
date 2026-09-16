"""Write the coverage MANIFEST of an existing raw-return patch (FX-TRAIN TRN-02, 2026-09-13; rules in v4_rawpatch_lib.py). NEVER writes or edits a patch.

For the given cache and patch, every clip candidate {isfinite(ch0) and ch0 == +-float16(0.3)} is classified from 5m kline SOURCE files:
  kept            a patch row (its close pair is recorded; raw32_rederived_bitwise says whether float32(close_t/close_prev - 1) reproduces raw32)
  not_clipped     a candidate NOT in the patch whose true return has |rv| <= 0.3 (it only rounds to the clip value in float16)
  clipped_missing a candidate NOT in the patch with |rv| > 0.3 — the E-0908-B omission; recorded, never repaired here (the gate FAILs on it)
  unresolved      a candidate (or patch row) whose close pair is not in the sources — recorded (the gate FAILs on it)
Sources (KLINE_SOURCES, comma list of directories, searched in order): monthly CSV <dir>/<SYM>_<YYYY-MM>.csv (make_raw_patch.py layout: month of the close
time, then the previous month) or daily zips <dir>/<SYM>/<YYYY-MM-DD>.zip (r6 layout: date of the bar's open time, then of its close time).
env (all REQUIRED, no defaults): CACHE, RAW_PATCH, KLINE_SOURCES, MANIFEST_OUT (refused if it already exists — a manifest is never overwritten).
Exit 0 when the manifest is written (the classification is data; v4_gate_rawpatch.py / pod_dlw_targets_raw.py decide PASS), 2 on refusal."""
import json, os, sys, time
import numpy as np
_REQ = ("CACHE", "RAW_PATCH", "KLINE_SOURCES", "MANIFEST_OUT")
_miss = [k for k in _REQ if not os.environ.get(k)]
if _miss:
    print(f"RAWPATCH_MANIFEST_REFUSED missing env {_miss} (no defaults)", flush=True); sys.exit(2)
CACHE, PATCH, OUTP = os.environ["CACHE"], os.environ["RAW_PATCH"], os.environ["MANIFEST_OUT"]
SRCS = [s for s in os.environ["KLINE_SOURCES"].split(",") if s]
if os.path.exists(OUTP):
    print(f"RAWPATCH_MANIFEST_REFUSED {OUTP} exists (a manifest is never overwritten)", flush=True); sys.exit(2)
for p in (CACHE, PATCH) + tuple(SRCS):
    if not os.path.exists(p):
        print(f"RAWPATCH_MANIFEST_REFUSED input missing: {p}", flush=True); sys.exit(2)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v4_rawpatch_lib as L
t0 = time.time()
Z = np.load(CACHE, allow_pickle=True); CTS = Z["ts"].astype(np.int64); syms = [str(s) for s in Z["symbols"]]; ch0 = Z["data"][:, :, 0]
P = np.load(PATCH, allow_pickle=False); pr = P["row"].astype(np.int64); pc = P["col"].astype(np.int64); raw = P["raw32"].astype(np.float32)
cr, cc = L.candidates(ch0); cset = set(zip(cr.tolist(), cc.tolist())); pkeys = list(zip(pr.tolist(), pc.tolist())); pset = set(pkeys)
print(f"cache {os.path.basename(CACHE)} TT {ch0.shape[0]} candidates {len(cset)} | patch rows {len(pkeys)} | sources {SRCS}", flush=True)
closes = {}; sources = {}
def prev_month_file(d, sym, t):
    y, m = time.gmtime(t).tm_year, time.gmtime(t).tm_mon - 1
    if m == 0: y, m = y - 1, 12
    return f"{d}/{sym}_{y:04d}-{m:02d}.csv"
def find_close(sym, t):
    """(close, path) or (None, None): first source file (in the documented order) that has a close at t."""
    order = []
    for d in SRCS:
        order += [f"{d}/{sym}_{time.strftime('%Y-%m', time.gmtime(t))}.csv", prev_month_file(d, sym, t),
                  f"{d}/{sym}/{time.strftime('%Y-%m-%d', time.gmtime(t - 300))}.zip", f"{d}/{sym}/{time.strftime('%Y-%m-%d', time.gmtime(t))}.zip"]
    for p in order:
        if not os.path.isfile(p): continue
        if p not in closes:
            closes[p] = L.read_closes(p); sources[p] = L.sha256_file(p)
        v = closes[p].get(int(t))
        if v is not None: return v, p
    return None, None
kept, not_clipped, clipped_missing, unresolved = [], [], [], []
def pair(r, c):
    t = int(CTS[r]); s = syms[c]
    a, pa = find_close(s, t); b, pb = find_close(s, t - 300)
    return t, s, a, pa, b, pb
for i, (r, c) in enumerate(pkeys):
    t, s, a, pa, b, pb = pair(r, c)
    base = {"row": int(r), "col": int(c), "ts": t, "ts_utc": L.utc(t), "symbol": s}
    if a is None or b is None or not (b > 0):
        unresolved.append(dict(base, kind="patch_row", close_t=a, close_prev=b)); continue
    rv = a / b - 1.0
    kept.append(dict(base, close_t=a, close_prev=b, src_t=pa, src_prev=pb, rv=rv, raw32=float(raw[i]), raw32_rederived_bitwise=bool(np.float32(rv).view(np.uint32) == raw[i].view(np.uint32))))
for (r, c) in sorted(cset - pset):
    t, s, a, pa, b, pb = pair(r, c)
    base = {"row": int(r), "col": int(c), "ts": t, "ts_utc": L.utc(t), "symbol": s, "cache_value": float(ch0[r, c])}
    if a is None or b is None or not (b > 0):
        unresolved.append(dict(base, kind="candidate_not_in_patch", close_t=a, close_prev=b)); continue
    rv = a / b - 1.0
    (not_clipped if abs(rv) <= 0.3 else clipped_missing).append(dict(base, close_t=a, close_prev=b, src_t=pa, src_prev=pb, rv=rv))
man = {"schema": L.MANIFEST_SCHEMA, "cache": CACHE, "cache_sha256": L.sha256_file(CACHE), "raw_patch": PATCH, "raw_patch_sha256": L.sha256_file(PATCH),
       "candidate_rule": "isfinite(ch0) & (ch0 == +-float16(0.3))", "keep_rule": "|close_t/close_prev - 1| > 0.3", "close_rule": "5m kline: close time = open_time//1000 + 300, close = column 4",
       "kline_sources": SRCS, "sources": dict(sorted(sources.items())), "kept": kept, "not_clipped": not_clipped, "clipped_missing": clipped_missing, "unresolved": unresolved,
       "counts": {"candidates": len(cset), "patch_rows": len(pkeys), "kept": len(kept), "kept_rederived_bitwise": sum(1 for e in kept if e["raw32_rederived_bitwise"]),
                  "not_clipped": len(not_clipped), "clipped_missing": len(clipped_missing), "unresolved": len(unresolved), "patch_rows_not_candidates": len(pset - cset)},
       "self_sha256": L.sha256_file(os.path.abspath(__file__)), "lib_sha256": L.sha256_file(L.__file__), "built_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "wall_s": round(time.time() - t0, 1)}
os.makedirs(os.path.dirname(os.path.abspath(OUTP)), exist_ok=True)
with open(OUTP + ".tmp", "w") as f: json.dump(man, f, indent=1)
os.replace(OUTP + ".tmp", OUTP)
print("RAWPATCH_MANIFEST_DONE " + json.dumps(man["counts"]) + f" -> {OUTP}", flush=True)
