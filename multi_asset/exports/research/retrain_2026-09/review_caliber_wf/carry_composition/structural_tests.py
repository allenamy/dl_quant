"""carry_composition step 3 (Mac, READ-ONLY on ~/wide_shadow).
A. Replay live-form WITHOUT FTRIM (V1, fresh pod run cc_live_w3fix_noftrim_callog_s42) vs live target at the 28 anchors:
   carry ladder V1 -> V1|450 -> V1|live members -> live; band-short names; per-name weights for the deep-negative names;
   nsel / cap (2.5/nsel) / max|w| in each book.
B. Test (i) fund rank base: single-anchor target (device chain lines 185-209 without EMA) with z = 0.21*xz(king)+0.79*xz(fund)
   where the fund rank base is {829-panel finite (replay M1 emulation), aux base_syms (M1 live base as of today), 400 live members
   (what the producer used at these anchors)}; FTRIM off/on. Reports LP / SN / band-short gross share and carry of the target.
C. Test (ii) FTRIM: replay trimmed names (z<0 & rn8<=-10bp, kc and fc chains, reconstructed from the same inputs) vs live
   would-be-trimmed names (live short & band) at the 28 anchors; and post-09-02 combo ftrim record counts vs live band shorts.
D. INFERRED bound: fixed-seat 2024->26 net_ex if carry were scaled by the live/replay ratio (per year), from replay_family.json."""
import json, os, time, numpy as np
from scipy.stats import rankdata
SP = "/Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/b9646a9e-31a1-4eb3-a08b-e8ea13fdceb0/scratchpad/review_caliber"
G1 = f"{SP}/gap_1"; OUT = f"{SP}/carry_composition"; WS = "/Users/haosiyu/wide_shadow"
def f(t): return time.strftime("%m-%d %HZ", time.gmtime(int(t)))
P = np.load(f"{G1}/panel_fund_tail.npz", allow_pickle=True); pts = P["ts"].astype(np.int64); psym = [str(s) for s in P["symbols"]]; NW = len(psym); sidx = {s: j for j, s in enumerate(psym)}
FN = P["f_fund_now"].astype(np.float64); IV = P["f_fund_iv"].astype(np.float64); FE = P["f_fund_ema_v1"].astype(np.float64); prow = {int(t): i for i, t in enumerate(pts)}
cfg = json.load(open(f"{WS}/shadow_bundle/config.json")); live450 = np.array([s in set(cfg["symbols_live"]) for s in psym])
aux = json.load(open(f"{WS}/state/aux.json")); base_m1 = np.array([s in set(aux["base_syms"]) for s in psym])
INP = json.load(open(f"{OUT}/replay_inputs_overlap.json")); assert INP["symbols"] == psym
ARMS = json.load(open(f"{OUT}/W_overlap_4arms.json"))
OV = [N for N in range(1787716800, 1788120000 + 1, 14400) if N != 1788033600]
sig = {r["anchor_ts"]: r for r in (json.loads(l) for l in open(f"{WS}/shadow_log.jsonl") if l.strip()) if r.get("e") == "signal"}
def rates(N):
    i = prow[N]; iv = np.where(np.isfinite(IV[i]) & (IV[i] > 0), IV[i], 8.0)
    return np.nan_to_num(FN[i]) * (4.0 / iv), np.where(np.isfinite(FN[i]), FN[i] * (8.0 / iv), np.nan)
def dm(w):
    nz = np.abs(w) > 1e-12; o = w.copy()
    if nz.any():
        o[nz] -= o[nz].mean(); g0 = np.abs(w).sum(); g1 = np.abs(o).sum()
        if g1 > 1e-9: o *= g0 / g1
    return o
def expo(w, r, band):
    g = np.abs(w).sum(); s = dm(w)
    return {"carry": (s * r).sum() / g * 1e4, "pay_SN": (s * r)[(s < 0) & (r < 0)].sum() / g * 1e4, "pay_LP": (s * r)[(s > 0) & (r > 0)].sum() / g * 1e4,
            "LP": np.abs(s[(s > 0) & (r > 0)]).sum() / g, "SN": np.abs(s[(s < 0) & (r < 0)]).sum() / g, "band_g": np.abs(s[(s < 0) & band]).sum() / g, "band_pay": (s * r)[(s < 0) & band].sum() / g * 1e4,
            "band_n": int(((s < 0) & band).sum()), "maxw": float(np.abs(s).max()), "n": int((np.abs(s) > 1e-12).sum())}
