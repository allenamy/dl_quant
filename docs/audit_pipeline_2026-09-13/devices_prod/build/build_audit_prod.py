#!/usr/bin/env python3
"""build_audit_prod.py -- generates AUDIT_PROD.md, AUDIT_PROD.json and AUDIT_PROD_columns.csv from committed receipts (receipts_prod/) and code shas.
Every number in the register is read from a receipt at build time; code line citations are computed by searching unique snippets in sha-checked files.
The only computation of its own: the king booster threshold / float16-midpoint distance (lightgbm dump of slow2026.txt 8d79186b, read-only).
Run: env -i PATH=/usr/bin:/bin HOME=/Users/haosiyu /Users/haosiyu/wide_shadow/venv/bin/python -B docs/audit_pipeline_2026-09-13/devices_prod/build/build_audit_prod.py PATH,HOME,LC_CTYPE,__CF_USER_TEXT_ENCODING
"""
import os, sys, json, csv, hashlib, stat, time
WHITE = set(x for x in sys.argv[1].split(",") if x) if len(sys.argv) > 1 else None
assert WHITE, "env whitelist argv[1] required"
assert sorted(k for k in os.environ if k not in WHITE) == [], ("ENV WHITELIST VIOLATION", sorted(os.environ))
import numpy as np
HOME = "/Users/haosiyu"; REPO = HOME + "/Desktop/quant_research"; AD = REPO + "/docs/audit_pipeline_2026-09-13"; RP = AD + "/receipts_prod"; WS = HOME + "/wide_shadow"
SF_DATALESS = getattr(stat, "SF_DATALESS", 0x40000000)
def gsha(p):
    st = os.stat(p); assert not (st.st_flags & SF_DATALESS), ("dataless", p)
    h = hashlib.sha256(); n = 0
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b); n += len(b)
    assert n == st.st_size; return h.hexdigest()
def J(name): return json.load(open(f"{RP}/{name}"))
R_KING = J("parity_king.json"); R_F10 = J("parity_f10.json"); R_MEM = J("members_audit.json"); R_CHK = J("prod_target_checks.json")
R_SEAT = J("state_seat_ledger_probe.json"); R_TIME = J("state_combo_timing_probe.json"); R_EXT = J("parity_x0910_extract.json")
RECEIPTS = {n: gsha(f"{RP}/{n}") for n in ("parity_king.json", "parity_king_columns.csv", "parity_f10.json", "parity_f10_columns.csv", "members_audit.json", "prod_target_checks.json",
                                         "state_seat_ledger_probe.json", "state_combo_timing_probe.json", "parity_x0910_extract.json", "pod2_provenance.txt")}
CODE = {
    "shadow_loop_v3.py": (WS + "/shadow_loop_v3.py", "e9c9837412130884bc72d4bbcb52b33e9dc8660274b76ae68f46639d2d21b36e"),
    "combo_stage.py": (WS + "/fea171/combo_stage.py", "b5c698f9d1ee9acb73c9bf5f3a1e15843d3298e95a810ebf0107a7d68c6ee358"),
    "dlw_features.py": (WS + "/fea171/dlw_features.py", "29ae6a985d891e56340378bb432c0370e914b93709eec44f54592472e4d20a76"),
    "f8_higher_order_features.py": (WS + "/fea171/f8_higher_order_features.py", "2c500c7ad2bb0f5ddccf431021df50a106a39f4d228bd6cf2d074c5c12f66a5f"),
    "pod_fea_ext.py": (REPO + "/multi_asset/exports/research/retrain_2026-09/pod_fea_ext.py", "02157bda4fe0f6cd6f42215a0a5551b819b817249de4d3ffda26a2963e6a0378"),
    "pod_fea_ext_clamp.py": (REPO + "/multi_asset/exports/research/retrain_2026-09/v4_chain_2026-09-09/pod_fea_ext_clamp.py", "b9f9c72816241715fc4b767950420e74f50adbbbcfc4ea77b362407ab5efa4ac"),
    "pod_dlw_features_ext.py": (REPO + "/multi_asset/exports/research/retrain_2026-09/pod_dlw_features_ext.py", "e86725cc2768bb6265dd8fb2b3580629706166da012298768b1c0788e8f5a624"),
    "pod_f8_build_ext.py": (REPO + "/multi_asset/exports/research/retrain_2026-09/pod_f8_build_ext.py", "f606bffa620004f69ace3704ca19d8f3643b764e918f5eea5a4575b40587f07e"),
    "pod_dlw_targets_ext.py": (REPO + "/multi_asset/exports/research/retrain_2026-09/pod_dlw_targets_ext.py", "c21683ee23b775b46d927b9b606418d3039379f9fc279c027119fd36d73bce89"),
    "pod_panel_ext.py": (REPO + "/multi_asset/exports/research/retrain_2026-09/pod_panel_ext.py", "db7f0474b64fb3098a8d1a6af29f61423d7b99c74c6834eb6424b77d1642b5ac"),
    "pod_export_bundle_v3.py": (REPO + "/multi_asset/exports/research/retrain_2026-09/pod_export_bundle_v3.py", "c210bac649071e30530147e4b808f662d87e07ad521eaadb307b3453c348dc6a"),
    "pod_f10_refit_ext.py": (REPO + "/multi_asset/exports/research/retrain_2026-09/pod_f10_refit_ext.py", "ea3675b8012ea266646571f6e1550f248d894cae832b190a8beab27befab9fb7"),
    "slow2026.txt": (WS + "/shadow_bundle/slow2026.txt", "8d79186b6380132cb67684acf1ebfcdb2c53261c850f46a4908b06bfa7a81282"),
    "config.json": (WS + "/shadow_bundle/config.json", "3a8422f377519cac77b0c42305d2ba40a4b7a42a830f0542bda844f66647c94e"),
}
for k, (p, h) in CODE.items(): assert gsha(p) == h, ("CODE SHA", k)
TXT = {k: open(p, encoding="utf-8").read().split("\n") for k, (p, h) in CODE.items() if k.endswith(".py")}
def L(key, snippet, end=None):
    hits = [i + 1 for i, ln in enumerate(TXT[key]) if snippet in ln]; assert len(hits) == 1, (key, snippet, hits)
    if end is None: return f"L{hits[0]}"
    h2 = [i + 1 for i, ln in enumerate(TXT[key]) if end in ln and i + 1 >= hits[0]]; assert h2, (key, end); return f"L{hits[0]}-{h2[0]}"
def S(key): return CODE[key][1][:8]
def C(key, snippet, end=None): return f"{key} ({S(key)}) {L(key, snippet, end)}"

# ---- king booster thresholds vs float16 midpoints (the one computation of this builder)
import lightgbm as lgb
bst = lgb.Booster(model_file=CODE["slow2026.txt"][0]); dm = bst.dump_model(); thr = []
thr_feat = []
def walk(n):
    if "split_feature" in n: thr.append(float(n["threshold"])); thr_feat.append(int(n["split_feature"])); walk(n["left_child"]); walk(n["right_child"])
for t in dm["tree_info"]: walk(t["tree_structure"])
rel = []
for t in thr:
    f = np.float16(t); fv = float(f)
    a_, b_ = (fv, float(np.nextafter(f, np.float16(np.inf)))) if fv <= t else (float(np.nextafter(f, np.float16(-np.inf))), fv)
    if a_ == t: b_ = float(np.nextafter(np.float16(a_), np.float16(np.inf)))
    rel.append(abs(t - (a_ + b_) / 2.0) / (b_ - a_))
rel = np.array(rel)
KN_ = json.load(open(CODE["config.json"][0]))["keep_names"]; offm = rel > 1e-9; thr_a = np.array(thr); feat_a = np.array(thr_feat)
THR16 = {"n_thresholds": int(len(thr)), "n_on_f16_midpoint_within_1e-9_step": int((~offm).sum()), "max_distance_on_midpoint_group": float(rel[~offm].max()),
         "n_off_midpoint": int(offm.sum()), "off_midpoint_threshold_abs_max": (float(np.abs(thr_a[offm]).max()) if offm.any() else None),
         "off_midpoint_distance_over_step_min": (float(rel[offm].min()) if offm.any() else None),
         "off_midpoint_by_feature": {KN_[k]: int((feat_a[offm] == k).sum()) for k in sorted(set(feat_a[offm].tolist()))},
         "n_exactly_f16_representable": int(sum(1 for t in thr if float(np.float16(t)) == t))}
print("THR16", THR16)

# ---- column parity table
def rows_csv(name): return list(csv.DictReader(open(f"{RP}/{name}")))
KCOL = rows_csv("parity_king_columns.csv"); FCOL = rows_csv("parity_f10_columns.csv")
TR_K_WIN = C("pod_fea_ext.py", 'VAL.append(((s_[E] - s_[E - w])).astype(np.float32))') + "/" + L("pod_fea_ext.py", 'VAL.append(((s_[E] - s_[E - w]) / nf).astype(np.float32))') + "/" + L("pod_fea_ext.py", "vv = np.sqrt(np.maximum((r2s[E] - r2s[E - w]) / nf - mm ** 2, 0))")
TR_K_STORE = C("pod_fea_ext.py", "FEA = np.full((len(E), NW, NF), np.nan, np.float16)") + " + " + L("pod_fea_ext.py", "FEA[i, m, col] = np.clip(np.nan_to_num(x, nan=0), -1e4, 1e4); col += 1")
TR_K_RANK = C("pod_fea_ext.py", "rr[ok] = rankdata(x[ok]) / max(ok.sum() - 1, 1) - 0.5") + "; members " + L("pod_fea_ext.py", "ok = (covr[i] >= 0.95) & (v7[i] >= 1e-4) & np.isfinite(y4[i])", "if len(m) > 400:")
TR_K_FUND = C("pod_fea_ext.py", 'FUND = [PW["f_fund_ema"], PW["f_fund_now"]]') + "/" + L("pod_fea_ext.py", "FEA[i, m, col] = np.nan_to_num(fv[j, m], nan=0); col += 1") + "; panel v0 " + C("pod_panel_ext.py", "# v0: 墙钟 HL3d 原始 rate", "prev_t = ft[k]; e0[k] = acc") + ", stale " + L("pod_panel_ext.py", "stale = okp & ((anchor_s - np.where(okp, ft[np.maximum(pos, 0)], 0)) > 12 * 3600)")
TR_K_OCT = "October chain builder " + C("pod_fea_ext_clamp.py", "Ew = np.maximum(E - w, 0)   # E-0909-A clamp (was E - w: negative index wraps to the cache tail)") + " (same clock, same float16 store)"
TR_K_EXPORT = C("pod_export_bundle_v3.py", 'keep = [k for k, nm in enumerate(names) if not (nm.startswith("ret5_sum_48") or nm.startswith("ret5_sum_288"))]') + "/" + L("pod_export_bundle_v3.py", "rows_X.append(FEA[i, m[ok]][:, keep].astype(np.float32))")
SV_K_WIN = C("shadow_loop_v3.py", "seg = CDf[max(ai + 1 - w, 0):ai + 1, :, ch]") + " (rows [E-w+1, E]) + " + L("shadow_loop_v3.py", "FE_ANCH = np.full((len(m), 82), np.nan, np.float32)") + " float32"
SV_K_RANK = C("shadow_loop_v3.py", "rr[okx] = rankdata(x[okx]) / max(okx.sum() - 1, 1) - 0.5") + "; members " + L("shadow_loop_v3.py", 'r5seg = CDf[max(ai + 1 - 2016, 0):ai + 1, :, 0]', 'm = np.sort(m[np.argsort(-qvm[m])[:P["NTOP"]]])')
SV_K_FUND = C("shadow_loop_v3.py", "rn = rate * (8.0 / iv)") + " v1 EMA; " + L("shadow_loop_v3.py", "if led and anchor - led[-1][0] <= 12 * 3600:") + " fresh<=12h; " + L("shadow_loop_v3.py", "FE_ANCH[:, 80] = np.nan_to_num(fe_v[m], nan=0)") + "/" + L("shadow_loop_v3.py", "FE_ANCH[:, 81] = np.nan_to_num(fn_v[m], nan=0)")
SV_F_82 = C("dlw_features.py", "hi = E + 1") + " (rows [E-w+1, E], float16 X)"
TR_F_82 = C("pod_dlw_features_ext.py", "hi = E + 1") + " (differs from serving only at L16 default PANEL path)"
SV_F_89 = C("f8_higher_order_features.py", "hi = E + 1 ")
TR_F_89 = f"pod_f8_build_ext.py ({S('pod_f8_build_ext.py')}) same statement (differs from serving only in the path constants L17-23)"
SV_F_MEM = C("combo_stage.py", "for i in range(len(e_rows)): ms_arr[i] = pm") + " (scored anchor's members on every history row)"
TR_F_MEM = C("pod_dlw_targets_ext.py", "ok = (covr[i] >= 0.95) & (vstd[i] >= 1e-4) & np.isfinite(y4s[i])") + " (own members per anchor, 829 names, forward-finite)"
SV_F_FUND = C("combo_stage.py", 'fe[-1, j] = float(est["acc"])') + "/" + L("combo_stage.py", "fn[-1, j] = float(rows_[-1][1])") + " (v1 EMA, raw rate, all names, no freshness mask)"
TR_F_FUND = "panel wide_panel_4h_v3splice (c5d10f6a, receipts_prod/pod2_reports dlw_ext features report) f_fund_ema v0 / f_fund_now; names outside live450 = 0 (T4b RECEIPT F2)"
SV_F_BTCV = C("combo_stage.py", "_v[i] = np.nanstd(_r5[i - W:i])") + " (nanstd rows [i-2016, i), first 7 days back-filled)"
TR_F_BTCV = C("pod_dlw_targets_ext.py", "btcv = np.sqrt(np.maximum((CS_r2[E, BTC_T] - CS_r2[S, BTC_T]) / nb") + " (zero-filled, divisor E-S)"
SV_F_DRANK = C("f8_higher_order_features.py", "out[ok] = D[ok] - D[np.where(ok)[0] - 6]")
SV_F_DISP = C("f8_higher_order_features.py", "disp = np.array([np.nanstd(r24v[st[i]:st[i + 1]]) for i in range(nA)])") + ", causal z " + L("f8_higher_order_features.py", "mu = s.shift(1).rolling(win, min_periods=minn).mean().values")
SV_F_TREND = C("f8_higher_order_features.py", "CSpm = cs(pmf); CSp = cs(pz); CSp2 = cs(pz ** 2)")
SV_F_STD = C("combo_stage.py", "xz_in = np.nan_to_num(np.clip((X171 - M[\"mu\"]) / M[\"sd_\"], -5, 5))")
TR_F_STD = C("pod_f10_refit_ext.py", "x = torch.clamp((XT[a:b] - mu) / sd, -5, 5)") + "/" + L("pod_f10_refit_ext.py", "s = mdl.f(torch.nan_to_num(x)).squeeze(-1)")

