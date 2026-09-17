#!/usr/bin/env python3
"""fp2_member_mask_build.py — FP2-8 §2.2 (2026-09-17): the A1 TRAINING member mask = TRADABLE(W24H) at the anchor, on the 5m CACHE's own 4h grid.

Not the U-PIT/CRYPTO umask (that would fold a universe-policy choice into a data-correctness fix); tradability only — the FX_DATA definition
(SPEC_TRADABILITY: TRADABLE(A) ⇔ ≥1 TRADED bar with close in (A−24h, A]) read from the certified artifact tradability_v1.npz (run 2, sha 54d409d0…).

Positive control (before anything is written, three-state):
  P1  every 4h anchor of the cache grid has a tradability row (grid coverage; 0 missing)
  P2  on the A0 panel axis: (this mask AND umask_UPIT_CRYPTO) == FX_DATA's certified injection artifact umask_UPIT_CRYPTO_tradable_W24H (3badc4b6…) BITWISE
      — ties this device's reading of `state_W24H == TRADABLE` to the artifact FX_DATA judged with (TRD-D3 N1–N9)
  P3  symbols axis identical to the cache
Verdict PASS ⇒ deterministic npz {ts, symbols, mask, definition, tradability_sha256, spec_sha256} + receipt; FAIL ⇒ nothing written, rc 1;
an input that cannot be read/verified ⇒ UNAVAILABLE rc 3.
env (all required): CACHE  TRD_NPZ  TRD_SHA  UMASK_NPZ  INJECT_NPZ  INJECT_SHA  OUT  RECEIPT   (PYTHONPATH must carry common/tradability.py)"""
import hashlib, json, os, sys, time, zipfile
import numpy as np

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""): h.update(ch)
    return h.hexdigest()

def det_npz(path, arrays):   # deterministic writer (= fx_trd01_inject.py det_npz): fixed date, sorted keys, no pickle
    tmp = path + ".tmp"
    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for k in sorted(arrays):
            zi = zipfile.ZipInfo(k + ".npy", date_time=(1980, 1, 1, 0, 0, 0)); zi.compress_type = zipfile.ZIP_DEFLATED
            a = np.asarray(arrays[k]); a = a if a.ndim == 0 else np.ascontiguousarray(a)
            with zf.open(zi, "w", force_zip64=True) as fh: np.lib.format.write_array(fh, a, allow_pickle=False)
    os.replace(tmp, path)

