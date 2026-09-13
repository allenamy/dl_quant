#!/usr/bin/env python3
"""t4_live_judge.py — Mac, read-only (PREREG_T4 §6). Gates PC1 / PC-INJ / ONE-PLACE / V0P / V1R / C81 and the per-anchor
live-window deltas of arm v0 versus arm served (41 chained anchors 2026-09-05 16Z .. 09-12 08Z). Descriptive only; no verdict.
Launch: env -i PATH=/usr/bin:/bin HOME=/Users/haosiyu /Users/haosiyu/wide_shadow/venv/bin/python -B devices/t4_live_judge.py <whitelist>"""
import os, sys, json, time, hashlib
WHITE = set(x for x in sys.argv[1].split(",") if x) if len(sys.argv) > 1 else None
assert WHITE, "whitelist argv[1]"
assert sorted(k for k in os.environ if k not in WHITE) == [], ("ENV WHITELIST VIOLATION", sorted(os.environ))
import numpy as np
from scipy.stats import rankdata
HERE = os.path.dirname(os.path.abspath(__file__)); T4 = os.path.dirname(HERE); PRIV = T4 + "/private"
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
PREREG_SHA = "0f94b754c9ca4c6e65c3f2a63146dab7036f37862abd2210cbbfcef661aab4dd"; assert sha(T4 + "/PREREG_T4_king_feature_skew_2026-09-13.md") == PREREG_SHA
ANCH = list(range(1788624000, 1789200000 + 1, 14400)); A0, A1 = ANCH[0], ANCH[-1]
CFG = json.load(open("/Users/haosiyu/wide_shadow/shadow_bundle/config.json")); SYMS = CFG["symbols_panel"]; JOF = {s: j for j, s in enumerate(SYMS)}; KEEP = CFG["keep_idx"]
assert KEEP.index(80) == 76 and KEEP.index(81) == 77
REC = {a: list(np.load(PRIV + f"/replay_rec_{a}.npy", allow_pickle=True)) for a in ("served", "v0", "v1inj")}
RCP = {a: json.load(open(T4 + f"/receipts/T4_REPLAY_{a}_{A0}_{A1}.json")) for a in ("served", "v0", "v1inj")}
for a in REC: assert [int(r["anchor"]) for r in REC[a]] == ANCH, (a, "anchor list")
assert RCP["served"]["device_file_sha256"].startswith("4d3bc157") and RCP["v0"]["device_file_sha256"].startswith("0fff8406") and RCP["v1inj"]["device_file_sha256"].startswith("0fff8406")
FEED = np.load(PRIV + "/v0_feed.npz", allow_pickle=True); assert sha(PRIV + "/v0_feed.npz") == RCP["v0"]["v0_feed_sha256"]; FA = {int(a): i for i, a in enumerate(FEED["anchors"])}
X10 = np.load(PRIV + "/pod2_inputs/x0910_live_window.npz", allow_pickle=True); assert sha(PRIV + "/pod2_inputs/x0910_live_window.npz") == "fa284e5b0f22deb20d52aba75416fc96ddeab4ab7805e396e720df78194409d9"
assert [str(s) for s in X10["panel_symbols"]] == SYMS and [str(s) for s in X10["targets_symbols"]] == SYMS
PROW = {int(t): k for k, t in enumerate(X10["panel_ts"])}; MROW = {int(t): k for k, t in enumerate(X10["meta_ts"])}
GATES = {}
# ---------------- PC1: served still reproduces live
k_linf = [a["weights_npz_Linf"] for a in RCP["served"]["anchors"]]; c_linf = [(a.get("combo") or {}).get("target_live_Linf") for a in RCP["served"]["anchors"]]
GATES["PC1"] = dict(king_Linf_max=float(max(k_linf)), king_pass_anchors=int(sum(x <= 1e-6 for x in k_linf)), combo_target_live_Linf_max=float(max(c_linf)), combo_pass_anchors=int(sum((x is not None and x <= 2e-4) for x in c_linf)),
                    combo_rc=[(a.get("combo") or {}).get("rc") for a in RCP["served"]["anchors"]], lr_entry_max_abs_diff=float(max((a.get("lr_entry_max_abs_diff") or 0.0) for a in RCP["served"]["anchors"])))
