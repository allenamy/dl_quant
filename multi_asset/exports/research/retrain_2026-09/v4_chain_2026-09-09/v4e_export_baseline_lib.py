"""v4e_export_baseline_lib.py — the PER-MONTH approved export baseline (TRN-15; RUNBOOK_monthly_retrain_2026-10.md §0★ 修订 6 item 2).

WHY THIS EXISTS. `gates.BUNDLE_export.approved_baseline.live_pins_sha256` / `.bundle_base_sha256` are ONE pair of shas, frozen
when the September contract was written. RUNBOOK §0★ step 0 requires `live_pins.json` to be re-copied from the IN-SERVICE bundle
and the baseline IC json to be re-established EVERY month — so from October on those two files can never equal the frozen pair and
check E2b fails BY CONSTRUCTION, for a reason that has nothing to do with October's data (AUDIT_TRAIN TRN-15; the September pins
in particular cannot be reused, universe Phase A M1 went live 2026-09-04).

THE RULING IS TO PARAMETERISE, NOT TO RELAX (contract `month_contract_rulings.TRN-15_export_baseline_per_month`, user word
2026-09-18「按最佳建议来」): the approved pins / baseline become a PER-MONTH approval object, and the gate still demands a
BYTE-IDENTICAL match against an EXPLICITLY approved sha. It must never accept "whatever is on disk", and it must never fall back
to another month's approval — applying September's approval to October is precisely the thing the ruling forbids.

WHAT THIS REFUSES (every one a NAMED reason the caller puts in its receipt; none of them is a silent pass):
  contract_block_absent   the contract carries no `approved_export_baselines` map — i.e. the OLD contract shape. Fail closed.
                          The global `approved_baseline` is NOT a fallback: a fallback would silently re-approve one month's
                          files for every later month, which is the defect (「字段缺了就跳过」是一整类门缺陷).
  month_not_declared      the caller did not say which month this is. A gate that guesses its inputs binds nothing (E-0826-D).
  month_not_approved      the map has no entry for this month, or the entry is null. 2026-10 is deliberately null until the
                          October pins and baseline json exist and are approved by their own user word. An absent key is an
                          absent key, never a null verdict.
  entry_malformed_<what>  the entry exists but does not carry both hex64 shas under LIVE_PINS / BUNDLE_BASE.

WHAT IT DELIBERATELY DOES **NOT** DO: it never hashes a file and never looks at a path. It answers one question only — "which sha
is approved for this month" — so that the caller's identity check stays a byte comparison against an approved constant.
"""

RULING_KEY = "TRN-15_export_baseline_per_month"
MAP_KEY = "approved_export_baselines"
FIELDS = (("LIVE_PINS", "live_pins_sha256"), ("BUNDLE_BASE", "bundle_base_sha256"))


def _hex64(s):
    return isinstance(s, str) and len(s) == 64 and all(c in "0123456789abcdef" for c in s)


def approved_export_baseline(contract, month):
    """(entry, reason, detail) — entry is None iff reason is not None; NEVER both None.

    entry = {"live_pins_sha256": ..., "bundle_base_sha256": ..., "source": "<json path in the contract>",
             "approved_utc": ..., "declared_paths": {...}}  (declared_paths is provenance only; the binding is the sha)
    """
    ruling = ((contract.get("month_contract_rulings") or {}).get(RULING_KEY) or {})
    amap = ruling.get(MAP_KEY)
    if not isinstance(amap, dict):
        return None, "contract_block_absent", {
            "looked_for": f"month_contract_rulings.{RULING_KEY}.{MAP_KEY}",
            "why": "this contract still carries only the single frozen gates.BUNDLE_export.approved_baseline pair, which is "
                   "one month's approval; the per-month approval map is the approved object from 2026-09-18 onwards",
            "not_a_fallback": "gates.BUNDLE_export.approved_baseline is NOT used as a fallback — see this module's docstring"}
    if not (isinstance(month, str) and month.strip()):
        return None, "month_not_declared", {
            "month": month, "looked_for": "env V4_MONTH (the month contract's own V4_MONTH key)",
            "why": "the approved baseline is per month, so a run that does not say which month it is cannot be checked against "
                   "an approved sha (E-0826-D)", "months_declared": sorted(amap)}
    month = month.strip()
    if month not in amap:
        return None, "month_not_approved", {
            "month": month, "reason": "no entry", "months_declared": sorted(amap),
            "why": f"no approved export baseline for month {month} in "
                   f"month_contract_rulings.{RULING_KEY}.{MAP_KEY}; this month's live_pins.json and baseline json must be "
                   f"立档 and their shas approved (a separate, recorded user word) before the export stage can run"}
    ent = amap[month]
    if ent is None:
        return None, "month_not_approved", {
            "month": month, "reason": "entry is null (deliberately unapproved)", "months_declared": sorted(amap),
            "why": f"month {month} is present but explicitly null: the month's pins / baseline do not exist yet or have not "
                   f"been approved. Null is a refusal, never a skipped check"}
    if not isinstance(ent, dict):
        return None, "entry_malformed_not_an_object", {"month": month, "got_type": type(ent).__name__}
    out = {"source": f"month_contract_rulings.{RULING_KEY}.{MAP_KEY}.{month}",
           "approved_utc": ent.get("approved_utc"), "declared_paths": {}}
    for key, field in FIELDS:
        sub = ent.get(key)
        if not isinstance(sub, dict):
            return None, f"entry_malformed_{key}_missing", {"month": month, "looked_for": f"{out['source']}.{key}"}
        sha = sub.get("sha256")
        if not _hex64(sha):
            return None, f"entry_malformed_{key}_sha256", {"month": month, "got": str(sha)[:24],
                                                           "looked_for": f"{out['source']}.{key}.sha256 (64 hex chars)"}
        out[field] = sha
        out["declared_paths"][key] = sub.get("path")
    return out, None, {"month": month, "months_declared": sorted(amap)}
