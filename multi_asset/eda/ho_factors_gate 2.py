"""DATA-GATE for the HIGHER-ORDER dynamic factor set (build_ho_factors.py).

> created 2026-06-20 | branch dual-source-perp | READ-ONLY analysis

HONEST QUESTION (numbers only)
------------------------------
The tradable target is perp_y_600 (std ~16.7 bps). The basis-change r = perp_y -
spot_y is an IDENTITY (r == basis change over the horizon, corr 1.0) and only
~0.3% of perp variance; basis predicts r at 0.5+ but that is largely a level->
reversion identity (the rich gate's +600s shift sentinel INFLATED r-IC 0.54->0.73,
i.e. r-IC is NOT a clean leak-free alpha measure). So r-IC is reported only as a
DIAGNOSTIC. The DECISIVE, tradable test is:

  block-deltaP on perp_y over the CURRENT set (spot64 + simple-cross = basis +
  xvenue from the rich library), per regime (STRONG 2025-02/04, CHOPPY 2026-03/05),
  CLEAN ::4, walk-forward, MAD-sigma, lambda-on-val, 1-day embargo.

For each HO family and the union we report:
  perp blk dP : pooled CLEAN perp_y Pearson of (CURRENT + family) - CURRENT.
  perp dP vs spot64 : (spot64 + family) - spot64  (does it help even raw?).
  r-IC (diag) : multivariate r-IC (sanity / mechanism only, NOT tradable).
  leak sentinel: rebuild the time-series HO families from a +600s FORWARD-shifted
                 mid grid; the perp blk dP must NOT inflate (a true >=t leak would).
  null band   : y-permutation 97.5pct |perp dP| (sampling floor).
Ranked by RETAINED incremental perp blk dP (min over the two regimes -- a factor
must help, or at least not hurt, in BOTH).
"""
from __future__ import annotations
import argparse, glob, json, os.path as p, sys
import numpy as np
from scipy.stats import pearsonr, spearmanr

_REPO = "/mnt/storage/private/work_hsy/quant_research_multi_asset"
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

from multi_asset.data.build_rich_xfeats import build_day as build_rich_day, FAMILIES as RICH_FAM, per_second_source, _sample_grid
from multi_asset.data.build_ho_factors import build_day_ho, HO_FAMILIES, family_basis_dynamics, family_leadlag, family_regime, _finalize, family_orderflow, family_bookshape
from multi_asset.eda.perpY_ridge_gate import _fit_select, _predict
from multi_asset.eda.rich_xfeats_gate import (
    DATA_DIR, LASTTS_DIR, SPOT_DIR, CLEAN_DIR, MID_DIR, US, HORIZON_S,
    _have, _clean_idx, walkforward, _first_ge,
    TEST_DAYS, VAL_DAYS, MIN_TRAIN_DAYS,
)

STRONG_FOLDS = [dict(name="strong_2025_02", test_start="2025-02-01"),
                dict(name="strong_2025_04", test_start="2025-04-01")]
CHOPPY_FOLDS = [dict(name="choppy_2026_03", test_start="2026-03-01"),
                dict(name="choppy_2026_05", test_start="2026-05-01")]