GATES["PC1"]["PASS"] = bool(GATES["PC1"]["king_pass_anchors"] >= 0.95 * 41 and GATES["PC1"]["combo_pass_anchors"] == 41)
v0_combo_rc = [(a.get("combo") or {}).get("rc") for a in RCP["v0"]["anchors"]]; assert all(r == 0 for r in v0_combo_rc) and all(r == 0 for r in GATES["PC1"]["combo_rc"]), (v0_combo_rc, GATES["PC1"]["combo_rc"])
# ---------------- PC-INJ: v1inj (injection path fed the device's own EMA) == served, bitwise
def jw(arm, sub, A): return json.load(open(PRIV + f"/replay_home_{arm}/state/{sub}/{A}.json"))["weights"]
inj = dict(X_bitwise=True, pred_bitwise=True, king_npz_bitwise=True, king_target_json_bitwise=True, first_failure=None)
for k, A in enumerate(ANCH):
    s_, i_ = REC["served"][k], REC["v1inj"][k]
    ok = dict(X_bitwise=bool(np.array_equal(s_["X"], i_["X"])), pred_bitwise=bool(np.array_equal(s_["pred"], i_["pred"])),
              king_npz_bitwise=bool(np.array_equal(s_["king_idx"], i_["king_idx"]) and np.array_equal(s_["king_val"], i_["king_val"])), king_target_json_bitwise=bool(jw("served", "target_live", A) == jw("v1inj", "target_live", A)))
    for kk, v in ok.items():
        if not v:
            inj[kk] = False
            if inj["first_failure"] is None: inj["first_failure"] = [A, kk]
GATES["PC_INJ"] = inj; GATES["PC_INJ"]["PASS"] = all(inj[k] for k in ("X_bitwise", "pred_bitwise", "king_npz_bitwise", "king_target_json_bitwise"))
# ---------------- ONE-PLACE
mk = json.load(open(T4 + "/receipts/RECEIPT_T4_mk_v0col80_device.json"))
one = dict(diff_changed_lines=mk["diff_changed_lines"], members_equal_all=True, X_other_cols_bitwise_all=True, pred_equal_where_col76_equal_all=True, rows_col76_equal=0, rows_total=0, rows_col76_differ=0)
for k, A in enumerate(ANCH):
    s_, v_ = REC["served"][k], REC["v0"][k]
    if not np.array_equal(s_["members"], v_["members"]): one["members_equal_all"] = False; continue
    oth = [c for c in range(78) if c != 76]
    if not np.array_equal(s_["X"][:, oth], v_["X"][:, oth]): one["X_other_cols_bitwise_all"] = False
    eq = s_["X"][:, 76] == v_["X"][:, 76]; one["rows_col76_equal"] += int(eq.sum()); one["rows_total"] += int(len(eq)); one["rows_col76_differ"] += int((~eq).sum())
    if not np.array_equal(s_["pred"][eq], v_["pred"][eq]): one["pred_equal_where_col76_equal_all"] = False
GATES["ONE_PLACE"] = one; GATES["ONE_PLACE"]["PASS"] = bool(one["diff_changed_lines"] == 1 and one["members_equal_all"] and one["X_other_cols_bitwise_all"] and one["pred_equal_where_col76_equal_all"])
# ---------------- V0P / V1R / C81
def relcmp(a, b, absfloor=1e-7, absthr=1e-9):
    a = np.asarray(a, float); b = np.asarray(b, float); small = np.abs(b) < absfloor
    rel = np.where(small, np.nan, np.abs(a - b) / np.where(small, 1.0, np.abs(b)))
    big = ~small
    return dict(n=int(len(a)), n_rel=int(big.sum()), median_rel=float(np.median(rel[big])) if big.any() else None, share_rel_le_1e3=float((rel[big] <= 1e-3).mean()) if big.any() else None,
                share_rel_le_1e6=float((rel[big] <= 1e-6).mean()) if big.any() else None, max_rel=float(rel[big].max()) if big.any() else None, n_small=int(small.sum()), small_abs_le_thr=int((np.abs(a - b)[small] <= absthr).sum()))
