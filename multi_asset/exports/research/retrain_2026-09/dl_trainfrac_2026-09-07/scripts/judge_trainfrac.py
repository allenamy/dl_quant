"""judge_trainfrac.py — PREREG_dl_full_gradient_window_2026-09-07 (sha d5f078a0910e826e) judge.
WRITTEN BEFORE ANY ARM NUMBER EXISTS (arms not yet trained at authoring time; GPU held by CONST2027).
Readings §4.1/§4.2/§4.3 are transcribed VERBATIM from the prereg; nothing here may be edited after numbers are seen.
Device lineage: identical g definition / window / bootstrap to judge_replication.py (health-check main arm d30_n2_c42, prod caliber).
usage: judge_trainfrac.py  ->  results/judge_trainfrac.json + trainfrac_tables.md"""
import os, json, time, calendar, hashlib
import numpy as np
PA = "/workspace/review_scratch/allweather_trackB/replay/dev_alt/probe_artifacts"
TF = "/workspace/review_scratch/trainfrac/replay/dev_alt/probe_artifacts"
G_ = "/workspace/review_scratch/dl_monthly_gate/replay/dev_alt/probe_artifacts"
OUT_D = "/workspace/review_scratch/trainfrac/results"; os.makedirs(OUT_D, exist_ok=True)
COLS = ["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
ARM = "d30_n2_c42"; NB = 2000; SEED = 20260905; DELTA = 0.05          # §4.3 tolerance, per gross
CUT = calendar.timegm((2026,8,10,20,0,0)); T25 = calendar.timegm((2025,1,1,0,0,0))
T2503 = calendar.timegm((2025,3,1,0,0,0)); T26 = calendar.timegm((2026,1,1,0,0,0))
EXPECT = {"LEGS":"101","CAL":"log","LOOK":900,"WRULE":"msharpe","MEMBERS_TOPN":829,"TRADE_TOPN":0,"FTRIM":"zero","UMASK_SCOPE":"m1","W3FIX":None,
          "SLOW_NPY":"/workspace/shadow_bundle_v3/slow_pred_pinned.npy"}
ARMS = {"yearly_s42":  (f"{G_}/w10_ablation_series_BASE_s42.npz",              "42"),
        "CONST42":     (f"{PA}/w10_ablation_series_G_mE1c_R0_spl42.npz",       "42"),
        "FIX7":        (f"{PA}/w10_ablation_series_G_mE1cX7_R0_spl42.npz",     "42"),
        "X7FULL":      (f"{TF}/w10_ablation_series_G_mE1x7full_R0_spl42.npz",  "42"),
        "X6FULL":      (f"{TF}/w10_ablation_series_G_mE1x6full_R0_spl42.npz",  "42")}
def sha(p): return hashlib.sha256(open(p,"rb").read()).hexdigest()
def iso(t): return time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(t)))
D, META = {}, {}
for k,(p,fseed) in ARMS.items():
    assert os.path.exists(p), f"MISSING ARM ARTIFACT {k}: {p} — judge refuses to run on a partial arm set"
    z = np.load(p, allow_pickle=True); cfg = json.loads(str(z["config_json"]))
    assert [str(c) for c in z["cols"]] == COLS, k
    for kk,v in EXPECT.items(): assert cfg.get(kk) == v, (k,kk,cfg.get(kk),v)
    assert cfg["FSEED"] == fseed and abs(cfg["PHI"]-0.45) < 1e-12 and cfg.get("PHIDYN",0) == 0, (k,cfg["FSEED"])
    R = z[f"{ARM}_rec"]; D[k] = {c: R[:,i] for i,c in enumerate(COLS)}
    META[k] = {"artifact":p, "sha256_16":sha(p)[:16], "FPRED":cfg["FPRED"], "FSEED":cfg["FSEED"], "n":int(len(R))}
