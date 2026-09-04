"""units_table.py — gap_units review (READ-ONLY on all inputs; writes only to /workspace/review_scratch/gap_units/).

Prints, for each (form × caliber × arm × period): n, mean net_ex, mean net, mean gross_total, per-gross recipe A/B,
annualised %/gross, 2× gross, Sharpe, max drawdown (NAV bps and gross bps, with peak/trough dates), worst UTC month,
mean w3_king/w3_fund, mean turnover, mean pnl_ex/carry_ex/cost_ex, identity residual.
All numbers printed here come from the npz rec arrays; nothing is hand-computed.

Run:  cd /workspace/review_scratch/gap_units && /workspace/venv/bin/python units_table.py | tee units_table.out
"""
import numpy as np, json, time, calendar, hashlib, os, sys

PORT = "/workspace/port_w10/probe_artifacts"
RS = "/workspace/review_scratch"
DEV = "/workspace/port_w10/w10_universe.py"
META = "/workspace/data/wide_fea_v2ext_meta.npz"      # == /workspace/port_w10/pod_backup_2026-08-21/wide_fea_hist_meta.npz (symlink)
CUT = calendar.timegm(time.strptime("2026-08-10 20:00", "%Y-%m-%d %H:%M"))
ANN = 2190.0            # 4h anchors per year (6/day × 365)
NW = 829


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()[:16]


def d(ts):
    return time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(ts)))


def ym(ts):
    return time.strftime("%Y-%m", time.gmtime(int(ts)))


print("SELF_SHA256", sha(os.path.abspath(__file__)))
print("DEVICE", DEV, "sha256[:16]", sha(DEV))
print("META", META, "sha256[:16]", sha(META), "-> realpath of port pod_backup meta:", os.path.realpath("/workspace/port_w10/pod_backup_2026-08-21/wide_fea_hist_meta.npz"))
print("CUT (2026<=08-10 20:00Z) epoch", CUT, "=", d(CUT))
print()

# ---------------------------------------------------------------- device line receipts (printed from the file itself)
LINES = open(DEV).read().split("\n")


def show(lo, hi):
    for k in range(lo, hi + 1):
        print(f"  L{k}: {LINES[k - 1]}")


print("=" * 100)
print("DEVICE LINE RECEIPTS (w10_universe.py)")
print("=" * 100)
print("-- caliber switch (CAL) and W3FIX / MEMBERS_TOPN / FTRIM / TRADE_TOPN whitelists")
show(17, 20); show(27, 31); show(41, 42)
print("-- COST_B cost model + tier_of")
show(116, 119)
print("-- qv4h (4h quote-volume proxy used by tier_of) and sel gate")
show(198, 201)
print("-- stop layer: run(SLOW, LRa, pos, depth, need, cool); depth=None => S0 (no stop); tgt[bl]=0 while a name is suspended; fires when avg-cost depth <= depth for `need` consecutive anchors, cool-off `cool` anchors")
show(145, 145); show(211, 213); show(300, 303)
print("-- file-caliber path: sm = blended book, trade = sm - HB, cost cbps on |trade[m]| by tier, y expm1 only if CAL=simple, carry, pnl_raw")
show(263, 265); show(274, 281)
print("-- executor-caliber path (\"_ex\"): smr = sm with non-zero set re-demeaned and L1 rescaled to original gross; trr = smr - HR; pnl_r/car_r/cbps_r on smr/trr")
show(266, 273); show(304, 308)
print("-- rec tuple (column order) and gross_total / gross_member / gross_sel / netlong")
show(309, 313)
print("-- arms and column names")
show(319, 320)
print("-- summary stats (file caliber 'net' vs '_ex'); NOTE L349 labels np.abs(R[:,21]) as turnover_ex_mean but column 21 is cost_ex (mislabel)")
show(335, 336); show(344, 349)
print()

# COST_B numeric
COST_B = [(-0.25, 5.0, 0.85), (0.5, 6.0, 0.75), (2.0, 8.0, 0.55)]
print("COST_B tuples are (maker_bps, taker_bps, maker_fraction); tier 0: qv4h >= 5e6 USDT, tier 1: qv4h >= 1e6, tier 2: else; qv4h = expm1(clip(qvk,0,30))*48")
for tt, (mk, tk, fr) in enumerate(COST_B):
    print(f"  tier {tt}: maker {mk:+.2f} bps × {fr:.2f} + taker {tk:.2f} bps × {1-fr:.2f} = blended {fr*mk+(1-fr)*tk:.4f} bps per unit |trade| (one-way, per NAV)")