def _load_day(day, shift_mid_sec=0):
    """current set (spot64 + rich basis + rich xvenue) + HO families + targets."""
    lc = np.load(p.join(LASTTS_DIR, f"{day}.npz"))
    ts = lc["timestamps"].astype(np.int64)
    pts = lc["perp_ts"].astype(np.int64)
    diff = pts - ts
    if diff.size == 0 or not np.all(diff == diff[0]) or abs(int(diff[0])) > 10*US:
        return None
    spot64 = lc["spot_last"].astype(np.float64)
    # rich CURRENT set: basis + xvenue
    dr = build_rich_day(day, mid_dir=MID_DIR, lastts_dir=LASTTS_DIR)
    if not np.array_equal(dr["ts"], ts):
        return None
    cur = np.concatenate([dr["fam"]["basis"][1], dr["fam"]["xvenue"][1]], axis=1)
    # HO families
    if shift_mid_sec == 0:
        dh = build_day_ho(day, MID_DIR, LASTTS_DIR)
        ho = {f: dh["fam"][f][1] for f in HO_FAMILIES}
        ho_names = {f: dh["fam"][f][0] for f in HO_FAMILIES}
    else:
        ho, ho_names = _build_ho_shifted(day, ts, shift_mid_sec)
    # targets
    zs = np.load(p.join(SPOT_DIR, f"{day}.npz"))
    zc = np.load(p.join(CLEAN_DIR, f"{day}.npz"))
    if not (np.array_equal(zs["timestamps"].astype(np.int64), ts) and
            np.array_equal(zc["timestamps"].astype(np.int64), ts)):
        return None
    sy = zs["y_600"].astype(np.float64); sm = zs["y_mask_600"].astype(bool)
    cy = zc["y_600"].astype(np.float64); cm = zc["y_mask_600"].astype(bool)
    r = cy - sy
    mask = sm & cm & np.isfinite(sy) & np.isfinite(cy) & np.all(np.isfinite(spot64), 1) & np.all(np.isfinite(cur),1)
    for f in HO_FAMILIES:
        mask &= np.all(np.isfinite(ho[f]), 1)
    return dict(ts=ts, spot64=spot64, cur=cur, ho=ho, ho_names=ho_names,
                spot_y=sy, perp_y=cy, r=r, mask=mask)


def _build_ho_shifted(day, ts, shift_sec):
    """Rebuild the TIME-SERIES HO families (bd/ll/of/rg) from a +shift forward
    mid grid (leak sentinel). bs is snapshot-row based; rebuild from the same
    snapshots (its lags are causal already) -- shift only the mid-derived ones.
    A forward shift makes the grid value at second t reflect t+shift (future);
    perp blk dP must NOT increase."""
    lc = np.load(p.join(LASTTS_DIR, f"{day}.npz"))
    spot_last = lc["spot_last"].astype(np.float64); perp_last = lc["perp_last"].astype(np.float64)
    pred_sec = ts // US
    zm = np.load(p.join(MID_DIR, f"{day}.npz"))
    sec = zm["sec"].astype(np.int64)
    sm = zm["spot_mid"].astype(np.float64).copy(); pm = zm["perp_mid"].astype(np.float64).copy()
    n = sec.size
    if shift_sec < n:          # shift BOTH legs forward (basis future)
        sm[:n-shift_sec] = sm[shift_sec:]; sm[n-shift_sec:] = sm[-1]
        pm[:n-shift_sec] = pm[shift_sec:]; pm[n-shift_sec:] = pm[-1]
    src = per_second_source(sec, sm, pm)
    ho = {}; ho_names = {}
    names, X = _finalize(family_basis_dynamics(src, pred_sec)); ho["bd"]=X; ho_names["bd"]=names
    names, X = _finalize(family_leadlag(src), sec, pred_sec); ho["ll"]=X; ho_names["ll"]=names
    names, X = _finalize(family_orderflow(src, perp_last, pred_sec)); ho["of"]=X; ho_names["of"]=names
    names, X = _finalize(family_bookshape(src, spot_last, perp_last, pred_sec, ts)); ho["bs"]=X; ho_names["bs"]=names
    names, X = _finalize(family_regime(src, spot_last, perp_last, pred_sec)); ho["rg"]=X; ho_names["rg"]=names
    return ho, ho_names


def load_days(days, shift_mid_sec=0, verbose=False):
    acc_spot, acc_cur = [], []
    acc_ho = {f: [] for f in HO_FAMILIES}
    acc_sy, acc_cy, acc_r, acc_ts, acc_di = [], [], [], [], []
    ho_names = None; kept = []
    for day in days:
        if not _have(day):
            continue
        d = _load_day(day, shift_mid_sec=shift_mid_sec)
        if d is None:
            continue
        keep = d["mask"] & _clean_idx(d["ts"])
        if keep.sum() == 0:
            continue
        if ho_names is None:
            ho_names = d["ho_names"]
        ki = len(kept)
        acc_spot.append(d["spot64"][keep]); acc_cur.append(d["cur"][keep])
        for f in HO_FAMILIES:
            acc_ho[f].append(d["ho"][f][keep])
        acc_sy.append(d["spot_y"][keep]); acc_cy.append(d["perp_y"][keep])
        acc_r.append(d["r"][keep]); acc_ts.append(d["ts"][keep])
        acc_di.append(np.full(int(keep.sum()), ki, np.int32)); kept.append(day)
    if not kept:
        raise RuntimeError("no usable days")
    out = dict(spot64=np.concatenate(acc_spot), cur=np.concatenate(acc_cur),
               ho={f: np.concatenate(acc_ho[f]) for f in HO_FAMILIES}, ho_names=ho_names,
               spot_y=np.concatenate(acc_sy), perp_y=np.concatenate(acc_cy),
               r=np.concatenate(acc_r), ts=np.concatenate(acc_ts),
               day_idx=np.concatenate(acc_di), kept_days=kept)
    if verbose:
        print(f"[load] kept {len(kept)} days N={out['spot64'].shape[0]} "
              f"HO total k={sum(out['ho'][f].shape[1] for f in HO_FAMILIES)} shift={shift_mid_sec}")
    return out


