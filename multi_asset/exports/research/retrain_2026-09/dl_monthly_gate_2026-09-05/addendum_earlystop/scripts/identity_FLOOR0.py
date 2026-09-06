"""identity_FLOOR0.py — PREREG_dl_monthly_earlystop §1 identity receipt: the early-stop trainer with BEST_EP_FLOOR=0 (verbatim rule) on fold 202501 must
reproduce the CONST (mE1c seed 42) fold bitwise: preds_fold npz sha equal, .pt sha equal, per-fold config equal except best_epoch_rule / self_sha256 /
wall-clock fields (wall_clock_s, epoch_s, finished_utc). → earlystop/results/identity_FLOOR0.json"""
import json, hashlib, numpy as np, os
B = "/workspace/review_scratch/allweather_trackB"; sh = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
me = f"{B}/earlystop/FLOOR0/shard0"; ref = f"{B}/mE1_constseed/shard0"; YM = 202501
pm, pr = f"{me}/preds_fold/mE1c_{YM}.npz", f"{ref}/preds_fold/mE1c_{YM}.npz"; tm, tr = f"{me}/models/mE1c_{YM}.pt", f"{ref}/models/mE1c_{YM}.pt"
Pm, Pr = np.load(pm)["P"], np.load(pr)["P"]
Cm, Cr = json.load(open(f"{me}/models/mE1c_{YM}_config.json")), json.load(open(f"{ref}/models/mE1c_{YM}_config.json"))
skip = {"best_epoch_rule", "self_sha256", "wall_clock_s", "epoch_s", "finished_utc"}
diff = {k: (Cm.get(k), Cr.get(k)) for k in set(Cm) | set(Cr) if k not in skip and Cm.get(k) != Cr.get(k)}
OUT = {"fold": YM, "preds_npz_sha_mine": sh(pm), "preds_npz_sha_const": sh(pr), "preds_npz_sha_equal": sh(pm) == sh(pr), "P_bitwise_equal": bool(np.array_equal(Pm, Pr, equal_nan=True)), "P_max_abs_delta": float(np.nanmax(np.abs(Pm - Pr))),
       "pt_sha_mine": sh(tm), "pt_sha_const": sh(tr), "pt_sha_equal": sh(tm) == sh(tr), "config_fields_compared": sorted((set(Cm) | set(Cr)) - skip), "config_diff_excluding": sorted(skip), "config_differences": diff,
       "best_epoch_rule_mine": Cm.get("best_epoch_rule"), "best_epoch_mine": Cm["best_epoch"], "best_epoch_const": Cr["best_epoch"], "self_sha_mine": Cm["self_sha256"], "self_sha_const": Cr["self_sha256"]}
OUT["verdict"] = "IDENTITY_FLOOR0_OK" if (OUT["preds_npz_sha_equal"] and OUT["P_bitwise_equal"] and OUT["pt_sha_equal"] and not diff) else "IDENTITY_FLOOR0_FAIL"
os.makedirs(f"{B}/earlystop/results", exist_ok=True); json.dump(OUT, open(f"{B}/earlystop/results/identity_FLOOR0.json", "w"), indent=1)
print(json.dumps({k: v for k, v in OUT.items() if k != "config_fields_compared"}, indent=1)); print(OUT["verdict"])
