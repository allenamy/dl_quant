"""carry_composition step 3 (live side, Mac, READ-ONLY on ~/wide_shadow).
(1) FTRIM counterfactual on the live target book at the 28 overlap anchors: zero the shorts whose 8h-normalised rate
    rn8 = rate*(8/iv) <= -10bp (the replay's FTRIM=zero rule, w10_universe.py L195-197 / combo_stage.py L245-248),
    renormalise, and re-measure carry; count how many live names sit in that band.
(2) Live book time series 08-26 00Z -> latest with producer-ledger rates (== panel, gap_1): carry/gross, pay_SN, pay_LP,
    ONG weight, band-name count/gross, to see whether FTRIM going live (first anchor with a ftrim record) moved pay_SN.
(3) EMA input check: producer fund EMA reconstructed from ledger_tail (rn = rate*8/iv, HL 3d, per settlement) vs panel
    f_fund_ema_v1 at 08-31 00Z and 08-26 04Z: Spearman/Pearson, and rank agreement inside the live members."""
import json, os, time, numpy as np
from scipy.stats import rankdata, spearmanr
SP = "/Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/b9646a9e-31a1-4eb3-a08b-e8ea13fdceb0/scratchpad/review_caliber"
G1 = f"{SP}/gap_1"; OUT = f"{SP}/carry_composition"; WS = "/Users/haosiyu/wide_shadow"
def f(t): return time.strftime("%m-%d %HZ", time.gmtime(int(t)))
P = np.load(f"{G1}/panel_fund_tail.npz", allow_pickle=True)
pts = P["ts"].astype(np.int64); psym = [str(s) for s in P["symbols"]]; NW = len(psym); sidx = {s: j for j, s in enumerate(psym)}
FN = P["f_fund_now"].astype(np.float64); IV = P["f_fund_iv"].astype(np.float64); FE = P["f_fund_ema_v1"].astype(np.float64); prow = {int(t): i for i, t in enumerate(pts)}
aux = json.load(open(f"{WS}/state/aux.json")); LT = aux["ledger_tail"]
R = json.load(open(f"{G1}/replay_tail_rows.json")); tag = "pod_live_w3fix_callog_s42"; wts = [int(t) for t in R[tag]["W_ts"]]
def r_last(s, N):
    led = LT.get(s)
    if not led: return None
    best = None
    for ft, r, iv in led:
        if ft <= N: best = (ft, r, iv)
        else: break
    if best is None or N - best[0] > 12 * 3600: return None
    return best
def rates_ledger(N):
    r4 = np.zeros(NW); rn8 = np.full(NW, np.nan)
    for j, s in enumerate(psym):
        rl = r_last(s, N)
        if rl: r4[j] = rl[1] * (4.0 / rl[2]); rn8[j] = rl[1] * (8.0 / rl[2])
    return r4, rn8
def rates_panel(N):
    i = prow[N]; iv = np.where(np.isfinite(IV[i]) & (IV[i] > 0), IV[i], 8.0)
    return np.nan_to_num(FN[i]) * (4.0 / iv), np.where(np.isfinite(FN[i]), FN[i] * (8.0 / iv), np.nan)
def dm(w):
    nz = np.abs(w) > 1e-12; o = w.copy()
    if nz.any():
        o[nz] -= o[nz].mean(); g0 = np.abs(w).sum(); g1 = np.abs(o).sum()
        if g1 > 1e-9: o *= g0 / g1
    return o
def vec(path):
    w = np.zeros(NW)
    for s, v in json.load(open(path))["weights"].items(): w[sidx[s]] = float(v)
    return w
def expo(w, r):
    g = np.abs(w).sum(); return {"carry": (w * r).sum() / g * 1e4, "pay_SN": (w * r)[(w < 0) & (r < 0)].sum() / g * 1e4, "pay_LP": (w * r)[(w > 0) & (r > 0)].sum() / g * 1e4, "SN": np.abs(w[(w < 0) & (r < 0)]).sum() / g, "gross": g}
