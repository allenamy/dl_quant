#!/usr/bin/env python3
"""ad_funding_iv.py -- AUDIT_DATA 2026-09-13, device B (pod2, CPU, READ-ONLY): funding settlement-interval caliber of the 4h panels.

Question: does any panel's f_fund_iv (and the 8h-normalised EMA f_fund_ema_v1 built from it) use a WRONG settlement interval?
Known suspect (memory x0910_fund_iv_interval_mismatch, T5b): the r6 x0910 splice gives every API-tail row of a symbol ONE interval
taken from /fapi/v1/fundingInfo at pull time (r6_panel_splice.py L82 `SEP_IV.get(s)` + L90 explicit-iv-over-spacing precedence).

Truth used here, per settlement row: the zip archive's own `funding_interval_hours` column when the row is in a zip, otherwise the
spacing to the previous settlement of the same symbol (hours, snapped to {1,2,4,6,8}); first row / gap > 24 h => unknown.
Event stream = zips (/workspace/wide_multisrc/funding) U fund_aug.json.gz U r6_fund_sep.json.gz, union by second.

Positive controls (must pass before any finding is read):
  PC1  zip rows: the archive column agrees with the spacing rule wherever both are defined (reported as a rate, not assumed).
  PC2  the r6 builder rule (verbatim algebra of r6_panel_splice.py L57-L120) re-derived here reproduces the x0910 panels' TAIL
       f_fund_iv exactly and f_fund_ema_v1 to float32 rounding; if not, the tail comparison is declared INVALID.
Readings: per panel (v2ext, v3splice, v2ext_x0910, v3splice_x0910) the count of (anchor, symbol) cells where the panel interval
differs from truth (prefix vs tail for x0910), top symbols; on the x0910 tails the corrected EMA (same seed, true interval)
vs the panel EMA: max |d|, per-anchor Spearman over the full finite base, FTRIM class flips (rn8 = f_fund_now*8/iv <= -0.0010).
Usage: python3 ad_funding_iv.py <out_receipt.json>
"""
import os, sys, io, csv, json, glob, gzip, zipfile, time, hashlib
from multiprocessing import Pool
import numpy as np
from scipy.stats import spearmanr

ENV_WHITELIST = set()
os.nice(19)
OUT = sys.argv[1]
W = "/workspace"; FDIR = f"{W}/wide_multisrc/funding"
AUGP = f"{W}/fund_aug.json.gz"; SEPP = f"{W}/uplift_2026-09-11/r6/dl/r6_fund_sep.json.gz"
PANELS = {"v2ext": f"{W}/data/wide_panel_4h_v2ext.npz", "v3splice": f"{W}/data/wide_panel_4h_v3splice.npz",
          "v2ext_x0910": f"{W}/uplift_2026-09-11/r6/out/wide_panel_4h_v2ext_x0910.npz", "v3splice_x0910": f"{W}/uplift_2026-09-11/r6/out/wide_panel_4h_v3splice_x0910.npz"}
BASE_OF = {"v2ext_x0910": "v2ext", "v3splice_x0910": "v3splice"}
HL = 3 * 86400.0; ALLOWED = np.array([1.0, 2.0, 4.0, 6.0, 8.0])
FTRIM_TH = -0.0010
WATCH = ["SKRUSDT", "SOPHUSDT", "IOSTUSDT"]

def utc(t): return time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(int(t)))
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): h.update(b)
    return h.hexdigest()
def snap(x):
    x = np.asarray(x, float); out = np.full(x.shape, np.nan); ok = np.isfinite(x)
    out[ok] = ALLOWED[np.argmin(np.abs(x[ok][:, None] - ALLOWED[None, :]), axis=1)]; return out

AUG = json.loads(gzip.open(AUGP, "rt").read()); SEP = json.loads(gzip.open(SEPP, "rt").read())
AUG_IV = {k: float(v) for k, v in (AUG.get("intervals") or {}).items() if v}
SEP_IV = {k: float(v) for k, v in (SEP.get("intervals") or {}).items() if v}

