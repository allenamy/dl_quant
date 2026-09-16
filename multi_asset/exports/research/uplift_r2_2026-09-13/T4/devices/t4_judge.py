#!/usr/bin/env python3
"""t4_judge.py — pod2, CPU, read-only (PREREG_T4 §3 score layer, §4 book layer, §5 verdict).
Runs only after RECEIPT_T4_kings.json (K26/KF/AL/S0 pass) and RECEIPT_T4_book_drive.json (GATE PB pass) exist; asserts both.
Bootstrap = r18_judge.py boot() verbatim (UTC-day blocks, NB 2000, default_rng([20260905,k]), ratio of day sums / day counts).
Launch: env -i PATH=... HOME=/root /workspace/venv/bin/python devices/t4_judge.py PATH,HOME,LC_CTYPE
"""
import os, sys, json, time, hashlib, calendar
WHITE = set(x for x in sys.argv[1].split(",") if x) if len(sys.argv) > 1 else None
assert WHITE, "launch with a non-empty env whitelist as argv[1]"
BANNED = ('CAL', 'JUDGE', 'UPLIFT', 'PANEL', 'LOOK', 'WRULE', 'LEGS', 'PHI', 'FSEED', 'W3FIX', 'FTRIM', 'UMASK', 'SLOW', 'FPRED', 'MEMBERS_TOPN', 'COSTB', 'SLEEVE', 'KMOD', 'SEAT', 'RNSM', 'LTRIM', 'CDAMP', 'FUNDSCALE', 'FEMAT', 'TRADE_TOPN', 'REF_SKIP', 'PYTHON', 'OMP', 'MKL', 'R18', 'SMA', 'SBAND', 'FTPOS', 'OUT_TAG')
EXTRA = sorted(k for k in os.environ if k not in WHITE); assert EXTRA == [], ("ENV WHITELIST VIOLATION", EXTRA)
BAN = sorted(k for k in os.environ if k.startswith(BANNED)); assert BAN == [], ("CALIBER FLAG PRESENT", BAN)
import numpy as np
from scipy.stats import rankdata
T4 = "/workspace/uplift_r2_2026-09-13/T4"; R18 = "/workspace/uplift_2026-09-11/r18_foundation"
PREREG_SHA = "0f94b754c9ca4c6e65c3f2a63146dab7036f37862abd2210cbbfcef661aab4dd"; DER_SHA = "9b8a6323e8f0ac31ecb4046f6759dce09ba89645cbfc356db71f51c662b2c5c4"
def sha(p):
    h = hashlib.sha256()
    with open(os.path.realpath(p), "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
assert sha(T4 + "/PREREG_T4_king_feature_skew_2026-09-13.md") == PREREG_SHA
KR = json.load(open(T4 + "/receipts/RECEIPT_T4_kings.json")); G = KR["gates"]
assert G["K26"]["PASS"] and G["KF_PASS_bitwise"] and G["AL"]["PASS"] and G["S0_PASS"], G
BD = json.load(open(T4 + "/receipts/RECEIPT_T4_book_drive.json")); assert BD["gate"]["PB"]["PASS"], BD["gate"]
t0 = time.time()
NB = 2000; UB = calendar.timegm((2026, 8, 30, 20, 0, 0)); K24 = calendar.timegm((2024, 1, 1, 0, 0, 0)); Y26T = calendar.timegm((2026, 1, 1, 0, 0, 0))
# ------------------------------------------------------------------ axes and masks (r18_judge.py load())
def load_arm(p, base, king):
    Z = np.load(p, allow_pickle=True); C = [str(c) for c in Z["cols"]]; rec = np.asarray(Z["d30_n2_c42_rec"], float); cfg = json.loads(str(Z["config_json"]))
    assert cfg["CAL"] == "log" and cfg["PHI"] == 0.45 and cfg["LEGS"] == "101" and cfg["WRULE"] == "msharpe" and cfg["W3FIX"] is None and cfg["UMASK_SCOPE"] == "m1" and cfg["LOOK"] == 900 and cfg["FTRIM"] == "zero" and cfg["MEMBERS_TOPN"] == 829, cfg
    assert cfg["COSTB_JSON"].endswith("costb_PWR_G230k.json") and cfg["UPLIFT"]["self_sha256"] == DER_SHA
    exp_slow = {"K0": ("SLOW_v3_on_v4axis.npy", "K0_v4axis.npy"), "K1": ("K1_v4axis.npy",), "K0f": ("K0f_v4axis.npy",)}[king]
    assert cfg["SLOW_NPY"].endswith(exp_slow), (p, cfg["SLOW_NPY"])
    r18 = cfg["R18"]; want = {"C0": dict(R18_ELIG=0, R18_WARM=0), "NW": dict(R18_ELIG=1, R18_WARM=1)}[base]
    for k, v in want.items(): assert r18[k] == v, (p, k, r18[k])
    assert r18["SMA"] == 0.1 and r18["SBAND"] == 2.5e-4
    col = lambda k: rec[:, C.index(k)]
    ts = col("ts").astype(np.int64); gt = col("gross_total")
    d = dict(ts=ts, g=col("net_ex") / gt, pnl=col("pnl_ex") / gt, car=col("carry_ex") / gt, cst=col("cost_ex") / gt, tau=col("turnover") / gt, w3k=col("w3_king"), lk=col("leg_king"), sha=sha(p), path=p, slow=cfg["SLOW_NPY"])
    assert np.allclose(d["pnl"] - d["car"] - d["cst"], d["g"], atol=1e-9)
    return d
ARMS = {}
ARMS[("C0", "42", "K0")] = load_arm(T4 + "/arms/PB_K0_C0_s42.npz", "C0", "K0")
ARMS[("C0", "2027", "K0")] = load_arm(R18 + "/arms/C0_s2027.npz", "C0", "K0")
ARMS[("NW", "42", "K0")] = load_arm(R18 + "/arms/NW_s42.npz", "NW", "K0")
ARMS[("NW", "2027", "K0")] = load_arm(R18 + "/arms/NW_s2027.npz", "NW", "K0")
for b in ("C0", "NW"):
    for s in ("42", "2027"): ARMS[(b, s, "K1")] = load_arm(T4 + f"/arms/K1_{b}_s{s}.npz", b, "K1")
for s in ("42", "2027"): ARMS[("C0", s, "K0f")] = load_arm(T4 + f"/arms/K0f_C0_s{s}.npz", "C0", "K0f")
ts = ARMS[("C0", "42", "K0")]["ts"]
for k, x in ARMS.items(): assert np.array_equal(x["ts"], ts), k
WT = ts <= UB; WA = WT.copy(); WA[:900] = False; KL = WA & (ts >= K24); Y26 = WA & (ts >= Y26T)
assert WA.sum() == 9138 and KL.sum() == 5838, (WA.sum(), KL.sum())
DAY = np.array([time.strftime("%Y%m%d", time.gmtime(int(t))) for t in ts]); YEAR = np.array([time.gmtime(int(t)).tm_year for t in ts])
_DRAW = {}
def draws(nd):
    if nd not in _DRAW: _DRAW[nd] = np.stack([np.random.default_rng([20260905, k]).integers(0, nd, nd) for k in range(NB)])
    return _DRAW[nd]
def boot(d, mask):   # r18_judge.py boot() (CI95 part) verbatim
    idx = np.nonzero(mask)[0]; dd = {}
    for k in idx: dd.setdefault(DAY[k], []).append(k)
    keys = sorted(dd); tot = np.array([d[dd[k]].sum() for k in keys]); cnt = np.array([len(dd[k]) for k in keys], float); nd = len(keys)
    r = draws(nd); ms = tot[r].sum(1) / cnt[r].sum(1)
    return dict(ci95=[float(np.percentile(ms, 2.5)), float(np.percentile(ms, 97.5))], se=float(ms.std(ddof=1)), n_days=nd)
def shp(x): return float(x.mean() / x.std(ddof=1) * np.sqrt(2190))
def excl0(ci): return bool(ci[0] > 0 or ci[1] < 0)
# ------------------------------------------------------------------ score layer (§3)
M4P = "/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz"; M4 = np.load(M4P, allow_pickle=True); E4 = M4["E_ts"].astype(np.int64); Y4S = M4["y4"]
E4row = {int(t): k for k, t in enumerate(E4)}
K = {k: np.load(KR["outputs"][k]["v4axis"]) for k in ("K0", "K1", "K0f")}
for k in K: assert sha(KR["outputs"][k]["v4axis"]) == KR["outputs"][k]["v4axis_sha256"]
PANP = "/workspace/data/wide_panel_4h_v2ext.npz"; PW = np.load(PANP, allow_pickle=True); pw_row = {int(t): j for j, t in enumerate(PW["ts"].astype(np.int64))}; IV = PW["f_fund_iv"]
TG = np.load("/workspace/dlw_v4raw/data/dlw_targets.npz", allow_pickle=True)
SYM_OK = bool([str(s) for s in PW["symbols"]] == [str(s) for s in TG["symbols"]] == [str(s) for s in np.load(T4 + "/arms/PB_K0_C0_s42.npz", allow_pickle=True)["symbols"]])
assert SYM_OK, "symbol axes differ (panel / dlw targets / replay)"
def spear(a, b):
    ra = rankdata(a); rb = rankdata(b); ra -= ra.mean(); rb -= rb.mean()
    den = np.sqrt((ra * ra).sum() * (rb * rb).sum()); return float((ra * rb).sum() / den) if den > 0 else np.nan
def dec(x):
    n = len(x); r = rankdata(x); return np.minimum(9, np.floor(10 * (r - 0.5) / n)).astype(np.int8)
CLS = ("all", "4h", "1h", "8h", "other")
nT = len(ts)
PER = {f"rho_{p}": np.full(nT, np.nan) for p in ("K1", "K0f")}
PER.update({f"IC_{k}": np.full(nT, np.nan) for k in ("K0", "K1", "K0f", "K0_onK0fcells")})
DECCH = {p: {c: np.zeros(nT) for c in CLS} for p in ("K1", "K0f")}; DECN = {p: {c: np.zeros(nT) for c in CLS} for p in ("K1", "K0f")}
king_finite_WA = np.zeros(nT, bool); no_row4 = 0
for i in np.nonzero(WA)[0]:
    k4 = E4row.get(int(ts[i]))
    if k4 is None: no_row4 += 1; continue
    k0 = K["K0"][k4]
    if np.isfinite(k0).any(): king_finite_WA[i] = True
    j = pw_row.get(int(ts[i])); ivrow = IV[j] if j is not None else np.full(829, np.nan)
    y = Y4S[k4]
    for p in ("K1", "K0f"):
        kp = K[p][k4]; c = np.isfinite(k0) & np.isfinite(kp)
        if c.sum() < 50: continue
        a, b = k0[c], kp[c]; PER[f"rho_{p}"][i] = spear(a, b)
        ch = dec(a) != dec(b); iv = ivrow[c]
        cls = {"all": np.ones(len(a), bool), "4h": iv == 4.0, "1h": iv == 1.0, "8h": iv == 8.0}; cls["other"] = ~(cls["4h"] | cls["1h"] | cls["8h"])
        for cn, msk in cls.items(): DECCH[p][cn][i] = ch[msk].sum(); DECN[p][cn][i] = msk.sum()
        cy = c & np.isfinite(y)
        if cy.sum() >= 50:
            if p == "K1": PER["IC_K0"][i] = spear(k0[cy], y[cy]); PER["IC_K1"][i] = spear(kp[cy], y[cy])
            else: PER["IC_K0_onK0fcells"][i] = spear(k0[cy], y[cy]); PER["IC_K0f"][i] = spear(kp[cy], y[cy])
PER["dIC_K1"] = PER["IC_K1"] - PER["IC_K0"]; PER["dIC_K0f"] = PER["IC_K0f"] - PER["IC_K0_onK0fcells"]
WIN = {"W_ALPHA_kingfinite": WA & king_finite_WA, "KING_LIVE": KL, "Y2026": Y26}
SCORE = dict(windows_n={w: int(m.sum()) for w, m in WIN.items()}, W_ALPHA_kingfinite_equals_KING_LIVE=bool(np.array_equal(WA & king_finite_WA, KL)), anchors_without_v4_row=no_row4,
             first_king_finite_anchor_in_WA=time.strftime("%Y-%m-%d %HZ", time.gmtime(int(ts[np.nonzero(WA & king_finite_WA)[0][0]]))))
for w, m in WIN.items():
    o = {}
    for p in ("K1", "K0f"):
        r = PER[f"rho_{p}"]; mm = m & np.isfinite(r)
        o[f"spearman_K0_vs_{p}"] = dict(n=int(mm.sum()), mean=float(r[mm].mean()), median=float(np.median(r[mm])), p1=float(np.percentile(r[mm], 1)), p5=float(np.percentile(r[mm], 5)), min=float(r[mm].min()))
        o[f"decile_change_share_{p}"] = {c: dict(changed=int(DECCH[p][c][m].sum()), cells=int(DECN[p][c][m].sum()), share=float(DECCH[p][c][m].sum() / max(DECN[p][c][m].sum(), 1))) for c in CLS}
    for lab, arr in (("IC_K0", PER["IC_K0"]), ("IC_K1", PER["IC_K1"]), ("dIC_K1_minus_K0", PER["dIC_K1"]), ("IC_K0f", PER["IC_K0f"]), ("dIC_K0f_minus_K0", PER["dIC_K0f"])):
        mm = m & np.isfinite(arr); b = boot(arr, mm)
        o[lab] = dict(n=int(mm.sum()), mean=float(arr[mm].mean()), **b, ci95_excl0=excl0(b["ci95"]),
                      by_year={int(yv): dict(n=int((mm & (YEAR == yv)).sum()), mean=float(arr[mm & (YEAR == yv)].mean())) for yv in sorted(set(YEAR[mm].tolist()))})
    SCORE[w] = o
    print("SCORE", w, json.dumps({k: (v if not isinstance(v, dict) else {kk: vv for kk, vv in v.items() if kk != "by_year"}) for k, v in o.items()}, default=str)[:3000], flush=True)
# ------------------------------------------------------------------ book layer (§4)
def block(arm, base, mask):   # r18_judge.py block() (CI95 part)
    d = arm["g"] - base["g"]; n = int(mask.sum()); b = boot(d, mask)
    o = dict(n=n, g_arm=float(arm["g"][mask].mean()), g_base=float(base["g"][mask].mean()), dg=float(d[mask].mean()), **b, sharpe_arm=shp(arm["g"][mask]), sharpe_base=shp(base["g"][mask]),
             dpnl=float((arm["pnl"] - base["pnl"])[mask].mean()), dcarry=float((arm["car"] - base["car"])[mask].mean()), dcost=float((arm["cst"] - base["cst"])[mask].mean()),
             tau_arm=float(arm["tau"][mask].mean()), tau_base=float(base["tau"][mask].mean()), n_anchors_g_differs=int((np.abs(d[mask]) > 1e-12).sum()),
             first_anchor_g_differs=(time.strftime("%Y-%m-%d %HZ", time.gmtime(int(ts[mask][np.nonzero(np.abs(d[mask]) > 1e-12)[0][0]]))) if (np.abs(d[mask]) > 1e-12).any() else None),
             w3_king_arm=float(arm["w3k"][mask].mean()), w3_king_base=float(base["w3k"][mask].mean()), leg_king_arm=float(arm["lk"][mask].mean()), leg_king_base=float(base["lk"][mask].mean()))
    o["dtau_pct"] = 100 * (o["tau_arm"] - o["tau_base"]) / o["tau_base"]; o["ci95_excl0"] = excl0(o["ci95"]); o["ci95_halfwidth"] = (o["ci95"][1] - o["ci95"][0]) / 2
    assert abs(o["dpnl"] - o["dcarry"] - o["dcost"] - o["dg"]) < 1e-9
    o["by_year"] = {int(yv): dict(n=int((mask & (YEAR == yv)).sum()), dg=float(d[mask & (YEAR == yv)].mean())) for yv in sorted(set(YEAR[mask].tolist()))}
    return o
BOOK = {}
pre2024 = WT & (ts < K24)
for (b, s, k), arm in ARMS.items():
    if k == "K0": continue
    base = ARMS[(b, s, "K0")]; key = f"{k}_minus_K0|{b}|s{s}"
    BOOK[key] = {w: block(arm, base, m) for w, m in (("W_ALPHA", WA), ("KING_LIVE", KL), ("Y2026", Y26))}
    BOOK[key]["pre2024_max_abs_dg"] = float(np.abs(arm["g"] - base["g"])[pre2024].max())
    print("BOOK", key, json.dumps({w: {kk: vv for kk, vv in v.items() if kk != "by_year"} for w, v in BOOK[key].items() if isinstance(v, dict)}, default=str), flush=True)
# ------------------------------------------------------------------ verdict (§5)
A_c0 = [BOOK[f"K1_minus_K0|C0|s{s}"]["KING_LIVE"] for s in ("42", "2027")]
condA = bool(all(x["ci95_excl0"] for x in A_c0) and (np.sign(A_c0[0]["dg"]) == np.sign(A_c0[1]["dg"])))
A_nw = [BOOK[f"K1_minus_K0|NW|s{s}"]["KING_LIVE"] for s in ("42", "2027")]
condA_nw = bool(all(x["ci95_excl0"] for x in A_nw) and (np.sign(A_nw[0]["dg"]) == np.sign(A_nw[1]["dg"])))
B_ic = SCORE["KING_LIVE"]["dIC_K1_minus_K0"]; condB = bool(B_ic["ci95_excl0"])
A_f = [BOOK[f"K0f_minus_K0|C0|s{s}"]["KING_LIVE"] for s in ("42", "2027")]
condA_f = bool(all(x["ci95_excl0"] for x in A_f) and (np.sign(A_f[0]["dg"]) == np.sign(A_f[1]["dg"]))); condB_f = bool(SCORE["KING_LIVE"]["dIC_K0f_minus_K0"]["ci95_excl0"])
verdict = "MATERIAL" if (condA or condB) else "NOT MATERIAL (at this resolution)"

# ⚠ 更正 DEV-04 · P2 · AUD-KB K4 2026-09-16(原句字节保留, 不改写): 采用 FX-EVAL K2 规则 R-T4(δ D1 = 0.05 / D4 = 0.003)替换 L150 谓词; 本次存档读数重标 = INCONCLUSIVE(RELABEL_TABLE_K2 T4 行), 不另立标签

labels = []
if condA != condA_nw: labels.append("BASE-DEPENDENT")
if condA_f or condB_f: labels.append("INSTRUMENT-FLAG")
VERDICT = dict(verdict=verdict, labels=labels, condA_C0_KL_both_seeds_same_sign=condA, condB_dIC_KL=condB, condA_NW_KL=condA_nw, null_K0f_condA=condA_f, null_K0f_condB=condB_f,
               resolution=dict(book_dg_ci95_halfwidth_C0_KL={s: A_c0[i]["ci95_halfwidth"] for i, s in enumerate(("42", "2027"))}, dIC_ci95_halfwidth_KL=(B_ic["ci95"][1] - B_ic["ci95"][0]) / 2),
               readings=dict(book_C0_KL={s: dict(dg=A_c0[i]["dg"], ci95=A_c0[i]["ci95"]) for i, s in enumerate(("42", "2027"))}, book_NW_KL={s: dict(dg=A_nw[i]["dg"], ci95=A_nw[i]["ci95"]) for i, s in enumerate(("42", "2027"))},
                             dIC_KL=dict(mean=B_ic["mean"], ci95=B_ic["ci95"]), null_book_C0_KL={s: dict(dg=A_f[i]["dg"], ci95=A_f[i]["ci95"]) for i, s in enumerate(("42", "2027"))},
                             null_dIC_KL=dict(mean=SCORE["KING_LIVE"]["dIC_K0f_minus_K0"]["mean"], ci95=SCORE["KING_LIVE"]["dIC_K0f_minus_K0"]["ci95"])))
RC = dict(self_sha256=sha(os.path.abspath(__file__)), prereg_sha256=PREREG_SHA, kings_receipt_sha256=sha(T4 + "/receipts/RECEIPT_T4_kings.json"), book_drive_receipt_sha256=sha(T4 + "/receipts/RECEIPT_T4_book_drive.json"),
          inputs={M4P: sha(M4P), PANP: sha(PANP)}, arms={f"{b}|s{s}|{k}": dict(path=x["path"], sha256=x["sha"], slow=x["slow"]) for (b, s, k), x in ARMS.items()},
          score=SCORE, book=BOOK, verdict=VERDICT, env=dict(whitelist=sorted(WHITE), actual={k: os.environ[k] for k in sorted(os.environ)}), numpy=np.__version__,
          built_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), wall_s=round(time.time() - t0, 1))
json.dump(RC, open(T4 + "/receipts/RECEIPT_T4_judge.json", "w"), indent=1, default=str)
np.savez_compressed(T4 + "/receipts/T4_score_per_anchor.npz", ts=ts, WA=WA, KL=KL, Y26=Y26, **PER, **{f"decch_{p}_{c}": DECCH[p][c] for p in DECCH for c in CLS}, **{f"decn_{p}_{c}": DECN[p][c] for p in DECN for c in CLS})
print("VERDICT", json.dumps(VERDICT, indent=1, default=str)); print("DONE_t4_judge", RC["wall_s"])
