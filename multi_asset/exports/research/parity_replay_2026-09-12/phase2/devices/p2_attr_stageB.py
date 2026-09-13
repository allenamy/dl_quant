#!/usr/bin/env python3
"""ATTR Stage B (static, no gate) -- docs/PREREG_combo_chain_residual_attribution_2026-09-13.md §2 Stage B + AMENDMENT 1/2. READ-ONLY on every input.
(1) combo state sources: every anchor of the Phase 1 chain receipt (c38270ce...) and the G2-C chain receipt (bound to G2C_verdict chain_receipt_sha256)
    carries kc_src=own / fc_src=own in the combo tail; replay target_combo/{A}.json kc/fc_state_source (G2-C chain tree) and the producer's target_combo/{A}.json;
    first-anchor previous-state files (state_H_{f10,kc,fc}_1788609600) used by the Phase 1 chain (copies from the Mac replay_home) and by the G2-C chain
    tree vs the producer's own files (AMENDMENT 1 SHA256SUMS); per-anchor replay vs producer state_H_{f10,kc,fc}_A L-inf over the 41 G2-C chain anchors.
(2) the three Phase 1 backfill probe receipts re-read (cells filled / lost / changed).
(3) left-boundary deficit per chain anchor: rows <= A in the Phase 1 rolling (snapshot 1789200000, c2ab7134...) and in the G2-C chain hybrid, vs 11520.
(4) dead live names per anchor (AMENDMENT 1 A1.2: no 5m bar in (A-24h, A] with finite log_cnt > 0), from snapshot 1789200000 rolling and from the G2-C
    chain hybrid; counts in the producer's king member set (weights/{A}.npz 'members' = the F10 scoring cross-section, n_f10_scored), king weights,
    target_live_king, target_combo and target_live; snapshot anchors 1789214400/1789228800/1789243200 also vs snapshot aux prev_rec.members.
Writes only /workspace/uplift_r2_2026-09-13/P2/receipts/ATTR_stageB.json.
usage: env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B p2_attr_stageB.py PATH,HOME,LC_CTYPE"""
import os, sys, json, time, hashlib, re
WL = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else set()
assert WL, "env whitelist (argv[1]) must be non-empty"
extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
import numpy as np
P2 = "/workspace/uplift_r2_2026-09-13/P2"; W = P2 + "/work"; RC = P2 + "/receipts"; OUT = RC + "/ATTR_stageB.json"; PRODH = W + "/live_ro/prod_stateH_attr"; AI = W + "/phase1_ro/attr_inputs"
assert os.path.abspath(OUT).startswith(RC + "/ATTR_")
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 22), b""): h.update(ch)
    return h.hexdigest()
def iso(t): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(t)))
T0 = time.time()
PIN = {"phase1_chain_receipt": (W + "/live_ro/PARITY_phase1_chain_full_1788624000_1789200000.json", "c38270ce5604f7fd87b2f5e2416102c60bbdb803e73ea5bdd1a6119d9fc738a5"),
       "snap_1789200000_rolling": (W + "/snapshots/1789200000/rolling.npz", "c2ab71344d965d08b7ea0dac82acace7b030716047d732a4296756704f82f93d"),
       "snap_1789214400_rolling": (W + "/snapshots/1789214400/rolling.npz", "2582fd7519e2d846df72916279ce6fedec4b7a29f3787ed476ecc15c69beee4f"),
       "snap_1789228800_rolling": (W + "/snapshots/1789228800/rolling.npz", "3448aa217b00961a9523e743a37166b1eb3f2e86b609bd36ec129d6f5a9fb35c"),
       "snap_1789243200_rolling": (W + "/snapshots/1789243200/rolling.npz", "8d19b76feab424cb45c2e8d7362ebce091552f060ce6533d45910cb7da6fd4c9"),
       "snap_1789214400_aux": (W + "/snapshots/1789214400/aux.json", "4a3572efa33f1a393048107b28b9a794d50ee37193aa09ba2153d235d6b4242a"),
       "snap_1789228800_aux": (W + "/snapshots/1789228800/aux.json", "d653bca08bccc087dd076b72d31d5be25a991f92cf676c36d7e4fab10fb7ba0c"),
       "snap_1789243200_aux": (W + "/snapshots/1789243200/aux.json", "69d8af7c9b3b7ac3957dfc52fc77c8ba97b53cdeec4b450e31f47b2526065360"),
       "backfill_12Z": (AI + "/receipts/BACKFILL_probe_1789200000_vs_1789214400.json", "4d8fa2ed51719751b70002ea640da41e41b5c20360307bb779cff69205ee61bf"),
       "backfill_16Z": (AI + "/receipts/BACKFILL_probe_1789214400_vs_1789228800.json", "edb5cde06cad410866c292c709b9a38380cedd778ea4c0e2891304da8c3f3167"),
       "backfill_20Z": (AI + "/receipts/BACKFILL_probe_1789228800_vs_1789243200.json", "a421561f55875d3805103e89e7ecb771965b7c4b676e96d7d6a93159b23ea759"),
       "prod_stateH_sums": (PRODH + "/ATTR_prod_stateH_SHA256SUMS.txt", "243a78d78a87ac24d480fc322643ee943706afe33e856dc15a7175f3947f50fc"),
       "bundle_config": ("/workspace/shadow_bundle_v3/config.json", "3a8422f377519cac77b0c42305d2ba40a4b7a42a830f0542bda844f66647c94e")}
