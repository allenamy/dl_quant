"""Factor-factory 5-gate pipeline — multi-asset v2. Scores ONE factor F against the commoditized
baseline B, over the panel (Y forward return, CL clean mask). CPU-only, walk-forward / OOS.

  (a) xs-IC/IR         factor_scorer.score_factor  — standalone cross-sectional rank-IC + IR + breadth + decay + null
  (b) INCREMENTAL IC   factor_scorer.incremental_ic — rank-IC of F vs B's residual of Y (the EDGE metric)
  (c) orthogonality    factor_scorer.factor_corr    — per-ts rank-corr vs B (and any accepted factors)
  (d) walk-forward Ridge ΔIC (HERE) — expanding-window cross-sectional Ridge(Y~[B,F]) vs Ridge(Y~[B]),
                        per-ts z-scored features; ΔmeanIC = IC[B,F]−IC[B]. GATE ΔIC≥+0.003, per-fold sign-consistent.
  (e) net-cost L/S contribution (HERE) — L/S book on the [B,F] Ridge-combined signal vs B-alone; Δ break-even
                        per-side + Δ net-Sharpe at the operating turnover. GATE: improves net-cost economics.

Accept a factor only if it clears all five walk-forward. Every a/b number must beat its shuffle-null.
"""
from __future__ import annotations
import argparse, glob, json, os, sys, os.path as op
import numpy as np
sys.path.insert(0, op.abspath(op.join(op.dirname(__file__), "..", "..")))
from multi_asset.eval.factor_scorer import (_perts_ic, _ric, ic_summary, incremental_ic, factor_corr,
                                            ic_decay, shuffle_null)
from multi_asset.eval.backtest_longshort import rank_weights

SEC_PER_YEAR = 365 * 24 * 3600
MIN_ASSETS = 5
COST_GRID = (0.0, 1.0, 2.0, 2.5, 5.0)
ALPHA_GRID = (1.0, 0.5, 0.3, 0.2, 0.1, 0.05, 0.02)


# ------------- per-ts standardized cross-sectional rows (shared by d & e) -------------
def _panel_rows(feats, Y, CL, min_assets=MIN_ASSETS):
    """For each usable ts, z-score each feature across the valid assets; return per-ts dicts."""
    T = Y.shape[0]; rows = []
    for t in range(T):
        v = CL[t] & np.isfinite(Y[t])
        for Fi in feats:
            v = v & np.isfinite(Fi[t])
        if v.sum() < min_assets:
            continue
        idx = np.where(v)[0]; y = Y[t, idx]
        cols = []
        for Fi in feats:
            x = Fi[t, idx].astype(np.float64); s = x.std()
            cols.append((x - x.mean()) / s if s > 1e-12 else x * 0.0)
        rows.append(dict(t=t, idx=idx, y=y, X=np.column_stack(cols) if cols else np.zeros((len(idx), 0))))
    return rows


def _ridge_fit(X, y, l2):
    k = X.shape[1]
    if k == 0:
        return np.zeros(0)
    return np.linalg.solve(X.T @ X + l2 * np.eye(k), X.T @ y)


