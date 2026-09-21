#!/usr/bin/env python3
"""bt_gate_bindings.py — WHAT THE ACCEPTANCE GATE IS BOUND TO (round-7 review G-02 / G-03), split out of bt_gate_external.py so it
is importable and can be tested on its own.

THE DEFECT THIS EXISTS FOR (G-02, P1): bt_gate_external.py re-ran each stored path through the simulator and then threw away the
recomputation's JSON output — it compared only the npz arrays, and for the sidecar it checked nothing but the npz sha the sidecar
carries about itself. But the real downstream reader does not read the arrays alone: `bt_p2_reading.load_paths2` takes
`flatten_log` FROM THE PATH_*.json SIDECAR and `p2_of` decides every withheld anchor from it. So an archive could keep every npz
byte identical, add one day-stop to the sidecar, re-sign it, and the gate still printed PASS / exit 0 while the published P2
reading changed (the reviewer's six-anchor consumer fixture moved 22.825141712 % -> 1 %).

THE FIX, in the shape of the class and not of the field: the recomputation's own sidecar document is compared to the stored one
AS A WHOLE. It is not a list of fields the gate knows are important — that list would be exactly as complete as the last person's
memory. Everything the simulator emits must come back bitwise; the only escapes are the NAMED ones below, each with the reason it
cannot be recomputed AND the separate check that certifies it instead. A field a consumer starts reading tomorrow is already
covered, because it was already being compared.

`CONSUMED_SIDECAR_FIELDS` is therefore NOT the binding — it is a completeness ledger over the consumers, so that a field which a
reader depends on can never end up in the "cannot be recomputed" list without someone noticing. `sidecar_fields_read_by_sources()`
re-derives the set from the consumer sources on every run and the gate FAILS if a consumer reads a field this ledger does not name.
HONEST LIMIT OF THAT CENSUS: it reads source text, so a consumer that looks a field up through a computed key, or through a name
this scanner does not recognise as a sidecar handle, would not be seen. It is an omission detector, not a proof — which is why the
binding itself is the whole-document recomputation above and does not depend on it.
"""
import json
import os
import re

# the devices that read FIELDS out of a PATH_<tag>_seed_NN.json sidecar, and the variable each one holds the sidecar dict in.
# The census below re-derives the fields from these sources; declaring the handle keeps it exact (no inference, no false hits) and
# a rename shows up as "this consumer no longer has the handle it declares", which is drift the gate reports rather than absorbs.
CONSUMER_HANDLES = {
    "bt_p2_reading.py": ("J",), "bt_p_reading.py": ("J",), "bt_run_summary.py": ("J",),
    "bt_ext_control.py": ("J", "OJ", "NJ"), "bt_g_convention.py": ("J",), "bt_gate_external.py": ("SJ",),
}
# every OTHER device in this directory that touches a PATH_* sidecar, with the reason it reads no field out of one. A device that
# is in neither list is reported as UNCLASSIFIED (fail closed): a new consumer added tomorrow cannot be invisible just by not
# being on the first list.
NOT_SIDECAR_FIELD_READERS = {
    "bt_launch.py": "the WRITER (through bt_driver_lib.save_path); it reads no field back out of a sidecar",
    "bt_gate_tamper_test.py": "test device: it re-signs copies of a run directory and publishes no number",
    "bt_gate_binding_test.py": "test device: it builds fixture sidecars and publishes no number",
    "bt_launch_governor_test.py": "test device", "bt_main_a0_test.py": "test device",
    "bt_p2_reading_test.py": "test device: hand-built fixture paths", "bt_p_reading_test.py": "test device: hand-built fixture paths",
    "bt_window_end_test.py": "test device (E-0921-B): hand-built fixture paths; publishes no number",
    "bt_gate_bindings.py": "this module: it is handed the sidecar dict, it never opens one",
    "bt_tables.py": "reads PATH_*.npz arrays only (bt_tables.py:504 lists *.npz); it opens no sidecar json",
}

# every top-level sidecar field some consumer reads, and what it decides. Kept because a field that a reader depends on must never
# sit in NOT_RECOMPUTABLE_SIDECAR_FIELDS unnoticed; `certification_closure()` checks exactly that.
CONSUMED_SIDECAR_FIELDS = {
    "flatten_log": "bt_p2_reading.load_paths2 -> withheld_mask/p2_of: decides every withheld anchor of every window (G-02); "
                   "bt_run_summary counts the day-stop dates from it",
    "npz_sha256": "bt_p2_reading.load_paths2, bt_p_reading.load_paths, bt_run_summary and the gate's own E6: the array file's identity",
    "seed": "the gate (which member of the population this path is) and every reader that orders paths by seed",
    "tag": "the gate: which run of the config this path belongs to",
    "ua_counters": "bt_run_summary: the unavailable-panel counters reported per run",
    "events_fired_counts": "bt_run_summary: the event census per run",
    "runtime_s": "bt_run_summary: the wall-clock budget table",
    "policy": "bt_run_summary: which policy the run declares",
    "device_sha256": "the gate (E7): which code wrote this path",
    "config_sha256": "the gate (E7): which run config wrote this path",
    "calibration_sha256": "the gate (E7): which calibration wrote this path",
    "price_pin": "the gate (E7): which price table wrote this path",
    "price": "bt_ext_control: which price grid the two compared runs used",
    "ua_set": "bt_ext_control: which unavailable-name set the two compared runs used",
    "calibration_params_used": "bt_ext_control: the calibration the two compared runs resolved to",
    "sealed_initial_sha256": "bt_ext_control: the sealed initial state, compared across two runs of different tags",
}