def vec(path):
    w = np.zeros(NW)
    for s, v in json.load(open(path))["weights"].items(): w[sidx[s]] = float(v)
    return w
def xz(v):
    ok = np.isfinite(v); out = np.full(len(v), np.nan)
    if ok.sum() >= 10: out[ok] = rankdata(v[ok]) / max(ok.sum() - 1, 1) - 0.5
    return out
def xz_in_base(vm, base_mask, fe_row):
    """rank of each name's fund EMA within the base distribution (base names with finite EMA); non-base names NaN."""
    bv = fe_row[base_mask & np.isfinite(fe_row)]; out = np.full(NW, np.nan)
    if len(bv) >= 10:
        r = rankdata(bv) / max(len(bv) - 1, 1) - 0.5; keys = np.where(base_mask & np.isfinite(fe_row))[0]; pos = {int(k): i for i, k in enumerate(keys)}
        for j in range(NW):
            if np.isfinite(vm[j]) and j in pos: out[j] = r[pos[j]]
    return out
DEEP = ["ONGUSDT", "COTIUSDT", "TUTUSDT", "BICOUSDT", "HOMEUSDT", "ONTUSDT", "ACEUSDT", "SKRUSDT"]
print("== A. replay live-form WITHOUT FTRIM (V1) vs live target, 28 anchors, per gross, dm caliber, + = pays ==")
acc = {k: [] for k in ("V1", "V1_in450", "V1_inmem", "live", "m1t400", "canon", "ftrim")}; deep = {k: {s: [] for s in DEEP} for k in ("live", "V1", "m1t400", "canon", "ftrim")}
caps = []
for N in OV:
    r4, rn8 = rates(N); band = np.isfinite(rn8) & (rn8 <= -0.0010)
    tl = vec(f"{WS}/state/target_live/{N}.json"); z = np.load(f"{WS}/state/weights/{N}.npz"); mem = np.zeros(NW, bool); mem[z["members"].astype(np.int64)] = True
    W = {}
    for tag, key in (("V1_live_w3fix_noftrim", "V1"), ("m1t400_dyn_noftrim", "m1t400"), ("canon_w3fix_noftrim", "canon"), ("live_w3fix_ftrim", "ftrim")):
        a = ARMS[tag]; k = a["W_ts"].index(N); W[key] = np.array(a["W"][k], np.float64); cols = a["cols"]; row = a["rows"][k]
        if key == "V1": nsel_v1 = row[cols.index("nsel")]; nmem_v1 = row[cols.index("nmember")]
    acc["V1"].append(expo(W["V1"], r4, band)); acc["V1_in450"].append(expo(np.where(live450, W["V1"], 0.0), r4, band)); acc["V1_inmem"].append(expo(np.where(mem, W["V1"], 0.0), r4, band))
    acc["live"].append(expo(tl, r4, band)); acc["m1t400"].append(expo(W["m1t400"], r4, band)); acc["canon"].append(expo(W["canon"], r4, band)); acc["ftrim"].append(expo(W["ftrim"], r4, band))
    for key, w in (("live", tl), ("V1", W["V1"]), ("m1t400", W["m1t400"]), ("canon", W["canon"]), ("ftrim", W["ftrim"])):
        s = dm(w) / np.abs(w).sum()
        for sname in DEEP: deep[key][sname].append(s[sidx[sname]])
    sl = sig.get(N, {}); caps.append({"N": N, "live_sel": sl.get("sel"), "live_cap": 2.5 / sl["sel"] if sl.get("sel") else None, "v1_nsel": nsel_v1, "v1_cap": 2.5 / nsel_v1, "v1_nmember": nmem_v1,
                                      "live_maxw": acc["live"][-1]["maxw"] / np.abs(tl).sum(), "v1_maxw": acc["V1"][-1]["maxw"] / np.abs(W["V1"]).sum()})
