#!/usr/bin/env python3
"""ovn_identity.py — prereg §1.7 identity disclosure (docs/PREREG_old_vs_new_models_same_engine_2026-09-23.md, 8530d2b7f / 1217d786), written
BEFORE any NAV of the OLD-vs-NEW comparison exists. Reads model / fold / gate facts only; no prices, no returns.
  ① OLD: per anchor the King / F10 fold that scored it (object-B P3 records), that fold's label_end (object-B RUN_CONFIG_A0_main king_folds /
     f10_folds), gap in anchors, and an IN-SAMPLE flag = label_end > A (the fold's training labels reach past this anchor's start). Per segment.
  ② NEW: per fold (King incl. the 2022H2 warm-up fold; F10 per seed) max_train_label_end vs the first anchor it serves, gap in anchors, and the
     prereg test gap >= 60; per anchor of the combo axis the serving fold (King: KING_OOF model_sha256; F10: the fold's scores.npz rows),
     with every fold artifact sha-checked against the training receipts, and the lineage NEW target receipt -> F10_OOF / legs -> KING_OOF.
  ③ both scaled publication gates: the rule text quoted from the code (file, sha, line numbers), the action on failure, per-segment counts of
     published / fallback / hold anchors for both readings, mean member count n per segment, and the integer equivalence of the scaled floors
     (ceil(380 n / 400) vs int(np.ceil(.95 n)); ceil(150 n / 400) vs int(np.ceil(.375 n))) for every n in 1..829.
  ④ / ⑤ are attached from the adapter receipts and the config-diff receipt (paths given on the command line; each sha recorded).
usage: env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B ovn_identity.py PATH,HOME,LC_CTYPE <out.json> [<adapter_rcpt_s42> <adapter_rcpt_s2027> <config_diff_rcpt>]
"""
import os, sys, json, time, math, hashlib, calendar, collections

import numpy as np

WL = set(sys.argv[1].split(",")); extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
OUT = sys.argv[2]; ATTACH = sys.argv[3:6]
H4 = 14400; DAY = 86400


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def ts(iso): return calendar.timegm(time.strptime(iso, "%Y-%m-%dT%H:%M:%SZ"))
def iso(t): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(t)))


def pin(p, want):
    got = sha(p); assert got == want, f"sha mismatch {p}: {got[:16]} != {want[:16]}"; return {"path": p, "sha256": got}


SEG = {"2023H2": ("2023-06-30T04:00:00Z", "2023-12-31T20:00:00Z"), "2024": ("2024-01-01T00:00:00Z", "2024-12-31T20:00:00Z"),
       "2025": ("2025-01-01T00:00:00Z", "2025-12-31T20:00:00Z"), "2026 (report only)": ("2026-01-01T00:00:00Z", "2026-08-31T00:00:00Z"),
       "2026-08-31T04Z..09-18T20Z (describe only)": ("2026-08-31T04:00:00Z", "2026-09-18T20:00:00Z")}
SEGT = {k: (ts(a), ts(b)) for k, (a, b) in SEG.items()}


def seg_of(A):
    for k, (a, b) in SEGT.items():
        if a <= A <= b: return k
    return None


def month_start(A):
    g = time.gmtime(int(A)); return calendar.timegm((g.tm_year, g.tm_mon, 1, 0, 0, 0))


rec = {"doc": "IDENTITY_DISCLOSURE (prereg §1.7)", "device": "ovn_identity.py", "self_sha256": sha(os.path.abspath(__file__)), "utc": iso(time.time()),
       "written_before_any_nav": True, "segments": SEG, "inputs": {}}
OB = "/workspace/object_b_2026-09-19"; NB = "/workspace/codex_research/QNT-2026-0907/combo_20260923"; NR = "/workspace/old_vs_new_2026-09-23"