def zip_rows(s):
    rows = []
    for zp in sorted(glob.glob(f"{FDIR}/{s}/*.zip")):
        try:
            zf = zipfile.ZipFile(zp)
            with zf.open(zf.namelist()[0]) as fh:
                for row in csv.reader(io.TextIOWrapper(fh)):
                    if not row or not row[0].strip().isdigit() and "time" in row[0].lower(): continue
                    try:
                        ts_ = int(row[0]); rate = float(row[-1]) if abs(float(row[-1])) < 0.2 else float(row[1]); iv = np.nan
                        if len(row) >= 3:
                            try:
                                cand = float(row[1])
                                if 1 <= cand <= 24 and abs(cand - round(cand)) < 1e-9 and abs(float(row[-1])) < 0.2: iv = cand
                            except Exception: pass
                        rows.append((ts_ // 1000, rate, iv))
                    except Exception: continue
        except Exception: continue
    return rows

def per_symbol(s):
    zr = zip_rows(s)
    ar = [(int(t) // 1000, float(r)) for t, r in (AUG.get("rates") or {}).get(s, [])]
    sr = [(int(t) // 1000, float(r)) for t, r in (SEP.get("rates") or {}).get(s, [])]
    # ---- truth stream: union by second; rate precedence zip > aug > sep; conflicts counted ----
    ev = {}; conflicts = 0
    for t, r, iv in zr: ev.setdefault(t, {})["zip"] = (r, iv)
    for t, r in ar: ev.setdefault(t, {})["aug"] = r
    for t, r in sr: ev.setdefault(t, {})["sep"] = r
    ft = np.array(sorted(ev), np.int64)
    rate = np.empty(len(ft)); ivcol = np.full(len(ft), np.nan); src = np.zeros(len(ft), np.int8)
    for k, t in enumerate(ft):
        e = ev[int(t)]; vals = []
        if "zip" in e: rate[k] = e["zip"][0]; ivcol[k] = e["zip"][1]; src[k] |= 1; vals.append(e["zip"][0])
        if "aug" in e:
            src[k] |= 2; vals.append(e["aug"])
            if not (src[k] & 1): rate[k] = e["aug"]
        if "sep" in e:
            src[k] |= 4; vals.append(e["sep"])
            if not (src[k] & 3): rate[k] = e["sep"]
        if len(vals) > 1 and (max(vals) - min(vals)) > 1e-12: conflicts += 1
    dt_h = np.full(len(ft), np.nan)
    if len(ft) > 1:
        d = np.round(np.diff(ft) / 3600.0); dt_h[1:] = np.where((d > 0) & (d <= 24), d, np.nan)
    iv_dt = snap(dt_h)
    iv_true = np.where(np.isfinite(ivcol), ivcol, iv_dt)
    both = np.isfinite(ivcol) & np.isfinite(iv_dt)
    pc1 = {"zip_rows_with_col": int(np.isfinite(ivcol).sum()), "both_defined": int(both.sum()), "col_ne_spacing": int((both & (ivcol != iv_dt)).sum())}
    # ---- r6 builder rule, verbatim algebra (r6_panel_splice.py L63-L91): zips + AUG(AUG_IV) + SEP(SEP_IV), sort, explicit iv wins ----
    rows = list(zr) + [(t, r, AUG_IV.get(s, np.nan)) for t, r in ar] + [(t, r, SEP_IV.get(s, np.nan)) for t, r in sr]
    b = None
    if rows:
        rows.sort(); ded = {}
        for t_, r_, i_ in rows:
            if t_ not in ded or np.isfinite(i_): ded[t_] = (r_, i_)
        bft = np.array(sorted(ded), np.int64); bfr = np.array([ded[t][0] for t in bft]); bfiv = np.array([ded[t][1] for t in bft])
        bdt = np.round(np.diff(bft) / 3600.0); bdv = np.full(len(bft), np.nan); bdv[1:] = np.where((bdt > 0) & (bdt <= 24), bdt, np.nan)
        biv = np.where(np.isfinite(bfiv), bfiv, bdv); biv = np.where(np.isfinite(biv), biv, 8.0)
        biv = ALLOWED[np.argmin(np.abs(biv[:, None] - ALLOWED[None, :]), axis=1)]
        b = (bft, bfr, biv)
    # ---- v2ext builder rule (pod_panel_ext.py L104-L122): zips + AUG only ----
    rows2 = list(zr) + [(t, r, AUG_IV.get(s, np.nan)) for t, r in ar]
    b2 = None
    if rows2:
        rows2.sort(); ded = {}
        for t_, r_, i_ in rows2:
            if t_ not in ded or np.isfinite(i_): ded[t_] = (r_, i_)
        cft = np.array(sorted(ded), np.int64); cfr = np.array([ded[t][0] for t in cft]); cfiv = np.array([ded[t][1] for t in cft])
        cdt = np.round(np.diff(cft) / 3600.0); cdv = np.full(len(cft), np.nan); cdv[1:] = np.where((cdt > 0) & (cdt <= 24), cdt, np.nan)
        civ = np.where(np.isfinite(cfiv), cfiv, cdv); civ = np.where(np.isfinite(civ), civ, 8.0)
        civ = ALLOWED[np.argmin(np.abs(civ[:, None] - ALLOWED[None, :]), axis=1)]
        b2 = (cft, cfr, civ)
    return s, {"ft": ft, "rate": rate, "iv_true": iv_true, "src": src, "conflicts": conflicts, "pc1": pc1, "r6rule": b, "v2rule": b2,
               "sep_iv": SEP_IV.get(s), "aug_iv": AUG_IV.get(s)}

def lookup(ft, vals, ts, stale=12 * 3600):
    pos = np.searchsorted(ft, ts, side="right") - 1; ok = pos >= 0
    ok &= (ts - np.where(ok, ft[np.maximum(pos, 0)], 0)) <= stale
    out = np.full(len(ts), np.nan); out[ok] = vals[pos[ok]]; return out, ok, pos

if __name__ == "__main__":
    assert not (ENV_WHITELIST - set(os.environ))
    t0 = time.time()
    P = {k: np.load(v, allow_pickle=True) for k, v in PANELS.items()}
    syms = [str(x) for x in P["v2ext"]["symbols"]]
    for k in P: assert [str(x) for x in P[k]["symbols"]] == syms, k
    with Pool(6) as pool:
        S = dict(pool.map(per_symbol, syms, chunksize=8))
    rec = {"device": "ad_funding_iv.py", "self_sha256": sha(os.path.abspath(__file__)), "inputs": {k: {"path": v, "sha256": sha(v)} for k, v in PANELS.items()},
           "aug": {"path": AUGP, "sha256": sha(AUGP), "intervals_n": len(AUG_IV)}, "sep": {"path": SEPP, "sha256": sha(SEPP), "intervals_n": len(SEP_IV),
           "meta": SEP.get("meta")}, "funding_dir_zip_files": len(glob.glob(f"{FDIR}/*/*.zip"))}
    rec["PC1_zip_column_vs_spacing"] = {"zip_rows_with_col": sum(v["pc1"]["zip_rows_with_col"] for v in S.values()),
                                       "both_defined": sum(v["pc1"]["both_defined"] for v in S.values()),
                                       "col_ne_spacing": sum(v["pc1"]["col_ne_spacing"] for v in S.values()),
                                       "symbols_with_disagreement": sorted([s for s, v in S.items() if v["pc1"]["col_ne_spacing"]])[:40],
                                       "rate_conflicts_between_sources": sum(v["conflicts"] for v in S.values())}
    panels = {}
    for pk, Z in P.items():
        ts = Z["ts"].astype(np.int64); IV = Z["f_fund_iv"].astype(np.float64); FN = Z["f_fund_now"].astype(np.float64); FE = Z["f_fund_ema_v1"].astype(np.float64)
        cut = int(P[BASE_OF[pk]]["ts"].astype(np.int64)[-1]) if pk in BASE_OF else None
        seg = (ts > cut) if cut is not None else np.zeros(len(ts), bool)
        mm = {"prefix": 0, "tail": 0}; cmp = {"prefix": 0, "tail": 0}; by_sym = {}; by_month = {}; fn_mis = 0; watch = {}
        truth_iv = np.full(IV.shape, np.nan)
        for j, s in enumerate(syms):
            v = S[s]
            if not len(v["ft"]): continue
            tiv, ok, pos = lookup(v["ft"], v["iv_true"], ts); trate, _, _ = lookup(v["ft"], v["rate"], ts)
            truth_iv[:, j] = tiv
            fin = np.isfinite(IV[:, j]) & np.isfinite(tiv)
            bad = fin & (IV[:, j] != tiv)
            fn_mis += int((np.isfinite(FN[:, j]) & np.isfinite(trate) & (np.abs(FN[:, j] - trate) > 1e-9)).sum())
            for nm, sel in (("prefix", ~seg), ("tail", seg)):
                cmp[nm] += int((fin & sel).sum()); mm[nm] += int((bad & sel).sum())
            if bad.any():
                by_sym[s] = {"cells": int(bad.sum()), "tail_cells": int((bad & seg).sum()), "first": utc(ts[bad][0]), "last": utc(ts[bad][-1]),
                             "panel_iv_values": sorted(set(np.unique(IV[bad, j]).tolist())), "true_iv_values": sorted(set(np.unique(tiv[bad]).tolist()))}
                for t in ts[bad]:
                    m = time.strftime("%Y-%m", time.gmtime(int(t))); by_month[m] = by_month.get(m, 0) + 1
            if s in WATCH and seg.any():
                watch[s] = [{"anchor": utc(ts[r]), "panel_iv": (None if not np.isfinite(IV[r, j]) else float(IV[r, j])), "true_iv": (None if not np.isfinite(tiv[r]) else float(tiv[r]))}
                            for r in np.where(seg)[0][::6]]
        top = dict(sorted(by_sym.items(), key=lambda kv: -kv[1]["cells"])[:25])
        pr = {"n_anchors": int(len(ts)), "first": utc(ts[0]), "last": utc(ts[-1]), "cut_utc": (utc(cut) if cut else None), "tail_anchors": int(seg.sum()),
              "compared_cells": cmp, "iv_mismatch_cells": mm, "symbols_with_mismatch": len(by_sym), "fund_now_vs_stream_mismatch_cells": fn_mis,
              "mismatch_by_month": dict(sorted(by_month.items())), "top_symbols": top, "watch": watch}
        # ---- tails of the x0910 panels: PC2 reproduce with the r6 rule, then correct with the true interval ----
        if pk in BASE_OF:
            B = P[BASE_OF[pk]]; nC = len(B["ts"]); tail_ts = ts[nC:]; assert np.array_equal(ts[:nC], B["ts"].astype(np.int64))
            BE = B["f_fund_ema_v1"].astype(np.float64)
            rep_iv_bad = 0; rep_ema_max = 0.0; rep_cells = 0; cor = np.full((len(tail_ts), len(syms)), np.nan); rep = np.full_like(cor, np.nan)
            for j, s in enumerate(syms):
                v = S[s]; b = v["r6rule"]
                if b is None: continue
                bft, bfr, biv = b
                pos = np.searchsorted(bft, tail_ts, side="right") - 1; okp = pos >= 0
                fi = np.full(len(tail_ts), np.nan); fi[okp] = biv[pos[okp]]
                stale = okp & ((tail_ts - np.where(okp, bft[np.maximum(pos, 0)], 0)) > 12 * 3600); fi[stale] = np.nan
                pf = IV[nC:, j]; both = np.isfinite(pf) | np.isfinite(fi)
                rep_iv_bad += int((both & ~((np.isfinite(pf) & np.isfinite(fi) & (pf == fi)) | (~np.isfinite(pf) & ~np.isfinite(fi)))).sum())
                seed = BE[-1, j]
                if not np.isfinite(seed): continue
                sel = np.where(bft > int(B["ts"][-1]))[0]
                # replicate (r6 rule) and correct (true iv: zip col else spacing else 8.0) with the SAME event times/rates
                tv = v["iv_true"]; tmap = dict(zip(v["ft"].tolist(), tv.tolist()))
                for mode, arr in (("rep", rep), ("cor", cor)):
                    e1 = float(np.float32(seed)); prev_t = int(B["ts"][-1]); k2 = 0
                    for r_row, ta in enumerate(tail_ts):
                        while k2 < len(sel) and bft[sel[k2]] <= ta:
                            i_ = sel[k2]; ivv = biv[i_] if mode == "rep" else tmap.get(int(bft[i_]), np.nan)
                            if not np.isfinite(ivv): ivv = 8.0
                            a = 1 - 0.5 ** (max(bft[i_] - prev_t, 1) / HL); e1 = e1 + a * (bfr[i_] * (8.0 / ivv) - e1); prev_t = int(bft[i_]); k2 += 1
                        arr[r_row, j] = np.float32(e1)
                okr = np.isfinite(rep[:, j]) & np.isfinite(FE[nC:, j]); rep_cells += int(okr.sum())
                if okr.any(): rep_ema_max = max(rep_ema_max, float(np.abs(rep[okr, j] - FE[nC:, j][okr]).max()))
            PC2 = {"tail_iv_cells_not_reproduced": rep_iv_bad, "tail_ema_v1_cells_compared": rep_cells, "tail_ema_v1_maxabs_replica_vs_panel": rep_ema_max,
                   "PASS": bool(rep_iv_bad == 0 and rep_ema_max <= 1e-6)}
            # seed note: the builder seeds from float32 base values then accumulates in float64 before the float32 write; replica does the same
            d = np.abs(cor - FE[nC:]); okd = np.isfinite(cor) & np.isfinite(FE[nC:])
            sp = []; flips = []; n_changed = []
            for r_row in range(len(tail_ts)):
                ok = okd[r_row]
                if ok.sum() >= 30: sp.append(float(spearmanr(cor[r_row, ok], FE[nC + r_row, ok]).correlation))
                n_changed.append(int((d[r_row] > 1e-6).sum()))
                fn = FN[nC + r_row]; piv = IV[nC + r_row]; tiv = truth_iv[nC + r_row]; okf = np.isfinite(fn) & np.isfinite(piv) & np.isfinite(tiv)
                flips.append(int(((fn[okf] * 8.0 / piv[okf] <= FTRIM_TH) != (fn[okf] * 8.0 / tiv[okf] <= FTRIM_TH)).sum()))
            worst = np.argsort(-np.nan_to_num(d, nan=0.0).max(0))[:10]
            pr["tail_correction"] = {"PC2_builder_rule_reproduces_panel_tail": PC2, "valid": PC2["PASS"],
                                     "ema_v1_maxabs_corrected_vs_panel": float(np.nanmax(np.where(okd, d, np.nan))) if okd.any() else None,
                                     "ema_v1_cells_absdiff_gt_1e-6": int((okd & (d > 1e-6)).sum()), "ema_v1_cells_compared": int(okd.sum()),
                                     "per_anchor_spearman_min": (min(sp) if sp else None), "per_anchor_spearman_median": (float(np.median(sp)) if sp else None),
                                     "per_anchor_names_changed_max": (max(n_changed) if n_changed else None),
                                     "ftrim_class_flips_total": int(sum(flips)), "ftrim_class_flips_anchors_with_any": int(sum(1 for x in flips if x)),
                                     "worst_symbols": [{"symbol": syms[j], "max_abs_ema_v1_diff": float(np.nanmax(np.where(okd[:, j], d[:, j], np.nan))) if okd[:, j].any() else None,
                                                        "sep_interval_at_pull": S[syms[j]]["sep_iv"]} for j in worst]}
        panels[pk] = pr
    rec["panels"] = panels
    rec["elapsed_s"] = round(time.time() - t0, 1); rec["numpy"] = np.__version__
    json.dump(rec, open(OUT, "w"), indent=1)
    print("AD_FUNDING_IV_DONE", json.dumps({k: {"mm": v["iv_mismatch_cells"], "syms": v["symbols_with_mismatch"], "pc2": v.get("tail_correction", {}).get("valid")} for k, v in panels.items()}))
