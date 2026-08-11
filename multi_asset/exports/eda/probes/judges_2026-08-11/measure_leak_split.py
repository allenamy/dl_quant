"""把 leak 拆成【可预测】与【不可预测】两半 —— 执行 PREREG_leak_split_predictable_2026-08-04.md
(FROZEN v1, sha c45c7968e7b2797662bcc899e58ea79fe7105cea7bcd59f474d4971345f5eec5)。

判读规则在那份预注册 §3, 已在看到本脚本任何输出之前封存。本脚本【不重述】判读规则的理由,
只按它执行并把三行表的命中项打出来。

装置复用 `measure_lookahead_exploitation_s1`(import, 不复制): tilt / market / leak / 重抽样参数。
"""
import sys, json
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/eda")
import numpy as np
import measure_lookahead_exploitation_s1 as M

B = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports"
T = B + "/train"
RUNS = {"clean_plain":  T + "/wideA_lamorth0_5yr_causal_v1",
        "clean_xattn":  T + "/wideA_lamorth0_xattn_5yr_causal_v1",
        "frozen_plain": T + "/wideA_lamorth0_5yr",
        "frozen_xattn": T + "/wideA_lamorth0_xattn_5yr"}
LAGS = (1, 4, 12, 24, 72)          # 预注册 §1: m1 m4 m12 m24 m72
BURN_FRAC = 0.20                   # 预注册 §1: 前 20% 锚 burn-in, 不出读数


def trailing_sums(m, lags):
    """Σ market[t−(k−1) … t], 每个 k 一列。前缀和, 与 leak/causal 同族构造。"""
    pref = np.concatenate([[0.0], np.cumsum(m)])
    out = []
    for k in lags:
        lo = np.maximum(0, np.arange(len(m)) + 1 - k)
        out.append(pref[np.arange(len(m)) + 1] - pref[lo])
    return np.column_stack(out)


def expanding_ols_predict(X, y, burn):
    """严格因果: 第 i 行的预测只用【严格早于 i】的行拟合。
    ★ running X'X / X'y —— 精确等价于逐行重拟合, 但每步 O(p^2) 而非 O(n p^2)。
    ★ 全样本拟合会让 pred 吸收噪声、把 unpred 人为缩小 ⇒ 系统性偏向"plain 清白",
      而那正是作者已表达过的倾向 —— 预注册 §1 明令不得如此。"""
    n, p = X.shape
    A = np.column_stack([np.ones(n), X])          # 截距
    q = p + 1
    XtX = np.zeros((q, q)); Xty = np.zeros(q)
    pred = np.full(n, np.nan)
    for i in range(n):
        if i >= burn:
            try:
                beta = np.linalg.solve(XtX + 1e-10 * np.eye(q), Xty)
                pred[i] = float(A[i] @ beta)
            except np.linalg.LinAlgError:
                pred[i] = np.nan
        XtX += np.outer(A[i], A[i]); Xty += A[i] * y[i]
    return pred


z = np.load(B + "/wide_dl_full_corrfund_causal_v1.npz", allow_pickle=True)
chn = [str(x) for x in z["ch_names"]]
beta = z["CH"][:, :, chn.index("beta_24h")]
member, CL, Y = z["MEMBER110"], z["CL4"], z["Y4"]
mkt = M.market_series(B + "/wide_panel_full.npz")
leak_all, caus_all = M.leak_causal(mkt)
P_all = trailing_sums(mkt, LAGS)

hdr = ("run", "n", "corr(t,Lpred)", "corr(t,Lunpred)", "95%CI unpred", "CI∋0")
print("{:14s} {:>6} {:>14} {:>16} {:>24} {:>7}".format(*hdr))
rec = {}
for name, d in RUNS.items():
    rows, tilt = M.tilt_series(d, beta, member, CL, Y)
    lk, Pm = leak_all[rows], P_all[rows]                 # 按锚行取, 保持时间序
    burn = int(BURN_FRAC * len(rows))
    lp = expanding_ols_predict(Pm, lk, burn)
    ok = np.isfinite(lp)
    t_, l_, p_ = tilt[ok], lk[ok], lp[ok]
    u_ = l_ - p_
    c_pred = float(np.corrcoef(t_, p_)[0, 1])
    c_unp = float(np.corrcoef(t_, u_)[0, 1])
    lo, hi = M.block_boot_ci(t_, u_)
    z0 = bool(lo <= 0.0 <= hi)
    print("{:14s} {:6d} {:+14.4f} {:+16.4f}   [{:+.4f}, {:+.4f}] {:>7}".format(
        name, int(ok.sum()), c_pred, c_unp, lo, hi, "yes" if z0 else "NO"))
    rec[name] = {"n_scored": int(ok.sum()), "n_burn_in": burn,
                 "corr_tilt_leak_predictable": round(c_pred, 5),
                 "corr_tilt_leak_unpredictable": round(c_unp, 5),
                 "ci95_unpredictable": [round(lo, 5), round(hi, 5)],
                 "ci_contains_zero": z0,
                 "r2_of_leak_predictor": round(float(1 - u_.var() / l_.var()), 5)}

# ── 预注册 §2/§3 的判读, 按封存顺序执行 ────────────────────────────────────────
fp, fx = rec["frozen_plain"], rec["frozen_xattn"]
partner_ok = (not fp["ci_contains_zero"] and not fx["ci_contains_zero"]
              and fp["corr_tilt_leak_unpredictable"] > 0 and fx["corr_tilt_leak_unpredictable"] > 0)
print("\n[§2 伙伴判据] 冻结 run 在 unpred 上必须 CI 排除 0 且为正: "
      + ("PASS" if partner_ok else "FAIL"))
if not partner_ok:
    verdict = "TABLE_VOID — 扣掉可预测部分把真实泄漏利用一起扣没了; 本表不为任何一支背书"
else:
    cp, cx = rec["clean_plain"], rec["clean_xattn"]
    if cp["ci_contains_zero"] and not cx["ci_contains_zero"]:
        verdict = ("UNEXPECTED_SHAPE — plain 含 0 而 xattn 排除 0, 与 §8-2 相反; "
                   "两支都不放行, 回审计(预注册 §3 末行)")
    elif cp["ci_contains_zero"]:
        verdict = ("(a) —— plain 的残余落在【可预测】那一半 = 择时本事; "
                   "§8-2 对 plain 的『不过』源自判据字面未为此留条款 ⇒ plain 清白")
    else:
        verdict = "(b) —— 残留泄漏通路存在于【不可预测】那一半 ⇒ plain 出局, 上 xattn"
print("[§3 判读]  " + verdict)

json.dump({"prereg": "PREREG_leak_split_predictable_2026-08-04.md",
           "prereg_sha256": "c45c7968e7b2797662bcc899e58ea79fe7105cea7bcd59f474d4971345f5eec5",
           "lags": list(LAGS), "burn_frac": BURN_FRAC,
           "block": M.BLOCK, "nboot": M.NBOOT,
           "partner_check_pass": partner_ok, "verdict": verdict, "runs": rec},
          open(B + "/eda/RESULT_leak_split_2026-08-04.json", "w"), indent=1)
print("record -> eda/RESULT_leak_split_2026-08-04.json")
