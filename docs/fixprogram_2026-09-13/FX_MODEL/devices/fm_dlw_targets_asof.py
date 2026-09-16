"""fm_dlw_targets_asof.py -- FX-MODEL new builder for TIM-01 (member clock) and TRN-06 (membership population).

Base: v4_chain_2026-09-09/pod_dlw_targets_raw.py, sha256 d7c528231f00902964c5244fe8402bbd84688af05c04c2dab8760fe8ad584be2,
copied from the COMMITTED blob byte-for-byte (not the working tree) and then edited in exactly three places. The base's
original docstring follows unchanged below, so the frozen conventions it records stay readable.

KNOBS -- all REQUIRED env, no defaults; a missing or unrecognised value refuses rather than guessing:
  FMT_MEMBER_CLOCK  legacy_Em1 | serve_E
        legacy_Em1 member statistics over rows [E-2016, E-1]: the bar closing AT the anchor is invisible (base).
        serve_E    rows [E-2015, E], matching shadow_loop_v3.py L365/L371, which is what the producer serves.
        Red test R-TIM-5 is the assertion this flips.
  FMT_FORWARD_TERM  legacy_isfinite | trailing_only
        legacy_isfinite membership requires a finite FORWARD label -- a property of the future decides whether a row is
                        trained on. TRN-06 channel B. Red test R-TRD-1 demonstrates it interventionally.
        trailing_only   no forward term, as production. NOTE THE COUPLING (FACT_TABLE_MODEL §5.2): removing the forward
                        term INCREASES dead-but-kept rows (channel A). The two channels are different populations,
                        reported jointly and never summed.
  FMT_TRADABLE      off | <path to tradability_v1.npz>   (+ FMT_TRADABLE_SHA, REQUIRED and asserted when a path is given)
        Admits only names whose W24H decision state at that anchor is TRADABLE (== 2). Per FXR-DATA-1 this is a
        labelled admission screen built from PAST ACTIVITY -- not a settlement truth. Exit P&L for a dead contract
        stays explicitly unknown, and nothing here claims otherwise. TRN-06 channel A.

POSITIVE CONTROL: legacy_Em1 + legacy_isfinite + off must reproduce the base's arrays BITWISE before this builder is
used for anything. "Bitwise" means the arrays; a report/meta field necessarily names the device that wrote it.

FX-TRAIN has an in-flight TRN-02 change to the same base in the working tree (4568bea6063fd21f) adding raw-patch
coverage verification. It is ORTHOGONAL to these knobs -- it touches patch application, not the member screen -- but
the two must be reconciled before either reaches the October chain.

--- the base's original docstring, unchanged, follows ---

DLW · 目标 / 锚 / 成员 唯一真相源 @jpline(2026-08-22, Session 6737834a-DLW)。
预注册: multi_asset/exports/eda/PREREG_RESULT_DLW_xattn_2026-08-22.md §P.1(冻结段 SHA256 33f066c9…64577, commit 7acda02, 先于任何数字)。
产物: /mnt/storage/private/work_hsy/dlw_2026-08-22/data/dlw_targets.npz
      (E_ts / E_row / members(object) / y4s / YR4s / YRZ / yrs / qvk / btcv / has_panel / symbols / meta_json)
      + results/dlw_targets_report.json(常数、输入 SHA、锚数、对齐自检、结构断言)。
冻结约定(P.1):
  缓存 ts = bar 收盘时刻; 锚行 E = ts % 14400 == 0 且 E ≥ 576 且 E + 48 ≤ TT − 1。
  成员统计窗(覆盖/波动/量能/BTC 波动) rows [max(E−2016, 0), E)(旧装置 pod_kcurve.py 逐字, 使成员集与 K 曲线装置同构)。
  目标 y4s = Π_{k=1..48}(1 + ret5[E+k]) − 1 = 持仓窗 (N, N+4h] 简单持有收益(缺 bar 记 0, 有数 bar < 46 ⇒ NaN)。
  残差 YR4s = y4s − X β: X = 六因子 {f_rev_4h, f_rev_24h, f_vol_7d, f_range_24h, f_mom_7d, f_fund_ema} 在 wide_panel_4h_v1 锚行的成员内秩 z
  (缺失 ⇒ 0), 岭 λ=1e-3, 有数成员 ≥ 60 才回归(DESIGN_wide_book_v1 §5 逐字)。
  标签 YRZ = 成员内 YR4s 秩线性缩放到 [−0.5, 0.5]。
结构断言: 目标行窗 = [E+1, E+48](min_target_row_offset = +1); 输入行窗(由 dlw_features.py / dlw_train.py 各自断言)≤ E。
用法 @jpline: python dlw_targets.py
"""
import os, sys, json, time, hashlib
import numpy as np
from scipy.stats import rankdata, spearmanr