def M(k, q): return float(np.mean([e[q] for e in acc[k]]))
def SE(k1, k2): d = np.array([a["carry"] - b["carry"] for a, b in zip(acc[k1], acc[k2])]); return d.mean(), d.std(ddof=1) / np.sqrt(len(d))
print(f"{'book':10s} {'carry':>7s} {'pay_SN':>7s} {'pay_LP':>7s} {'LP':>6s} {'SN':>6s} {'band_g':>7s} {'band_pay':>8s} {'band_n':>6s} {'n':>4s}")
for k in ("canon", "m1t400", "V1", "V1_in450", "V1_inmem", "live", "ftrim"):
    print(f"{k:10s} {M(k,'carry'):+7.3f} {M(k,'pay_SN'):+7.3f} {M(k,'pay_LP'):+7.3f} {M(k,'LP'):6.3f} {M(k,'SN'):6.3f} {M(k,'band_g'):7.3f} {M(k,'band_pay'):+8.3f} {M(k,'band_n'):6.1f} {M(k,'n'):4.0f}")
print("ladder: V1 -> V1|450: %+.3f (se %.3f) | V1|450 -> V1|live members: %+.3f (se %.3f) | V1|members -> live: %+.3f (se %.3f) | live - V1 total: %+.3f (se %.3f) | live - ftrim(deployed form): %+.3f (se %.3f) | V1 - ftrim (FTRIM effect in replay): %+.3f (se %.3f)" % (
    *SE("V1_in450", "V1"), *SE("V1_inmem", "V1_in450"), *SE("live", "V1_inmem"), *SE("live", "V1"), *SE("live", "ftrim"), *SE("V1", "ftrim")))
print("\nper-name mean weight per unit gross (dm) at the 28 anchors, deep-negative-funding names:")
print(f"{'name':10s} {'rate4h':>8s} " + " ".join(f"{k:>8s}" for k in ("live", "V1", "m1t400", "canon", "ftrim")))
for sname in DEEP:
    rr = np.mean([rates(N)[0][sidx[sname]] for N in OV]) * 1e4
    print(f"{sname:10s} {rr:+8.2f} " + " ".join(f"{np.mean(deep[k][sname]):+8.4f}" for k in ("live", "V1", "m1t400", "canon", "ftrim")))
print("\nnsel / cap: live sel (producer signal row) mean %.1f -> cap 2.5/sel %.5f; V1 nsel mean %.1f (nmember %.0f) -> cap %.5f; max|w|/gross: live %.5f V1 %.5f" % (
    np.mean([c["live_sel"] for c in caps if c["live_sel"]]), np.mean([c["live_cap"] for c in caps if c["live_cap"]]), np.mean([c["v1_nsel"] for c in caps]), np.mean([c["v1_nmember"] for c in caps]), np.mean([c["v1_cap"] for c in caps]),
    np.mean([c["live_maxw"] for c in caps]), np.mean([c["v1_maxw"] for c in caps])))
print("  per anchor live_sel/v1_nsel:", " ".join(f"{c['live_sel']}/{int(c['v1_nsel'])}" for c in caps))
# B. rank-base test on single-anchor targets
print("\n== B. test (i): fund rank base -> single-anchor TARGET composition (no EMA), z = 0.21*xz(king pinned)+0.79*xz(fund|base), device sel/demean/L1/cap; per gross ==")
def target(z, sel, capw):
    w = np.where(sel, z, 0.0)
    if sel.sum() == 0: return None
    w[sel] -= w[sel].mean(); g = np.abs(w).sum()
    if g < 1e-9: return None
    w /= g; w = np.clip(w, -capw, capw); g2 = np.abs(w).sum(); return w / g2 if g2 > 1e-9 else w