common = [N for N in wts if N >= 1787716800 and N in prow and os.path.exists(f"{WS}/state/target_live/{N}.json")]
print(f"(1) FTRIM counterfactual on live target book, {len(common)} anchors {f(common[0])}->{f(common[-1])} (panel rates; + = pays; per gross)")
acc = []
for N in common:
    r4, rn8 = rates_panel(N); tl = dm(vec(f"{WS}/state/target_live/{N}.json")); Wr = dm(np.array(R[tag]["W"][wts.index(N)], np.float64))
    band = np.isfinite(rn8) & (rn8 <= -0.0010)
    live_band_short = (tl < 0) & band; rep_band_short = (Wr < 0) & band
    cf = tl.copy(); cf[live_band_short] = 0.0; cf = dm(cf)
    # also: shrink the band shorts to the replay's residual level instead of zero (EMA/band residual): not needed, zero is the rule
    e_l = expo(tl, r4); e_c = expo(cf, r4); e_r = expo(Wr, r4)
    acc.append({"N": N, "live": e_l["carry"], "live_cf": e_c["carry"], "replay": e_r["carry"], "n_band_names": int(band.sum()),
                "n_live_band_short": int(live_band_short.sum()), "g_live_band_short": float(np.abs(tl[live_band_short]).sum() / e_l["gross"]),
                "pay_live_band_short": float((tl * r4)[live_band_short].sum() / e_l["gross"] * 1e4),
                "n_rep_band_short": int(rep_band_short.sum()), "g_rep_band_short": float(np.abs(Wr[rep_band_short]).sum() / e_r["gross"]),
                "pay_rep_band_short": float((Wr * r4)[rep_band_short].sum() / e_r["gross"] * 1e4),
                "live_SN": e_l["pay_SN"], "cf_SN": e_c["pay_SN"], "rep_SN": e_r["pay_SN"], "live_LP": e_l["pay_LP"], "rep_LP": e_r["pay_LP"]})
A = acc
def m(k): return np.mean([x[k] for x in A])
def se(k1, k2): d = np.array([x[k1] - x[k2] for x in A]); return d.mean(), d.std(ddof=1) / np.sqrt(len(d))
print(f"  live {m('live'):+.3f} | live with band shorts zeroed (FTRIM-cf) {m('live_cf'):+.3f} | replay(FTRIM=zero) {m('replay'):+.3f}")
print("  gap live - replay: %+.3f (se %.3f) | gap live_cf - replay: %+.3f (se %.3f) | FTRIM-cf removes: %+.3f (se %.3f)" % (*se("live", "replay"), *se("live_cf", "replay"), *se("live", "live_cf")))
print(f"  band (rn8<=-10bp/8h) names in panel: mean {m('n_band_names'):.1f} | live short names in band: {m('n_live_band_short'):.1f} (gross share {m('g_live_band_short'):.3f}, they pay {m('pay_live_band_short'):+.3f}) | replay short names in band: {m('n_rep_band_short'):.1f} (gross {m('g_rep_band_short'):.3f}, pay {m('pay_rep_band_short'):+.3f})")
print(f"  pay_SN: live {m('live_SN'):+.3f} cf {m('cf_SN'):+.3f} replay {m('rep_SN'):+.3f} | pay_LP: live {m('live_LP'):+.3f} replay {m('rep_LP'):+.3f}")
print("  per anchor: when | live | live_cf | replay | n_live_band_short g pay | n_rep_band_short g pay")
for x in A: print(f"   {f(x['N'])} {x['live']:+6.2f} {x['live_cf']:+6.2f} {x['replay']:+6.2f} | {x['n_live_band_short']:2d} {x['g_live_band_short']:.3f} {x['pay_live_band_short']:+.2f} | {x['n_rep_band_short']:2d} {x['g_rep_band_short']:.3f} {x['pay_rep_band_short']:+.2f}")
# (2) time series with ledger rates through the latest target_live
print("\n(2) live target book time series (ledger rates == panel; per gross): when | prod | ftrim_rec | carry | pay_SN | pay_LP | SN share | n band shorts | g band shorts | ONG w | COTI w | TUT w")
allN = sorted(int(x[:-5]) for x in os.listdir(f"{WS}/state/target_live") if x.endswith(".json") and x[:-5].isdigit())
ser = []
jONG, jCOTI, jTUT = sidx.get("ONGUSDT"), sidx.get("COTIUSDT"), sidx.get("TUTUSDT")
for N in allN:
    if N < 1787702400: continue
    r4, rn8 = rates_ledger(N); tl = dm(vec(f"{WS}/state/target_live/{N}.json")); prod = json.load(open(f"{WS}/state/target_live/{N}.json")).get("producer", "")[:5]
    tc = f"{WS}/state/target_combo/{N}.json"; ft = json.load(open(tc)).get("ftrim") if os.path.exists(tc) else None
    band = np.isfinite(rn8) & (rn8 <= -0.0010); lbs = (tl < 0) & band; e = expo(tl, r4)
    ser.append({"N": N, "prod": prod, "ftrim": (f"kc{ft['n_kc']}/fc{ft['n_fc']}" if ft else "-"), "carry": e["carry"], "pay_SN": e["pay_SN"], "pay_LP": e["pay_LP"], "SN": e["SN"],
                "n_band": int(lbs.sum()), "g_band": float(np.abs(tl[lbs]).sum() / e["gross"]), "ONG": float(tl[jONG]), "COTI": float(tl[jCOTI]), "TUT": float(tl[jTUT])})
    print(f"   {f(N)} {prod:5s} {ser[-1]['ftrim']:9s} {e['carry']:+6.2f} {e['pay_SN']:+6.2f} {e['pay_LP']:+6.2f} {e['SN']:.3f} {int(lbs.sum()):2d} {ser[-1]['g_band']:.3f} {tl[jONG]:+.4f} {tl[jCOTI]:+.4f} {tl[jTUT]:+.4f}")
