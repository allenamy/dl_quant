"""DLW · 判官(从存盘预测出全部读数与门; 与结论同寿命)@jpline(2026-08-22, Session 6737834a-DLW)。
预注册 §P.2/P.4/P.5/P.6(冻结段 SHA256 33f066c9…64577, commit 7acda02)。
输入: data/dlw_targets.npz + preds/dlw_{ARM}_s{SEED}.npy(R82_s0 / L82_s0 / D0_s42 / D1h8_s42 / D1h4_s42 / D1h1_s42 / D1h8_s2027 / D1h8_s3037 / D0_s2027, 有几臂读几臂)
      + (G1) pod_backup_2026-08-21/slow_pred_hist_oos.npy 与 wide_fea_hist_meta.npz(K0 慢 king, 按 E_ts 对齐)。
固定锚集 A = 测试年锚中 核心臂(R82, L82, D0_s42, D1h8_s42 之可得者)全部有限 IC 的锚; 集 B = A ∩ 成员 ≥ 360。
读数: 逐锚 Spearman(pred, YR4s)(主, 残差秩 IC)/ Spearman(pred, y4s)(原始)/ 逐名时序 Pearson / Q4(BTC 7 日波动最坏五分位, A 内分位)/ σŷ/σy / 逐年 / 配对 t / 种子 sd。
门: G0 ΔIC_A(D1h8 − max(R82, L82)) ≥ +0.005 且逐折 Δ>0 ≥ 3/4(4/4 并报; 恰 3/4 ⇒ 条件通过); 归纳偏置增量 D1h8−D0 ≥ +0.005 且 ≥3/4 且 ≥2×种子 sd ⇒ 有增量;
    |Δ| ≤ max(0.002, 种子 sd) ⇒ 无增量; 其余 未分辨。有效性: shuffle null |IC|<2SE; 偏移谱峰@0; σŷ/σy ≥ 0.02。G1 仅 G0 过。
用法 @jpline: python dlw_judge.py  → results/dlw_judge.json + 终端表
"""
import os, sys, json, time, glob, hashlib
import numpy as np
from scipy.stats import rankdata, spearmanr, pearsonr

ROOT = "/mnt/storage/private/work_hsy"; OUT = f"{ROOT}/dlw_2026-08-22"; B = f"{ROOT}/pod_backup_2026-08-21"
YEARS = (2023, 2024, 2025, 2026)
CORE = ["R82_s0", "L82_s0", "D0_s42", "D1h8_s42"]
T0 = time.time()


def log(*a):
    print(f"[{time.time()-T0:6.1f}s]", *a, flush=True)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""):
            h.update(ch)
    return h.hexdigest()


def spear(x, y, nmin=30):
    ok = np.isfinite(x) & np.isfinite(y)
    if ok.sum() < nmin:
        return np.nan
    return spearmanr(x[ok], y[ok]).correlation


def xz(v):
    ok = np.isfinite(v); out = np.full(len(v), np.nan); n = int(ok.sum())
    if n >= 10:
        out[ok] = (rankdata(v[ok]) - (n + 1) / 2) / max(n - 1, 1)
    return out


def nanmean(a):
    a = np.asarray(a, float); return float(np.nanmean(a)) if np.isfinite(a).any() else float("nan")


def paired(d):
    d = np.asarray(d, float); d = d[np.isfinite(d)]
    if len(d) < 3:
        return {"mean": float("nan"), "t": float("nan"), "n": int(len(d))}
    return {"mean": float(d.mean()), "t": float(d.mean() / (d.std(ddof=1) / np.sqrt(len(d)) + 1e-12)), "n": int(len(d))}


