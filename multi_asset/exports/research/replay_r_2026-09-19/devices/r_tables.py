#!/usr/bin/env python3
"""r_tables.py — stream R tables (program §4 + the frozen RUN_CONFIG 'tables' block), from the 12 simulated runs of r_launch.py.

Statistics are the judge's (fp2_per_year_table.py 230e3c79, imported, not re-implemented): level() mean g / CI95 UTC-day block bootstrap
(NB 2000, rng([20260905,k])) / sharpe_anchor / sharpe_daily (L = 1) / maxdd_L (per anchor, L = 2.0); boot() for paired differences.
The 21-cell regime helpers (boot_dist / delta_dist / Bonferroni K = 21 percentiles 0.119 / 99.881 of the same draws) follow G0's
g0_regime_tables.py (6f448750) line by line; labels = G0 g0_labels.npz (04cb06f4) LAB_EXCL primary, LAB_INCL sensitivity.

Series (per 4h window [A, A+4h), gross_mult gm = 2.0, NAV at the window start N0):
  simulated executor book: g = 1e4·(N1−N0)/(gm·N0); pnl = 1e4·price_and_trading/(gm·N0); car = −1e4·funding/(gm·N0) (paid > 0);
  cst = 1e4·fee/(gm·N0); tau = turnover/(gm·N0); gt = gross0/(gm·N0); nl = net0/gross0. g = pnl − car − cst (asserted).
  S2 production-path target book: S2_series.npz from r0_repro.py (S2 accounting: E-close fills, costb_PWR_G230k; NOSTOP and D18 STOP).
  research real-cost book: PER_YEAR_TABLE_REALCOST arms (judge load(), dyn seat), A0 ↔ S2_A0pred, A1 ↔ S2_v4, same seed.
Refuses unless: R_LAUNCH.json VERDICT PASS with every run's npz sha = the file; the judge reproduces the published realcost W_ALPHA g / CI
exactly; label axis = the S2 axis prefix; every run's audits clean (fee error 0, funding error ≤ 1e-9 USDT, no sub-floor exit tails,
window identity ≤ 1e-6 USDT). Blind protocol: only per-arm COUNTS are read (arm balance); no per-arm outcome exists in the inputs.
v2 (after reading v1 f698c999 / e312f2fe, disclosed; every v1 number recomputed identically): the executor layer is split with the pre-declared
no-day-stop sensitivity runs ((a) executor_noDayStop − S2 STOP, (b) executor − executor_noDayStop), the P2-LIT decomposition and the dated list
of §4-2 flattens are added to the markdown. No run, series, window, statistic or definition changed.
usage: env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B r_tables.py PATH,HOME,LC_CTYPE <config.json>
"""
import os, sys, json, time, hashlib, importlib.util, calendar, collections
WL = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else set()
assert WL, "env whitelist (argv[1]) must be non-empty"
extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"): os.environ[_k] = "1"
import numpy as np

T0 = time.time()
CFG_P = os.path.abspath(sys.argv[2]); CFG = json.load(open(CFG_P)); ROOT = CFG["paths"]["pod_root"]
GM = float(CFG["current_production_config"]["gross_mult"]); LEV = 2.0; KB = 21; ALPHA_B = 0.05 / KB; PB = [100 * ALPHA_B / 2, 100 * (1 - ALPHA_B / 2)]
LAB = ["low", "mid", "high"]; K24 = calendar.timegm((2024, 1, 1, 0, 0, 0))


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def log(*a): print("[%6.0fs]" % (time.time() - T0), *a, flush=True)


def utc(t): return time.strftime("%Y-%m-%dT%HZ", time.gmtime(int(t)))


rec = dict(device="r_tables.py", self_sha256=sha(os.path.abspath(__file__)), argv=sys.argv, env=dict(os.environ), numpy=np.__version__,
           utc_start=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), config=dict(path=CFG_P, sha256=sha(CFG_P)), checks=[])
FAILS = []
def check(name, ok, detail=None):
    rec["checks"].append(dict(check=name, ok=bool(ok), detail=detail)); log("CHECK", name, "OK" if ok else "FAIL", json.dumps(detail, default=str)[:240] if detail is not None else "")
    if not ok: FAILS.append(name)
def refuse(why):
    rec["VERDICT"] = "REFUSED"; rec["why"] = why; rec["failed"] = FAILS
    json.dump(rec, open(ROOT + "/receipts/R_TABLES.json", "w"), indent=1, default=float); print("R_TABLES REFUSED", why, flush=True); sys.exit(3)


