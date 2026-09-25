#!/usr/bin/env python3
"""derive_short_cohort_forward_log.py -- derive the SHORT-cohort forward logger from the long one.

PREREG docs/PREREG_short_squeeze_onset_forward_2026-09-25.md (revision 1, lead-frozen).
Pattern: sha-pin the source + a NAMED substitution table + occurrence-count assertions + an archived
unified diff. Nothing is hand-edited, so the short device's provenance is a diff against the long one.

WHY the derived script lands OUTSIDE ~/Desktop (lead ruling, prereg §7):
  launchd hits a TCC wall on the iCloud Desktop repo -- it can stat but NOT enumerate, and a glob
  swallows the error and returns []. A job whose script or log lives in the repo therefore runs
  "successfully" and does nothing. Both the script and its log go to ~/parabolic_onset_forward_short/.

THE THREE SIGN MIRRORS (prereg §3) and nothing else about the measurement changes: cohort v>0 -> v<0,
onset direction down -> up (placebo mirrors with it), and value = -r-cost -> +r-cost, because exiting a
SHORT is worth the rise you avoid. P layer stays r3d >= +0.20: a shorted name that already ran up 20%
and keeps going up IS the squeeze.

usage: derive_short_cohort_forward_log.py <env-whitelist> [--out ~/parabolic_onset_forward_short]
"""
import difflib
import hashlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "parabolic_onset_forward_log.py")
# The long device's sha at derivation time. It has been constant across all 17 historical runs
# (run_log script_sha), so a change here means the parent device moved and this derivation is stale.
SRC_SHA = None  # recorded, not pinned, on the first derivation; asserted on every later one
PIN_FILE = os.path.join(HERE, "derive_short_cohort_SRC_PIN.json")

GATE_START_UTC = "2026-09-25T00:00:00Z"   # lead: only anchors >= this count toward the re-judge gate

