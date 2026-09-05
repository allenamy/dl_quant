"""six_seed_rule.py — final adjudication under the S-1 precedent (team-lead 2026-09-05, rule stated before the numbers: ammunition campaign F7_ALL45
"擦线触发六种子终审"): for each arm, admit ⇔ mean over the 6 seeds {42, 2027, 7, 123, 2024, 31337} of Δavg(3 folds vs the same-seed BASE) ≥ +0.003
AND the 2026-fold Δ ≥ 0 in at least 5 of 6 seeds. Arms A1 and A1A2 judged separately (family of 2). The two-seed letter-of-the-gate verdict stays primary.
usage: six_seed_rule.py <s1_ALL.json> <s1_seeds4.json> <out.json>"""
import sys, json
import numpy as np
a, b, out = sys.argv[1:4]
J2 = json.load(open(a)); J4 = json.load(open(b))
res = {"rule": "mean_6seed_Δavg >= +0.003 AND 2026 Δ >= 0 in >= 5/6 seeds; arms judged separately", "seeds": [], "arms": {}}
for arm in ("A1", "A1A2"):
    rows = []
    for J in (J2, J4):
        for s, r in J["arms"][arm]["runs"].items():
            rows.append({"seed": int(s), "ic": r["ic"], "delta": r["delta"], "avg_delta": r["avg_delta"], "base_ic": J["arms"]["BASE"]["runs"][s]["ic"],
                         "rho_base": r["rho_base"], "ic_resid_base": r["ic_resid_base"], "base_ic_resid": J["arms"]["BASE"]["runs"][s]["ic_resid_base"]})
    rows.sort(key=lambda r: [42, 2027, 7, 123, 2024, 31337].index(r["seed"]))
    m = float(np.mean([r["avg_delta"] for r in rows])); n26 = sum(r["delta"]["2026"] >= 0 for r in rows)
    per_fold = {y: round(float(np.mean([r["delta"][y] for r in rows])), 4) for y in ("2024", "2025", "2026")}
    admit = (m >= 0.003) and (n26 >= 5) and len(rows) == 6
    res["arms"][arm] = {"per_seed": rows, "mean_avg_delta_6": round(m, 4), "mean_delta_by_fold": per_fold, "n_2026_ge0": n26, "n_seeds": len(rows),
                        "two_seed_letter_verdict": J2["arms"][arm]["verdict"], "six_seed_adjudication": "ADMIT" if admit else "NOT ADMITTED",
                        "mean_rho_base": {y: round(float(np.mean([r["rho_base"][y] for r in rows])), 3) for y in ("2024", "2025", "2026")},
                        "mean_ic_resid_minus_base": {y: round(float(np.mean([r["ic_resid_base"][y] - r["base_ic_resid"][y] for r in rows])), 4) for y in ("2024", "2025", "2026")}}
    print(f"{arm}: " + " | ".join(f"s{r['seed']} Δavg {r['avg_delta']:+.4f} (2026 {r['delta']['2026']:+.4f})" for r in rows))
    print(f"{arm}: mean6 {m:+.4f} by_fold {per_fold} 2026>=0 in {n26}/6 -> two-seed {J2['arms'][arm]['verdict']} | six-seed {res['arms'][arm]['six_seed_adjudication']}")
res["seeds"] = [r["seed"] for r in res["arms"]["A1"]["per_seed"]]
json.dump(res, open(out, "w"), indent=1); print("SIX_SEED_DONE")
