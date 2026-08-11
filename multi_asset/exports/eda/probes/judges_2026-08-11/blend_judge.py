"""合成判决: w·z(h24_C) + (1−w)·z(perhead), w ∈ {0.5, 0.7}, 同 dl_only 装置净夏普扫描。
判读先写死: 合成候选值得进部署预注册 ⇔ 净@3.63(最优a) ≥ 2.0 且 @5.8 不低于 1.8
且逐年 5/5 正 —— 即拿到 y24 的 ~90% 净额; 塌陷韧性由本地伴测判定(fresh 近6 ≥ +0.02)。"""
import numpy as np, glob, json
BASE = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports"
P = np.load(f"{BASE}/wide_dl_full_corrfund_causal_0731.npz", allow_pickle=True)
Y4 = P["Y4"]; MEM = P["MEMBER110"]; CL4 = P["CL4"]; TS = P["ts"]


def zr(x):
    m = np.isfinite(x); out = np.full(len(x), np.nan)
    if m.sum() < 3: return out
    r = np.argsort(np.argsort(x[m])).astype(float)
    out[m] = (r - r.mean()) / (r.std() + 1e-12); return out


def arm(tag):
    rows_all, ens_all = [], []
    for f in sorted(glob.glob(f"{BASE}/train/{tag}/fold_*_head_scores.npz")):
        z = np.load(f, allow_pickle=True); S = z["scores"]; rows = z["te_rows"]
        for r in rows:
            mem = MEM[r]; hz = []
            for h in range(S.shape[2]):
                v = np.where(mem, S[r, :, h], np.nan); s = np.nanstd(v)
                hz.append((v - np.nanmean(v)) / s if s > 0 else v * np.nan)
            rows_all.append(int(r)); ens_all.append(np.nanmean(hz, axis=0))
    o = np.argsort(rows_all)
    return np.array(rows_all)[o], np.array(ens_all)[o]


rA, eA = arm("wideA_h24_C")
rB, eB = arm("wideA_perhead_v1")
assert (rA == rB).all()


def book(w):
    w = np.where(np.isfinite(w), w, 0.0); w = w - w.mean()
    s = np.abs(w).sum(); return w / s if s > 1e-12 else w


out = {}
for wgt in (0.5, 0.7):
    ens = [wgt * zr(eA[k]) + (1 - wgt) * zr(eB[k]) for k in range(len(rA))]
    res = {}
    for a in (1.0, 0.3, 0.1, 0.03, 0.01):
        prev = None; state = None; pnl = []; turn = []; yrs = []
        for k, r in enumerate(rA):
            tgt = book(ens[k])
            if a < 1.0:
                state = tgt if state is None else (1 - a) * state + a * tgt
                w = book(state)
            else:
                w = tgt
            y = np.where(MEM[r] & CL4[r] & np.isfinite(Y4[r]), Y4[r], 0.0)
            pnl.append(float(np.dot(w, y)))
            turn.append(0.0 if prev is None else float(np.abs(w - prev).sum()))
            prev = w
            yrs.append(int(str(np.datetime64(int(TS[r]), "ms"))[:4]))
        pnl = np.array(pnl); turn = np.array(turn); rr = {}
        for c in (3.63, 5.8):
            net = pnl - turn * c / 1e4
            per = {yy: round(float(net[np.array(yrs) == yy].mean() /
                                    (net[np.array(yrs) == yy].std() + 1e-12) * np.sqrt(2190)), 2)
                   for yy in sorted(set(yrs)) if (np.array(yrs) == yy).sum() > 100}
            rr[str(c)] = {"net_ann": round(float(net.mean() / (net.std() + 1e-12) * np.sqrt(2190)), 3),
                          "per_year": per}
        rr["turnover_ann"] = round(float(turn.mean() * 2190), 0)
        res[str(a)] = rr
    out[f"blend_{wgt}"] = res
print(json.dumps(out, indent=1))
