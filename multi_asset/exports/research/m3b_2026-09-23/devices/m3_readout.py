#!/usr/bin/env python3
"""m3_readout.py — ★ M3b copy: identical to the M3 readout (e60dae8b) except that the in-path report counts cause 7 ('applied_via_combined')
as applied (diff receipts/M3B_READOUT_vs_M3.diff). R4's control arm may be M3's zero-hedge control (bitwise the base for all 32 seeds).
M3 text: M3 criteria R1–R3 (gates) and R4 (report only) on ONE base, per the definitions FROZEN in m3_rules.py (committed before any
M3 number). Inputs: the base's 32 certified paths, the M3 overlay's 32 paths, the zero-hedge control's 32 paths + its bitwise-comparison
receipt (must be BITWISE_EQUAL for all 32 seeds, else R4's cost attribution is UNAVAILABLE — named, not zero), both arms' sidecars, the flat-book
npz (R3).
R4 hedge-leg cost per path and complete day d: Δfee_d = 1e4 × [Σ BTC fees(M3) / NAV_open,d(M3) − Σ BTC fees(ctrl) / NAV_open,d(ctrl)], Δfund_d the
same with funding PAID (−f); an event at time t belongs to the window (A, A + 4h] that contains it (the simulator's snapshot convention) and to
that window's UTC day; NAV_open,d = the simulator equity at d 00:00Z (nav0 of the day's first window). Averaged over days, then over paths.
usage: env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B m3_readout.py PATH,HOME,LC_CTYPE <label> <base_dir> <m3_dir>
         <ctrl_dir> <m3_sidecar_dir> <ctrl_sidecar_dir> <exec_path_npz> <ctrl_compare_json> <out.json>
"""
import os, sys, json, time
WL = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else set()
assert WL, "env whitelist (argv[1]) must be non-empty"
extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import m3_rules as RU
import m3_common as CM
import m3_hook as H

DAY, H4 = 86400, 14400
label, base_d, m3_d, ctrl_d, m3_sc, ctrl_sc, ep_npz, cmp_json, outp = sys.argv[2:11]
OUT = {"device": "m3_readout.py", "self_sha256": CM.sha(os.path.abspath(__file__)), "rules_sha256": CM.sha(os.path.join(HERE, "m3_rules.py")),
       "common_sha256": CM.sha(os.path.join(HERE, "m3_common.py")), "hook_sha256": CM.sha(os.path.join(HERE, "m3_hook.py")), "pins": CM.pins_ok(),
       "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "label": label,
       "inputs": {"base": base_d, "m3": m3_d, "ctrl": ctrl_d, "m3_sidecar": m3_sc, "ctrl_sidecar": ctrl_sc, "exec_path_npz": [ep_npz, CM.sha(ep_npz)],
                  "ctrl_compare": [cmp_json, CM.sha(cmp_json)]},
       "windows": {k: [time.strftime("%Y-%m-%dT%HZ", time.gmtime(a)), time.strftime("%Y-%m-%dT%HZ", time.gmtime(b))] for k, (a, b) in RU.WINDOWS.items()}}
B = CM.load_dir(base_d); X = CM.load_dir(m3_d); Cc = CM.load_dir(ctrl_d)
if not (np.array_equal(B["mean"]["A"], X["mean"]["A"]) and np.array_equal(B["mean"]["A"], Cc["mean"]["A"])): raise RU.Empty("axes differ")
OUT["inputs"]["files_sha256"] = {"base": B["file_sha256"], "m3": X["file_sha256"], "ctrl": Cc["file_sha256"]}
bmap = CM.bmap_for(B["mean"])
CMP = json.load(open(cmp_json))
ctrl_ok = CMP.get("VERDICT") == "BITWISE_EQUAL" and len(CMP.get("per_seed", {})) == 32
OUT["ctrl_bitwise_equal_base_32_seeds"] = ctrl_ok

# ---- per-window metrics, both arms ----
tab = {}
for w, (a0, a1) in RU.WINDOWS.items():
    tb, tm = CM.metrics(B["mean"], a0, a1, bmap), CM.metrics(X["mean"], a0, a1, bmap)
    tab[w] = {"base": {"mean_path": tb, "paths": CM.path_dist(B["paths"], a0, a1, bmap)}, "m3": {"mean_path": tm, "paths": CM.path_dist(X["paths"], a0, a1, bmap)},
              "delta_m3_minus_base": {k: (tm[k] - tb[k]) if (tm[k] is not None and tb[k] is not None) else None
                                      for k in ("sharpe", "total_return", "cagr", "maxdd_5m", "worst_day", "mu_daily", "sd_daily", "beta_daily_vs_btc", "g_bps_per_anchor",
                                                "funding_paid_bps", "fee_bps", "price_bps")}}