print("  cost per anchor = Σ_tier Σ_names |trade_name| × blended_rate_tier  (bps per NAV); trade = one-way change in weight (sm - previous)")
print()

# ---------------------------------------------------------------- runs
FIX = "fixed-seat live (W3FIX=0.21,0,0.79 M829 T400 FTRIM=zero)"
DYN = "dynamic-seat live (msharpe seats, M829 T400 FTRIM=zero)"
CAN = "canon (meta members, dynamic seats, FTRIM=off)"
CANF = "EXTRA canon fixed-seat (W3FIX=0.21,0,0.79 M0 T0 FTRIM=off) [not requested]"
C_SUM = "Σ-simple (CAL=log; y4 = meta Σ r5[E..E+47])"
C_EXP = "expm1 (CAL=simple; y4 -> expm1(Σ r5))"
C_PO = "compounded same window Π(1+r5[E..E+47])−1 (CAL=log; refute_C6_1 alt true_old)"
C_PN = "compounded exchange window Π(1+r5[E+1..E+48])−1 (CAL=log; refute_C6_2 altrun newprod)"
RUNS = [
    (FIX, C_SUM, f"{PORT}/w10_ablation_series_pod_live_w3fix_callog_s42.npz", META, "id", "live"),
    (FIX, C_EXP, f"{PORT}/w10_ablation_series_pod_live_w3fix_calsimple_s42.npz", META, "expm1", "live"),
    (FIX, C_PO, f"{RS}/refute_C6_1/dev/probe_artifacts/w10_ablation_series_alt_true_old_w3fix.npz", f"{RS}/refute_C6_1/alt/meta_true_old.npz", "id", "live"),
    (FIX, C_PN, f"{RS}/refute_C6_2/altrun/newprod/probe_artifacts/w10_ablation_series_alt_newprod_w3fix.npz", f"{RS}/refute_C6_2/altrun/meta_newprod.npz", "id", "live"),
    (DYN, C_SUM, f"{PORT}/w10_ablation_series_pod_live_callog_s42.npz", META, "id", "live"),
    (DYN, C_EXP, f"{PORT}/w10_ablation_series_pod_live_calsimple_s42.npz", META, "expm1", "live"),
    (DYN, C_PO, f"{RS}/refute_C6_1/dev/probe_artifacts/w10_ablation_series_alt_true_old_dyn.npz", f"{RS}/refute_C6_1/alt/meta_true_old.npz", "id", "live"),
    (DYN, C_PN, f"{RS}/refute_C6_2/altrun/newprod/probe_artifacts/w10_ablation_series_alt_newprod_dyn.npz", f"{RS}/refute_C6_2/altrun/meta_newprod.npz", "id", "live"),
    (CAN, C_SUM, f"{PORT}/w10_ablation_series_pod_canon_callog_s42.npz", META, "id", "canon"),
    (CAN, C_EXP, f"{PORT}/w10_ablation_series_pod_canon_calsimple_s42.npz", META, "expm1", "canon"),
    (CANF, C_SUM, f"{PORT}/w10_ablation_series_pod_canon_w3fix_callog_s42.npz", META, "id", "canon"),
]
print("NOT AVAILABLE: canon form × compounded target — no such npz exists under refute_C6_1/ or refute_C6_2/ (all alt runs carry MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero).")
print()

MT = np.load(META, allow_pickle=True)
E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; qvk = MT["qvk"]; y4_meta = MT["y4"]
erow = {int(t): i for i, t in enumerate(E_ts)}
# live-form members: device L49-53 rebuild (MEMBERS_TOPN=829)
_live_m = np.empty(len(E_ts), dtype=object)
for _i in range(len(E_ts)):
    _q = np.nan_to_num(qvk[_i], nan=-1.0); _ord = np.argsort(-_q); _ord = _ord[_q[_ord] > -0.5]
    _live_m[_i] = np.sort(_ord[:829]).astype(np.int64)

_meta_cache = {}


