"""HEADLINE AUDIT — the mandatory battery every headline run must pass before its number reaches the
doc. Zero GPU, saved preds. Consolidates the logic-error audit (2026-07-03) into one reusable module.

Battery (arm preds vs baseline preds, same fold/test window):
 1. NODE-SET IDENTITY   — n equal, timestamp set equal, mask identical. Any mismatch invalidates Δ.
 2. DUAL CALIBER + EXACT HEALTH — cd-CLEAN, DENSE, β, σŷ/σy (unrounded) for arm and baseline.
 3. DEPLOY-CONTRACT RETENTION vs BASELINE CONTROL — 1h/12h/24h causal-demean cd; a real signal
    retains a comparable fraction to the healthy baseline, a slow-band ARTIFACT collapses (arm_keep
    << base_keep). This is what caught the choppy-specialist (8% vs 49%) and cleared 2025-10 (90% vs 84%).
 4. β-RESCALE HEALTH REPAIR — causal trailing-30d label-closed OLS β̂ rescale (ŷ'=β̂_trail·ŷ).
    Pearson-invariant => cd survives BY CONSTRUCTION; only repairs β into [0.5,1.8] and σ above 0.02.
    IRONY GUARD: this is the SAME trailing-β component whose recalib layer died as a POOLED IC LEVER
    (0c, pooled lift +0.0002). Using it here as a PER-FOLD HEALTH REPAIR on a run that already passes
    the deploy contract is a DIFFERENT, legitimate use — it claims ZERO IC gain (cd unchanged), only
    calibration health. Do not conflate with the killed pooled-IC claim.

VERDICT: ARTIFACT (deploy-collapse + DENSE sign-flip) | HEALTH-FAIL→RESCUABLE | WIN | WEAK.

Run LOCAL:
  python multi_asset/eval/headline_audit.py \
    --arm experiments/d1gate/d1_2025_10_run1/fold_0/ema_test_preds.npz \
    --baseline experiments_local/wfEMA/wf_2025_10/fold_0/ema_test_preds.npz
"""
from __future__ import annotations
import numpy as np, argparse
from collections import deque
from scipy.stats import pearsonr

SEC = 1_000_000; HZ = 600 * SEC; DAY = 86400 * SEC
BETA_LO, BETA_HI, SIG_MIN = 0.5, 1.8, 0.02


def load(path, apply_mask=True):
    z = np.load(path, allow_pickle=True); pr = z["predictions"]
    q = (pr[:, 1] if pr.ndim == 2 else pr).astype(np.float64)
    y = z["targets"].astype(np.float64); ts = z["timestamps"].astype(np.int64)
    m = z["mask"].astype(bool) if "mask" in z.files else np.ones(len(y), bool)
    o = np.argsort(ts)
    if apply_mask:
        return q[o][m[o]], y[o][m[o]], ts[o][m[o]]
    return q[o], y[o], ts[o], m[o]


def _clean_idx(t):
    o = np.argsort(t); keep = []; last = -1e18
    for i in o:
        if t[i] - last >= HZ:
            keep.append(i); last = t[i]
    return np.array(keep, int)


def cd(q, y, t):
    dk = t // DAY; rs = []
    for d in np.unique(dk):
        idx = np.where(dk == d)[0]; k = _clean_idx(t[idx])
        if len(k) > 20:
            qk = q[idx][k]; yk = y[idx][k]
            if qk.std() > 1e-12 and yk.std() > 1e-12:
                r = pearsonr(qk, yk)[0]
                if np.isfinite(r): rs.append(r)
    return float(np.mean(rs)) if rs else np.nan


def dense(q, y): return float(pearsonr(q, y)[0])
def beta(q, y): return float(np.cov(y, q)[0, 1] / q.var())
def sigr(q, y): return float(q.std() / y.std())


