"""Derive basis_{month} configs from d1_{month}_run1 — change ONLY npz_dir,
revin_skip_idx, output_dir, _comment. Everything else identical (apples-to-apples)."""
import json, os, copy

MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset"
CFGDIR = os.path.join(MA, "configs", "d1gate")
# instantaneous cross-basis levels (80=x_mid_ratio_log, 81=x_basis_bps) + 10 X_basis dynamics (88..97)
REVIN_SKIP = [80, 81, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97]

for month in ["2026_01", "2025_10"]:
    src = os.path.join(CFGDIR, f"d1_{month}_run1.json")
    d = json.load(open(src))
    base_npz = d["data"]["npz_dir"]
    base_skip = d["model"].get("revin_skip_idx")
    d["data"]["npz_dir"] = "data/npz_v2arch_augms"
    d["model"]["revin_skip_idx"] = REVIN_SKIP
    d["output_dir"] = f"experiments/d1gate/basis_{month}"
    d["model"]["_comment"] = (
        f"BASIS-FULL arm = d1_{month}_run1 (bugfix-only Run1) + X_basis(10 dynamics, ch88:97) "
        f"concatenated into X on npz_v2arch_augms (base-88 byte-identical) + RevIN-skip on "
        f"instantaneous cross-basis 80/81 and the 10 X_basis 88:97. All model/training/dul/seed/"
        f"fold identical to Run1. Gate: 2026-01 drift dP>=+0.005 clean AND 2025-10 strong >=-0.005."
    )
    out = os.path.join(CFGDIR, f"basis_{month}.json")
    json.dump(d, open(out, "w"), indent=2)
    print(f"wrote {out}")
    print(f"   npz_dir: {base_npz} -> {d['data']['npz_dir']}")
    print(f"   revin_skip_idx: {base_skip} -> {d['model']['revin_skip_idx']}")
    print(f"   output_dir: {d['output_dir']}")
    print(f"   fold_test_starts: {d['training']['fold_test_starts']}  seed(train)={d['training'].get('seed')} epochs={d['training']['epochs']} patience={d['training']['patience']}")
    # sanity: confirm the ONLY diffs vs run1 are the 4 intended keys
    ref = json.load(open(src))
    diffs = []
    def walk(a, b, path=""):
        if isinstance(a, dict):
            for k in set(a) | set(b):
                walk(a.get(k), b.get(k), path + "/" + k)
        else:
            if a != b:
                diffs.append(path)
    walk(ref, d)
    print(f"   DIFFS vs run1: {sorted(diffs)}")