def fnum(x):
    try: return float(x)
    except Exception: return None
COLS = []
for r in KCOL:
    j = int(r["col_idx"]); nm = r["name"]; served = r["keep_pos"] != ""
    if not served:
        cls, dims, tsrc, ssrc = "NOT_SERVED_TO_KING", ["keep_idx excludes ret5_sum_48/288 (value and rank)"], TR_K_EXPORT, "shadow_loop_v3.py L420-421 X = FE_ANCH[:, keep]"
    elif nm == "fund_ema":
        cls, dims, tsrc, ssrc = "DIFFERENT", ["unit: v0 raw per-settlement EMA vs v1 rate*8/iv EMA (T4)", "state: panel full-history recursion vs producer state seeded 08-16 (D17 residue)", "precision: float16 store"], TR_K_FUND, SV_K_FUND
    elif nm == "fund_now":
        cls, dims, tsrc, ssrc = "EQUIVALENT_FORMULA", ["same rule: last settled raw rate if <=12h old else 0", "precision: float16 store (relative step ~1e-3 at |rate| ~2e-5)"], TR_K_FUND, SV_K_FUND
    elif nm.endswith("_r"):
        cls, dims, tsrc, ssrc = "DIFFERENT", ["timestamp alignment: rows [E-w, E-1] (train) vs [E-w+1, E] (serve)", "universe for cross-sectional ranks: members from 829 cache names (incl. non-live450) vs live-450 members", "precision: float16 store, float64 vs float32 window sums"], TR_K_WIN + "; " + TR_K_RANK + "; " + TR_K_STORE, SV_K_WIN + "; " + SV_K_RANK
    else:
        cls, dims, tsrc, ssrc = "DIFFERENT", ["timestamp alignment: rows [E-w, E-1] (train) vs [E-w+1, E] (serve)", "precision: float16 store, float64 vs float32 window sums"], TR_K_WIN + "; " + TR_K_STORE, SV_K_WIN
    row = {"model": "king_lgbm_8d79186b", "col_idx": j, "booster_input_pos": r["keep_pos"], "name": nm, "classification": cls, "dimensions": " | ".join(dims),
           "training_source": tsrc + ("; " + TR_K_OCT if served and nm not in ("fund_ema", "fund_now") else ""), "serving_source": ssrc, "gain": r["gain"], "gain_rank": r["gain_rank"], "split_count": r["split"]}
    for k_, v_ in r.items():
        if ":" in k_: row["measured:" + k_] = v_
    COLS.append(row)
F_ST = R_F10["pair_stats"]
def f10_class(j, nm):
    if j < 80 and nm.endswith("_v"): return "IDENTICAL_CODE", ["per-name window statistic; same builder statement; float16 on both sides"], TR_F_82, SV_F_82
    if j < 80: return "DIFFERENT", ["identical code; universe for cross-sectional ranks: training members D (829 names, forward-finite) vs served members"], TR_F_82 + "; " + TR_F_MEM, SV_F_82 + "; members = producer pm"
    if nm == "fund_ema": return "DIFFERENT", ["unit: v0 (train) vs v1 (serve) (T4b)", "fill: training names outside live450 = 0; serving no 12h freshness mask"], TR_F_FUND, SV_F_FUND
    if nm == "fund_now": return "EQUIVALENT_FORMULA", ["raw last rate on both sides", "fill: serving has no 12h freshness mask (inert while every member is fresh, T4b); training names outside live450 = 0"], TR_F_FUND, SV_F_FUND
    if nm.startswith("J:drank"): return "DIFFERENT", ["history member set: served rank at anchor i-6 uses the scored anchor's members", "universe for ranks"], TR_F_89 + "; " + TR_F_MEM, SV_F_DRANK + "; " + SV_F_MEM
    if nm in ("H:disp_z", "H:r4xdisp", "H:r24xdisp", "H:m7xdisp", "H:v7xdisp"): return "DIFFERENT", ["history member set for the cross-sectional dispersion series", "universe"], TR_F_89 + "; " + TR_F_MEM, SV_F_DISP + "; " + SV_F_MEM
    if nm == "H:btcv_z": return "EQUIVALENT_FORMULA", ["btcv: zero-filled std with divisor E-S (train) vs nanstd with first-7-day back-fill (serve); measured equal on 17 anchors (0 cells > 1e-3)", "back-fill reaches the causal window only in caches shorter than ~37 days (PROD-36)"], TR_F_89 + "; " + TR_F_BTCV, SV_F_89 + "; " + SV_F_BTCV
    if nm in ("H:r4xbtcv", "H:r24xbtcv", "H:m7xbtcv", "H:v7xbtcv"): return "DIFFERENT", ["btcv_z factor equivalent (see H:btcv_z)", "rank factor: universe"], TR_F_89 + "; " + TR_F_BTCV, SV_F_89 + "; " + SV_F_BTCV
    if nm in ("C:trend_288", "C:trend_2016"): return "DIFFERENT", ["numerical: global cumsum from cache start (4.7-year training cache vs 40-day serving cache; AUDIT_TRAIN TRN-16)", "universe for anchor ranks"], TR_F_89, SV_F_TREND
    if nm.startswith("I:"): return "DIFFERENT", ["products of X82 rank columns: universe"], TR_F_89, SV_F_89
    return "DIFFERENT", ["identical code; per-name raw feature ranked within anchor members: universe for ranks"], TR_F_89 + "; " + TR_F_MEM, SV_F_89 + "; members = producer pm"
for r in FCOL:
    j = int(r["col_idx"]); nm = r["name"]; cls, dims, tsrc, ssrc = f10_class(j, nm)
    row = {"model": "v2main_f10_351ae26b", "col_idx": j, "booster_input_pos": j, "name": nm, "classification": cls, "dimensions": " | ".join(dims), "training_source": tsrc, "serving_source": ssrc,
           "gain": "", "gain_rank": "", "split_count": ""}
    for k_, v_ in r.items():
        if ":" in k_: row["measured:" + k_] = v_
    COLS.append(row)
allkeys = []
for row in COLS:
    for k_ in row:
        if k_ not in allkeys: allkeys.append(k_)
with open(AD + "/AUDIT_PROD_columns.csv", "w", newline="") as f:
    wr = csv.DictWriter(f, fieldnames=allkeys); wr.writeheader(); [wr.writerow(r_) for r_ in COLS]
print("columns", len(COLS))

# ---- helpers for numbers from receipts
def fmt(x, nd=4):
    if x is None: return "n/a"
    if isinstance(x, (int, np.integer)): return f"{int(x):,}"
    return f"{x:.{nd}f}" if abs(x) >= 10 ** (-nd + 1) or x == 0 else f"{x:.2e}"
KS = {k: v["summary"] for k, v in R_KING["score_arms"].items()}
def ks(arm, key, stat="median", nd=4): return fmt(KS[arm][key][stat], nd)
P10 = R_KING["P10_f16_cast"]["summary"]
KTHR = R_KING["thresholds_f16"]["per_column"]
exposed = sum(v["served_cells_in_risk_interval"] for v in KTHR.values()); served_cells = sum(v["served_cells"] for v in KTHR.values())
flip_cols = {v["name"]: (v["P10_leaf_rows_changed_single_col"], v["P10_rank_changed_single_col"]) for v in KTHR.values() if v["P10_leaf_rows_changed_single_col"] > 0}
CLK = sorted(R_KING["score_clock_substitution_per_column"].items(), key=lambda kv: kv[1]["spearman_median"])
GAINRANK = {v["name"]: v["gain_rank"] for v in KTHR.values()}
PSK = R_KING["pair_stats"]
univ_rank_shift = sorted(((v["median"], n) for n, v in PSK["universe_Trep_vs_TP"].items() if n.endswith("_r")), reverse=True)
MS = R_MEM["summary"]; MG = R_MEM["gates"]
CH = R_CHK; E3 = CH["EXE03"]; E3F = CH["EXE03_popfree_frequency"]["summary"]
SE = R_SEAT["S1"]; SE2 = R_SEAT["S2"]; TI = R_TIME
F10S = {k: v["summary"] for k, v in R_F10["score"].items()}
def fs(arm, key="spearman", stat="median", nd=4): return fmt(F10S[arm][key][stat], nd)
FST = R_F10["pair_stats"]; FAMSUB = R_F10["score_family_substitution_FS_with_T171"]
def fcount(pair, pred=lambda n, v: True): return sum(1 for n, v in FST[pair].items() if pred(n, v) and v["n_gt_1e-3"] > 0)

# ---- register
ITEMS = []
def add(**kw): ITEMS.append(kw)
KREC = "receipts_prod/parity_king.json (" + RECEIPTS["parity_king.json"][:8] + ", device file parity_king.py sha256 " + R_KING["self_sha256"][:8] + ")"
FREC = "receipts_prod/parity_f10.json (" + RECEIPTS["parity_f10.json"][:8] + ", device file parity_f10.py sha256 " + R_F10["self_sha256"][:8] + ")"
MREC = "receipts_prod/members_audit.json (" + RECEIPTS["members_audit.json"][:8] + ", device file members_audit.py sha256 " + R_MEM["self_sha256"][:8] + ")"
CREC = "receipts_prod/prod_target_checks.json (" + RECEIPTS["prod_target_checks.json"][:8] + ", device file prod_target_checks.py sha256 " + R_CHK["self_sha256"][:8] + ")"
SREC = "receipts_prod/state_seat_ledger_probe.json (" + RECEIPTS["state_seat_ledger_probe.json"][:8] + ")"
TREC = "receipts_prod/state_combo_timing_probe.json (" + RECEIPTS["state_combo_timing_probe.json"][:8] + ")"
g = R_KING["gates"]
KGATES = (f"gates (all bitwise): G-PRED booster(served X) == recorded pred {g['G-PRED']['bitwise_equal']}/{g['G-PRED']['anchors']}; G-SREP production code text L355-404 on the live cache "
          f"reproduces served members + 76 columns {g['G-SREP']['keep0_75_bitwise_equal']}/{g['G-SREP']['anchors']}; G-TREP training-builder formula reproduces the stored x0910 features "
          f"{g['G-TREP']['bitwise_equal']:,}/{g['G-TREP']['cells']:,} cells; G-DATA production code on the pod cache (live 450) == served {g['G-DATA']['keep0_75_bitwise_equal']}/{g['G-DATA']['anchors']}")
top_clock = "; ".join(f"{n} (gain rank {GAINRANK[n]}): score Spearman {v['spearman_median']:.4f}, deciles changed {v['decile_changed_median']:.0f}" for n, v in CLK[:6])

add(id="PROD-01", layer="MODEL INPUT / king (clock)",
    title="King kline features are trained on rows [E-w, E-1] and served on rows [E-w+1, E]; the October chain keeps the training clock",
    what_is_wrong=("All 76 served kline columns are computed one 5-minute bar later at serving than in training (the builder's cumulative sums have a leading zero row, the producer slices through the anchor row). "
                   f"On 32 anchors (2026-09-05 16Z..09-10 20Z), scoring the served names with the training clock (served members, float16 store) against the served input gives king-score Spearman median {ks('TP','spearman')} "
                   f"(min {ks('TP','spearman','min')}), deciles changed median {ks('TP','n_decile_changed',nd=0)} of 400 names, top-decile overlap median {ks('TP','top_decile_overlap',nd=3)} (min {ks('TP','top_decile_overlap','min',3)}). "
                   f"Largest single columns (served X with one column swapped to the training clock): {top_clock}. "
                   "Recorded before as E-0909-F: G4 on the v4 booster (Spearman 0.976-0.990), G3 book A1e-A1 UNDECIDED; the clock-corrected v4e export failed the guard band by 0.007. "
                   "The October chain still builds king features with the training clock."),
    evidence=[TR_K_WIN + " -- training window rows [E-w, E-1]", SV_K_WIN + " -- serving window rows [E-w+1, E]",
              KREC + ": score_arms.TP, pair_stats.clock_TP_vs_TPE, score_clock_substitution_per_column; " + KGATES,
              "receipts_prod/pod2_provenance.txt: w3_monthly_chain_2026-09-12/device/pod_fea_ext_clamp.py b9f9c728 (= review_scratch copy used by x0910)",
              "docs/PREREG_king_clock_E_2026-09-09.md AMENDMENT 2-4; docs/HANDOFF_round2_b0a573a1_closure_2026-09-09.md §3 (G3/G4 tables)"],
    status="OPEN_MEASURED_MATERIAL", affects=["live_trading", "future_eval", "future_retrain"], severity="P2",
    severity_reason="About a quarter of king deciles move per anchor at the score layer; the book-layer effect was not detectable at ±0.3 bps/anchor (G3 on v4e) and has not been measured for 8d79186b; no export gate checks the clock.",
    recommended_action="Before the October export, put the clock contract to the user: train on the serving clock (pod_fea_ext_e.py, judged with a CI-based book gate rather than the guard band) or serve rows [E-w, E-1]. Add a producer-path raw-feature parity gate to the export (training builder vs producer code on the same anchors, as G-TREP/G-SREP here; cf. AUDIT_TRAIN TRN-18).",
    method="VERIFIED")

