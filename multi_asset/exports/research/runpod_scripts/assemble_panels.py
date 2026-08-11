"""把 harness 臂组装成引擎可用的 (T,N) 严格 OOS 预测面板 —— #72 翻译测试的前置。

配方逐字照 multi_asset/data/build_s2_pred_panel.py:
  "Each ts uses ONLY its own test-fold's honest-ensemble composite
   (per-ts z-mean of the 6 factor heads over member&CL&finite cells)"
前提(已核验): 冠军臂用 --year_folds ⇒ 每个 ts 只属于它自己那年的测试折, 满足"只用自己 test-fold"。

★ 两侧必须同协议: y4 与 y8 都从 harness 臂出, 不与生产折 newgen 混用(跨世代跨协议比较是陷阱)。
"""
import numpy as np, glob, json, sys

P = np.load("/workspace/data/wide_dl_pm32_hz.npz", allow_pickle=True)
MEM = P["MEMBER110"]; ts = P["ts"]
T, N = MEM.shape

ARMS = {
    "y4": ["rb32_lam0_yr4_s42", "rb32_lam0_yr4_s2027", "rb32_lam0_yr4_s3037"],
    "y8": ["rb32_lam0_yr8_s42", "rb32_lam0_yr8_s2027", "rb32_lam0_yr8_s3037",
           "yr8_s4047", "yr8_s5051"],
}
CLKEY = {"y4": "CL4", "y8": "CL8"}


def composite(tag, CL):
    """返回 (T,N) 的严格 OOS 复合分, 非 OOS 处为 NaN。"""
    out = np.full((T, N), np.nan, dtype=np.float64)
    n_rows = 0
    for f in sorted(glob.glob(f"/workspace/exports_train/{tag}/fold_*_head_scores.npz")):
        z = np.load(f, allow_pickle=True)
        S = z["scores"]; te = z["te_rows"]
        for t in te:
            t = int(t)
            base = np.where(MEM[t] & CL[t])[0]
            if base.size < 5:
                continue
            comp = np.zeros(base.size); nk = 0
            for k in range(S.shape[2]):
                col = S[t, base, k].astype(np.float64)
                if np.isfinite(col).all() and col.std() > 1e-12:
                    comp += (col - col.mean()) / col.std(); nk += 1
            if nk:
                out[t, base] = comp / nk
                n_rows += 1
    return out, n_rows


for hz, tags in ARMS.items():
    CL = P[CLKEY[hz]]
    acc = np.zeros((T, N)); cnt = np.zeros((T, N))
    for tag in tags:
        c, nr = composite(tag, CL)
        m = np.isfinite(c)
        acc[m] += c[m]; cnt[m] += 1
        print(f"  {tag}: OOS 行 {nr}  有限格 {m.mean():.4f}", flush=True)
    ens = np.where(cnt > 0, acc / np.maximum(cnt, 1), np.nan)
    # 逐 ts 再 z 一次, 让两个视界的分数同尺(引擎侧还会 z, 这里只是去掉种子数差异)
    for t in np.where(np.isfinite(ens).any(1))[0]:
        b = np.where(np.isfinite(ens[t]))[0]
        if b.size >= 5 and ens[t, b].std() > 1e-12:
            ens[t, b] = (ens[t, b] - ens[t, b].mean()) / ens[t, b].std()
    key = "king_pred"
    outp = f"/workspace/harness_{hz}_pred_panel.npz"
    np.savez_compressed(outp, **{key: ens.astype(np.float32)}, ts=ts,
                        symbols=P["symbols"], n_seeds=len(tags), horizon=int(hz[1:]),
                        recipe="build_s2_pred_panel: per-ts z-mean of 6 heads over member&CL, own test-fold only",
                        arms=np.array(tags, dtype=object))
    print(f"[{hz}] 种子 {len(tags)}  有限格 {np.isfinite(ens).mean():.4f}  -> {outp}", flush=True)

print("ASSEMBLE_DONE")