ks = list(D); ts0 = D[ks[0]]["ts"].astype(np.int64)
for k in ks: assert np.array_equal(D[k]["ts"].astype(np.int64), ts0), f"anchor grid differs: {k}"
days = ts0 // 86400
months = np.array([time.gmtime(int(t)).tm_year*100 + time.gmtime(int(t)).tm_mon for t in ts0])
WIN = {"FROZEN 2025-03->26<=cut": (ts0>=T2503)&(ts0<=CUT), "2026<=cut": (ts0>=T26)&(ts0<=CUT), "FULL 2025-01->26<=cut": (ts0>=T25)&(ts0<=CUT)}
PW, W26, FW = "FROZEN 2025-03->26<=cut", "2026<=cut", "FULL 2025-01->26<=cut"
G = {k: D[k]["net_ex"]/D[k]["gross_total"] for k in ks}
TPG = {k: D[k]["turnover"]/D[k]["gross_total"] for k in ks}
rng = np.random.default_rng(SEED)
def boot(x, m):
    v = x[m]; d = days[m]; ud, inv = np.unique(d, return_inverse=True); nd = len(ud)
    s = np.bincount(inv, weights=v, minlength=nd); c = np.bincount(inv, minlength=nd)
    idx = rng.integers(0, nd, size=(NB, nd)); mn = s[idx].sum(1)/c[idx].sum(1)
    return {"n":int(m.sum()), "mean":float(v.mean()), "lo":float(np.percentile(mn,2.5)), "hi":float(np.percentile(mn,97.5)),
            "P>0":float((mn>0).mean()), "nav_pct_yr_2x":float(v.mean()*43.8)}
def sharpe(x): return float(x.mean()/x.std(ddof=1)*np.sqrt(2190)) if len(x)>2 and x.std(ddof=1)>0 else float("nan")
def maxdd(x): c = np.cumsum(x); return float(np.max(np.maximum.accumulate(c)-c)) if len(x) else float("nan")
T = []
def p(s=""): T.append(s); print(s)
O = {"prereg_sha256":"d5f078a0910e826e6435787d736a11fcc7a264f4b4ca5c464c34b4d5d4599d73","arm":ARM,"delta":DELTA,
     "n_anchors":int(len(ts0)),"windows":{w:int(m.sum()) for w,m in WIN.items()},"arms":META,
     "bootstrap":{"blocks":"UTC day","n":NB,"seed":SEED},"levels":{},"deltas":{},"reading":{}}
p(f"<!-- judge_trainfrac.py (written before any arm number) prereg d5f078a0910e826e; n={len(ts0)} {iso(ts0[0])}→{iso(ts0[-1])}; windows {O['windows']}; UTC-day block {NB} seed {SEED}; delta={DELTA} -->")
p("## TF-1 · Levels per gross (bps/anchor)")
p("| arm | FPRED | seed | FROZEN [CI95] | S | maxDD | turn/gross | 2026<=cut | FULL |"); p("|---|---|---|---|---|---|---|---|---|")
for k in ks:
    row = {}
    for w,m in WIN.items():
        x = G[k][m]; row[w] = {"n":int(m.sum()),"mean":float(x.mean()),"sharpe":sharpe(x),"maxDD_bps":maxdd(x),
                               "turn_per_gross":float(TPG[k][m].mean()),"nav_pct_yr_2x":float(x.mean()*43.8),"boot":boot(G[k],m)}
    O["levels"][k] = row; a = row[PW]
    p(f"| {k} | {META[k]['FPRED']} | {META[k]['FSEED']} | **{a['mean']:+.3f}** [{a['boot']['lo']:+.3f}, {a['boot']['hi']:+.3f}] | {a['sharpe']:+.2f} | {a['maxDD_bps']:.0f} | {a['turn_per_gross']:.5f} | {row[W26]['mean']:+.3f} | {row[FW]['mean']:+.3f} |")