SH = {}
for k, (p, s) in PIN.items():
    SH[k] = sha(p); assert SH[k] == s, (k, SH[k], s)
G2CV = json.load(open(RC + "/G2C_verdict.json")); PREP = json.load(open(RC + "/G2C_prep.json"))
chain_p = W + "/g2c_chain/receipts/PARITY_G2C_chain_1788624000_1789200000.json"; assert sha(chain_p) == G2CV["chain_receipt_sha256"]
hyb_p = W + "/g2c_chain/home/wide_shadow/state/rolling.npz"; assert sha(hyb_p) == PREP["runs"]["g2c_chain"]["hybrid_sha256"]
SUMS = {}
for l in open(PIN["prod_stateH_sums"][0]):
    if l.strip(): d_, f_ = l.rstrip("\n").split("  ", 1); SUMS[f_] = d_
cfg = json.load(open(PIN["bundle_config"][0])); SYMS = list(cfg["symbols_panel"]); LIVE = list(cfg["symbols_live"]); col = {s: j for j, s in enumerate(SYMS)}
lidx = np.array([col[s] for s in LIVE], np.int64)
ANCH = [1788624000 + 14400 * k for k in range(41)]; A_PREV0 = 1788609600
R = {"device": os.path.abspath(__file__), "self_sha256": sha(os.path.abspath(__file__)), "env": dict(os.environ), "inputs": {k: {"path": PIN[k][0], "sha256": SH[k]} for k in PIN},
     "g2c_chain_receipt": {"path": chain_p, "sha256": G2CV["chain_receipt_sha256"]}, "g2c_chain_hybrid_rolling_sha256": PREP["runs"]["g2c_chain"]["hybrid_sha256"], "utc_start": iso(T0)}

# (1) state sources
src_re = re.compile(r"kc_src=(\S+) fc_src=(\S+)")
def tail_src(rec):
    out = []
    for a in rec["anchors"]:
        m = [src_re.search(t) for t in ((a.get("combo") or {}).get("tail") or [])]; m = [x for x in m if x]
        out.append((int(a["anchor"]), (m[-1].group(1), m[-1].group(2)) if m else None))
    return out
P1 = json.load(open(PIN["phase1_chain_receipt"][0])); GC = json.load(open(chain_p))
s1 = {}
for name, rec in (("phase1_chain", P1), ("g2c_chain", GC)):
    ts_ = tail_src(rec)
    s1[name] = {"anchors": [a for a, _ in ts_] == ANCH, "n_own_own": sum(1 for _, v in ts_ if v == ("own", "own")), "not_own": [(a, v) for a, v in ts_ if v != ("own", "own")]}
rep_tc = []; prod_tc = []
for A in ANCH:
    r = json.load(open(f"{W}/g2c_chain/replay_home/state/target_combo/{A}.json")); p = json.load(open(f"{W}/live_ro/state/target_combo/{A}.json"))
    rep_tc.append((r["kc_state_source"], r["fc_state_source"])); prod_tc.append((p["kc_state_source"], p["fc_state_source"]))
