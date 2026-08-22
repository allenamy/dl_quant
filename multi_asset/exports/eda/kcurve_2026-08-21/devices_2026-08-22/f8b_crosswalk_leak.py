"""F-8B · 口径对账表(cross)+ 泄漏终审(leak)@jpline CPU(2026-08-22, Session 6737834a-F8)。
预注册: CALIBER_CROSSWALK_wide_signal_2026-08-22.md §C(SHA d88d541d…4a7b)+ PREREG_RESULT_F8B_leak_final_2026-08-22.md §V(SHA 77564153…c626), commit ebec104, 先于新数。
cross: 每份存盘预测 × 四坐标读数(N-resid 集A / N-raw 集A / N-raw@25-26B / O-raw@25-26B[目标=y4old])+ 分解算术 + 堆叠两形态新算 + ρ(F8ALL_lgbm, D1h8_s42)。
leak : 四仪器 × 每族(A..J, Hs, ALL, S300): 结构收据引用 / 配对 Δnull(同置换双臂, 锚聚类 SE)/ 增量谱(臂⊥base, 判据只看 k≥0)/ 2026 封存段; 陈化曲线引用 f8_stale_test.json 补 SE; S300 重算存预测(Ridge α=1000 事前定 + LGBM dlw 参数)。
用法: python -u f8b_crosswalk_leak.py cross|leak
"""
import os, sys, json, time, hashlib
import numpy as np
from scipy.stats import rankdata, spearmanr

ROOT = "/mnt/storage/private/work_hsy"
DLW = f"{ROOT}/dlw_2026-08-22"; OUT = f"{ROOT}/f8_2026-08-22"; K0DIR = f"{ROOT}/pod_backup_2026-08-21"
YEARS = (2023, 2024, 2025, 2026); EMBARGO = 60
LGB_PARAMS = dict(n_estimators=400, learning_rate=0.05, num_leaves=63, subsample=0.8, colsample_bytree=0.8, random_state=0, n_jobs=8, verbose=-1)
CW_SHA = "d88d541d66594d87609f2a5abcfc8de142fa0305cb55f78009fc71dbbd214a7b"; LEAK_SHA = "775641530b80b3339869161bf5c695a89562f6b0dc8658ccaaa53861a2eac626"; PREREG_COMMIT = "ebec104"
T0 = time.time()


def log(*a):
    print(f"[{time.time()-T0:7.1f}s]", *a, flush=True)


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


def nm(a):
    a = np.asarray(a, float)
    return float(np.nanmean(a)) if np.isfinite(a).any() else float("nan")


def xz(v):
    ok = np.isfinite(v); out = np.full(len(v), np.nan); n = int(ok.sum())
    if n >= 10:
        out[ok] = (rankdata(v[ok]) - (n + 1) / 2) / max(n - 1, 1)
    return out


def load_all():
    TG = np.load(f"{DLW}/data/dlw_targets.npz", allow_pickle=True)
    T = dict(E_ts=TG["E_ts"].astype(np.int64), MS=list(TG["members"]), yrs=TG["yrs"].astype(int), YRZ=TG["YRZ"],
             YR4s=TG["YR4s"], y4s=TG["y4s"], y4old=TG["y4old"], btcv=TG["btcv"], syms=[str(s) for s in TG["symbols"]])
    T["nA"], T["NW"] = T["YR4s"].shape; T["memn"] = np.array([len(m) for m in T["MS"]])
    return T


def pred_matrix_K0(T):
    K0 = np.load(f"{K0DIR}/slow_pred_hist_oos.npy"); MT = np.load(f"{K0DIR}/wide_fea_hist_meta.npz", allow_pickle=True)
    krow = {int(t): j for j, t in enumerate(MT["E_ts"].astype(np.int64))}
    P = np.full((T["nA"], T["NW"]), np.nan, np.float32)
    for i, t in enumerate(T["E_ts"]):
        j = krow.get(int(t))
        if j is not None:
            P[i] = K0[j]
    return P


