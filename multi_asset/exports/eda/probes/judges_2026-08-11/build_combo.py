"""Build STATE+RANK combo configs = Run2 substrate (state d24 + gain) +
npz_v2arch_rank inputs + revin_skip_idx. Two surviving tail levers, different
mechanisms (conditioning vs input-norm), both raw-target (no objective conflict)."""
import json, copy

run2 = json.load(open("configs/d1gate/d1_2026_04_run2.json"))       # state+gain template
rank = json.load(open("configs/arms/rank_2026_01.json"))            # revin_skip_idx + rank npz
skip = rank["model"]["revin_skip_idx"]
assert len(skip) == 34, len(skip)

months = {"combo_2025_10": ("2025-10-10", "strong-guard"),
          "combo_2026_01": ("2026-01-10", "drift-hole"),
          "combo_2026_04": ("2026-04-10", "state-rules")}
for name, (ts, role) in months.items():
    c = copy.deepcopy(run2)
    # DATA: rank-normalised inputs + state overlay (compose; ts aligned, regime_prior 6-d -> 24)
    c["data"]["npz_dir"] = "data/npz_v2arch_rank"
    c["data"]["state_prior_dir"] = "data/npz_v2arch_state"
    c["data"].pop("align_target_dir", None); c["data"].pop("align_aux_dir", None)
    c["data"]["preload"] = True
    # MODEL: Run2 state+gain (d_prior=24) + rank input-norm bypass
    c["model"]["revin_skip_idx"] = skip
    c["model"]["n_horizons"] = 1
    assert c["model"]["use_state_prior"] and c["model"]["use_output_gain"] and c["model"]["d_prior"] == 24
    c["model"]["_comment"] = ("STATE+RANK combo: Run2 (state d24 + output gain) + npz_v2arch_rank "
                              "inputs + revin_skip_idx (34ch static-z stationary rank). Two tail "
                              "levers, no objective conflict (both raw y_600).")
    c["training"].pop("dul_config", None) or None  # keep Run2 dul_config as-is
    c["training"]["fold_test_starts"] = [ts]
    c["training"]["preload"] = True
    c["training"]["num_workers"] = 0
    c["training"]["save_epoch_ckpts"] = True
    c["training"]["_comment"] = f"COMBO {name} ({role}): state+gain + rank-norm inputs, raw target."
    c["_comment"] = (f"STATE+RANK combo {name} — final component-freeze candidate. Run2 state+gain "
                     f"+ rank-norm inputs (revin_skip 34ch). Role={role}. Eval standard raw-y.")
    c["output_dir"] = f"experiments/combo/{name}"
    json.dump(c, open(f"configs/d1gate/{name}.json", "w"), indent=2)
    print(f"built {name}: fold={ts} npz={c['data']['npz_dir'].split('_')[-1]} "
          f"revin_skip={len(skip)} state=yes gain={c['model']['use_output_gain']} d_prior={c['model']['d_prior']}")