# ───────── ① OLD ─────────
I = rec["inputs"]
I["old_targets_receipt"] = pin(f"{OB}/receipts/TARGETS_A0_main.json", "5ebac7205afc2cd0b5a0c85bd3daf2e2210e56dad9b0461fd015025cb4518385")
I["old_targets_npz"] = pin(f"{OB}/work/A0_main/TARGETS_A0_main.npz", "b9f0dc9f2011f9defaac80b116415de3f4d75ffb497cbb9533cd995879036c41")
I["old_run_config"] = pin(f"{OB}/receipts/RUN_CONFIG_A0_main.json", "0b4b06da2f204832be3eeb124dcdd2ab72399f2dba21936f29c185f80d86f799")
I["old_p3_records"] = pin(f"{OB}/work/A0_main/P3.json", "cff3e160f4a4961e97043cdcdb93a105c24694f83931509dc5539bac72826bcd")
TR = json.load(open(I["old_targets_receipt"]["path"])); RC = json.load(open(I["old_run_config"]["path"])); P3 = json.load(open(I["old_p3_records"]["path"]))
assert TR["p3_json_sha256"] == I["old_p3_records"]["sha256"], "OLD targets receipt was not built from this P3.json"
kle = {int(y): ts(v["label_end"]) for y, v in RC["king_folds"].items()}; fle = {int(y): ts(v["label_end"]) for y, v in RC["f10_folds"].items()}
old = {"receipt_fields": {"king_fold_served_by_year": TR["king_fold_served_by_year"], "f10_fold_served_by_year": TR["f10_fold_served_by_year"],
                          "king_first_served": TR["king_first_served"], "f10_first_served": TR["f10_first_served"], "B_CORE_start": TR["B_CORE_start"]},
       "folds": {"king": {str(y): {"file": v["file"], "sha256": v["sha256"], "label_end": v["label_end"]} for y, v in RC["king_folds"].items()},
                 "f10": {str(y): {"np": v["np"], "sha256": v["sha256"], "trained_through": v["trained_through"], "label_end": v["label_end"]} for y, v in RC["f10_folds"].items()}},
       "serving_rules": {"king": "b_lib.FoldBooster('folds'): latest fold Y with label_end[Y] < A - 30 d; none => king leg neutral (all NaN)",
                         "f10": "b_lib.f10_fold_for: latest fold Y with label_end[Y] < first second of A's UTC month"}}