PAIRS = [("X7FULL","FIX7","X7FULL − FIX7 [§4.1 primary 1]"), ("X7FULL","CONST42","X7FULL − CONST42 [§4.1 primary 2]"),
         ("X6FULL","FIX7","X6FULL − FIX7 [§4.2 data+norm effect]"), ("X7FULL","X6FULL","X7FULL − X6FULL [§4.2 schedule/step effect]"),
         ("X7FULL","yearly_s42","X7FULL − yearly_s42 [§4.3 NI leg]"), ("X6FULL","yearly_s42","X6FULL − yearly_s42 [§4.3 NI leg]"),
         ("FIX7","CONST42","FIX7 − CONST42 [device integrity: must reproduce +0.267 [+0.083,+0.462]]")]
p(f"\n## TF-2 · Paired Δ per gross (Δg by anchor; UTC-day-block bootstrap; every contrast prints BOTH arm names — E-0907-E)")
p("| contrast | **FROZEN** | **2026≤cut** | FULL | ΔSharpe frz | Δturn% | maxDD ref→x | Δ w/o best month |"); p("|---|---|---|---|---|---|---|---|")
for kx,ky,name in PAIRS:
    dg = G[kx]-G[ky]; res = {w: boot(dg, WIN[w]) for w in WIN}
    for w in WIN: res[w]["exact_zero"] = bool(np.all(dg[WIN[w]] == 0))
    mc = {str(mo): float(dg[(months==mo)&WIN[PW]].sum()) for mo in sorted(set(months[WIN[PW]].tolist()))}
    best = max(mc, key=mc.get); drop = boot(dg, WIN[PW] & (months != int(best)))
    tx, ty = float(TPG[kx][WIN[PW]].mean()), float(TPG[ky][WIN[PW]].mean())
    O["deltas"][name] = {"x":kx,"ref":ky,"windows":res,"dturn_pct_frozen":(tx/ty-1)*100,
                         "dSharpe_frozen":sharpe(G[kx][WIN[PW]])-sharpe(G[ky][WIN[PW]]),
                         "maxDD_ref":maxdd(G[ky][WIN[PW]]),"maxDD_x":maxdd(G[kx][WIN[PW]]),
                         "monthly_contrib_bps":mc,"best_month":best,"drop_best_month":drop}
    f = lambda w: f"{res[w]['mean']:+.3f} [{res[w]['lo']:+.3f},{res[w]['hi']:+.3f}] P{res[w]['P>0']:.2f}" + (" (=0)" if res[w]["exact_zero"] else "")
    p(f"| {name} | **{f(PW)}** | **{f(W26)}** | {f(FW)} | {O['deltas'][name]['dSharpe_frozen']:+.3f} | {O['deltas'][name]['dturn_pct_frozen']:+.1f}% | {maxdd(G[ky][WIN[PW]]):.0f}→{maxdd(G[kx][WIN[PW]]):.0f} | {drop['mean']:+.3f} [{drop['lo']:+.3f},{drop['hi']:+.3f}] (best {best}) |")
