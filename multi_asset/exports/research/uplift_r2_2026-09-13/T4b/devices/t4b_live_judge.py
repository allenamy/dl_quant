#!/usr/bin/env python3
"""t4b_live_judge.py — Mac, read-only (PREREG_T4b §5-§6). Gates and per-anchor deltas for the snapshot-forward live window.
Arms: served (parity devices), v2inj (one-line combo device fed the replay's own EMA acc), v2v0 (one-line combo device fed the v0
feed), seatK1 (parity devices; seat history with the 09-05 seeded king rows re-scored with column 80 = v1). Descriptive only.
Launch: env -i PATH=/usr/bin:/bin HOME=/Users/haosiyu /Users/haosiyu/wide_shadow/venv/bin/python -B devices/t4b_live_judge.py <whitelist>"""
import os, sys, json, time, hashlib, glob
WHITE = set(x for x in sys.argv[1].split(",") if x) if len(sys.argv) > 1 else None
assert WHITE, "whitelist argv[1]"
assert sorted(k for k in os.environ if k not in WHITE) == [], ("ENV WHITELIST VIOLATION", sorted(os.environ))
import numpy as np
from scipy.stats import rankdata
HERE = os.path.dirname(os.path.abspath(__file__)); T4B = os.path.dirname(HERE); PRIV = T4B + "/private"; R = T4B + "/receipts"
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
_fr = open(R + "/PREREG_FREEZE_sha.txt").readline().split(); PREREG_SHA = _fr[2]; assert sha(T4B + "/PREREG_T4b_v2main_feature_skew_2026-09-13.md") == PREREG_SHA
ARMS = ("served", "v2inj", "v2v0", "seatK1")
REC = {a: list(np.load(PRIV + f"/replay_rec_{a}.npy", allow_pickle=True)) for a in ARMS}
ANCH = [int(r["anchor"]) for r in REC["served"]]
for a in ARMS: assert [int(r["anchor"]) for r in REC[a]] == ANCH, a
RCP = {a: json.load(open(glob.glob(R + f"/T4B_REPLAY_{a}_*.json")[0])) for a in ARMS}
for a in ARMS: assert RCP[a]["prereg_sha256"] == PREREG_SHA and RCP[a]["arm"] == a
CFG = json.load(open("/Users/haosiyu/wide_shadow/shadow_bundle/config.json")); SYMS = CFG["symbols_panel"]
def jw(arm, sub, A): return json.load(open(PRIV + f"/replay_home_{arm}/state/{sub}/{A}.json"))["weights"]
G = {}
# ---- PCB: served reproduces live bitwise (king weights, combo target_live, target_combo)
pcb = []
for c in RCP["served"]["anchors"]:
    cb = c.get("combo") or {}
    pcb.append(dict(anchor=c["anchor"], king_Linf=c["weights_npz_Linf"], king_content_sha_equal=c["content_sha_equal"], king_json_Linf=c["target_live_json_Linf"],
                    combo_rc=cb.get("rc"), target_live_Linf=cb.get("target_live_Linf"), target_combo_Linf=cb.get("target_combo_Linf"), w3m_equal=cb.get("w3m_equal")))
G["PCB"] = dict(per_anchor=pcb, PASS=bool(all(p["king_Linf"] == 0.0 and p["king_content_sha_equal"] and p["king_json_Linf"] == 0.0 and p["combo_rc"] == 0 and p["target_live_Linf"] == 0.0 and p["target_combo_Linf"] == 0.0 and p["w3m_equal"] for p in pcb)))
# ---- PC-INJ: v2inj == served bitwise
def same(x, y):
    if isinstance(x, tuple): return all(np.array_equal(a, b) for a, b in zip(x, y))
    return bool(np.array_equal(x, y))