resB = {}
for N in OV:
    i = prow[N]; r4, rn8 = rates(N); band = np.isfinite(rn8) & (rn8 <= -0.0010); a = INP["anchors"][str(N)]
    slow = np.array(a["slow"], float); qvk = np.array(a["qvk"], float); y4ok = np.array(a["y4ok"], bool); fe = FE[i]
    zk = np.nan_to_num(xz(slow))
    qv4h = np.expm1(np.clip(qvk, 0, 30)) * 48; rk = np.empty(NW, int); rk[np.argsort(-qvk)] = np.arange(NW)
    sel_rep = y4ok & (qv4h >= 2.5e5) & (rk < 400)
    zl = np.load(f"{WS}/state/weights/{N}.npz"); memL = np.zeros(NW, bool); memL[zl["members"].astype(np.int64)] = True
    sel_live_proxy = memL & (qv4h >= 2.5e5)   # producer's own qv gate uses its cache; proxy with meta qvk
    bases = {"829 panel (replay)": np.ones(NW, bool), "M1 base_syms (aux, today)": base_m1, "400 live members (producer @ these anchors)": memL}
    for bname, bm in bases.items():
        zf = np.nan_to_num(xz_in_base(fe, bm, fe))
        for fl in ("off", "zero"):
            for selname, sel in (("replay sel", sel_rep), ("live members sel", sel_live_proxy)):
                z = 0.21 * zk + 0.79 * zf
                if fl == "zero": z = np.where((z < 0) & band, 0.0, z)
                w = target(z, sel, 2.5 / max(int(sel.sum()), 1))
                if w is None: continue
                key = (bname, fl, selname); e = expo(w, r4, band); resB.setdefault(key, []).append(e)
print(f"{'base':44s} {'FTRIM':6s} {'sel':17s} {'carry':>7s} {'pay_SN':>7s} {'LP':>6s} {'SN':>6s} {'band_g':>7s} {'band_pay':>8s} {'band_n':>6s} {'n':>4s}")
for key, es in resB.items():
    m = {q: np.mean([e[q] for e in es]) for q in es[0]}
    print(f"{key[0]:44s} {key[1]:6s} {key[2]:17s} {m['carry']:+7.3f} {m['pay_SN']:+7.3f} {m['LP']:6.3f} {m['SN']:6.3f} {m['band_g']:7.3f} {m['band_pay']:+8.3f} {m['band_n']:6.1f} {m['n']:4.0f}")
# C. FTRIM name sets
print("\n== C. test (ii): FTRIM name sets at the 28 anchors ==")
jac = []; cnt = []
for N in OV:
    i = prow[N]; r4, rn8 = rates(N); band = np.isfinite(rn8) & (rn8 <= -0.0010); a = INP["anchors"][str(N)]
    slow = np.array(a["slow"], float); f10 = np.array(a["f10"], float); fe = FE[i]
    zf_fund = np.nan_to_num(xz(fe)); zk = np.nan_to_num(xz(slow)); z10 = np.nan_to_num(xz(f10))
    z_kc = 0.21 * zk + 0.79 * zf_fund; z_fc = 0.21 * z10 + 0.79 * zf_fund
    T_kc = set(np.where((z_kc < 0) & band)[0]); T_fc = set(np.where((z_fc < 0) & band)[0])
    tl = dm(vec(f"{WS}/state/target_live/{N}.json")); T_live = set(np.where((tl < 0) & band)[0]); T_band = set(np.where(band)[0])
    jac.append(len(T_kc & T_live) / max(len(T_kc | T_live), 1)); cnt.append((len(T_band), len(T_kc), len(T_fc), len(T_live), len(T_kc & T_live), len(T_live - T_kc), len(T_kc - T_live)))
c = np.array(cnt, float)
print("  mean counts: band names in panel %.1f | replay trimmed kc %.1f fc %.1f | live shorts in band (would be trimmed) %.1f | kc∩live %.1f | live-only %.1f | kc-only %.1f | Jaccard(kc,live) %.3f" % (*c.mean(0), np.mean(jac)))
print("  note: replay F10 preds are NaN at all 28 anchors (f10 finite = 0) => replay fc chain z = 0.79*xz(fund) here; kc and fc trimmed sets identical:", all(x[1] == x[2] for x in cnt))
# post-09-02 anchors: combo ftrim record vs live band shorts
LT = aux["ledger_tail"]
def r_last(s, N):
    led = LT.get(s)
    if not led: return None
    best = None
    for ft, r, iv in led:
        if ft <= N: best = (ft, r, iv)
        else: break
    if best is None or N - best[0] > 12 * 3600: return None
    return best
