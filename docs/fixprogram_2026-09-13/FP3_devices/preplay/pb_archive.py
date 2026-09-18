#!/usr/bin/env python3
"""P-B receipt: per-anchor deviation curve of a preplay run vs the production archive, bound to the driver bytes that produced it, with phase means at the
production interventions and the seat-vector agreement. usage: pb_archive.py <run_dir> <driver.py> <out.json> [label]"""
import json, sys, time, hashlib, os, numpy as np
RUN, DRV, OUT = sys.argv[1:4]; LABEL = sys.argv[4] if len(sys.argv) > 4 else os.path.basename(RUN)
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
rows = [json.loads(l) for l in open(f"{RUN}/PREPLAY_anchors.jsonl")]
CUTS = [(1788350400, "09-02 12Z combo FTRIM b5c698f9"), (1788494400, "09-04 04Z shadow M1 e9c98374"), (1788624000, "09-05 16Z seat seeding (file 4a3bfd9a9353)"), (1789660800, "09-17 16Z combo 3520d363")]
per = []
for r in rows:
    k = r.get("king_vs_archive") or {}; c = r.get("combo_vs_archive") or {}; c = c if isinstance(c, dict) else {}
    per.append({"anchor_ts": r["anchor_ts"], "utc": r["utc"], "king_l1_rel": k.get("l1_rel"), "king_max_abs_dw": k.get("max_abs_dw"), "king_n_diff": k.get("n_diff_gt_1e-6"), "combo_l1_rel": c.get("l1_rel"), "combo_max_abs_dw": c.get("max_abs_dw"), "combo_rc": r.get("combo_rc"), "w3_max_abs_diff": r.get("w3_max_abs_diff"), "members_symdiff": r.get("members_symdiff_vs_archive"), "versions": r.get("versions"), "fetch_calls": r.get("fetch_calls")})
ts = np.array([p["anchor_ts"] for p in per]); kl = np.array([p["king_l1_rel"] if p["king_l1_rel"] is not None else np.nan for p in per], float); cl = np.array([p["combo_l1_rel"] if p["combo_l1_rel"] is not None else np.nan for p in per], float); w3 = np.array([p["w3_max_abs_diff"] if p["w3_max_abs_diff"] is not None else np.nan for p in per], float)
edges = sorted(set([int(ts.min())] + [c for c, _ in CUTS if ts.min() < c <= ts.max()] + [int(ts.max()) + 1])); names = {c: n for c, n in CUTS}
phases = []
for a, b in zip(edges[:-1], edges[1:]):
    m = (ts >= a) & (ts < b)
    phases.append({"from": time.strftime("%m-%d %HZ", time.gmtime(a)), "to_excl": time.strftime("%m-%d %HZ", time.gmtime(b)), "starts_with": names.get(a, "start"), "n": int(m.sum()), "king_l1_mean": float(np.nanmean(kl[m])), "king_l1_median": float(np.nanmedian(kl[m])), "king_l1_max": float(np.nanmax(kl[m])), "combo_l1_mean": float(np.nanmean(cl[m])), "combo_l1_median": float(np.nanmedian(cl[m])), "combo_l1_max": float(np.nanmax(cl[m])), "w3_max_abs_diff_max": float(np.nanmax(w3[m])), "w3_exact_frac": float(np.mean(w3[m] <= 1e-9))})
last = per[-1]; first = per[0]
out = {"device": "pb_archive.py", "self_sha256": sha(__file__), "utc": time.strftime("%FT%TZ", time.gmtime()), "label": LABEL, "run_dir": RUN, "driver": {"path": DRV, "sha256": sha(DRV)}, "n_anchors": len(per), "first": first["utc"], "last": last["utc"],
       "members_symdiff_all_zero": all((p["members_symdiff"] or 0) == 0 for p in per), "combo_rc_all_zero": all((p["combo_rc"] or 0) == 0 for p in per), "phases": phases, "per_anchor": per,
       "reads": "same producer/combo bytes as production at each anchor (versions per row), HistFetcher = the only injection (klines from the research cache prefill, exchangeInfo inferred from 24h settlements, fundingRate from the producer's own ledger); bootstrap state from the bundle + causal corrections, NOT the true 08-30 production state ⇒ the residual is initial-state lineage decaying; from the seeding anchor on the seat vector equals production's (w3 diff 0)"}
json.dump(out, open(OUT, "w"), indent=1)
print("n", len(per), "first", first["utc"], "last", last["utc"], "driver", out["driver"]["sha256"][:8])
for p in phases: print(f"  {p['from']}→{p['to_excl']} ({p['starts_with']}): n {p['n']} king L1 mean {p['king_l1_mean']:.4f} max {p['king_l1_max']:.4f} | combo mean {p['combo_l1_mean']:.4f} max {p['combo_l1_max']:.4f} | w3 exact {p['w3_exact_frac']:.2f} max {p['w3_max_abs_diff_max']:.4f}")
print("last 6:", [(p["utc"], round(p["king_l1_rel"], 4), round(p["combo_l1_rel"], 4), p["w3_max_abs_diff"]) for p in per[-6:]])