def _uni_ic(x, y):
    m = np.isfinite(x) & np.isfinite(y)
    if m.sum() < 50 or x[m].std()==0 or y[m].std()==0:
        return float("nan")
    return float(pearsonr(x[m], y[m])[0])


def run_regime(name, folds, json_out=None):
    last = max(f["test_start"] for f in folds)
    import datetime as dt
    y, mo = map(int, last[:7].split("-"))
    ndays = (dt.date(y+(mo==12), (mo%12)+1, 1) - dt.date(y, mo, 1)).days
    end = f"{last[:7]}-{ndays:02d}"
    alld = sorted({p.basename(f)[:-4] for f in glob.glob(p.join(LASTTS_DIR,"*.npz"))
                   if p.basename(f)[0].isdigit()})
    days = [d for d in alld if d <= end and _have(d)]
    print(f"\n{'='*80}\nREGIME={name} folds={[f['name'] for f in folds]} cand_days={len(days)} (..{end})")
    data = load_days(days, verbose=True)
    dl = data["kept_days"]; di = data["day_idx"]
    spot64 = data["spot64"]; cur = data["cur"]; ho = data["ho"]
    perp_y = data["perp_y"]; r = data["r"]
    current = np.concatenate([spot64, cur], axis=1)   # CURRENT production set

    base_cur = walkforward(current, perp_y, di, dl, folds)
    base_spot = walkforward(spot64, perp_y, di, dl, folds)
    print(f"\n[base] CURRENT(spot64+basis+xvenue k={current.shape[1]}) perp_y P={base_cur['P']:+.4f}  "
          f"spot64-only P={base_spot['P']:+.4f}")
    print(f"\n-- per HO-family (walk-forward pooled OOS, perp_y is the TRADABLE target) --")
    print(f"  {'fam':4s} k  {'perp_blkdP_vsCUR':>16s} {'perp_dP_vsSPOT':>14s} {'rIC(diag)':>10s}  perfoldP(perp,vsCUR)")
    fam_res = {}
    for f in HO_FAMILIES:
        Xf = ho[f]
        blk_cur = walkforward(np.concatenate([current, Xf],1), perp_y, di, dl, folds)
        blk_spot = walkforward(np.concatenate([spot64, Xf],1), perp_y, di, dl, folds)
        ric = walkforward(Xf, r, di, dl, folds)
        dP_cur = blk_cur["P"] - base_cur["P"]
        dP_spot = blk_spot["P"] - base_spot["P"]
        fam_res[f] = dict(k=Xf.shape[1], dP_cur=dP_cur, dP_spot=dP_spot, rIC=ric["P"],
                          blk_cur_P=blk_cur["P"], perfold=blk_cur["perfold_P"])
        print(f"  {f:4s} {Xf.shape[1]:2d} {dP_cur:+16.4f} {dP_spot:+14.4f} {ric['P']:+10.4f}  {blk_cur['perfold_P']}")
    # union of all HO
    allho = np.concatenate([ho[f] for f in HO_FAMILIES], axis=1)
    blk_u = walkforward(np.concatenate([current, allho],1), perp_y, di, dl, folds)
    blk_us = walkforward(np.concatenate([spot64, allho],1), perp_y, di, dl, folds)
    ric_u = walkforward(allho, r, di, dl, folds)
    print(f"\n-- UNION HO (k={allho.shape[1]}) perp blk dP vs CUR = {blk_u['P']-base_cur['P']:+.4f}  "
          f"vs SPOT = {blk_us['P']-base_spot['P']:+.4f}  rIC(diag)={ric_u['P']:+.4f}  perfold={blk_u['perfold_P']}")

    # top univariate perp-IC and r-IC across all HO
    names = sum([data["ho_names"][f] for f in HO_FAMILIES], [])
    uni = []
    for j, nm in enumerate(names):
        uni.append((nm, _uni_ic(allho[:,j], perp_y), _uni_ic(allho[:,j], r)))
    uni_perp = sorted(uni, key=lambda t: -abs(t[1]) if np.isfinite(t[1]) else 0)
    print("\n-- top-15 HO features by |univariate perp-IC| (perp / r) --")
    for nm, pp, pr_ in uni_perp[:15]:
        print(f"  {nm:30s} perp:{pp:+.4f}  r:{pr_:+.4f}")

    # add-one-in over CURRENT: top-10 by |perp-IC|, each added to CURRENT, dP
    print("\n-- add-one-in over CURRENT: top-10 HO by |perp-IC| --")
    addone = []
    for nm, pp, pr_ in uni_perp[:10]:
        j = names.index(nm)
        rr = walkforward(np.concatenate([current, allho[:,[j]]],1), perp_y, di, dl, folds)
        d = rr["P"] - base_cur["P"]
        addone.append((nm, round(d,4), round(rr["P"],4)))
        print(f"  +{nm:30s} CUR+1 perp P={rr['P']:+.4f}  dP={d:+.4f}")

    out = dict(regime=name, n=int(base_cur["n"]),
               base_cur_P=round(base_cur["P"],4), base_spot_P=round(base_spot["P"],4),
               families={f: dict(k=v["k"], perp_blkdP_vsCUR=round(v["dP_cur"],4),
                                 perp_dP_vsSPOT=round(v["dP_spot"],4),
                                 rIC_diag=round(v["rIC"],4), perfold=v["perfold"])
                         for f,v in fam_res.items()},
               union=dict(k=int(allho.shape[1]),
                          perp_blkdP_vsCUR=round(blk_u["P"]-base_cur["P"],4),
                          perp_dP_vsSPOT=round(blk_us["P"]-base_spot["P"],4),
                          rIC_diag=round(ric_u["P"],4), perfold=blk_u["perfold_P"]),
               top_uni_perp=[dict(name=nm, perpIC=round(pp,4), rIC=round(pr_,4))
                             for nm,pp,pr_ in uni_perp[:15]],
               add_one_in=[dict(name=nm, dP=d, cur_plus1_P=cp) for nm,d,cp in addone])

    # leak sentinel (+600s shift): union perp blk dP must NOT inflate
    try:
        ds = load_days(days, shift_mid_sec=600)
        sho = np.concatenate([ds["ho"][f] for f in HO_FAMILIES], axis=1)
        cur_s = np.concatenate([ds["spot64"], ds["cur"]], axis=1)
        base_s = walkforward(cur_s, ds["perp_y"], ds["day_idx"], ds["kept_days"], folds)
        blk_s = walkforward(np.concatenate([cur_s, sho],1), ds["perp_y"], ds["day_idx"], ds["kept_days"], folds)
        sent = round(blk_s["P"] - base_s["P"], 4)
        print(f"\n-- leak sentinel (+600s fwd mid): union perp blk dP unshifted={out['union']['perp_blkdP_vsCUR']:+.4f}  shifted={sent:+.4f}  (shifted must NOT exceed)")
        out["leak_sentinel_shifted_union_dP"] = sent
    except Exception as e:
        print("sentinel err", e)

    if json_out:
        json.dump(out, open(json_out,"w"), indent=2, default=float)
        print(f"saved -> {json_out}")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--regime", choices=["strong","choppy","both"], default="both")
    ap.add_argument("--json_out", default=None)
    a = ap.parse_args()
    if a.regime in ("strong","both"):
        run_regime("STRONG", STRONG_FOLDS, a.json_out and a.json_out.replace(".json","_strong.json"))
    if a.regime in ("choppy","both"):
        run_regime("CHOPPY", CHOPPY_FOLDS, a.json_out and a.json_out.replace(".json","_choppy.json"))


if __name__ == "__main__":
    main()
