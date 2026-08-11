"""y24 六种子统一判官 — 归因终裁: 同一装置上的完整种子分布。
C 满折: wideA_h24_C(原+0.853的臂) / wideA_h24_C_s2 / rb32_lam0_yr24_s1337(pod新训)
C 半折(3/5): h24_C_s3/s4/s5 — 限其覆盖跨度, 对照同掩
ctrl: wideA_lamorth0_5yr_corrfund_v1(时代主对照) + rb32_lam0_yr4_s42_pod(新训对照)
装置 = gate1_judge v3 原样(ffill-24h + 网格掩齐 + 慢书 a∈{.1,.03,.01} 各取优, 成本{3.63,5.8})。
判读: Δ(C@bestA − ctrl@bestA)@3.63 的种子分布 vs 采纳线 +0.15。"""
import sys, glob, json
MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA); sys.path.insert(0, MA + "/engine/live")
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
import numpy as np
import torch; torch.backends.mkldnn.enabled = False
from engine import replay_fullhist as RF
from engine import signal_chain as SC
from scipy.stats import rankdata

TR = MA + "/exports/train"
G1 = "/mnt/storage/private/work_hsy/probe_artifacts/gate1"
KREF = "/mnt/storage/private/work_hsy/probe_artifacts/king_pred_newgen.npz"
S2REF = "/mnt/storage/private/work_hsy/probe_artifacts/s2_pred_newgen.npz"
C_FULL = {"C_orig": f"{TR}/wideA_h24_C", "C_s2": f"{TR}/wideA_h24_C_s2",
          "C_1337": f"{G1}/rb32_lam0_yr24_s1337"}
C_PART = {"C_s3": f"{TR}/h24_C_s3", "C_s4": f"{TR}/h24_C_s4", "C_s5": f"{TR}/h24_C_s5"}
CTRLS = {"ctrl_era": f"{TR}/wideA_lamorth0_5yr_corrfund_v1", "ctrl_pod": f"{G1}/rb32_lam0_yr4_s42_pod"}
SPEEDS = [0.1, 0.03, 0.01]; COSTS = [3.63, 5.8]

kref = np.load(KREF, allow_pickle=True)
NROW, NCOL = kref["king_pred"].shape

def zr_row(v):
    o = np.full_like(v, np.nan, np.float64); m = np.isfinite(v)
    if m.sum() < 20: return o
    r = rankdata(v[m]); o[m] = (r - r.mean()) / (r.std() + 1e-12); return o

def stitch(path, ffill24):
    acc = np.full((NROW, NCOL), np.nan, np.float64)
    for f in sorted(glob.glob(f"{path}/fold_*_head_scores.npz")):
        d = np.load(f); sc, rows = d["scores"], d["te_rows"]
        keep = rows[rows < NROW]
        comp = np.full((len(keep), NCOL), np.nan)
        for i, rr in enumerate(keep):
            hz = np.stack([zr_row(sc[rr, :, h]) for h in range(sc.shape[2])])
            with np.errstate(all="ignore"):
                comp[i] = np.nanmean(hz, 0)
        acc[keep] = comp
    if ffill24:
        last = None; age = 99
        for i in range(NROW):
            if np.isfinite(acc[i]).any(): last = acc[i].copy(); age = 0
            elif last is not None and age < 23: acc[i] = last; age += 1
    return acc

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
z = np.load(S2REF, allow_pickle=True)
np.savez("/tmp/ms_s2zero.npz", s2_pred=np.zeros((NROW, NCOL), np.float32), ts=z["ts"])

def run(kpath, a, c):
    _ST.update(a=a, prev=np.zeros(NMAX), have=False)
    RF._SRC, RF._SRC_KEY = None, None; RF.COST_BPS = c
    o = RF.run_replay(funding_mode="rank", use_c5=True, shaping="cap",
                      king=kpath, s2="/tmp/ms_s2zero.npz", weights=dict(W), verbose=False)
    return {"sh": float(o["avg_net_of_cost_sharpe"]),
            "py": {int(y): float(o["per_year"][y]["net_of_cost_sharpe"]) for y in o["per_year"]}}

def judge(arms, note, mask=None):
    print(f"\n===== {note} =====", flush=True)
    panels = {}
    cover = None
    for name, path in arms.items():
        acc = stitch(path, ffill24=name.startswith("C_"))
        if cover is None and name.startswith("ctrl"):
            cover = np.isfinite(acc).any(1)
        panels[name] = acc
    if mask is not None:
        cover = cover & mask
    for name in panels:
        acc = panels[name]
        acc[~cover] = np.nan
        np.savez(f"/tmp/ms_{name}.npz", king_pred=acc.astype(np.float32), ts=kref["ts"])
        print(f"[{name}] 网格行 {int(np.isfinite(acc).any(1).sum())}", flush=True)
    out = {}
    for name in panels:
        best = None
        for a in SPEEDS:
            r363 = run(f"/tmp/ms_{name}.npz", a, 3.63)
            if best is None or r363["sh"] > best[1]["sh"]:
                best = (a, r363)
        r58 = run(f"/tmp/ms_{name}.npz", best[0], 5.8)
        out[name] = {"a": best[0], "sh363": best[1]["sh"], "sh58": r58["sh"], "py": best[1]["py"]}
        print(f"{name}: best a={best[0]} 净@3.63 {best[1]['sh']:+.3f} @5.8 {r58['sh']:+.3f}", flush=True)
    for cn in [k for k in out if k.startswith("ctrl")]:
        for an in [k for k in out if k.startswith("C_")]:
            d = out[an]["sh363"] - out[cn]["sh363"]
            d58 = out[an]["sh58"] - out[cn]["sh58"]
            yrs = sum(1 for y in out[an]["py"] if out[an]["py"][y] - out[cn]["py"].get(y, 0) > 0)
            print(f"Δ({an} − {cn}) @3.63 = {d:+.3f} | @5.8 {d58:+.3f} | 逐年 {yrs}/{len(out[an]['py'])}", flush=True)
    return out

r_full = judge({**CTRLS, **C_FULL}, "满折三种子(全跨度)")

part_cover = np.zeros(NROW, bool)
for f in sorted(glob.glob(f"{C_PART['C_s3']}/fold_*_head_scores.npz")):
    d = np.load(f); rows = d["te_rows"]; keep = rows[rows < NROW]
    lo, hi = keep.min(), min(keep.max() + 24, NROW)
    part_cover[lo:hi] = True
r_part = judge({**CTRLS, **C_PART}, "半折三种子(限 3 折跨度, 对照同掩)", mask=part_cover)
json.dump({"full": {k: {kk: vv for kk, vv in v.items() if kk != 'py'} for k, v in r_full.items()},
           "part": {k: {kk: vv for kk, vv in v.items() if kk != 'py'} for k, v in r_part.items()}},
          open(f"{G1}/multiseed_verdict.json", "w"), indent=1)
print("MULTISEED_DONE")