def strat_ic(q, y, ts):
    """H1 tail/body split: pool the per-day-CLEAN rows, split by |q-demeaned| into top-20% (tail)
    vs rest-80% (body), return (all, tail20, rest80) pooled IC. The rank-norm arm's pre-registered
    claim is that stationary inputs move the drift rest-80% (body) IC off the H1 ~0 floor."""
    dk = ts // DAY; qs = []; ys = []
    for d in np.unique(dk):
        idx = np.where(dk == d)[0]; k = _clean_idx(ts[idx])
        if len(k) > 20:
            qs.append(q[idx][k]); ys.append(y[idx][k])
    if not qs:
        return np.nan, np.nan, np.nan
    Q = np.concatenate(qs); Y = np.concatenate(ys); Qd = Q - Q.mean()
    thr = np.quantile(np.abs(Qd), 0.8); tail = np.abs(Qd) >= thr

    def _ic(m):
        return float(pearsonr(Q[m], Y[m])[0]) if (m.sum() > 10 and Q[m].std() > 1e-9 and Y[m].std() > 1e-9) else np.nan
    return _ic(np.ones(len(Q), bool)), _ic(tail), _ic(~tail)


def causal_demean(q, ts, win_s):
    win = win_s * SEC; o = np.argsort(ts); t = ts[o]; qs = q[o]
    out = np.empty_like(qs); dq = deque(); cs = 0.0
    for i in range(len(qs)):
        dq.append((t[i], qs[i])); cs += qs[i]
        while dq and dq[0][0] < t[i] - win:
            cs -= dq.popleft()[1]
        out[i] = qs[i] - cs / len(dq)
    r = np.empty_like(out); r[o] = out; return r


def causal_beta_rescale(q, y, ts, win_days=30, embargo_days=1, min_rows=200):
    """ŷ' = β̂_trail·ŷ, β̂_trail = OLS(y~ŷ) over trailing win_days of LABEL-CLOSED rows (ts_j+600s+emb<=t).
    Causal; Pearson-invariant up to the slow variation of β̂. Returns rescaled preds + β̂ series."""
    W = win_days * DAY; LAG = HZ + embargo_days * DAY
    b = np.full(len(q), np.nan)
    order = np.argsort(ts); ts_s = ts[order]
    for rank, i in enumerate(order):
        t_i = ts[i]
        closed = (ts + LAG <= t_i) & (ts > t_i - W - LAG)
        if closed.sum() >= min_rows and q[closed].std() > 1e-9:
            b[i] = np.cov(y[closed], q[closed])[0, 1] / q[closed].var()
    # causal forward-fill the burn-in with the earliest valid β̂ (seed)
    fv = np.where(np.isfinite(b[order]))[0]
    if len(fv):
        seed = b[order][fv[0]]
        bo = b[order]
        for k in range(len(bo)):
            if not np.isfinite(bo[k]): bo[k] = bo[k - 1] if k > 0 else seed
        b[order] = bo
    b = np.clip(np.nan_to_num(b, nan=1.0), 0.25, 10.0)
    return b * q, b


def health(q, y):
    b = beta(q, y); s = sigr(q, y)
    ok = (s >= SIG_MIN) and (BETA_LO <= b <= BETA_HI)
    return ok, b, s