def main():
    req = ("CACHE", "TRD_NPZ", "TRD_SHA", "UMASK_NPZ", "INJECT_NPZ", "INJECT_SHA", "OUT", "RECEIPT")
    miss = [k for k in req if not os.environ.get(k)]
    if miss: print("REFUSED env missing", miss); return 3
    E = {k: os.environ[k] for k in req}
    rec = {"device": os.path.basename(__file__), "self_sha256": sha(os.path.abspath(__file__)), "utc": time.strftime("%FT%TZ", time.gmtime()),
           "env": E, "numpy": np.__version__, "checks": {}, "VERDICT": None}
    def check(name, ok, detail=None):
        rec["checks"][name] = {"ok": bool(ok), "detail": detail}; print(("  OK   " if ok else "  FAIL ") + name + (("  — " + json.dumps(detail, default=str)[:200]) if detail is not None else ""), flush=True)
    try:
        import tradability as T
        A = T.Artifact.load(E["TRD_NPZ"], expected_sha256=E["TRD_SHA"])
        with zipfile.ZipFile(E["CACHE"]) as z:
            cts = np.load(z.open("ts.npy")).astype(np.int64); csym = [str(s) for s in np.load(z.open("symbols.npy"), allow_pickle=True)]
        U = np.load(E["UMASK_NPZ"], allow_pickle=True); I = np.load(E["INJECT_NPZ"], allow_pickle=True)
        inj_sha = sha(E["INJECT_NPZ"])
    except Exception as e:   # noqa: BLE001
        rec["VERDICT"] = "UNAVAILABLE"; rec["error"] = repr(e); json.dump(rec, open(E["RECEIPT"], "w"), indent=1, default=str)
        print("UNAVAILABLE", repr(e)); return 3
    rec["inputs"] = {"cache": E["CACHE"], "tradability_sha256": A.sha256, "umask_sha256": sha(E["UMASK_NPZ"]), "inject_sha256": inj_sha, "spec_sha256": T.SPEC_SHA256}
    check("P0 inject artifact sha == declared (FX_DATA TRD-D3 N2)", inj_sha == E["INJECT_SHA"], {"got": inj_sha[:16], "declared": E["INJECT_SHA"][:16]})
    check("P3 symbols axis: cache == tradability", csym == A.symbols, {"n_cache": len(csym), "n_trd": len(A.symbols)})
    grid = cts[cts % 14400 == 0]
    missing = [int(t) for t in grid if int(t) not in A._row]
    check("P1 every cache 4h anchor has a tradability row", not missing, {"anchors": int(len(grid)), "first": int(grid[0]), "last": int(grid[-1]), "n_missing": len(missing), "missing_first": missing[:5]})
    if any(not c["ok"] for c in rec["checks"].values()):
        rec["VERDICT"] = "FAIL"; json.dump(rec, open(E["RECEIPT"], "w"), indent=1, default=str); print("FAIL (nothing written)"); return 1
    TR = A._z["state_W24H"][A.rows(grid)] == T.TRADABLE
    uts = U["ts"].astype(np.int64); UM = np.asarray(U["mask"]); usym = [str(s) for s in U["symbols"]]
    check("P3b symbols axis: umask == cache", usym == csym)
    grow = {int(t): i for i, t in enumerate(grid)}
    umiss = [int(t) for t in uts if int(t) not in grow]
    check("P2a every umask anchor is on the cache 4h grid", not umiss, {"n_umask": int(len(uts)), "n_missing": len(umiss)})
    if not umiss:
        sub = TR[[grow[int(t)] for t in uts]] & UM
        IM = np.asarray(I["mask"]); same_axis = np.array_equal(I["ts"].astype(np.int64), uts) and [str(s) for s in I["symbols"]] == usym
        check("P2 (mask AND umask) on the A0 axis == certified injection artifact BITWISE", same_axis and IM.dtype == bool and IM.shape == sub.shape and np.array_equal(sub, IM),
              {"same_axis": same_axis, "cells": int(sub.size), "diff_cells": (int((sub != IM).sum()) if IM.shape == sub.shape else None),
               "umask_true": int(UM.sum()), "umask_and_tradable_true": int(sub.sum()), "dropped": int((UM & ~TR[[grow[int(t)] for t in uts]]).sum())})
    if any(not c["ok"] for c in rec["checks"].values()):
        rec["VERDICT"] = "FAIL"; json.dump(rec, open(E["RECEIPT"], "w"), indent=1, default=str); print("FAIL (nothing written)"); return 1
    years = grid.astype("datetime64[s]").astype("datetime64[Y]").astype(int) + 1970
    rec["stats"] = {"anchors": int(len(grid)), "symbols": len(csym), "tradable_cells": int(TR.sum()), "cells": int(TR.size), "tradable_share": float(TR.mean()),
                    "by_year_tradable_share": {str(int(y)): float(TR[years == y].mean()) for y in np.unique(years)}}
    det_npz(E["OUT"], {"ts": grid, "symbols": np.array(csym), "mask": TR, "spec_sha256": np.array(T.SPEC_SHA256), "tradability_sha256": np.array(A.sha256),
                       "definition": np.array("TRADABLE(W24H) at the anchor (SPEC_TRADABILITY), on the 5m cache 4h grid; training member mask for FP2-8 arm A1")})
    back = np.load(E["OUT"], allow_pickle=True)
    check("W1 re-read == written (mask, ts, symbols)", np.array_equal(back["mask"], TR) and np.array_equal(back["ts"], grid) and [str(s) for s in back["symbols"]] == csym)
    rec["output"] = {"path": E["OUT"], "sha256": sha(E["OUT"]), "bytes": os.path.getsize(E["OUT"])}
    rec["VERDICT"] = "PASS" if all(c["ok"] for c in rec["checks"].values()) else "FAIL"
    json.dump(rec, open(E["RECEIPT"], "w"), indent=1, default=str); print(rec["VERDICT"], json.dumps(rec["stats"])[:300], rec["output"]["sha256"][:16])
    return 0 if rec["VERDICT"] == "PASS" else 1

if __name__ == "__main__":
    sys.exit(main())
