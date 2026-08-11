import json
q = "experiments/d1gate/queue.txt"
lines = open(q).read().splitlines()
# (1) dequeue aux_2026_04 + aux_2025_12
lines = [l for l in lines if "aux_2026_04" not in l and "aux_2025_12" not in l]
# (2) insert rank_2026_01 -> rank_2026_04 right after aux_2026_01 (running)
out, ins = [], False
for l in lines:
    out.append(l)
    if "aux_2026_01" in l and not ins:
        out += ["configs/arms/rank_2026_01.json", "configs/arms/rank_2026_04.json"]
        ins = True
assert ins, "aux_2026_01 anchor not found"
open(q, "w").write("\n".join(out) + "\n")
print("QUEUE_EDIT_DONE")

# rank config sanity
c = json.load(open("configs/arms/rank_2026_01.json"))
m, d = c["model"], c["data"]
print("rank revin_skip_idx present:", "revin_skip_idx" in m,
      "| n:", len(m.get("revin_skip_idx", [])))
print("rank use_fixed_regime_state:", m.get("use_fixed_regime_state"))
print("rank npz_dir:", d.get("npz_dir"), "| state_prior_dir:", d.get("state_prior_dir"))
print("rank fold:", c["training"]["fold_test_starts"], "| out:", c["output_dir"])
print("NEW QUEUE:")
for l in open(q).read().splitlines():
    if l and not l.startswith("#"):
        print("  ", l)