SUBS = [
    # 1. output goes outside the repo (TCC wall), and to its own directory with its own `done` ledger
    ('REPO = os.path.dirname(os.path.abspath(__file__)).split("/multi_asset/")[0]; OUTD = f"{REPO}/multi_asset/exports/live/parabolic_onset_forward"',
     'OUTD = os.environ.get("SHORT_OUTD", f"{HOME}/parabolic_onset_forward_short")',
     1, "own directory, outside ~/Desktop; own events/run_log/done ledger"),

    # 2. MIRROR 1 -- cohort: book SHORT names
    ('coh = [(s, v, v / l1) for s, v in w.items() if v > 0 and l1 > 0 and (v / l1) >= 0.5 * capw and s in SI]',
     'coh = [(s, v, v / l1) for s, v in w.items() if v < 0 and l1 > 0 and (-v / l1) >= 0.5 * capw and s in SI]',
     1, "MIRROR 1: cohort = book SHORT names (w_norm stays signed, the threshold uses |w|)"),

    # 3. MIRROR 2 -- the onset of interest is UP; the placebo mirrors to DOWN
    ('for sign, typ in ((-1, "onset"), (+1, "mirror")):',
     'for sign, typ in ((+1, "onset"), (-1, "mirror")):',
     1, "MIRROR 2: onset = intra-anchor UP move (the squeeze); placebo = DOWN"),

    # 4+5. MIRROR 3 -- value of exiting a SHORT is the rise avoided, minus cost
    ('"value_bps": (float(-f1["next"] * 1e4 - COST) if f1["next"] is not None else None)',
     '"value_bps": (float(+f1["next"] * 1e4 - COST) if f1["next"] is not None else None)',
     1, "MIRROR 3a: value of exiting a short = +r - cost (event record)"),
    ('up["value_bps"] = float(-up["fwd_delay5m"]["next"] * 1e4 - COST)',
     'up["value_bps"] = float(+up["fwd_delay5m"]["next"] * 1e4 - COST)',
     1, "MIRROR 3b: same sign flip on the backfill/update pass"),

    # 6. label every record so the two cohorts can never be confused downstream
    ('"cohort_def": "book_long_only"',
     '"cohort_def": "book_short_only"',
     2, "cohort label on both the anchor record and each event record"),

    # 7. launchd/TCC guard: must be able to ENUMERATE, not merely stat
    ('cfg = json.load(open(BUNDLE_CFG));',
     'for _d in (STATE, f"{STATE}/target_live_king"):\n'
     '    # ENUMERATE, not stat: the TCC wall on ~/Desktop allows stat and blocks listing, so a stat-based\n'
     '    # self-check passes while the job still runs silently empty (the notary chain did this for 16 days).\n'
     '    _n = len(os.listdir(_d))\n'
     '    assert _n > 0, f"cannot enumerate {_d} (got {_n} entries) -- refusing to run silently empty"\n'
     'cfg = json.load(open(BUNDLE_CFG));',
     1, "startup self-check: enumerate the input dirs or exit non-zero"),

    # 8. the gate window must be a quantity the device OUTPUTS, not a rule someone remembers
    ('''summ = {}
for th in THETAS:
    k_ = f"theta{int(th*100)}"; summ[k_] = {}
    for lab, cond in (("P", lambda r: r["type"] == "onset" and r.get("layer") == "P"), ("Q", lambda r: r["type"] == "onset" and r.get("layer") == "Q"), ("mirror_P", lambda r: r["type"] == "mirror" and r.get("layer") == "P")):
        rs = [r for r in ids2.values() if r["anchor"] >= SINCE and abs(r["theta"] - th) < 1e-9 and cond(r)]
        v = [r["fwd_delay5m"]["next"] for r in rs if (r.get("fwd_delay5m") or {}).get("next") is not None]
        summ[k_][lab] = {"n_events": len(rs), "n_filled_next": len(v), "mean_r_tau5m_to_next_bps": (round(float(np.mean(v)) * 1e4, 1) if v else None)}''',
     '''GATE_START = calendar.timegm(time.strptime("__GATE_START_UTC__", "%Y-%m-%dT%H:%M:%SZ"))
summ = {}
# Two segments, reported SEPARATELY and never added together (prereg rev 1 §5): only anchors
# >= GATE_START are forward evidence; 09-01..09-24 overlaps the period that generated the hypothesis
# and is descriptive only. Summing them is the single most likely way to violate this prereg, so the
# device emits them as separate objects rather than trusting anyone to keep them apart.
for seg, lo, hi in (("gate_forward_ge_" + "__GATE_START_UTC__".replace("-", "").replace(":", "").replace("T", "_")[:11], GATE_START, 1 << 62),
                    ("in_sample_descriptive_NOT_forward", SINCE, GATE_START)):
    summ[seg] = {}
    for th in THETAS:
        k_ = f"theta{int(th*100)}"; summ[seg][k_] = {}
        for lab, cond in (("P", lambda r: r["type"] == "onset" and r.get("layer") == "P"), ("Q", lambda r: r["type"] == "onset" and r.get("layer") == "Q"), ("mirror_P", lambda r: r["type"] == "mirror" and r.get("layer") == "P")):
            rs = [r for r in ids2.values() if lo <= r["anchor"] < hi and abs(r["theta"] - th) < 1e-9 and cond(r)]
            v = [r["fwd_delay5m"]["next"] for r in rs if (r.get("fwd_delay5m") or {}).get("next") is not None]
            summ[seg][k_][lab] = {"n_events": len(rs), "n_filled_next": len(v), "mean_r_tau5m_to_next_bps": (round(float(np.mean(v)) * 1e4, 1) if v else None)}
_gseg = [k for k in summ if k.startswith("gate_forward_")][0]
_gate_days = sorted({(a // 86400) for a in done2 if a >= GATE_START})
GATE_STATUS = {"gate_start_utc": "__GATE_START_UTC__", "segment_used": _gseg,
               "theta8_P_filled_next": summ[_gseg]["theta8"]["P"]["n_filled_next"],
               "n_calendar_days": len(_gate_days), "need_theta8_P_filled": 200, "need_calendar_days": 14,
               "TRIGGERED": bool(summ[_gseg]["theta8"]["P"]["n_filled_next"] >= 200 and len(_gate_days) >= 14),
               "NOTE": "the in-sample segment is NEVER added to these counts"}''',
     1, "run_log reports gate vs in-sample segments separately + an explicit GATE_STATUS object"),

    # 9. carry both objects into the run_log line
    ('"events_new": stats["events"], "updates": updates, "summary_2026_09plus": summ, "dry_run": args.dry_run}',
     '"events_new": stats["events"], "updates": updates, "summary_by_segment": summ, "gate_status": GATE_STATUS, '
     '"cohort_def": "book_short_only", "prereg": "docs/PREREG_short_squeeze_onset_forward_2026-09-25.md rev1", "dry_run": args.dry_run}',
     1, "run_log line carries the segmented summary, the gate status and the cohort label"),
]


