#!/usr/bin/env python3
"""Extension run vs main run on their common anchors (comparison type (3) reproduction, not a return): the extension chain (OBJB_DATA=x0918r)
must reproduce the main chain bit for bit on every anchor <= 2026-08-31 00Z, because those anchors read exactly the same inputs
(mk_ext_inputs.py prefix proofs + the x0918r variant-diff C1). Checked per anchor: members, king book H, kc / fc states, the producer's king
target file, the combo target, the three readings' traded kind, and the P3 record fields that are pure functions of the inputs (combo status without its wall-clock fields utc / elapsed_s / age_s).
PASS <=> every common anchor equal. Writes receipts/EXT_REPRO_<ext>_vs_<main>.json.
usage: ext_repro_check.py MAIN_TAG EXT_TAG"""
import os, sys, json, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import b_lib as BL

R = os.environ.get("OBJB_ROOT", "/workspace/object_b_2026-09-19")
main_tag, ext_tag = sys.argv[1], sys.argv[2]
DM = json.load(open(f"{R}/work/{main_tag}/P3.json")); DE = json.load(open(f"{R}/work/{ext_tag}/P3.json"))
ZM = np.load(f"{R}/work/{main_tag}/P3.vec.npz"); ZE = np.load(f"{R}/work/{ext_tag}/P3.vec.npz")
VM = {k: ZM[k] for k in ZM.files}; VE = {k: ZE[k] for k in ZE.files}
im = {int(a): i for i, a in enumerate(VM["anchor"])}; ie = {int(a): i for i, a in enumerate(VE["anchor"])}
common = sorted(set(im) & set(ie)); assert common and common[0] == int(VM["anchor"][0])
RM = {int(r["anchor"]): r for r in DM["records"]}; RE = {int(r["anchor"]): r for r in DE["records"]}


def seg(V, name, i):
    if name == "pm": a, b = V["pm_off"][i], V["pm_off"][i + 1]; return (V["pm"][a:b],)
    a, b = V[name + "_off"][i], V[name + "_off"][i + 1]; return V[name + "_idx"][a:b], V[name + "_val"][a:b]


FIELDS = ("wrote", "n_live", "n_base", "lr_len", "n_members", "traded_lit", "traded_scaled", "traded_scaled_l333_only")
bad = []; n_eq = 0
for A in common:
    i, j = im[A], ie[A]; diffs = []
    for name in ("pm", "king", "kc", "fc", "king_file", "combo"):
        x, y = seg(VM, name, i), seg(VE, name, j)
        if not all(u.dtype == v.dtype and np.array_equal(u, v) for u, v in zip(x, y)): diffs.append(name)
    for f in FIELDS:
        if RM[A].get(f) != RE[A].get(f): diffs.append(f)
    km, ke = RM[A].get("king") or {}, RE[A].get("king") or {}
    if km.get("fold") != ke.get("fold"): diffs.append("king.fold")
    fm, fe = RM[A].get("f10") or {}, RE[A].get("f10") or {}
    if (fm.get("fold"), fm.get("n_scored"), fm.get("model_sha")) != (fe.get("fold"), fe.get("n_scored"), fe.get("model_sha")): diffs.append("f10")
    cm, ce = (RM[A].get("combo") or {}), (RE[A].get("combo") or {})
    wall = ("utc", "elapsed_s", "age_s")   # wall-clock fields of combo_live_status.json (run time, not inputs)
    sm_ = {k: v for k, v in (cm.get("status") or {}).items() if k not in wall}; se_ = {k: v for k, v in (ce.get("status") or {}).items() if k not in wall}
    if (sm_, cm.get("preflight"), cm.get("combo_meta"), cm.get("combo_rc"), cm.get("known_crash")) != (se_, ce.get("preflight"), ce.get("combo_meta"), ce.get("combo_rc"), ce.get("known_crash")):
        diffs.append("combo_record")
    if diffs: bad.append({"anchor": BL.iso(A), "differs": diffs})
    else: n_eq += 1
doc = {"comparison_type": "(3) reproduction — extension chain vs main chain on common anchors (not a return)", "main": main_tag, "ext": ext_tag,
       "main_p3_sha256": [BL.sha(f"{R}/work/{main_tag}/P3.json"), BL.sha(f"{R}/work/{main_tag}/P3.vec.npz")],
       "ext_p3_sha256": [BL.sha(f"{R}/work/{ext_tag}/P3.json"), BL.sha(f"{R}/work/{ext_tag}/P3.vec.npz")],
       "n_common": len(common), "common": [BL.iso(common[0]), BL.iso(common[-1])], "n_equal": n_eq, "n_differ": len(bad), "first_differences": bad[:50],
       "ext_only": [BL.iso(min(set(ie) - set(im))), BL.iso(max(set(ie) - set(im))), len(set(ie) - set(im))] if set(ie) - set(im) else None,
       "VERDICT": "PASS" if not bad else "FAIL", "self_sha256": BL.sha(os.path.abspath(__file__)), "utc": BL.iso(time.time())}
json.dump(doc, open(f"{R}/receipts/EXT_REPRO_{ext_tag}_vs_{main_tag}.json", "w"), indent=1)
print(json.dumps({k: doc[k] for k in ("n_common", "n_equal", "n_differ", "ext_only", "VERDICT")}), flush=True)