def per(lo, hi, k): a = [x[k] for x in ser if lo <= x["N"] <= hi]; return np.mean(a), len(a)
for lab, lo, hi in (("pre-FTRIM 08-26 00Z..09-02 00Z", 1787702400, 1788307200), ("post-FTRIM 09-02 04Z..latest", 1788321600, 9e12)):
    print(f"  {lab:32s}: carry %+.3f pay_SN %+.3f pay_LP %+.3f g_band %.3f (n %d)" % (per(lo, hi, "carry")[0], per(lo, hi, "pay_SN")[0], per(lo, hi, "pay_LP")[0], per(lo, hi, "g_band")[0], per(lo, hi, "carry")[1]))
# (3) EMA reconstruction from ledger_tail vs panel f_fund_ema_v1
print("\n(3) producer fund EMA (reconstructed from ledger_tail: rn=rate*8/iv, a=1-0.5^(dt/3d)) vs panel f_fund_ema_v1")
def ema_at(N):
    out = np.full(NW, np.nan); span = np.full(NW, np.nan)
    for j, s in enumerate(psym):
        led = LT.get(s)
        if not led: continue
        est = None; first = None
        for ft, r, iv in led:
            if ft > N: break
            if first is None: first = ft
            rn = r * (8.0 / iv)
            if est is None: est = {"acc": rn, "last_ts": ft}
            else:
                a = 1 - 0.5 ** (max(ft - est["last_ts"], 1) / (3 * 86400.0)); est = {"acc": est["acc"] + a * (rn - est["acc"]), "last_ts": ft}
        if est and N - est["last_ts"] <= 12 * 3600: out[j] = est["acc"]; span[j] = (N - first) / 86400.0
    return out, span
for N in (1787716800, 1788134400):
    if N not in prow: continue
    e, span = ema_at(N); pe = FE[prow[N]]
    ok = np.isfinite(e) & np.isfinite(pe); okl = ok & (span >= 30)
    z = np.load(f"{WS}/state/weights/{N}.npz"); mem = z["members"].astype(np.int64); mm = np.zeros(NW, bool); mm[mem] = True
    okm = ok & mm
    print(f"  {f(N)}: both finite {ok.sum()} (span>=30d: {okl.sum()}); spearman all {spearmanr(e[ok], pe[ok])[0]:.4f}, span>=30d {spearmanr(e[okl], pe[okl])[0]:.4f}; members {okm.sum()}: spearman {spearmanr(e[okm], pe[okm])[0]:.4f}, median |diff|/|panel| {np.median(np.abs(e[okm]-pe[okm])/np.maximum(np.abs(pe[okm]),1e-9)):.3f}, max|diff| {np.abs(e[okm]-pe[okm]).max():.2e}")
    # panel-NaN where ledger has and vice versa, within members
    print(f"     members: ledger-finite & panel-NaN {int((np.isfinite(e) & ~np.isfinite(pe) & mm).sum())}, panel-finite & ledger-NaN {int((~np.isfinite(e) & np.isfinite(pe) & mm).sum())}")
    # rank position of ONG / COTI in both
    for s in ("ONGUSDT", "COTIUSDT", "TUTUSDT", "BICOUSDT"):
        j = sidx[s]; rk_l = (rankdata(e[okm]) / (okm.sum() - 1) - 0.5)[np.where(okm)[0].tolist().index(j)] if okm[j] else np.nan; rk_p = (rankdata(pe[okm]) / (okm.sum() - 1) - 0.5)[np.where(okm)[0].tolist().index(j)] if okm[j] else np.nan
        print(f"     {s}: ledger EMA {e[j]:+.5f} panel {pe[j]:+.5f} | member-rank z ledger {rk_l:+.3f} panel {rk_p:+.3f} | span {span[j]:.1f}d")
json.dump({"cf": acc, "series": ser}, open(f"{OUT}/ftrim_live_cf.json", "w"), indent=1, default=float)
# old bundle king preds shape (for a possible SLOW_NPY arm)
p = f"{WS}/shadow_bundle.aug20260816_backup/slow_pred_pinned.npy"
if os.path.exists(p): a = np.load(p, mmap_mode="r"); print("\nold bundle slow_pred_pinned.npy shape", a.shape, "finite", float(np.isfinite(a).mean()))