# ── §4.1 primary gate (verbatim from prereg) ──
d1 = O["deltas"]["X7FULL − FIX7 [§4.1 primary 1]"]; d2 = O["deltas"]["X7FULL − CONST42 [§4.1 primary 2]"]
c1 = bool(d1["windows"][PW]["lo"] > 0); c2 = bool(d2["windows"][PW]["lo"] > 0); c3 = bool(d1["windows"][W26]["mean"] >= 0)
A = c1 and c2 and c3; B = bool(d1["windows"][PW]["hi"] < 0)
verdict = "(A) CANDIDATE" if A else ("(B) REJECT" if B else "(C) UNDECIDED")
p(f"\n## TF-3 · §4.1 primary gate (transcribed verbatim, frozen before numbers)")
p("| condition | value | met |"); p("|---|---|---|")
p(f"| 1. X7FULL − FIX7 FROZEN CI lower > 0 | {d1['windows'][PW]['lo']:+.4f} | {c1} |")
p(f"| 2. X7FULL − CONST42 FROZEN CI lower > 0 | {d2['windows'][PW]['lo']:+.4f} | {c2} |")
p(f"| 3. X7FULL − FIX7 2026 point >= 0 | {d1['windows'][W26]['mean']:+.4f} | {c3} |")
p(f"| (B) X7FULL − FIX7 FROZEN CI upper < 0 | {d1['windows'][PW]['hi']:+.4f} | {B} |")
p(f"\n**VERDICT: {verdict}**")
# ── §4.2 attribution + pre-committed conditional action ──
da = O["deltas"]["X6FULL − FIX7 [§4.2 data+norm effect]"]; ds = O["deltas"]["X7FULL − X6FULL [§4.2 schedule/step effect]"]
data_ci0 = bool(da["windows"][PW]["lo"] <= 0 <= da["windows"][PW]["hi"]); step_pos = bool(ds["windows"][PW]["lo"] > 0)
trig = bool(c1 and data_ci0 and step_pos)
p(f"\n## TF-4 · §4.2 attribution (reported, non-gating)")
p(f"- data+norm effect  X6FULL − FIX7   : {da['windows'][PW]['mean']:+.4f} [{da['windows'][PW]['lo']:+.4f},{da['windows'][PW]['hi']:+.4f}]  (CI contains 0: {data_ci0})")
p(f"- schedule/step eff X7FULL − X6FULL : {ds['windows'][PW]['mean']:+.4f} [{ds['windows'][PW]['lo']:+.4f},{ds['windows'][PW]['hi']:+.4f}]  (CI lower > 0: {step_pos})")
p(f"- **PRE-COMMITTED CONDITIONAL ACTION triggered: {trig}** — if True the gain is MORE TRAINING, not new data: "
  f"FIX8@0.85 / FIX9@0.85 must be run first, and until then NO claim that the full window has value.")
O["reading"] = {"conditions":{"1_X7FULL_minus_FIX7_lo_gt0":c1,"2_X7FULL_minus_CONST42_lo_gt0":c2,"3_2026_point_ge0":c3,
                "B_upper_lt0":B},"verdict":verdict,
                "attribution":{"data_ci_contains_0":data_ci0,"step_lo_gt0":step_pos,"conditional_action_triggered":trig}}
# ── §4.3 non-inferiority leg, CORRECT form (E-0907-F): judge CI lower > -delta ──
p(f"\n## TF-5 · §4.3 non-inferiority vs yearly_s42 — **proper test at δ={DELTA} (E-0907-F): pass ⇔ CI lower > −δ**")
p("| arm − ref | window | Δ | CI95 | **CI lower** | −δ | NI PASS? | old decision-rule would say |"); p("|---|---|---|---|---|---|---|---|")
ni = {}
for nm in ("X7FULL − yearly_s42 [§4.3 NI leg]", "X6FULL − yearly_s42 [§4.3 NI leg]"):
    for w in (PW, W26):
        r = O["deltas"][nm]["windows"][w]
        ok = bool(r["lo"] > -DELTA); old = bool(r["mean"] >= -DELTA and ((r["lo"] <= 0 <= r["hi"]) or r["lo"] > 0))
        ni[f"{nm}|{w}"] = {"delta":DELTA,"mean":r["mean"],"lo":r["lo"],"hi":r["hi"],"ni_pass":ok,"old_decision_rule":old}
        p(f"| {nm.split(' [')[0]} | {w} | {r['mean']:+.4f} | [{r['lo']:+.4f},{r['hi']:+.4f}] | **{r['lo']:+.4f}** | {-DELTA:+.2f} | **{ok}** | {old} |")
p(f"\n> Wording rule (E-0907-F): write \"非劣于年折\" ONLY where NI PASS is True. Where only the old decision rule holds, "
  f"the arm may be described ONLY as \"未过冻结决策规则的否决线\", and δ={DELTA} with the CI lower bound must be printed alongside.")
O["reading"]["non_inferiority"] = ni
json.dump(O, open(f"{OUT_D}/judge_trainfrac.json","w"), indent=1, default=float)
open(f"{OUT_D}/trainfrac_tables.md","w").write("\n".join(T)+"\n")
print(f"\nwrote {OUT_D}/judge_trainfrac.json + trainfrac_tables.md")