post = []
for fn_ in sorted(os.listdir(f"{WS}/state/target_combo")):
    if not fn_.endswith(".json"): continue
    N = int(fn_[:-5]); d = json.load(open(f"{WS}/state/target_combo/{N}.json")); ft = d.get("ftrim")
    if not ft: continue
    rn8 = np.full(NW, np.nan)
    for j, s in enumerate(psym):
        rl = r_last(s, N)
        if rl: rn8[j] = rl[1] * (8.0 / rl[2])
    band = np.isfinite(rn8) & (rn8 <= -0.0010); tl = dm(vec(f"{WS}/state/target_live/{N}.json")); short_band = set(psym[j] for j in np.where((tl < 0) & band)[0])
    names_kc = set(ft["names_kc"].keys()); post.append((N, len(names_kc), ft["n_fc"], len(short_band), len(names_kc & short_band), len(short_band - names_kc)))
    # sanity: all combo-trimmed names satisfy the band rule under the ledger rates
    bad = [s for s in names_kc if not (np.isfinite(rn8[sidx[s]]) and rn8[sidx[s]] <= -0.0010)]
    if bad: print("   WARN combo ftrim names not in ledger band:", f(N), bad)
print("  post-09-02 anchors (combo ftrim record active): n=%d | combo trimmed kc mean %.1f fc %.1f | live target shorts still in band %.1f (of which in combo's trimmed set %.1f; not trimmed %.1f = z>=0 or EMA residual)" % (
    len(post), np.mean([p[1] for p in post]), np.mean([p[2] for p in post]), np.mean([p[3] for p in post]), np.mean([p[4] for p in post]), np.mean([p[5] for p in post])))
print("   per anchor: " + " ".join(f"{f(p[0])}:{p[1]}/{p[3]}/{p[4]}" for p in post))
# D. INFERRED scaled bound
print("\n== D. INFERRED bound: fixed-seat deployed-form (pod_live_w3fix_callog_s42) net_ex per NAV if carry scaled by live/replay ratio ==")
fam = json.load(open(f"{OUT}/replay_family_existing.json")) if os.path.exists(f"{OUT}/replay_family_existing.json") else None
ratio = M("live", "carry") / M("ftrim", "carry"); ratio_v1 = M("V1", "carry") / M("ftrim", "carry")
print(f"  ratio live/replay(deployed form) = {M('live','carry'):.3f}/{M('ftrim','carry'):.3f} = {ratio:.3f}; ratio V1(no-FTRIM replay)/deployed = {ratio_v1:.3f}")
if fam:
    for tag in ("pod_live_w3fix_callog_s42", "pod_live_w3fix_calsimple_s42"):
        r = fam[tag]; ys = r["by_year"]
        for y in ("2024", "2025", "2026"):
            v = ys[y]; print(f"  {tag} {y}: net_ex {v['net_ex_perNAV']:+.3f} carry_ex {v['carry_ex_perNAV']:+.3f} -> scaled x{ratio:.2f}: {v['net_ex_perNAV'] - (ratio - 1) * v['carry_ex_perNAV']:+.3f} | x{ratio_v1:.2f}: {v['net_ex_perNAV'] - (ratio_v1 - 1) * v['carry_ex_perNAV']:+.3f}")
        a = r["2024on"]; print(f"  {tag} 2024on: net_ex {a['net_ex_perNAV']:+.4f} carry_ex {a['carry_ex_perNAV']:+.4f} -> scaled x{ratio:.2f}: {a['net_ex_perNAV'] - (ratio - 1) * a['carry_ex_perNAV']:+.3f} | x{ratio_v1:.2f}: {a['net_ex_perNAV'] - (ratio_v1 - 1) * a['carry_ex_perNAV']:+.3f}")
json.dump({"A": {k: acc[k] for k in acc}, "caps": caps, "B": {"|".join(k): v for k, v in resB.items()}, "C": cnt, "post": post}, open(f"{OUT}/structural_tests.json", "w"), indent=1, default=float)