def main():
    TG = np.load(f"{OUT}/data/dlw_targets.npz", allow_pickle=True)
    E_ts = TG["E_ts"].astype(np.int64); MS = list(TG["members"]); yrs = TG["yrs"]; YR4s = TG["YR4s"]; y4s = TG["y4s"]; YRZ = TG["YRZ"]
    btcv = TG["btcv"]; qvk = TG["qvk"]; syms = [str(s) for s in TG["symbols"]]
    nA, NW = YR4s.shape; memn = np.array([len(m) for m in MS])
    files = sorted(glob.glob(f"{OUT}/preds/dlw_*.npy"))
    arms = {os.path.basename(f)[4:-4]: np.load(f) for f in files}
    log("arms:", list(arms))
    test = np.isin(yrs, YEARS)
    ICR = {}; ICY = {}; SIG = {}
    for a, P in arms.items():
        icr = np.full(nA, np.nan); icy = np.full(nA, np.nan); sg = np.full(nA, np.nan)
        for i in np.where(test)[0]:
            m = MS[i]; p = P[i, m]
            if np.isfinite(p).sum() < 30:
                continue
            icr[i] = spear(p, YR4s[i, m]); icy[i] = spear(p, y4s[i, m])
            ok = np.isfinite(p) & np.isfinite(YRZ[i, m])
            if ok.sum() >= 30:
                sg[i] = np.std(p[ok]) / (np.std(YRZ[i, m][ok]) + 1e-12)
        ICR[a] = icr; ICY[a] = icy; SIG[a] = sg
    core = [a for a in CORE if a in arms]
    A = test.copy()
    for a in core:
        A &= np.isfinite(ICR[a])
    A_idx = np.where(A)[0]; Bm = A & (memn >= 360)
    log(f"集 A {A.sum()} 锚(核心臂 {core}), 年份 {dict(zip(*np.unique(yrs[A], return_counts=True)))}; 集 B {Bm.sum()}")
    qb = np.quantile(btcv[A], [0.2, 0.4, 0.6, 0.8]); qgrp = np.full(nA, -1); qgrp[A] = np.digitize(btcv[A], qb)   # 4 = Q4 最坏(最高波动)
    out = {"prereg_sha": "33f066c9460587864866e4f31afb72c24ae93c98183fc779c12aa0af70764577", "prereg_commit": "7acda02", "self_sha256": sha(os.path.abspath(__file__)),
           "targets_sha256": sha(f"{OUT}/data/dlw_targets.npz"), "arms_present": list(arms), "core_arms": core,
           "setA": {"n": int(A.sum()), "by_year": {str(y): int((A & (yrs == y)).sum()) for y in YEARS}}, "setB": {"n": int(Bm.sum())},
           "pred_sha256": {a: sha(f"{OUT}/preds/dlw_{a}.npy") for a in arms}, "table": {}, "delta": {}, "seed_sd": {}, "validity": {}, "gates": {}}
    # ---- 主表
    for a in arms:
        r = {"ic_resid_A": nanmean(ICR[a][A]), "ic_raw_A": nanmean(ICY[a][A]), "ic_resid_B": nanmean(ICR[a][Bm]), "ic_raw_B": nanmean(ICY[a][Bm]),
             "ic_resid_by_year": {str(y): nanmean(ICR[a][A & (yrs == y)]) for y in YEARS}, "ic_raw_by_year": {str(y): nanmean(ICY[a][A & (yrs == y)]) for y in YEARS},
             "ic_resid_2325": nanmean(ICR[a][A & (yrs <= 2024)]), "ic_resid_2526": nanmean(ICR[a][A & (yrs >= 2025)]),
             "q_by_quintile": [nanmean(ICR[a][A & (qgrp == g)]) for g in range(5)], "sigma_ratio_median": float(np.nanmedian(SIG[a][A])),
             "n_A_finite": int(np.isfinite(ICR[a][A]).sum())}
        r["q4_over_all"] = r["q_by_quintile"][4] / r["ic_resid_A"] if r["ic_resid_A"] else float("nan")
        # 逐名时序 Pearson(A 内测试锚, ≥200 锚的名)
        P = arms[a]; pc = []
        for n in range(NW):
            ok = A & np.isfinite(P[:, n]) & np.isfinite(YR4s[:, n])
            if ok.sum() >= 200:
                pc.append(pearsonr(P[ok, n], YR4s[ok, n])[0])
        r["per_asset_pearson_mean"] = float(np.mean(pc)) if pc else float("nan"); r["per_asset_n"] = len(pc)
        r["divergence_flag"] = bool(np.sign(r["per_asset_pearson_mean"]) != np.sign(r["ic_resid_A"])) if pc else None
        out["table"][a] = r
    # ---- 成对 Δ
    def delta(a1, a2):
        d = ICR[a1] - ICR[a2]; res = paired(d[A]); res["by_year"] = {str(y): nanmean(d[A & (yrs == y)]) for y in YEARS}
        res["n_pos_years"] = int(sum(v > 0 for v in res["by_year"].values() if np.isfinite(v))); res["n_years"] = int(sum(np.isfinite(v) for v in res["by_year"].values()))
        res["raw_mean"] = nanmean((ICY[a1] - ICY[a2])[A]); res["B_mean"] = nanmean(d[Bm]); return res
    pairs = [("D1h8_s42", "D0_s42"), ("D1h8_s42", "R82_s0"), ("D1h8_s42", "L82_s0"), ("D0_s42", "L82_s0"), ("D0_s42", "R82_s0"), ("L82_s0", "R82_s0"),
             ("D1h4_s42", "D1h8_s42"), ("D1h1_s42", "D1h8_s42"), ("D1h4_s42", "D0_s42"), ("D1h1_s42", "D0_s42"), ("D1h8_s2027", "D0_s2027")]
    for a1, a2 in pairs:
        if a1 in arms and a2 in arms:
            out["delta"][f"{a1}-{a2}"] = delta(a1, a2)
    # ---- 种子 sd
    for fam in ("D1h8", "D0"):
        ks = [a for a in arms if a.startswith(fam + "_s")]
        vals = [out["table"][a]["ic_resid_A"] for a in ks]
        out["seed_sd"][fam] = {"seeds": ks, "ic_A": vals, "sd": float(np.std(vals, ddof=1)) if len(vals) >= 2 else None, "mean": float(np.mean(vals)) if vals else None}
    # ---- 有效性: shuffle null + 偏移谱
    rng = np.random.default_rng(0)
    for a in arms:
        P = arms[a]; nulls = []
        for s in range(3):
            rs = np.random.default_rng(s); v = []
            for y in YEARS:
                ia = np.where(A & (yrs == y) & np.isfinite(ICR[a]))[0]
                if len(ia) < 10:
                    continue
                perm = rs.permutation(ia)
                for i, j in zip(ia, perm):
                    m = MS[i]; v.append(spear(P[i, m], YR4s[j, m]))
            nulls.append(nanmean(v))
        true_ic = ICR[a][A]; se = float(np.nanstd(true_ic) / np.sqrt(np.isfinite(true_ic).sum()))
        spec = {}
        for k in range(-6, 7):
            v = []
            for i in A_idx[::3]:
                j = i + k
                if 0 <= j < nA:
                    m = MS[i]; v.append(spear(P[i, m], YR4s[j, m]))
            spec[str(k)] = nanmean(v)
        peak = max(spec, key=lambda kk: spec[kk] if np.isfinite(spec[kk]) else -9)
        out["validity"][a] = {"shuffle_null_mean": float(np.mean(nulls)), "shuffle_null_per_seed": nulls, "se_true": se, "null_pass": bool(abs(np.mean(nulls)) < 2 * se),
                              "offset_spectrum": spec, "peak_k": int(peak), "peak_pass": int(peak) == 0,
                              "sigma_pass": bool(out["table"][a]["sigma_ratio_median"] >= 0.02)}
    # ---- 门
    g = {}
    if all(a in arms for a in ("R82_s0", "L82_s0", "D1h8_s42")):
        base = "L82_s0" if out["table"]["L82_s0"]["ic_resid_A"] >= out["table"]["R82_s0"]["ic_resid_A"] else "R82_s0"
        d = delta("D1h8_s42", base)
        g["G0"] = {"base_arm": base, "delta_A": d["mean"], "t": d["t"], "by_year": d["by_year"], "n_pos_years": d["n_pos_years"], "n_years": d["n_years"],
                   "pass_delta": d["mean"] >= 0.005, "pass_folds_3of4": d["n_pos_years"] >= 3, "pass_folds_4of4": d["n_pos_years"] == 4}
        g["G0"]["verdict"] = ("PASS" if (g["G0"]["pass_delta"] and g["G0"]["pass_folds_4of4"]) else
                              "CONDITIONAL_PASS_需第5折" if (g["G0"]["pass_delta"] and g["G0"]["pass_folds_3of4"]) else "FAIL")
    if all(a in arms for a in ("D0_s42", "D1h8_s42")):
        d = out["delta"]["D1h8_s42-D0_s42"]; sd = out["seed_sd"]["D1h8"]["sd"]; sd_eff = sd if sd is not None else 0.002
        inc = {"delta_A": d["mean"], "t": d["t"], "n_pos_years": d["n_pos_years"], "seed_sd_D1h8": sd, "seed_sd_used": sd_eff, "provisional_sd": sd is None}
        if d["mean"] >= 0.005 and d["n_pos_years"] >= 3 and d["mean"] >= 2 * sd_eff:
            inc["verdict"] = "有增量"
        elif abs(d["mean"]) <= max(0.002, sd_eff):
            inc["verdict"] = "无增量"
        else:
            inc["verdict"] = "未分辨"
        g["inductive_bias_D1_minus_D0"] = inc
    # ---- G1(仅 G0 过; 也无条件报读数供参考, 标注)
    if "D1h8_s42" in arms and os.path.exists(f"{B}/slow_pred_hist_oos.npy"):
        K0 = np.load(f"{B}/slow_pred_hist_oos.npy"); MT = np.load(f"{B}/wide_fea_hist_meta.npz", allow_pickle=True)
        k_ts = MT["E_ts"].astype(np.int64); krow = {int(t): j for j, t in enumerate(k_ts)}
        P = arms["D1h8_s42"]; ic_res, ic_k0, ic_st = [], [], {0.25: [], 0.5: []}; yy = []
        for i in A_idx:
            j = krow.get(int(E_ts[i]))
            if j is None:
                continue
            m = MS[i]; k = K0[j, m]; p = P[i, m]; ok = np.isfinite(k) & np.isfinite(p) & np.isfinite(YR4s[i, m])
            if ok.sum() < 30:
                continue
            zk = xz(np.where(ok, k, np.nan)); zp = xz(np.where(ok, p, np.nan))
            X = np.stack([np.ones(ok.sum()), zk[ok]], 1); beta = np.linalg.lstsq(X, zp[ok], rcond=None)[0]; resid = zp[ok] - X @ beta
            ic_res.append(spear(resid, YR4s[i, m][ok])); ic_k0.append(spear(zk[ok], YR4s[i, m][ok])); yy.append(yrs[i])
            for lam in ic_st:
                ic_st[lam].append(spear(zk[ok] + lam * zp[ok], YR4s[i, m][ok]))
        yy = np.array(yy); ic_res = np.array(ic_res); ic_k0 = np.array(ic_k0)
        g["G1_readout"] = {"note": "K0 = pod slow_pred_hist_oos(旧 y4 秩目标/旧窗口训练; 只作对齐参照); 门只在 G0 过后生效",
                           "n": int(len(yy)), "ic_K0": nanmean(ic_k0), "delta_resid_ic": nanmean(ic_res), "by_year": {str(y): nanmean(ic_res[yy == y]) for y in YEARS},
                           "stack": {str(l): nanmean(np.array(v) - ic_k0) for l, v in ic_st.items()},
                           "pass_if_G0": bool(nanmean(ic_res) >= 0.003 and all(nanmean(ic_res[yy == y]) >= 0 for y in YEARS if (yy == y).any()))}
    out["gates"] = g
    json.dump(out, open(f"{OUT}/results/dlw_judge.json", "w"), indent=1)
    # ---- 终端表
    print("\n===== DLW 主表(集 A 残差秩 IC; 括号内原始秩 IC) =====")
    print(f"{'arm':<12s}{'IC_A':>9s}{'(raw)':>9s}{'2023':>8s}{'2024':>8s}{'2025':>8s}{'2026':>8s}{'IC_B':>8s}{'Q4':>8s}{'σ':>7s}{'tsP':>8s}{'null':>8s}{'pk':>4s}")
    for a, r in out["table"].items():
        v = out["validity"][a]
        print(f"{a:<12s}{r['ic_resid_A']:>+9.4f}{r['ic_raw_A']:>+9.4f}" + "".join(f"{r['ic_resid_by_year'][str(y)]:>+8.4f}" for y in YEARS) +
              f"{r['ic_resid_B']:>+8.4f}{r['q_by_quintile'][4]:>+8.4f}{r['sigma_ratio_median']:>7.3f}{r['per_asset_pearson_mean']:>+8.4f}{v['shuffle_null_mean']:>+8.4f}{v['peak_k']:>4d}")
    print("\n===== 成对 Δ(集 A, 配对 t, 逐年) =====")
    for k, d in out["delta"].items():
        print(f"{k:<22s} Δ {d['mean']:+.4f} t {d['t']:+.1f} 同号 {d['n_pos_years']}/{d['n_years']} | " + " ".join(f"{y}:{d['by_year'][str(y)]:+.4f}" for y in YEARS) + f" | B {d['B_mean']:+.4f} raw {d['raw_mean']:+.4f}")
    print("\n===== 种子 sd =====", json.dumps(out["seed_sd"]))
    print("\n===== 门 =====", json.dumps(g, ensure_ascii=False, indent=1))
    log("JUDGE_DONE")


if __name__ == "__main__":
    main()
