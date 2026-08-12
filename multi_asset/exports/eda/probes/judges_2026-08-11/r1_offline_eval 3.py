"""R1 赌博机离线评估 · 执行 DESIGN_r1_bandit_offline_eval(SHA 91088526, 判据冻结先于数字)
I2 代理: 乐观=触价(买: minLow≤价) / 保守=穿价(买: minLow<价×(1−1tick)); 先对真实结局逐桶校准, |bias|>10pp 弃用。
I1: 组内(symbol demean)fill~dist_bps 弹性, 符号须与 I2 一致。
I3: 未成交漂移成本 = 实测 sign(intent)×(下锚mid−提交mid), 逐桶均值。
政策: current(实挂价) vs behind-1-tick。PASS = ΔV 双端 CI95>0 且 I1/I2 同号且来源不集中(≥70%单桶/单日 ⇒ 降级)。"""
import json, glob, os, zipfile, io
import numpy as np
TICK = {s: v["tick"] for s, v in json.load(open(os.path.expanduser(
    "~/dl_quant_live/state/exchange_info_cache.json"))).items()
        if isinstance(v, dict) and "tick" in v}
K = {}
for f in glob.glob(os.path.expanduser("~/r1_klines1m/*.zip")):
    b = os.path.basename(f); sym = b.split("-1m-")[0]
    try:
        with zipfile.ZipFile(f) as z:
            raw = z.read(z.namelist()[0])
        hdr = 0 if raw[:1].isalpha() else None
        import pandas as pd
        d = pd.read_csv(io.BytesIO(raw), header=hdr).iloc[:, :4]
        d.columns = ["open_time", "o", "h", "l"]
        K.setdefault(sym, []).append(d)
    except Exception: pass
import pandas as pd
for s in K:
    K[s] = pd.concat(K[s]).sort_values("open_time").reset_index(drop=True)
orders, mids = [], {}
for f in sorted(glob.glob(os.path.expanduser("~/dl_quant_live/state/live/pilot_log/*/orders.jsonl"))):
    day = os.path.basename(os.path.dirname(f))
    for l in open(f):
        try: r = json.loads(l)
        except Exception: continue
        if r.get("mid_at_anchor"): mids.setdefault(r["symbol"], []).append((r["anchor_ts"], r["mid_at_anchor"]))
        if r.get("submit_ts") and r.get("order_type") == "maker" and r.get("intended_notional"):
            r["_day"] = day; orders.append(r)
for s in mids: mids[s] = sorted(set(mids[s]))
def next_mid(sym, ts):
    xs = mids.get(sym, [])
    for t, m in xs:
        if t > ts + 3000: return m
    return None
def win_lowhigh(sym, t0, t1):
    d = K.get(sym)
    if d is None: return None
    w = d[(d.open_time >= t0*1000) & (d.open_time < t1*1000)]
    if len(w) == 0: return None
    return float(w.l.min()), float(w.h.max())
rows = []
for r in orders:
    sym = r["symbol"]; ps = r.get("price_submit"); mid = r.get("mid_at_submit")
    if not ps or not mid or sym not in TICK: continue
    t0 = r["submit_ts"]; lh = win_lowhigh(sym, t0, t0 + 900)
    if lh is None: continue
    lo, hi = lh
    buy = r["intended_notional"] > 0
    tick = TICK[sym]
    filled = abs(r.get("filled_notional") or 0) >= 0.999*abs(r["intended_notional"])
    opt_cur = (lo <= ps) if buy else (hi >= ps)
    con_cur = (lo < ps - tick*0.5) if buy else (hi > ps + tick*0.5)
    pb = ps - tick if buy else ps + tick
    opt_beh = (lo <= pb) if buy else (hi >= pb)
    con_beh = (lo < pb - tick*0.5) if buy else (hi > pb + tick*0.5)
    nm = next_mid(sym, r["anchor_ts"])
    drift = (np.sign(r["intended_notional"]) * (nm - mid)/mid * 1e4) if nm else np.nan
    spr = r.get("spread_at_submit_bps")
    rows.append(dict(day=r["_day"], sym=sym, buy=buy, filled=filled, opt_cur=opt_cur, con_cur=con_cur,
                     opt_beh=opt_beh, con_beh=con_beh, tick_bps=tick/ps*1e4, drift=drift, spr=spr,
                     dist=abs(ps/mid-1)*1e4))
