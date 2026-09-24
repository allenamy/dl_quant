"""fa_b8trcpt.py — build the variant TARGET_RECEIPT.json for a B8 combo, and report the combo-level behavioural
difference BEFORE anything downstream runs.

PREREG docs/PREREG_fresh_rootcause_B8_2026-09-24.md (38f4c0fbd).

fa_b8combo.py writes literal.npz / scaled_diagnostic.npz but not TARGET_RECEIPT.json; the adapter needs one whose
policies[pol].sha matches the npz it accompanies (this is the `new_receipt_policy_sha` refusal that bit B4). Same
rewrite as fa_bvariant.py L58-72: take the arm's own TARGET_RECEIPT.json, point path/sha/reasons at the variant's
files, keep the originals inside for provenance.

Behavioural assertion (not textual): the variant combo must differ from the arm's own combo. A seat change that
left the published book bitwise identical would mean the switch did not reach the book, and the engine run would be
a re-run of the baseline wearing a variant's name. The per-anchor difference counts are computed and recorded here,
which is also the "report the behavioural difference before any readout" step the lead asked for.

usage: ... fa_b8trcpt.py WL <src_combo_dir> <variant_dir>
"""
import os, sys, json, time, hashlib, collections
import numpy as np

WL_ = set(sys.argv[1].split(",")); _x = sorted(set(os.environ) - WL_); assert not _x, f"env outside whitelist: {_x}"
SRC, OUTD = sys.argv[2], sys.argv[3]
POLS = ("scaled_diagnostic", "literal")


def shab(b):
    return hashlib.sha256(b).hexdigest()


def sha_file(p):
    with open(p, "rb") as f:
        return shab(f.read())          # one captured buffer; nothing re-opens the file to hash it again


rec = {"device": "fa_b8trcpt.py", "self_sha256": sha_file(os.path.abspath(__file__)),
       "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
       "prereg": {"path": "docs/PREREG_fresh_rootcause_B8_2026-09-24.md", "commit": "38f4c0fbd"},
       "source_combo": SRC, "variant_dir": OUTD, "policies": {}}

TR = json.load(open(f"{SRC}/TARGET_RECEIPT.json"))
TR["DIAGNOSTIC_VARIANT"] = {"variant": "B8", "source_combo": SRC,
                            "note": "seat recomputed for a shorter msharpe_look; a configuration this pipeline "
                                    "cannot produce; research arm only",
                            "original_policies": {k: {"path": v.get("path"), "sha": v.get("sha"), "reasons": v.get("reasons")}
                                                  for k, v in TR.get("policies", {}).items()}}
allok = True
for pol in POLS:
    sp, vp = f"{SRC}/{pol}.npz", f"{OUTD}/{pol}.npz"
    S = np.load(sp, allow_pickle=True); V = np.load(vp, allow_pickle=True)
    assert np.array_equal(S["E_ts"], V["E_ts"]), f"{pol}: variant axis differs from source"
    assert np.array_equal(S["symbols"], V["symbols"]), f"{pol}: variant symbol axis differs from source"
    stm = np.asarray(S["trade_mask"]).astype(bool); vtm = np.asarray(V["trade_mask"]).astype(bool)
    sw = np.asarray(S["weights"]); vw = np.asarray(V["weights"])
    wdiff = ~np.isclose(np.nan_to_num(sw, nan=-9e9), np.nan_to_num(vw, nan=-9e9), rtol=0, atol=0)
    d = {"anchors": int(len(S["E_ts"])),
         "anchors_with_any_weight_cell_differing": int(wdiff.any(1).sum()),
         "weight_cells_differing": int(wdiff.sum()),
         "anchors_with_trade_mask_differing": int((stm != vtm).sum()),
         "publish_source": int(stm.sum()), "publish_variant": int(vtm.sum()),
         "reasons_source": dict(collections.Counter(str(x) for x in S["reason"])),
         "reasons_variant": dict(collections.Counter(str(x) for x in V["reason"]))}
    d["behavioural_difference_present"] = bool(d["anchors_with_any_weight_cell_differing"] > 0)
    allok = allok and d["behavioural_difference_present"]
    b = open(vp, "rb").read(); h = shab(b)
    TR["policies"][pol]["path"] = vp
    TR["policies"][pol]["sha"] = h
    TR["policies"][pol]["reasons"] = d["reasons_variant"]
    d["variant_sha256"] = h; d["source_sha256"] = sha_file(sp)
    rec["policies"][pol] = d
    assert d["behavioural_difference_present"], \
        f"{pol}: variant combo is bitwise identical to the source on every anchor -- the seat change did not reach the book"

json.dump(TR, open(f"{OUTD}/TARGET_RECEIPT.json", "w"), indent=2)
rec["target_receipt_sha256"] = sha_file(f"{OUTD}/TARGET_RECEIPT.json")
json.dump(rec, open(f"{OUTD}/FA_B8TRCPT_RECEIPT.json", "w"), indent=2, default=float)
assert os.path.exists(f"{OUTD}/FA_B8TRCPT_RECEIPT.json"), "receipt not written"
print("FA_B8TRCPT " + ("BEHAVIOURAL_DIFF_PRESENT" if allok else "NO_DIFF") + " " +
      json.dumps({p: {k: rec["policies"][p][k] for k in ("anchors_with_any_weight_cell_differing",
                                                         "anchors_with_trade_mask_differing",
                                                         "publish_source", "publish_variant")} for p in POLS}), flush=True)
