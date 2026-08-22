"""§31 set-transformer 截面组织臂 @jpline 3090(判据冻结先于跑):
每锚成员集作 token 集合(78 慢特征/币), 2 层 MHA(d64/4头), 目标=锚内秩, 折=按年扩张, 双种子.
判据: vs LGBM78 平台基线(0.0530/0.0550/0.0545) 三折平均 Δ≥+0.003 双种子全过, 否则 DL 截面组织轴关闭.
env: FEA_IN META_IN OUT_JSON
"""
import json, time, os
import numpy as np
import torch
import torch.nn as nn
from scipy.stats import rankdata, spearmanr

dev = "cuda" if torch.cuda.is_available() else "cpu"
FEA = np.load(os.environ["FEA_IN"], mmap_mode="r")
MT = np.load(os.environ["META_IN"], allow_pickle=True)
E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; y4 = MT["y4"]
names = [str(n) for n in MT["names"]]
yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts])
nA = len(E_ts)
keep = [k for k, nm in enumerate(names) if not (nm.startswith("ret5_sum_48") or nm.startswith("ret5_sum_288"))]
NF = len(keep)
print(f"锚 {nA} 特征 {NF} dev {dev}", flush=True)
def sp(a, b):
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 30: return np.nan
    r = spearmanr(a[ok], b[ok]); return r.correlation if hasattr(r, "correlation") else r[0]
# 逐锚样本(变长集合): 存 (X[n_i,NF], y_rank[n_i])
ANCH = []
for i in range(nA):
    m = members[i]
    yv = y4[i, m]; ok = np.isfinite(yv)
    if ok.sum() < 50: continue
    rr = (rankdata(yv[ok]) / max(ok.sum() - 1, 1) - 0.5).astype(np.float32)
    X = np.asarray(FEA[i, m[ok]][:, keep], dtype=np.float32)
    X = np.clip(np.nan_to_num(X, nan=0), -1e4, 1e4)
    ANCH.append((i, X, rr, yv[ok]))
print(f"有效锚 {len(ANCH)}", flush=True)

class SetBlock(nn.Module):
    def __init__(self, d, h):
        super().__init__()
        self.att = nn.MultiheadAttention(d, h, batch_first=True)
        self.n1 = nn.LayerNorm(d); self.n2 = nn.LayerNorm(d)
        self.ff = nn.Sequential(nn.Linear(d, d * 2), nn.GELU(), nn.Linear(d * 2, d))
    def forward(self, x):
        a, _ = self.att(x, x, x)
        x = self.n1(x + a)
        return self.n2(x + self.ff(x))

class SetModel(nn.Module):
    def __init__(self, nf, d=64):
        super().__init__()
        self.inp = nn.Sequential(nn.Linear(nf, d), nn.GELU())
        self.b1 = SetBlock(d, 4); self.b2 = SetBlock(d, 4)
        self.head = nn.Linear(d, 1)
    def forward(self, x):  # x: (1, n, nf)
        z = self.inp(x)
        z = self.b2(self.b1(z))
        return self.head(z).squeeze(-1)  # (1, n)

def run_fold(train_idx, test_idx, seed):
    torch.manual_seed(seed); np.random.seed(seed)
    model = SetModel(NF).to(dev)
    opt = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
    # 逐锚特征标准化统计(训练集全局)
    mu = np.zeros(NF, np.float64); sq = np.zeros(NF, np.float64); cnt = 0
    for j in train_idx:
        _, X, _, _ = ANCH[j]
        mu += X.sum(0); sq += (X.astype(np.float64) ** 2).sum(0); cnt += len(X)
    mu /= cnt; sd = np.sqrt(np.maximum(sq / cnt - mu ** 2, 1e-12))
    mu32, sd32 = mu.astype(np.float32), sd.astype(np.float32)
    for ep in range(3):
        order = np.random.permutation(train_idx)
        tot = 0.0
        for j in order:
            _, X, rr, _ = ANCH[j]
            xb = torch.from_numpy(np.clip((X - mu32) / sd32, -8, 8)).unsqueeze(0).to(dev)
            yb = torch.from_numpy(rr).unsqueeze(0).to(dev)
            pred = model(xb)
            loss = ((pred - yb) ** 2).mean()
            opt.zero_grad(); loss.backward(); opt.step()
            tot += float(loss)
        print(f"    seed{seed} ep{ep} loss {tot/len(order):.5f}", flush=True)
    model.eval()
    ics = []
    with torch.no_grad():
        for j in test_idx:
            _, X, _, yraw = ANCH[j]
            xb = torch.from_numpy(np.clip((X - mu32) / sd32, -8, 8)).unsqueeze(0).to(dev)
            pv = model(xb).squeeze(0).cpu().numpy()
            ics.append(sp(pv, yraw))
    return float(np.nanmean(ics))

ayrs = np.array([yrs[a[0]] for a in ANCH])
BASE = {"2024": 0.0530, "2025": 0.0550, "2026": 0.0545}
res = {"base_lgbm78": BASE, "seeds": []}
for seed in (42, 2027):
    ic_by = {}
    for YV in (2024, 2025, 2026):
        tr = np.where(ayrs < YV)[0]; te = np.where(ayrs == YV)[0]
        if len(te) == 0: continue
        ic_by[str(YV)] = round(run_fold(tr, te, seed), 4)
        print(f"  [seed{seed} {YV}] IC {ic_by[str(YV)]:+.4f}", flush=True)
    d = {y: round(ic_by[y] - BASE[y], 4) for y in ic_by}
    avg = round(float(np.mean(list(d.values()))), 4)
    res["seeds"].append({"seed": seed, "ic": ic_by, "delta": d, "avg_delta": avg})
    print(f"[seed{seed}] Δavg {avg:+.4f}", flush=True)
passes = [s["avg_delta"] >= 0.003 for s in res["seeds"]]
res["VERDICT"] = "UPGRADE_TO_BOOK_LEVEL" if all(passes) else "SET_ORG_AXIS_CLOSED"
print(f"VERDICT {res['VERDICT']}", flush=True)
json.dump(res, open(os.environ.get("OUT_JSON", "settrans_jp.json"), "w"), indent=1)
print("SETTRANS_DONE", flush=True)