OUT["table"] = tab
WM = list(RU.WINDOWS)[0]; a0, a1 = RU.MAIN

# ---- R1 / R2 / R3 ----
crit = {}
crit["R1"] = RU.r1(tab[WM]["m3"]["mean_path"]["beta_daily_vs_btc"])
crit["R1"].update(base=tab[WM]["base"]["mean_path"]["beta_daily_vs_btc"], se_nw_m3=tab[WM]["m3"]["mean_path"]["beta_se_newey_west_lag5"],
                  se_classical_m3=tab[WM]["m3"]["mean_path"]["beta_se_classical"], per_path_m3=tab[WM]["m3"]["paths"]["beta_daily_vs_btc"])
days, rd_b, rb = CM.daily_series(B["mean"], a0, a1, bmap); days2, rd_m, rb2 = CM.daily_series(X["mean"], a0, a1, bmap)
if not (np.array_equal(days, days2) and np.array_equal(rb, rb2)): raise RU.Empty("day axes differ")
crit["R2"] = RU.r2(days, rd_m, rd_b, rb)
pp = []
for pb, pm in zip(B["paths"], X["paths"]):
    _, rb_, _ = CM.daily_series(pb, a0, a1, bmap); _, rm_, _ = CM.daily_series(pm, a0, a1, bmap); up = rb > RU.BTC_UP
    pp.append(float(rm_[up].mean() - rb_[up].mean()) if up.any() else float("nan"))
crit["R2"]["per_path_diff (report)"] = RU.dist(np.array(pp)) if np.isfinite(pp).any() else None
Z = np.load(ep_npz); mm = (Z["window"] == 0) & Z["reached"].astype(bool)
crit["R3"] = RU.r3(Z["intended_gross_units"][mm], Z["move_plan"][mm])
OUT["criteria"] = crit


# ---- R4: hedge-leg cost from the sidecars ----
def sc_file(d, seed):
    fs = [f for f in os.listdir(d) if f.startswith("M3SC_") and f.endswith(f"_seed_{seed:02d}.npz")]
    if len(fs) != 1: raise RU.Empty(f"{d}: {len(fs)} sidecars for seed {seed}")
    return os.path.join(d, fs[0])


def path_file(d, seed):
    fs = [f for f in os.listdir(d) if f.startswith("PATH_") and f.endswith(f"_seed_{seed:02d}.npz")]
    if len(fs) != 1: raise RU.Empty(f"{d}: {len(fs)} path files for seed {seed}")
    return os.path.join(d, fs[0])