NEW_DOC = '''"""parabolic_onset_forward_log_short.py -- DERIVED, do not hand-edit.

Derived from parabolic_onset_forward_log.py by derive_short_cohort_forward_log.py (see the .diff and
DERIVE_RECEIPT.json next to this file). Prereg: docs/PREREG_short_squeeze_onset_forward_2026-09-25.md
revision 1 (lead-frozen criteria, inherited verbatim from 26aeb23 with a sign mirror).

WHAT IT MEASURES: for names the book is SHORT, does an intra-anchor UP onset (cumulative >= +theta)
continue up to the next anchor -- i.e. does the loss on a held short keep running, and is exiting that
short worth more than the cost? P layer is unchanged (r3d >= +0.20): a shorted name that already ran up
20% and keeps going up IS the squeeze.

THE THREE MIRRORS vs the parent (everything else is byte-identical):
  cohort  v > 0            ->  v < 0            (threshold on |w|)
  onset   first <= -theta  ->  first >= +theta  (the placebo mirrors to the DOWN direction)
  value   -r - cost        ->  +r - cost        (exiting a short is worth the rise avoided)

WINDOW (prereg rev 1 §4, lead): anchors >= 2026-09-25T00:00Z are the forward sample and are the ONLY
ones that count toward the re-judge gate. 2026-09-01..09-24 is backfilled for a shared axis with the
long cohort but is DESCRIPTIVE ONLY -- it overlaps 09-16..24, the period that generated the hypothesis.
The run_log emits the two segments as separate objects plus an explicit gate_status, because adding
them together is the single most likely way to violate this prereg.

ZERO-TOUCH: reads ~/wide_shadow/state/rolling.npz, shadow_bundle/config.json and
state/target_live_king/<A>.json. Calls NO API. Writes ONLY under its own output directory
(~/parabolic_onset_forward_short by default, $SHORT_OUTD to override) -- never under ~/wide_shadow,
~/dl_quant_live, or the research repo. It lives outside ~/Desktop on purpose: launchd hits a TCC wall
on the iCloud repo where it can stat but NOT enumerate, so a job there runs "successfully" and does
nothing. Startup asserts it can ENUMERATE its inputs.

usage: parabolic_onset_forward_log_short.py [--since 2026-09-01T00:00:00Z] [--dry-run]
"""'''

def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


def main():
    wl = set(sys.argv[1].split(","))
    extra = sorted(set(os.environ) - wl)
    assert not extra, f"env outside whitelist: {extra}"
    out_dir = os.path.expanduser(sys.argv[3] if len(sys.argv) > 3 and sys.argv[2] == "--out"
                                 else "~/parabolic_onset_forward_short")
    src = open(SRC, "rb").read()
    src_sha = sha_bytes(src)
    if os.path.exists(PIN_FILE):
        pinned = json.load(open(PIN_FILE))["src_sha256"]
        assert src_sha == pinned, (f"the parent device changed ({src_sha[:16]} != pinned {pinned[:16]}): "
                                   "re-read it and re-derive deliberately, do not auto-accept")
    text = src.decode()

    # Replace the parent docstring wholesale FIRST: a derived device that documents itself as the
    # long cohort is a lie that outlives the diff. (My own "no book_long_only survives" assertion
    # caught this -- the label also lived in the prose, not just in the two record literals.)
    i = text.index('"""'); j = text.index('"""', i + 3) + 3
    assert i < 200 and j - i > 1500, f"docstring boundaries look wrong: {i}, {j}"
    text = text[:i] + NEW_DOC + text[j:]

    applied = []
    for old, new, n_exp, why in SUBS:
        new = new.replace("__GATE_START_UTC__", GATE_START_UTC)
        n = text.count(old)
        assert n == n_exp, f"expected {n_exp} occurrence(s), found {n}: {old[:70]!r}"
        text = text.replace(old, new)
        applied.append({"occurrences": n, "why": why, "old_first80": old[:80], "new_first80": new[:80]})
    assert text != src.decode()
    # the long cohort's label must be entirely gone from the derived file
    assert "book_long_only" not in text, "a long-cohort label survived the derivation"

    os.makedirs(out_dir, exist_ok=True)
    dst = os.path.join(out_dir, "parabolic_onset_forward_log_short.py")
    open(dst, "w").write(text)
    diff = "".join(difflib.unified_diff(src.decode().splitlines(True), text.splitlines(True),
                                        fromfile="parabolic_onset_forward_log.py",
                                        tofile="parabolic_onset_forward_log_short.py"))
    open(dst + ".diff", "w").write(diff)
    rec = {"device": "derive_short_cohort_forward_log.py", "self_sha256": sha_bytes(open(os.path.abspath(__file__), "rb").read()),
           "utc": time.strftime("%FT%TZ", time.gmtime()), "src": SRC, "src_sha256": src_sha,
           "derived": dst, "derived_sha256": sha_bytes(text.encode()), "diff": dst + ".diff",
           "diff_lines": diff.count("\n"), "gate_start_utc": GATE_START_UTC,
           "prereg": "docs/PREREG_short_squeeze_onset_forward_2026-09-25.md rev1", "substitutions": applied}
    open(os.path.join(out_dir, "DERIVE_RECEIPT.json"), "w").write(json.dumps(rec, indent=2))
    if not os.path.exists(PIN_FILE):
        open(PIN_FILE, "w").write(json.dumps({"src_sha256": src_sha, "pinned_utc": rec["utc"]}, indent=2))
    print(json.dumps({k: rec[k] for k in ("src_sha256", "derived", "derived_sha256", "diff_lines", "gate_start_utc")}, indent=1))
    for a in applied:
        print(f"  x{a['occurrences']}  {a['why']}")
    print("DERIVE_SHORT_COHORT_OK")


if __name__ == "__main__":
    main()