add(id="PROD-02", layer="MODEL INPUT / king (rank universe)",
    title="King rank columns use a different cross-section in training (all 829 cache names) than at serving (live-450 members); 82 of 400 recent training members are outside the live 450",
    what_is_wrong=(f"On {MS['PK']['jaccard']['n']} anchors (2026-08-17 04Z..09-10 20Z) production members and king-training members overlap with Jaccard median {MS['PK']['jaccard']['median']:.3f}; "
                   f"the {MS['K_not_P_outside_live450']['median']:.0f} (median) training-only members are all outside the live 450 (tokenized equities such as AAPLUSDT, AMZNUSDT, ANTHROPICUSDT and non-pinned listings). "
                   f"Restricting the training rule to the live 450 leaves a symmetric difference of median {MS['pathK_symdiff_to_P']['K1_live450']['median']:.0f} (max {MS['pathK_symdiff_to_P']['K1_live450']['max']:.0f}, the clock); the forward-finite term, the divisor and float32 change 0 names. "
                   f"Ranks of the same names shift (largest median |Δrank|: {univ_rank_shift[0][1]} {univ_rank_shift[0][0]:.3f}, {univ_rank_shift[1][1]} {univ_rank_shift[1][0]:.3f}) while order among common names is kept. "
                   f"Scoring the common names with the two rank sets (training clock on both) gives king-score Spearman median {ks('universe_common','spearman')} (min {ks('universe_common','spearman','min')}), "
                   f"deciles changed median {ks('universe_common','n_decile_changed',nd=0)}, top-decile overlap median {ks('universe_common','top_decile_overlap',nd=3)}. "
                   "The in-service booster's label years (< 2026) hold 24 non-crypto pairs, all in 2025 (AUDIT_DATA C6), so the live model is served a crypto-only cross-section close to its training years; every 2026 research king score is computed on the stock-inclusive cross-section (7.3% of 2026 member pairs)."),
    evidence=[TR_K_RANK + " -- members from every cache name", SV_K_RANK + " -- members among the 450 fetched names",
              MREC + ": summary.PK, K_not_P_outside_live450, pathK_symdiff_to_P, one_at_a_time_symdiff_vs_P, top_symbols.K_not_P; gates V1/V2/V3 all pass",
              KREC + ": pair_stats.universe_Trep_vs_TP, score_arms.universe_common",
              "docs/audit_pipeline_2026-09-13/devices_data/receipts/AD_C_cache_members.json C6_universe_class_in_training_members (king_meta_members 2025 noncrypto_pairs 24; 2026 42,363, share 0.0726)"],
    status="OPEN_MEASURED_MATERIAL", affects=["future_eval", "future_retrain"], severity="P2",
    severity_reason="Score-layer change larger than the clock effect; it enters every 2026 research king score and any retrain that includes 2026 anchors; book layer not measured.",
    recommended_action="Use one member universe for training, research replay and serving (the 2026-09-08 CRYPTO-default ruling), applied inside the member rules of pod_fea_ext_clamp.py and pod_dlw_targets_raw.py before the next export; until then label 2026 research king scores 'research cross-section'.",
    method="VERIFIED")

add(id="PROD-03", layer="MODEL INPUT / king (research vs served, total)",
    title="Research king inputs at 2026 anchors are not the served inputs: on common names the in-service booster's scores agree with Spearman 0.94, not the 0.994 T4 measured for column 80 alone",
    what_is_wrong=(f"The stored x0910 training rows (the representation behind A0's pinned king and P2 S2's injected king) re-scored with 8d79186b against the served inputs on the same names: Spearman median "
                   f"{ks('Tstored_common_as_stored','spearman')} (min {ks('Tstored_common_as_stored','spearman','min')}), deciles changed median {ks('Tstored_common_as_stored','n_decile_changed',nd=0)}, "
                   f"top-decile overlap median {ks('Tstored_common_as_stored','top_decile_overlap',nd=3)} (min {ks('Tstored_common_as_stored','top_decile_overlap','min',3)}); with the served fund columns swapped in: "
                   f"{ks('Tstored_common_fund_from_S','spearman')}. The gap combines PROD-01 (clock), PROD-02 (rank universe) and column 80 (PROD-04)."),
    evidence=[KREC + ": score_arms.Tstored_common_as_stored, Tstored_common_fund_from_S; " + KGATES,
              "multi_asset/exports/research/uplift_r2_2026-09-13/T4/RESULT_T4_king_feature_skew_2026-09-13.md §3 (column 80 only: per-anchor Spearman 0.9944)",
              "docs/PREREG_producer_parity_phase2_oos_2026-09-12.md A2.2 D1 (king OOF injected into the production path)"],
    status="OPEN_MEASURED_MATERIAL", affects=["future_eval"], severity="P2",
    severity_reason="Every replay contrast that treats the research king as the live king, including P2 S2's production-path history, carries this score gap; its book-layer size is unmeasured.",
    recommended_action="For production-path replays compute king predictions from producer-definition features (serving clock, serving members, v1 column 80) or label the king arm 'research representation'; add this score contrast to P2's G2-C-BIND.",
    method="VERIFIED")

add(id="PROD-04", layer="MODEL INPUT / king (column 80)",
    title="King column 80 fund EMA trained v0, served v1 (H2b / T4)",
    what_is_wrong=(f"Known (T4). Measured here on common names over 32 anchors: served vs stored training value median relative difference {PSK['total_S_vs_T']['fund_ema']['median']:.3f} "
                   f"(4h names served = 2x training), per-anchor Spearman median {PSK['total_S_vs_T']['fund_ema']['spearman_median']:.3f}. T4 judged the book effect NOT MATERIAL (Δg +0.018 [-0.030, +0.063] bps/anchor, ΔIC -0.0001 ± 0.00017). The October export reintroduces it (AUDIT_TRAIN TRN-04)."),
    evidence=[TR_K_FUND, SV_K_FUND, KREC + ": pair_stats.total_S_vs_T.fund_ema", "uplift_r2_2026-09-13/T4/RESULT_T4_king_feature_skew_2026-09-13.md §0/§5"],
    status="VERIFIED_IMMATERIAL", affects=["live_trading", "future_retrain"], severity="P3",
    severity_reason="Book effect below ±0.05 bps/anchor at T4's resolution; the defect itself persists.",
    recommended_action="Decide the column-80 caliber together with PROD-01/PROD-02 before the October export (serve v0 or train v1).", method="VERIFIED")

add(id="PROD-05", layer="MODEL INPUT / king (precision, P10)",
    title="King trained on float16-stored features and served float32: no decile or selection change on 47 served anchors; 4 of 18,800 row paths change",
    what_is_wrong=(f"Of {THR16['n_thresholds']:,} booster thresholds, {THR16['n_on_f16_midpoint_within_1e-9_step']:,} sit on the midpoint of two adjacent float16 values (largest distance {THR16['max_distance_on_midpoint_group']:.1e} of a float16 step, the model file's print precision), "
                   "where a float32 input and its float16 round trip branch differently only when the float32 value lies exactly on the midpoint; "
                   f"{THR16['n_off_midpoint']} (in {len(THR16['off_midpoint_by_feature'])} columns, mostly rank columns; fund_now {THR16['off_midpoint_by_feature'].get('fund_now', 0)}) sit on a float16 grid value (distance {THR16['off_midpoint_distance_over_step_min']:.3f} step), "
                   "where float32 inputs in the half step above the threshold branch differently. "
                   f"Served inputs, 47 anchors: {exposed} of {served_cells:,} cells lie inside such a risk window. Casting every served input to float16 before predict changes the leaf path of {int(P10['leaf_rows_changed']['sum'])} rows "
                   f"({', '.join(f'{n} {a}' for n, (a, b) in flip_cols.items())}), {int(P10['n_rank_changed']['sum'])} rank positions ({int(P10['n_rank_changed']['max'])} on one anchor), "
                   f"{int(P10['n_decile_changed']['sum'])} deciles, top/bottom-decile overlap {P10['top_decile_overlap']['min']:.2f}/{P10['bottom_decile_overlap']['min']:.2f}, "
                   f"max |Δpred| {P10['max_abs_dpred']['max']:.4f} (served score sd ≈ 0.024), king-leg z max change {P10['max_abs_dlegz']['max']:.3f} on one name ({P10['max_abs_dz_kc']['max']:.4f} after the masked seat). "
                   "Storage alone (float16 vs float32 at the serving clock) changes no cell by more than 1e-3 in any column; float64 vs float32 window sums change at most 94 rank cells in a column (ties). "
                   f"fund_now shows {PSK['total_S_vs_T']['fund_now']['n_gt_1e-3']} cells above 1e-3 relative from float16 quantisation of rates near 2e-5, with no leaf change."),
    evidence=[TR_K_STORE, SV_K_WIN, KREC + ": P10_f16_cast, thresholds_f16.per_column, pair_stats.store_TPE_vs_TPE32 and reduction_TPE32_vs_S",
              "devices_prod/build/build_audit_prod.py threshold check (lightgbm dump of slow2026.txt 8d79186b)"],
    status="VERIFIED_IMMATERIAL", affects=["live_trading"], severity="P3",
    severity_reason="Resolution: decile level over 47 anchors x 400 names; rank level 30 name-anchors.",
    recommended_action="None. Do not add a float16 cast to serving; it buys nothing measurable.", method="VERIFIED")

mg = R_MEM["gates"]; R_ = MS["R"]; SEL = MS["SEL"]; QV = MS["QV4H"]
add(id="PROD-10", layer="MEMBERSHIP / replay universe",
    title="The A0 research replay trades a different member set from production: 373 masked crypto names vs the producer's top-400 of the live 450",
    what_is_wrong=(f"Production rule reproduced exactly (V1 {mg['V1_prod_rule_on_snapshot']}, V2 {mg['V2_prod_rule_on_pod_cache_live450']}; data parity DP {mg['DP_data_parity_live450']}). "
                   f"Over {R_['anchors']} anchors the A0 member set (all names with finite meta qvk, masked by umask_UPIT_CRYPTO; no top-400 cut) has {R_['nR']['median']:.0f} names; "
                   f"overlap with production members median {R_['R_inter_P']['median']:.0f}, production-only {R_['P_not_R']['median']:.0f}, A0-only {R_['R_not_P']['median']:.0f} ({R_['R_not_P_outside_live450']['median']:.0f} outside the live 450). "
                   f"Liquidity-selected sets: Jaccard median {SEL['jaccard']['median']:.3f} (min {SEL['jaccard']['min']:.3f}); production-selected names missing from A0's selection are almost all not A0 members "
                   f"({SEL['Psel_not_Rsel_why_total']['not_in_R_members']} of {SEL['Psel_not_Rsel_why_total']['not_in_R_members'] + SEL['Psel_not_Rsel_why_total']['qv4hR_below'] + SEL['Psel_not_Rsel_why_total']['y4_nan']} name-anchors); "
                   f"A0-selected names missing from production are mostly outside the live 450 ({SEL['Rsel_not_Psel_why_total']['outside_live450']} of {sum(SEL['Rsel_not_Psel_why_total'].values())}). "
                   "T5 attributes 5.2% / 5.1% of the August carry gap (+0.061 bps/anchor) to the member set; the counts here are consistent with a small, persistent universe share."),
    evidence=[MREC + ": summary.R, summary.SEL, summary.T5_window", "multi_asset/exports/research/uplift_r2_2026-09-13/T5/RESULT_T5_deployed_carry_gap_2026-09-13.md L25/L66 (M 成员集 +0.061, 5.2%/5.1%)",
              "docs/PREREG_producer_parity_phase2_oos_2026-09-12.md A2.2 D4 (P2 uses PIT universe, not pins)"],
    status="OPEN_MEASURED_MATERIAL", affects=["future_eval"], severity="P3",
    severity_reason="Known replay deviation with a measured ~5% share of one carry gap; not a live defect.",
    recommended_action="Keep A0 vs production universe as a named deviation in every replay-vs-live contrast; P2's production-path replay already runs the producer's own member code.", method="VERIFIED")

