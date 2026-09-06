"""identity_fold.py — generic single-fold identity receipt: <mine_dir> <ref_dir> <tag_mine> <tag_ref> <YM> <out.json> [extra config keys to exclude, csv]
preds_fold npz sha equal, P bitwise equal, .pt sha equal, config equal except best_epoch_rule/self_sha256/wall_clock_s/epoch_s/finished_utc + extras."""
import json, hashlib, numpy as np, os, sys
mine, ref, tm, tr, YM, out = sys.argv[1:7]; extra = set(sys.argv[7].split(",")) if len(sys.argv) > 7 else set(); sh = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
pm, pr = f"{mine}/preds_fold/{tm}_{YM}.npz", f"{ref}/preds_fold/{tr}_{YM}.npz"; ptm, ptr = f"{mine}/models/{tm}_{YM}.pt", f"{ref}/models/{tr}_{YM}.pt"
Pm, Pr = np.load(pm)["P"], np.load(pr)["P"]; Cm, Cr = json.load(open(f"{mine}/models/{tm}_{YM}_config.json")), json.load(open(f"{ref}/models/{tr}_{YM}_config.json"))
skip = {"best_epoch_rule", "self_sha256", "wall_clock_s", "epoch_s", "finished_utc", "tag"} | extra
diff = {k: (Cm.get(k), Cr.get(k)) for k in set(Cm) | set(Cr) if k not in skip and Cm.get(k) != Cr.get(k)}
OUT = {"fold": int(YM), "mine": pm, "ref": pr, "preds_npz_sha_mine": sh(pm), "preds_npz_sha_ref": sh(pr), "preds_npz_sha_equal": sh(pm) == sh(pr), "P_bitwise_equal": bool(np.array_equal(Pm, Pr, equal_nan=True)), "P_max_abs_delta": float(np.nanmax(np.abs(Pm - Pr))),
       "pt_sha_mine": sh(ptm), "pt_sha_ref": sh(ptr), "pt_sha_equal": sh(ptm) == sh(ptr), "config_excluded": sorted(skip), "config_differences": diff, "best_epoch_mine": Cm["best_epoch"], "best_epoch_ref": Cr["best_epoch"], "self_sha_mine": Cm["self_sha256"], "self_sha_ref": Cr["self_sha256"], "mine_extra": {k: Cm.get(k) for k in ("init_mode", "init_state_path", "lr", "best_epoch_rule")}}
OUT["verdict"] = "IDENTITY_OK" if (OUT["preds_npz_sha_equal"] and OUT["P_bitwise_equal"] and OUT["pt_sha_equal"] and not diff) else "IDENTITY_FAIL"
os.makedirs(os.path.dirname(out), exist_ok=True); json.dump(OUT, open(out, "w"), indent=1); print(json.dumps({k: v for k, v in OUT.items() if k != "config_excluded"}, indent=1)); print(OUT["verdict"])
