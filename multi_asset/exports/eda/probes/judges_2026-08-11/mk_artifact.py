"""Augment the new-generation replay artifact with the fields the guard must be able to check.

SPEC 0f8be1fe §1: do NOT enumerate dimensions — bind to a GENERATION HASH, so that anything
changing makes the assertion red and forces a deliberate re-bless.
SPEC §2-3: the disjoint check must read a DECLARED window, not rely on a file's end date by accident.
team-lead addition: generation cannot see IN-SAMPLE-ness (PRODFOLD and the 5-fold are the SAME
generation and differ only in that) -> it needs its own declared field.
"""
import hashlib, json
import numpy as np
import pandas as pd

MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
MEMBERS = {
    "king": (MA + "/exports/train/wideA_lamorth0_xattn_5yr_corrfund_v1", "/tmp/king_pred_newgen.npz", "king_pred"),
    "s2":   (MA + "/exports/train/wideA_s2_y24_5yr_corrfund_emb10",      "/tmp/s2_pred_newgen.npz",   "s2_pred"),
}
rep = json.load(open("/tmp/engine_fullhist_replay_newgen.json"))

mem, hs = {}, []
for leg, (rundir, predf, key) in MEMBERS.items():
    z = np.load(predf)
    h = hashlib.sha256(np.ascontiguousarray(z[key])).hexdigest()
    mem[leg] = {"run": rundir.split("/")[-1], "pred_sha256": h,
                "kind": "5-fold walk-forward, out-of-sample per test year"}
    hs.append(h)
gen_id = hashlib.sha256("".join(sorted(hs)).encode()).hexdigest()[:16]

ts = np.load("/tmp/king_pred_newgen.npz")["ts"].astype(np.int64)
p = np.load("/tmp/king_pred_newgen.npz")["king_pred"]
rows = np.where(np.isfinite(p).any(1))[0]
w0, w1 = int(ts[rows.min()]), int(ts[rows.max()])

rep["generation"] = {
    "id": gen_id, "members": mem,
    "flip_rule": ("keyed to the generation hash ON PURPOSE. A retrain changes the hash, the "
                  "assertion fails, and a deliberate re-bless is forced — the baseline and the "
                  "model version flip together or not at all. SPEC 0f8be1fe §1: this does not "
                  "enumerate which dimensions must match, so it does not fall behind them."),
}
rep["predictions_out_of_sample"] = True
rep["out_of_sample_note"] = (
    "★ The generation hash CANNOT see this. A PRODUCTION-FOLD arm would be the SAME generation and "
    "differ only by being in-sample — measured 2026-08-04 at 1.18x higher, which would raise "
    "DECAY_FRAC*baseline and fire the guard on a healthy model. Hence a declared field, checked "
    "separately from the hash.")
rep["baseline_window"] = {
    "first_anchor_ts_ms": w0, "last_anchor_ts_ms": w1,
    "first_utc": pd.to_datetime(w0, unit="ms", utc=True).isoformat(),
    "last_utc": pd.to_datetime(w1, unit="ms", utc=True).isoformat(),
    "note": ("DECLARED, per SPEC §2-3. The disjoint check must read this rather than rely on the "
             "frozen panel's end date, which the old docstring itself called an accident.")}
rep["panel"] = {"assembly": "wide_dl_full_fundfix.npz", "ch31_arm": "SERVE",
                "why": ("SPEC §2-2: the baseline answers 'what will it get once live', not 'how well "
                        "was it trained' — so SERVE, not the causal panel it was trained on. Using "
                        "the training caliber sets the baseline too high and the guard never fires.")}
out = MA + "/exports/eda/engine_fullhist_replay_newgen_2026-08-04.json"
json.dump(rep, open(out, "w"), indent=1)
print("generation id  = %s" % gen_id)
for k, v in mem.items():
    print("  %-5s %s  %s" % (k, v["pred_sha256"][:16], v["run"]))
print("baseline window = %s .. %s" % (rep["baseline_window"]["first_utc"][:10],
                                      rep["baseline_window"]["last_utc"][:10]))
print("per_year mean_rank_ic -> rounded to 3dp (what monitor must declare):")
print("  " + ", ".join("%s: %.3f" % (y, round(v["mean_rank_ic"], 3))
                       for y, v in sorted(rep["per_year"].items())))
print("wrote %s" % out)
