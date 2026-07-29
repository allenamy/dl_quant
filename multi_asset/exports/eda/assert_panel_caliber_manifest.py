"""0C — the funding CALIBER of every panel this frozen model generation holds, bound to the GENERATION.

> created 2026-07-27 | Session: 0C | 状态: permanent guard | 作废条件: 从不 (随模型世代重新祝福, 不作废)

WHY THIS EXISTS — THE GUARD MUST FOLLOW THE PRINCIPLE, NOT THE INSTANCE
-----------------------------------------------------------------------
`dl_quant_live/checkpoints/MANIFEST.json` says it best, in its own `why`:

    "norm stats are hashed alongside the weights because feeding a frozen model different
     normalisation is the same failure as loading different weights."

That sentence is a statement about a CLASS, and only one member of the class was guarded. The
funding caliber of the input panel is the same kind of object as the normalisation statistics:

    changing it changes what the frozen weights are fed, with no retraining.

⇒ Giving a frozen model a re-calibered panel IS giving it different weights. `norm_stats.npz` got a
  hash; `wide_dl_full.npz`'s funding dimension got nothing. This file closes that, at the level of
  the principle rather than the instance.

WHAT IT ASSERTS (three things, and all three must hold)
-------------------------------------------------------
 1. GENERATION IDENTITY. The frozen king/s2 fold-4 checkpoints still hash to the generation this
    manifest was blessed against. If they do not, the blessing is STALE and the run FAILS — it does
    not quietly keep asserting yesterday's expectation about today's model.
 2. PER-PANEL CALIBER. Every panel the manifest lists, that is present on this machine, still
    measures the caliber it was blessed with (`as_trained` / `corrected`, bands and forbidden middle
    from `assert_funding_dim`). A panel silently rebuilt into the other caliber FAILS here.
 3. NON-VACUITY. If nothing could be verified — no panels present, or no checkpoints to identify the
    generation — the verdict is UNKNOWN (exit 2), never PASS. A guard whose denominator is empty and
    whose verdict is green is not a guard; the drift gate next door has been printing
    "no drift across 0 vendored modules" for two days for exactly this reason.

★ THIS IS WHY THE EXPECTATION FLIPS WITH THE MODEL VERSION, MECHANICALLY
------------------------------------------------------------------------
`assert_funding_dim`'s header carries a FORWARD NOTE: if the heads are ever retrained on the
normalised caliber, the expectation must flip with the model version. A note is a thing a human has
to remember. Here the expectation is KEYED TO THE GENERATION HASH, so a retrain cannot silently
inherit the old expectation: the generation changes, check (1) fails, and the only way forward is to
re-bless deliberately — at which point the caliber is re-stated on purpose. The flip and the model
version become one act, which is what they always were.

★ WHAT IT DOES **NOT** GUARD, ON PURPOSE
-----------------------------------------
It does not say which caliber is CORRECT. `corrected` is the better dimension and `as_trained` is
what the frozen heads were fitted on; this file asserts CONSISTENCY WITH TRAINING, and the red test
below exists to prove exactly that — a genuinely corrected `wide_dl_full` panel must FAIL here while
this generation holds. A guard that rewarded "more correct" would have waved through the very drift
it exists to catch.

Usage
-----
    python assert_panel_caliber_manifest.py                 # assert (exit 0 / 1 / 2)
    python assert_panel_caliber_manifest.py --json out.json
    python assert_panel_caliber_manifest.py --bless         # re-record after a deliberate change
    python assert_panel_caliber_manifest.py --substitute exports/wide_dl_full.npz=<other.npz>
                                                            # RED TESTS ONLY (see tests_panel_caliber_manifest.py)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import assert_funding_dim as AFD          # THE measurement lives there; never re-derived here
import panel_caliber_stamp as PCS         # the artifact's own declaration; cross-checked below

MA = AFD.MA                                # .../multi_asset
MANIFEST_PATH = os.path.join(AFD.EDA, "panel_caliber_manifest.json")

# The frozen generation, as two checkpoint files. Both machines are searched because the same two
# files live under different names in the two repos and hash IDENTICALLY (verified 2026-07-27:
# server exports/train/wideA_*/fold_4_model.pt == dl_quant_live/checkpoints/{king,s2}_fold4.pt).
GENERATION_MEMBERS = {
    "king": [MA + "/exports/train/wideA_lamorth0_xattn_5yr/fold_4_model.pt",
             os.path.expanduser("~/dl_quant_live/checkpoints/king_fold4.pt")],
    "s2":   [MA + "/exports/train/wideA_s2_y24_5yr/fold_4_model.pt",
             os.path.expanduser("~/dl_quant_live/checkpoints/s2_fold4.pt")],
}


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1 << 22):
            h.update(chunk)
    return h.hexdigest()


def resolve_generation():
    """Identify the frozen generation from the checkpoints present on THIS machine.

    Returns {"id": str|None, "members": {...}, "resolved": [...], "unresolved": [...]}.
    id is None when neither member could be read — which the caller must treat as UNKNOWN.
    """
    members, unresolved = {}, []
    for name, candidates in GENERATION_MEMBERS.items():
        for p in candidates:
            if os.path.exists(p):
                members[name] = {"path": p, "sha256": _sha256(p)}
                break
        else:
            unresolved.append(name)
    if unresolved:
        # A generation identified from HALF its members is not the generation. Partial identity is
        # the failure mode where a swap of the unread half is invisible.
        return {"id": None, "members": members, "unresolved": unresolved}
    blob = "|".join(f"{n}:{members[n]['sha256']}" for n in sorted(members))
    return {"id": hashlib.sha256(blob.encode()).hexdigest()[:16], "members": members,
            "unresolved": []}


def load_manifest(path=MANIFEST_PATH):
    if not os.path.exists(path):
        return None
    return json.load(open(path))


def bless(path=MANIFEST_PATH, note=None):
    """Record the CURRENT state as the expectation. A deliberate act, never automatic."""
    gen = resolve_generation()
    if gen["id"] is None:
        print(f"REFUSING TO BLESS: cannot identify the frozen generation "
              f"(unreadable members: {gen['unresolved']}). Blessing an unidentified generation "
              f"would produce a manifest that can never be checked against anything.", flush=True)
        return 2
    panels = {}
    for slot in DEFAULT_SLOTS:
        p = os.path.join(MA, slot)
        if not os.path.exists(p):
            print(f"  [bless] {slot}: ABSENT on this machine — not recorded", flush=True)
            continue
        gaps, missing = AFD.measure_gaps(p)
        if missing:
            print(f"  [bless] {slot}: channels missing {missing} — not recorded", flush=True)
            continue
        cal = {c: AFD.classify_gap(gaps[c]["mean_gap"]) for c in AFD.CHANNELS if c in gaps}
        distinct = set(cal.values())
        if len(distinct) != 1 or "MIDDLE" in distinct:
            print(f"  [bless] {slot}: REFUSED — channels disagree or land in the forbidden middle "
                  f"({cal}). Blessing this would freeze an undeclared state.", flush=True)
            return 1
        daily = slot in REBUILT_DAILY
        panels[slot] = {"caliber": distinct.pop(),
                        "measured": {c: gaps[c] for c in AFD.CHANNELS if c in gaps},
                        "control_Y4": gaps.get("Y4"),
                        "role": SLOT_ROLE.get(slot, ""),
                        "rebuilt_daily": daily,
                        "file_sha256_16": (None if daily else _sha256(p)[:16]),
                        "file_sha256_note": ("rebuilt daily by design — no hash recorded; the "
                                             "measurement is the check" if daily else
                                             "bit-identity to this hash is a stronger statement "
                                             "than a re-measurement"),
                        "file_size": os.path.getsize(p),
                        "measured_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        print(f"  [bless] {slot}: {panels[slot]['caliber']}  "
              f"{ {c: v['mean_gap'] for c, v in panels[slot]['measured'].items()} }", flush=True)
    if not panels:
        print("REFUSING TO BLESS: no panel could be measured on this machine. An empty manifest "
              "would assert nothing while looking like a guard.", flush=True)
        return 2
    payload = {
        "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "author": "0C",
        "why": ("the funding caliber of a model-input panel is the same class of object as the "
                "frozen normalisation statistics: changing it feeds the frozen weights something "
                "they were not fitted on. norm_stats got a hash; this is the panel's."),
        "generation": {"id": gen["id"],
                       "members": {n: {"sha256": v["sha256"], "seen_at": v["path"]}
                                   for n, v in gen["members"].items()},
                       "blessed_because": (note or
                           "the frozen king/s2 heads were fitted on the AS-TRAINED (un-normalised) "
                           "funding caliber and have not been retrained since the 2026-07-25 fix"),
                       "flip_rule": ("this manifest is keyed to the generation hash ON PURPOSE. A "
                                     "retrain changes the hash, which fails the assertion, which "
                                     "forces a deliberate re-bless — the caliber expectation and "
                                     "the model version flip together or not at all.")},
        "panels": panels,
    }
    json.dump(payload, open(path, "w"), indent=1)
    print(f"\nBLESSED generation {gen['id']} over {len(panels)} panel(s) -> {path}", flush=True)
    return 0


SLOT_ROLE = {
    "exports/wide_dl_full.npz":
        "the model-input panel the frozen heads were TRAINED on (built 2026-07-11)",
    "exports/live/wide_dl_live.npz":
        "the daily splice fed to the same frozen heads; must match the training caliber",
}
# ★ Slots that are REBUILT EVERY DAY BY DESIGN get no hash shortcut. Storing a hash for them would
# put a number in the manifest that is guaranteed to be stale by tomorrow morning — and a stale
# recorded hash is not a harmless leftover, it is a claim a later reader can mistake for evidence.
# For these the measurement IS the check, every day. (7 s on a 1 GB panel; the shortcut was never
# about them.)
REBUILT_DAILY = {"exports/live/wide_dl_live.npz"}
DEFAULT_SLOTS = list(SLOT_ROLE)


def assert_manifest(path=MANIFEST_PATH, substitutes=None, verbose=True, force_measure=False):
    """Returns (exit_code, report). 0 PASS / 1 FAIL / 2 UNKNOWN."""
    substitutes = substitutes or {}
    rep = {"checked_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "manifest": path, "panels": {}, "findings": []}
    man = load_manifest(path)
    if man is None:
        rep["findings"].append("manifest absent — nothing has ever been blessed; UNKNOWN, not clean")
        rep["verdict"] = "UNKNOWN"
        if verbose:
            print("UNKNOWN: no manifest at " + path, flush=True)
        return 2, rep

    # ── 1. generation identity ───────────────────────────────────────────────────────────────
    gen = resolve_generation()
    want_gen = man["generation"]["id"]
    rep["generation"] = {"expected": want_gen, "observed": gen["id"],
                         "unresolved": gen["unresolved"]}
    if gen["id"] is None:
        rep["findings"].append(
            f"GENERATION UNIDENTIFIABLE on this machine (unreadable: {gen['unresolved']}). The "
            f"caliber expectation is keyed to the generation, so it cannot be applied. UNKNOWN.")
        rep["verdict"] = "UNKNOWN"
        if verbose:
            print("\n".join(rep["findings"]), flush=True)
        return 2, rep
    if gen["id"] != want_gen:
        rep["findings"].append(
            f"★ GENERATION CHANGED: manifest blessed against {want_gen}, this machine holds "
            f"{gen['id']}. The frozen heads are not the ones this caliber expectation was written "
            f"for. Do NOT edit the expectation to match — re-bless deliberately, and while doing so "
            f"decide whether the retrain was on the normalised caliber (if so the expectation "
            f"becomes `corrected`). This is the flip that must not happen by accident.")
        rep["verdict"] = "FAIL"
        if verbose:
            print("\n".join(rep["findings"]), flush=True)
        return 1, rep

    # ── 2. per-panel caliber ─────────────────────────────────────────────────────────────────
    n_checked = 0
    for slot, want in man["panels"].items():
        p = substitutes.get(slot, os.path.join(MA, slot))
        entry = {"path": p, "expected_caliber": want["caliber"]}
        if substitutes.get(slot):
            entry["SUBSTITUTED"] = True
        if not os.path.exists(p):
            entry["state"] = "ABSENT"
            rep["panels"][slot] = entry
            if verbose:
                print(f"  {slot:34s} ABSENT on this machine — not verified", flush=True)
            continue
        # ★ THE ARTIFACT'S OWN STAMP VS THIS MANIFEST'S BLESSING (0C 2026-07-29). Two declarations
        # about the same artifact now exist: the stamp its builder wrote into it, and the caliber
        # this generation was blessed with. They must agree. If they do not, someone changed one
        # declaration and not the other — and a mislabelled artifact is how a panel ends up in a
        # role it was never built for while every individual check still reads green.
        # ⇒ Checked BEFORE the hash shortcut so a disagreement is not skipped by bit-identity.
        try:
            _st = PCS.read(p)
        except PCS.StampError as e:
            _st = None
            entry["stamp"] = f"BROKEN: {e}"
            rep["findings"].append(f"★ {slot} carries a BROKEN caliber stamp: {e}. A declaration "
                                   f"that cannot be read is not an absent one — find the writer.")
        if _st is not None:
            entry["stamp"] = {"caliber": _st["funding_caliber"], "by": _st.get("declared_by")}
            if _st["funding_caliber"] != want["caliber"]:
                rep["findings"].append(
                    f"★ {slot} STAMP/BLESSING DISAGREE: the artifact declares "
                    f"`{_st['funding_caliber']}` (written by {_st.get('declared_by')}), this "
                    f"generation was blessed with `{want['caliber']}`. One of the two was changed "
                    f"without the other. Do not reconcile by editing whichever is easier to edit — "
                    f"decide which caliber this generation is supposed to hold, and make the "
                    f"builder and the blessing say it together.")
        # ★ HASH FIRST, MEASURE ONLY IF IT MOVED. Bit-identity to the blessed file is a STRONGER
        # statement than a re-measurement (no sampling, no threshold) and costs seconds instead of
        # minutes on a 1 GB panel. This is also literally what `norm_stats` gets — the measurement
        # below is the extra step, for the case a legitimate rebuild changed the bytes.
        sha16 = _sha256(p)[:16]
        entry["file_sha256_16"] = sha16
        # A daily-rebuilt slot has no blessed hash (None), so this comparison can never match and
        # the panel is always measured. Stated explicitly so nobody "optimises" it back.
        if not force_measure and want.get("file_sha256_16") and sha16 == want["file_sha256_16"]:
            entry["state"] = "BIT_IDENTICAL"
            n_checked += 1
            rep["panels"][slot] = entry
            if verbose:
                print(f"  {slot:34s} want {want['caliber']:10s} | bit-identical to the blessed "
                      f"file ({sha16}) -> PASS", flush=True)
            continue
        gaps, missing = AFD.measure_gaps(p)
        if missing:
            entry["state"] = "CHANNELS_MISSING"; entry["missing"] = missing
            rep["panels"][slot] = entry
            rep["findings"].append(f"{slot}: funding channels missing {missing} — cannot verify")
            continue
        got = {c: AFD.classify_gap(gaps[c]["mean_gap"]) for c in AFD.CHANNELS if c in gaps}
        entry.update(state="CHECKED", measured={c: gaps[c]["mean_gap"] for c in gaps},
                     observed_caliber=got)
        n_checked += 1
        bad = {c: v for c, v in got.items() if v != want["caliber"]}
        rep["panels"][slot] = entry
        if verbose:
            marks = " ".join(f"{c}={gaps[c]['mean_gap']:+.4f}({got[c]})" for c in got)
            print(f"  {slot:34s} want {want['caliber']:10s} | {marks} "
                  f"-> {'PASS' if not bad else 'FAIL'}", flush=True)
        if bad:
            entry["FAILED"] = bad
            rep["findings"].append(
                f"★ {slot} carries {sorted(set(bad.values()))} but this generation was blessed with "
                f"`{want['caliber']}`. {want.get('role','')} "
                + ("A reading in the FORBIDDEN MIDDLE means the funding dimension was changed "
                   "without declaring which caliber was intended. "
                   if "MIDDLE" in bad.values() else "")
                + ("This panel is what the frozen weights were fitted on; re-calibering it is the "
                   "same failure as swapping the weights. Find who rebuilt it — do not 'fix' the "
                   "expectation." if want["caliber"] == "as_trained" else
                   "Re-calibering it away from the blessed state changes what the frozen weights "
                   "are fed."))

    # ── 3. non-vacuity ───────────────────────────────────────────────────────────────────────
    if n_checked == 0:
        rep["findings"].append(
            "VACUOUS: the generation matched but NOT ONE panel was verifiable on this machine. "
            "A green from an empty denominator is the failure this check refuses to produce.")
        rep["verdict"] = "UNKNOWN"
        if verbose:
            print("\n".join(f"\n{f}" for f in rep["findings"]), flush=True)
        return 2, rep

    rep["n_panels_checked"] = n_checked
    rep["verdict"] = "PASS" if not rep["findings"] else "FAIL"
    if verbose:
        for f in rep["findings"]:
            print("\n" + f, flush=True)
        print(f"\nVERDICT: {rep['verdict']}  (generation {gen['id']}, "
              f"{n_checked} panel(s) verified)", flush=True)
    return (0 if rep["verdict"] == "PASS" else 1), rep


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default=MANIFEST_PATH)
    ap.add_argument("--bless", action="store_true",
                    help="record the CURRENT state as the expectation (deliberate act)")
    ap.add_argument("--note", default=None, help="why this generation is blessed with this caliber")
    ap.add_argument("--json", default=None, help="write the report here")
    ap.add_argument("--substitute", action="append", default=[], metavar="SLOT=PATH",
                    help="RED TESTS ONLY: read SLOT from PATH instead of its real location")
    ap.add_argument("--force-measure", action="store_true",
                    help="re-measure even when the file is bit-identical to the blessed one")
    a = ap.parse_args(argv)
    if a.bless:
        return bless(a.manifest, a.note)
    subs = dict(s.split("=", 1) for s in a.substitute)
    rc, rep = assert_manifest(a.manifest, subs, force_measure=a.force_measure)
    if a.json:
        json.dump(rep, open(a.json, "w"), indent=1, default=str)
    return rc


if __name__ == "__main__":
    sys.exit(main())