inj_keys = ("X", "pred", "king_val", "king_idx", "combo_X171", "combo_scol", "combo_f10", "panel_fe_last", "panel_fn_last", "state_H_f10", "state_H_kc", "state_H_fc")
inj = {k: all(same(REC["served"][i][k], REC["v2inj"][i][k]) for i in range(len(ANCH))) for k in inj_keys}
inj["target_live_combo"] = all(jw("served", "target_live_combo", A) == jw("v2inj", "target_live_combo", A) for A in ANCH)
inj["target_combo"] = all(jw("served", "target_combo", A) == jw("v2inj", "target_combo", A) for A in ANCH)
G["PC_INJ"] = dict(**inj, PASS=bool(all(inj.values())))
# ---- ONE-PLACE: v2v0 differs from served only through V2MAIN column 80
mk = json.load(open(R + "/RECEIPT_T4b_mk_v2col80_device.json"))
one = dict(diff_changed_lines=mk["diff_changed_lines"], king_stage_bitwise=True, scol_equal=True, X171_other_cols_bitwise=True, f10_equal_where_col80_equal=True, panel_fn_bitwise=True,
           rows_col80_equal=0, rows_col80_differ=0)
for i, A in enumerate(ANCH):
    s, v = REC["served"][i], REC["v2v0"][i]
    if not all(same(s[k], v[k]) for k in ("X", "pred", "king_val", "king_idx")): one["king_stage_bitwise"] = False
    if not np.array_equal(s["combo_scol"], v["combo_scol"]): one["scol_equal"] = False; continue
    oth = [c for c in range(171) if c != 80]
    if not np.array_equal(s["combo_X171"][:, oth], v["combo_X171"][:, oth]): one["X171_other_cols_bitwise"] = False
    eq = s["combo_X171"][:, 80] == v["combo_X171"][:, 80]; one["rows_col80_equal"] += int(eq.sum()); one["rows_col80_differ"] += int((~eq).sum())
    if not np.array_equal(s["combo_f10"][eq], v["combo_f10"][eq]): one["f10_equal_where_col80_equal"] = False
    if not np.array_equal(s["panel_fn_last"], v["panel_fn_last"]): one["panel_fn_bitwise"] = False
G["ONE_PLACE"] = dict(**one, PASS=bool(one["diff_changed_lines"] == 1 and one["king_stage_bitwise"] and one["scol_equal"] and one["X171_other_cols_bitwise"] and one["f10_equal_where_col80_equal"] and one["panel_fn_bitwise"]))
# ---- V1R: the feed's rate*8/iv reconstruction vs the served V2MAIN panel value on scored members
FEED = np.load(PRIV + "/v0_feed_fwd.npz", allow_pickle=True); FA = {int(a): k for k, a in enumerate(FEED["anchors"])}
ra, rb_ = [], []; bad = {}
for i, A in enumerate(ANCH):
    s = REC["served"][i]; sc = s["combo_scol"]; a_ = np.float32(FEED["V1R"][FA[A]][sc]); b_ = s["panel_fe_last"][sc]
    ok = np.isfinite(a_) & (np.abs(b_) >= 1e-7); ra.append(a_[ok]); rb_.append(b_[ok])
    rel = np.abs(a_[ok].astype(np.float64) - b_[ok]) / np.abs(b_[ok])
    for j in sc[ok][rel > 1e-3]: bad[SYMS[j]] = bad.get(SYMS[j], 0) + 1
rel = np.abs(np.concatenate(ra).astype(np.float64) - np.concatenate(rb_)) / np.abs(np.concatenate(rb_))
G["V1R"] = dict(n=int(len(rel)), median_rel=float(np.median(rel)), share_le_1e3=float((rel <= 1e-3).mean()), share_le_1e6=float((rel <= 1e-6).mean()), max_rel=float(rel.max()),
                names_over_1e3=dict(sorted(bad.items(), key=lambda x: -x[1])[:25]))
