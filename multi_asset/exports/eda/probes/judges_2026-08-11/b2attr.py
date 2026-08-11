import sys, numpy as np, pandas as pd
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset")
src_txt = open("/mnt/storage/private/work_hsy/probe_artifacts/breadth2.py").read()
exec(src_txt.split('R = {"prereg_sha"')[0])
YRS = (int(src.ts[anchors[-1]]) - int(src.ts[anchors[0]])) / (1000*3600*24*365.25)

def shr(p, t, c=3.63):
    return RF._dsharpe(pd.DataFrame({"day": DAY, "n": p - t*c*1e-4}).groupby("day").n.sum().values)

print("\n===== 毛额/换手分解 (E72-bis 预登记要求) =====")
print("臂           累计毛额    年化换手    Sh@3.63     Δ毛额     Δ换手   Δ夏普")
bp, bt, _ = run(None); bg = bp.sum(); bta = bt.sum()/YRS; bs = shr(bp, bt)
print(f"基线       {bg:+10.4f} {bta:10.1f}  {bs:+9.4f}")
for c in ["C1", "C2"]:
    for w in [0.05, 0.10]:
        p, t, _ = run(c, "real", w); g = p.sum(); ta = t.sum()/YRS; s = shr(p, t)
        print(f"{c} w={w:.2f} {g:+10.4f} {ta:10.1f}  {s:+9.4f}  {g-bg:+8.4f} {ta-bta:+8.1f} {s-bs:+7.4f}")
print("\n判读: 若 Δ夏普 主要由 Δ换手(负)驱动而非 Δ毛额(正) ⇒ 记在换手线, 不构成宽度。")