def load_meta_y4(p):
    if p not in _meta_cache:
        z = np.load(p, allow_pickle=True)
        assert np.array_equal(z["E_ts"].astype(np.int64), E_ts), p
        _meta_cache[p] = z["y4"]
    return _meta_cache[p]


def load(p):
    z = np.load(p, allow_pickle=True)
    cols = [str(c) for c in z["cols"]]; c = {n: k for k, n in enumerate(cols)}
    cfg = json.loads(str(z["config_json"]))
    return z, cols, c, cfg


def maxdd(x, ts):
    """max drawdown of cumsum(x) with a zero baseline (peak = max(0, running max)). returns (dd, peak_ts, trough_ts)."""
    cum = np.concatenate([[0.0], np.cumsum(x)])
    peak = np.maximum.accumulate(cum); dd = peak - cum; k = int(np.argmax(dd)); j = int(np.argmax(cum[:k + 1]))
    tsx = np.concatenate([[ts[0]], ts])
    return float(dd[k]), tsx[j], tsx[k]


def maxdd_nobase(x):
    cum = np.cumsum(x); return float(np.max(np.maximum.accumulate(cum) - cum))


def periods(ts, yr):
    return [("2024", yr == 2024), ("2025", yr == 2025), ("2026<=08-10", (yr == 2026) & (ts <= CUT)), ("2026->08-30", yr == 2026),
            ("2024->26", yr >= 2024), ("2025->26", yr >= 2025)]


HDR = ("| period | n | months | net_ex | net | gross | A=mean(nx)/mean(g) | B=mean(nx/g) | A %/yr gross | B %/yr gross | A 2x | B 2x | Sharpe(nx) "
       "| DD NAV bps (peak->trough) | DD gross bps (peak->trough) | worst month (sum nx) | w3_king | w3_fund | turnover | pnl_ex | carry_ex | cost_ex | max resid |")
SEP = "|" + "---|" * (HDR.count("|") - 1)

headline = []   # (form, caliber, arm, period, n, net_ex, A, A%/yr, sharpe, ddnav, worst_month)
quoted = {}