s1["g2c_chain_replay_target_combo_own_own"] = sum(1 for v in rep_tc if v == ("own", "own")); s1["producer_target_combo_own_own"] = sum(1 for v in prod_tc if v == ("own", "own"))
s1["producer_target_combo_not_own"] = [(A, v) for A, v in zip(ANCH, prod_tc) if v != ("own", "own")]
fp = {}
for tag in ("f10", "kc", "fc"):
    f = f"state_H_{tag}_{A_PREV0}.npz"
    fp[tag] = {"producer_sha256": SUMS.get(f), "phase1_chain_copy_sha256": sha(f"{AI}/replay_home/fea171/{f}"), "g2c_chain_copy_sha256": sha(f"{W}/g2c_chain/replay_home/fea171/{f}"),
               "g2c_tree_home_sha256": sha(f"{W}/g2c_chain/home/wide_shadow/fea171/{f}")}
    fp[tag]["all_equal_producer"] = len({fp[tag]["producer_sha256"], fp[tag]["phase1_chain_copy_sha256"], fp[tag]["g2c_chain_copy_sha256"], fp[tag]["g2c_tree_home_sha256"]}) == 1 and fp[tag]["producer_sha256"] is not None
    z = np.load(f"{W}/g2c_chain/replay_home/fea171/{f}"); fp[tag]["anchor_field"] = int(z["anchor"])
s1["first_anchor_prev_state_files"] = fp
def dense(p):
    z = np.load(p); v = np.zeros(829); v[z["idx"].astype(int)] = z["val"]; return v
per = []
for A in ANCH:
    row = {"anchor": A}
    for tag in ("f10", "kc", "fc"):
        f = f"state_H_{tag}_{A}.npz"; pp = f"{PRODH}/{f}"; rp = f"{W}/g2c_chain/replay_home/fea171/{f}"
        if f in SUMS and os.path.exists(rp):
            assert sha(pp) == SUMS[f]; d = np.abs(dense(rp) - dense(pp)); row[tag] = {"Linf": float(d.max()), "n_gt_1e6": int((d > 1e-6).sum()), "worst": SYMS[int(np.argmax(d))]}
        else:
            row[tag] = None
    gca = next(a for a in GC["anchors"] if int(a["anchor"]) == A); cb = gca.get("combo") or {}
    row["target_live_Linf"] = cb.get("target_live_Linf"); row["target_combo_Linf"] = cb.get("target_combo_Linf"); per.append(row)
s1["g2c_chain_state_H_vs_producer"] = per
s1["summary"] = {tag: {"n_with_file": sum(1 for r in per if r[tag]), "n_exact0": sum(1 for r in per if r[tag] and r[tag]["Linf"] == 0.0), "max": max((r[tag]["Linf"] for r in per if r[tag]), default=None)} for tag in ("f10", "kc", "fc")}
R["B1_state_sources"] = s1

# (2) backfill probes
R["B2_backfill_probes"] = {k: {kk: json.load(open(PIN[k][0])).get(kk) for kk in ("early_anchor", "late_anchor", "rows_compared", "cells_filled_later", "cells_lost", "cells_changed_finite", "symbols_with_fill")}
                           for k in ("backfill_12Z", "backfill_16Z", "backfill_20Z")}
R["B2_all_zero"] = all(v["cells_filled_later"] == 0 and v["cells_lost"] == 0 and v["cells_changed_finite"] == 0 for v in R["B2_backfill_probes"].values())

# (3) deficit table
S0 = np.load(PIN["snap_1789200000_rolling"][0], allow_pickle=True); s0ts = S0["ts"].astype(np.int64); s0d = S0["data"]
HY = np.load(hyb_p, allow_pickle=True); hts = HY["ts"].astype(np.int64); hd = HY["data"]
assert np.array_equal(s0ts, hts) and len(s0ts) == 11520
deficit = []
for A in ANCH:
    n_le = int((s0ts <= A).sum()); deficit.append({"anchor": A, "utc": iso(A), "rows_le_A": n_le, "producer_rows": 11520, "deficit": 11520 - n_le, "first_row_utc_replay": iso(s0ts[0]), "first_row_utc_producer": iso(A - 11519 * 300)})
R["B3_left_boundary_deficit"] = {"per_anchor": deficit, "deficit_first": deficit[0]["deficit"], "deficit_last": deficit[-1]["deficit"], "formula_1920_minus_48k_holds": all(d["deficit"] == 1920 - 48 * k for k, d in enumerate(deficit))}

# (4) dead names
def dead_set(ts, d, A):
    w = (ts > A - 86400) & (ts <= A); assert int(w.sum()) == 288, (A, int(w.sum()))
    lc = d[w][:, lidx, 4].astype(np.float64)
    return set(int(j) for j in lidx[~np.any(np.isfinite(lc) & (lc > 0), axis=0)])
