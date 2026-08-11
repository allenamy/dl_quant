"""HOLD (comment out) the remaining always-Run2 completeness fillers so the runner
IDLES after basis_2025_10 instead of auto-advancing. Recoverable (commented, not
deleted). Idempotent. Does NOT touch basis_2025_10 (running) or anything above it."""
Q = "/mnt/storage/private/work_hsy/quant_research_multi_asset/experiments/d1gate/queue.txt"
HOLD = {
    "configs/d1gate/d1_2025_12_run2.json",
    "configs/d1gate/d1_2026_02_run2.json",
    "configs/d1gate/d1_2026_03_run2.json",
    "configs/d1gate/d1_2026_05_run2.json",
    "configs/d1gate/lora_2026_04.json",
    "configs/d1gate/d1_2026_01_run1_b1024.json",
}
PFX = "# HELD 07-05 (reallocation by basis_2025_10 result): "
lines = [l.rstrip("\n") for l in open(Q)]
out, held = [], []
for l in lines:
    s = l.strip()
    if s in HOLD:                 # active entry -> comment it
        out.append(PFX + s); held.append(s)
    else:
        out.append(l)
open(Q, "w").write("\n".join(out) + "\n")
print(f"held {len(held)} completeness fillers:")
for h in held:
    print("   ", h)
print("--- queue tail (active entries only) ---")
for i, l in enumerate(out, 1):
    s = l.strip()
    if s and not s.startswith("#"):
        print(f"  {i:>3}  {l}")