def block(form, cal, path, metap, tr, mmode):
    z, cols, c, cfg = load(path)
    print("=" * 100)
    print(f"FORM: {form}\nCALIBER: {cal}\nFILE: {path}\n  sha256[:16] {sha(path)}  config_json: CAL={cfg['CAL']} W3FIX={cfg['W3FIX']} MEMBERS_TOPN={cfg['MEMBERS_TOPN']} TRADE_TOPN={cfg['TRADE_TOPN']} FTRIM={cfg['FTRIM']} LEGS={cfg['LEGS']} PHI={cfg['PHI']} FSEED={cfg['FSEED']} SLOW_NPY={cfg['SLOW_NPY']}")
    print(f"  cols: {cols}")
    y4 = load_meta_y4(metap)
    for arm in ("S0", "d30_n2_c42"):
        R = z[f"{arm}_rec"]; W = z[f"{arm}_W"].astype(np.float64)
        ts = R[:, c["ts"]].astype(np.int64); yr = np.array([time.gmtime(int(t)).tm_year for t in ts])
        nx = R[:, c["net_ex"]]; net = R[:, c["net"]]; g = R[:, c["gross_total"]]
        px, cx, kx = R[:, c["pnl_ex"]], R[:, c["carry_ex"]], R[:, c["cost_ex"]]
        resid_all = np.abs(nx - (px - cx - kx))
        resid_file = np.abs(net - (R[:, c["pnl"]] - R[:, c["carry"]] - R[:, c["cost"]]))
        # y4-input verification: pnl (file col) == 1e4 * Σ_m W[m] * T(nan_to_num(y4[i,m]))
        rows = np.array([erow[int(t)] for t in ts])
        chk = np.empty(len(ts))
        for k, i in enumerate(rows):
            m = members[i] if mmode == "canon" else _live_m[i]
            yv = np.nan_to_num(y4[i, m], nan=0.0)
            if tr == "expm1":
                yv = np.expm1(yv)
            chk[k] = (W[k, m] * yv).sum() * 1e4
        dchk = np.abs(chk - R[:, c["pnl"]])
        zg = int((g < 1e-9).sum())
        print(f"\n-- ARM {arm}: n={len(ts)} first={d(ts[0])} last={d(ts[-1])} | identity max|net_ex-(pnl_ex-carry_ex-cost_ex)|={resid_all.max():.3e} bps; file: max|net-(pnl-carry-cost)|={resid_file.max():.3e} bps | anchors with gross_total<1e-9: {zg}")
        print(f"   y4-INPUT CHECK (pnl column vs 1e4*Σ_m W·T(y4_meta_of_this_run)): max|Δ| all={dchk.max():.4f} bps; by year: " + ", ".join(f"{y}:{dchk[yr==y].max():.4f}" for y in sorted(set(yr.tolist()))) + f"  [meta={metap} T={tr} members={mmode}]")
        print(HDR); print(SEP)
        for lab, msk in periods(ts, yr):
            n = int(msk.sum()); a = nx[msk]; gg = g[msk]; t_ = ts[msk]
            months = n / 6 / 30.4
            A = a.mean() / gg.mean()
            ratio = np.where(gg > 1e-9, a / np.where(gg > 1e-9, gg, 1.0), 0.0); B = ratio.mean()
            sh = a.mean() / a.std(ddof=1) * np.sqrt(ANN)
            ddn, pn, tn = maxdd(a, t_); ddg, pg, tg = maxdd(ratio, t_)
            mons = {}
            for t, v in zip(t_, a):
                mons[ym(t)] = mons.get(ym(t), 0.0) + v
            wm = min(mons, key=mons.get)
            mon_lab = f"{months:.1f}" if lab.startswith("2026") else ""
            print(f"| {lab} | {n} | {mon_lab} | {a.mean():+.4f} | {net[msk].mean():+.4f} | {gg.mean():.4f} | {A:+.4f} | {B:+.4f} | {A*ANN/100:+.2f}% | {B*ANN/100:+.2f}% | {2*A*ANN/100:+.2f}% | {2*B*ANN/100:+.2f}% | {sh:+.3f} "
                  f"| {ddn:.1f} ({d(pn)} -> {d(tn)}) | {ddg:.1f} ({d(pg)} -> {d(tg)}) | {wm} {mons[wm]:+.1f} | {R[msk, c['w3_king']].mean():.3f} | {R[msk, c['w3_fund']].mean():.3f} | {R[msk, c['turnover']].mean():.5f} "
                  f"| {px[msk].mean():+.4f} | {cx[msk].mean():+.4f} | {kx[msk].mean():.4f} | {resid_all[msk].max():.1e} |")
            headline.append((form, cal, arm, lab, n, a.mean(), A, A * ANN / 100, sh, ddn, f"{wm} {mons[wm]:+.1f}", kx[msk].mean()))
            if lab == "2024->26":
                quoted[(form, cal, arm)] = (net[msk].mean(), net[msk].mean() / net[msk].std(ddof=1) * np.sqrt(ANN), a.mean(), sh)
        if arm == "d30_n2_c42" and form == FIX and cal == C_SUM:
            a = nx[yr == 2024]
            print(f"   DD-convention check (fixed-seat live Σ-simple d30 2024): zero-baseline {maxdd(a, ts[yr==2024])[0]:.1f} bps vs no-baseline (refuters' final_stats.py convention) {maxdd_nobase(a):.1f} bps")
    return z


ZS = {}
for run in RUNS:
    ZS[run[2]] = block(*run)

# ---------------------------------------------------------------- headline (d30 arm only, compact)
print("\n" + "=" * 100)
print("HEADLINE (arm d30_n2_c42; net_ex bps/anchor per NAV; A = mean(net_ex)/mean(gross_total); %/yr = A×2190/100; DD zero-baseline bps NAV)")
print("=" * 100)
print("| form | caliber | period | n | net_ex | A per-gross | A %/yr gross | Sharpe | DD NAV bps | worst month | cost_ex |")
print("|---|---|---|---|---|---|---|---|---|---|---|")
for (form, cal, arm, lab, n, m, A, ann, sh, ddn, wm, kx) in headline:
    if arm == "d30_n2_c42":
        print(f"| {form.split(' (')[0]} | {cal.split(' (')[0]} | {lab} | {n} | {m:+.4f} | {A:+.4f} | {ann:+.2f}% | {sh:+.3f} | {ddn:.1f} | {wm} | {kx:.4f} |")