# the ONLY fields exempt from "must come back bitwise from the recomputation", each with the reason AND the check that certifies it
# instead. An exemption with no certifier is a hole with a note next to it.
NOT_RECOMPUTABLE_SIDECAR_FIELDS = {
    "runtime_s": "wall-clock seconds of the original run: not a property of the numbers and not reproducible by construction. "
                 "It is a budget figure in bt_run_summary, never an input to a published number.",
}
# fields the PATH writer (bt_driver_lib.save_path) adds AFTER run_one returned, so the recomputation cannot carry them. Each names
# the gate check that certifies it instead — `certification_closure()` refuses a save-time field with no certifier.
SAVE_TIME_SIDECAR_FIELDS = {
    "npz_sha256": "E6.each_path_npz_matches_the_sha_in_its_own_json re-hashes the array file from disk",
    "device_sha256": "E7.save_time_device_shas_match_the_code_that_is_here / the approved table (checked in the gate)",
    "config_sha256": "E7.save_time_config_sha_equals_the_run_config_the_gate_was_given",
    "calibration_sha256": "E7.save_time_calibration_sha_equals_the_approved_calibration_pin",
    "price_pin": "E7.save_time_price_pin_equals_the_approved_price_table",
}

_LOAD_SITE = re.compile(r'json\.load\(\s*open\(')
_INLINE = re.compile(r'\.json"\s*\)+\s*(?:\[\s*|\.get\s*\(\s*)"(\w+)"')


def _accesses(src, handle):
    return set(re.findall(r'\b%s\s*(?:\[\s*|\.get\s*\(\s*)"(\w+)"' % re.escape(handle), src))


def sidecar_fields_read_by_sources(here, handles=None):
    """{field: [source files that read it]}, plus the drift findings — re-derived from the consumer sources every time the gate
    runs, so a field a reader starts using tomorrow shows up as a NAMED omission instead of a silent one."""
    handles = CONSUMER_HANDLES if handles is None else handles
    found, drift = {}, []
    for name, hs in sorted(handles.items()):
        p = os.path.join(here, name)
        if not os.path.exists(p):
            drift.append(f"{name}: source file absent"); continue
        src = open(p, encoding="utf-8").read()
        if not (_LOAD_SITE.search(src) and "PATH_" in src):
            drift.append(f"{name}: declared as a sidecar consumer but it no longer opens a PATH_* sidecar")
        hits = set(_INLINE.findall(src))
        for h in hs:
            a = _accesses(src, h)
            if not a:
                drift.append(f"{name}: declared handle {h!r} reads no field — the handle was renamed or the reader changed")
            hits |= a
        for f in hits:
            found.setdefault(f, []).append(name)
    return found, drift


def unclassified_sidecar_files(here, handles=None, others=None):
    """every bt_*.py in this directory that opens a json file AND mentions a PATH_* sidecar but is in neither list. A device that
    starts reading sidecars tomorrow is caught by NOT BEING CLASSIFIED — the same fail-closed shape as bt_agg's inverted A4
    trigger, rather than by being remembered."""
    handles = CONSUMER_HANDLES if handles is None else handles
    others = NOT_SIDECAR_FIELD_READERS if others is None else others
    out = []
    for fn in sorted(os.listdir(here)):
        if not (fn.startswith("bt_") and fn.endswith(".py")) or fn in handles or fn in others:
            continue
        src = open(os.path.join(here, fn), encoding="utf-8", errors="replace").read()
        if _LOAD_SITE.search(src) and "PATH_" in src:
            out.append(fn)
    return out


def census_gaps(here, handles=None, others=None):
    """fields a consumer reads that CONSUMED_SIDECAR_FIELDS does not name (the omission this ledger exists to make visible)"""
    found, drift = sidecar_fields_read_by_sources(here, handles)
    return {"undeclared_fields_a_consumer_reads": {k: v for k, v in sorted(found.items()) if k not in CONSUMED_SIDECAR_FIELDS},
            "declared_but_no_consumer_reads_them": sorted(set(CONSUMED_SIDECAR_FIELDS) - set(found)),
            "listed_consumers_that_load_no_sidecar": sorted(drift),
            "files_that_touch_a_sidecar_and_are_classified_as_neither": unclassified_sidecar_files(here, handles, others),
            "fields_found": sorted(found)}