v0p_a, v0p_b, v1r_a, v1r_b, c81_a, c81_b = [], [], [], [], [], []; v1r_names = {}; v0p_names = {}
for k, A in enumerate(ANCH):
    s_ = REC["served"][k]; m = s_["members"]; fresh = s_["X"][:, 76] != 0.0
    fv = FEED["V0"][FA[A]][m]; f1 = FEED["V1R"][FA[A]][m]
    v1r_a.append(f1[fresh]); v1r_b.append(s_["X"][fresh, 76].astype(np.float64))
    bad = np.abs(np.float32(f1[fresh]) - s_["X"][fresh, 76]) > 1e-3 * np.abs(s_["X"][fresh, 76])
    for jj in m[fresh][bad]: v1r_names[SYMS[jj]] = v1r_names.get(SYMS[jj], 0) + 1
    p = PROW.get(A)
    if p is not None:
        pe = X10["f_fund_ema"][p][m].astype(np.float64); pn = X10["f_fund_now"][p][m].astype(np.float64)
        okp = fresh & np.isfinite(pe); v0p_a.append(fv[okp]); v0p_b.append(pe[okp])
        badp = np.abs(fv[okp] - pe[okp]) > 1e-3 * np.abs(pe[okp])
        for jj in m[okp][badp & (np.abs(pe[okp]) >= 1e-7)]: v0p_names[SYMS[jj]] = v0p_names.get(SYMS[jj], 0) + 1
        okn = np.isfinite(pn) & (s_["X"][:, 77] != 0.0); c81_a.append(s_["X"][okn, 77].astype(np.float64)); c81_b.append(pn[okn])
V0P = relcmp(np.concatenate(v0p_a), np.concatenate(v0p_b)); V0P["anchors"] = int(sum(1 for A in ANCH if A in PROW)); V0P["names_over_1e3"] = dict(sorted(v0p_names.items(), key=lambda x: -x[1])[:25])
V0P["PASS"] = bool(V0P["median_rel"] is not None and V0P["median_rel"] <= 1e-4 and V0P["share_rel_le_1e3"] >= 0.95)
V1R = relcmp(np.float32(np.concatenate(v1r_a)), np.concatenate(v1r_b)); V1R["names_over_1e3"] = dict(sorted(v1r_names.items(), key=lambda x: -x[1])[:25])
V1R["PASS"] = bool(V1R["median_rel"] is not None and V1R["median_rel"] <= 1e-4 and V1R["share_rel_le_1e3"] >= 0.95)
C81 = relcmp(np.concatenate(c81_a), np.concatenate(c81_b)); C81["PASS"] = bool(C81["share_rel_le_1e6"] is not None and C81["share_rel_le_1e6"] >= 0.99)
GATES.update(V0P=V0P, V1R=V1R, C81=C81)
# ---------------- per-anchor deltas (v0 vs served)
def spear(a, b):
    ra = rankdata(a); rb = rankdata(b); ra -= ra.mean(); rb -= rb.mean(); den = np.sqrt((ra * ra).sum() * (rb * rb).sum()); return float((ra * rb).sum() / den) if den > 0 else float("nan")
def dec(x): n = len(x); r = rankdata(x); return np.minimum(9, np.floor(10 * (r - 0.5) / n)).astype(np.int8)
def wstats(w0, w1):
    keys = sorted(set(w0) | set(w1)); a = np.array([w0.get(k, 0.0) for k in keys]); b = np.array([w1.get(k, 0.0) for k in keys]); G0 = np.abs(a).sum(); G1 = np.abs(b).sum()
    return dict(Linf=float(np.abs(a - b).max()), L1=float(np.abs(a - b).sum()), L1_norm=float(np.abs(a / G0 - b / G1).sum()), gross_v0=float(G0), gross_served=float(G1), net_v0=float(a.sum()), net_served=float(b.sum()),
                n_v0=int((a != 0).sum()), n_served=int((b != 0).sum()), corr=float(np.corrcoef(a, b)[0, 1])), keys, a, b
