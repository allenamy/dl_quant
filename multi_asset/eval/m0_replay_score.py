"""PER-YEAR scorer for the M0 full-history walk-forward replay (pre-reg R1-R5).

Reads the M0 replay panel (tag m0_fullhist_wf: panel_ref.npz with >=3600 CL + fold_*_preds.npz)
and a funding_ema panel on the SAME ts grid, then reports, PER CALENDAR YEAR + POOLED:
  - M0 standalone xsec rank-IC (>=3600 CL) + empirical within-ts shuffle-null z
  - M0 net-cost L/S (BE/side, net-Sh @2/5/10bps, per-fold, months-pos, max-DD) via the scorecard engine
  - funding_ema standalone (same caliber, cross-check vs megacap_funding_replay.json)
  - funding+M0 equal-risk z-blend (the deployable Book-1 config)
  - latency decay (fresh-signal caliber)

The pre-registered read (docs/2026-07-09_M0_fullhistory_replay_prereg.md):
  R1 regime-robust: per-year IC z>=2.5 AND sign-consistent (2023/2024/2025); weak-2023 soft-pass if 2024&2025 pass.
  R2 DIVERSIFICATION (decisive): 2024 M0 net-Sh@5bps > 0 while funding 2024 net-Sh < 0.
  R3 favorable-window: if M0 strong ONLY 2025 -> discount headline to test-year mean/median.
  R4 long-run headline: report M0 + blend test-year mean & median.
  R5 maturity gradient: 2023(1yr)<2024(2yr)<2025(3yr) train -> an IC uptrend could be maturity not regime.

Reuses the VALIDATED scorecard caliber (portfolio_scorecard.book_stats/blend/latency,
factor_scorer._perts_ic, factor_pipeline._null_z). CPU. Honest raw-caliber (clipped-target, same as scorecard).

Usage (on server):
  PYTHONPATH=. python multi_asset/eval/m0_replay_score.py --m0_tag m0_fullhist_wf --funding_tag fund_ema_fullhist
  # validation on the existing single-window panel (machinery smoke test):
  PYTHONPATH=. python multi_asset/eval/m0_replay_score.py --m0_tag fund_resid_h3600 --funding_tag fund_ema_h3600 --validate
"""
from __future__ import annotations
import argparse, datetime as dt, numpy as np, sys, os.path as op
sys.path.insert(0, op.abspath(op.join(op.dirname(__file__), "..", "..")))
from multi_asset.eval.factor_pipeline import load_panel, _null_z
from multi_asset.eval.factor_scorer import _perts_ic
from multi_asset.eval.portfolio_scorecard import book_stats, blend, latency, MIN_ASSETS

EXPORT = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/train"


def _years(ts):
    """Calendar year per row (unit-agnostic ns/us/ms/s)."""
    t0 = int(ts[0]); unit = 1e9 if t0 > 1e17 else (1e6 if t0 > 1e14 else (1e3 if t0 > 1e11 else 1.0))
    return np.array([dt.datetime.utcfromtimestamp(int(t) / unit).year for t in ts])


def _row_subset(P, rows):
    return P[rows] if P is not None else None


def _score_one(name, sig, Y, CL, ts, day, horizon, null_z=True):
    ic, _ = _perts_ic(sig, Y, CL)
    if len(ic) == 0:
        return None
    out = dict(name=name, n_ic=len(ic), ic=float(ic.mean()))
    if null_z:
        z = _null_z(lambda Fs: _perts_ic(Fs, Y, CL)[0].mean(), ic.mean(), sig, Y, CL, n=25, seed=0)
        out["z"] = z["z"]; out["null_mean"] = z["null_mean"]
    st = book_stats(sig, Y, CL, ts, day, horizon)
    out.update(be=st["be"], turnover=st["turnover"], gross_sh=st["gross_sh"],
               net_sh=st["net_sh_grid"], per_fold=st["per_fold_net_sh"],
               months_pos=st["months_pos"], max_dd=st["max_dd_bps"], alpha=st["alpha"])
    return out