def certification_closure():
    """every consumed field must be either recomputed-and-compared, or named in one of the two exemption lists WITH a certifier.
    This is the check that stops a load-bearing field from quietly moving into the "cannot be recomputed" column."""
    uncertified = [f for f in CONSUMED_SIDECAR_FIELDS
                   if f in NOT_RECOMPUTABLE_SIDECAR_FIELDS and f in SAVE_TIME_SIDECAR_FIELDS]
    empty = sorted([f for f, why in list(NOT_RECOMPUTABLE_SIDECAR_FIELDS.items()) + list(SAVE_TIME_SIDECAR_FIELDS.items())
                    if not str(why).strip()])
    recomputed = sorted(f for f in CONSUMED_SIDECAR_FIELDS
                        if f not in NOT_RECOMPUTABLE_SIDECAR_FIELDS and f not in SAVE_TIME_SIDECAR_FIELDS)
    return {"ok": not uncertified and not empty,
            "consumed_fields_bound_by_recomputation": recomputed,
            "consumed_fields_certified_otherwise": {f: (SAVE_TIME_SIDECAR_FIELDS.get(f) or NOT_RECOMPUTABLE_SIDECAR_FIELDS.get(f))
                                                    for f in sorted(CONSUMED_SIDECAR_FIELDS) if f not in recomputed},
            "exemptions_with_no_reason": empty, "exemptions_in_both_lists": sorted(uncertified)}


def _canon(o):
    """the recomputation's document put through the SAME serialisation the writer used (bt_driver_lib.save_path), so a difference
    is a difference in the numbers and not in how Python happened to hold them"""
    return json.loads(json.dumps(o, default=lambda x: sorted(x) if isinstance(x, set) else str(x)))


def compare_sidecar(stored, recomputed):
    """the WHOLE stored sidecar against the WHOLE recomputed one. Returns the finding, never a bare bool:
       absent_from_the_archive  — the simulator emits it and the archive does not carry it (an absent key is a finding, not a skip)
       absent_from_the_recomputation — the archive carries a field the simulator does not emit and nobody declared as save-time
       differing                — the field came back different
       exempt                   — the named, certified exemptions that were skipped, listed so the receipt says what was NOT compared
    """
    rec = _canon(recomputed)
    st_keys, rc_keys = set(stored), set(rec)
    exempt = sorted((st_keys | rc_keys) & (set(NOT_RECOMPUTABLE_SIDECAR_FIELDS) | set(SAVE_TIME_SIDECAR_FIELDS)))
    absent_archive = sorted(rc_keys - st_keys - set(exempt))
    absent_recomp = sorted(st_keys - rc_keys - set(exempt))
    differing = []
    for k in sorted((st_keys & rc_keys) - set(exempt)):
        if json.dumps(stored[k], sort_keys=True, default=str) != json.dumps(rec[k], sort_keys=True, default=str):
            differing.append(k)
    return {"absent_from_the_archive": absent_archive, "absent_from_the_recomputation": absent_recomp,
            "differing": differing, "exempt_and_certified_elsewhere": exempt,
            "compared": len((st_keys & rc_keys) - set(exempt)), "ok": not (absent_archive or absent_recomp or differing)}


def approved_seed_set(APP):
    """THE population, fixed by the independently approved run identity (round-7 G-03). It used to come from the CLI on one side
    (`NSEED`) and from the aggregate's self-reported `path_files` on the other, so `NSEED=1` with a corrupted seed 1 still in the
    aggregate passed with full=true, and an aggregate whose members were [seed0, seed0] passed too. `paths_R` lives in the approved
    economics block, which is hashed as one unit — the caller cannot shrink it without failing E2."""
    r = APP["economics"]["paths_R"]
    n = int(r)
    if n != r or n <= 0:
        raise ValueError(f"the approved economics declare paths_R={r!r}, which is not a positive whole number of paths")
    return frozenset(range(n))


def aggregate_member_seeds(AGGJ):
    """the seeds the aggregate says it averaged, AS A LIST so a repeat is visible. Comparing counts is what let [seed0, seed0]
    through: len() == 2 == len(approved)."""
    return [f["seed"] for f in AGGJ["path_files"]]


def set_report(name, got, want):
    """sets, never counts — with both directions named, because "how many" is the comparison that failed in G-03"""
    got_l = list(got)
    got_s, want_s = set(got_l), set(want)
    dup = sorted({x for x in got_l if got_l.count(x) > 1})
    return {"quantity": name, "missing": sorted(want_s - got_s), "unexpected": sorted(got_s - want_s), "repeated": dup,
            "n_listed": len(got_l), "n_distinct": len(got_s), "n_approved": len(want_s),
            "ok": (got_s == want_s and not dup)}