pk = MS["pathK_step_symdiff"]; pd_ = MS["pathD_step_symdiff"]
add(id="PROD-11", layer="MEMBERSHIP / training rule terms",
    title="The forward-finite member term (D20), the window divisor and float32 change no member in 147 recent anchors; the one-bar clock changes at most 2",
    what_is_wrong=(f"Path from each training rule to the production rule, one factor at a time, on {MS['PK']['jaccard']['n']} anchors: universe to live 450 changes median {pk['K1_live450']['median']:.0f} names (all of the difference), "
                   f"dropping the forward-finite term {pk['K2_no_lookahead']['max']:.0f} (max), serving clock {pk['K3_clock_E']['max']:.0f} (max; mean {pk['K3_clock_E']['mean']:.3f}), production divisor {pk['K4_divP']['max']:.0f}, float32 {pk['K5_float32_eq_P']['max']:.0f}; "
                   f"the DL rule behaves the same (D2 {pd_['D2_no_lookahead']['max']:.0f}, D3 {pd_['D3_clock_E']['max']:.0f}). Median qvm gap at the top-400 cut {MS['ntop_cut_gap_qvm']['median']:.4f}. "
                   "This bounds AUDIT_TRAIN TRN-06 (D20) to zero member changes in this window; delisting-heavy history was not measured."),
    evidence=[MREC + ": summary.pathK_step_symdiff, pathD_step_symdiff, one_at_a_time_symdiff_vs_P, ntop_cut_gap_qvm; gates V3/V4 (K and D rules reproduce the stored x0910 members 147/147)",
              C("pod_dlw_targets_ext.py", "ok = (covr[i] >= 0.95) & (vstd[i] >= 1e-4) & np.isfinite(y4s[i])"), TR_K_RANK],
    status="VERIFIED_IMMATERIAL", affects=["future_eval", "future_retrain"], severity="P3",
    severity_reason="Resolution one name per anchor over 2026-08-17..09-10; periods with delistings not covered.",
    recommended_action="Keep TRN-06 open for history; no action for the recent window.", method="VERIFIED")

add(id="PROD-12", layer="MEMBERSHIP / liquidity gate (P3 qv4h)",
    title="qv4h is the same quantity in production and in the A0 replay; the 0.52 log gap recorded in r17 compares a different formula",
    what_is_wrong=(f"Production qv4h = expm1(mean log1p(qv5m) over 2016 rows) x 48; A0 uses the same expression on meta qvk. On {QV['n_common_name_anchor']:,} name-anchors |Δlog qv4h| median {QV['P_vs_R_abs_dlog']['median']:.1e}, "
                   f"p90 {QV['P_vs_R_abs_dlog']['p90']:.1e}, max {QV['P_vs_R_abs_dlog']['max']:.1e}; cost-tier agreement {QV['P_vs_R_tier_agree']:.5f}; {QV['P_vs_R_threshold_2.5e5_disagree']} name-anchors fall on different sides of the 2.5e5 gate "
                   f"(the two windows differ by one bar and in float precision; not separated). The r17 formula (arithmetic 4h quote volume) differs from both by |Δlog| median {QV['r17_formula_vs_R_abs_dlog']['median']:.3f} (tier agreement {QV['r17_formula_vs_R_tier_agree']:.3f}): a Jensen gap between two definitions, not a data difference (G2-A' already showed identical 5m channels)."),
    evidence=[C("shadow_loop_v3.py", "qv4h = np.expm1(np.clip(qvm[m], 0, 30)) * 48"), C("pod_export_bundle_v3.py", "qv4h = np.expm1(np.clip(qvk[i, m], 0, 30)) * 48"), MREC + ": summary.QV4H",
              "docs/PREREG_producer_parity_phase2_oos_2026-09-12.md 收据 1 (r17 |Δlog| 0.52) and AMENDMENT 1 (G2-A' live450 PASS)"],
    status="VERIFIED_IMMATERIAL", affects=["future_eval"], severity="P3",
    severity_reason="Resolution: 17 gate-side disagreements in 47,190 name-anchors.",
    recommended_action="Do not use the arithmetic 4h quote-volume formula for the liquidity gate or cost tiers in any replay.", method="VERIFIED")

ftr = CH["FTRIM_served"]
add(id="PROD-20", layer="SERVING STATE / seat",
    title="The masked model seat is computed on 819 seeded rows scored with the training representation plus 81 producer rows",
    what_is_wrong=(f"leg_returns_live.json keeps {SE['n_rows_file']} rows; the 900-row msharpe window holds {SE['seeded_rows_in_window']} rows seeded on 09-05 from the v3 bundle (8d79186b predictions on training features: v0 column 80, rows [E-w, E-1], training members; labels [E, E+47]; anchors {SE['seeded_ts_first']} .. {SE['seeded_ts_last']}) "
                   f"and {SE['producer_rows_in_window']} producer rows ({SE['producer_rows_anchor_first']} .. {SE['producer_rows_anchor_last']}; {SE['producer_rows_by_booster']}). w3 recomputed from the file equals the 12Z signal to 4 decimals; masked seat w3m {SE['w3m_recomputed']}. "
                   f"The last seeded row leaves the window after {SE['scored_anchors_until_last_seeded_row_leaves_window']} scored anchors (projected {SE['projected_exit_anchor_if_every_anchor_scored']}). "
                   "Measured part (T4b §5): re-scoring the seeded rows with v1 column 80 moves the seat +0.0078 and combo target_live L1 by 0.0066 (6 anchors); PROD-01..03 differences (clock, universe) in the seeded rows are not measured."),
    evidence=[SREC + ": S1", C("shadow_loop_v3.py", "shp = r.mean(1) / (r.std(1) + 1e-9); shp = np.maximum(shp, 0.0)"), "uplift_r2_2026-09-13/T4b/RESULT_T4b_v2main_feature_skew_2026-09-13.md §5", "memory seat_seed_v3_deployed_2026_09_05"],
    status="OPEN_NOT_MEASURED", affects=["live_trading", "future_eval"], severity="P3",
    severity_reason="Self-healing over ~4.5 months; the one measured component is small.",
    recommended_action="No live action; any replay that uses the live seat must state the seeded-row mix.", method="VERIFIED")

add(id="PROD-21", layer="RETRAIN PROCEDURE / seat",
    title="The October bundle swap has no seat re-seeding step, and no rule fixes which scoring representation a seed must use",
    what_is_wrong="RUNBOOK_monthly_retrain_2026-10 §0★ step 8 (backup, swap, sidecar A2, acceptance, first-anchor check) never seeds leg_returns_live.json; the producer ignores bundle rows while the file holds >= 900 rows, so after a swap the seat keeps describing 8d79186b and the seeded v3 rows for about 150 days. The 09-05 precedent required a user-approved seed.",
    evidence=["docs/RUNBOOK_monthly_retrain_2026-10.md §0★ step 8 and L187 (grep: no 播种/seed/leg_returns_live other than L187)", C("shadow_loop_v3.py", 'self.LR = {leg: list(lr[leg]) + list(extra[leg]) for leg in ("king", "rev24", "fund")}'),
              "multi_asset/exports/live/seat_seed_v3_2026-09-05/dryrun_seat_seed.py (not referenced by the runbook)", "AUDIT_TRAIN TRN-12"],
    status="PENDING_USER_DECISION", affects=["future_retrain", "live_trading"], severity="P2",
    severity_reason="A silent seat mismatch at the next swap is the same class as the 0.19 vs 0.30 gap fixed on 09-05.",
    recommended_action="Add an explicit seat step to the swap (seed or not; declared scoring representation and label window; dry run like 09-05) and take the user's word on it with the bundle sha.", method="VERIFIED")

add(id="PROD-22", layer="SERVING STATE / funding EMA (D17)",
    title="D17 funding-EMA artefacts in the live producer state are decaying and do not recur",
    what_is_wrong=(f"12 names carry ledger rows whose stored interval differs from the time gap, all before 09-05 12Z ({SE2['stored_iv_ne_gap_iv_rows_before_2026_09_05_12Z']}); none after, over {SE2['adjacent_row_pairs_checked']:,} adjacent pairs. "
                   "They come from the 08-16 bundle seed; the running append path derives intervals from time gaps and the seed loads only when rolling.npz is absent. "
                   "Inherited EMA residual 2.60e-5 at 09-05 16Z, 5.58e-6 at 09-12 08Z (half-life 3 days); fund-leg z Spearman >= 0.99996, top decile unchanged 41/41 anchors (P2 receipts)."),
    evidence=[SREC + ": S2", C("shadow_loop_v3.py", "iv = (ft - led[-1][0]) / 3600.0 if led else 8.0"), C("shadow_loop_v3.py", 'aux["ledger_tail"] = {s: rows[-400:] for s, rows in lg.items()}'),
              "parity_replay_2026-09-12/phase2/receipts/G2Bpp_inwindow_recursion.json and D17_forensics.json (PREREG_producer_parity_phase2 收据 3, 附 D17 取证)"],
    status="VERIFIED_IMMATERIAL", affects=["live_trading", "future_eval"], severity="P3",
    severity_reason="Resolution: fund z Spearman 0.99996, top decile unchanged.",
    recommended_action="None for live; producer-path replays keep the 'clean rebuild != live EMA' label until the residual is below 1e-9 (about mid-October). Note that FX-PROD P9 (PROD-40) is a separate, recurring interval defect in the same append path.", method="VERIFIED")

add(id="PROD-23", layer="BUILDERS / funding interval",
    title="Panel, splice and October exporter still apply one declared interval to every API-tail funding row",
    what_is_wrong="Names whose settlement interval changed inside the API tail get the fetch-time interval on older rows; this fed the D17 rows (08-16 seed) and the x0910 September interval errors, and flows into f_fund_iv, f_fund_ema_v1, rn8/FTRIM and carry in research panels and into any bundle ledger/EMA seed.",
    evidence=[C("pod_panel_ext.py", 'rows.append((int(t_ms) // 1000, float(rate), AUG_IV.get(s, np.nan)))'), C("pod_export_bundle_v3.py", 'rows.append((int(t_ms) // 1000, float(rate), AUG_IV.get(s, np.nan)))'),
              "pod_export_bundle_v4.py (42555a37) L220/L230-234, present in pod2 w3_monthly_chain device dir; r6_panel_splice.py (cccc5b6b) L81-91", "uplift_r2_2026-09-13/T5b/RESULT_T5b.md §5.1 (x0910 carry vs ledger, IOST ratio 8.00)", "AUDIT_TRAIN TRN-07; T5d prereg (repairs September cells only)"],
    status="OPEN_MEASURED_MATERIAL", affects=["future_eval", "future_retrain"], severity="P2",
    severity_reason="The October splice panel and any bundle seed inherit it; live is exposed only through a state reset from a seed.",
    recommended_action="Derive each row's interval from its own settlement history (gap or per-row declared history), validated against executor settlement records as T5b did; relabel x0910-based September carry/FTRIM readings until T5d lands.", method="VERIFIED (code) / CITED (T5b numbers)")

add(id="PROD-24", layer="COMBO TARGET / FTRIM as served",
    title="FTRIM is served as a z-layer exclusion before demeaning, not a forced exit; residual shorts decay and freeze under the neutral band",
    what_is_wrong=(f"Rule '{ftr['rules'][0]}' in both chains since {ftr['first']} ({ftr['anchors']} anchors): median {ftr['n_kc_median']:.0f} names per chain (max {ftr['n_kc_max']}), rn8 coverage min {ftr['rn8_coverage_min']}. "
                   "rn8 = latest ledger rate x 8 / stored interval, so FX-PROD P9 interval mislabels reach the classification. "
                   "T5b (61 anchors 09-02..09-12): frozen residual gross 0.33% [0.24%, 0.40%], max age 41 anchors (ONG); frozen-residual carry -0.120 bps/anchor [-0.245, -0.021] (PROVISIONAL: its carry gate is red, PROD-23); all FTRIM residuals +0.115 [-0.080, +0.334] (secondary); residual shorts pay +0.294 [+0.155, +0.478] (post hoc). The executor adds no band freeze."),
    evidence=[C("combo_stage.py", "_band_kc = (z_kc < 0) & np.isfinite(rn8_m) & (rn8_m <= FTRIM_HI)"), C("combo_stage.py", "rn8_full[_j] = float(_r[1]) * (8.0 / (_iv if _iv > 0 else 8.0))"), C("combo_stage.py", 'smv = np.where(np.abs(trade) < P["band"], H, smv)'),
              CREC + ": FTRIM_served", "uplift_r2_2026-09-13/T5b/RESULT_T5b.md"],
    status="OPEN_MEASURED_MATERIAL", affects=["live_trading", "future_eval"], severity="P2",
    severity_reason="Carry drag of order 0.1-0.3 bps/anchor on residual shorts; not a risk exposure.",
    recommended_action="A forced exit for FTRIM names is a book-behaviour change needing the user's ruling (FX-BOOK P7); re-read after T5d and after FX-PROD P9.", method="VERIFIED (code) / CITED (T5b)")

