"""Build the 4 arch_iter configs from d1_*_run1. CONCAT: +model.use_perp_concat.
TAILW: +training.dul_config.use_tail_weight (+gamma/max). Else identical to Run1."""
import json, os
MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset"
SRC = f"{MA}/configs/d1gate"
OUT = f"{MA}/configs/arch_iter"
os.makedirs(OUT, exist_ok=True)

def diffs(a, b):
    out = []
    def walk(x, y, p=""):
        if isinstance(x, dict) or isinstance(y, dict):
            x = x or {}; y = y or {}
            for k in set(x) | set(y):
                walk(x.get(k), y.get(k), p + "/" + k)
        elif x != y:
            out.append(p)
    walk(a, b); return sorted(out)

for m in ["2025_10", "2026_01"]:
    run1 = json.load(open(f"{SRC}/d1_{m}_run1.json"))

    # ARM CONCAT
    c = json.loads(json.dumps(run1))
    c["model"]["use_perp_concat"] = True
    c["output_dir"] = f"experiments/arch_iter/concat_{m}"
    c["model"]["_comment"] = (f"ARM CONCAT = d1_{m}_run1 + perp CONCAT fusion "
        f"(use_perp_concat=True): concat[h|perp_proj(h_perp)]->fusion Linear->d_model, "
        f"replacing the additive gated residual. Gated OFF=bit-identical to Run1. "
        f"Guard: 2025_10 PROTECT / 2026_01 LIFT. Gate on Pearson AND Spearman vs run1.")
    json.dump(c, open(f"{OUT}/concat_{m}.json", "w"), indent=2)
    print(f"concat_{m}: diffs vs run1 = {diffs(run1, c)}")

    # ARM TAILW
    t = json.loads(json.dumps(run1))
    t["training"]["dul_config"]["use_tail_weight"] = True
    t["training"]["dul_config"]["tail_weight_gamma"] = 1.0
    t["training"]["dul_config"]["tail_weight_max"] = 3.0
    t["output_dir"] = f"experiments/arch_iter/tailw_{m}"
    t["model"]["_comment"] = (f"ARM TAILW = d1_{m}_run1 + bounded tail-weight on the "
        f"PRIMARY rank+dir_Huber terms (use_tail_weight, w=clamp(1+|y|/sigma,max=3)). "
        f"Gated OFF=bit-identical. Bounded emphasis (anti-#12) => gate on Pearson AND "
        f"Spearman. Guard: 2025_10 PROTECT / 2026_01 LIFT.")
    json.dump(t, open(f"{OUT}/tailw_{m}.json", "w"), indent=2)
    print(f"tailw_{m}:  diffs vs run1 = {diffs(run1, t)}")
