#!/usr/bin/env python3
"""prod_target_checks.py -- AUDIT_PROD: producer-side confirmation of AUDIT_EXEC EXE-03 and CHK-01, FTRIM as served. Mac, read-only, no statistic about P&L.
Reads ~/wide_shadow/state/{target_live,target_live_king,target_combo,weights}, ~/wide_shadow/fea171/state_H_{kc,fc}_<A>.npz, ~/wide_shadow/shadow_log.jsonl,
~/dl_quant_live/state/live/pilot_log/20260913/{anchors,orders}.jsonl and the executor reshape source (signal/legs.py, scheduler/anchor_loop.py) — nothing is written
outside docs/audit_pipeline_2026-09-13/receipts_prod/prod_target_checks.json.
CHK-01  counterfactual rewrite R(A) = sum|w_live - w_king| / sum|w_king| (pilot_journal/tools/inspect_anchor.py L33-38 formula) for every combo-era anchor, and its
        producer-side decomposition: R_kc = sum|sm_kc - w_king|/sum|w_king|, R_fc likewise (state_H_kc/fc = the two chains that combo_stage.py L270 mixes 0.55/0.45),
        gate: 0.55*sm_kc + 0.45*sm_fc == target_live weights; with w3 (signal log), FTRIM counts and rho_kc_fc from target_combo.
EXE-03  (a) producer net/gross of target_live at 12Z and of the executor's popped names; (b) the executor reshape (legs.py reshape_after_withhold: w - mean(w), / sum|w|)
        re-executed on the producer vector with the recorded pops must reproduce orders.jsonl target_w; (c) sign flips and their filled notional; (d) for every combo-era
        anchor, the producer net/gross and the flips a pop-free re-demean alone would cause (lower bound on executor flips).
FTRIM   per anchor names excluded in kc/fc (target_combo ftrim), rn8 coverage.
Launch (verbatim): devices_prod/parity/parity_run_mac.sh checks
"""
import os, sys, json, time, hashlib, stat, glob
WHITE = set(x for x in sys.argv[1].split(",") if x) if len(sys.argv) > 1 else None
assert WHITE, "env whitelist argv[1] required"
assert sorted(k for k in os.environ if k not in WHITE) == [], ("ENV WHITELIST VIOLATION", sorted(os.environ))
import numpy as np
T0 = time.time()
def log(*a): print("[%7.1fs]" % (time.time() - T0), *a, flush=True)
SF_DATALESS = getattr(stat, "SF_DATALESS", 0x40000000)
def gsha(p):
    st = os.stat(p); assert not (st.st_flags & SF_DATALESS), ("dataless", p)
    h = hashlib.sha256(); n = 0
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b); n += len(b)
    assert n == st.st_size, ("short read", p); return h.hexdigest()
def U(t): return time.strftime("%Y-%m-%d %HZ", time.gmtime(int(t)))
HOME = "/Users/haosiyu"; WS = HOME + "/wide_shadow"; EX = HOME + "/dl_quant_live"; REPO = HOME + "/Desktop/quant_research"
OUTJ = REPO + "/docs/audit_pipeline_2026-09-13/receipts_prod/prod_target_checks.json"
CODE = {"legs.py": EX + "/signal/legs.py", "anchor_loop.py": EX + "/scheduler/anchor_loop.py", "inspect_anchor.py": REPO + "/multi_asset/exports/live/pilot_journal/tools/inspect_anchor.py",
        "combo_stage.py": WS + "/fea171/combo_stage.py", "config.json": WS + "/shadow_bundle/config.json"}