print("\n" + "=" * 100)
print("HEADLINE (arm S0, same columns)")
print("=" * 100)
print("| form | caliber | period | n | net_ex | A per-gross | A %/yr gross | Sharpe | DD NAV bps | worst month | cost_ex |")
print("|---|---|---|---|---|---|---|---|---|---|---|")
for (form, cal, arm, lab, n, m, A, ann, sh, ddn, wm, kx) in headline:
    if arm == "S0":
        print(f"| {form.split(' (')[0]} | {cal.split(' (')[0]} | {lab} | {n} | {m:+.4f} | {A:+.4f} | {ann:+.2f}% | {sh:+.3f} | {ddn:.1f} | {wm} | {kx:.4f} |")

# ---------------------------------------------------------------- cost_ex per year, fixed-seat live form
print("\n" + "=" * 100)
print("COST_EX PER YEAR — fixed-seat live form (both calibers), both arms; plus cost_ex/turnover (paths differ: turnover = blended path |sm-HB|, cost_ex = reshaped path |smr-HR|; ratio is INDICATIVE only)")
print("=" * 100)
for cal, path in ((C_SUM, f"{PORT}/w10_ablation_series_pod_live_w3fix_callog_s42.npz"), (C_EXP, f"{PORT}/w10_ablation_series_pod_live_w3fix_calsimple_s42.npz")):
    z = ZS[path]; cols = [str(c) for c in z["cols"]]; c = {n: k for k, n in enumerate(cols)}
    for arm in ("S0", "d30_n2_c42"):
        R = z[f"{arm}_rec"]; ts = R[:, 0].astype(np.int64); yr = np.array([time.gmtime(int(t)).tm_year for t in ts])
        line = []
        for y in sorted(set(yr.tolist())):
            m = yr == y
            line.append(f"{y}: cost_ex {R[m, c['cost_ex']].mean():.4f} bps/anchor (= {R[m, c['cost_ex']].mean()*ANN/100:.2f}%/yr NAV; cost(file) {R[m, c['cost']].mean():.4f}; turnover {R[m, c['turnover']].mean():.5f}; cost_ex/turnover {R[m, c['cost_ex']].mean()/R[m, c['turnover']].mean():.3f} bps per unit)")
        print(f"  [{cal.split(' (')[0]}] {arm}:\n    " + "\n    ".join(line))

# ---------------------------------------------------------------- previously quoted numbers
print("\n" + "=" * 100)
print("PREVIOUSLY QUOTED 'canon net_2024on 1.11 vs 0.78 (Sharpe 2.59 vs 1.93); live 1.49 vs 0.79 (3.23 vs 1.85)' — column/arm attribution")
print("=" * 100)
print("Recomputed from the npz rec arrays over 2024->26 (all anchors with year>=2024), mean and mean/std(ddof=1)*sqrt(2190):")
for form in (CAN, DYN, FIX):
    for arm in ("S0", "d30_n2_c42"):
        s = quoted[(form, C_EXP, arm)]; l = quoted[(form, C_SUM, arm)]
        print(f"  {form.split(' (')[0]:18s} {arm:11s} | 'net' (file caliber) col: CAL=simple {s[0]:+.4f} S {s[1]:.3f}  vs CAL=log {l[0]:+.4f} S {l[1]:.3f}  | 'net_ex' col: CAL=simple {s[2]:+.4f} S {s[3]:.3f}  vs CAL=log {l[2]:+.4f} S {l[3]:.3f}")
print("Summary-JSON fields (device L336: net_2024on/sharpe_2024on are computed on column 1 = 'net'; L345-347: net_ex_2024on/sharpe_ex_2024on on column 18 = 'net_ex'):")
for tag in ("pod_canon_calsimple_s42", "pod_canon_callog_s42", "pod_live_calsimple_s42", "pod_live_callog_s42", "pod_live_w3fix_calsimple_s42", "pod_live_w3fix_callog_s42"):
    J = json.load(open(f"{PORT}/w10_ablation_summary_{tag}.json"))
    for arm in ("S0", "d30_n2_c42"):
        o = J[arm]
        print(f"  {tag:30s} {arm:11s} net_2024on={o['net_2024on']:.4f} sharpe_2024on={o['sharpe_2024on']:.3f} | net_ex_2024on={o['net_ex_2024on']:.4f} sharpe_ex_2024on={o['sharpe_ex_2024on']:.3f}")