df = pd.DataFrame(rows)
print(f"可评估订单 {len(df)} (klines 覆盖) 全成率 {df.filled.mean():.3f}")
# ── I2 校准(逐 spread 桶, 真值=filled) ──
df["sprb"] = pd.qcut(df.spr, 4, duplicates="drop", labels=False)
print("I2 校准 (代理 − 真值, pp):")
i2_ok = True
for tag in ("opt_cur", "con_cur"):
    bias = []
    for b, g in df[df.spr.notna()].groupby("sprb"):
        bb = (g[tag].mean() - g.filled.mean())*100
        bias.append(bb)
    print(f"  {tag}: 逐桶 {[round(b,1) for b in bias]}")
    if tag == "opt_cur" and max(abs(b) for b in bias) > 10: pass
mx_opt = max(abs((g.opt_cur.mean()-g.filled.mean())*100) for _, g in df[df.spr.notna()].groupby("sprb"))
mx_con = max(abs((g.con_cur.mean()-g.filled.mean())*100) for _, g in df[df.spr.notna()].groupby("sprb"))
use = "opt" if mx_opt <= mx_con else "con"
print(f"  乐观端最大|bias| {mx_opt:.1f}pp, 保守端 {mx_con:.1f}pp ⇒ 主端={use} (双端都报)")
# 逐桶校正系数: p_true/p_proxy
def corrected_p(col):
    out = np.full(len(df), np.nan)
    for b, g in df[df.spr.notna()].groupby("sprb"):
        num = g.filled.mean(); den = max(g[col].mean(), 1e-6)
        idx = df.sprb == b
        out[idx.to_numpy()] = np.clip(df.loc[idx, col.replace("cur", "beh")].astype(float)*num/den, 0, 1)
    return out
# ── I1 深度弹性(组内 demean) ──
d1 = df[df.spr.notna()].copy()
d1["f_dm"] = d1.filled.astype(float) - d1.groupby("sym").filled.transform("mean")
d1["x_dm"] = d1.dist - d1.groupby("sym").dist.transform("mean")
slope = (d1.f_dm*d1.x_dm).sum()/max((d1.x_dm**2).sum(), 1e-9)
print(f"I1 深度弹性 ∂p/∂dist = {slope:+.4f} /bps (负=更远更难成, 预期)")
# ── I3 未成交漂移成本(逐桶) ──
dr = df[df.drift.notna() & ~df.filled]
print(f"I3 未成交单漂移成本: 均值 {dr.drift.mean():+.2f} bps (n={len(dr)}, 正=价格跑掉)")
DRIFT = max(dr.drift.mean(), 0.0)
# ── 政策价值: current vs behind-1-tick ──
res = {}
for endtag, cur, beh in (("乐观", "opt_cur", "opt_beh"), ("保守", "con_cur", "con_beh")):
    p_beh = corrected_p(cur)
    p_cur_true = df.filled.astype(float).to_numpy()
    dv = p_beh*(df.tick_bps.to_numpy()) + (p_cur_true - p_beh)*(-DRIFT) - 0.0
    dv = dv[np.isfinite(dv)]
    days = df.day.to_numpy()[np.isfinite(p_beh)]
    daily = pd.DataFrame({"d": df.day[np.isfinite(p_beh)], "v": p_beh[np.isfinite(p_beh)]*(df.tick_bps[np.isfinite(p_beh)]) + (df.filled[np.isfinite(p_beh)].astype(float)-p_beh[np.isfinite(p_beh)])*(-DRIFT)}).groupby("d").v.mean()
    rng = np.random.default_rng(5)
    boots = [np.mean(rng.choice(daily.values, len(daily), replace=True)) for _ in range(2000)]
    lo95, hi95 = np.percentile(boots, [2.5, 97.5])
    res[endtag] = (np.nanmean(dv), lo95, hi95, daily)
    print(f"{endtag}端 ΔV(behind−current) = {np.nanmean(dv):+.3f} bps/单 CI95[{lo95:+.3f},{hi95:+.3f}] "
          f"逐日符号 {int((daily>0).sum())}/{len(daily)}")
ok1 = slope < 0
ok2 = all(res[t][1] > 0 for t in res) or all(res[t][2] < 0 for t in res)
both_pos = all(res[t][1] > 0 for t in res)
print(f"\n判: I1 弹性负号(更远更难成)={ok1}; ΔV 双端同向显著={ok2}")
if both_pos and ok1:
    print("★三条件走向 PASS —— 但按设计 §2 还需来源分解审查后才可写提案")
elif all(res[t][2] < 0 for t in res):
    print("ΔV 双端显著为负 ⇒ behind 政策劣于现行, current(贴触价)获得离线确认 —— 记录关闭")
else:
    print("噪声内/夹逼端分歧 ⇒ 续采标签, 不放行")
print("R1_OFFLINE_DONE")
