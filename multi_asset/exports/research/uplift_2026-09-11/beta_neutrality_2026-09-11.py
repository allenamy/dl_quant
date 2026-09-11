#!/usr/bin/env python3
"""READ-ONLY. Axis: is the live book beta-neutral, and what caused the big loss days?
Instruments:
  positions  = dl_quant_live/state/live/pilot_log/*/position_readback.jsonl (venue_position_notional, post-anchor)
  prices(book)= anchors.jsonl mid_at_anchor_vector  [VERIFIED empirically = snapshot at anchor+30min, see ALIGN below]
  prices(idx) = wide_shadow/state/rolling.npz ch0 = 5m SIMPLE return (clip +-0.3), 829-name panel, 08-02 04:05Z..09-11 04:00Z
  caliber     = SUM of 5m simple returns over the same +30min-shifted 4h window (E-0904-F lineage: no expm1)
No venue API. No writes outside exports/research/uplift_2026-09-11/.
"""
import json, glob, os, time, collections, sys
import numpy as np

OUT = os.path.dirname(os.path.abspath(__file__))
LIVE = os.path.expanduser("~/dl_quant_live/state/live")
WS = os.path.expanduser("~/wide_shadow")
OFF_BARS = 6            # mid_at_anchor_vector snapshot offset, VERIFIED by offset scan (corr peak 0.982 @ +6 bars)
H = 14400

def utc(t, f="%m-%d %HZ"): return time.strftime(f, time.gmtime(int(t)))
def jl(p):
    out = []
    for l in open(p, errors="ignore"):
        l = l.strip()
        if not l: continue
        try: out.append(json.loads(l))
        except Exception: pass
    return out

# ---------- panel ----------
z = np.load(f"{WS}/state/rolling.npz", allow_pickle=True)
PTS = z["ts"].astype(np.int64); R5 = z["data"][:, :, 0].astype(np.float32)
cfg = json.load(open(f"{WS}/shadow_bundle/config.json"))
SP = cfg["symbols_panel"]; LIVEU = set(cfg["symbols_live"])
IDX = {s: i for i, s in enumerate(SP)}
TPOS = {int(t): i for i, t in enumerate(PTS)}
LIVE_COLS = np.array([IDX[s] for s in cfg["symbols_live"]])
BIG = {"BTCUSDT", "ETHUSDT"}
ALT_COLS = np.array([IDX[s] for s in cfg["symbols_live"] if s not in BIG])
BTC = IDX["BTCUSDT"]

def win(a, off=OFF_BARS):
    i0 = TPOS.get(a + off * 300); i1 = TPOS.get(a + H + off * 300 - 300)
    if i0 is None or i1 is None: return None
    return R5[i0:i1 + 1]

def panel_ret(a, off=OFF_BARS):
    """4h simple-sum return per panel name; NaN where any 5m bar missing."""
    b = win(a, off)
    if b is None: return None
    bad = np.isnan(b).any(axis=0)
    r = np.nansum(b, axis=0).astype(np.float64); r[bad] = np.nan
    return r

# ---------- ledger ----------
mid = {}; anch = {}
for p in sorted(glob.glob(f"{LIVE}/pilot_log/2026*/anchors.jsonl")):
    for r in jl(p):
        a = int(round(float(r["anchor_ts"]) / H) * H)
        mv = r.get("mid_at_anchor_vector"); mv = json.loads(mv) if isinstance(mv, str) else mv
        if mv: mid[a] = {s: float(v) for s, v in mv.items() if v}
        anch[a] = r
pos = collections.defaultdict(dict)
for p in sorted(glob.glob(f"{LIVE}/pilot_log/2026*/position_readback.jsonl")):
    for r in jl(p):
        a = int(round(float(r["anchor_ts"]) / H) * H)
        n = r.get("venue_position_notional")
        if n is not None and abs(float(n)) > 0: pos[a][r["symbol"]] = float(n)

ANCH = sorted(a for a in pos if a in mid and a + H in mid and panel_ret(a) is not None)

rows = []
for a in ANCH:
    m0, m1 = mid[a], mid[a + H]
    pr = panel_ret(a)
    gross = sum(abs(v) for v in pos[a].values()); net = sum(pos[a].values())
    pl = lp = sp_ = 0.0; covered = 0.0; per = []
    for s, n in pos[a].items():
        if s in m0 and s in m1 and m0[s] > 0:
            r = m1[s] / m0[s] - 1.0
            u = n * r; pl += u; covered += abs(n); per.append((s, n, r, u))
            if n > 0: lp += u
            else: sp_ += u
    alt = float(np.nanmean(pr[ALT_COLS])); altn = int(np.isfinite(pr[ALT_COLS]).sum())
    altmed = float(np.nanmedian(pr[ALT_COLS]))
    breadth = float(np.nanmean(pr[ALT_COLS] > 0))
    btc = float(pr[BTC])
    gl = sum(n for s, n, r, u in per if n > 0); gs = -sum(n for s, n, r, u in per if n < 0)
    rows.append(dict(a=a, gross=gross, net=net, ng=net / gross if gross else 0.0,
                     covered=covered, cov_frac=covered / gross if gross else 0.0,
                     pl=pl, lp=lp, sp=sp_, gl=gl, gs=gs,
                     bps=pl / gross * 1e4 if gross else 0.0,
                     lbps=lp / gl * 1e4 if gl else 0.0, sbps=sp_ / gs * 1e4 if gs else 0.0,
                     alt=alt, altmed=altmed, altn=altn, breadth=breadth, btc=btc,
                     n=len(per), per=per,
                     ng_ledger=anch.get(a, {}).get("net_over_gross"),
                     regime=anch.get(a, {}).get("regime_at_anchor")))