def daily_btc(sc, pth, days_):
    S = np.load(sc); P = np.load(pth)
    A = P["A"].astype(np.int64); nav0 = P["nav0"]
    op = {int(a): float(n) for a, n in zip(A, nav0) if a % DAY == 0}
    idx = {int(d): i for i, d in enumerate(days_)}
    fee = np.zeros(len(days_)); fund = np.zeros(len(days_)); turn = np.zeros(len(days_))
    tr = S["trades"]; fu = S["funding"]
    for arr, col, sign, out in ((tr, 5, 1.0, fee), (fu, 1, -1.0, fund), (tr, 3, None, turn)):
        if len(arr) == 0: continue
        t = arr[:, 0]; Aw = (np.ceil(t / H4) - 1) * H4; d = (Aw // DAY * DAY).astype(np.int64)
        v = np.abs(arr[:, col]) if sign is None else sign * arr[:, col]
        for dd, vv in zip(d.tolist(), v.tolist()):
            i = idx.get(dd)
            if i is not None: out[i] += vv
    nav = np.array([op[int(d)] for d in days_])
    return 1e4 * fee / nav, 1e4 * fund / nav, 1e4 * turn / nav, str(S["mode"])


r4 = {"ctrl_bitwise_equal_base": ctrl_ok}
for w, (w0, w1) in RU.WINDOWS.items():
    dd, _, _ = RU.complete_days(B["mean"]["A"], B["mean"]["r"], w0, w1)
    per = {"d_fee": [], "d_fund": [], "d_total": [], "m3_fee": [], "m3_fund": [], "ctrl_fee": [], "ctrl_fund": [], "d_turn": []}
    for seed in range(32):
        f1, u1, t1, mo1 = daily_btc(sc_file(m3_sc, seed), path_file(m3_d, seed), dd)
        f0, u0, t0, mo0 = daily_btc(sc_file(ctrl_sc, seed), path_file(ctrl_d, seed), dd)
        if mo1 != "overlay" or mo0 != "control": raise RU.Empty(f"sidecar modes {mo1}/{mo0}")
        per["d_fee"].append(float((f1 - f0).mean())); per["d_fund"].append(float((u1 - u0).mean())); per["d_total"].append(float((f1 + u1 - f0 - u0).mean()))
        per["m3_fee"].append(float(f1.mean())); per["m3_fund"].append(float(u1.mean())); per["ctrl_fee"].append(float(f0.mean())); per["ctrl_fund"].append(float(u0.mean()))
        per["d_turn"].append(float((t1 - t0).mean()))
    r4[w] = {"n_days": int(len(dd)), "n_paths": 32, "unit": "bps of the day's opening simulator NAV per complete day; BTCUSDT only",
             **{k: {"path_mean": float(np.mean(v)), "p2.5": float(np.percentile(v, 2.5)), "p97.5": float(np.percentile(v, 97.5))} for k, v in per.items()},
             "delta_sharpe": tab[w]["delta_m3_minus_base"]["sharpe"], "delta_total_return": tab[w]["delta_m3_minus_base"]["total_return"],
             "delta_maxdd_5m": tab[w]["delta_m3_minus_base"]["maxdd_5m"], "delta_worst_day": tab[w]["delta_m3_minus_base"]["worst_day"],
             "delta_mu_daily_bps": 1e4 * tab[w]["delta_m3_minus_base"]["mu_daily"], "delta_sd_daily_bps": 1e4 * tab[w]["delta_m3_minus_base"]["sd_daily"]}
    if not ctrl_ok: r4[w]["cost_attribution"] = "UNAVAILABLE: control not bitwise equal to base for all 32 seeds"
OUT["R4_report_only"] = r4

# ---- in-path hedge statistics (report only; pooled over 32 seeds of the M3 run) ----
cn = {v: k for k, v in H.CAUSE.items()}; ip = {}
for w, (w0, w1) in RU.WINDOWS.items():
    cause = []; intended = []; applied = []; post = []; btcsk = []; gsx = []
    for seed in range(32):
        S = np.load(sc_file(m3_sc, seed)); A = S["A"].astype(np.int64); m = (A >= w0) & (A <= w1)
        cause.append(S["cause"][m]); intended.append(S["add_intended"][m] / S["gs"][m]); applied.append(S["add_applied"][m] / S["gs"][m])
        post.append((S["pos_beta"] + S["plan_beta"])[m]); btcsk.append(S["btc_plan_skip"][m])
    cause = np.concatenate(cause); intended = np.concatenate(intended); applied = np.concatenate(applied); post = np.concatenate(post); btcsk = np.concatenate(btcsk)
    ap = np.isin(cause, H.APPLIED)                     # M3b: 'applied' and 'applied_via_combined' both deliver the hedge
    ip[w] = {"trading_anchor_records": int(len(cause)), "cause_counts": {cn[int(c)]: int(np.sum(cause == c)) for c in np.unique(cause)},
             "delivered_share_at_target (Σ applied·sign(intended) / Σ|intended|)": float((applied * np.sign(intended)).sum() / np.abs(intended).sum()),
             "intended_hedge_over_gs": RU.dist(intended), "planned_post_trade_book_beta_applied_anchors": RU.dist(post[ap]),
             "planned_post_trade_book_beta_skipped_anchors": RU.dist(post[~ap]) if (~ap).any() else None,
             "btc_plan_row_on_applied_anchors": {k: int(np.sum(btcsk[ap] == v)) for k, v in H.PLAN_SKIP.items() if np.sum(btcsk[ap] == v)}}
OUT["in_path_hedge_report_only"] = ip

und = [k for k in ("R1", "R2", "R3") if crit[k].get("pass") is None]
fail = [k for k in ("R1", "R2", "R3") if crit[k].get("pass") is False]
OUT["undecided_because"] = und; OUT["failing"] = fail
OUT["VERDICT"] = "UNDECIDED" if und else ("FAIL" if fail else "PASS")
json.dump(OUT, open(outp + ".tmp", "w"), indent=1, default=float); os.replace(outp + ".tmp", outp)
print(f"M3_READOUT {label} VERDICT={OUT['VERDICT']} failing={fail} undecided={und} R1={crit['R1']['measured']:+.4f} "
      f"R2_diff={crit['R2'].get('diff')} R3_D={crit['R3']['D_delivered_share']:.4f} out_sha256={CM.sha(outp)}", flush=True)
