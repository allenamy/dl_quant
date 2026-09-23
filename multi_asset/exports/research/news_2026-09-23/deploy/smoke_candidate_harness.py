"""Smoke test of the candidate-acceptance MACHINERY (mac_candidate_acceptance.Candidate) against production itself: candidate = the
in-service models, no symbols_fetch, no re-seed; starting state = production's own at A0 (prev_rec, seats, kc/fc files); one anchor A1.
If the sandbox faithfully reproduces production, the served prev_rec / w3 / combo_raw / publish at A1 equal production's archived
ones bitwise. Mac, production venv, quiet window; never writes ~/wide_shadow."""
import os, sys, json, argparse, hashlib
import numpy as np
P = os.path.expanduser("~/cc_tmp/news_20260923"); WS = os.path.expanduser("~/wide_shadow")
sys.path.insert(0, f"{P}/devices"); sys.path.insert(0, f"{P}/deploy")
import mac_candidate_acceptance as CA


def main():
    A0 = int(sys.argv[1]); A1 = A0 + 14400; out = f"{P}/deploy/smoke_candidate"; os.makedirs(out, exist_ok=True)
    cfg = json.load(open(f"{WS}/shadow_bundle/config.json")); syms = cfg["symbols_panel"]; NW = len(syms)
    aux = json.load(open(f"{WS}/state/snap/{A0}/aux.json")); pr = aux["prev_rec"]; lr = json.load(open(f"{WS}/state/snap/{A0}/leg_returns_live.json"))
    E = {"symbols": np.array(syms), f"m_{A0}": np.array(pr["members"]), f"KZ_{A0}": np.array(pr["legz"]["king"]), f"Z24_{A0}": np.array(pr["legz"]["rev24"]),
         f"ZFD_{A0}": np.array(pr["legz"]["fund"]), f"LR_upto_{A0}": np.stack([lr["king"], lr["rev24"], lr["fund"]], 1)}
    for tag in ("kc", "fc"):
        z = np.load(f"{WS}/fea171/state_H_{tag}_{A0}.npz"); v = np.zeros(NW); v[z["idx"].astype(int)] = z["val"]; E[f"{tag}_{A0}"] = v
    ep = f"{out}/prod_eval_{A0}.npz"; np.savez(ep, **E)
    a = argparse.Namespace(king=f"{WS}/shadow_bundle/slow2026.txt", f10=f"{WS}/fea171/f10_live_s42_np.npz", eval=ep, replay=f"{P}/parity/parity_fund_slice.npz",
                           added=f"{P}/deploy/added_names.json", x0918r=f"{P}/parity/parity_cache_slice.npz", holes=f"{P}/parity/parity_holes_slice.npz",
                           producer=f"{P}/deploy/producer_patch/shadow_loop_v3.py", out=out, start=A0, n=1)
    cand = CA.Candidate(a, f"{out}/sandbox", a.f10, fetchlist=False, reseed=False); cand.build(A0)
    # the production chain started from its OWN king-book weights and prev_rec: restore the production prev_rec exactly
    s = cand.step(A1)
    auxA1 = json.load(open(f"{WS}/state/snap/{A1}/aux.json")); prA1 = auxA1["prev_rec"]
    tcA1 = json.load(open(f"{WS}/state/target_combo/{A1}.json")); stA1 = json.load(open(f"{WS}/state/snap/{A1}/combo_live_status.json"))
    wz = np.load(f"{WS}/state/weights_combo/{A1}.npz"); raw = np.zeros(NW); raw[wz["idx"].astype(int)] = wz["val"].astype(np.float64)
    r = {"A0": A0, "A1": A1, "combo_rc": s["rc"],
         "prev_rec_members_equal": s["prev_rec"]["members"] == prA1["members"],
         "prev_rec_legz_equal": all(s["prev_rec"]["legz"][k] == prA1["legz"][k] for k in ("king", "rev24", "fund")),
         "w3_masked_equal": s["target_combo"]["w3_masked"] == tcA1["w3_masked"],
         "target_combo_weights_equal": s["target_combo"]["weights"] == tcA1["weights"],
         "combo_raw_f32_bitwise": bool(np.array_equal(s["combo_raw_f32"].view(np.uint64), raw.view(np.uint64))),
         "publish_equal": bool(s["status"].get("ok")) == bool(stA1.get("ok")),
         "kc_src": s["target_combo"].get("kc_state_source"), "fc_src": s["target_combo"].get("fc_state_source")}
    r["PASS"] = all(v for k, v in r.items() if k.endswith("_equal") or k.endswith("_bitwise")) and r["combo_rc"] == 0
    json.dump(r, open(f"{out}/SMOKE_CANDIDATE_HARNESS.json", "w"), indent=1); print("SMOKE", json.dumps(r)); sys.exit(0 if r["PASS"] else 3)


if __name__ == "__main__":
    main()