print(f"== ALIGN: mid_at_anchor_vector offset = +{OFF_BARS} bars (+30min); anchors usable n={len(rows)} {utc(rows[0]['a'])}..{utc(rows[-1]['a'])}")
print(f"   mean position coverage by mid vector = {np.mean([r['cov_frac'] for r in rows]):.4f}")

def seg(lo, hi): return [r for r in rows if lo <= r["a"] <= hi]
def T(*x):
    import calendar; return calendar.timegm(x + (0,) * (6 - len(x)))

PERIODS = [("whole live 08-02..09-11", rows[0]["a"], rows[-1]["a"]),
           ("pre-combo 08-02..08-26 00Z", rows[0]["a"], T(2026, 8, 26, 0)),
           ("combo era 08-26 04Z..", T(2026, 8, 26, 4), rows[-1]["a"]),
           ("post-deposit 09-03 16Z..", T(2026, 9, 3, 16), rows[-1]["a"])]

def ols(y, X):
    X = np.column_stack([np.ones(len(y))] + list(X))
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ b
    dof = max(len(y) - X.shape[1], 1)
    s2 = resid @ resid / dof
    cov = s2 * np.linalg.pinv(X.T @ X)
    se = np.sqrt(np.diag(cov))
    return b, se, 1 - resid @ resid / ((y - y.mean()) @ (y - y.mean()))

print("\n== [1] REALIZED BETA of the live book (per anchor, book return in bps of gross vs index return in bps)")
print("%-28s %4s %9s %9s %9s %9s %9s %9s" % ("period", "n", "b_alt", "se", "b_btc", "se", "alpha_bps", "R2"))
BETAS = {}
for lab, lo, hi in PERIODS:
    rs = seg(lo, hi)
    if len(rs) < 10: continue
    y = np.array([r["bps"] for r in rs]); xa = np.array([r["alt"] for r in rs]) * 1e4; xb = np.array([r["btc"] for r in rs]) * 1e4
    b, se, r2 = ols(y, [xa, xb])
    b1, se1, r21 = ols(y, [xa])
    BETAS[lab] = dict(b_alt_uni=b1[1], se_alt_uni=se1[1], a_uni=b1[0], r2_uni=r21, b_alt=b[1], b_btc=b[2], a=b[0], r2=r2, n=len(rs))
    print("%-28s %4d %9.4f %9.4f %9.4f %9.4f %9.3f %9.3f" % (lab, len(rs), b[1], se[1], b[2], se[2], b[0], r2))
print("  univariate vs altEW only:")
for lab in BETAS:
    d = BETAS[lab]; print("    %-28s b_alt=%+.4f (se %.4f, t %+.2f)  alpha=%+.3f bps/anchor  R2=%.3f" % (lab, d["b_alt_uni"], d["se_alt_uni"], d["b_alt_uni"] / d["se_alt_uni"], d["a_uni"], d["r2_uni"]))

print("\n== [2] HALF-BOOK betas (long half return per unit long gross; short half per unit short gross; both vs altEW)")
print("%-28s %4s %10s %10s %10s %10s %10s %10s" % ("period", "n", "bL_alt", "t", "bS_alt", "t", "corrL", "corrS"))
for lab, lo, hi in PERIODS:
    rs = seg(lo, hi)
    if len(rs) < 10: continue
    xa = np.array([r["alt"] for r in rs]) * 1e4
    yl = np.array([r["lbps"] for r in rs]); ys = np.array([r["sbps"] for r in rs])
    bl, sel, _ = ols(yl, [xa]); bs, ses, _ = ols(ys, [xa])
    print("%-28s %4d %10.4f %10.2f %10.4f %10.2f %10.3f %10.3f" % (lab, len(rs), bl[1], bl[1] / sel[1], bs[1], bs[1] / ses[1],
          np.corrcoef(yl, xa)[0, 1], np.corrcoef(ys, xa)[0, 1]))