def cross():
    T = load_all(); nA, NW = T["nA"], T["NW"]; yrs = T["yrs"]; MS = T["MS"]; test = np.isin(yrs, YEARS)
    B25 = test & (yrs >= 2025) & (T["memn"] >= 360)
    preds = {"K0_slowking_oldtgt": pred_matrix_K0(T)}
    for a in ("R82_s0", "L82_s0", "D0_s42", "D1h8_s42", "D1h8_s2027", "D1h8_s3037", "D2aux12_s42"):
        p = f"{DLW}/preds/dlw_{a}.npy"
        if os.path.exists(p):
            preds[a] = np.load(p)
    for m in ("ridge", "lgbm"):
        for a in ("base", "pALL"):
            preds[f"F8_{m}_{a}"] = np.load(f"{OUT}/preds/f8_{m}_{a}.npy")
    # 堆叠① z-sum
    zsum = np.full((nA, NW), np.nan, np.float32)
    L = preds["L82_s0"]; D8 = preds["D1h8_s42"]
    for i in np.where(test)[0]:
        m = MS[i]; a_ = L[i, m]; b_ = D8[i, m]
        ok = np.isfinite(a_) & np.isfinite(b_)
        if ok.sum() >= 30:
            v = np.full(len(m), np.nan); v[ok] = (xz(np.where(ok, a_, np.nan))[ok] + xz(np.where(ok, b_, np.nan))[ok])
            zsum[i, m] = v
    preds["STACK_zsum_L82_D1h8"] = zsum
    # 堆叠② 83 列 LGBM(折 2024/2025; 训练=有 D1h8 的更早年)
    FE = np.load(f"{DLW}/data/dlw_fea82.npz", allow_pickle=True)
    X82 = FE["X"]; pa = FE["pair_a"].astype(np.int64); ps = FE["pair_s"].astype(np.int64)
    zfeat = np.zeros(len(pa), np.float32)
    st = np.searchsorted(pa, np.arange(nA + 1))
    d8fin = np.zeros(nA, bool)
    for i in range(nA):
        m = MS[i]; b_ = D8[i, m]
        if np.isfinite(b_).sum() >= 30:
            d8fin[i] = True; z = xz(b_); zfeat[st[i]:st[i + 1]] = np.nan_to_num(z, nan=0.0)
    Y = T["YRZ"][pa, ps]; okrow = np.isfinite(Y)
    Xs = np.concatenate([X82[okrow].astype(np.float32), zfeat[okrow, None]], 1); Yv = Y[okrow].astype(np.float32)
    A_ = pa[okrow]; S_ = ps[okrow]
    import lightgbm as lgb
    st83 = np.full((nA, NW), np.nan, np.float32)
    for YV in (2024, 2025):
        te_anchor = np.where(yrs == YV)[0]; first_te = int(te_anchor[0])
        tr_ok = np.zeros(nA, bool); tr_ok[(yrs < YV) & (np.arange(nA) < first_te - EMBARGO) & d8fin] = True
        tr = tr_ok[A_]; te = (yrs[A_] == YV) & d8fin[A_]
        gbm = lgb.LGBMRegressor(**LGB_PARAMS).fit(Xs[tr], Yv[tr])
        st83[A_[te], S_[te]] = gbm.predict(Xs[te]).astype(np.float32)
        log(f"stack83 {YV} trained rows {tr.sum()}")
    preds["STACK83_L82_plus_zD1h8"] = st83
    del X82, Xs
    out = {"prereg": {"cw_sha": CW_SHA, "commit": PREREG_COMMIT}, "self_sha256": sha(os.path.abspath(__file__)),
           "targets_sha256": sha(f"{DLW}/data/dlw_targets.npz"), "cells": {}, "rho": {}, "decomp": {}}
    for name, P in preds.items():
        icr = np.full(nA, np.nan); icy = np.full(nA, np.nan); ico = np.full(nA, np.nan)
        for i in np.where(test)[0]:
            m = MS[i]; p = P[i, m]
            if np.isfinite(p).sum() < 30:
                continue
            icr[i] = spear(p, T["YR4s"][i, m]); icy[i] = spear(p, T["y4s"][i, m]); ico[i] = spear(p, T["y4old"][i, m])
        fin = np.isfinite(icr)
        cell = {"n_anchors": int(fin.sum()), "years_present": sorted(set(int(y) for y in yrs[fin])),
                "N_resid_A": nm(icr[fin]), "N_raw_A": nm(icy[fin]),
                "N_resid_by_year": {str(y): nm(icr[fin & (yrs == y)]) for y in YEARS},
                "N_raw_by_year": {str(y): nm(icy[fin & (yrs == y)]) for y in YEARS},
                "N_raw_B2526": nm(icy[fin & B25]), "O_raw_B2526": nm(ico[fin & B25]), "N_resid_B2526": nm(icr[fin & B25]),
                "n_B2526": int((fin & B25).sum())}
        out["cells"][name] = cell
        log(name, json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in cell.items() if not k.endswith("by_year")}))
    # 分解算术
    for name in ("L82_s0", "D1h8_s42", "K0_slowking_oldtgt", "F8_lgbm_pALL"):
        c = out["cells"][name]
        out["decomp"][name] = {"resid_A": c["N_resid_A"], "step1_caliber_resid_to_raw": c["N_raw_A"] - c["N_resid_A"],
                               "raw_A": c["N_raw_A"], "step2_anchorset_A_to_B2526": c["N_raw_B2526"] - c["N_raw_A"],
                               "raw_B2526": c["N_raw_B2526"], "step3_target_y4s_to_y4old": c["O_raw_B2526"] - c["N_raw_B2526"],
                               "old_raw_B2526": c["O_raw_B2526"]}
    # 有效性锚点
    k0o = out["cells"]["K0_slowking_oldtgt"]["O_raw_B2526"]
    out["anchor_check"] = {"K0_O_raw_B2526": k0o, "band": [0.060, 0.068], "pass": bool(0.060 <= k0o <= 0.068)}
    # ρ 格
    PA = preds["F8_lgbm_pALL"]; PD = preds["D1h8_s42"]
    rhos = []; d_resid = []
    icr_A = np.full(nA, np.nan); icr_D = np.full(nA, np.nan)
    for i in np.where(test)[0]:
        m = MS[i]; a_ = PA[i, m]; b_ = PD[i, m]
        ok = np.isfinite(a_) & np.isfinite(b_)
        if ok.sum() < 30:
            continue
        rhos.append(spear(a_, b_))
        icr_A[i] = spear(np.where(ok, a_, np.nan), T["YR4s"][i, m]); icr_D[i] = spear(np.where(ok, b_, np.nan), T["YR4s"][i, m])
    okp = np.isfinite(icr_A) & np.isfinite(icr_D); d = icr_A[okp] - icr_D[okp]
    out["rho"] = {"rho_mean": nm(rhos), "n_common_anchors": int(okp.sum()), "years": sorted(set(int(y) for y in yrs[okp])),
                  "ic_resid_F8ALL_on_common": nm(icr_A[okp]), "ic_resid_D1h8_on_common": nm(icr_D[okp]),
                  "paired_diff_mean": float(d.mean()), "paired_diff_t": float(d.mean() / (d.std(ddof=1) / np.sqrt(len(d)) + 1e-12)),
                  "verdict_rule": "|diff|<=0.005 且 rho>=0.5 ⇒ 同一块信息(弹药>模型类第三证)"}
    json.dump(out, open(f"{OUT}/results/f8b_crosswalk.json", "w"), indent=1)
    print("\n==== CROSSWALK(行=预测, 列=坐标)====")
    print(f"{'pred':<26s}{'nA':>6s}{'N-resid':>9s}{'N-raw':>9s}{'N-raw@25-26B':>13s}{'O-raw@25-26B':>13s}{'N-resid@B':>10s}{'years'}")
    for name, c in out["cells"].items():
        print(f"{name:<26s}{c['n_anchors']:>6d}{c['N_resid_A']:>+9.4f}{c['N_raw_A']:>+9.4f}{c['N_raw_B2526']:>+13.4f}{c['O_raw_B2526']:>+13.4f}{c['N_resid_B2526']:>+10.4f}  {c['years_present']}")
    print("anchor_check", out["anchor_check"]); print("rho", json.dumps(out["rho"]))
    log("CROSS_DONE")