for form, lab in ((CAN, "canon"), (DYN, "live dyn")):
    s0s = quoted[(form, C_EXP, "S0")]; s0l = quoted[(form, C_SUM, "S0")]; d3s = quoted[(form, C_EXP, "d30_n2_c42")]; d3l = quoted[(form, C_SUM, "d30_n2_c42")]
    print(f"  {lab}: quoted pair matches S0 'net' (CAL=simple {s0s[0]:.4f}/{s0s[1]:.3f} vs CAL=log {s0l[0]:.4f}/{s0l[1]:.3f}). Same comparison on d30 'net_ex': {d3s[2]:.4f}/{d3s[3]:.3f} vs {d3l[2]:.4f}/{d3l[3]:.3f}. "
          f"Δ(S0 net − d30 net_ex): CAL=simple {s0s[0]-d3s[2]:+.4f} bps (S {s0s[1]-d3s[3]:+.3f}); CAL=log {s0l[0]-d3l[2]:+.4f} bps (S {s0l[1]-d3l[3]:+.3f})")

# ---------------------------------------------------------------- cross-run bitwise checks
print("\n" + "=" * 100)
print("CROSS-RUN BITWISE CHECKS (rec arrays)")
print("=" * 100)
pairs = [
    ("C6_1 alt_sum_old_w3fix (meta y4 rebuilt as Σ r5[E..E+47]) vs PORT live w3fix callog", f"{RS}/refute_C6_1/dev/probe_artifacts/w10_ablation_series_alt_sum_old_w3fix.npz", f"{PORT}/w10_ablation_series_pod_live_w3fix_callog_s42.npz"),
    ("C6_1 alt_sum_old_dyn vs PORT live dyn callog", f"{RS}/refute_C6_1/dev/probe_artifacts/w10_ablation_series_alt_sum_old_dyn.npz", f"{PORT}/w10_ablation_series_pod_live_callog_s42.npz"),
    ("C6_2 alt_base_w3fix vs PORT live w3fix callog", f"{RS}/refute_C6_2/altrun/base/probe_artifacts/w10_ablation_series_alt_base_w3fix.npz", f"{PORT}/w10_ablation_series_pod_live_w3fix_callog_s42.npz"),
    ("C6_1 alt_true_new_w3fix vs C6_2 alt_newprod_w3fix (both Π(1+r5[E+1..E+48])−1, independently built)", f"{RS}/refute_C6_1/dev/probe_artifacts/w10_ablation_series_alt_true_new_w3fix.npz", f"{RS}/refute_C6_2/altrun/newprod/probe_artifacts/w10_ablation_series_alt_newprod_w3fix.npz"),
    ("C6_1 alt_true_new_dyn vs C6_2 alt_newprod_dyn", f"{RS}/refute_C6_1/dev/probe_artifacts/w10_ablation_series_alt_true_new_dyn.npz", f"{RS}/refute_C6_2/altrun/newprod/probe_artifacts/w10_ablation_series_alt_newprod_dyn.npz"),
    ("C6_1 rerun_prodnew live w3fix vs C6_2 alt_newprod_w3fix", f"{RS}/refute_C6_1/rerun_prodnew/probe_artifacts/w10_ablation_series_prodnew_live_w3fix_callog_s42.npz", f"{RS}/refute_C6_2/altrun/newprod/probe_artifacts/w10_ablation_series_alt_newprod_w3fix.npz"),
]
for lab, a, b in pairs:
    za = np.load(a, allow_pickle=True); zb = np.load(b, allow_pickle=True)
    for arm in ("S0", "d30_n2_c42"):
        Ra = za[f"{arm}_rec"]; Rb = zb[f"{arm}_rec"]
        print(f"  {lab} [{arm}]: array_equal={np.array_equal(Ra, Rb)} max|Δ net_ex|={np.max(np.abs(Ra[:, 18]-Rb[:, 18])):.3e} max|Δ pnl|={np.max(np.abs(Ra[:, 2]-Rb[:, 2])):.3e}")