ROOT = "/mnt/storage/private/work_hsy"
CACHE = os.environ.get("DLWT_CACHE", "/workspace/data/dlnative_5m_wide829_f16_ext.npz")  # EXT_ENV
PANEL = os.environ.get("DLWT_PANEL", "/workspace/data/wide_panel_4h_v2ext.npz")  # EXT_ENV
OUT = os.environ.get("DLWT_OUT", "/workspace/dlw_ext")  # EXT_ENV
W = 576; FWD = 48; TRAIL = 2016; NTOP = 400; MIN_MEM = 50; MIN_FIN = 46
F6_KEYS = ["f_rev_4h", "f_rev_24h", "f_vol_7d", "f_range_24h", "f_mom_7d", "f_fund_ema"]; LAM = 1e-3; MIN_RES = 60
CHN_EXPECT = ["ret5", "range", "cpos", "log_qv", "log_cnt", "log_avgsz", "tbf"]

# ═════════════ FX-MODEL knobs: ALL REQUIRED, NO DEFAULTS (a missing or unrecognised knob refuses, never guesses) ══════
_REQ = ("FMT_MEMBER_CLOCK", "FMT_FORWARD_TERM", "FMT_TRADABLE")
_missing = [k for k in _REQ if not os.environ.get(k)]
if _missing:
    raise SystemExit("FMT_REFUSED: required env not set, and this builder has no defaults: %s" % _missing)
FMT_MEMBER_CLOCK = os.environ["FMT_MEMBER_CLOCK"]
FMT_FORWARD_TERM = os.environ["FMT_FORWARD_TERM"]
FMT_TRADABLE = os.environ["FMT_TRADABLE"]
if FMT_MEMBER_CLOCK not in ("legacy_Em1", "serve_E"):
    raise SystemExit("FMT_REFUSED: FMT_MEMBER_CLOCK=%r not in {legacy_Em1, serve_E}" % FMT_MEMBER_CLOCK)
if FMT_FORWARD_TERM not in ("legacy_isfinite", "trailing_only"):
    raise SystemExit("FMT_REFUSED: FMT_FORWARD_TERM=%r not in {legacy_isfinite, trailing_only}" % FMT_FORWARD_TERM)
_TRD_STATE = _TRD_ROW = _TRD_COL = None
_TRD_META = {"mode": "off"}
T0 = time.time()


def log(*a):
    print(f"[{time.time()-T0:7.1f}s]", *a, flush=True)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""):
            h.update(ch)
    return h.hexdigest()


def spear(x, y):
    ok = np.isfinite(x) & np.isfinite(y)
    return spearmanr(x[ok], y[ok]).correlation if ok.sum() >= 10 else np.nan


def xz(v):
    """成员内秩 z ∈ [−0.5, 0.5], 缺失 ⇒ 0(中性)。"""
    ok = np.isfinite(v); out = np.zeros(len(v), np.float64); n = int(ok.sum())
    if n >= 10:
        r = rankdata(v[ok]); out[ok] = (r - (n + 1) / 2) / max(n - 1, 1)
    return out, ok