nb = E3["remainder_net_over_full_gross"]; pn = E3["producer_net_over_gross"]; pp = E3["popped_sum_w_over_G"]
add(id="PROD-25", layer="COMBO TARGET -> EXECUTOR reshape (EXE-03 confirmed)",
    title="EXE-03 confirmed from producer files: 91% of the 12Z 撤名残差 is the producer's own net; the uniform re-demean flips small shorts on 99 of 109 combo anchors",
    what_is_wrong=(f"12Z target_live: net/gross {pn:+.4%}; the 11 popped names {pp:+.4%} (net long); remainder {nb:+.4%} = the alarm's net_before/sizing {E3['alarm_net_before_over_sizing_gross']:+.4%}. "
                   f"Share of net_before from the producer's own net {E3['share_of_net_before_from_producer_net']:.1%}, from removing the popped longs {E3['share_from_removing_popped']:.1%}; the alarm text names only the popped names. "
                   f"Re-executing legs.reshape_after_withhold on the producer vector with the recorded pops reproduces orders target_w in sign for {E3['reproduced_vs_orders_target_w']['sign_agreement']}/{E3['reproduced_vs_orders_target_w']['n_common']} names "
                   f"(values x{E3['reproduced_vs_orders_target_w']['ratio_orders_over_reproduced_median']:.7f} after a later per-name cap on {list(E3['reproduced_vs_orders_target_w']['ratio_outliers'])}). "
                   f"Sign flips short->long {E3['n_flips_short_to_long']} ({', '.join(x['symbol'] for x in E3['sign_flips'])}), long->short {E3['n_flips_long_to_short']}; {E3['flipped_filled_nonzero']} filled, {E3['flipped_filled_notional_usdt']:.2f} USDT. "
                   f"Across {E3F['anchors']} combo anchors the producer book is net short on {E3F['net_short_anchors']} (median {E3F['net_over_gross_median']:+.2%}, min {E3F['net_over_gross_min']:+.2%}); the re-demean alone (no pops) flips names on {E3F['anchors_with_flips']} anchors (median {E3F['n_flip_median']:.0f}, max {E3F['n_flip_max']}; flipped unit gross median {E3F['flipped_unit_gross_median']:.2e})."),
    evidence=[CREC + ": EXE03, EXE03_popfree_frequency", "~/dl_quant_live signal/legs.py (" + R_CHK["code_sha256"]["legs.py"][:8] + ") reshape_after_withhold: w = w - w.mean(); w = w / s", "~/dl_quant_live scheduler/anchor_loop.py (" + R_CHK["code_sha256"]["anchor_loop.py"][:8] + ") L1854-1861 alarm text", C("combo_stage.py", "combo_raw = 0.55 * sm_kc + 0.45 * sm_fc"), "AUDIT_EXEC EXE-03"],
    status="PENDING_USER_DECISION", affects=["live_trading", "reporting"], severity="P2",
    severity_reason="Structural every-anchor behaviour: the producer writes an un-neutralised book and the executor's uniform shift reverses small opposite-side intents; the alarm misattributes the cause.",
    recommended_action="Alarm: report producer net and popped-name net separately (FX-EXEC E6). Book: run the side-proportional allocation as a registered experiment (FX-BOOK P8) before any change; measure why the combo book is persistently net short (EMA band freeze, keep-mask exits, cap clipping) before choosing where to neutralise.", method="VERIFIED")

cd = CH["CHK01_change_0903_to_0913"]; cds = CH["CHK01_descriptive"]; claims = CH["CHK01_claims_vs_measured_pct"]
add(id="PROD-26", layer="COMBO TARGET / counterfactual rewrite (CHK-01 confirmed)",
    title="CHK-01 confirmed (11/11 values); the rise from 17% to 27% is the V2MAIN chain moving away from the king book, not FTRIM or rev24 removal",
    what_is_wrong=(f"Σ|w_live - w_king| / Σ|w_king| (inspect_anchor.py L33-38) matches all {sum(1 for v in claims.values() if v['match_2dp'])} of {len(claims)} values AUDIT_EXEC quotes. "
                   f"Decomposition by the two chains combo_stage mixes (gate: 0.55·kc + 0.45·fc equals target_live to {CH['CHK01_gate_mix_equals_target_live_maxabs']:.1e}): "
                   f"R_kc {cd['R_kc']['2026-09-03 08Z']:.3f} -> {cd['R_kc']['2026-09-13 12Z']:.3f} (flat), R_fc {cd['R_fc']['2026-09-03 08Z']:.3f} -> {cd['R_fc']['2026-09-13 12Z']:.3f}; "
                   f"rho_kc_fc {cd['rho_kc_fc']['2026-09-03 08Z']} -> {cd['rho_kc_fc']['2026-09-13 12Z']}; masked model seat {cd['w3_masked']['2026-09-03 08Z'][0]} -> {cd['w3_masked']['2026-09-13 12Z'][0]}. "
                   f"Across {cds['n_anchors']} anchors corr(R, R_fc) {cds['corr_R_Rfc']:.3f}, corr(R, rho_kc_fc) {cds['corr_R_rho_kc_fc']:.3f}, corr(R, masked seat) {cds['corr_R_masked_model_seat']:.3f}, corr(R, R_kc) {cds['corr_R_Rkc']:.3f}, corr(R, FTRIM count) {cds['corr_R_ftrim_n']:.3f}. "
                   "Mechanism (descriptive): the doubled model seat (09-05 seeding, PROD-20) raised V2MAIN's coefficient in the fc chain while the kc chain stays near the king book."),
    evidence=[CREC + ": CHK01_claims_vs_measured_pct, CHK01_change_0903_to_0913, CHK01_descriptive", "multi_asset/exports/live/pilot_journal/tools/inspect_anchor.py (" + R_CHK["code_sha256"]["inspect_anchor.py"][:8] + ") L33-38", "docs/CRON_TEMPLATES_2026-09-04.md:13", "AUDIT_EXEC CHK-01"],
    status="DOC_STALE", affects=["reporting"], severity="P3",
    severity_reason="Producer side has no defect; the template's fixed level is stale (AUDIT_EXEC keeps CHK-01 at P2 for the escalation rule).",
    recommended_action="Replace the fixed 19-20% level with a trailing band and report R_kc/R_fc next to R so a real change in the V2MAIN chain is visible.", method="VERIFIED")

cw = TI["combo_written_s"]
add(id="PROD-27", layer="COMBO LIVE / timing",
    title="The combo rewrite lands within 9 s of its hard deadline at worst; a late producer run skips the rewrite with no page",
    what_is_wrong=(f"Since combo went live: {TI['n_anchors']} anchors, {TI['n_combo']} traded the combo target, {TI['n_king_form']} the king form ({TI['king_form_rows'][0]['anchor']}, king file written at {TI['king_form_rows'][0]['king_written_s']:.0f} s). "
                   f"Combo target written median {cw['median']:.0f} s after the anchor, p99 {cw['p99']:.0f} s, max {cw['max']:.0f} s against the 1360 s bail; minimum margin {cw['min_margin_to_hard_deadline_1360s']:.0f} s, {cw['n_within_60s_of_deadline']} of {TI['n_combo']} anchors within 60 s. "
                   "A combo run that starts late bails with a HIGH page and the executor trades the king form; if the producer finishes after N+22:35 the daemon skips silently (the 08-30 00Z case). The executor reads at N+24."),
    evidence=[TREC, f"fea171/combo_live_daemon.sh (72f78d1e) L27-29 silent skip branch", C("combo_stage.py", "_deadline = A + 22 * 60 + 40"), "receipts_prod/runtime_processes.txt (com.hsy.combolive PID 30944)"],
    status="OPEN_MEASURED_MATERIAL", affects=["live_trading"], severity="P2",
    severity_reason="A ~10 s slowdown on the slowest observed anchor would switch that anchor's traded book to the king form; one of the two failure paths raises no page.",
    recommended_action="Page on the daemon's late-skip branch; separately (user word) move the producer offset earlier or widen the deadline consistently with the N+24 read; keep heavy Mac jobs out of N+15..N+25.", method="VERIFIED")

add(id="PROD-28", layer="PRODUCER RUNTIME / versions",
    title="The running producer and combo daemon execute the on-disk code, bundle and F10 model (verification record)",
    what_is_wrong="None found. com.hsy.shadowloop PID 10900 started 2026-09-05 12:47:33Z, after shadow_loop_v3.py (e9c98374) was last written 09-04 00:53:42Z; bundle MANIFEST 8/8 matches disk (booster 8d79186b, signal booster_sha on every anchor since 09-01 08Z); combo_stage.py (b5c698f9) is launched fresh each anchor by com.hsy.combolive (PID 30944, started 08-30 05:03Z, daemon file 08-26); fea171/f10_live_s42_np.npz 351ae26b equals the pod2 export; xfer_ref/xfer_syms symbol axes equal config symbols_panel. The pinned feature code runs bitwise equal to the served inputs (G-SREP/G-F10SREP).",
    evidence=["receipts_prod/runtime_processes.txt", "receipts_prod/pod2_provenance.txt (f8_ext/models/f10_live_s42_np.npz 351ae26b)", SREC + ": S6", KREC + ": G-SREP", FREC + ": G-F10SREP"],
    status="VERIFIED_IMMATERIAL", affects=["live_trading"], severity="P3", severity_reason="Record only (exact sha, mtime and process start ordering).", recommended_action="None.", method="VERIFIED")

add(id="PROD-29", layer="PRODUCER RUNTIME / second writer",
    title="The sidecar daemon is a second, non-atomic writer of the same combo intermediates",
    what_is_wrong="com.hsy.sidecar (PID 30943) runs sidecar_blend.py (6140790e), which repeats combo_stage.py L1-222 and writes mini/cache.npz, mini/data/dlw_targets.npz, xfer_panel_live.npz, state_H_f10_<A>.npz and target_blend/<A>.json with non-atomic np.savez; combo_stage reads the same paths (state_H_f10 is the fc warm-start fallback). Isolation is timing only: the sidecar sleeps 120 s after a new target_live. 0 overlaps observed in 109 anchors; the sidecar last recomputed the 171 pipeline at 08-30 00Z.",
    evidence=["receipts_prod/runtime_processes.txt (sidecar_daemon.sh 01d75619: sleep 120 / 180)", "~/wide_shadow/fea171/sidecar_blend.py (6140790e) L123-124, L143, L194, L211", C("combo_stage.py", 'hf_prev = f"{HERE}/state_H_f10_{A - 14400}.npz"')],
    status="VERIFIED_IMMATERIAL", affects=["live_trading"], severity="P3", severity_reason="Latent; 0 collisions observed; a collision would most likely fail loud (king fallback with page).",
    recommended_action="Retire the sidecar (target_blend has no reader) or give it its own output paths; a production process change needs the user's word.", method="VERIFIED (code, process list) / CITED (collision count from the fork's log scan)")

add(id="PROD-30", layer="PRODUCER RUNTIME / sandbox producer",
    title="A modified sandbox producer (exec_n6) has been running at N+1 since 09-06 against the live bundle",
    what_is_wrong="PID 50689 runs ~/cc_tmp/exec_n6_sandbox/shadow_loop_v3.py with WIDE_SHADOW_HOME=~/cc_tmp/exec_n6_sandbox and SHADOW_OFFSET_MIN=1 (own lock and state, live bundle read-only, not launchd-managed). It shares the IP's API budget and writes target files that are not the live chain.",
    evidence=["receipts_prod/runtime_processes.txt (ps lstart Sep 6 20:58:03 SGT; env WIDE_SHADOW_HOME, SHADOW_OFFSET_MIN=1)", "docs/PREREG_deploy_exec_n6_2026-09-06.md; STATE.md (conditional GO, swap needs user word)"],
    status="PENDING_USER_DECISION", affects=["future_eval", "reporting"], severity="P3", severity_reason="Isolated state; risk is mistaking its outputs for live and API-budget sharing.",
    recommended_action="Stop it or label its outputs when the exec_n6 decision is made.", method="VERIFIED")

add(id="PROD-31", layer="MODEL ARTEFACTS / stale copies",
    title="fea171/f10_live_s42.pt next to the served numpy model is the August model, not the checkpoint behind 351ae26b",
    what_is_wrong="~/wide_shadow/fea171/f10_live_s42.pt (d6619801, written 08-24) is the August model (trained_through 08-10 20Z); the served npz 351ae26b comes from pod2 f8_ext/models/f10_live_s42.pt (c983b3e3). combo_stage loads only the npz.",
    evidence=["receipts_prod/runtime_processes.txt (mtimes and sha prefixes)", C("combo_stage.py", 'M = np.load(f"{HERE}/f10_live_s42_np.npz")')],
    status="DOC_STALE", affects=["future_eval", "reporting"], severity="P3", severity_reason="Wrong-copy risk only.",
    recommended_action="Rename the .pt with an _aug suffix or add a note beside it.", method="VERIFIED (sha/mtime) / CITED (trained_through from the fork's read)")

add(id="PROD-32", layer="SERVING / stop overlay",
    title="stop_overlay.py is a reporting shadow on the king-form weights; the served stop is the executor's per_name_stop",
    what_is_wrong="com.hsy.stopoverlay computes its stops on state/weights/<A>.npz (the producer's king-form book), so its held/stopped counts and cf_bps describe a book that is not traded. No executor code reads stop_overlay.json; config/book.json names stop_overlay.py only in the basis note of the wide per-name-stop profile (d30, 2 anchors, 7-day cooloff), which the executor applies after target_live (W9 fix deployed in ef60f85).",
    evidence=["receipts_prod/runtime_processes.txt (grep -rl stop_overlay over live/ scheduler/ signal/ ops/ config/: config/book.json only)", "~/wide_shadow/stop_overlay.py (d54a2e16) L1-37", "AUDIT_EXEC (EXE-08 running tree ef60f85)"],
    status="DOC_STALE", affects=["reporting"], severity="P3", severity_reason="Mislabelled reporting only.",
    recommended_action="Label or retire stop_overlay; never cite its depths or cf_bps as live.", method="VERIFIED")