per4 = []
for A in ANCH:
    ds = dead_set(s0ts, s0d, A); dh = dead_set(hts, hd, A)
    wz = np.load(f"{W}/live_ro/state/weights/{A}.npz"); mem = set(int(x) for x in wz["members"]); kw = set(int(x) for x in wz["idx"][np.abs(wz["val"]) > 0])
    tk = json.load(open(f"{W}/live_ro/state/target_live_king/{A}.json"))["weights"]; tc = json.load(open(f"{W}/live_ro/state/target_combo/{A}.json")); tl = json.load(open(f"{W}/live_ro/state/target_live/{A}.json"))["weights"]
    names = sorted(SYMS[j] for j in ds)
    per4.append({"anchor": A, "n_dead_live": len(ds), "hybrid_equal": ds == dh, "n_in_members_F10_cross_section": len(ds & mem), "n_members": len(mem), "producer_n_f10_scored": tc.get("n_f10_scored"),
                 "n_in_king_weights": len(ds & kw), "n_in_target_live_king": sum(1 for s in names if s in tk), "n_in_target_combo": sum(1 for s in names if s in tc["weights"]),
                 "n_in_target_live": sum(1 for s in names if s in tl), "dead_in_members": sorted(SYMS[j] for j in ds & mem), "dead_names": names})
snap4 = {}
for A in (1789214400, 1789228800, 1789243200):
    Z = np.load(PIN[f"snap_{A}_rolling"][0], allow_pickle=True); zts = Z["ts"].astype(np.int64); assert int(zts[-1]) >= A
    ds = dead_set(zts, Z["data"], A); aux = json.load(open(PIN[f"snap_{A}_aux"][0])); pr = aux["prev_rec"]; pm = set(int(x) for x in pr["members"])
    wz = np.load(f"{W}/live_ro/state/weights/{A}.npz")
    snap4[str(A)] = {"prev_rec_anchor": pr["anchor_ts"], "n_dead_live": len(ds), "n_in_aux_prev_rec_members": len(ds & pm), "aux_members_equal_weights_members": sorted(pm) == sorted(int(x) for x in wz["members"]),
                     "dead_in_members": sorted(SYMS[j] for j in ds & pm)}
R["B4_dead_names"] = {"rule": "no 5m bar in (A-24h, A] with finite log_cnt (channel 4 = log1p(trade count)) > 0; live names only (symbols_live 450)", "per_anchor": per4, "snapshot_anchors": snap4,
                      "summary": {"n_anchors": len(per4), "n_anchors_with_dead": sum(1 for r in per4 if r["n_dead_live"]), "max_dead": max(r["n_dead_live"] for r in per4),
                                  "n_anchors_dead_in_F10_cross_section": sum(1 for r in per4 if r["n_in_members_F10_cross_section"]), "max_dead_in_F10_cross_section": max(r["n_in_members_F10_cross_section"] for r in per4),
                                  "n_anchors_dead_in_target_live": sum(1 for r in per4 if r["n_in_target_live"]), "hybrid_equal_all": all(r["hybrid_equal"] for r in per4),
                                  "members_count_equals_n_f10_scored_all": all(r["n_members"] == r["producer_n_f10_scored"] for r in per4)}}
R["runtime_s"] = round(time.time() - T0, 1)
json.dump(R, open(OUT + ".tmp", "w"), indent=1); os.replace(OUT + ".tmp", OUT)
b4 = R["B4_dead_names"]["summary"]
print("ATTR_STAGE_B done | B1 own/own phase1=%d/41 g2c=%d/41 replay_tc=%d prod_tc=%d first_prev_equal=%s state_H_summary=%s | B2 all_zero=%s | B3 deficit %d->%d formula=%s | B4 %s | receipt_sha256=%s"
      % (s1["phase1_chain"]["n_own_own"], s1["g2c_chain"]["n_own_own"], s1["g2c_chain_replay_target_combo_own_own"], s1["producer_target_combo_own_own"], {t: fp[t]["all_equal_producer"] for t in fp},
         json.dumps(s1["summary"]), R["B2_all_zero"], R["B3_left_boundary_deficit"]["deficit_first"], R["B3_left_boundary_deficit"]["deficit_last"], R["B3_left_boundary_deficit"]["formula_1920_minus_48k_holds"],
         json.dumps(b4), sha(OUT)), flush=True)
