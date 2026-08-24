"""L4 事件研究 @jpline。预注册 PREREG_L4_event_overlay_2026-08-24(SHA 058d7872, commit 6785ff5)先于本数字。
触发: 已持仓名 z·sign(w) ≤ −1.5 且落逆向侧末十分位; 动作: 减50%+等额配对对侧最逆向; 成本 taker 7bps×2(全往返)。
Δ/事件 = 避免的锚内损失 − 成本(bps of gross-2 NAV)。SEED 环境变量选 L3 种子。"""
import os, sys, json, time, math
import numpy as np
HERE = "/mnt/storage/private/work_hsy/f8_2026-08-22"; sys.path.insert(0, HERE)
import f3_zoo_nonfunding_leg as f3
SEED = int(os.environ.get("SEED", "42"))
T0 = time.time()
def log(*a): print(f"[{time.time()-T0:6.1f}s]", *a, flush=True)
f3.load_all()
ch = f3.run_chain_n(("king", "rev24", "fund"), tag="C3r_l4")
W = ch["W"]; ch_ts = np.asarray(ch["ts"], np.int64)
Z5 = np.load(f"{HERE}/data/f12_l3.npz", allow_pickle=True)
ts5 = Z5["ts5"].astype(np.int64); R5 = np.nan_to_num(Z5["X_kl"][:, :, 0].astype(np.float32))
amap = Z5["amap"].astype(np.int64); scol60 = Z5["scol60"].astype(np.int64)
P = np.load(f"{HERE}/preds/f12_p30_s{SEED}.npz", allow_pickle=True)
P30 = P["P30"].astype(np.float32); ts30 = P["ts30"].astype(np.int64)
DLW_TS = np.load(f"{HERE}/../dlw_2026-08-22/data/dlw_targets.npz", allow_pickle=True)["E_ts"].astype(np.int64)
chpos = {int(t): i for i, t in enumerate(ch_ts)}
a2ch = np.array([chpos.get(int(t), -1) for t in DLW_TS])
T30 = min(len(ts30), P30.shape[0])
CUM = np.cumsum(np.vstack([np.zeros((1, R5.shape[1]), np.float32), R5]), 0)   # CUM[k]=sum r5[0..k-1]
COST = 7e-4 * 2
events = []
trig_per_anchor = {}
cur_a = -1; fired = set()
for t in range(T30 - 1):
    t5 = t * 6
    if t5 + 1 >= len(ts5):
        break
    a = amap[t5]
    if a < 0 or a2ch[a] < 0:
        continue
    if a != cur_a:
        cur_a = a; fired = set()
    j = a2ch[a]
    a_next = t5
    while a_next < len(ts5) and amap[a_next] == a:
        a_next += 1
    if a_next - t5 < 2:
        continue
    w = W[j][scol60]                                   # 59 名持仓(gross-2 单位)
    z_raw = P30[t, :, 1]
    ok = np.isfinite(z_raw) & (np.abs(w) > 1e-4)
    okz = np.isfinite(z_raw)
    if okz.sum() < 30 or not ok.any():
        continue
    mu, sd = np.nanmean(z_raw[okz]), np.nanstd(z_raw[okz]) + 1e-9
    z = (z_raw - mu) / sd
    lo, hi = np.nanquantile(z[okz], 0.1), np.nanquantile(z[okz], 0.9)
    adverse = ok & (z * np.sign(w) <= -1.5) & (((w > 0) & (z <= lo)) | ((w < 0) & (z >= hi)))
    cand = [i for i in np.where(adverse)[0] if i not in fired]
    if not cand:
        continue
    for i in cand[:3]:
        opp = ok & (np.sign(w) == -np.sign(w[i]))
        if not opp.any():
            continue
        sc_opp = z * np.sign(w)
        jj = int(np.where(opp)[0][np.argmin(sc_opp[opp])])
        trim_i = 0.5 * abs(w[i]); trim_j = min(0.5 * abs(w[jj]), trim_i); trim_i = trim_j
        if trim_i < 1e-5:
            continue
        r_i = float(CUM[a_next] [i] - CUM[t5 + 1][i])   # 触发后→锚末
        r_j = float(CUM[a_next][jj] - CUM[t5 + 1][jj])
        avoided = trim_i * (-np.sign(w[i])) * r_i + trim_j * (-np.sign(w[jj])) * r_j
        cost = COST * (trim_i + trim_j)
        events.append({"t": int(ts5[t5]), "a": int(a), "d_bps": float((avoided - cost) * 1e4),
                       "avoid_bps": float(avoided * 1e4), "cost_bps": float(cost * 1e4),
                       "yr": time.gmtime(int(ts5[t5])).tm_year})
        fired.add(i); fired.add(jj)
        trig_per_anchor[a] = trig_per_anchor.get(a, 0) + 1
log(f"events {len(events)} anchors_with_trigger {len(trig_per_anchor)}")
d = np.array([e["d_bps"] for e in events]); yrs = np.array([e["yr"] for e in events]); anc = np.array([e["a"] for e in events])
rng = np.random.default_rng(7); ua = np.unique(anc); bs = []
for _ in range(2000):
    pick = rng.choice(ua, len(ua))
    sel = np.concatenate([d[anc == a_] for a_ in pick]) if len(pick) else d
    bs.append(sel.mean())
ci = [float(np.quantile(bs, 0.025)), float(np.quantile(bs, 0.975))]
byyr = {int(y): {"n": int((yrs == y).sum()), "mean": round(float(d[yrs == y].mean()), 3)} for y in sorted(set(yrs.tolist()))}
mx = max(trig_per_anchor.values()) if trig_per_anchor else 0
rep = {"seed": SEED, "prereg_sha": "058d7872", "n_events": len(events), "d_mean_bps": round(float(d.mean()), 3),
       "d_CI95": [round(c, 3) for c in ci], "avoid_mean": round(float(np.mean([e["avoid_bps"] for e in events])), 3),
       "cost_mean": round(float(np.mean([e["cost_bps"] for e in events])), 3), "by_year": byyr,
       "triggers_per_anchor_mean": round(len(events) / max(len(trig_per_anchor), 1), 2), "max_per_anchor": mx,
       "anchors_frac_with_trigger": round(len(trig_per_anchor) / 7900, 3),
       "gate": {"ci_gt0": ci[0] > 0, "years_3of": sum(v["mean"] > 0 for v in byyr.values()), "le3": mx <= 3}}
json.dump(rep, open(f"{HERE}/results/f13_l4_s{SEED}.json", "w"), indent=1, default=float)
log("L4_DONE", json.dumps(rep, ensure_ascii=False)[:400])