ROWS = []; DG = []
for k, A in enumerate(ANCH):
    s_, v_ = REC["served"][k], REC["v0"][k]; iv = s_["iv_last"]
    rho = spear(v_["pred"], s_["pred"]); ch = dec(v_["pred"]) != dec(s_["pred"])
    cls = {"all": np.ones(len(iv), bool), "4h": iv == 4.0, "1h": iv == 1.0, "8h": iv == 8.0}
    decs = {c: dict(n=int(msk.sum()), changed=int(ch[msk].sum())) for c, msk in cls.items()}
    ksw, _, _, _ = wstats(jw("v0", "target_live", A), jw("served", "target_live", A))
    csw, keys, a, b = wstats(jw("v0", "target_live_combo", A), jw("served", "target_live_combo", A))
    row = dict(anchor=A, utc=time.strftime("%Y-%m-%d %HZ", time.gmtime(A)), king_score_spearman=rho, decile_change=decs, col76_rows_differ=int((s_["X"][:, 76] != v_["X"][:, 76]).sum()), members=int(len(iv)),
               king_target=ksw, combo_target_live=csw, w3m_v0=v_.get("w3_masked"), w3m_served=s_.get("w3_masked"), w3_v0=list(map(float, v_["w3"])), w3_served=list(map(float, s_["w3"])), ftrim_v0=v_.get("ftrim_n"), ftrim_served=s_.get("ftrim_n"))
    mr = MROW.get(A)
    if mr is not None:
        y = X10["meta_y4s"][mr]; yk = np.array([y[JOF[s]] if s in JOF else np.nan for s in keys], float); dw = a / np.abs(a).sum() - b / np.abs(b).sum()
        cov = np.isfinite(yk); row["price_dg_bps_descriptive"] = float(1e4 * (dw[cov] * yk[cov]).sum()); row["price_dg_uncovered_absdw_share"] = float(np.abs(dw[~cov]).sum() / max(np.abs(dw).sum(), 1e-300))
        DG.append((A, row["price_dg_bps_descriptive"]))
    ROWS.append(row)
def summ(vals): v = np.array(vals, float); return dict(median=float(np.median(v)), max=float(v.max()), min=float(v.min()), mean=float(v.mean()))
SUMMARY = dict(king_score_spearman=summ([r["king_score_spearman"] for r in ROWS]),
               decile_change_share={c: float(sum(r["decile_change"][c]["changed"] for r in ROWS) / max(sum(r["decile_change"][c]["n"] for r in ROWS), 1)) for c in ("all", "4h", "1h", "8h")},
               decile_cells={c: int(sum(r["decile_change"][c]["n"] for r in ROWS)) for c in ("all", "4h", "1h", "8h")},
               king_target_Linf=summ([r["king_target"]["Linf"] for r in ROWS]), king_target_L1_norm=summ([r["king_target"]["L1_norm"] for r in ROWS]),
               combo_target_live_Linf=summ([r["combo_target_live"]["Linf"] for r in ROWS]), combo_target_live_L1_norm=summ([r["combo_target_live"]["L1_norm"] for r in ROWS]),
               combo_target_live_corr=summ([r["combo_target_live"]["corr"] for r in ROWS]), combo_gross_ratio_v0_over_served=summ([r["combo_target_live"]["gross_v0"] / r["combo_target_live"]["gross_served"] for r in ROWS]),
               w3m_king_v0_minus_served=summ([r["w3m_v0"][0] - r["w3m_served"][0] for r in ROWS]))
if DG:
    d = np.array([x[1] for x in DG]); days = np.array([time.strftime("%Y%m%d", time.gmtime(x[0])) for x in DG]); ud = sorted(set(days)); tot = np.array([d[days == u].sum() for u in ud]); cnt = np.array([(days == u).sum() for u in ud], float)
    r = np.stack([np.random.default_rng([20260905, k]).integers(0, len(ud), len(ud)) for k in range(2000)]); ms = tot[r].sum(1) / cnt[r].sum(1)
    SUMMARY["price_dg_descriptive"] = dict(n_anchors=int(len(d)), n_days=len(ud), mean=float(d.mean()), ci95=[float(np.percentile(ms, 2.5)), float(np.percentile(ms, 97.5))], note="descriptive only: price leg, no carry/cost/execution clock; chained arms diverge")
RC = dict(self_sha256=sha(os.path.abspath(__file__)), prereg_sha256=PREREG_SHA, replay_receipts={a: sha(T4 + f"/receipts/T4_REPLAY_{a}_{A0}_{A1}.json") for a in RCP}, replay_recs={a: sha(PRIV + f"/replay_rec_{a}.npy") for a in REC},
          v0_feed_sha256=sha(PRIV + "/v0_feed.npz"), gates=GATES, summary=SUMMARY, per_anchor=ROWS, env=dict(whitelist=sorted(WHITE), actual={k: os.environ[k] for k in sorted(os.environ)}), numpy=np.__version__,
          built_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
json.dump(RC, open(T4 + "/receipts/RECEIPT_T4_live_judge.json", "w"), indent=1, default=str)
print(json.dumps(dict(gates=GATES, summary=SUMMARY), indent=1, default=str))
assert GATES["PC_INJ"]["PASS"], "PC-INJ FAIL"
assert GATES["ONE_PLACE"]["PASS"], "ONE-PLACE FAIL"
print("DONE_t4_live_judge")
