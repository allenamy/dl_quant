"""DLW · 82 列弹药(G0 预门用)@jpline(2026-08-22, Session 6737834a-DLW)。
预注册 §P.1(冻结段 SHA256 33f066c9…64577, commit 7acda02)。定义逐字 runpod_scripts/workspace_mirror/pod_fea_wide.py(wide_fea_v1),
唯一改动 = 窗端点对齐为 rows [E−w+1, E+1)(含收盘于 N 的那根 bar; 目标从 E+1 起 ⇒ 零重叠零间隙)+ 早期锚窗起点 clip 0(旧装置对 E−w<0 的负索引回绕未处理)。
列(82, 顺序与 wide_fea_v1 同): for ch in [ret5, range, cpos, log_qv, log_cnt, log_avgsz, tbf] for w in [48, 288, 864, 2016, 8640]:
  (ret5 窗和 / 其余窗均值) 各 {值(clip ±1e4, nan→0), 成员内秩 [−0.5,0.5]}; + vol 5 窗(窗内 ret5 标准差){值, 秩}; + fund_ema, fund_now(面板锚行, nan→0)。
锚/成员 = dlw_targets.npz(唯一真相源)。产物: data/dlw_fea82.npz(X f16 (n_pairs, 82) 长格式 + pair_a/pair_s + names + meta)。
结构断言: max_feature_row == E(偏移 0)。
用法 @jpline: python dlw_features.py
"""
import os, json, time, hashlib
import numpy as np
from scipy.stats import rankdata

ROOT = "/mnt/storage/private/work_hsy"
CACHE = os.environ.get("F171_CACHE", f"{ROOT}/w3lane/kcurve/data/dlnative_5m_wide829_f16.npz")  # F171_ENV
PANEL = f"{ROOT}/w3lane/kcurve/data/wide_panel_4h_v1.npz"
OUT = os.environ.get("F171_OUT", f"{ROOT}/dlw_2026-08-22")  # F171_ENV
CHN = ["ret5", "range", "cpos", "log_qv", "log_cnt", "log_avgsz", "tbf"]
WINS = (48, 288, 864, 2016, 8640)
T0 = time.time()


def log(*a):
    print(f"[{time.time()-T0:7.1f}s]", *a, flush=True)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""):
            h.update(ch)
    return h.hexdigest()


def main():
    TG = np.load(f"{OUT}/data/dlw_targets.npz", allow_pickle=True)
    E = TG["E_row"].astype(np.int64); E_ts = TG["E_ts"].astype(np.int64); MS = TG["members"]; syms = [str(s) for s in TG["symbols"]]
    nA = len(E); NW = len(syms)
    Z = np.load(CACHE, allow_pickle=True)
    CD = Z["data"]; CTS = Z["ts"].astype(np.int64)
    assert [str(s) for s in Z["symbols"]] == syms and [str(c) for c in Z["ch"]] == CHN
    assert np.array_equal(CTS[E], E_ts), "E_row ↔ E_ts 不一致"
    TT = CD.shape[0]
    hi = E + 1                                   # CS 半开区间上界 ⇒ 最后一行 = E(收盘于 N)
    assert int((hi - 1 - E).max()) == 0, "max_feature_row 必须 == E"
    VAL, val_names = [], []
    z1 = np.zeros((1, NW))
    for c, nm in enumerate(CHN):
        x = CD[:, :, c].astype(np.float32); fin = np.isfinite(x)
        CSf = np.concatenate([z1.astype(np.int32), np.cumsum(fin, 0, dtype=np.int32)])
        CSx = np.concatenate([z1, np.cumsum(np.where(fin, x, 0).astype(np.float64), 0)])
        CS2 = np.concatenate([z1, np.cumsum(np.where(fin, x, 0).astype(np.float64) ** 2, 0)]) if c == 0 else None
        for w in WINS:
            lo = np.maximum(hi - w, 0)
            nf = np.maximum(CSf[hi] - CSf[lo], 1)
            if c == 0:
                VAL.append((CSx[hi] - CSx[lo]).astype(np.float32)); val_names.append(f"{nm}_sum_{w}")
            else:
                VAL.append(((CSx[hi] - CSx[lo]) / nf).astype(np.float32)); val_names.append(f"{nm}_mean_{w}")
        if c == 0:
            VOLS = []
            for w in WINS:
                lo = np.maximum(hi - w, 0); nf = np.maximum(CSf[hi] - CSf[lo], 1)
                mm = (CSx[hi] - CSx[lo]) / nf
                VOLS.append(np.sqrt(np.maximum((CS2[hi] - CS2[lo]) / nf - mm ** 2, 0)).astype(np.float32))
        del x, fin, CSf, CSx, CS2
        log(f"channel {nm} done")
    for w, v in zip(WINS, VOLS):
        VAL.append(v); val_names.append(f"vol_{w}")
    del CD
    PW = np.load(PANEL, allow_pickle=True)
    pw_row = {int(t): j for j, t in enumerate(PW["ts"].astype(np.int64))}
    FUND = [PW["f_fund_ema"].astype(np.float32), PW["f_fund_now"].astype(np.float32)]; fund_names = ["fund_ema", "fund_now"]
    NVAL = len(VAL); NF = NVAL * 2 + 2
    names = [n + s for n in val_names for s in ("_v", "_r")] + fund_names
    assert NF == 82 and len(names) == 82, (NF, len(names))
    n_pairs = int(sum(len(m) for m in MS))
    X = np.zeros((n_pairs, NF), np.float16); pair_a = np.zeros(n_pairs, np.int32); pair_s = np.zeros(n_pairs, np.int16)
    pos = 0; n_nofund = 0
    for i in range(nA):
        m = MS[i]; n = len(m); sl = slice(pos, pos + n)
        col = 0
        for v in VAL:
            xv = v[i, m]
            X[sl, col] = np.clip(np.nan_to_num(xv, nan=0.0), -1e4, 1e4); col += 1
            ok = np.isfinite(xv); rr = np.zeros(n, np.float32)
            if ok.sum() >= 10:
                rr[ok] = rankdata(xv[ok]) / max(ok.sum() - 1, 1) - 0.5
            X[sl, col] = rr; col += 1
        j = pw_row.get(int(E_ts[i]))
        if j is None:
            n_nofund += 1
        for fv in FUND:
            X[sl, col] = 0.0 if j is None else np.nan_to_num(fv[j, m], nan=0.0); col += 1
        pair_a[sl] = i; pair_s[sl] = m; pos += n
        if i % 2000 == 0:
            log(f"fea {i}/{nA}")
    assert pos == n_pairs
    meta = dict(n_pairs=n_pairs, n_anchors=int(nA), NF=NF, names=names, feature_row_window="[E-w+1, E] (max_feature_row == E)",
                anchors_without_panel_row=int(n_nofund), cache_sha256=sha(CACHE), panel_sha256=sha(PANEL), targets_sha256=sha(f"{OUT}/data/dlw_targets.npz"),
                self_sha256=sha(os.path.abspath(__file__)))
    np.savez(f"{OUT}/data/dlw_fea82.npz", X=X, pair_a=pair_a, pair_s=pair_s, names=np.array(names), meta_json=json.dumps(meta))
    meta["fea_sha256"] = sha(f"{OUT}/data/dlw_fea82.npz")
    json.dump(meta, open(f"{OUT}/results/dlw_features_report.json", "w"), indent=1)
    log("FEATURES_DONE", X.shape, "no-panel anchors", n_nofund)


if __name__ == "__main__":
    main()