G["V1R"]["PASS"] = bool(G["V1R"]["median_rel"] <= 1e-4 and G["V1R"]["share_le_1e3"] >= 0.95)
for nm, f in (("ZH", "RECEIPT_T4b_zh_gate.json"), ("SA", "RECEIPT_T4b_seat_override.json"), ("SL", "RECEIPT_T4b_seat_lr.json")):
    J = json.load(open(R + "/" + f)); G[nm] = J.get("result", J.get("gate_SA", J.get("gate_SL")))
    G[nm + "_receipt_sha256"] = sha(R + "/" + f)
# ---- per-anchor deltas
def spear(a, b):
    ra_ = rankdata(a); rb2 = rankdata(b); ra_ -= ra_.mean(); rb2 -= rb2.mean(); den = np.sqrt((ra_ * ra_).sum() * (rb2 * rb2).sum()); return float((ra_ * rb2).sum() / den) if den > 0 else float("nan")
def dec(x): n = len(x); r = rankdata(x); return np.minimum(9, np.floor(10 * (r - 0.5) / n)).astype(np.int8)
def wstats(w0, w1):
    keys = sorted(set(w0) | set(w1)); a = np.array([w0.get(k, 0.0) for k in keys]); b = np.array([w1.get(k, 0.0) for k in keys]); G0 = np.abs(a).sum(); G1 = np.abs(b).sum()
    return dict(Linf=float(np.abs(a - b).max()), L1=float(np.abs(a - b).sum()), L1_norm=float(np.abs(a / G0 - b / G1).sum()), gross_arm=float(G0), gross_served=float(G1), net_arm=float(a.sum()), net_served=float(b.sum()), corr=float(np.corrcoef(a, b)[0, 1]))
def sstats(x, y):
    a = np.zeros(829); b = np.zeros(829); a[x[0]] = x[1]; b[y[0]] = y[1]; Ga = np.abs(a).sum(); Gb = np.abs(b).sum()
    return dict(Linf=float(np.abs(a - b).max()), L1_norm=float(np.abs(a / Ga - b / Gb).sum()) if Ga > 0 and Gb > 0 else None)
ROWS = []
for i, A in enumerate(ANCH):
    s, v, k1 = REC["served"][i], REC["v2v0"][i], REC["seatK1"][i]
    m = np.array(s["members"]); ivmap = {int(j): float(iv) for j, iv in zip(m, s["iv_last"])}; sc = s["combo_scol"]; iv = np.array([ivmap.get(int(j), np.nan) for j in sc])
    ch = dec(v["combo_f10"]) != dec(s["combo_f10"]); cls = {"all": np.ones(len(sc), bool), "4h": iv == 4.0, "1h": iv == 1.0, "8h": iv == 8.0}
    ratio = s["combo_X171"][:, 80].astype(np.float64) / np.where(v["combo_X171"][:, 80] != 0, v["combo_X171"][:, 80], np.nan)
    row = dict(anchor=A, utc=time.strftime("%Y-%m-%d %HZ", time.gmtime(A)), scored=int(len(sc)),
               v2=dict(f10_spearman=spear(v["combo_f10"], s["combo_f10"]), decile_change={c: dict(n=int(msk.sum()), changed=int(ch[msk].sum())) for c, msk in cls.items()},
                       col80_served_over_v0_median={c: (float(np.nanmedian(ratio[msk])) if np.isfinite(ratio[msk]).any() else None) for c, msk in cls.items()},
                       state_fc=sstats(v["state_H_fc"], s["state_H_fc"]), state_f10=sstats(v["state_H_f10"], s["state_H_f10"]),
                       combo_target_live=wstats(jw("v2v0", "target_live_combo", A), jw("served", "target_live_combo", A)), w3m_equal=bool(v.get("w3_masked") == s.get("w3_masked"))),
               seat=dict(w3_served=list(map(float, s["w3"])), w3_seatK1=list(map(float, k1["w3"])), w3m_served=s.get("w3_masked"), w3m_seatK1=k1.get("w3_masked"),
                         king_target=wstats(jw("seatK1", "target_live", A), jw("served", "target_live", A)), combo_target_live=wstats(jw("seatK1", "target_live_combo", A), jw("served", "target_live_combo", A)),
                         state_fc=sstats(k1["state_H_fc"], s["state_H_fc"]), state_kc=sstats(k1["state_H_kc"], s["state_H_kc"]), king_stage_X_pred_bitwise=bool(same(k1["X"], s["X"]) and same(k1["pred"], s["pred"]))))
    ROWS.append(row)