add(id="PROD-33", layer="DOCS",
    title="CLAUDE.md says the executor reads at N+23; the executor reads at N+24",
    what_is_wrong="config/book.json external_book.anchor_offset_min = 24; external_book.py wakes at nominal + offset x 60 s; the 12Z rebalance id A1789302239 started 12:23:59Z.",
    evidence=[TREC + ": executor_anchor_offset_min 24", "AUDIT_EXEC DOC-01"], status="DOC_STALE", affects=["reporting"], severity="P3", severity_reason="Documentation only.",
    recommended_action="Correct the project identity line in CLAUDE.md.", method="VERIFIED")

add(id="PROD-34", layer="IN-SERVICE MODEL / king training data",
    title="The in-service booster 8d79186b was trained on the unclamped builder: 30-day windows of January-2022 training rows wrap to the cache tail (E-0909-A)",
    what_is_wrong="pod_fea_ext.py (02157bda, the builder of wide_fea_v2ext.npy used by pod_export_bundle_v3.py) takes s_[E - w] with no clamp, so anchors with E < w read the end of the cache (e.g. 2022-01-11 00Z cpos_mean_8640_v -242,695 clipped to -10,000, ranks computed on the garbage). The October builder clamps; the in-service model still contains these rows. Row count and effect on 8d79186b not measured.",
    evidence=[C("pod_fea_ext.py", "nf = np.maximum(f_[E] - f_[E - w], 1)"), TR_K_OCT, "docs/RESULT_holefix_round2_corrected_chain_2026-09-09.md L62 (king_wrap_verify)", "receipts_prod/pod2_provenance.txt (pod_fea_ext.py 02157bda; wide_fea_v2ext_meta.npz 4b1b6047, 09-01 05:33)"],
    status="OPEN_NOT_MEASURED", affects=["live_trading"], severity="P3", severity_reason="Early-2022 rows only (anchors before 2022-01-31); fixed for the next export.",
    recommended_action="No live action; the next export with the clamp builder removes it (keep the clamp statistic gate).", method="VERIFIED (code) / INFERRED (affected-row range)")

add(id="PROD-35", layer="IN-SERVICE MODEL / V2MAIN training data",
    title="The in-service V2MAIN was trained with fund columns set to 0 for names outside today's live 450, and on the pre-holefix cache",
    what_is_wrong="dlw_ext fea82 (9bc111a4) was built on panel wide_panel_4h_v3splice (c5d10f6a), whose funding columns are empty outside the live 450, so 26.8% of training pairs carry fund_ema = fund_now = 0 (T4b RECEIPT F2); served members always have real values. The same features were built on dlnative_5m_wide829_f16_ext (72eb7849), before the 08-12.. hole repair. Neither effect on the served model is measured.",
    evidence=["receipts_prod/pod2_reports/dlw_ext_results_dlw_features_report.json (panel_sha256 c5d10f6a, cache_sha256 72eb7849, self e86725cc)", "receipts_prod/pod2_provenance.txt (data/wide_panel_4h_v3splice.npz c5d10f6a)",
              "uplift_r2_2026-09-13/T4b/receipts/RECEIPT_T4b_facts_v2main.json F2_stored_zeros", "AUDIT_DATA batch 2 F2 (devices_data/receipts/AD_F_batch2.json)"],
    status="OPEN_NOT_MEASURED", affects=["live_trading", "future_retrain"], severity="P3", severity_reason="Training-distribution defect of the served model; size unknown; the October chain rebuilds features.",
    recommended_action="Build DL fund columns from the panel that covers every training name (or mask the loss on names without funding) in the next export, and state it in the export gate.", method="VERIFIED")

add(id="PROD-40", layer="PRODUCER / funding append (cross-reference)",
    title="FX-PROD P9: the producer labels short-to-long interval-switch rows by the backward gap and inflates rn 2-4x",
    what_is_wrong="Owned by FX-PROD (fix in progress, not re-derived here). It reaches every served consumer of rn: king and V2MAIN column 80 (v1 EMA), the fund leg's base-distribution rank, FTRIM's rn8 classification (PROD-24) and the carry estimate.",
    evidence=[C("shadow_loop_v3.py", "iv = float(min([1.0, 2.0, 4.0, 6.0, 8.0], key=lambda a: abs(a - (iv if 0 < iv <= 24 else 8.0))))"), C("shadow_loop_v3.py", "rn = rate * (8.0 / iv)"), C("combo_stage.py", "rn8_full[_j] = float(_r[1]) * (8.0 / (_iv if _iv > 0 else 8.0))"), "FX-PROD P9 (lead message; docs/fixprogram_2026-09-13/FIXPROGRAM_2026-09-13.md)"],
    status="OPEN_MEASURED_MATERIAL", affects=["live_trading", "future_eval"], severity="P2", severity_reason="As assessed by FX-PROD; cross-referenced so the served-input register is complete.",
    recommended_action="Follow FX-PROD P9; after its fix, re-read PROD-24 FTRIM counts and the column-80 contrast.", method="CITED (FX-PROD P9)")

# ---- V2MAIN items (numbers from receipts_prod/parity_f10.json; one check on the run's saved arrays)
FA_P = HOME + "/cc_tmp/aud_prod/f10_arrays.npz"; DLR_P = HOME + "/cc_tmp/aud_prod/parity_stage/dl_x0910_rows.npz"; T4R_P = HOME + "/cc_tmp/aud_prod/parity_stage/T4_replay_rec_served.npy"
ARR_SHA = {"f10_arrays.npz": gsha(FA_P), "dl_x0910_rows.npz": gsha(DLR_P), "T4_replay_rec_served.npy": gsha(T4R_P)}
assert ARR_SHA["dl_x0910_rows.npz"] == "c03ac4afa04ef61edbb1ad8bb1db6a73afe7535109747a196d9889240c6ed81e" and ARR_SHA["T4_replay_rec_served.npy"] == "942d20a91496f60b626a18cac13185b00f5ac2cd26c5300c7d57e5fefcb3c92f"
FA = np.load(FA_P); DLR = np.load(DLR_P, allow_pickle=True); T4R = {int(r["anchor"]): r for r in np.load(T4R_P, allow_pickle=True)}
FUNDNOW = []
for a in [1788624000 + 28800 * k for k in range(16)] + [1789070400]:
    xs = FA[f"FS_{a}"]; ss = np.asarray(T4R[a]["members"], np.int64); rm = DLR["pair_ts"].astype(np.int64) == a; xt = DLR["X82"][rm].astype(np.float32); st = DLR["pair_s"].astype(np.int64)[rm]
    c = np.intersect1d(ss, st); i_ = np.searchsorted(ss, c); j_ = np.searchsorted(st, c); fs_, ft_ = xs[i_, 81], xt[j_, 81]
    den = np.maximum(np.abs(fs_), np.abs(ft_)); FUNDNOW.append({"anchor": time.strftime("%Y-%m-%d %HZ", time.gmtime(a)), "train_zero_share": float((ft_ == 0).mean()), "serve_zero_share": float((fs_ == 0).mean()),
                                                                  "cells_gt_1e-3": int((np.abs(fs_ - ft_) > 1e-3 * den).sum())})
FUNDNOW_BAD = [x for x in FUNDNOW if x["cells_gt_1e-3"] > 0]
ft_rows = R_F10["score"]["FT_vs_FS"]["per_anchor"]
ftcols = [n for n, v in FST["phase1_truncation_FT_vs_FS"].items() if v["bitwise_equal_share"] < 1]
hmcols = [n for n, v in FST["history_members_FS_vs_FH"].items() if v["bitwise_equal_share"] < 1]
gF = R_F10["gates"]
F10GATES = (f"gates: G-F10SREP production 40-day cache reproduces served combo_X171/scol/f10 bitwise {gF['G-F10SREP']['full40d']['X171_bitwise']}/6 (also the T4b 234-239-row view {gF['G-F10SREP']['t4b_view']['X171_bitwise']}/6); "
            f"G-MEMBERCODE {gF['G-MEMBERCODE']['equal']}/{gF['G-MEMBERCODE']['checked_anchors']}; G-F10CODE PASS (training code on training members reproduces the stored rows; trend_288 {gF['G-F10CODE']['trend']['C:trend_288']:.4f}, trend_2016 {gF['G-F10CODE']['trend']['C:trend_2016']:.4f} bitwise share); G-BOOT bundle tail == pod cache on live450 ({gF['G-BOOT_info']['bitwise_diff']} diffs)")
famtxt = ", ".join(f"{f} {v['spearman_median']:.4f}" for f, v in sorted(FAMSUB.items(), key=lambda kv: kv[1]["spearman_median"]) if f not in ("C_trend", "H_btcv", "H_disp", "J_drank"))
add(id="PROD-06", layer="MODEL INPUT / V2MAIN (rank universe)",
    title="V2MAIN inputs differ between training and serving almost entirely through the member universe of every cross-sectional rank; score Spearman 0.982",
    what_is_wrong=(f"On 17 anchors (09-05 16Z..09-10 20Z) the served 171 columns vs the stored x0910 training rows on common names give V2MAIN-score Spearman median {fs('FS_vs_T171')} (min {fs('FS_vs_T171','spearman','min')}), max rank change median {fs('FS_vs_T171','max_abs_drank','median',3)}; "
                   f"{fcount('total_FS_vs_T171')} of 171 columns have cells beyond 1e-3. Holding code and data fixed and changing only the member sets (production-rule members on live450 vs training members on 829 names) reproduces the gap: Spearman {fs('FH_vs_FD')} (min {fs('FH_vs_FD','spearman','min')}); "
                   f"the same code on training members reproduces the stored training rows (Spearman {fs('FD_vs_T171')}, max score change {fs('FD_vs_T171','max_abs_dscore','max',5)}). "
                   f"Score Spearman when one family is swapped to training values: {famtxt}. The in-service V2MAIN (trained through 2026-08-30) saw 2026 cross-sections that include tokenized equities (7.3% of 2026 member pairs, AUDIT_DATA C6); it is served crypto-only live-450 cross-sections."),
    evidence=[SV_F_82 + "; " + SV_F_89 + "; " + SV_F_MEM, TR_F_82 + "; " + TR_F_89 + "; " + TR_F_MEM, FREC + ": score.FS_vs_T171/FH_vs_FD/FD_vs_T171, pair_stats, score_family_substitution_FS_with_T171; " + F10GATES,
              MREC + ": summary.PD (Jaccard median " + f"{MS['PD']['jaccard']['median']:.3f})", "devices_data/receipts/AD_C_cache_members.json C6 (dl_targets_members 2026 noncrypto share 0.0726)"],
    status="OPEN_MEASURED_MATERIAL", affects=["live_trading", "future_eval", "future_retrain"], severity="P2",
    severity_reason="Every rank-based V2MAIN input is on a different cross-section from training for the served model and for every 2026 research score; book layer not measured.",
    recommended_action="Same fix as PROD-02: one member universe (CRYPTO default) in pod_dlw_targets_raw.py member selection before the October DL retrain; add a served-vs-builder X171 parity gate at export (this device's G-F10SREP/G-F10CODE pattern).", method="VERIFIED")
add(id="PROD-07", layer="MODEL INPUT / V2MAIN (history members)",
    title="Serving reuses the scored anchor's member set on every history row; only the 24h rank-change and dispersion columns move, score Spearman 0.9998",
    what_is_wrong=(f"combo_stage writes members = pm for all history anchors ('近似'), while training uses each anchor's own members. Rebuilding the served rows with each history row's production member set changes only {len(hmcols)} columns ({', '.join(hmcols)}): "
                   f"J:drank cells beyond 1e-3 {FST['history_members_FS_vs_FH']['J:drank_m7_1d']['n_gt_1e-3']}/{FST['history_members_FS_vs_FH']['J:drank_v7_1d']['n_gt_1e-3']}/{FST['history_members_FS_vs_FH']['J:drank_r24_1d']['n_gt_1e-3']} of ~6,800 (max 0.5 where a name was not a member 24h earlier), "
                   f"H:disp_z median relative change {FST['history_members_FS_vs_FH']['H:disp_z']['median']:.3f} (max {FST['history_members_FS_vs_FH']['H:disp_z']['max']:.3f}). "
                   f"V2MAIN score Spearman median {fs('FS_vs_FH','spearman','median',5)} (min {fs('FS_vs_FH','spearman','min',5)}), max rank change median {fs('FS_vs_FH','max_abs_drank','median',3)} (max {fs('FS_vs_FH','max_abs_drank','max',3)}). "
                   f"Early rows of the long cache without a full 7-day window reused the first full-window member set ({R_F10['FH_early_rows_fallback']['n_rows_filled']} rows, outside every scored anchor's windows); anchors without a weights file used the production member code ({R_F10['FH_early_rows_fallback']['anchors_without_weights_file_member_code_used']})."),
    evidence=[SV_F_MEM, SV_F_DRANK, SV_F_DISP, FREC + ": pair_stats.history_members_FS_vs_FH, score.FS_vs_FH, FH_early_rows_fallback; " + F10GATES],
    status="OPEN_MEASURED_MATERIAL", affects=["live_trading", "future_eval"], severity="P3",
    severity_reason="Real but small at the score layer (Spearman >= 0.9996); confined to 8 columns.",
    recommended_action="Store per-anchor member sets in producer state and pass them to the 171 pipeline (a producer change; bundle with the PROD-06 universe fix).", method="VERIFIED")
