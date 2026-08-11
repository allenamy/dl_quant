"""窗口特异性 —— 执行 PREREG_leak_window_specificity_2026-08-04.md
(FROZEN v1, sha 39cb7131124a10d01f894e56b70aaae4191e79b812213a89aba3dd042cbcb246)

★ 上一版(leak_split)失败于: 只写了对 run 的伙伴判据, 没写对【仪器】的有效性判据。
  本版 §2 就是那条: 冻结 run 必须在 Δ=0 出尖峰, 否则本装置分辨不出窗口, 全表作废。
装置复用 measure_lookahead_exploitation_s1(import): tilt / market / 重抽样参数。
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
DELTAS = (-22, 0, 11, 22, 33, 44, 66, 88, 110)     # 预注册 §1; −22 只作读图参照
FAR = 44                                            # 预注册 §2: "远窗" = Δ >= 44


def window_sum(m, lo, hi):
    """Σ market[t+lo … t+hi], 越界补 0(与 leak_causal 同族)。"""
    pref = np.concatenate([[0.0], np.cumsum(m)])
    n = len(m); t = np.arange(n)
    a = np.clip(t + lo, 0, n); b = np.clip(t + hi + 1, 0, n)
    return pref[b] - pref[a]


def boot_peak_drop(tilt, W0, Wfar_list, block=M.BLOCK, nboot=M.NBOOT, seed=20260803):
    """|c(0)| − mean(|c(Δ_far)|) 的 block-bootstrap CI —— 预注册 §4 的绝对值形式。"""
    rng = np.random.default_rng(seed)
    n = len(tilt); nb = int(np.ceil(n / block))
    pool = np.arange(0, max(1, n - block + 1))
    out = np.empty(nboot)
    for b in range(nboot):
        st = rng.choice(pool, size=nb, replace=True)
        idx = np.concatenate([np.arange(s, s + block) for s in st])[:n]
        idx = idx[idx < n]
        ts = tilt[idx]
        if ts.std() < 1e-18:
            out[b] = np.nan; continue
        c0 = abs(np.corrcoef(ts, W0[idx])[0, 1])
        cf = [abs(np.corrcoef(ts, W[idx])[0, 1]) for W in Wfar_list]
        out[b] = c0 - float(np.mean(cf))
    out = out[np.isfinite(out)]
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))


z = np.load(B + "/wide_dl_full_corrfund_causal_v1.npz", allow_pickle=True)
chn = [str(x) for x in z["ch_names"]]
beta = z["CH"][:, :, chn.index("beta_24h")]
member, CL, Y = z["MEMBER110"], z["CL4"], z["Y4"]
mkt = M.market_series(B + "/wide_panel_full.npz")
WIN = {d: window_sum(mkt, 1 + d, 11 + d) for d in DELTAS}

print("c(Δ) = corr(tilt, Σ market[t+1+Δ … t+11+Δ])   ★Δ=0 是被泄漏的那 11 抽头")
print("{:14s}".format("run") + "".join("{:>9}".format("Δ=%d" % d) for d in DELTAS)
      + "{:>12}{:>22}".format("peak_drop", "95%CI peak_drop"))
rec = {}
for name, d in RUNS.items():
    rows, tilt = M.tilt_series(d, beta, member, CL, Y)
    cs = {dd: float(np.corrcoef(tilt, WIN[dd][rows])[0, 1]) for dd in DELTAS}
    far = [dd for dd in DELTAS if dd >= FAR]
    pd_ = abs(cs[0]) - float(np.mean([abs(cs[dd]) for dd in far]))
    lo, hi = boot_peak_drop(tilt, WIN[0][rows], [WIN[dd][rows] for dd in far])
    z0 = bool(lo <= 0.0 <= hi)
    print("{:14s}".format(name) + "".join("{:+9.4f}".format(cs[dd]) for dd in DELTAS)
          + "{:+12.4f}   [{:+.4f}, {:+.4f}]".format(pd_, lo, hi))
    rec[name] = {"c_by_delta": {str(k): round(v, 5) for k, v in cs.items()},
                 "peak_drop": round(pd_, 5), "ci95_peak_drop": [round(lo, 5), round(hi, 5)],
                 "ci_contains_zero": z0}

fp, fx = rec["frozen_plain"], rec["frozen_xattn"]
valid = (fp["peak_drop"] > 0 and fx["peak_drop"] > 0
         and not fp["ci_contains_zero"] and not fx["ci_contains_zero"])
partner = (fp["c_by_delta"]["0"] > 0 and fx["c_by_delta"]["0"] > 0)
print("\n[§2 有效性判据] 冻结 run 在 Δ=0 出尖峰(peak_drop>0 且 CI 排除 0): "
      + ("PASS — 本装置分辨得出窗口" if valid else "FAIL — 分辨不出窗口"))
print("[§3 伙伴判据]  冻结 run 的 c(0) 显著为正: " + ("PASS" if partner else "FAIL"))

if not (valid and partner):
    verdict = "TABLE_VOID — 装置无法定位窗口(或伙伴判据不过) ⇒ 本文不推进选臂"
else:
    cp = rec["clean_plain"]
    verdict = ("(b) 窗口特异 ⇒ 是【那条】泄漏的残留通路 ⇒ plain 出局, 上 xattn"
               if not cp["ci_contains_zero"] else
               "(a) 非窗口特异 ⇒ 不是那条泄漏, §8-2 对 plain 的『不过』不构成泄漏证据 ⇒ plain 清白")
print("[§4 判读]    " + verdict)

json.dump({"prereg": "PREREG_leak_window_specificity_2026-08-04.md",
           "prereg_sha256": "39cb7131124a10d01f894e56b70aaae4191e79b812213a89aba3dd042cbcb246",
           "deltas": list(DELTAS), "far_from": FAR, "block": M.BLOCK, "nboot": M.NBOOT,
           "validity_check_pass": valid, "partner_check_pass": partner,
           "verdict": verdict, "runs": rec},
          open(B + "/eda/RESULT_leak_window_specificity_2026-08-04.json", "w"), indent=1)
print("record -> eda/RESULT_leak_window_specificity_2026-08-04.json")
