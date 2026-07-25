"""Nail the true 3-fold champion IC + re-run T2a with the correct champion, and characterize
the available xattn seed triple honestly. Writes /tmp/0c_probe.json."""
import os
import json, sys, numpy as np
MA = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # .../multi_asset
sys.path.insert(0, MA + "/handoff")
import acceptance_battery as ab
M = MA + "/exports/train"
THR = {k: v for k, v in json.load(open(MA + "/handoff/acceptance_thresholds_0C_frozen.json")).items() if not k.startswith("_")}


def poolic(prod):
    rows = ab.all_oos_rows(prod)
    ics, _ = ab.ic_series(prod, prod["S"], rows)
    pf = []
    for f in prod["folds"]:
        i2, _ = ab.ic_series(prod, f["C"], f["te_rows"])
        pf.append(round(float(np.mean(i2)), 4))
    return round(float(np.mean(ics)), 4), pf


OUT = {}
dirs = {"lamorth0_xattn(champ3?)": "wideA_lamorth0_xattn", "lamorth0(no-xattn)": "wideA_lamorth0",
        "xattn(seed42)": "wideA_xattn", "xattn_seed43": "wideA_xattn_seed43",
        "xattn_seed44": "wideA_xattn_seed44", "conformer_ref(lamorth1)": "wideA_conformer_ref"}
prods = {}
for tag, d in dirs.items():
    p = ab.load_products(f"{M}/{d}", THR["min_base"])
    ic, pf = poolic(p)
    OUT[tag] = dict(pooled_ic=ic, per_fold=pf, md5=p["panel_md5"])
    prods[tag] = p
    print(f"{tag:26s} pooled={ic} perfold={pf} md5={p['panel_md5']}", flush=True)

# correct T2a: conformer vs the HIGHEST-IC 3-fold champion
champ_tag = max(("lamorth0_xattn(champ3?)", "xattn(seed42)"), key=lambda t: OUT[t]["pooled_ic"])
champ3 = prods[champ_tag]
OUT["_champ3_used"] = champ_tag
rep = ab.run_battery(prods["conformer_ref(lamorth1)"], champ=champ3, thr=THR)
gb = [g for g in rep["gates"] if g["name"] == "b_honest_ensemble_ic"][0]
OUT["T2a_corrected"] = dict(verdict=rep["verdict"], failed=rep["failed_gates"],
                            cand_ic=gb["pooled_ic"], champ_ic=gb["champion_ic"], thresh=gb["threshold"])
print("T2a_corrected:", OUT["T2a_corrected"], flush=True)

# gate g on the available xattn seed triple (penalized variant — honest label)
seedp = {t: prods[t] for t in ("xattn(seed42)", "xattn_seed43", "xattn_seed44")}
# map to load_products-style dict keyed for gate_g
gg = ab.gate_g_seeds({k: v for k, v in seedp.items()}, THR)
OUT["G_xattn_penalized_triple"] = dict(cov=gg.get("cov"), passed=gg["passed"],
                                       per_seed={k: v["mean"] for k, v in gg.get("per_seed", {}).items()})
print("G penalized triple:", OUT["G_xattn_penalized_triple"], flush=True)

json.dump(OUT, open("/tmp/0c_probe.json", "w"), indent=1, default=str)
print("SAVED /tmp/0c_probe.json", flush=True)