# =====================================================================================
def leak():
    T = load_all(); nA, NW = T["nA"], T["NW"]; yrs = T["yrs"]; MS = T["MS"]; test = np.isin(yrs, YEARS); YR4s = T["YR4s"]
    res = {"prereg": {"leak_sha": LEAK_SHA, "commit": PREREG_COMMIT}, "self_sha256": sha(os.path.abspath(__file__)),
           "structural": {"f8_build_report_sha": sha(f"{OUT}/results/f8_build_report.json"), "f8s_build_report_sha": sha(f"{OUT}/results/f8s_build_report.json"),
                          "max_row_offset_vs_E": json.load(open(f"{OUT}/results/f8_build_report.json"))["max_row_offset_vs_E"],
                          "struct_assert": json.load(open(f"{OUT}/results/f8_build_report.json"))["struct_assert"]},
           "stale_cited": json.load(open(f"{OUT}/results/f8_stale_test.json")), "families": {}, "verdicts": {}}
    # ---- S300 重算(Ridge α=1000 事前定 + LGBM), 存预测
    FE = np.load(f"{DLW}/data/dlw_fea82.npz", allow_pickle=True)
    X82 = FE["X"]; pa = FE["pair_a"].astype(np.int64); ps = FE["pair_s"].astype(np.int64)
    SC = np.load(f"{OUT}/data/f8_scale518.npz", allow_pickle=True)
    XS = SC["X"][:, :214]
    Y = T["YRZ"][pa, ps]; okrow = np.isfinite(Y)
    Xall = np.concatenate([X82[okrow].astype(np.float32), XS[okrow]], 1); Yv = Y[okrow].astype(np.float32)
    A_ = pa[okrow]; S_ = ps[okrow]; YRA = yrs[A_]
    del XS
    for model in ("ridge", "lgbm"):
        pth = f"{OUT}/preds/f8b_{model}_S300.npy"
        if os.path.exists(pth):
            continue
        P = np.full((nA, NW), np.nan, np.float32)
        for YV in YEARS:
            te_anchor = np.where(yrs == YV)[0]; first_te = int(te_anchor[0])
            tr_ok = np.zeros(nA, bool); tr_ok[(yrs < YV) & (np.arange(nA) < first_te - EMBARGO)] = True
            tr = tr_ok[A_]; te = YRA == YV
            if model == "ridge":
                mu = Xall[tr].mean(0); sd = Xall[tr].std(0) + 1e-9
                Xs = np.clip((Xall[tr] - mu) / sd, -5, 5).astype(np.float64); Xa = np.concatenate([Xs, np.ones((Xs.shape[0], 1))], 1)
                G = Xa.T @ Xa; G[:-1, :-1] += 1000.0 * np.eye(Xs.shape[1]); beta = np.linalg.solve(G, Xa.T @ Yv[tr].astype(np.float64)); del Xs, Xa, G
                Xt = np.clip((Xall[te] - mu) / sd, -5, 5).astype(np.float64); pv = (np.concatenate([Xt, np.ones((Xt.shape[0], 1))], 1) @ beta).astype(np.float32); del Xt
            else:
                import lightgbm as lgb
                pv = lgb.LGBMRegressor(**LGB_PARAMS).fit(Xall[tr], Yv[tr]).predict(Xall[te]).astype(np.float32)
            P[A_[te], S_[te]] = pv
            log(f"S300 {model} {YV} done")
        np.save(pth, P)
    del Xall, X82
    # ---- 电池: 每模型每臂
    fams = ["pA", "pB", "pC", "pD", "pE", "pF", "pG", "pH", "pI", "pJ", "pHs", "pALL", "S300"]
    for model in ("ridge", "lgbm"):
        base = np.load(f"{OUT}/preds/f8_{model}_base.npy")
        A_idx_all = np.where(test)[0]
        # null 置换表(3 种子, 同年内): 预生成 j 映射, 双臂共用
        perms = {}
        for s in range(3):
            rs = np.random.default_rng(s); mp = {}
            for y in YEARS:
                ia = np.where(test & (yrs == y))[0]; pm = rs.permutation(ia)
                for i, j in zip(ia, pm):
                    mp[i] = j
            perms[s] = mp
        sub = A_idx_all[::2]
        base_null = {s: {} for s in range(3)}
        for s in range(3):
            for i in sub:
                j = perms[s][i]; m = MS[i]
                base_null[s][i] = spear(base[i, m], YR4s[j, m])
        for fam in fams:
            pth = f"{OUT}/preds/f8_{model}_{fam}.npy" if fam != "S300" else f"{OUT}/preds/f8b_{model}_S300.npy"
            if not os.path.exists(pth):
                continue
            P = np.load(pth)
            key = f"{model}:{fam}"
            # 配对 Δnull(锚聚类: 每锚 3 种子均值)
            dvals = []
            for i in sub:
                m = MS[i]; ds = []
                for s in range(3):
                    j = perms[s][i]
                    a_ = spear(P[i, m], YR4s[j, m]); b_ = base_null[s][i]
                    if np.isfinite(a_) and np.isfinite(b_):
                        ds.append(a_ - b_)
                if ds:
                    dvals.append(np.mean(ds))
            dvals = np.array(dvals); dn_mean = float(dvals.mean()); dn_se = float(dvals.std(ddof=1) / np.sqrt(len(dvals)))
            # 增量谱
            spec = {}
            for k in range(-6, 7):
                v = []
                for i in A_idx_all[::3]:
                    j = i + k
                    if not (0 <= j < nA):
                        continue
                    m = MS[i]; p = P[i, m]; b_ = base[i, m]
                    ok = np.isfinite(p) & np.isfinite(b_)
                    if ok.sum() < 30:
                        continue
                    zp = np.full(len(m), np.nan); zb = np.full(len(m), np.nan)
                    zp[ok] = rankdata(p[ok]); zb[ok] = rankdata(b_[ok])
                    Xr = np.stack([np.ones(int(ok.sum())), zb[ok]], 1); beta = np.linalg.lstsq(Xr, zp[ok], rcond=None)[0]
                    r = np.full(len(m), np.nan); r[ok] = zp[ok] - Xr @ beta
                    v.append(spear(r, YR4s[j, m]))
                spec[str(k)] = nm(v)
            kpos = {k: spec[str(k)] for k in range(0, 7)}
            peak_kpos = max(kpos, key=lambda kk: kpos[kk] if np.isfinite(kpos[kk]) else -9)
            # 2026 封存段 Δ
            icr_a = np.full(nA, np.nan); icr_b = np.full(nA, np.nan)
            for i in np.where(test & (yrs == 2026))[0]:
                m = MS[i]; icr_a[i] = spear(P[i, m], YR4s[i, m]); icr_b[i] = spear(base[i, m], YR4s[i, m])
            d26 = nm((icr_a - icr_b)[np.isfinite(icr_a - icr_b)])
            fam_res = {"dnull_mean": dn_mean, "dnull_se": dn_se, "dnull_within_2se": bool(abs(dn_mean) <= 2 * dn_se),
                       "inc_spectrum": spec, "peak_kpos": int(peak_kpos), "peak_at_0": bool(peak_kpos == 0), "delta_2026": d26, "n_null_anchors": int(len(dvals))}
            # 判决(V.2)
            if fam_res["dnull_within_2se"] and fam_res["peak_at_0"]:
                v_ = "无泄漏"
            elif (not fam_res["dnull_within_2se"]) and (not fam_res["peak_at_0"]):
                v_ = "有泄漏"
            else:
                v_ = "该列不可判定"
            fam_res["verdict"] = v_
            res["families"][key] = fam_res
            log(key, f"Δnull {dn_mean:+.5f}±{dn_se:.5f} peak_k+ {peak_kpos} Δ2026 {d26:+.4f} ⇒ {v_}")
    json.dump(res, open(f"{OUT}/results/f8b_leak_final.json", "w"), indent=1)
    print("\n==== LEAK FINAL(行=模型:族)====")
    print(f"{'arm':<12s}{'Δnull±SE':>20s}{'|Δ|≤2SE':>8s}{'峰k≥0':>6s}{'Δ2026':>9s}  判决")
    for k, v in res["families"].items():
        print(f"{k:<12s}{v['dnull_mean']:+.5f}±{v['dnull_se']:.5f}{'':>2s}{str(v['dnull_within_2se']):>8s}{v['peak_kpos']:>6d}{v['delta_2026']:>+9.4f}  {v['verdict']}")
    log("LEAK_DONE")


if __name__ == "__main__":
    {"cross": cross, "leak": leak}[sys.argv[1]]()