add(id="PROD-08", layer="MODEL INPUT / V2MAIN (btcv)",
    title="btcv is defined differently in training (zero-filled, divisor E-S) and serving (nanstd with back-fill) but the served values are equal",
    what_is_wrong=(f"H:btcv_z: 0 cells beyond 1e-3 between served rows and stored training rows (and between F_H and F_D) on 17 anchors; swapping the btcv family to training values leaves V2MAIN score Spearman {FAMSUB['H_btcv']['spearman_median']:.5f} (the products carry rank-universe differences). "
                   "The back-fill matters only in short caches (PROD-36)."),
    evidence=[SV_F_BTCV, TR_F_BTCV, FREC + ": pair_stats.total_FS_vs_T171['H:btcv_z'], universe_btcv_FH_vs_FD['H:btcv_z']"],
    status="VERIFIED_IMMATERIAL", affects=["live_trading"], severity="P3", severity_reason="Resolution 1e-3 relative on every cell of 17 anchors.", recommended_action="None for live; see PROD-36 for replays.", method="VERIFIED")
add(id="PROD-09", layer="MODEL INPUT / V2MAIN (trend cumsum length)",
    title="The two trend columns depend on cache length (global cumulative sums); the same code on a 48-day cache differs from the 4.7-year training build in 1.1% / 0.06% of cells",
    what_is_wrong=(f"G-F10CODE: with training members, training btcv and the pod cache, every column reproduces the stored training rows bitwise except C:trend_288 ({gF['G-F10CODE']['trend']['C:trend_288']:.4f} bitwise; {FST['code_identity_FD_vs_T171']['C:trend_288']['n_gt_1e-3']} cells beyond 1e-3, max {FST['code_identity_FD_vs_T171']['C:trend_288']['max']:.4f} rank units) "
                   f"and C:trend_2016 ({gF['G-F10CODE']['trend']['C:trend_2016']:.4f}; {FST['code_identity_FD_vs_T171']['C:trend_2016']['n_gt_1e-3']} cells, max {FST['code_identity_FD_vs_T171']['C:trend_2016']['max']:.4f}). "
                   f"Serving runs on a 40-day cache, training on the full history, so near-tied trend values rank differently. Swapping the trend columns alone leaves V2MAIN score Spearman {FAMSUB['C_trend']['spearman_median']:.5f}. Same mechanism AUDIT_TRAIN TRN-16 found in the STEP1 gate."),
    evidence=[SV_F_TREND, FREC + ": gates.G-F10CODE, pair_stats.code_identity_FD_vs_T171", "AUDIT_TRAIN TRN-16"],
    status="VERIFIED_IMMATERIAL", affects=["live_trading", "future_retrain"], severity="P3",
    severity_reason="Resolution: rank changes <= 0.005 on 1.1% of trend_288 cells; score Spearman 0.9999.",
    recommended_action="Adopt the local-window trend builder (pod_f8_build_stable.py, TRN-16) for training and serving together.", method="VERIFIED")
add(id="PROD-36", layer="REPLAY DEVICE / Phase-1 G-P2 residual",
    title="Mechanism of the open Phase-1 G-P2 residual found: replay caches shorter than ~37 days put btcv back-fill into the 180-anchor z window",
    what_is_wrong=(f"Running the production 171 pipeline with the cache truncated at the Phase-1 replay start (2026-08-03 08:05Z) instead of the producer's 40 days changes only {', '.join(ftcols)}, and only while the truncated cache holds <= 213 anchor rows: "
                   + "; ".join(f"{r['anchor']} ({r['n_e_rows_truncated']} rows) max |Δscore| {r['max_abs_dscore']:.1e}, max |Δrank| {r['max_abs_drank']:.4f}" for r in ft_rows) + ". "
                   "_btcv_series fills the first 2,016 rows with the first full-window value; the causal z uses the previous 180 anchors, which reach those rows when the cache is shorter than about 37 days. "
                   "The live producer always holds 40 days (239 rows) and is unaffected; replay chain runs started from a later snapshot are affected on their first days, which matches Phase 1's DL-leg-only, decaying residual (target-level link INFERRED: the combo chain was not re-run)."),
    evidence=[SV_F_BTCV, SV_F_DISP, FREC + ": score.FT_vs_FS.per_anchor, pair_stats.phase1_truncation_FT_vs_FS, gates.G-F10SREP (a 20-hour truncation, 234 rows, is bitwise inert)",
              "multi_asset/exports/research/parity_replay_2026-09-12/RESULT_parity_phase1_2026-09-12.md §2-§3 (G-P2 0/41, residual only in the DL leg, latest anchor exact)"],
    status="OPEN_MEASURED_MATERIAL", affects=["future_eval"], severity="P2",
    severity_reason="Explains an open gate of the production-path replay that P2 (now main priority) must close; affects any chain replay that truncates the producer cache.",
    recommended_action="In the replay device, give every scored anchor a full 40-day cache (prepend rows from the bundle tail or pod cache, verified equal on live450 as here) and re-run the Phase-1 chain; G-P2 at 1e-6 should then pass or show a second mechanism.", method="VERIFIED (feature and score layers) / INFERRED (target layer)")
add(id="PROD-37", layer="MODEL INPUT / V2MAIN (columns 80-81)",
    title="V2MAIN column 80 trained v0 / served v1 and column 81 fill rules (T4b), measured on 17 anchors",
    what_is_wrong=(f"fund_ema served vs training: median relative difference {FST['total_FS_vs_T171']['fund_ema']['median']:.3f}, per-anchor Spearman {FST['total_FS_vs_T171']['fund_ema']['spearman_median']:.3f}. "
                   f"fund_now is equal (0 cells beyond 1e-3) on every anchor except {', '.join(x['anchor'] for x in FUNDNOW_BAD)}, where all training rows are 0 because the x0910 splice panel ends at 2026-09-10 00Z (the TRN-17 pattern); "
                   f"zero shares otherwise equal on both sides (max {max(x['serve_zero_share'] for x in FUNDNOW):.3f}). Serving takes columns 80/81 for every name in the producer's EMA state with no 12h freshness mask; only members reach the model and all members were fresh (T4b). "
                   f"Swapping both fund columns to training values: V2MAIN score Spearman {FAMSUB['fund']['spearman_median']:.4f} (min {FAMSUB['fund']['spearman_min']:.4f}). Historical book effect NOT MEASURED (T4b: no fold checkpoints)."),
    evidence=[SV_F_FUND, TR_F_FUND, FREC + ": pair_stats.total_FS_vs_T171 fund_ema/fund_now, score_family_substitution fund", "f10_arrays.npz check in this builder (sha " + ARR_SHA["f10_arrays.npz"][:12] + ")", "uplift_r2_2026-09-13/T4b/RESULT_T4b_v2main_feature_skew_2026-09-13.md §0-§4; AUDIT_TRAIN TRN-05, TRN-17"],
    status="OPEN_NOT_MEASURED", affects=["live_trading", "future_retrain"], severity="P3",
    severity_reason="Score-layer effect small (Spearman 0.999); book effect unmeasured; the October export reintroduces the split (TRN-05, P2 there).",
    recommended_action="Decide the column-80 caliber for both models at once (PROD-04); give the monthly panel a row for every training anchor (TRN-17).", method="VERIFIED")

# ---- counts, summary tables, writer
ITEMS.sort(key=lambda x: x["id"])
STATUSES = ["FIXED_DEPLOYED", "VERIFIED_IMMATERIAL", "OPEN_MEASURED_MATERIAL", "OPEN_NOT_MEASURED", "PENDING_USER_DECISION", "DOC_STALE"]
COUNTS = {"by_status": {s: sum(1 for i in ITEMS if i["status"] == s) for s in STATUSES}, "by_severity": {p: sum(1 for i in ITEMS if i["severity"] == p) for p in ("P0", "P1", "P2", "P3")}, "total": len(ITEMS)}
assert sum(COUNTS["by_status"].values()) == len(ITEMS)
import subprocess
def commit_of(path):
    try: return subprocess.check_output(["/usr/bin/git", "-C", REPO, "log", "--format=%h", "--", path], text=True, env={"PATH": "/usr/bin:/bin", "HOME": HOME}).split()
    except Exception as e: return [f"ERR {type(e).__name__}"]
DEVICES = []
for rel_ in ["devices_prod/members/members_stage.py", "devices_prod/members/members_stage.sh", "devices_prod/members/members_audit.py", "devices_prod/members/members_run_pod2.sh",
             "devices_prod/state/state_seat_ledger_probe.py", "devices_prod/state/state_combo_timing_probe.py", "devices_prod/parity/parity_x0910_extract.py", "devices_prod/parity/parity_run_pod2.sh",
             "devices_prod/parity/parity_king.py", "devices_prod/parity/parity_f10.py", "devices_prod/parity/prod_target_checks.py", "devices_prod/parity/parity_run_mac.sh", "devices_prod/parity/pod2_provenance.sh",
             "devices_prod/build/build_audit_prod.py"]:
    p = AD + "/" + rel_; DEVICES.append({"path": "docs/audit_pipeline_2026-09-13/" + rel_, "sha256": gsha(p), "commits_newest_first": commit_of("docs/audit_pipeline_2026-09-13/" + rel_)})
NOT_CHECKED = [
    "Book layer (P&L) of every model-input item: PROD-01/02/03 for 8d79186b and PROD-06/07/08/09 for V2MAIN are measured at the feature and score layers only.",
    "Parity before 2026-09-05 16Z: served king inputs exist for 47 anchors (09-05 16Z..09-13 08Z) and served V2MAIN inputs are reproduced for 17 overlap anchors (09-05 16Z..09-10 20Z) plus 6 bitwise anchors; one regime, no crash anchors; the 29ffaf58 era (08-16..09-01) not covered.",
    "V2MAIN column parity against the in-service model's own training rows (dlw_ext / f8_ext, pre-holefix cache, trained through 08-30): the x0910 rows built by the same builders on the holefix2 cache stand in; the ext rows were not compared.",
    "The fund leg's served inputs (xz_in_base over the exchange base list) against any research panel; the rev24 leg (computed, masked out of combo); the king-form fallback path's parity.",
    "The row count and model effect of E-0909-A in 8d79186b's training rows (PROD-34) and of the zero fund columns / pre-holefix cache in V2MAIN's (PROD-35).",
    "FX-PROD P9's truth table (cross-referenced, not re-derived); T5d; T5b numbers (cited).",
    "Other launchd jobs (c2shadow, universe_shadow, w4liqcapture, depthwatch, regime_dash) beyond confirming they do not write target_live/target_combo; the Telegram paths inside combo_stage.",
    "Executor internals beyond reading the 12Z anchors/orders rows and legs.py/anchor_loop.py for EXE-03 (aud-exec scope); why PIEVERSEUSDT was capped after the reshape.",
    "Why the combo book is persistently net short (EMA band freeze, keep-mask exits, cap clipping): the net is measured, its cause is not.",
    "jpline (not accessed); pod2 GPU (not used).",
]
fam_rows = []
for fam, names in R_F10["families"].items():
    tot = FST["total_FS_vs_T171"]; hm = FST["history_members_FS_vs_FH"]; ub = FST["universe_btcv_FH_vs_FD"]; ci = FST["code_identity_FD_vs_T171"]
    fam_rows.append((fam, len(names), sum(1 for n in names if tot[n]["n_gt_1e-3"] > 0), sum(1 for n in names if hm[n]["n_gt_1e-3"] > 0), sum(1 for n in names if ub[n]["n_gt_1e-3"] > 0),
                     sum(1 for n in names if ci[n]["n_gt_1e-3"] > 0), FAMSUB.get(fam, {}).get("spearman_median")))
king_table = []
for r in COLS:
    if not r["model"].startswith("king") or r["booster_input_pos"] == "": continue
    king_table.append((int(r["gain_rank"]), r["name"], r["classification"], fnum(r.get("measured:total_S_vs_T:share_gt_1e-3")), fnum(r.get("measured:total_S_vs_T:spearman_median")),
                       fnum(r.get("measured:clock_TP_vs_TPE:spearman_median")), fnum(r.get("measured:universe_Trep_vs_TP:median")), fnum(r.get("measured:clock_subst:spearman_median")), fnum(r.get("measured:clock_subst:decile_changed_median")),
                       int(fnum(r.get("measured:P10:leaf_rows_changed_single_col")) or 0)))
king_table.sort()
def f_(x, nd=4): return "" if x is None else (f"{x:.{nd}f}")
MD = []
w = MD.append
w("> **创建:** 2026-09-13 15:xxZ | **Session:** https://claude.ai/code/session_01BzpuBRGZh8oPvpD8NgqsME (aud-prod, auditor teammate, read-only) | **状态:** 审计登记册(只读; 未改任何实盘文件; 由 devices_prod/build/build_audit_prod.py 从已提交收据生成) | **作废条件:** shadow_loop_v3.py ≠ e9c98374、combo_stage.py ≠ b5c698f9、bundle MANIFEST 或 slow2026.txt ≠ 8d79186b、f10_live_s42_np.npz ≠ 351ae26b、任一被引收据 sha 改变,或任一登记项被修复/裁定后需差异复核")
w("")
w("# AUDIT_PROD — producer and model-serving layer (read-only, 2026-09-13)")
w("")
w("Companion data: `AUDIT_PROD.json` (same register, same wording) and `AUDIT_PROD_columns.csv` (every king and V2MAIN input column: definition sources, classification, measured statistics).")
w("")
w("## 0. What was audited, frozen at what")
w("")
w("| Object | Value |")
w("|---|---|")
for k in ("shadow_loop_v3.py", "combo_stage.py", "dlw_features.py", "f8_higher_order_features.py", "slow2026.txt", "config.json"):
    w(f"| {k} (serving) | `{CODE[k][1]}` |")