per = collections.defaultdict(lambda: collections.defaultdict(lambda: collections.Counter()))
gaps = collections.defaultdict(lambda: collections.defaultdict(list)); rule_viol = collections.Counter(); insample = collections.Counter()
for r in P3["records"]:
    A = int(r["anchor"]); s = seg_of(A)
    if s is None: continue
    kg = r.get("king") or {}; f1 = r.get("f10") or {}
    kf = kg.get("fold"); ff = f1.get("fold")
    per[s]["king_fold"][str(kf)] += 1; per[s]["f10_fold"][str(ff)] += 1
    if kf is not None:
        le = kle[int(kf)]; assert int(kg["label_end"]) == le, ("P3 king label_end vs run config", A)
        gaps[s]["king"].append((A - le) // H4)
        if not (le < A - 30 * DAY): rule_viol["king"] += 1
        if le > A: insample["king"] += 1
    if ff is not None:
        le = fle[int(ff)]; gaps[s]["f10"].append((A - le) // H4)
        if not (le < month_start(A)): rule_viol["f10"] += 1
        if le > A: insample["f10"] += 1
old["per_segment"] = {s: {"king_fold_counts": dict(per[s]["king_fold"]), "f10_fold_counts": dict(per[s]["f10_fold"]),
                          "king_gap_anchors_min": (int(min(gaps[s]["king"])) if gaps[s]["king"] else None),
                          "f10_gap_anchors_min": (int(min(gaps[s]["f10"])) if gaps[s]["f10"] else None),
                          "n_anchors": int(sum(per[s]["king_fold"].values()))} for s in SEG if s in per}
old["serving_rule_violations"] = dict(rule_viol); old["in_sample_anchors"] = {"king": insample["king"], "f10": insample["f10"]}
old["in_sample_note"] = ("IN-SAMPLE := the serving fold's label_end > A. Counted over every anchor of the five segments. 0 means no OLD anchor in "
                         "these segments is scored by a fold whose training labels reach it. The F10 gap at a year's first anchor is 1 anchor "
                         "(label_end = 20Z of Dec 31, served from Jan 1 00Z): out of sample but WITHOUT the 60-anchor embargo NEW uses; the King "
                         "gap is >= 181 anchors by the 30-day rule. OLD keeps serving the previous year's King fold for the first 30 days of 2024/2025/2026.")
rec["item1_OLD_folds"] = old

# ───────── ② NEW ─────────
KR_p = f"{NB}/corrected_combo_v1d/king/TRAIN_RECEIPT.json"; KO_p = f"{NB}/corrected_combo_v1d/king/KING_OOF.npz"
LR_p = f"{NB}/corrected_combo_v1d/data/LEGS_RECEIPT.json"
KR = json.load(open(KR_p)); LR = json.load(open(LR_p))
I["new_king_train_receipt"] = {"path": KR_p, "sha256": sha(KR_p)}; I["new_legs_receipt"] = {"path": LR_p, "sha256": sha(LR_p)}
I["new_king_oof"] = pin(KO_p, KR["predictions_sha256"])
assert LR["input_sha"][KO_p] == I["new_king_oof"]["sha256"] and LR["input_sha"][KR_p] == I["new_king_train_receipt"]["sha256"], "legs were not built from this King OOF"
KO = np.load(KO_p); KE = KO["E_ts"].astype(np.int64); KM = KO["model_sha256"]
kfold = {f["model_sha256"]: f for f in KR["folds"]}
for f in KR["folds"]: assert sha(f["model_path"]) == f["model_sha256"], ("king model file drift", f["fold"])
new = {"king_folds": [], "f10_folds": {}, "per_anchor": {}}
for f in KR["folds"]:
    served = KE[KM == f["model_sha256"]]
    new["king_folds"].append({"fold": f["fold"], "model_sha256": f["model_sha256"], "max_train_label_end": iso(f["max_train_label_end"]),
                              "first_served": iso(served.min()), "last_served": iso(served.max()), "n_served": int(len(served)),
                              "gap_first_anchors": int((served.min() - f["max_train_label_end"]) // H4),
                              "gap_ge_60": bool((served.min() - f["max_train_label_end"]) // H4 >= 60),
                              "note": ("seat/leg-return history only: the NEW combo axis starts 2023-01-01T00Z" if f["fold"] == "2022H2_WARMUP" else None)})
TGT = {}
_DT0 = np.load(f"{NB}/corrected_combo_v1d/data/dlw_targets.npz", allow_pickle=True); FULL_AXIS = _DT0["E_ts"].astype(np.int64); del _DT0
for seed in ("42", "2027"):
    TRp = f"{NR}/new_targets/combo_s{seed}/TARGET_RECEIPT.json"; T = json.load(open(TRp)); TGT[seed] = T
    fdir = f"{NB}/corrected_combo_v1d/f10_s{seed}"; FR_p = os.path.realpath(fdir) + "/TRAIN_RECEIPT.json"; FR = json.load(open(FR_p))
    oof_key = f"{NB}/corrected_combo_v1d/f10_s{seed}/F10_OOF.npz"
    assert T["inputs"][oof_key] == FR["pred_sha256"], "NEW target receipt not built from this F10 OOF"
    assert T["inputs"][f"{NB}/corrected_combo_v1d/data/f10v2_legs.npz"] == LR["artifact_sha"], "NEW target receipt not built from these legs"
    for p, h in FR["fold_artifacts"].items():
        assert sha(os.path.realpath(fdir) + p.split(f"f10_s{seed}")[1]) == h, ("F10 fold artifact drift", p)
    rows = []
    for fold in FR["folds"]:
        fr = json.load(open(f"{os.path.realpath(fdir)}/{fold}/FOLD_RECEIPT.json")); S = np.load(f"{os.path.realpath(fdir)}/{fold}/scores.npz")
        E = S["E_ts"].astype(np.int64); r = S["rows"].astype(np.int64); served = E      # scores.npz E_ts = the fold's served anchors; rows index the full axis
        assert np.array_equal(FULL_AXIS[r], E), ("F10 fold rows vs full axis", seed, fold)
        ad = fr["admission"]
        rows.append({"fold": fold, "max_train_label_end": iso(ad["max_train_label_end"]), "cutoff": iso(ad["cutoff"]), "test_start": iso(ad["test_start"]),
                     "first_served": iso(served.min()), "last_served": iso(served.max()), "n_served": int(len(served)),
                     "gap_first_anchors": int((served.min() - ad["max_train_label_end"]) // H4), "gap_ge_60": bool((served.min() - ad["max_train_label_end"]) // H4 >= 60),
                     "model_sha256": fr["model_sha256"], "seed": fr["seed"]})
    new["f10_folds"][f"s{seed}"] = rows
    new["per_anchor"][f"s{seed}"] = {"f10_min_gap_anchors": int(min(r_["gap_first_anchors"] for r_ in rows)), "f10_all_folds_gap_ge_60": all(r_["gap_ge_60"] for r_ in rows),
                                     "f10_train_receipt": {"path": FR_p, "sha256": sha(FR_p)}}
combo_axis = np.arange(ts("2023-01-01T00:00:00Z"), ts("2026-09-18T20:00:00Z") + 1, H4, dtype=np.int64)
kpos = {int(t): i for i, t in enumerate(KE)}; kgap = []
for A in combo_axis:
    m = KM[kpos[int(A)]]; f = kfold[m]; kgap.append((int(A) - f["max_train_label_end"]) // H4)
new["per_anchor"]["king_min_gap_anchors_on_combo_axis"] = int(min(kgap)); new["per_anchor"]["king_all_gap_ge_60"] = bool(min(kgap) >= 60)
new["embargo_rule"] = "King: king_folds.fold_rows train = anchors with a + 4h <= start - 60*4h (train_king.py asserts max_train_label_end <= score_start - 60*4h); F10: train_f10.py cutoff = first test anchor - 60*4h, train anchors with a + 4h <= cutoff. Labels are y4s (4h) in both trainers."
rec["item2_NEW_folds"] = new

# ───────── ③ gates ─────────
def quote(path, want_sha, needles):
    assert sha(path) == want_sha, f"source sha {path}"
    L = open(path, encoding="utf-8").read().split("\n"); out = []
    for nd in needles:
        hit = [(i + 1, L[i].strip()) for i in range(len(L)) if nd in L[i]]
        assert len(hit) >= 1, f"needle not found in {path}: {nd}"
        out += [{"line": h[0], "text": h[1]} for h in hit]
    return {"path": path, "sha256": want_sha, "lines": out}


gates = {"OLD_scaled": {"code": quote(f"{OB}/devices/b_driver.py", "aaf82ba6cf602725bc840327de6d0551f684dd28d3c3f6e109ce59cff93ee94a",
                                      ["n = len(pm); okf =", "inside = all(", "n_in = int(sum(", "f380 = math.ceil(380 * n / 400)", "scaled = (okf >= f380)",
                                       'rec["scaled_ok"] = bool(scaled or lit_ok)', 'rec["traded_scaled"] = "combo" if', 'rec["traded_scaled"] = rec["traded_lit"] = "hold(producer_skip)"']),
                         "rule": "publish combo iff okf >= ceil(380 n/400) AND 0.4 <= gross <= 1.2 AND names >= ceil(150 n/400) AND every weight inside the live universe AND names in universe >= ceil(150 n/400) AND gross in universe > 0.4 AND the producer's king file exists (or the as-coded literal gate passed); n = producer members at A",
                         "on_failure": "TRADE THE PRODUCER'S KING FILE (kind 1) — the King-form fallback; producer skip => hold (kind 0)"},
         "OLD_literal": {"code": quote(f"{OB}/devices/combo_stage_replay_3520d363.py", "92c49fa82d4c5c1bdb70c6155c0c3e7bfe3c5f012e1db0aeb686ef1fbcd6e1d8",
                                       ["assert int(okf.sum()) >= 380", "assert 0.4 <= _g <= 1.2", "assert len(_nz) >= 150", 'assert _pt["n_in_universe"] >= 150']),
                         "rule": "production COMBO_LIVE preflight, constants 380 / [0.4, 1.2] / 150 / reader check", "on_failure": "king file (fail-open)"},
         "NEW_scaled_diagnostic_and_literal": {"code": quote(f"{NB}/devices/combo_target.py", "d7577e824298fb90a554f35ac9c4d634202a4ed7e4e00cabc597a2d4eafdb544",
                                                             ["coverage_gate=380 if publication=='literal' else int(np.ceil(.95*n))", "if okf.sum()<coverage_gate",
                                                              "if not .4<=gross<=1.2", "if names<names_gate", "return {'accepted':not reasons"]),
                                               "state_and_hold": quote(f"{NB}/devices/continuous_combo.py", "1501c9f63641bf447c4cb33661d08da25ced0948f9fae63cebb44cdfd1995d21",
                                                                       ["A false trade_mask means HOLD CONTRACTS", "if result['accepted']:", "out['trade_mask'][i]=True",
                                                                        "out['weights'][i]=np.where(np.abs(result['raw'])>1e-9,result['raw'],0.)", "if not ready[i]:"]),
                                               "rule": "scaled_diagnostic: publish iff okf >= int(np.ceil(.95 n)) AND 0.4 <= gross <= 1.2 AND names >= int(np.ceil(.375 n)); literal: 380 / [0.4, 1.2] / 150; n = len(members[i]) of NEW's corrected member list; states evolve on every ready anchor",
                                               "on_failure": "HOLD (trade_mask False: keep contracts; never King substitution); unready causal legs => HOLD"}}
eq380 = [n for n in range(1, 830) if math.ceil(380 * n / 400) != int(np.ceil(.95 * n))]; eq150 = [n for n in range(1, 830) if math.ceil(150 * n / 400) != int(np.ceil(.375 * n))]
gates["floor_equivalence_n_1_to_829"] = {"ceil380_vs_ceil095_mismatch_n": eq380, "ceil150_vs_ceil0375_mismatch_n": eq150}
OZ = np.load(I["old_targets_npz"]["path"]); OA = OZ["anchor"].astype(np.int64)
cnt = {}
for R_ in ("scaled", "lit"):
    k = OZ[f"{R_}_kind"]; c = {}
    for s, (a, b) in SEGT.items():
        m = (OA >= a) & (OA <= b)
        if m.any(): c[s] = {"n_anchors": int(m.sum()), "combo_published": int(np.sum(k[m] == 2)), "king_fallback": int(np.sum(k[m] == 1)), "hold": int(np.sum(k[m] == 0))}
    cnt[f"OLD_{R_}"] = c
nm_old = collections.defaultdict(list)
for r in P3["records"]:
    s = seg_of(int(r["anchor"]))
    if s and r.get("n_members") is not None: nm_old[s].append(int(r["n_members"]))
DT = np.load(f"{NB}/corrected_combo_v1d/data/dlw_targets.npz", allow_pickle=True); I["new_dlw_targets"] = {"path": f"{NB}/corrected_combo_v1d/data/dlw_targets.npz", "sha256": sha(f"{NB}/corrected_combo_v1d/data/dlw_targets.npz")}
assert I["new_dlw_targets"]["sha256"] == TGT["42"]["inputs"][I["new_dlw_targets"]["path"]]
DE = DT["E_ts"].astype(np.int64); DM = DT["members"]; nm_new = collections.defaultdict(list)
for i, A in enumerate(DE):
    s = seg_of(int(A))
    if s: nm_new[s].append(len(DM[i]))
for seed in ("42", "2027"):
    for R_, pol in (("scaled", "scaled_diagnostic"), ("lit", "literal")):
        Z = np.load(f"{NR}/new_targets/combo_s{seed}/{pol}.npz"); assert sha(f"{NR}/new_targets/combo_s{seed}/{pol}.npz") == TGT[seed]["policies"][pol]["sha"]
        E = Z["E_ts"].astype(np.int64); tm = Z["trade_mask"]; rs = Z["reason"]; c = {}
        for s, (a, b) in SEGT.items():
            m = (E >= a) & (E <= b)
            if m.any(): c[s] = {"n_anchors": int(m.sum()), "combo_published": int(tm[m].sum()), "king_fallback": 0, "hold": int((~tm[m]).sum()),
                                "hold_reasons": dict(collections.Counter(rs[m & ~tm].tolist()))}
        cnt[f"NEW_s{seed}_{R_}"] = c
gates["publishable_anchor_counts_per_segment"] = cnt
gates["mean_member_count_n_per_segment"] = {"OLD (producer members, P3 n_members)": {s: float(np.mean(v)) for s, v in nm_old.items()},
                                            "NEW (dlw_targets members)": {s: float(np.mean(v)) for s, v in nm_new.items()}}
gates["NAMED_CONFOUNDS"] = [
    "C1 FAILURE ACTION DIFFERS: when the scaled gate fails OLD trades the producer's King file (the King-form fallback, kind 1) while NEW HOLDS its contracts. Any OLD-vs-NEW difference contains this publication-semantics difference; it is not a pure model difference.",
    "C2 GATE CONDITIONS DIFFER: OLD additionally requires every weight inside the live universe, names-in-universe >= ceil(150 n/400), gross-in-universe > 0.4 and an existing King file; NEW has none of these (its chain is masked to the legal set). NEW's F10 coverage floor int(np.ceil(.95 n)) and names floor int(np.ceil(.375 n)) equal OLD's ceil(380 n/400) / ceil(150 n/400) except for the n listed in floor_equivalence_n_1_to_829.",
    "C3 n DIFFERS: OLD n = the producer's member count at A (as-trained member rule); NEW n = NEW's corrected member list. The same formula therefore gives different floors.",
    "C4 EMBARGO / FRESHNESS DIFFERS: OLD F10 folds are yearly with a 1-anchor gap at the year start and OLD King is served with a 30-day lag (previous year's fold for January); NEW King is yearly with a 60-anchor embargo, NEW F10 is yearly for 2023/2024 and MONTHLY from 2025-01 with a 60-anchor embargo. From 2025 NEW's F10 is refreshed 12x a year, OLD's once.",
    "C5 STATE START: NEW's combo state starts at zero on 2023-01-01T00Z (hypothetical common start); OLD's chain cold-starts 2022-01-31. Both are warm by the judgment window (2023-06-30T04Z), but NEW's seat/state history is 6 months long there.",
]
rec["item3_gates"] = gates

# ───────── ④ ⑤ attached ─────────
names = ("item4_adapter_s42", "item4_adapter_s2027", "item5_config_diff")
for nm, p in zip(names, ATTACH):
    d = json.load(open(p)); rec[nm] = {"path": p, "sha256": sha(p), "content": d}
for nm in names[len(ATTACH):]:
    rec[nm] = "NOT YET ATTACHED (run again with the receipt path)"
json.dump(rec, open(OUT + ".tmp", "w"), indent=1, ensure_ascii=False); os.replace(OUT + ".tmp", OUT)
print("OVN_IDENTITY wrote", OUT, sha(OUT), "| OLD in-sample anchors", old["in_sample_anchors"], "rule violations", dict(rule_viol),
      "| NEW king min gap", new["per_anchor"]["king_min_gap_anchors_on_combo_axis"], "f10 min gap", {k: v["f10_min_gap_anchors"] for k, v in new["per_anchor"].items() if k.startswith("s")},
      "| attached", len(ATTACH), flush=True)
