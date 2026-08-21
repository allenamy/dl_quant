"""W2 · 两书重叠名/对冲抵消核算(只注记, 不建模) + 瘦身序列落盘。
输入(完整 npz, 含权重矩阵; 单副本在 jpline probe_artifacts/ 与本机 scratch, 不入 git):
  w2_live_series.npz  SHA256 92f99f2d2cb297d420cd36fab04744c01b7d1e553ffb104f175de6c69a34cd58
  w2_wide_series.npz  SHA256 e227cd887f77f63f6e1fbb7fd31eedb1927c69dbf8df7a92356a624aebc90503
输出(入 git): results/series/w2_live_series_slim.npz, results/series/w2_wide_series_slim.npz(去掉权重矩阵的逐锚列),
             results/w2_overlap_2026-08-21.json(逐年重叠名/同向/反向/抵消 gross 注记)。
用法: python3 w2_overlap.py <full_npz_dir> <out_dir>
"""
import sys, os, json, time, hashlib, numpy as np
SRC = sys.argv[1]; OUT = sys.argv[2]; os.makedirs(os.path.join(OUT, "series"), exist_ok=True)
def sha(p):
    h = hashlib.sha256(); h.update(open(p, "rb").read()); return h.hexdigest()
LP = os.path.join(SRC, "w2_live_series.npz"); WP = os.path.join(SRC, "w2_wide_series.npz")
print("sha live", sha(LP)); print("sha wide", sha(WP))
L = np.load(LP, allow_pickle=True); Wd = np.load(WP, allow_pickle=True)
# ---- slim copies (no weight matrices) ----
np.savez_compressed(os.path.join(OUT, "series", "w2_live_series_slim.npz"), **{k: L[k] for k in L.files if not k.startswith("W_")})
np.savez_compressed(os.path.join(OUT, "series", "w2_wide_series_slim.npz"), **{k: Wd[k] for k in Wd.files if not k.endswith("_W")})
# ---- overlap ----
lts = L["ts"].astype(np.int64); lsym = [str(s) for s in L["symbols"]]; LW = L["W_S1"]
cols = [str(c) for c in Wd["cols"]]; R = Wd["d30_n2_c42_rec"]; wts = R[:, cols.index("ts")].astype(np.int64); wsym = [str(s) for s in Wd["symbols"]]; WW = Wd["d30_n2_c42_W"]
widx = {s: i for i, s in enumerate(wsym)}; lmap = np.array([widx.get(s, -1) for s in lsym]); mapped = lmap >= 0
wpos = {int(t): j for j, t in enumerate(wts)}
rows = []
for i, t in enumerate(lts):
    j = wpos.get(int(t))
    if j is None: continue
    lw = LW[i].astype(float); ww = WW[j].astype(float)
    gL = np.abs(lw).sum(); gW = np.abs(ww).sum()
    if gL < 1e-9 or gW < 1e-9: continue
    lw_on_w = np.zeros(len(wsym)); lw_on_w[lmap[mapped]] = lw[mapped]
    actL = np.abs(lw_on_w) > 1e-4; actW = np.abs(ww) > 2.5e-4      # wide: above its band (EMA dust excluded)
    both = actL & actW
    same = both & (np.sign(lw_on_w) == np.sign(ww)); opp = both & (np.sign(lw_on_w) != np.sign(ww))
    mn = np.minimum(np.abs(lw_on_w), np.abs(ww))
    c = 0.5 * lw_on_w / gL + 0.5 * ww / gW
    rows.append((int(t), time.gmtime(int(t)).tm_year, int(actL.sum()), int(actW.sum()), int(both.sum()), int(same.sum()), int(opp.sum()),
                 float(np.abs(lw_on_w[both]).sum() / gL), float(np.abs(ww[both]).sum() / gW),
                 float(mn[same].sum() / gL), float(mn[opp].sum() / gL), float(np.abs(c).sum()), float(np.abs(lw[~mapped]).sum() / gL)))
A = np.array(rows)
names = ["ts", "yr", "n_live_active", "n_wide_active", "n_overlap", "n_same_sign", "n_opp_sign", "live_gross_share_in_overlap", "wide_gross_share_in_overlap",
         "same_sign_min_gross_over_liveG", "opp_sign_min_gross_over_liveG", "gross_of_5050_unitblend", "live_gross_unmapped_share"]
out = {"n_common": int(len(A)), "live_syms_mapped": int(mapped.sum()), "live_syms_total": int(len(lsym)), "by_year": {}, "all": {}}
for y in sorted(set(A[:, 1].astype(int).tolist())):
    m = A[:, 1] == y; out["by_year"][int(y)] = {nm: round(float(A[m, k].mean()), 4) for k, nm in enumerate(names) if k >= 2}
out["all"] = {nm: round(float(A[:, k].mean()), 4) for k, nm in enumerate(names) if k >= 2}
out["note"] = ("live_active=|w|>1e-4; wide_active=|w|>2.5e-4(去 EMA 尘埃); overlap=两书同时活跃的名; same/opp=同向/反向; "
               "min_gross=重叠名上 min(|w_L|,|w_W|) 合计占在役 gross; gross_of_5050_unitblend=单位 gross 各半混合后的实际 gross(<1 即抵消); 仅注记不建模")
json.dump(out, open(os.path.join(OUT, "w2_overlap_2026-08-21.json"), "w"), indent=1, ensure_ascii=False)
print(json.dumps(out["all"], ensure_ascii=False)); print("by_year", json.dumps(out["by_year"], ensure_ascii=False))