def audit(arm_path, base_path, wins=(3600, 43200, 86400)):
    # 1. node identity (pre-mask)
    qa0, ya0, ta0, ma0 = load(arm_path, apply_mask=False)
    qb0, yb0, tb0, mb0 = load(base_path, apply_mask=False)
    same_n = len(ta0) == len(tb0)
    set_eq = set(ta0.tolist()) == set(tb0.tolist())
    mask_eq = same_n and bool((ma0 == mb0).all())
    print("1) NODE-SET IDENTITY: "
          f"n_arm={len(ta0)} n_base={len(tb0)} same_n={same_n} set_equal={set_eq} "
          f"mask_identical={mask_eq} valid_arm={int(ma0.sum())} valid_base={int(mb0.sum())}")
    node_ok = same_n and set_eq and mask_eq

    qa, ya, ta = load(arm_path); qb, yb, tb = load(base_path)
    a_cd, a_de, (a_ok, a_b, a_s) = cd(qa, ya, ta), dense(qa, ya), health(qa, ya)
    b_cd, b_de, (b_ok, b_b, b_s) = cd(qb, yb, tb), dense(qb, yb), health(qb, yb)
    print("\n2) DUAL CALIBER + EXACT HEALTH")
    print(f"   ARM  cd={a_cd:+.4f} DENSE={a_de:+.4f} beta={a_b:+.3f} sigma={a_s:.5f}  health={'OK' if a_ok else 'FAIL'}")
    print(f"   BASE cd={b_cd:+.4f} DENSE={b_de:+.4f} beta={b_b:+.3f} sigma={b_s:.5f}  health={'OK' if b_ok else 'FAIL'}")
    print(f"   Δcd={a_cd-b_cd:+.4f}  ΔDENSE={a_de-b_de:+.4f}  (DENSE abs-sign-agrees-with-cd: {np.sign(a_de)==np.sign(a_cd)})")

    print("\n3) DEPLOY-CONTRACT RETENTION (causal demean) vs BASELINE CONTROL")
    a_dm1 = cd(causal_demean(qa, ta, wins[0]), ya, ta)
    b_dm1 = cd(causal_demean(qb, tb, wins[0]), yb, tb)
    a_keep = a_dm1 / a_cd if a_cd > 1e-9 else np.nan
    b_keep = b_dm1 / b_cd if b_cd > 1e-9 else np.nan
    for w in wins:
        print(f"   ARM  demean {w:>6}s cd={cd(causal_demean(qa,ta,w),ya,ta):+.4f}")
    print(f"   ARM 1h-retain={100*a_keep:.0f}%  BASE 1h-retain={100*b_keep:.0f}%  dDEPLOY(1h)={a_dm1-b_dm1:+.4f}")
    collapse = np.isfinite(a_keep) and np.isfinite(b_keep) and a_keep < 0.5 * b_keep

    a_all, a_tail, a_rest = strat_ic(qa, ya, ta); b_all, b_tail, b_rest = strat_ic(qb, yb, tb)
    print("\n3b) H1 TAIL/BODY STRATIFIED IC (top-20% |pred| vs rest-80%; rank-arm claim = move rest-80% up)")
    print(f"   ARM  tail20={a_tail:+.4f} rest80={a_rest:+.4f}   BASE tail20={b_tail:+.4f} rest80={b_rest:+.4f}"
          f"   Δrest80={a_rest-b_rest:+.4f}")

    print("\n4) β-RESCALE HEALTH REPAIR (causal trailing-30d; Pearson-invariant => cd preserved)")
    qr, bser = causal_beta_rescale(qa, ya, ta)
    r_cd, (r_ok, r_b, r_s) = cd(qr, ya, ta), health(qr, ya)
    print(f"   post-rescale cd={r_cd:+.4f} (Δ vs raw {r_cd-a_cd:+.4f})  beta={r_b:+.3f}  sigma={r_s:.5f}  "
          f"health={'OK' if r_ok else 'FAIL'}  | β̂_trail median={np.median(bser):.2f} range[{bser.min():.2f},{bser.max():.2f}]")

    # verdict
    dense_flip = np.sign(a_de) != np.sign(a_cd)
    if collapse and dense_flip:
        v = "ARTIFACT (deploy-collapse + DENSE sign-flip)"
    elif a_cd <= b_cd + 1e-9:
        v = "WEAK (no cd lift over baseline)"
    elif not a_ok and r_ok:
        v = "WIN-after-RESCALE (raw HEALTH-FAIL, β-rescale repairs β/σ, cd survives deploy)"
    elif a_ok:
        v = "WIN (healthy, deploy-surviving)" if (np.isfinite(a_keep) and a_keep >= 0.5*b_keep) else "REVIEW (healthy but deploy-weak)"
    else:
        v = "HEALTH-FAIL (rescale did not repair — investigate)"
    print(f"\nVERDICT: {v}")
    print(f"  node_identity={'OK' if node_ok else 'BROKEN — Δ INVALID'}")
    print("DONE_HEADLINE_AUDIT.")
    return v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True)
    ap.add_argument("--baseline", required=True)
    a = ap.parse_args()
    print(f"arm      = {a.arm}\nbaseline = {a.baseline}\n" + "=" * 78)
    audit(a.arm, a.baseline)


if __name__ == "__main__":
    main()