def main():
    os.makedirs(f"{OUT}/data", exist_ok=True); os.makedirs(f"{OUT}/results", exist_ok=True)
    rep = {"self_sha256": sha(os.path.abspath(__file__)), "const": dict(W=W, FWD=FWD, TRAIL=TRAIL, NTOP=NTOP, MIN_MEM=MIN_MEM, MIN_FIN=MIN_FIN,
           F6_KEYS=F6_KEYS, LAM=LAM, MIN_RES=MIN_RES, target_row_window="[E+1, E+48]", member_stat_window="[max(E-2016,0), E)",
           prereg_sha="33f066c9460587864866e4f31afb72c24ae93c98183fc779c12aa0af70764577", prereg_commit="7acda02")}
    log("sha256 inputs ..."); rep["input_sha256"] = {"cache": sha(CACHE), "panel": sha(PANEL)}
    Z = np.load(CACHE, allow_pickle=True)
    CTS = Z["ts"].astype(np.int64); CD = Z["data"]; syms = [str(s) for s in Z["symbols"]]; ch = [str(c) for c in Z["ch"]]
    assert ch[:7] == CHN_EXPECT and (len(ch) == 7 or ch[7] == "ret5_raw"), ch
    RET_CH = int(os.environ.get("DLWT_RET_CH", "0")); assert RET_CH in (0, 7)   # 7 = ret5_raw (PREREG_caliber_program §3)
    NW = len(syms); TT = CD.shape[0]; BTC_T = syms.index("BTCUSDT")
    # ── FX-MODEL: load the pinned tradability artifact here, where the cache symbol order is known ──
    global _TRD_STATE, _TRD_ROW, _TRD_COL, _TRD_META
    if FMT_TRADABLE != "off":
        _want = os.environ.get("FMT_TRADABLE_SHA")
        if not _want:
            raise SystemExit("FMT_REFUSED: FMT_TRADABLE is a path, so FMT_TRADABLE_SHA is required and is asserted")
        _got = sha(FMT_TRADABLE)
        if _got != _want:
            raise SystemExit("FMT_REFUSED: tradability sha mismatch: want %s got %s" % (_want, _got))
        _T = np.load(FMT_TRADABLE, allow_pickle=True)
        _tsym = [str(s) for s in _T["symbols"]]
        _missing_syms = [s for s in syms if s not in set(_tsym)]
        if _missing_syms:
            raise SystemExit("FMT_REFUSED: %d cache symbols absent from the tradability artifact, e.g. %s"
                             % (len(_missing_syms), _missing_syms[:5]))
        _pos = {s: k for k, s in enumerate(_tsym)}
        _TRD_COL = np.array([_pos[s] for s in syms], np.int64)     # artifact column order -> cache column order
        _TRD_STATE = _T["state_W24H"]                              # 0 NODATA / 1 UNTRADED / 2 TRADABLE
        _TRD_ROW = {int(t): k for k, t in enumerate(_T["anchor_ts"].astype(np.int64))}
        _TRD_META = {"mode": "on", "path": FMT_TRADABLE, "sha256": _got, "window": "W24H",
                     "spec_sha256": str(_T["spec_sha256"]), "n_symbols": int(_T["n_symbols"]),
                     "state_codes": "0 NODATA / 1 UNTRADED / 2 TRADABLE (common/tradability.py:24)",
                     "caveat": "FXR-DATA-1: a past-activity admission screen, NOT a settlement truth; exit P&L for a "
                               "dead contract stays explicitly unknown"}
        log("tradability screen ON %s" % json.dumps({k: _TRD_META[k] for k in ("sha256", "window", "n_symbols")}))
    log(f"cache {TT}x{NW}x{CD.shape[2]} ts {CTS[0]}..{CTS[-1]}")
    assert np.all(np.diff(CTS) == 300), "缓存 ts 非等距 300s"
    r5 = CD[:, :, 0].astype(np.float32)
    fin = np.isfinite(r5)
    r5z = np.where(fin, r5, 0).astype(np.float32)
    qvz = np.where(np.isfinite(CD[:, :, 3]), CD[:, :, 3], 0).astype(np.float32)
    z1 = np.zeros((1, NW))
    CS_f = np.concatenate([z1.astype(np.int32), np.cumsum(fin, 0, dtype=np.int32)])
    CS_r = np.concatenate([z1, np.cumsum(r5z, 0, dtype=np.float64)])
    CS_r2 = np.concatenate([z1, np.cumsum(r5z.astype(np.float64) ** 2, 0)])
    _rt = CD[:, :, RET_CH].astype(np.float32); _rtz = np.where(np.isfinite(_rt), _rt, 0).astype(np.float32)   # target channel only
    assert np.array_equal(np.isfinite(_rt), np.isfinite(CD[:, :, 0])), "target channel finiteness must equal ch0"
    _pp = os.environ.get("DLWT_RAW_PATCH")
    if _pp:
        _P = np.load(_pp); assert RET_CH == 0; _rtz[_P["row"], _P["col"]] = _P["raw32"].astype(np.float32)   # exact float32 raw returns on the clipped bars (PREREG_caliber_program section 3)
        log("raw patch applied: %d bars from %s" % (len(_P["row"]), _pp))
    CS_L = np.concatenate([z1, np.cumsum(np.log1p(_rtz.astype(np.float64)), 0)]); del _rt, _rtz
    CS_q = np.concatenate([z1, np.cumsum(qvz, 0, dtype=np.float64)])
    del r5, r5z, qvz, fin
    log("cumsums done")
    grid = np.where(CTS % 14400 == 0)[0]
    grid = grid[(grid >= W) & (grid + FWD <= TT - 1)]
    # ─────────── FX-MODEL KNOB 1/3, FMT_MEMBER_CLOCK: half-open upper bound of the member-statistic window ───────────
    # legacy_Em1 -> HI = E   -> rows [E-2016, E-1], the bar closing AT the anchor is INVISIBLE (base behaviour)
    # serve_E    -> HI = E+1 -> rows [E-2015, E],   matching shadow_loop_v3.py L365/L371, which the producer serves
    E = grid; HI = E if FMT_MEMBER_CLOCK == "legacy_Em1" else E + 1
    S = np.maximum(HI - TRAIL, 0)
    nfin = np.maximum(CS_f[HI] - CS_f[S], 1)
    covr = (CS_f[HI] - CS_f[S]) / np.maximum(HI - S, 1)[:, None]
    qvm = (CS_q[HI] - CS_q[S]) / nfin
    rs_ = CS_r[HI] - CS_r[S]
    vstd = np.sqrt(np.maximum((CS_r2[HI] - CS_r2[S]) / nfin - (rs_ / nfin) ** 2, 0))
    nb = np.maximum(HI - S, 1).astype(np.float64)
    btcv = np.sqrt(np.maximum((CS_r2[HI, BTC_T] - CS_r2[S, BTC_T]) / nb - ((CS_r[HI, BTC_T] - CS_r[S, BTC_T]) / nb) ** 2, 0))
    # ---- 目标: 行 [E+1, E+48] 复利(结构断言: 起点 E+1)
    lo_t = E + 1; hi_t = E + FWD + 1          # CS 半开区间 [lo_t, hi_t) = rows E+1..E+48
    assert int(lo_t.min() - E.min()) == 1 and np.all(hi_t - 1 - E == FWD) and hi_t.max() <= TT
    y4n = CS_f[hi_t] - CS_f[lo_t]
    y4s = np.expm1(CS_L[hi_t] - CS_L[lo_t]).astype(np.float32)
    y4s[y4n < MIN_FIN] = np.nan
    # 旧口径 y4(对照/对齐自检用, 不入任何训练): rows [E, E+47] 简单和
    y4old = (CS_r[E + FWD] - CS_r[E]).astype(np.float32); y4old[(CS_f[E + FWD] - CS_f[E]) < MIN_FIN] = np.nan
    del CS_f, CS_r, CS_r2, CS_L, CS_q, rs_
    MS, keep = [], []
    for i in range(len(E)):
        # ───── FX-MODEL KNOB 2/3, FMT_FORWARD_TERM ─────
        # legacy_isfinite: membership requires a finite FORWARD label, so a property of the future decides whether a
        #   row is trained on (red test R-TRD-1 demonstrates it interventionally). This is TRN-06 channel B.
        # trailing_only:  no forward term, matching production (shadow_loop_v3.py L374). NOTE the coupling recorded in
        #   FACT_TABLE_MODEL §5.2: removing the forward term INCREASES the number of dead-but-kept rows (channel A),
        #   which is what KNOB 3 is for. They are reported jointly, never summed.
        ok = (covr[i] >= 0.95) & (vstd[i] >= 1e-4)
        if FMT_FORWARD_TERM == "legacy_isfinite":
            ok = ok & np.isfinite(y4s[i])
        # ───── FX-MODEL KNOB 3/3, FMT_TRADABLE ─────
        # off: base behaviour. <path>: admit only names whose decision state at THIS anchor is TRADABLE (== 2), using
        #   FX-DATA's pinned artifact. Per FXR-DATA-1 this is a labelled ADMISSION SCREEN built from past activity --
        #   it is not a settlement truth, and exit P&L for a dead contract stays explicitly unknown.
        if _TRD_STATE is not None:
            _r = _TRD_ROW.get(int(CTS[E[i]]))
            ok = ok & (_TRD_STATE[_r][_TRD_COL] == 2) if _r is not None else ok & False
        m = np.where(ok)[0]
        if len(m) > NTOP:
            m = np.sort(m[np.argsort(-qvm[i, m])[:NTOP]])
        if len(m) >= MIN_MEM:
            MS.append(m); keep.append(i)
    keep = np.array(keep)
    E = E[keep]; y4s = y4s[keep]; y4old = y4old[keep]; qvk = qvm[keep].astype(np.float32); btcv = btcv[keep].astype(np.float32)
    E_ts = CTS[E]
    yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts])
    nA = len(E); memn = np.array([len(m) for m in MS])
    log(f"anchors {nA} 平均成员 {memn.mean():.0f} (≥360: {(memn>=360).sum()}) 年份 {dict(zip(*np.unique(yrs, return_counts=True)))}")
    # ---- 残差目标(六因子, 面板锚行 ts = N)
    PW = np.load(PANEL, allow_pickle=True)
    assert [str(s) for s in PW["symbols"]] == syms, "面板符号顺序 ≠ 缓存"
    pw_ts = PW["ts"].astype(np.int64); pw_row = {int(t): j for j, t in enumerate(pw_ts)}
    F6 = [PW[k].astype(np.float32) for k in F6_KEYS]; PY4 = PW["Y4"].astype(np.float32)
    YR4s = np.full((nA, NW), np.nan, np.float32); YRZ = np.full((nA, NW), np.nan, np.float32)
    has_panel = np.zeros(nA, bool); n_res = 0; r2s = []
    for i in range(nA):
        j = pw_row.get(int(E_ts[i]))
        if j is None:
            continue
        has_panel[i] = True
        m = MS[i]; y = y4s[i, m].astype(np.float64)
        X = np.zeros((len(m), 6))
        for c in range(6):
            X[:, c], _ = xz(F6[c][j, m])
        okrow = np.isfinite(y)
        if okrow.sum() < MIN_RES:
            continue
        Xo, yo = X[okrow], y[okrow]
        beta = np.linalg.solve(Xo.T @ Xo + LAM * np.eye(6), Xo.T @ yo)
        res = yo - Xo @ beta
        YR4s[i, m[okrow]] = res.astype(np.float32); n_res += 1
        vy = yo.var(); r2s.append(1 - res.var() / vy if vy > 0 else np.nan)
        rr = rankdata(res); YRZ[i, m[okrow]] = ((rr - (len(rr) + 1) / 2) / max(len(rr) - 1, 1)).astype(np.float32)
    log(f"YR4s 完成 {n_res}/{nA} 锚(有面板行 {has_panel.sum()}), 六因子值空间 R² 中位 {np.nanmedian(r2s):.4f}")
    # ---- 对齐自检: 本装置 y4s(窗 (N,N+4h]) vs 面板 Y4(旧窗 [N−5m,N+3h55m] 对数和) 在同行应 ≫ 相邻行
    chk = {-1: [], 0: [], 1: []}
    for i in range(60, nA - 60, max(nA // 200, 1)):
        j = pw_row.get(int(E_ts[i]))
        if j is None or j - 1 < 0 or j + 1 >= len(pw_ts):
            continue
        m = MS[i]
        for off in (-1, 0, 1):
            chk[off].append(spear(y4s[i, m], PY4[j + off, m]))
    c0, cm, cp = (float(np.nanmedian(chk[o])) for o in (0, -1, 1))
    log(f"对齐自检(y4s vs 面板旧 Y4): @0 {c0:+.3f} @-1 {cm:+.3f} @+1 {cp:+.3f} (n={len(chk[0])})")
    assert c0 > 0.8 and c0 > cm and c0 > cp, "对齐自检 FAIL"
    # 新旧目标差(同锚同名): 量级记录
    d = (y4s - y4old)
    rep["target_vs_old"] = {"median_abs_diff_bps": float(np.nanmedian(np.abs(d)) * 1e4), "mean_diff_bps": float(np.nanmean(d) * 1e4),
                            "spearman_same_row_median": c0, "spearman_prev_row": cm, "spearman_next_row": cp}
    meta = dict(rep["const"], n_anchors=int(nA), mean_members=float(memn.mean()), n_has_panel=int(has_panel.sum()), n_res=int(n_res),
                years={str(k): int(v) for k, v in zip(*np.unique(yrs, return_counts=True))}, cache=CACHE, panel=PANEL)
    meta["fm_knobs"] = {"FMT_MEMBER_CLOCK": FMT_MEMBER_CLOCK, "FMT_FORWARD_TERM": FMT_FORWARD_TERM,
                        "FMT_TRADABLE": FMT_TRADABLE}
    meta["fm_tradability"] = _TRD_META
    meta["fm_base"] = {"file": "v4_chain_2026-09-09/pod_dlw_targets_raw.py",
                       "sha256": "d7c528231f00902964c5244fe8402bbd84688af05c04c2dab8760fe8ad584be2",
                       "note": "copied from the COMMITTED blob, byte-for-byte, then three knobs added. FX-TRAIN has an "
                               "in-flight TRN-02 raw-patch-coverage change to the same base in the working tree "
                               "(4568bea6063fd21f); it is orthogonal to these knobs (patch verification, not the member "
                               "screen) and must be reconciled before either goes to the October chain."}
    meta["fm_member_stat_window"] = "[E-2016, E-1]" if FMT_MEMBER_CLOCK == "legacy_Em1" else "[E-2015, E]"
    np.savez(f"{OUT}/data/dlw_targets.npz", E_ts=E_ts, E_row=E, members=np.array(MS, dtype=object), y4s=y4s, YR4s=YR4s, YRZ=YRZ,
             yrs=yrs, qvk=qvk, btcv=btcv, has_panel=has_panel, symbols=np.array(syms), y4old=y4old, meta_json=json.dumps(meta))
    rep.update(meta); rep["targets_sha256"] = sha(f"{OUT}/data/dlw_targets.npz")
    rep["assert"] = {"min_target_row_offset": 1, "max_target_row_offset": FWD, "ts_step_300": True, "align_check_pass": True}
    json.dump(rep, open(f"{OUT}/results/dlw_targets_report.json", "w"), indent=1)
    log("TARGETS_DONE", json.dumps({k: rep[k] for k in ("n_anchors", "mean_members", "n_res", "years", "target_vs_old")}))


if __name__ == "__main__":
    main()
