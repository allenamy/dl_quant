"""S-1 关卡1 判官 — 忠实改编 n6_horizon_match 装置(引擎回放/EMA补丁/单腿书 逐字继承)。
判据(冻结, PREREG_horizon24 §4 + §部署前置①): C(y24_s1337)@各自最优a vs ctrl(y4_s42_pod)@各自最优a,
Δ慢书净夏普@3.63 ≥ +0.15(采纳线) 且 逐年同向 ≥3/5 且 @5.8 不反号。
原判决(种子42): Δ+0.853 @3.63 / +0.823 @5.8, 5/5 年。本关 = 第二种子复现(y24 种子噪声 7× 警告)。
复合口径 = 6 头逐 ts z-rank 后平均(w4_compare 同式), 折内只用 te_rows(严格 OOS)。"""
import sys, glob, json
MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA); sys.path.insert(0, MA + "/engine/live")
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
import numpy as np
import torch; torch.backends.mkldnn.enabled = False
from engine import replay_fullhist as RF
from engine import signal_chain as SC
from scipy.stats import rankdata

G1 = "/mnt/storage/private/work_hsy/probe_artifacts/gate1"
KREF = "/mnt/storage/private/work_hsy/probe_artifacts/king_pred_newgen.npz"
S2REF = "/mnt/storage/private/work_hsy/probe_artifacts/s2_pred_newgen.npz"
ARMS = {"C_y24_s1337": "rb32_lam0_yr24_s1337", "ctrl_y4_s42": "rb32_lam0_yr4_s42_pod"}
SPEEDS = [0.1, 0.03, 0.01]; COSTS = [0.001, 3.63, 5.8]

kref = np.load(KREF, allow_pickle=True)
NROW, NCOL = kref["king_pred"].shape

def zr_row(v):
    o = np.full_like(v, np.nan, np.float64); m = np.isfinite(v)
    if m.sum() < 20: return o
    r = rankdata(v[m])
    o[m] = (r - r.mean()) / (r.std() + 1e-12); return o

stitched = {}; cover = None
for name, tag in ARMS.items():
    acc = np.full((NROW, NCOL), np.nan, np.float64); nfill = 0
    for f in sorted(glob.glob(f"{G1}/{tag}/fold_*_head_scores.npz")):
        d = np.load(f); sc, rows = d["scores"], d["te_rows"]
        keep = rows[rows < NROW]
        comp = np.full((len(keep), NCOL), np.nan)
        for i, rr in enumerate(keep):
            hz = np.stack([zr_row(sc[rr, :, h]) for h in range(sc.shape[2])])
            comp[i] = np.nanmean(hz, 0)
        acc[keep] = comp; nfill += len(keep)
    fin = np.isfinite(acc).any(1)
    stitched[name] = acc
    print(f"[{name}] 填入 {nfill} 行, 有预测 {int(fin.sum())}", flush=True)
    if cover is None: cover = fin
    assert np.array_equal(fin, cover), "两臂覆盖不同 ⇒ 对照失效"
print("[对照] 覆盖逐位相同 ✓", flush=True)
for name, arr in stitched.items():
    np.savez(f"/tmp/g1_{name}.npz", king_pred=arr.astype(np.float32), ts=kref["ts"])
z = np.load(S2REF, allow_pickle=True)
np.savez("/tmp/g1_s2zero.npz", s2_pred=np.zeros((NROW, NCOL), np.float32), ts=z["ts"])

_ORIG = SC.SignalChain.shape_position; _ORIG_LP = SC.SignalChain.leg_positions
NMAX = 200; _ST = {"a": 1.0, "idx": None, "prev": np.zeros(NMAX), "have": False}
def patched_lp(self, t):
    o, m = _ORIG_LP(self, t); _ST["idx"] = m; return o, m
def patched(self, combo):
    base = _ORIG(self, combo); a = _ST["a"]
    if a >= 1.0: return base
    m = _ST["idx"]
    if m is None or len(base) != len(m): return base
    prev = _ST["prev"][m]; out = base
    if _ST["have"]:
        out = (1.0 - a) * prev + a * base
        out = out - out.mean()
        g0, g1 = np.abs(base).sum(), np.abs(out).sum()
        out = out * g0 / g1 if (g1 > 1e-12 and g0 > 0) else base
    _ST["prev"][:] = 0.0; _ST["prev"][m] = out; _ST["have"] = True
    return out
SC.SignalChain.shape_position = patched; SC.SignalChain.leg_positions = patched_lp
W = {"king": 1.0, "s2": 0.0, "funding": 0.0, "size": 0.0}

def run(kpath, a, c):
    _ST.update(a=a, prev=np.zeros(NMAX), have=False)
    RF._SRC, RF._SRC_KEY = None, None; RF.COST_BPS = c
    o = RF.run_replay(funding_mode="rank", use_c5=True, shaping="cap",
                      king=kpath, s2="/tmp/g1_s2zero.npz", weights=dict(W), verbose=False)
    return {"sh": float(o["avg_net_of_cost_sharpe"]),
            "per_year": {int(y): float(o["per_year"][y]["net_of_cost_sharpe"]) for y in o["per_year"]}}

res = {}
for name in ARMS:
    for a in SPEEDS:
        r = {c: run(f"/tmp/g1_{name}.npz", a, c) for c in COSTS}
        res[f"{name}_a{a}"] = {"gross": r[0.001]["sh"], "sh363": r[3.63]["sh"], "sh58": r[5.8]["sh"],
                               "py363": r[3.63]["per_year"]}
        print(f"{name} a={a}: 毛 {r[0.001]['sh']:+.3f} 净@3.63 {r[3.63]['sh']:+.3f} "
              f"净@5.8 {r[5.8]['sh']:+.3f}", flush=True)

bestC = max((res[f"C_y24_s1337_a{a}"]["sh363"], a) for a in SPEEDS)
bestA = max((res[f"ctrl_y4_s42_a{a}"]["sh363"], a) for a in SPEEDS)
d363 = bestC[0] - bestA[0]
d58 = res[f"C_y24_s1337_a{bestC[1]}"]["sh58"] - res[f"ctrl_y4_s42_a{bestA[1]}"]["sh58"]
pyC = res[f"C_y24_s1337_a{bestC[1]}"]["py363"]; pyA = res[f"ctrl_y4_s42_a{bestA[1]}"]["py363"]
yrs = sum(1 for y in pyC if (pyC[y] - pyA.get(y, 0)) > 0)
verdict = "PASS" if (d363 >= 0.15 and d58 > 0 and yrs >= 3) else "FAIL"
print(f"\n★ 关卡1: C@a{bestC[1]} {bestC[0]:+.3f} vs ctrl@a{bestA[1]} {bestA[0]:+.3f} "
      f"⇒ Δ@3.63 {d363:+.3f} (线+0.15) | Δ@5.8 {d58:+.3f} | 逐年同向 {yrs}/5 ⇒ {verdict}", flush=True)
print(f"  (原判决种子42: Δ+0.853/+0.823, 5/5 —— 本种子的复现读数如上)")
res["gate1"] = {"d363": round(d363, 3), "d58": round(d58, 3), "yrs": yrs, "verdict": verdict,
                "bestC_a": bestC[1], "bestA_a": bestA[1]}
json.dump(res, open(f"{G1}/gate1_verdict.json", "w"), indent=1)
print("GATE1_JUDGE_DONE")