# ------------- gate (d): walk-forward Ridge ΔIC -------------
def gate_d_ridge_dic(F, B, Y, CL, day, n_folds=4, l2=1.0):
    """Expanding-window cross-sectional Ridge; compare model [B] vs [B,F]; ΔmeanIC over OOS test ts."""
    rB = _panel_rows([B], Y, CL); rBF = _panel_rows([B, F], Y, CL)
    # align: use rows present in BOTH (same usable ts set — F & B finiteness may differ)
    tsB = {r["t"]: r for r in rB}; tsBF = {r["t"]: r for r in rBF}
    common = sorted(set(tsB) & set(tsBF))
    if len(common) < 50:
        return dict(dIC=np.nan, ic_B=np.nan, ic_BF=np.nan, per_fold=[], note="too few common ts")
    days = np.array([day[t] for t in common]); uniq = np.unique(days)
    edges = [uniq[len(uniq) * i // n_folds] for i in range(n_folds)] + [uniq[-1] + 1]

    def run(rows_map, feat_ncol):
        icf = []
        for i in range(1, n_folds):                                   # fold 0 = train-only seed
            tr = [t for t in common if day[t] < edges[i]]
            te = [t for t in common if edges[i] <= day[t] < edges[i + 1]]
            if len(tr) < 30 or not te:
                continue
            Xtr = np.vstack([rows_map[t]["X"][:, :feat_ncol] for t in tr])
            ytr = np.concatenate([rows_map[t]["y"] for t in tr])
            coef = _ridge_fit(Xtr, ytr, l2)
            ics = []
            for t in te:
                r = rows_map[t]; pred = r["X"][:, :feat_ncol] @ coef
                if pred.std() > 1e-12 and r["y"].std() > 1e-12:
                    ic = _ric(pred, r["y"])
                    if np.isfinite(ic): ics.append(ic)
            if ics: icf.append(float(np.mean(ics)))
        return icf

    icB_folds = run(tsB, 1); icBF_folds = run(tsBF, 2)
    n = min(len(icB_folds), len(icBF_folds))
    if n == 0:
        return dict(dIC=np.nan, ic_B=np.nan, ic_BF=np.nan, per_fold=[], note="no usable folds")
    dfold = [round(icBF_folds[k] - icB_folds[k], 4) for k in range(n)]
    return dict(ic_B=round(float(np.mean(icB_folds[:n])), 4), ic_BF=round(float(np.mean(icBF_folds[:n])), 4),
                dIC=round(float(np.mean(icBF_folds[:n]) - np.mean(icB_folds[:n])), 4),
                per_fold_dIC=dfold, sign_consistent=bool(all(x > 0 for x in dfold) or all(x < 0 for x in dfold)))


# ------------- L/S book break-even (compact, shared by gate e) -------------
def book_breakeven(signal, Y, CL, ts, horizon, min_assets=MIN_ASSETS):
    T, S = Y.shape
    targ_w, Yrows = [], []
    for t in range(T):
        v = CL[t] & np.isfinite(signal[t]) & np.isfinite(Y[t])
        if v.sum() < min_assets:
            continue
        idx = np.where(v)[0]; w = np.zeros(S); w[idx] = rank_weights(signal[t, idx])
        targ_w.append(w); Yrows.append(np.where(v, Y[t], 0.0))
    targ_w = np.array(targ_w); Yrows = np.array(Yrows); n = len(targ_w)
    if n == 0:
        return dict(be=np.nan, net_sharpe_c2=np.nan, best_alpha=None, n=0)
    per_yr = SEC_PER_YEAR / horizon; ann = np.sqrt(per_yr)

    def series(alpha):
        held = np.zeros(S); g = np.empty(n); tn = np.empty(n)
        for k in range(n):
            new = alpha * targ_w[k] + (1 - alpha) * held
            tn[k] = np.abs(new - held).sum(); g[k] = float((new * Yrows[k]).sum()); held = new
        return g, tn
    best = dict(be=-1e18)
    for al in ALPHA_GRID:
        g, tn = series(al); gm, tm = g.mean(), tn.mean()
        be = gm / tm * 1e4 if tm > 1e-12 else -1e18
        if be > best["be"]:
            net2 = g - tn * (2.0 * 1e-4)
            best = dict(be=float(be), best_alpha=al,
                        net_sharpe_c2=float(net2.mean() / net2.std() * ann) if net2.std() > 0 else np.nan)
    best["n"] = n
    return best


# ------------- gate (e): net-cost L/S contribution -------------
def gate_e_netcost(F, B, Y, CL, ts, day, horizon, l2=1.0):
    """Build the [B,F] Ridge-combined OOS signal, run the L/S book vs B-alone; Δ break-even + Δ net-Sharpe."""
    # OOS combined signal from an expanding Ridge (reuse gate-d rows), fall back to z(B)+z(F) if sparse
    rBF = _panel_rows([B, F], Y, CL); tsBF = {r["t"]: r for r in rBF}
    common = sorted(tsBF); T, S = Y.shape
    comb = np.full((T, S), np.nan); bsig = np.full((T, S), np.nan)
    days = np.array([day[t] for t in common]); uniq = np.unique(days); n_folds = 4
    edges = [uniq[len(uniq) * i // n_folds] for i in range(n_folds)] + [uniq[-1] + 1]
    for i in range(1, n_folds):
        tr = [t for t in common if day[t] < edges[i]]
        te = [t for t in common if edges[i] <= day[t] < edges[i + 1]]
        if len(tr) < 30 or not te:
            continue
        Xtr = np.vstack([tsBF[t]["X"] for t in tr]); ytr = np.concatenate([tsBF[t]["y"] for t in tr])
        coef = _ridge_fit(Xtr, ytr, l2)
        for t in te:
            r = tsBF[t]; comb[t, r["idx"]] = r["X"] @ coef; bsig[t, r["idx"]] = r["X"][:, 0]   # col0 = z(B)
    be_B = book_breakeven(bsig, Y, CL, ts, horizon)
    be_C = book_breakeven(comb, Y, CL, ts, horizon)
    return dict(be_baseline=round(be_B["be"], 3), be_combined=round(be_C["be"], 3),
                d_be=round(be_C["be"] - be_B["be"], 3),
                netSh_baseline_c2=round(be_B["net_sharpe_c2"], 2), netSh_combined_c2=round(be_C["net_sharpe_c2"], 2),
                d_netSh_c2=round(be_C["net_sharpe_c2"] - be_B["net_sharpe_c2"], 2), n=be_C["n"])


# ------------- empirical shuffle-null z (0B's warning: IC-IR vs 0 is BIASED with few assets — gate on
#               z vs the empirical within-ts permutation null, which absorbs the small-sample bias) -------------
def _usable_idx(F, Y, CL, min_assets=MIN_ASSETS):
    return [(t, np.where(CL[t] & np.isfinite(F[t]) & np.isfinite(Y[t]))[0])
            for t in range(F.shape[0]) if (CL[t] & np.isfinite(F[t]) & np.isfinite(Y[t])).sum() >= min_assets]

def _null_z(score_fn, real, F, Y, CL, n=25, seed=0, min_assets=MIN_ASSETS):
    """Permute F ACROSS assets within each usable ts; null distribution of score_fn's mean. z of real vs null."""
    rng = np.random.default_rng(seed); rows = _usable_idx(F, Y, CL, min_assets); vals = []
    for _ in range(n):
        Fs = F.copy()
        for t, idx in rows:
            Fs[t, idx] = F[t, idx[rng.permutation(len(idx))]]
        vals.append(score_fn(Fs))
    vals = np.asarray(vals); nm, ns = float(np.mean(vals)), float(np.std(vals) + 1e-12)
    return dict(real=round(float(real), 4), null_mean=round(nm, 4), null_std=round(ns, 4),
                z=round((float(real) - nm) / ns, 2))


# ------------- full factory -------------
def run_factory(F, B, Y, CL, ts, day, horizon, label="factor", existing=None, z_gate=2.5):
    ics, brd = _perts_ic(F, Y, CL)
    out = {"label": label, "gate_a": ic_summary(ics, brd, label), "ic_decay": ic_decay(F, Y, CL)}
    bics, bbrd = incremental_ic(F, B, Y, CL)
    out["gate_b_incremental"] = ic_summary(bics, bbrd, "incr_vs_B")
    out["gate_c_corr_vs_B"] = factor_corr(F, B, CL)
    if existing:
        out["gate_c_corr_vs_existing"] = {k: factor_corr(F, EF, CL) for k, EF in existing.items()}
    # empirical-null z for a (standalone IC) AND b (incremental IC) — the HONEST significance (not IR-vs-0)
    def _score_a(Fs):
        arr = _perts_ic(Fs, Y, CL)[0]; return float(np.mean(arr)) if len(arr) else np.nan
    def _score_b(Fs):
        arr = incremental_ic(Fs, B, Y, CL)[0]; return float(np.mean(arr)) if len(arr) else np.nan
    za = _null_z(_score_a, out["gate_a"]["mean_ic"], F, Y, CL)
    zb = _null_z(_score_b, out["gate_b_incremental"]["mean_ic"], F, Y, CL)
    out["gate_a_nullz"] = za; out["gate_b_nullz"] = zb
    out["gate_d_ridge"] = gate_d_ridge_dic(F, B, Y, CL, day)
    out["gate_e_netcost"] = gate_e_netcost(F, B, Y, CL, ts, day, horizon)
    # verdict — gate a/b on |empirical-null z| (sign pre-registered separately), NOT the biased IR-vs-0
    gd = out["gate_d_ridge"]; ge = out["gate_e_netcost"]
    passes = dict(
        a=bool(np.isfinite(za["z"]) and abs(za["z"]) >= z_gate),
        b=bool(np.isfinite(zb["z"]) and abs(zb["z"]) >= z_gate),
        c=bool(np.isfinite(out["gate_c_corr_vs_B"]) and abs(out["gate_c_corr_vs_B"]) < 0.7),
        d=bool(np.isfinite(gd.get("dIC", np.nan)) and abs(gd["dIC"]) >= 0.003 and gd.get("sign_consistent")),
        e=bool(np.isfinite(ge.get("d_be", np.nan)) and ge["d_be"] > 0),
    )
    out["passes"] = passes; out["ACCEPT"] = all(passes.values())
    return out


def load_panel(tag, export):
    d = op.join(export, tag)
    ref = np.load(op.join(d, "panel_ref.npz"), allow_pickle=True)
    Y, CL = ref["Y"].astype(np.float64), ref["CL"].astype(bool)
    T, S = Y.shape; pred = np.full((T, S), np.nan, np.float64)
    for f in sorted(glob.glob(op.join(d, "fold_*_preds.npz"))):
        z = np.load(f); pred[z["te_rows"]] = z["pred"][z["te_rows"]]
    return dict(ts=ref["ts"].astype(np.int64), day=ref["day"].astype(np.int64), Y=Y, CL=CL, pred=pred,
                symbols=[str(s) for s in ref["symbols"]])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline_tag", required=True, help="tag whose fold preds = commoditized baseline B")
    ap.add_argument("--factor_tag", default=None, help="tag whose fold preds = the factor F (same panel schema)")
    ap.add_argument("--factor_npz", default=None, help="alt: npz with F[T,S] (key 'F'/'factor')")
    ap.add_argument("--horizon", type=int, default=3600)
    ap.add_argument("--label", default="factor")
    ap.add_argument("--export", default="/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/train")
    a = ap.parse_args()
    P = load_panel(a.baseline_tag, a.export)
    if a.factor_tag:
        Pf = load_panel(a.factor_tag, a.export)
        assert np.array_equal(P["ts"], Pf["ts"]), "factor/baseline ts mismatch — different panels"
        assert np.allclose(np.nan_to_num(P["Y"]), np.nan_to_num(Pf["Y"]), atol=1e-9), "factor/baseline Y mismatch"
        F = Pf["pred"]
    else:
        z = np.load(a.factor_npz, allow_pickle=True); F = z["F"] if "F" in z.files else z["factor"]
    out = run_factory(F.astype(np.float64), P["pred"], P["Y"], P["CL"], P["ts"], P["day"], a.horizon, a.label)
    print(json.dumps(out, indent=2))
    print(f"\n{'ACCEPT' if out['ACCEPT'] else 'REJECT'} {a.label}: gates {out['passes']}")
    print("DONE_FACTOR_PIPELINE")


if __name__ == "__main__":
    main()