RC = {"self_sha256": gsha(os.path.abspath(__file__)), "env": {"whitelist": sorted(WHITE), "actual": {k: os.environ[k] for k in sorted(os.environ)}}, "argv": sys.argv,
      "python": sys.version.split()[0], "numpy": np.__version__, "code_sha256": {k: gsha(p) for k, p in CODE.items()}, "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
assert RC["code_sha256"]["combo_stage.py"] == "b5c698f9d1ee9acb73c9bf5f3a1e15843d3298e95a810ebf0107a7d68c6ee358"
LEGS = open(CODE["legs.py"]).read(); assert "        w = w - w.mean()" in LEGS and "            w = w / s                       # unit gross; the caller multiplies by sizing_gross" in LEGS
IA = open(CODE["inspect_anchor.py"]).read().split("\n"); RC["inspect_anchor_L33_38"] = IA[32:38]
cfg = json.load(open(CODE["config.json"])); SYMS = [str(s) for s in cfg["symbols_panel"]]; SIDX = {s: j for j, s in enumerate(SYMS)}
def wvec(doc):
    v = np.zeros(len(SYMS)); 
    for s, x in doc["weights"].items(): v[SIDX[s]] = float(x)
    return v
def npz_vec(p):
    z = np.load(p); v = np.zeros(len(SYMS)); v[z["idx"].astype(np.int64)] = z["val"].astype(np.float64); return v, int(z["anchor"]) if "anchor" in z.files else None
# ---------------- CHK-01 series + decomposition
sig = {}
for ln in open(WS + "/shadow_log.jsonl"):
    try: r = json.loads(ln)
    except Exception: continue
    if r.get("e") == "signal": sig[int(r["anchor_ts"])] = r
rows = []; files_sha = {}
for p in sorted(glob.glob(WS + "/state/target_live_king/*.json")):
    A = int(os.path.basename(p).split(".")[0]); pl = f"{WS}/state/target_live/{A}.json"; pc = f"{WS}/state/target_combo/{A}.json"
    if not os.path.exists(pl): continue
    dl = json.load(open(pl)); dk = json.load(open(p))
    if not str(dl.get("producer", "")).startswith("combo_stage"): continue
    wl, wk = wvec(dl), wvec(dk); gk = float(np.abs(wk).sum()); R = float(np.abs(wl - wk).sum() / gk)
    row = {"anchor": U(A), "ts": A, "R": R, "net_over_gross_live": float(wl.sum() / np.abs(wl).sum()), "n_live": int((wl != 0).sum()), "n_king": int((wk != 0).sum())}
    pk, pf = f"{WS}/fea171/state_H_kc_{A}.npz", f"{WS}/fea171/state_H_fc_{A}.npz"
    if os.path.exists(pk) and os.path.exists(pf):
        kc, ak = npz_vec(pk); fc, af = npz_vec(pf); assert ak == A and af == A
        mix = 0.55 * kc + 0.45 * fc; row["mix_equals_target_live_maxabs"] = float(np.abs(mix - wl).max())
        row["R_kc"] = float(np.abs(kc - wk).sum() / gk); row["R_fc"] = float(np.abs(fc - wk).sum() / gk); row["R_mix_vs_kc"] = float(np.abs(mix - kc).sum() / gk)
    if os.path.exists(pc):
        dc = json.load(open(pc)); row["rho_kc_fc"] = dc.get("rho_kc_fc"); row["w3_masked"] = dc.get("w3_masked")
        ft = dc.get("ftrim") or {}; row["ftrim_n_kc"] = ft.get("n_kc"); row["ftrim_n_fc"] = ft.get("n_fc"); row["rn8_coverage"] = ft.get("rn8_coverage")
    if A in sig: row["w3"] = sig[A].get("w3")
    rows.append(row)
RC["CHK01_rows"] = rows
gate = max((r.get("mix_equals_target_live_maxabs", 0.0) for r in rows), default=None); RC["CHK01_gate_mix_equals_target_live_maxabs"] = gate
claims = {"2026-09-03 08Z": 17.21, "2026-09-05 20Z": 20.50, "2026-09-09 12Z": 21.34, "2026-09-11 12Z": 24.60, "2026-09-12 12Z": 25.36, "2026-09-12 16Z": 25.99, "2026-09-12 20Z": 26.58,
          "2026-09-13 00Z": 27.10, "2026-09-13 04Z": 27.46, "2026-09-13 08Z": 27.20, "2026-09-13 12Z": 27.17}
byA = {r["anchor"]: r for r in rows}
RC["CHK01_claims_vs_measured_pct"] = {a: {"claimed": c, "measured": (round(byA[a]["R"] * 100, 2) if a in byA else None), "match_2dp": (a in byA and round(byA[a]["R"] * 100, 2) == c)} for a, c in claims.items()}
def corr(x, y):
    x = np.asarray(x, float); y = np.asarray(y, float); ok = np.isfinite(x) & np.isfinite(y); return float(np.corrcoef(x[ok], y[ok])[0, 1]) if ok.sum() > 5 else None
R_ = [r["R"] for r in rows]
RC["CHK01_descriptive"] = {"n_anchors": len(rows), "first": rows[0]["anchor"] if rows else None, "last": rows[-1]["anchor"] if rows else None,
    "corr_R_Rfc": corr(R_, [r.get("R_fc", np.nan) for r in rows]), "corr_R_Rkc": corr(R_, [r.get("R_kc", np.nan) for r in rows]),
    "corr_R_rev24_weight": corr(R_, [(r.get("w3") or [np.nan] * 3)[1] for r in rows]), "corr_R_rho_kc_fc": corr(R_, [r.get("rho_kc_fc") if r.get("rho_kc_fc") is not None else np.nan for r in rows]),
    "corr_R_ftrim_n": corr(R_, [(r.get("ftrim_n_kc") or 0) + (r.get("ftrim_n_fc") or 0) if r.get("ftrim_n_kc") is not None else np.nan for r in rows])}
def at(a): return byA.get(a, {})
RC["CHK01_change_0903_to_0913"] = {k: {"2026-09-03 08Z": at("2026-09-03 08Z").get(k), "2026-09-13 12Z": at("2026-09-13 12Z").get(k)} for k in ("R", "R_kc", "R_fc", "R_mix_vs_kc", "rho_kc_fc", "w3", "ftrim_n_kc", "ftrim_n_fc")}
log("CHK-01", RC["CHK01_claims_vs_measured_pct"]["2026-09-13 12Z"], RC["CHK01_descriptive"])
# ---------------- EXE-03
A = 1789300800; RID = "A1789302239"
anc = [json.loads(l) for l in open(EX + "/state/live/pilot_log/20260913/anchors.jsonl") if l.strip()]
row12 = [r for r in anc if r.get("rebalance_id") == RID]; assert len(row12) == 1; row12 = row12[0]; rs = row12["reshape"]
RC["EXE03_inputs"] = {"anchors.jsonl_sha256": gsha(EX + "/state/live/pilot_log/20260913/anchors.jsonl"), "orders.jsonl_sha256": gsha(EX + "/state/live/pilot_log/20260913/orders.jsonl"),
                      "target_live_sha256": gsha(f"{WS}/state/target_live/{A}.json"), "external_book_json_sha": row12["external_book"]["json_sha"]}
dl = json.load(open(f"{WS}/state/target_live/{A}.json")); w = {s: float(x) for s, x in dl["weights"].items()}
G = sum(abs(x) for x in w.values()); NET = sum(w.values()); popped = list(rs["popped_names"])
net_pop = sum(w.get(s, 0.0) for s in popped); gross_pop = sum(abs(w.get(s, 0.0)) for s in popped)
unit = {s: x / G for s, x in w.items()}; rest = {s: x for s, x in unit.items() if s not in set(popped)}
syms = sorted(rest); vec = np.array([rest[s] for s in syms]); nb = float(vec.sum()); gb = float(np.abs(vec).sum())
v2 = vec - vec.mean(); v2 = v2 / np.abs(v2).sum(); shift = -float(vec.mean())
orders = [json.loads(l) for l in open(EX + "/state/live/pilot_log/20260913/orders.jsonl") if RID in l]
tw = {}; filled = {}
for o in orders:
    if o.get("rebalance_id") != RID: continue
    s = o["symbol"]; tw.setdefault(s, float(o["target_w"])); filled[s] = filled.get(s, 0.0) + float(o.get("filled_notional") or 0.0)
rep = {syms[i]: float(v2[i]) for i in range(len(syms))}
common = sorted(set(rep) & set(tw))
maxdiff = max(abs(rep[s] - tw[s]) for s in common) if common else None
flips = [(s, w[s] / G, rep[s], tw.get(s), filled.get(s, 0.0)) for s in syms if np.sign(rest[s]) != np.sign(rep[s]) and rest[s] != 0]
RC["EXE03"] = {"anchor": U(A), "producer_sum_w": NET, "producer_sum_abs_w": G, "producer_net_over_gross": NET / G,
               "popped_names": popped, "popped_sum_w_over_G": net_pop / G, "popped_gross_share": gross_pop / G,
               "remainder_net_over_full_gross": nb, "alarm_net_before_over_sizing_gross": rs["net_before"] / rs["sizing_gross"], "remainder_gross_over_full_gross": gb,
               "executor_gross_before_over_sizing": rs["gross_before"] / rs["sizing_gross"],
               "share_of_net_before_from_producer_net": (NET / G) / nb if nb else None, "share_from_removing_popped": (-net_pop / G) / nb if nb else None,
               "uniform_shift_per_name_unit_gross": shift, "n_names_after_pop": len(syms),
               "reproduced_vs_orders_target_w": {"n_common": len(common), "n_orders_symbols": len(tw), "max_abs_diff": maxdiff},
               "sign_flips": [{"symbol": s, "producer_unit_w": a, "reshaped_w": b, "orders_target_w": c, "filled_notional_usdt": f} for s, a, b, c, f in flips],
               "n_flips_short_to_long": sum(1 for x in flips if x[1] < 0), "n_flips_long_to_short": sum(1 for x in flips if x[1] > 0),
               "flipped_filled_notional_usdt": float(sum(x[4] for x in flips)), "flipped_filled_nonzero": sum(1 for x in flips if abs(x[4]) > 0)}
log("EXE-03", {k: RC["EXE03"][k] for k in ("producer_net_over_gross", "popped_sum_w_over_G", "remainder_net_over_full_gross", "alarm_net_before_over_sizing_gross", "n_flips_short_to_long", "flipped_filled_notional_usdt")}, RC["EXE03"]["reproduced_vs_orders_target_w"])
freq = []
for r in rows:
    d = json.load(open(f"{WS}/state/target_live/{r['ts']}.json")); x = np.array([float(v) for v in d["weights"].values()]); g = np.abs(x).sum(); u = x / g
    a2 = u - u.mean(); fl = (np.sign(a2) != np.sign(u)) & (u != 0)
    freq.append({"anchor": r["anchor"], "net_over_gross": float(u.sum()), "n_names": int(len(u)), "n_flip_popfree": int(fl.sum()), "flipped_unit_gross": float(np.abs(u[fl]).sum()),
                 "n_flip_short_to_long": int((fl & (u < 0)).sum()), "n_flip_long_to_short": int((fl & (u > 0)).sum())})
RC["EXE03_popfree_frequency"] = {"rows": freq, "summary": {"anchors": len(freq), "net_short_anchors": sum(1 for f in freq if f["net_over_gross"] < 0), "net_long_anchors": sum(1 for f in freq if f["net_over_gross"] > 0),
    "net_over_gross_median": float(np.median([f["net_over_gross"] for f in freq])), "net_over_gross_min": float(min(f["net_over_gross"] for f in freq)), "net_over_gross_max": float(max(f["net_over_gross"] for f in freq)),
    "n_flip_median": float(np.median([f["n_flip_popfree"] for f in freq])), "n_flip_max": int(max(f["n_flip_popfree"] for f in freq)), "anchors_with_flips": sum(1 for f in freq if f["n_flip_popfree"] > 0),
    "flipped_unit_gross_median": float(np.median([f["flipped_unit_gross"] for f in freq]))}}
log("EXE-03 freq", RC["EXE03_popfree_frequency"]["summary"])
# ---------------- FTRIM as served
ft = []
for p in sorted(glob.glob(WS + "/state/target_combo/*.json")):
    d = json.load(open(p)); f = d.get("ftrim")
    if f: ft.append({"anchor": U(d["anchor_ts"]), "n_kc": f.get("n_kc"), "n_fc": f.get("n_fc"), "rn8_coverage": f.get("rn8_coverage"), "rule": f.get("rule")})
RC["FTRIM_served"] = {"anchors": len(ft), "first": ft[0]["anchor"] if ft else None, "last": ft[-1]["anchor"] if ft else None,
                      "n_kc_median": float(np.median([x["n_kc"] for x in ft])) if ft else None, "n_kc_max": max(x["n_kc"] for x in ft) if ft else None,
                      "n_fc_median": float(np.median([x["n_fc"] for x in ft])) if ft else None, "rn8_coverage_min": min(x["rn8_coverage"] for x in ft) if ft else None,
                      "rules": sorted(set(x["rule"] for x in ft)), "last_12": ft[-12:]}
log("FTRIM", {k: RC["FTRIM_served"][k] for k in ("anchors", "first", "n_kc_median", "n_kc_max", "n_fc_median", "rn8_coverage_min", "rules")})
RC["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()); RC["wall_s"] = round(time.time() - T0, 1)
json.dump(RC, open(OUTJ, "w"), indent=1, default=str); log("DONE prod_target_checks")