def summ(vals): v = np.array([x for x in vals if x is not None], float); return dict(median=float(np.median(v)), max=float(v.max()), min=float(v.min()), mean=float(v.mean()), n=int(len(v)))
SUMMARY = dict(anchors=[r["utc"] for r in ROWS],
               v2=dict(f10_spearman=summ([r["v2"]["f10_spearman"] for r in ROWS]),
                       decile_change_share={c: float(sum(r["v2"]["decile_change"][c]["changed"] for r in ROWS) / max(sum(r["v2"]["decile_change"][c]["n"] for r in ROWS), 1)) for c in ("all", "4h", "1h", "8h")},
                       decile_cells={c: int(sum(r["v2"]["decile_change"][c]["n"] for r in ROWS)) for c in ("all", "4h", "1h", "8h")},
                       col80_ratio_4h_median=summ([r["v2"]["col80_served_over_v0_median"]["4h"] for r in ROWS]), col80_ratio_8h_median=summ([r["v2"]["col80_served_over_v0_median"]["8h"] for r in ROWS]),
                       state_fc_L1_norm=summ([r["v2"]["state_fc"]["L1_norm"] for r in ROWS]), combo_target_live_Linf=summ([r["v2"]["combo_target_live"]["Linf"] for r in ROWS]),
                       combo_target_live_L1_norm=summ([r["v2"]["combo_target_live"]["L1_norm"] for r in ROWS]), combo_target_live_corr=summ([r["v2"]["combo_target_live"]["corr"] for r in ROWS]),
                       w3m_equal_all=bool(all(r["v2"]["w3m_equal"] for r in ROWS))),
               seat=dict(w3m_king_seatK1_minus_served=summ([r["seat"]["w3m_seatK1"][0] - r["seat"]["w3m_served"][0] for r in ROWS]), w3m_king_served=summ([r["seat"]["w3m_served"][0] for r in ROWS]),
                         king_target_L1_norm=summ([r["seat"]["king_target"]["L1_norm"] for r in ROWS]), combo_target_live_Linf=summ([r["seat"]["combo_target_live"]["Linf"] for r in ROWS]),
                         combo_target_live_L1_norm=summ([r["seat"]["combo_target_live"]["L1_norm"] for r in ROWS]), king_stage_X_pred_bitwise_all=bool(all(r["seat"]["king_stage_X_pred_bitwise"] for r in ROWS))))
RC = dict(self_sha256=sha(os.path.abspath(__file__)), prereg_sha256=PREREG_SHA, replay_receipts={a: sha(glob.glob(R + f"/T4B_REPLAY_{a}_*.json")[0]) for a in ARMS},
          replay_recs={a: sha(PRIV + f"/replay_rec_{a}.npy") for a in ARMS}, v0_feed_fwd_sha256=sha(PRIV + "/v0_feed_fwd.npz"), gates=G, summary=SUMMARY, per_anchor=ROWS,
          env=dict(whitelist=sorted(WHITE), actual={k: os.environ[k] for k in sorted(os.environ)}), numpy=np.__version__, built_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
json.dump(RC, open(R + "/RECEIPT_T4b_live_judge.json", "w"), indent=1, default=str)
print(json.dumps(dict(gates={k: (v if k != "PCB" else {"PASS": v["PASS"]}) for k, v in G.items()}, summary=SUMMARY), indent=1, default=str))
assert G["PC_INJ"]["PASS"] and G["ONE_PLACE"]["PASS"], "PC-INJ or ONE-PLACE FAIL"
print("DONE_t4b_live_judge")