for k in ("judge", "realcost_table", "g0_labels", "S2_series", "p2_s2_lib", "realcost_A0_s42", "realcost_A0_s2027", "realcost_A1_s42", "realcost_A1_s2027"):
    v = CFG["pins"][k]; check(f"pin.{k}", sha(v["path"]) == v["sha256"])
LR = json.load(open(ROOT + "/receipts/R_LAUNCH.json")); check("launch.PASS", LR.get("VERDICT") == "PASS" and not LR.get("smoke"), dict(sha256=sha(ROOT + "/receipts/R_LAUNCH.json")))
check("launch.config_is_this_config", LR["config"]["sha256"] == rec["config"]["sha256"])
if FAILS: refuse("inputs")
spec = importlib.util.spec_from_file_location("fp2_judge", CFG["pins"]["judge"]["path"]); J = importlib.util.module_from_spec(spec); spec.loader.exec_module(J)
spec = importlib.util.spec_from_file_location("p2_s2_lib", CFG["pins"]["p2_s2_lib"]["path"]); L2 = importlib.util.module_from_spec(spec); spec.loader.exec_module(L2)
# memory: the judge caches every (2000 × n_days) draw matrix forever; the same draws are regenerated on demand by an LRU of 6 (same expression,
# checked bitwise against the judge's own draws() on n = 1523 before use)
_LRU = collections.OrderedDict()
def _draws(nd):
    if nd in _LRU: _LRU.move_to_end(nd); return _LRU[nd]
    r = np.stack([np.random.default_rng([20260905, k]).integers(0, nd, nd) for k in range(J.NB)]); _LRU[nd] = r
    if len(_LRU) > 6: _LRU.popitem(last=False)
    return r
check("draws.lru_equals_judge", bool(np.array_equal(_draws(1523), J.draws(1523)))); J._DRAW.clear(); J.draws = _draws

# ---------------- simulated runs ----------------
RUNS = {}
for r in CFG["runs"]:
    tag = r["tag"]; od = ROOT + "/work/runs/" + tag.replace("|", "_"); npz = od + f"/SIM_{tag.replace('|', '_')}.npz"; js = od + f"/SIM_{tag.replace('|', '_')}.json"
    lr = LR["runs"][tag]; check(f"run.{tag}.rc0_and_sha", lr["rc"] == 0 and sha(npz) == lr["npz_sha256"] and sha(js) == lr["json"]["sha256"])
    Z = np.load(npz); o = json.load(open(js)); au = o["audits"]
    check(f"run.{tag}.audits", au["max_fee_err"] == 0.0 and au["funding_max_err"] <= 1e-9 and au["exit_subfloor_tails"] == 0 and au["window_identity_max_abs_err"] <= 1e-6 and au["funding_dup"] == 0, au)
    A = Z["A"].astype(np.int64); G = GM * Z["nav0"]
    x = dict(ts=A, g=1e4 * (Z["nav1"] - Z["nav0"]) / G, pnl=1e4 * Z["price_trade"] / G, car=-1e4 * Z["funding"] / G, cst=1e4 * Z["fee"] / G, tau_raw=Z["turnover"] / G,
             gt=Z["gross0"] / G, nl=np.where(Z["gross0"] > 0, Z["net0"] / np.where(Z["gross0"] > 0, Z["gross0"], 1.0), 0.0))
    check(f"run.{tag}.g_identity", float(np.abs(x["g"] - (x["pnl"] - x["car"] - x["cst"])).max()) <= 1e-9)
    RUNS[tag] = dict(run=r, x=x, Z={k: Z[k] for k in Z.files}, o=o)