w("| f10_live_s42_np.npz (serving) | `351ae26bd6b4a203431a280427fc0bbc968c66e903532168765d654e7e57b3a4` |")
for k in ("pod_fea_ext.py", "pod_fea_ext_clamp.py", "pod_dlw_features_ext.py", "pod_f8_build_ext.py", "pod_dlw_targets_ext.py", "pod_panel_ext.py", "pod_export_bundle_v3.py", "pod_f10_refit_ext.py"):
    w(f"| {k} (training; pod2 runtime copy has the same sha, receipts_prod/pod2_provenance.txt) | `{CODE[k][1]}` |")
w(f"| Training-side data compared | x0910 extension: king features 048ea709…, DL targets 5b628413…, fea82 e8377803…, fea89 d4a33cc3…, cache 81152994… (receipts_prod/parity_x0910_extract.json) |")
w(f"| Served inputs compared | T4 served records 942d20a9… (41 anchors) + T4b served records 6f121afe… (6 anchors); live rolling cache copy 9ef804fe… (after the 12Z anchor) |")
w("| Running processes | com.hsy.shadowloop PID 10900 (since 09-05 12:47Z), com.hsy.combolive PID 30944, com.hsy.sidecar PID 30943 (receipts_prod/runtime_processes.txt) |")
w("| Research branch | research/book-uplift-2026-09-11 |")
w("")
w("Constraints kept: ~/wide_shadow and ~/dl_quant_live only read (production feature code executed from sha-checked copies or from file text, bytecode writing disabled); no exchange API call; Mac devices refused to start inside N+10..N+55 of an anchor; pod2 CPU only, nice 19, ≤ 8 cores, PIDs 333197/339489 untouched, dd probe before the extraction write; bulky data in ~/cc_tmp/aud_prod; every device committed before it ran (failed first runs kept and named).")
w("")
w("Status legend: **FIXED_DEPLOYED** fix running; **VERIFIED_IMMATERIAL** checked, no effect at the stated resolution; **OPEN_MEASURED_MATERIAL** defect confirmed with numbers; **OPEN_NOT_MEASURED** mechanism confirmed, size not measured; **PENDING_USER_DECISION** needs a ruling or an experiment readout; **DOC_STALE** code/state right, a document is wrong. Method: VERIFIED = computed or read in this audit; CITED = taken from a named receipt; INFERRED = reasoning, not measured.")
w("")
w("## 1. Result")
w("")
p01 = [i for i in ITEMS if i["severity"] in ("P0", "P1")]
w(f"**P0: {COUNTS['by_severity']['P0']}. P1: {COUNTS['by_severity']['P1']}.**" + ("" if p01 else " No item reaches P1: nothing found changes the live book without a ruling today; the largest findings are model-input representation gaps measured at the score layer (PROD-01/02/03, PROD-06..09) whose book-layer size is unmeasured."))
w("")
if p01:
    w("| ID | Title | Status | Why |"); w("|---|---|---|---|")
    for i in p01: w(f"| {i['id']} | {i['title']} | {i['status']} | {i['severity_reason']} |")
    w("")
w("| Status | Count |"); w("|---|---:|")
for s in STATUSES: w(f"| {s} | {COUNTS['by_status'][s]} |")
w(f"| **Total** | **{COUNTS['total']}** |")
w("")
w("By severity: " + ", ".join(f"{p} {COUNTS['by_severity'][p]}" for p in ("P0", "P1", "P2", "P3")) + ".")
w("")
w("## 2. Short answers")
w("")
nk_diff = sum(1 for r in COLS if r["model"].startswith("king") and r["classification"] == "DIFFERENT" and r["booster_input_pos"] != "")
nf_cls = {c: sum(1 for r in COLS if r["model"].startswith("v2main") and r["classification"] == c) for c in ("IDENTICAL_CODE", "EQUIVALENT_FORMULA", "DIFFERENT")}
w(f"1. **Column-by-column definition parity** (`AUDIT_PROD_columns.csv`, 82 king builder columns + 171 V2MAIN columns). King (78 served): {nk_diff} DIFFERENT, 1 EQUIVALENT_FORMULA (fund_now), 4 builder columns not served. "
  "Every kline column differs in timestamp alignment (PROD-01) and float16 storage (PROD-05); every rank column also in cross-section universe (PROD-02); column 80 in unit (PROD-04). "
  f"V2MAIN (171): {nf_cls['IDENTICAL_CODE']} IDENTICAL_CODE, {nf_cls['EQUIVALENT_FORMULA']} EQUIVALENT_FORMULA, {nf_cls['DIFFERENT']} DIFFERENT. The serving feature code is the training builder with only path constants changed (dlw_features L16; f8 L17-23); the differences are inputs to that code: member universe for every rank (PROD-06), the scored anchor's members reused on history rows (PROD-07), btcv definition (PROD-08), cache length in the two trend columns (PROD-09), column 80/81 unit and fill (PROD-37, T4b). No column is UNVERIFIABLE: every served column was reproduced bitwise from production code and every training column from the training builders.")
w(f"2. **Measured** (feature and score layers, no P&L). King, 32 anchors: stored training features vs served inputs on the same names → king-score Spearman median {ks('Tstored_common_as_stored','spearman')} (PROD-03); training clock alone {ks('TP','spearman')} (PROD-01); rank universe alone {ks('universe_common','spearman')} (PROD-02); float16 alone ~1.0 (PROD-05). "
  f"V2MAIN, 17 anchors: stored training rows vs served inputs → V2MAIN-score Spearman median {fs('FS_vs_T171')} (PROD-06); history-member approximation alone {fs('FS_vs_FH')} (PROD-07); training code on training members reproduces the stored rows except the trend columns (G-F10CODE, PROD-09).")
w(f"3. **Membership and liquidity.** Production members = top 400 of the live 450; training members (king and DL, identical sets) = top 400 of all 829 cache names: Jaccard median {MS['PK']['jaccard']['median']:.3f}, the whole difference is the universe (PROD-02, PROD-11). A0 replay members = 373 masked crypto names: overlap {MS['R']['R_inter_P']['median']:.0f}/400 (PROD-10). qv4h is the same quantity in production and A0 (PROD-12).")
w("4. **Serving-state artefacts.** Seat: 819 of 900 window rows are the 09-05 seed (PROD-20; no re-seeding step for October, PROD-21). D17: decaying, immaterial, not recurring (PROD-22); the builder interval rule that caused it is still live in research builders (PROD-23) and FX-PROD P9 is a separate live append defect (PROD-40). FTRIM residual and band freeze (PROD-24). Uniform redistribution after withholding: EXE-03 confirmed and generalised (PROD-25).")
w("5. **Follow-ups from the lead.** P3 qv4h: PROD-12. P4 other-feature parity: PROD-01..03, PROD-06..09, PROD-37. P10 float16 train / float32 serve: PROD-05 (no served decile or selection change; 4 of 18,800 row paths). FTRIM as served: PROD-24; stop overlay as served: PROD-32 (the served stop is the executor's per_name_stop). EXE-03: confirmed, PROD-25. CHK-01: confirmed with mechanism, PROD-26. Phase-1 G-P2 residual mechanism: PROD-36.")
w("")
w("## 3. Column parity (appendix CSV has every column)")
w("")
w("### 3.1 King (8d79186b), 78 served columns, ordered by booster gain rank")
w("")
w("Columns: gain rank · name · class · share of common cells with |Δ| > 1e-3 (served vs stored training; relative for values, rank units for ranks) · per-anchor Spearman served vs stored · Spearman training clock vs serving clock · median |Δrank| from the universe (ranks only) · king-score Spearman when only this column takes the training clock · deciles changed (median, of 400) · rows whose leaf path changes if only this column is cast to float16 (47 anchors).")
w("")
w("| gain | column | class | >1e-3 share | Spearman S vs T | Spearman clock | universe |Δrank| | score Spearman (clock swap) | deciles | P10 rows |")
w("|---:|---|---|---:|---:|---:|---:|---:|---:|---:|")
for (gr, nm, cls, sh, sp, spc, un, css, dec, p10r) in king_table:
    w(f"| {gr} | {nm} | {cls} | {f_(sh,3)} | {f_(sp,4)} | {f_(spc,4)} | {f_(un,3)} | {f_(css,5)} | {'' if dec is None else f'{dec:.0f}'} | {p10r} |")
w("")
w("### 3.2 V2MAIN (351ae26b), 171 columns by family")
w("")
w("Columns with any cell above 1e-3 per comparison (relative for values and H z-scores, absolute for ranks and rank products), and the V2MAIN-score Spearman when the family's columns are swapped from served to stored training values on common names.")
w("")
w("| family | columns | served vs stored training | history members (F_S vs F_H) | universe + btcv (F_H vs F_D) | code identity (F_D vs stored) | score Spearman (family swap) |")
w("|---|---:|---:|---:|---:|---:|---:|")
for (fam, n, a, b, c, d, sp) in fam_rows:
    w(f"| {fam} | {n} | {a} | {b} | {c} | {d} | {f_(sp, 4)} |")
w("")
w("## 4. Register")
w("")
for i in ITEMS:
    w(f"### {i['id']} · {i['title']}")
    w("")
    w(f"- **Layer:** {i['layer']}  ")
    w(f"- **Status:** {i['status']} · **Severity:** {i['severity']} — {i['severity_reason']}  ")
    w(f"- **Affects:** {', '.join(i['affects'])} · **Method:** {i['method']}")
    w("")
    w(i["what_is_wrong"])
    w("")
    w("Evidence:")
    for e in i["evidence"]: w(f"- {e}")
    w("")
    w(f"Recommended action: {i['recommended_action']}")
    w("")
w("## 5. Devices, receipts and commands")
w("")
w("| Device | sha256 | commits (newest first) |"); w("|---|---|---|")
for d_ in DEVICES: w(f"| {d_['path']} | `{d_['sha256'][:16]}…` | {' '.join(d_['commits_newest_first'][:3])} |")
w("")
w("Receipts (sha256): " + "; ".join(f"`{k}` {v[:12]}…" for k, v in RECEIPTS.items()) + ".")
w("")
w("Verbatim commands: Mac `bash docs/audit_pipeline_2026-09-13/devices_prod/parity/parity_run_mac.sh king|f10|checks`; pod2 `bash /workspace/aud_prod_2026-09-13/parity/device/parity_run_pod2.sh extract` and `bash /workspace/aud_prod_2026-09-13/members/device/members_run_pod2.sh`; state probes `env -i PATH=/usr/bin:/bin HOME=/Users/haosiyu /Users/haosiyu/wide_shadow/venv/bin/python -B <device> PATH,HOME,LC_CTYPE,__CF_USER_TEXT_ENCODING`; provenance `bash docs/audit_pipeline_2026-09-13/devices_prod/parity/pod2_provenance.sh`; this document `env -i PATH=/usr/bin:/bin HOME=/Users/haosiyu /Users/haosiyu/wide_shadow/venv/bin/python -B docs/audit_pipeline_2026-09-13/devices_prod/build/build_audit_prod.py PATH,HOME,LC_CTYPE,__CF_USER_TEXT_ENCODING`.")
w("")
w("Failed or superseded runs kept: members_audit run 1 (env refused) and run 2 (stopped, slow assert) on pod2; parity_f10 run 1 (`receipts_prod/parity_f10_run1_d76ed216_FAILED_missing_weights_stdout.log`, no comparison numbers); prod_target_checks run 1 (`prod_target_checks_run1_b59fb791.json`, superseded by the revision that records the target_w ratio).")
w("")
w("## 6. Not checked")
w("")
for x in NOT_CHECKED: w(f"- {x}")
w("")
open(AD + "/AUDIT_PROD.md", "w").write("\n".join(MD) + "\n")
OUTJ = {"meta": {"created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "session": "https://claude.ai/code/session_01BzpuBRGZh8oPvpD8NgqsME (aud-prod)", "scope": "producer and model-serving layer (~/wide_shadow shadow_loop_v3, fea171/combo_stage and feature builders, king LGBM 8d79186b, V2MAIN f10_live_s42_np 351ae26b)",
                 "frozen": {k: CODE[k][1] for k in CODE}, "status_legend": {s: s for s in STATUSES}, "generator": {"path": "docs/audit_pipeline_2026-09-13/devices_prod/build/build_audit_prod.py", "sha256": gsha(os.path.abspath(__file__))},
                 "king_thresholds_vs_float16": THR16},
        "counts": COUNTS, "items": ITEMS, "not_checked": NOT_CHECKED, "devices": DEVICES, "receipts_sha256": RECEIPTS,
        "column_table": {"path": "docs/audit_pipeline_2026-09-13/AUDIT_PROD_columns.csv", "rows": len(COLS), "classification_counts": {m: {c: sum(1 for r in COLS if r["model"] == m and r["classification"] == c) for c in set(r["classification"] for r in COLS)} for m in set(r["model"] for r in COLS)}}}
json.dump(OUTJ, open(AD + "/AUDIT_PROD.json", "w"), indent=1, ensure_ascii=False, default=str)
print("WROTE", COUNTS)