print("\n== [3] P&L by half (USDT, mid-to-mid price P&L only; funding & commission excluded)")
print("%-28s %4s %12s %12s %12s %10s %10s" % ("period", "n", "total", "long half", "short half", "L bps/a", "S bps/a"))
for lab, lo, hi in PERIODS:
    rs = seg(lo, hi)
    if not rs: continue
    print("{:<28s} {:4d} {:+12,.0f} {:+12,.0f} {:+12,.0f} {:+10.2f} {:+10.2f} | altEW {:+7.2f} bps/a  BTC {:+7.2f}".format(lab, len(rs), sum(r["pl"] for r in rs), sum(r["lp"] for r in rs), sum(r["sp"] for r in rs), np.mean([r["lbps"] for r in rs]), np.mean([r["sbps"] for r in rs]), np.mean([r["alt"] for r in rs])*1e4, np.mean([r["btc"] for r in rs])*1e4))

json.dump({"rows": [{k: v for k, v in r.items() if k != "per"} for r in rows]},
          open(f"{OUT}/beta_neutrality_anchor_rows.json", "w"), indent=0, default=float)

# ---------- ex-ante per-name beta and book dollar-beta ----------
print("\n== [4] EX-ANTE dollar-beta vs dollar-net  (per-name beta to altEW from trailing 4h returns, 30d window)")
grid = sorted(set(int(t) for t in PTS if (int(t) - 0) % H == 0))
allret = {}
for g in grid:
    pr = panel_ret(g)
    if pr is not None: allret[g] = pr
gk = sorted(allret)
print(f"   panel 4h-return grid n={len(gk)} {utc(gk[0])}..{utc(gk[-1])}")
def name_betas(upto, lookback=180):
    ks = [t for t in gk if t < upto][-lookback:]
    if len(ks) < 40: return None
    M = np.array([allret[t] for t in ks])                     # (n, 829)
    alt = np.nanmean(M[:, ALT_COLS], axis=1)
    av = alt - alt.mean()
    den = float(av @ av)
    B = np.full(M.shape[1], np.nan)
    for j in range(M.shape[1]):
        col = M[:, j]; ok = np.isfinite(col)
        if ok.sum() < 30: continue
        c = col[ok] - col[ok].mean(); aa = alt[ok] - alt[ok].mean()
        d = float(aa @ aa)
        if d > 0: B[j] = float(c @ aa) / d
    return B
BCACHE = {}
out4 = []
for r in rows:
    day = int(r["a"]) // 86400 * 86400
    if day not in BCACHE: BCACHE[day] = name_betas(day)
    B = BCACHE[day]
    if B is None: continue
    dbeta = 0.0; used = 0.0
    for s, n in pos[r["a"]].items():
        j = IDX.get(s)
        if j is None or not np.isfinite(B[j]): continue
        dbeta += n * B[j]; used += abs(n)
    r["dbeta"] = dbeta; r["dbeta_g"] = dbeta / r["gross"]; r["beta_cov"] = used / r["gross"]
    out4.append(r)
db = np.array([r["dbeta_g"] for r in out4]); ng = np.array([r["ng"] for r in out4])
print(f"   anchors with beta est n={len(out4)}, mean name coverage {np.mean([r['beta_cov'] for r in out4]):.3f}")
print(f"   dollar-net/gross:  mean {ng.mean()*100:+.3f}%  sd {ng.std()*100:.3f}%  |max| {np.abs(ng).max()*100:.3f}%")
print(f"   beta-net/gross:    mean {db.mean()*100:+.3f}%  sd {db.std()*100:.3f}%  |max| {np.abs(db).max()*100:.3f}%")
print(f"   corr(dollar-net, beta-net) = {np.corrcoef(ng, db)[0,1]:+.3f}")
print(f"   share of anchors |dollar-net|>1.5%: {np.mean(np.abs(ng)>0.015):.3f}   |beta-net|>1.5%: {np.mean(np.abs(db)>0.015):.3f}")
print(f"   share of anchors |beta-net|>3%: {np.mean(np.abs(db)>0.03):.3f}  >5%: {np.mean(np.abs(db)>0.05):.3f}")
# how much P&L does the ex-ante beta explain?
y = np.array([r["bps"] for r in out4]); alt = np.array([r["alt"] for r in out4]) * 1e4
pred = db * alt
print(f"   ex-ante beta P&L contribution: mean {pred.mean():+.3f} bps/anchor (book mean {y.mean():+.3f}); sum over window {np.sum(pred*np.array([r['gross'] for r in out4])/1e4):+,.0f} USDT")
b, se, r2 = ols(y - pred, [alt])
print(f"   residual (book - ex-ante-beta*alt) regressed on alt: b={b[1]:+.4f} (t {b[1]/se[1]:+.2f}), alpha={b[0]:+.3f} bps/anchor")
json.dump([{k: v for k, v in r.items() if k != "per"} for r in out4], open(f"{OUT}/beta_exante_rows.json", "w"), indent=0, default=float)
print("DONE_PART1")
