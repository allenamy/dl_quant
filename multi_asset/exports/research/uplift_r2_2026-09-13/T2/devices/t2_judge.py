#!/usr/bin/env python3
"""t2_judge.py — PREREG_T2 §6 statistics and §6.2 decision for ARM-N / ARM-Nσ / ARM-SK on the A0 base (verdict) and the NW
base (robustness reading), read-only, CPU. Runs only after RECEIPT_T2_drive.json has GATE P / PC-0 / PC-1 PASS and the C2 block.
g = net_ex/gross_total (bps/anchor/unit gross). Paired Δg vs the SAME-SEED baseline of the same base (reference name printed).
UTC-day block bootstrap 2000, default_rng([20260905,k]) (r18 boot() verbatim); CI95 decisive, CI99-K (K=3) reported.
Tail = r18 tailrow at L=2.0, M=1.0 on W_TAIL (UTC-day compounding, NAV prepend 1.0, true peak-to-trough).
Caliber is read from each artifact's config_json, never from the environment.
Launch: env -i PATH=... HOME=/root /workspace/venv/bin/python devices/t2_judge.py PATH,HOME,LC_CTYPE
"""
import os, sys, json, time, hashlib, calendar
WHITE = set(x for x in sys.argv[1].split(",") if x) if len(sys.argv) > 1 else None
assert WHITE, "launch with a non-empty env whitelist as argv[1]"
BANNED = ('CAL', 'JUDGE', 'UPLIFT', 'PANEL', 'LOOK', 'WRULE', 'LEGS', 'PHI', 'FSEED', 'W3FIX', 'FTRIM', 'UMASK', 'SLOW', 'FPRED', 'MEMBERS_TOPN', 'COSTB', 'SLEEVE', 'KMOD', 'SEAT', 'RNSM', 'LTRIM', 'CDAMP', 'FUNDSCALE', 'FEMAT', 'TRADE_TOPN', 'REF_SKIP', 'PYTHON', 'OMP', 'MKL', 'R15', 'R18', 'SMA', 'SBAND', 'FTPOS', 'OUT_TAG', 'T2')
EXTRA = sorted(k for k in os.environ if k not in WHITE); assert EXTRA == [], ("ENV WHITELIST VIOLATION", EXTRA)
BAN = sorted(k for k in os.environ if k.startswith(BANNED)); assert BAN == [], ("CALIBER FLAG PRESENT", BAN)
ENV = dict(env_whitelist=sorted(WHITE), env_actual={k: os.environ[k] for k in sorted(os.environ)}, launch_cmdline=" ".join(sys.argv))
import numpy as np
ENV.update(python=sys.version.split()[0], numpy=np.__version__)
T0 = time.time()
T2 = "/workspace/uplift_r2_2026-09-13/T2"
PREREG_SHA = "981293b02b2ddae6574fa6dcf8db9b09a65cfa9f122a8b72d7e604ad5ec87eca"; DER_SHA = "380d6265082c67742a8cf47f844d76cf0e3cc3ca25557b29bdaf6c747907d341"
def sha(p):
    h = hashlib.sha256()
    with open(os.path.realpath(p), "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
assert sha(T2 + "/PREREG_T2_carry_net_sizing_2026-09-13.md") == PREREG_SHA
DR = json.load(open(T2 + "/receipts/RECEIPT_T2_drive.json")); assert DR["prereg_sha256"] == PREREG_SHA and DR["derived_device_sha256"] == DER_SHA
assert DR["gate"]["P"]["PASS"] and DR["gate"]["PC0"]["PASS"] and DR["gate"]["PC1"]["PASS"] and DR["STOP"] is False, "gates"
KR = json.load(open(T2 + "/receipts/RECEIPT_T2_kappa_main.json")); assert KR["C1"]["PASS"] and KR["prereg_sha256"] == PREREG_SHA
NAME_OK = bool(DR["name_arms_run"]); C2 = DR["C2"]
K = 3; ALPHA_K = 0.05 / K; PCT_K = (100 * ALPHA_K / 2, 100 * (1 - ALPHA_K / 2)); NB = 2000; RES_BPS = 0.23; CEIL = 0.11; TRIP = 0.165
UB = calendar.timegm((2026, 8, 30, 20, 0, 0)); K24 = calendar.timegm((2024, 1, 1, 0, 0, 0)); LIVE0 = calendar.timegm((2026, 8, 26, 0, 0, 0))
HALT = -0.04; ALERT = -0.0268; DDLIM = -0.25
SEEDS = ("42", "2027"); ARMS = (("N", "ARM-N", "name", "scalar"), ("Ns", "ARM-Nσ", "name", "sigma"), ("SK", "ARM-SK", "seat", "scalar")) if NAME_OK else (("SK", "ARM-SK", "seat", "scalar"),)
def load(tag, base, mode, kcol):
    p = T2 + "/arms/%s.npz" % tag; Z = np.load(p, allow_pickle=True); C = [str(c) for c in Z["cols"]]; rec = np.asarray(Z["d30_n2_c42_rec"], float); cfg = json.loads(str(Z["config_json"]))
    assert cfg["CAL"] == "log" and cfg["PHI"] == 0.45 and cfg["LEGS"] == "101" and cfg["WRULE"] == "msharpe" and cfg["W3FIX"] is None and cfg["UMASK_SCOPE"] == "m1" and cfg["LOOK"] == 900 and cfg["FTRIM"] == "zero" and cfg["MEMBERS_TOPN"] == 829 and cfg["FTPOS"] == 0 and cfg["SEATNET"] == 0, cfg
    assert cfg["COSTB_JSON"].endswith("costb_PWR_G230k.json") and cfg["SLOW_NPY"].endswith("SLOW_v3_on_v4axis.npy") and cfg["UPLIFT"]["self_sha256"] == DER_SHA and cfg["T2"]["prereg_sha256"] == PREREG_SHA, cfg
    assert cfg["T2"]["T2_MODE"] == mode and cfg["T2"]["T2_KCOL"] == kcol and cfg["T2"]["T2_KFORCE"] == "" and cfg["T2"]["T2_CLEAD"] == 0, cfg["T2"]
    assert (cfg["R18"]["R18_ELIG"], cfg["R18"]["R18_WARM"]) == ((0, 0) if base == "A0" else (1, 1)), cfg["R18"]
    if mode != "off": assert cfg["T2"]["T2_KPATH_sha256"] == KR["path_outputs"]["main"]["sha256"], "arm must read the main kappa path"
    col = lambda k: rec[:, C.index(k)]
    ts = col("ts").astype(np.int64); gt = col("gross_total")
    d = dict(tag=tag, ts=ts, gt=gt, g=col("net_ex") / gt, pnl=col("pnl_ex") / gt, car=col("carry_ex") / gt, cst=col("cost_ex") / gt, tau=col("turnover") / gt, tau_raw=col("turnover"),
             w3k=col("w3_king"), w3f=col("w3_fund"), nl=col("netlong"), cfg=cfg, sha=sha(p), path=p, cols=C, rec=rec)
    assert np.allclose(d["pnl"] - d["car"] - d["cst"], d["g"], atol=1e-9)
    d["WT"] = ts <= UB; d["WA"] = d["WT"].copy(); d["WA"][:900] = False; assert d["WA"].sum() == 9138 and d["WT"].sum() == 10038
    d["KL"] = ts >= K24; assert (d["WA"] & d["KL"]).sum() == 5838
    d["LV"] = (ts >= LIVE0) & (ts <= UB); assert d["LV"].sum() == 30
    if "d30_n2_c42_T2A" in Z: d["aux"] = np.asarray(Z["d30_n2_c42_T2A"], float); d["aux_cols"] = [str(c) for c in Z["d30_n2_c42_T2A_cols"]]; assert np.array_equal(d["aux"][:, 0].astype(np.int64), ts)
    return d
BASE = {(b, s): load("GP_%s_s%s" % (b, s), b, "off", "scalar") for b in ("A0", "NW") for s in SEEDS}
ARM = {(a, b, s): load("%s_%s_s%s" % (a, b, s), b, mode, kcol) for a, _, mode, kcol in ARMS for b in ("A0", "NW") for s in SEEDS}
ts = BASE[("A0", "42")]["ts"]; WA = BASE[("A0", "42")]["WA"]; WT = BASE[("A0", "42")]["WT"]; KL = BASE[("A0", "42")]["KL"]; LV = BASE[("A0", "42")]["LV"]
for k, x in list(BASE.items()) + list(ARM.items()): assert np.array_equal(x["ts"], ts), k
assert abs(BASE[("A0", "42")]["g"][WA].mean() - 0.6341957) < 5e-7 and abs(BASE[("A0", "42")]["tau"][WA].mean() - 0.0540270) < 5e-7
DAY = np.array([time.strftime("%Y%m%d", time.gmtime(int(t))) for t in ts]); YEAR = np.array([time.gmtime(int(t)).tm_year for t in ts]); DAYS = (ts // 86400) * 86400
# ------------------------------------------------------------------ r18 kernel (verbatim)
_DRAW = {}
def draws(nd):
    if nd not in _DRAW: _DRAW[nd] = np.stack([np.random.default_rng([20260905, k]).integers(0, nd, nd) for k in range(NB)])
    return _DRAW[nd]
def boot(d, mask):
    idx = np.nonzero(mask)[0]; dd = {}
    for k in idx: dd.setdefault(DAY[k], []).append(k)
    keys = sorted(dd); tot = np.array([d[dd[k]].sum() for k in keys]); cnt = np.array([len(dd[k]) for k in keys], float); nd = len(keys)
    r = draws(nd); ms = tot[r].sum(1) / cnt[r].sum(1)
    return dict(ci95=[float(np.percentile(ms, 2.5)), float(np.percentile(ms, 97.5))], ci99K=[float(np.percentile(ms, PCT_K[0])), float(np.percentile(ms, PCT_K[1]))], se=float(ms.std(ddof=1)), n_days=nd)
def shp(x): return float(x.mean() / x.std(ddof=1) * np.sqrt(2190)) if len(x) > 2 and x.std(ddof=1) > 0 else None
def block(arm, base, mask, ref_name):
    d = arm["g"] - base["g"]; n = int(mask.sum()); b = boot(d, mask)
    o = dict(reference=ref_name, n=n, g_arm=float(arm["g"][mask].mean()), g_base=float(base["g"][mask].mean()), dg=float(d[mask].mean()), **b, sharpe_arm=shp(arm["g"][mask]), sharpe_base=shp(base["g"][mask]), sharpe_se=float(np.sqrt(2190 / n)),
             dpnl=float((arm["pnl"] - base["pnl"])[mask].mean()), dcarry=float((arm["car"] - base["car"])[mask].mean()), dcost=float((arm["cst"] - base["cst"])[mask].mean()),
             carry_arm=float(arm["car"][mask].mean()), carry_base=float(base["car"][mask].mean()), pnl_arm=float(arm["pnl"][mask].mean()), pnl_base=float(base["pnl"][mask].mean()), cost_arm=float(arm["cst"][mask].mean()), cost_base=float(base["cst"][mask].mean()),
             tau_matched_arm=float(arm["tau"][mask].mean()), tau_matched_base=float(base["tau"][mask].mean()), gross_arm=float(arm["gt"][mask].mean()), gross_base=float(base["gt"][mask].mean()),
             n_anchors_g_differs=int((np.abs(d[mask]) > 1e-12).sum()))
    o["dsharpe"] = (o["sharpe_arm"] - o["sharpe_base"]) if (o["sharpe_arm"] is not None and o["sharpe_base"] is not None) else None
    o["dtau_pct"] = 100 * (o["tau_matched_arm"] - o["tau_matched_base"]) / o["tau_matched_base"]
    o["price_given_up_per_unit_carry_saved"] = (o["dpnl"] / o["dcarry"]) if abs(o["dcarry"]) > 1e-12 else None
    assert abs(o["dpnl"] - o["dcarry"] - o["dcost"] - o["dg"]) < 1e-9
    o["ci95_excl0"] = bool(o["ci95"][0] > 0 or o["ci95"][1] < 0); o["ci99K_excl0"] = bool(o["ci99K"][0] > 0 or o["ci99K"][1] < 0); o["below_resolution"] = bool(abs(o["dg"]) < RES_BPS)
    return o
def dayret(g, mask, L):
    idx = np.nonzero(mask)[0]; ud, inv = np.unique(DAYS[idx], return_inverse=True); out = np.ones(len(ud))
    np.multiply.at(out, inv, 1.0 + L * g[idx] * 1e-4); return ud, out - 1.0
def tailrow(g, mask, L=2.0, M=1.0):
    ud, rd = dayret(g, mask, L); mu = rd.mean(); rs = mu + M * (rd - mu)
    nav = np.concatenate([[1.0], np.cumprod(1.0 + rs)]); dd = nav / np.maximum.accumulate(nav) - 1.0; it = int(np.argmin(dd)); ip = int(np.argmax(nav[:it + 1]))
    yrs = (ud[-1] - ud[0]) / (365.25 * 86400); w = int(np.argmin(rs))
    return dict(L=L, M=M, n_days=int(len(ud)), maxdd=float(dd.min()), maxdd_peak=time.strftime("%Y-%m-%d", time.gmtime(int(ud[ip - 1]))) if ip > 0 else "start", maxdd_trough=time.strftime("%Y-%m-%d", time.gmtime(int(ud[it - 1]))),
                worst_day=time.strftime("%Y-%m-%d", time.gmtime(int(ud[w]))), worst_day_ret=float(rs[w]), halt=int((rs <= HALT).sum()), alert=int((rs <= ALERT).sum()), halt_per_yr=float((rs <= HALT).sum() / yrs), sd_day=float(rs.std(ddof=1)),
                ann_ret=float(nav[-1] ** (365.25 * 86400 / (ud[-1] - ud[0] + 86400)) - 1.0))
def per_year(arm, base, mask):
    out = {}
    for y in sorted(set(YEAR[mask].tolist())):
        m = mask & (YEAR == y); out[int(y)] = dict(n=int(m.sum()), g_arm=float(arm["g"][m].mean()), g_base=float(base["g"][m].mean()), dg=float((arm["g"] - base["g"])[m].mean()), sharpe_arm=shp(arm["g"][m]), sharpe_base=shp(base["g"][m]),
                                             dcarry=float((arm["car"] - base["car"])[m].mean()), dpnl=float((arm["pnl"] - base["pnl"])[m].mean()))
    return out
# ------------------------------------------------------------------ sigma bins (causal, from the main path) mapped to rec rows
KP = np.load(KR["path_outputs"]["main"]["path"], allow_pickle=True); assert sha(KR["path_outputs"]["main"]["path"]) == KR["path_outputs"]["main"]["sha256"]
kmap = {int(t): i for i, t in enumerate(KP["E_ts"].astype(np.int64))}; ridx = np.array([kmap[int(t)] for t in ts])
BIN = KP["bin_sigma"][ridx]; KAPS = KP["kappa_scalar"][ridx]; LAMS = KP["lam_scalar"][ridx]
def bins(arm, base, mask):
    o = {}
    for b in (0, 1, 2):
        m = mask & (BIN == b)
        if m.sum() < 30: o[b] = dict(n=int(m.sum())); continue
        d = arm["g"] - base["g"]; bb = boot(d, m); o[b] = dict(n=int(m.sum()), dg=float(d[m].mean()), ci95=bb["ci95"], n_days=bb["n_days"], g_base=float(base["g"][m].mean()), g_arm=float(arm["g"][m].mean()))
    return o
def name_aux(arm, mask):
    if "aux" not in arm: return None
    A = arm["aux"]; c = arm["aux_cols"]; col = lambda k: A[:, c.index(k)]
    used = col("name_path_used") > 0.5; m = mask & used
    return dict(frac_anchors_path_used=float(used[mask].mean()), frac_anchors_lam_zero_pure_carry_rank=float((m & (col("lam_name") == 0.0)).sum() / max(mask.sum(), 1)),
                mean_n_fz_changed=float(col("n_fz_changed")[mask].mean()), mean_abs_dfz_used=float(col("mean_abs_dfz")[m].mean()) if m.any() else None, mean_corr_fz_book_vs_fz_used=float(np.nanmean(col("corr_fz_book_vs_fz")[m])) if m.any() else None,
                kappa_mean_used=float(col("kappa_name")[m].mean()) if m.any() else None)
def seat_path(arm, base, mask):
    q = lambda x: [float(v) for v in np.percentile(x, [10, 50, 90])]
    return dict(w3_king_arm=float(arm["w3k"][mask].mean()), w3_king_base=float(base["w3k"][mask].mean()), pct_arm=q(arm["w3k"][mask]), pct_base=q(base["w3k"][mask]), mean_abs_dw3_king=float(np.abs(arm["w3k"] - base["w3k"])[mask].mean()),
                by_year={int(y): dict(arm=float(arm["w3k"][mask & (YEAR == y)].mean()), base=float(base["w3k"][mask & (YEAR == y)].mean())) for y in sorted(set(YEAR[mask].tolist()))},
                kappa_seat_mean=(float(np.nanmean(arm["aux"][:, arm["aux_cols"].index("kappa_seat")][mask])) if "aux" in arm else None))
# ------------------------------------------------------------------ assemble
OUT = dict(self_sha256=sha(os.path.abspath(__file__)), prereg_sha256=PREREG_SHA, derived_device_sha256=DER_SHA, env=ENV, K=K, alpha_K=ALPHA_K, resolution_bps=RES_BPS, ceiling_bps=CEIL, tripwire_bps=TRIP,
           windows=dict(W_ALPHA=int(WA.sum()), W_TAIL=int(WT.sum()), KING_LIVE=int((WA & KL).sum()), W_LIVE_REPLAY=int(LV.sum()), UB="2026-08-30 20Z"),
           drive_receipt_sha256=sha(T2 + "/receipts/RECEIPT_T2_drive.json"), kappa_receipt_sha256=sha(T2 + "/receipts/RECEIPT_T2_kappa_main.json"),
           artifacts={("%s" % x["tag"]): dict(path=x["path"], sha256=x["sha"]) for x in list(BASE.values()) + list(ARM.values())})
OUT["baselines"] = {"%s_s%s" % k: dict(W_ALPHA=dict(g=float(x["g"][WA].mean()), sharpe=shp(x["g"][WA]), tau=float(x["tau"][WA].mean()), carry=float(x["car"][WA].mean()), pnl=float(x["pnl"][WA].mean()), cost=float(x["cst"][WA].mean())),
                                             KING_LIVE=dict(g=float(x["g"][WA & KL].mean()), sharpe=shp(x["g"][WA & KL])), W_LIVE_REPLAY=dict(g=float(x["g"][LV].mean())), tail=tailrow(x["g"], WT)) for k, x in BASE.items()}
# PC-1 re-assert from the drive's artifacts (judge-computed Δg to 4 dp)
PC1 = {}
for s in SEEDS:
    Z = np.load(T2 + "/arms/PC1S_A0_s%s.npz" % s, allow_pickle=True); C = [str(c) for c in Z["cols"]]; r = np.asarray(Z["d30_n2_c42_rec"], float); g1 = r[:, C.index("net_ex")] / r[:, C.index("gross_total")]
    dg = float((g1 - BASE[("A0", s)]["g"])[WA].mean()); PC1[s] = dict(dg=dg, dg_4dp="%.4f" % dg, target={"42": "-0.0928", "2027": "-0.0894"}[s]); PC1[s]["match"] = PC1[s]["dg_4dp"] == PC1[s]["target"]
assert all(v["match"] for v in PC1.values()), PC1
OUT["PC1_judge_recomputed"] = PC1
RES = {}
for a, label, mode, kcol in ARMS:
    RES[a] = dict(label=label, mode=mode, kcol=kcol, bases={})
    for b in ("A0", "NW"):
        RB = {}
        for s in SEEDS:
            x, base = ARM[(a, b, s)], BASE[(b, s)]; ref = "%s_s%s (GP_%s_s%s)" % (b, s, b, s)
            RB[s] = dict(W_ALPHA=block(x, base, WA, ref), KING_LIVE=block(x, base, WA & KL, ref), W_LIVE_REPLAY=block(x, base, LV, ref), per_year=per_year(x, base, WA),
                         tail_arm=tailrow(x["g"], WT), tail_base=tailrow(base["g"], WT), sigma_bins=bins(x, base, WA), name_aux=name_aux(x, WA) if mode == "name" else None, seat_path=seat_path(x, base, WA) if mode == "seat" else None)
            RB[s]["W_LIVE_REPLAY"]["note"] = "n_days=5: CI uninformative (PREREG §6.1)"
        RES[a]["bases"][b] = RB
def decide(RB, c2_pass, trip_state):
    s_ = SEEDS; blk = {s: RB[s]["W_ALPHA"] for s in s_}
    dd_ok = {s: bool(abs(RB[s]["tail_arm"]["maxdd"]) <= abs(RB[s]["tail_base"]["maxdd"])) for s in s_}; halt_ok = {s: bool(RB[s]["tail_arm"]["halt"] <= RB[s]["tail_base"]["halt"]) for s in s_}
    lo_pos = {s: bool(blk[s]["ci95"][0] > 0) for s in s_}; hi_neg = {s: bool(blk[s]["ci95"][1] < 0) for s in s_}
    clauses = dict(ci95_lo_gt0=lo_pos, maxdd_not_worse_point=dd_ok, halt_not_worse_point=halt_ok, c2_pass=c2_pass, tripwire=trip_state)
    if c2_pass is False: v = "VOID (LEAK)"
    elif any(hi_neg.values()): v = "REJECT"
    elif all(lo_pos.values()) and all(dd_ok.values()) and all(halt_ok.values()) and trip_state in ("not_fired", "fired_pass"): v = "PROMOTE-candidate"
    elif trip_state == "fired_pending": v = "PENDING §7 (ceiling tripwire fired)"
    elif trip_state == "fired_fail": v = "UNDECIDED (LEAK-SUSPECT)"
    else:
        fail = [k for k, d in (("CI95 lower > 0", lo_pos), ("maxDD not worse", dd_ok), ("HALT not worse", halt_ok)) if not all(d.values())]
        v = "UNDECIDED (fails: %s)" % ", ".join(fail)
    flags = []
    if v == "PROMOTE-candidate" and any(blk[s]["ci99K"][0] <= 0 for s in s_): flags.append("MULTIPLICITY-FRAGILE")
    if any(blk[s]["below_resolution"] for s in s_): flags.append("BELOW-RESOLUTION")
    return dict(verdict=v, flags=flags, clauses=clauses, dg={s: blk[s]["dg"] for s in s_}, ci95={s: blk[s]["ci95"] for s in s_}, ci99K={s: blk[s]["ci99K"] for s in s_}, dtau_pct={s: blk[s]["dtau_pct"] for s in s_},
                mechanism_M2_carry_reduced_both_seeds=bool(all(blk[s]["dcarry"] < 0 for s in s_)),
                language="maxDD / HALT 'not worse' are single-path point comparisons inside a decision rule, not a statistical non-inferiority proof (E-0907-F)")
TRIPR = T2 + "/receipts/RECEIPT_T2_tripwire.json"; TRIP_RC = json.load(open(TRIPR)) if os.path.exists(TRIPR) else None
DEC = {}
for a, label, mode, kcol in ARMS:
    fired = any(RES[a]["bases"]["A0"][s]["W_ALPHA"]["dg"] > TRIP for s in SEEDS)
    if not fired: st = "not_fired"
    elif TRIP_RC is None or a not in TRIP_RC.get("arms", {}): st = "fired_pending"
    else: st = "fired_pass" if TRIP_RC["arms"][a]["PASS"] else "fired_fail"
    c2p = C2["arm_PASS"].get(a)
    DEC[a] = dict(A0_verdict=decide(RES[a]["bases"]["A0"], c2p, st), NW_reading=decide(RES[a]["bases"]["NW"], c2p, st), tripwire_fired=fired, tripwire_state=st, deployability="NOT_DEPLOYABLE as-is (book-behaviour change; PREREG §9)")
OUT.update(results=RES, decisions=DEC, C2_from_drive=dict(path_PASS=C2["path"]["PASS"], arm_PASS=C2["arm_PASS"], baseline_PASS=C2["baseline_PASS"]), built_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), wall_s=round(time.time() - T0, 1))
json.dump(OUT, open(T2 + "/receipts/RECEIPT_T2_judge.json", "w"), indent=1, default=float)
# rec-only copies for the repository
os.makedirs(T2 + "/receipts/arms_rec", exist_ok=True); RS = {}
for x in list(BASE.values()) + list(ARM.values()):
    p = T2 + "/receipts/arms_rec/%s.npz" % x["tag"]; kw = dict(cols=np.array(x["cols"]), rec=x["rec"], config_json=np.array(json.dumps(x["cfg"])), source_sha256=np.array(x["sha"]))
    if "aux" in x: kw["T2A"] = x["aux"]; kw["T2A_cols"] = np.array(x["aux_cols"])
    np.savez_compressed(p, **kw); RS[os.path.basename(p)] = sha(p)
json.dump(RS, open(T2 + "/receipts/arms_rec/SHA256_arms_rec.json", "w"), indent=1)
for a, label, mode, kcol in ARMS:
    for b in ("A0", "NW"):
        for s in SEEDS:
            o = RES[a]["bases"][b][s]["W_ALPHA"]; t = RES[a]["bases"][b][s]
            print("%-7s %s s%-4s dg %+.4f CI95 [%+.4f,%+.4f] CI99K [%+.4f,%+.4f] dpnl %+.4f dcarry %+.4f dcost %+.4f dtau %+.1f%% sharpe %.3f/%.3f maxDD %.4f/%.4f halt %d/%d" % (
                label, b, s, o["dg"], o["ci95"][0], o["ci95"][1], o["ci99K"][0], o["ci99K"][1], o["dpnl"], o["dcarry"], o["dcost"], o["dtau_pct"], o["sharpe_arm"], o["sharpe_base"], t["tail_arm"]["maxdd"], t["tail_base"]["maxdd"], t["tail_arm"]["halt"], t["tail_base"]["halt"]))
    print(label, "A0 verdict:", DEC[a]["A0_verdict"]["verdict"], DEC[a]["A0_verdict"]["flags"], "| NW reading:", DEC[a]["NW_reading"]["verdict"], "| tripwire", DEC[a]["tripwire_state"])
print("PC1", json.dumps(PC1)); print("DONE_t2_judge", OUT["wall_s"], "s")