def _fmt(r):
    if r is None:
        return "  (no usable rows)"
    z = f"z={r.get('z','  na'):>5}" if "z" in r else ""
    g = r["net_sh"]
    return (f"  {r['name']:<26} IC={r['ic']:+.4f} {z} | BE={r['be']:>6.1f} | "
            f"net-Sh 2/5/10={g[2.0]}/{g[5.0]}/{g[10.0]} | gross={r['gross_sh']:+.2f} | "
            f"turn={r['turnover']:.4f} a={r['alpha']} | per-fold={r['per_fold']} | mo+={r['months_pos']} | DD={r['max_dd']}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--m0_tag", default="m0_fullhist_wf")
    ap.add_argument("--funding_tag", default="fund_ema_fullhist")
    ap.add_argument("--export", default=EXPORT)
    ap.add_argument("--horizon", type=int, default=3600)
    ap.add_argument("--grid_from", choices=["funding", "m0"], default="funding",
                    help="which panel supplies the canonical Y/CL/ts (must be the >=3600-CL panel)")
    ap.add_argument("--validate", action="store_true",
                    help="smoke: also print whole-window numbers to reconcile vs the scorecard")
    a = ap.parse_args()

    # CANONICAL grid = the panel that carries the >=3600 CL. Default = the funding panel (as
    # portfolio_scorecard.py does); --grid_from m0 once the M0 panel_ref exports >=3600 CL.
    # If the funding panel is absent, score M0 STANDALONE (no blend) — requires --grid_from m0.
    Mp = load_panel(a.m0_tag, a.export)
    try:
        Fp = load_panel(a.funding_tag, a.export)
        have_funding = True
    except (FileNotFoundError, OSError, ValueError) as e:
        if a.grid_from != "m0":
            raise SystemExit(f"funding panel '{a.funding_tag}' missing ({e}); rerun with --grid_from m0 to score M0 standalone")
        print(f"[warn] funding panel '{a.funding_tag}' MISSING -> scoring M0 STANDALONE (no funding / no R4 blend)", flush=True)
        Fp = None; have_funding = False
    G, other = (Mp, Fp) if a.grid_from == "m0" else (Fp, Mp)
    Y, CL, ts, day = G["Y"], G["CL"], G["ts"].astype(np.int64), G["day"].astype(np.int64)
    grid_pred = G["pred"]
    if have_funding:
        other_ts = other["ts"].astype(np.int64)
        if other["pred"].shape == grid_pred.shape and np.array_equal(other_ts, ts):
            other_pred = other["pred"]
        else:
            common, i_g, i_o = np.intersect1d(ts, other_ts, return_indices=True)
            print(f"[align] grid ts {len(ts)} vs other ts {len(other_ts)} -> {len(common)} common", flush=True)
            Y, CL, ts, day, grid_pred = Y[i_g], CL[i_g], ts[i_g], day[i_g], grid_pred[i_g]
            other_pred = other["pred"][i_o]
        funding, M0 = (grid_pred, other_pred) if a.grid_from != "m0" else (other_pred, grid_pred)
    else:
        M0 = grid_pred; funding = None

    dense = float(CL.mean())
    print(f"grid={a.grid_from} (funding_tag={a.funding_tag}, m0_tag={a.m0_tag}): T={len(ts)} S={Y.shape[1]} | "
          f"CL frac={dense:.3f}  [>=3600 CL should be ~0.03-0.08; ~0.25 = 720s dense-CL LANDMINE]", flush=True)
    print(f"date range: {dt.datetime.utcfromtimestamp(int(ts[0])/(1e9 if ts[0]>1e17 else 1e3)):%Y-%m-%d} "
          f"-> {dt.datetime.utcfromtimestamp(int(ts[-1])/(1e9 if ts[0]>1e17 else 1e3)):%Y-%m-%d}", flush=True)

    yr = _years(ts)
    comb = blend([funding, M0], Y, CL) if have_funding else None
    per_year_m0 = {}; per_year_blend = {}; per_year_fund = {}
    for y in sorted(np.unique(yr)):
        rows = np.where(yr == y)[0]
        if len(rows) < 50:
            continue
        Yr, CLr, tsr, dayr = _row_subset(Y, rows), _row_subset(CL, rows), _row_subset(ts, rows), _row_subset(day, rows)
        print(f"\n===== YEAR {y}  (n_rows={len(rows)}) =====", flush=True)
        rm0 = _score_one("M0_dl", _row_subset(M0, rows), Yr, CLr, tsr, dayr, a.horizon)
        print(_fmt(rm0), flush=True); per_year_m0[y] = rm0
        if have_funding:
            rfd = _score_one("funding_ema", _row_subset(funding, rows), Yr, CLr, tsr, dayr, a.horizon)
            rbl = _score_one("BLEND (funding+M0)", _row_subset(comb, rows), Yr, CLr, tsr, dayr, a.horizon)
            print(_fmt(rfd), flush=True); print(_fmt(rbl), flush=True)
            per_year_fund[y] = rfd; per_year_blend[y] = rbl

    # ---- pre-registered read summary (R1-R4) ----
    def _collect(d, key):
        return [d[y][key] for y in sorted(d) if d[y] is not None and d[y].get(key) is not None]
    def _nsh5(d):
        return [d[y]["net_sh"][5.0] for y in sorted(d) if d[y] and d[y]["net_sh"].get(5.0) is not None]
    print("\n" + "=" * 70)
    print("PRE-REGISTERED READ (R1-R5) — see docs/2026-07-09_M0_fullhistory_replay_prereg.md")
    m0_ic = _collect(per_year_m0, "ic"); m0_z = _collect(per_year_m0, "z"); m0_n5 = _nsh5(per_year_m0)
    print(f"  M0 per-year IC   : {[round(x,4) for x in m0_ic]}  (mean {np.mean(m0_ic):+.4f} median {np.median(m0_ic):+.4f})")
    print(f"  M0 per-year z    : {m0_z}")
    print(f"  M0 net-Sh@5bps   : {m0_n5}  (mean {np.mean(m0_n5):+.2f} median {np.median(m0_n5):+.2f})")
    if have_funding:
        bl_n5 = _nsh5(per_year_blend)
        print(f"  BLEND net-Sh@5bps: {bl_n5}  (mean {np.mean(bl_n5):+.2f} median {np.median(bl_n5):+.2f})")
    else:
        print(f"  BLEND net-Sh@5bps: (funding panel absent — R4 pending fund_ema_fullhist)")
    print(f"  R1 regime-robust : IC z>=2.5 all years? {all(z>=2.5 for z in m0_z)} | sign-consistent+? {all(x>0 for x in m0_ic)}")
    if 2024 in per_year_m0 and per_year_m0[2024]:
        m24 = per_year_m0[2024]["net_sh"].get(5.0)
        f24 = per_year_fund.get(2024, {}).get("net_sh", {}).get(5.0) if per_year_fund.get(2024) else None
        b24 = per_year_blend.get(2024, {}).get("net_sh", {}).get(5.0) if per_year_blend.get(2024) else None
        print(f"  R2 DIVERSIFY 2024: M0 net-Sh@5={m24}  funding net-Sh@5={f24}  BLEND net-Sh@5={b24}  "
              f"-> {'M0 net-POSITIVE in 2024 (decisive diversification test)' if (m24 or -9)>0 else 'M0 net-negative 2024'}")
    print("=" * 70)

    if a.validate:
        print("\n[VALIDATE] whole-window (reconcile vs scorecard: M0 IC~0.0355, blend net-Sh@2~4.56):")
        sigs = [("M0_dl", M0)] + ([("funding_ema", funding), ("BLEND", comb)] if have_funding else [])
        for nm, sig in sigs:
            r = _score_one(nm, sig, Y, CL, ts, day, a.horizon)
            print(_fmt(r))
        print("  latency M0:", latency(M0, Y, CL, ts, a.horizon))
    print("DONE_M0_REPLAY_SCORE")


if __name__ == "__main__":
    main()