# meta y4 relations (cheap): true_old vs meta (same window) and newprod vs true_new
print("\nMETA y4 RELATIONS (cells both finite):")
yto = load_meta_y4(f"{RS}/refute_C6_1/alt/meta_true_old.npz"); ytn = load_meta_y4(f"{RS}/refute_C6_1/alt/meta_true_new.npz"); ynp = load_meta_y4(f"{RS}/refute_C6_2/altrun/meta_newprod.npz")
b = np.isfinite(y4_meta) & np.isfinite(yto)
print(f"  meta y4 (Σ-simple) vs true_old (Π same window): cells {int(b.sum())} mean(Π−Σ)={np.mean(yto[b]-y4_meta[b])*1e4:+.4f} bps mean|Π−Σ|={np.mean(np.abs(yto[b]-y4_meta[b]))*1e4:.4f} bps max|Π−Σ|={np.max(np.abs(yto[b]-y4_meta[b]))*1e4:.1f} bps nan-mismatch={int((np.isfinite(y4_meta)^np.isfinite(yto)).sum())}")
b = np.isfinite(ytn) & np.isfinite(ynp)
print(f"  C6_1 true_new vs C6_2 newprod (both Π shifted window): cells {int(b.sum())} exact_eq={float((ytn[b]==ynp[b]).mean()):.6f} max|Δ|={np.max(np.abs(ytn[b]-ynp[b])):.3e} nan-mismatch={int((np.isfinite(ytn)^np.isfinite(ynp)).sum())}")
b = np.isfinite(y4_meta)
print(f"  meta y4 stats: finite cells {int(b.sum())} mean {y4_meta[b].mean()*1e4:+.4f} bps; expm1(y4) mean {np.expm1(y4_meta[b]).mean()*1e4:+.4f} bps; mean(expm1(y4)−y4) {np.mean(np.expm1(y4_meta[b])-y4_meta[b])*1e4:+.4f} bps (convexity added by CAL=simple on top of a Σ-simple target)")

# ---------------------------------------------------------------- caliber-only deltas on an identical book path (fixed-seat, S0: weights cannot depend on y4 values)
print("\n" + "=" * 100)
print("CALIBER-ONLY DELTAS ON IDENTICAL BOOK PATH — fixed-seat live, arm S0 (no stop layer, W3FIX seats, so W is y4-value-independent)")
print("=" * 100)
FIXRUNS = [(cal, path) for (form, cal, path, _, _, _) in RUNS if form == FIX]
base_cal, base_path = FIXRUNS[0]
Wb = ZS[base_path]["S0_W"]; Rb = ZS[base_path]["S0_rec"]; tsb = Rb[:, 0].astype(np.int64); yrb = np.array([time.gmtime(int(t)).tm_year for t in tsb])
for cal, path in FIXRUNS[1:]:
    Wx = ZS[path]["S0_W"]; Rx = ZS[path]["S0_rec"]
    print(f"  [{cal.split(' (')[0]}] S0_W array_equal vs Σ-simple: {np.array_equal(Wb, Wx)}  max|ΔW|={np.max(np.abs(Wb.astype(np.float64)-Wx.astype(np.float64))):.3e}; turnover col equal: {np.array_equal(Rb[:,17], Rx[:,17])}; gross_total col equal: {np.array_equal(Rb[:,5], Rx[:,5])}; cost_ex col equal: {np.array_equal(Rb[:,21], Rx[:,21])}; carry_ex col equal: {np.array_equal(Rb[:,20], Rx[:,20])}")
    for lab, msk in periods(tsb, yrb):
        dn = Rx[msk, 18] - Rb[msk, 18]
        print(f"      {lab:12s} n={int(msk.sum())} Δnet_ex(this − Σ-simple) mean {dn.mean():+.4f} bps/anchor NAV (= Δpnl_ex mean {np.mean(Rx[msk,19]-Rb[msk,19]):+.4f}); per-gross A {dn.mean()/Rb[msk,5].mean():+.4f} => {dn.mean()/Rb[msk,5].mean()*ANN/100:+.2f}%/yr gross; Sharpe {Rx[msk,18].mean()/Rx[msk,18].std(ddof=1)*np.sqrt(ANN):+.3f} vs {Rb[msk,18].mean()/Rb[msk,18].std(ddof=1)*np.sqrt(ANN):+.3f}")
print("\nUNITS_TABLE_DONE")