if FAILS: refuse("runs")
TS = next(iter(RUNS.values()))["x"]["ts"]
for t_, R_ in RUNS.items(): check(f"axis.{t_}", bool(np.array_equal(R_["x"]["ts"], TS)))
AX = L2.AXIS; row = {int(t): i for i, t in enumerate(AX)}; RI = np.array([row[int(t)] for t in TS])
check("axis.W_ALPHA", bool(np.array_equal(RI, np.nonzero(L2.windows(AX)["W_ALPHA"])[0])))
DAY = np.array([time.strftime("%Y%m%d", time.gmtime(int(t))) for t in TS]); DAYS = (TS // 86400) * 86400
YR = np.array([time.gmtime(int(t)).tm_year for t in TS]); MO = np.array([time.gmtime(int(t)).tm_mon for t in TS])
YT = YR.astype(str); QT = np.array([f"{y}Q{(m - 1) // 3 + 1}" for y, m in zip(YR, MO)]); MT = np.array([f"{y}-{m:02d}" for y, m in zip(YR, MO)])
ALL = np.ones(len(TS), bool); KL = TS >= K24

# ---------------- research real-cost arms (+ exact reproduction of the published W_ALPHA) ----------------
PUB = json.load(open(CFG["pins"]["realcost_table"]["path"]))
RC = {}
for fam, seed in (("A0", "42"), ("A0", "2027"), ("A1", "42"), ("A1", "2027")):
    x = J.load(CFG["pins"][f"realcost_{fam}_s{seed}"]["path"], "dyn", seed=seed); check(f"realcost.load.{fam}_s{seed}", not x["why"], x["why"])
    WA = x["ts"] <= calendar.timegm((2026, 8, 30, 20, 0, 0)); WA[:900] = False
    dd = np.array([time.strftime("%Y%m%d", time.gmtime(int(t))) for t in x["ts"]])
    lv = J.level(x, WA, dd, (x["ts"] // 86400) * 86400, LEV); pb = PUB["arms"][f"{fam}/dyn/s{seed}"]["W_ALPHA"]
    check(f"realcost.repro.{fam}_s{seed}", lv["g"] == pb["g"] and lv["ci95"] == pb["ci95"] and lv["n"] == pb["n"], dict(g=lv["g"], pub=pb["g"]))
    ri = np.array([{int(t): i for i, t in enumerate(x["ts"])}[int(t)] for t in TS])
    RC[(fam, seed)] = dict(g=x["g"][ri], pnl=x["pnl"][ri], car=x["car"][ri], cst=x["cst"][ri], tau_raw=x["tau_raw"][ri] / x["gt"][ri], gt=x["gt"][ri], nl=x["nl"][ri],
                           tau_file=x["tau_raw"][ri])
if FAILS: refuse("realcost")

# ---------------- S2 series (S2 accounting, from R0) ----------------
S2Z = np.load(CFG["pins"]["S2_series"]["path"]); check("S2_series.axis", bool(np.array_equal(S2Z["ts"], AX)))
def s2(key):
    gtot = S2Z[key + "::gross_total"][RI]; pos = gtot > 0
    f = lambda c: np.where(pos, S2Z[key + "::" + c][RI] / np.where(pos, gtot, 1.0), 0.0)
    return dict(g=S2Z[key + "::g"][RI], pnl=f("pnl"), car=f("carry"), cst=f("cost"), tau_raw=f("turnover"), gt=gtot, nl=np.zeros(len(RI)))

# ---------------- legs (kc / fc parts of the CMB target) and seats ----------------
MT_ = np.load(L2.PIN["meta"][0], allow_pickle=True); assert sha(L2.PIN["meta"][0]) == L2.PIN["meta"][1]
mrow = {int(t): i for i, t in enumerate(MT_["E_ts"].astype(np.int64))}; Y4 = MT_["y4"]
LEGS = {}
for arm in sorted({r["run"]["arm"] for r in RUNS.values()}):
    d, Vz, rsha, vsha = L2.load_run(arm); V = {k: Vz[k] for k in Vz.files}; recs = d["records"]
    check(f"legs.{arm}.shas", rsha == CFG["s2_runs"][arm]["json_sha256"] and vsha == CFG["s2_runs"][arm]["vec_sha256"])
    def sp(nm, t): o_ = V[nm + "_off"]; return V[nm + "_idx"][o_[t]:o_[t + 1]].astype(np.int64), V[nm + "_val"][o_[t]:o_[t + 1]]
    lk = np.zeros(len(AX)); lf = np.zeros(len(AX)); kc = np.zeros(829); fc = np.zeros(829)
    w3 = np.full((len(AX), 3), np.nan)
    for t in range(len(AX)):
        r_ = recs[t]
        if r_.get("combo_meta") is not None:
            ki, kv = sp("kc", t); fi, fv = sp("fc", t); kc = np.zeros(829); kc[ki] = 0.55 * kv; fc = np.zeros(829); fc[fi] = 0.45 * fv
        c = kc + fc; c = np.where(np.abs(c) > 1e-9, c, 0.0); gg = np.abs(c).sum()
        y = np.nan_to_num(Y4[mrow[int(AX[t])]].astype(np.float64), nan=0.0)
        if gg > 0: lk[t] = 1e4 * (kc * y).sum() / gg; lf[t] = 1e4 * (fc * y).sum() / gg
        s_ = (r_.get("signal") or {}).get("w3")
        if s_ is not None: w3[t] = s_
    wk = w3[:, 0]; wf = w3[:, 2]; mk = np.where((wk + wf) > 0, wk / np.where((wk + wf) > 0, wk + wf, 1.0), np.nan)
    LEGS[arm] = dict(leg_kc=lk[RI], leg_fc=lf[RI], w3_king=wk[RI], w3_rev24=w3[RI, 1], w3_fund=wf[RI], seat_king_masked=mk[RI])
    log("legs", arm)

# ---------------- labels ----------------
GL = np.load(CFG["pins"]["g0_labels"]["path"], allow_pickle=True); gts = GL["ts"].astype(np.int64); VARS = [str(v) for v in GL["vars"]]
check("labels.axis_prefix", bool(np.array_equal(gts[:len(AX)], AX)))
lrow = {int(t): i for i, t in enumerate(gts)}; LI = np.array([lrow[int(t)] for t in TS])
LABS = {"EXCL": np.asarray(GL["LAB_EXCL"])[LI], "INCL": np.asarray(GL["LAB_INCL"])[LI]}
if FAILS: refuse("axes / labels")


# ---------------- helpers (G0 g0_regime_tables.py 6f448750 boot_dist / delta_dist, on the judge's draws) ----------------
def boot_dist(d, mask):
    idx = np.nonzero(mask)[0]
    if len(idx) == 0: return None
    dd = {}
    for k in idx: dd.setdefault(DAY[k], []).append(k)
    keys = sorted(dd); tot = np.array([d[dd[k]].sum() for k in keys]); cnt = np.array([len(dd[k]) for k in keys], float)
    r = J.draws(len(keys)); return tot[r].sum(1) / cnt[r].sum(1)


def delta_dist(d, m_in, m_out):
    idx = np.nonzero(m_in | m_out)[0]
    keys, inv = np.unique(DAY[idx], return_inverse=True); nd = len(keys)
    si = np.bincount(inv, weights=np.where(m_in[idx], d[idx], 0.0), minlength=nd); ci = np.bincount(inv, weights=m_in[idx].astype(float), minlength=nd)
    so = np.bincount(inv, weights=np.where(m_out[idx], d[idx], 0.0), minlength=nd); co = np.bincount(inv, weights=m_out[idx].astype(float), minlength=nd)
    r = J.draws(nd)
    with np.errstate(all="ignore"): return si[r].sum(1) / ci[r].sum(1) - so[r].sum(1) / co[r].sum(1)


def nav_stats(Z, mask):
    idx = np.nonzero(mask)[0]
    if len(idx) == 0: return None
    n0 = Z["nav0"][idx]; n1 = Z["nav1"][idx]; rr = n1 / n0 - 1.0
    nav = np.concatenate([[1.0], np.cumprod(1.0 + rr)]); dd = nav / np.maximum.accumulate(nav) - 1.0; it = int(np.argmin(dd)); ip = int(np.argmax(nav[:it + 1]))
    ud, inv = np.unique(DAYS[idx], return_inverse=True); dr = np.ones(len(ud)); np.multiply.at(dr, inv, 1.0 + rr); dr -= 1.0
    ndays = len(ud); ret = float(nav[-1] - 1.0)
    return dict(n=len(idx), nav_start=float(n0[0]), nav_end=float(n1[-1]), nav_return=ret, nav_return_annualised=float((1.0 + ret) ** (365.0 / ndays) - 1.0) if ndays > 0 and ret > -1 else None,
                nav_sharpe_daily=(float(dr.mean() / dr.std(ddof=1) * np.sqrt(365)) if ndays > 30 and dr.std(ddof=1) > 0 else None),
                nav_maxdd=float(dd.min()), maxdd_peak=(utc(TS[idx[ip - 1]] + 14400) if ip > 0 else utc(TS[idx[0]])), maxdd_trough=(utc(TS[idx[it - 1]] + 14400) if it > 0 else utc(TS[idx[0]])),
                worst_day=(time.strftime("%Y-%m-%d", time.gmtime(int(ud[int(np.argmin(dr))])))), worst_day_ret=float(dr.min()),
                daystop_flattens=int(Z["n_flatten_events"][idx].sum()), name_stop_triggers=int(Z["n_stop_events"][idx].sum()),
                halt_anchors=int((Z["status"][idx] == 1).sum()), hold_anchors=int((Z["status"][idx] == 2).sum()),
                hold_no_target=int(Z["hold_why_missing"][idx].sum()), hold_invalid_target=int(Z["hold_why_invalid"][idx].sum()),
                taker_share_of_executed=float(Z["rec_exec_taker"][idx][np.isfinite(Z["rec_exec_taker"][idx])].sum() / max(1e-9, np.nansum(Z["rec_exec_taker"][idx]) + np.nansum(Z["rec_exec_maker"][idx]))),
                executed_over_planned=float((np.nansum(Z["rec_exec_maker"][idx]) + np.nansum(Z["rec_exec_taker"][idx])) / max(1e-9, np.nansum(Z["rec_plan_turnover"][idx]))),
                fee_bps_of_turnover=float(1e4 * Z["fee"][idx].sum() / max(1e-9, Z["turnover"][idx].sum())),
                arm_counts_total=dict(chase=int(np.nansum(Z["armcount_chase"][idx])), no_chase=int(np.nansum(Z["armcount_no_chase"][idx])), chase_forced=int(np.nansum(Z["armcount_chase_forced"][idx]))),
                clamp_totals={k: int(np.nansum(Z["clamp_" + k][idx])) for k in ("popped", "reduced", "add_blocked", "flatten_only")},
                mean_n_untradable_withheld=float(np.nanmean(Z["rec_n_untradable"][idx])), mean_n_skip_min_notional=float(np.nanmean(Z["rec_n_skip_min_notional"][idx])),
                mean_target_share_untradable=float(np.nanmean(Z["target_share_untradable"][idx])))


def level(x, mask):
    if not mask.any(): return dict(n=0)
    lv = J.level(x, mask, DAY, DAYS, LEV); ms = boot_dist(x["g"], mask)
    lv["ci_bonf"] = [float(np.percentile(ms, PB[0])), float(np.percentile(ms, PB[1]))]
    lv["mark"] = "††" if (lv["ci_bonf"][0] > 0 or lv["ci_bonf"][1] < 0) else ("†" if (lv["ci95"][0] > 0 or lv["ci95"][1] < 0) else "")
    return lv


def diff(a, b, mask):
    d = a["g"] - b["g"]; bb = J.boot(d, mask, DAY)
    o = dict(n=int(mask.sum()), dg=float(d[mask].mean()), ci95=bb["ci95"], dpnl=float((a["pnl"] - b["pnl"])[mask].mean()), dcarry=float((a["car"] - b["car"])[mask].mean()),
             dcost=float((a["cst"] - b["cst"])[mask].mean()), dtau=float((a["tau_raw"] - b["tau_raw"])[mask].mean()))
    o["excl0"] = bool(o["ci95"][0] > 0 or o["ci95"][1] < 0); return o


def cell(x, extra, mask, rest=None):
    n = int(mask.sum())
    if n == 0: return {"n": 0}
    o = level(x, mask)
    for c, v in extra.items(): o[c] = float(np.nanmean(v[mask]))
    if rest is not None and rest.any():
        dd = delta_dist(x["g"], mask, rest); o["d_vs_rest"] = float(x["g"][mask].mean() - x["g"][rest].mean())
        o["d_ci95"] = [float(np.nanpercentile(dd, 2.5)), float(np.nanpercentile(dd, 97.5))]; o["d_ci_bonf"] = [float(np.nanpercentile(dd, PB[0])), float(np.nanpercentile(dd, PB[1]))]
        o["d_mark"] = "††" if (o["d_ci_bonf"][0] > 0 or o["d_ci_bonf"][1] < 0) else ("†" if (o["d_ci95"][0] > 0 or o["d_ci95"][1] < 0) else "")
    return o


# ---------------- per-run tables ----------------
OUT = {}
for tag, R_ in RUNS.items():
    x = R_["x"]; Z = R_["Z"]; ex = LEGS[R_["run"]["arm"]]
    t = dict(W_ALPHA=dict(level=level(x, ALL), nav=nav_stats(Z, ALL)), KING_LIVE=dict(level=level(x, KL), nav=nav_stats(Z, KL)))
    for nm, TG in (("year", YT), ("quarter", QT), ("month", MT)):
        t[nm] = {p: dict(level=level(x, TG == p), nav=nav_stats(Z, TG == p)) for p in sorted(set(TG.tolist()))}
    t["regime"] = {}
    for v, LB in LABS.items():
        t["regime"][v] = {}
        for j, nm in enumerate(VARS):
            labd = LB[:, j] >= 0
            t["regime"][v][nm] = {LAB[l]: cell(x, ex, labd & (LB[:, j] == l), labd & (LB[:, j] != l)) for l in range(3)}
            t["regime"][v][nm]["_labelled"] = dict(n=int(labd.sum()))
    t["run_json"] = {k: R_["o"][k] for k in ("status_counts", "events_fired_counts", "flatten_log", "stop_events_by_year", "target_stats", "invalid_target_reasons", "audits", "runtime_s", "nav_first", "nav_last")}
    OUT[tag] = t; log("tables", tag)

# ---------------- decomposition: research → S2 NOSTOP → S2 STOP → executor ----------------
DEC = {}
for tag, R_ in RUNS.items():
    r = R_["run"]
    if r["events"] != "rule": continue
    arm = r["arm"]; seed = arm.split("_s")[-1]; fam = "A0" if "A0pred" in arm else "A1"
    E_ = R_["x"]
    if r["book"] == "CMB":
        steps = [("research_realcost_" + fam, RC[(fam, seed)]), ("S2_CMB_NOSTOP", s2(f"{arm}|CMB|NOSTOP")), ("S2_CMB_STOP", s2(f"{arm}|CMB|STOP")), ("executor_sim", E_)]
    else:
        steps = [("research_realcost_" + fam, RC[(fam, seed)]), ("S2_LIT_NOSTOP", s2(f"{arm}|LIT|NOSTOP")), ("executor_sim", E_)]
    dm = {}
    for pn, TG in (("W_ALPHA", None), ("year", YT)):
        periods = {"W_ALPHA": ALL} if TG is None else {p: TG == p for p in sorted(set(TG.tolist()))}
        for p, m in periods.items():
            lv = {nm: dict(g=float(s["g"][m].mean()), price=float(s["pnl"][m].mean()), carry=float(s["car"][m].mean()), cost=float(s["cst"][m].mean()), tau=float(s["tau_raw"][m].mean()))
                  for nm, s in steps}
            dl = {f"{steps[i + 1][0]} − {steps[i][0]}": diff(steps[i + 1][1], steps[i][1], m) for i in range(len(steps) - 1)}
            dl[f"executor_sim − {steps[0][0]}"] = diff(steps[-1][1], steps[0][1], m)
            tn = tag.replace("|rule", "|none")                                   # v2 (added after reading v1): split the executor layer
            if r["book"] == "CMB" and tn in RUNS:
                xn = RUNS[tn]["x"]; s2s = steps[2][1]
                lv["executor_noDayStop"] = dict(g=float(xn["g"][m].mean()), price=float(xn["pnl"][m].mean()), carry=float(xn["car"][m].mean()), cost=float(xn["cst"][m].mean()), tau=float(xn["tau_raw"][m].mean()))
                dl["executor_noDayStop − S2_CMB_STOP"] = diff(xn, s2s, m); dl["executor_sim − executor_noDayStop"] = diff(E_, xn, m)
            dm[p] = dict(levels=lv, steps=dl)
    DEC[tag] = dm
# ---------------- sensitivity: rule − none ----------------
SENS = {}
for tag, R_ in RUNS.items():
    if R_["run"]["events"] != "rule" or R_["run"]["book"] != "CMB": continue
    tn = tag.replace("|rule", "|none")
    if tn not in RUNS: continue
    SENS[tag] = {p: diff(R_["x"], RUNS[tn]["x"], m) for p, m in [("W_ALPHA", ALL)] + [(y, YT == y) for y in sorted(set(YT.tolist()))]}
    SENS[tag]["nav_none_W_ALPHA"] = nav_stats(RUNS[tn]["Z"], ALL)

rec.update(tables=OUT, decomposition=DEC, sensitivity_rule_minus_none=SENS,
           definitions=CFG["tables"], labels=dict(path=CFG["pins"]["g0_labels"]["path"], vars=VARS), n_windows=len(TS))
rec["VERDICT"] = "PASS" if not FAILS else "RED"; rec["failed"] = FAILS; rec["runtime_s"] = round(time.time() - T0, 1)
rp = ROOT + "/receipts/R_TABLES.json"; json.dump(rec, open(rp + ".tmp", "w"), indent=1, default=float); os.replace(rp + ".tmp", rp)


# ---------------- markdown ----------------
def f(v, n=2, pct=False):
    if v is None: return "—"
    if isinstance(v, float) and not np.isfinite(v): return "—"
    return (f"{100 * v:+.{n}f}%" if pct else f"{v:+.{n}f}")
MAIN = [t for t in RUNS if RUNS[t]["run"]["events"] == "rule" and RUNS[t]["run"]["book"] == "CMB"]
LIT = [t for t in RUNS if RUNS[t]["run"]["book"] == "LIT"]
md = [f"# stream R tables (config {rec['config']['sha256'][:12]}…, device {rec['self_sha256'][:12]}…, built {time.strftime('%Y-%m-%dT%H:%MZ', time.gmtime())})", "",
      "g = 1e4·ΔNAV/(2.0·NAV) bps per 4h anchor per unit target gross (NAV return = 2.0·g·1e-4); price / carry(paid>0) / fee on the same scale. † CI95 excludes 0; †† Bonferroni K=21 interval excludes 0.", ""]
for grp, tags in (("P2-CMB (main)", MAIN), ("P2-LIT (report only, D10-confounded)", LIT)):
    md += [f"## {grp}: W_ALPHA and per year", "", "| run | period | n | g [CI95] | Sharpe (anchor) | NAV return | NAV Sharpe (daily) | NAV maxDD 2.0× | day-stops | name stops | HALT / HOLD anchors | price / carry / fee | τ |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for tag in tags:
        t = OUT[tag]
        for p, blk in [("W_ALPHA", t["W_ALPHA"])] + list(t["year"].items()):
            lv, nv = blk["level"], blk["nav"]
            md.append(f"| {tag} | {p} | {lv['n']} | {f(lv['g'])}{lv['mark']} [{f(lv['ci95'][0])}, {f(lv['ci95'][1])}] | {f(lv['sharpe_anchor'])} | {f(nv['nav_return'], 1, True)} | {f(nv['nav_sharpe_daily'])} | {f(nv['nav_maxdd'], 1, True)} | {nv['daystop_flattens']} | {nv['name_stop_triggers']} | {nv['halt_anchors']} / {nv['hold_anchors']} | {f(lv['pnl'])} / {f(lv['carry'])} / {f(lv['cost'])} | {lv['tau_raw']:.4f} |")
    md.append("")
md += ["## Decomposition (W_ALPHA and per year): research real-cost book → S2 production-path target (NOSTOP → D18 STOP) → executor layer", "",
       "| run | period | research g | S2 NOSTOP g | S2 STOP g | executor g | Δ exec − S2 STOP [CI95] | Δ exec − research [CI95] | τ research / S2 STOP / exec | fee research / S2 STOP / exec |", "|---|---|---|---|---|---|---|---|---|---|"]
for tag in MAIN:
    for p, blk in DEC[tag].items():
        lv = blk["levels"]; rk = [k for k in lv if k.startswith("research")][0]; st = blk["steps"]
        a = st["executor_sim − S2_CMB_STOP"]; b = st[f"executor_sim − {rk}"]
        md.append(f"| {tag} | {p} | {f(lv[rk]['g'])} | {f(lv['S2_CMB_NOSTOP']['g'])} | {f(lv['S2_CMB_STOP']['g'])} | {f(lv['executor_sim']['g'])} | {f(a['dg'])} [{f(a['ci95'][0])}, {f(a['ci95'][1])}] | {f(b['dg'])} [{f(b['ci95'][0])}, {f(b['ci95'][1])}] | {lv[rk]['tau']:.4f} / {lv['S2_CMB_STOP']['tau']:.4f} / {lv['executor_sim']['tau']:.4f} | {f(lv[rk]['cost'])} / {f(lv['S2_CMB_STOP']['cost'])} / {f(lv['executor_sim']['cost'])} |")
md += ["", "### v2 (added after reading v1): the executor layer split into (a) fills / fees / N+25 timing / withholds / min-notional / per-name stop machine = executor without the day stop − S2 STOP, and (b) the §4-2 day stop = executor − executor without the day stop", "",
       "| run | period | S2 STOP g | executor no day stop g | executor g | (a) Δ [CI95] | (b) Δ [CI95] |", "|---|---|---|---|---|---|---|"]
for tag in MAIN:
    for p, blk in DEC[tag].items():
        lv = blk["levels"]; st = blk["steps"]; a = st["executor_noDayStop − S2_CMB_STOP"]; b = st["executor_sim − executor_noDayStop"]
        md.append(f"| {tag} | {p} | {f(lv['S2_CMB_STOP']['g'])} | {f(lv['executor_noDayStop']['g'])} | {f(lv['executor_sim']['g'])} | {f(a['dg'])} [{f(a['ci95'][0])}, {f(a['ci95'][1])}] | {f(b['dg'])} [{f(b['ci95'][0])}, {f(b['ci95'][1])}] |")
md += ["", "### v2: P2-LIT decomposition (W_ALPHA; D10-confounded)", "", "| run | research g | S2 LIT NOSTOP g | executor g | Δ exec − S2 LIT [CI95] |", "|---|---|---|---|---|"]
for tag in LIT:
    blk = DEC[tag]["W_ALPHA"]; lv = blk["levels"]; rk = [k for k in lv if k.startswith("research")][0]; a = blk["steps"]["executor_sim − S2_LIT_NOSTOP"]
    md.append(f"| {tag} | {f(lv[rk]['g'])} | {f(lv['S2_LIT_NOSTOP']['g'])} | {f(lv['executor_sim']['g'])} | {f(a['dg'])} [{f(a['ci95'][0])}, {f(a['ci95'][1])}] |")
md += ["", "### v2: §4-2 day-stop flattens (UTC) per run", ""]
for tag in MAIN + LIT:
    fl_ = OUT[tag]["run_json"]["flatten_log"]; md.append(f"- {tag}: " + ("; ".join(f"{a_} ({w_.split(' at ')[0].replace('§4-2 day loss ', '')})" for a_, w_ in fl_) if fl_ else "none"))
md += ["", "## Regime cells (P2-CMB main, LAB_EXCL; all 21 cells)", "", "| run | cell | n | g [CI95] | Δ vs rest [CI95] | daily Sharpe | price / carry / fee | leg kc / fc | seat king (masked) |", "|---|---|---|---|---|---|---|---|---|"]
for tag in MAIN:
    for nm in VARS:
        for l in LAB:
            c = OUT[tag]["regime"]["EXCL"][nm][l]
            if not c.get("n"): md.append(f"| {tag} | {nm} {l} | 0 | — | — | — | — | — | — |"); continue
            md.append(f"| {tag} | {nm} {l} | {c['n']} | {f(c['g'])}{c['mark']} [{f(c['ci95'][0])}, {f(c['ci95'][1])}] | {f(c.get('d_vs_rest'))}{c.get('d_mark', '')} [{f((c.get('d_ci95') or [None])[0])}, {f((c.get('d_ci95') or [None, None])[1])}] | {f(c['sharpe_daily'])} | {f(c['pnl'])} / {f(c['carry'])} / {f(c['cost'])} | {f(c['leg_kc'])} / {f(c['leg_fc'])} | {c['seat_king_masked']:.2f} |")
md += ["", "## Sensitivity: §4-2 day stop (rule − none), P2-CMB", "", "| run | period | Δg [CI95] | Δprice | Δcarry | Δfee |", "|---|---|---|---|---|---|"]
for tag, blk in SENS.items():
    for p, d_ in blk.items():
        if p.startswith("nav_"): continue
        md.append(f"| {tag} | {p} | {f(d_['dg'])} [{f(d_['ci95'][0])}, {f(d_['ci95'][1])}] | {f(d_['dpnl'])} | {f(d_['dcarry'])} | {f(d_['dcost'])} |")
md += ["", "## Quarter and month (P2-CMB main)", "", "| run | period | n | g [CI95] | NAV return | price / carry / fee |", "|---|---|---|---|---|---|"]
for tag in MAIN:
    for nm in ("quarter", "month"):
        for p, blk in OUT[tag][nm].items():
            lv, nv = blk["level"], blk["nav"]
            md.append(f"| {tag} | {p} | {lv['n']} | {f(lv['g'])}{lv['mark']} [{f(lv['ci95'][0])}, {f(lv['ci95'][1])}] | {f(nv['nav_return'], 1, True)} | {f(lv['pnl'])} / {f(lv['carry'])} / {f(lv['cost'])} |")
mp = ROOT + "/receipts/R_TABLES.md"; open(mp + ".tmp", "w").write("\n".join(md) + "\n"); os.replace(mp + ".tmp", mp)
print("R_TABLES VERDICT=%s runs=%d json_sha256=%s md_sha256=%s runtime_s=%.0f" % (rec["VERDICT"], len(RUNS), sha(rp), sha(mp), time.time() - T0), flush=True)
sys.exit(0 if not FAILS else 3)
