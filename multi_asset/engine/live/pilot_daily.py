"""Daily pilot-prep orchestrator: guards -> logs -> metrics -> watchdog -> mirrored report.

Covers §9.5 items ④ (regime persisted), ⑥ (factor assertion + panel hash in the DAILY pipeline,
not just the build), ② (metrics with recorded hash) and ⑤ (report auto-mirrored to a second pair
of eyes).

★ ORDER MATTERS AND IS DELIBERATE:
  1. regime classifier      -- labels stamped BEFORE any markout is computed (§9-F8)
  2. factor + panel guards  -- if these fail the run REFUSES TO EMIT READINGS (§9-F10). A number
                               produced from an unverified panel is worse than no number: it looks
                               like evidence.
  3. shadow v2 logging      -- exercises the frozen schema on live signal data
  4. pilot_metrics          -- the only thing the gates may read, hash recorded alongside
  5. watchdog               -- all seven §4 conditions, mock broker
  6. report + mirror        -- single-operator work has no second reader; the stop-loss verdict
                               must be visible to someone not inside the loss

*** MOCK ONLY: no account, no credentials, no venue contact anywhere in this chain. ***

Out: exports/live/pilot_daily/<YYYYMMDD>/{report.md, report.json}
     exports/live/pilot_daily/mirror/<YYYYMMDD>_report.md   (delivery channel TBD by user)
"""
from __future__ import annotations
import argparse, hashlib, json, os, shutil, subprocess, sys, time

MA = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # .../multi_asset
PY = sys.executable
sys.path.insert(0, MA + "/engine/live")
sys.path.insert(0, MA)

def _env(name, default):
    """Env override -> works across process boundaries (inject_failures drives this as a
    subprocess, where setting a module attribute in the parent has no effect)."""
    return os.environ.get(name, default)


OUT = _env("PILOT_DAILY_OUT", MA + "/exports/live/pilot_daily")
MIRROR = _env("PILOT_DAILY_MIRROR", OUT + "/mirror")
LOG_ROOT = _env("PILOT_LOG_ROOT", MA + "/exports/live/pilot_log")
# ★ Production watchdog state lives at an EXPLICIT path. Relying on watchdog.py's default let a
# test that called PD.main() write a trip into PRODUCTION state (it did: a -8%/-48% fixture from
# tests_production_signature showed up as a standing HALT). Tests must override this.
WATCHDOG_STATE_DIR = _env("PILOT_WATCHDOG_DIR", MA + "/exports/live/watchdog")
LIVE_PANEL = _env("PILOT_LIVE_PANEL", MA + "/exports/live/wide_dl_live.npz")
# The production panel path, kept separately from the (overridable) LIVE_PANEL so the synthetic
# declaration in run_guards can be checked against something a test cannot move.
_PROD_LIVE_PANEL = MA + "/exports/live/wide_dl_live.npz"
# The factor version the engine is DECLARED to run (protocol §9.5). champion/challenger run the
# pre-fix factor; only the fixfunding third track runs the corrected one.
TRACK = "champion"          # which track this daily run represents
DECLARED_FACTOR_VERSION = "funding_ema_broken_v1"
# ★ TWO DIFFERENT STALENESS FAILURES, TWO THRESHOLDS (my first version conflated them and produced
# a false block):
#   FILE age  -- was the panel rebuilt at all? Detects a dead/crashed pipeline. Cron is daily, so
#                anything over ~30h means the loop itself stopped.
#   DATA age  -- how old is the newest bar INSIDE the panel? This feed is built from the T+1 public
#                archive, so a ~48-58h data lag is NORMAL and healthy, not a fault. Measured on a
#                healthy run: file age 0.8h, data age 57.8h.
# Blocking on data age with a file-age threshold marks every healthy day as stale.
# ⚠ The PILOT runs off a live venue feed, not the T+1 archive — when that path is wired,
#   MAX_PANEL_DATA_AGE_H must drop to hours, not days. This constant is path-specific.
# ★ The data-age bound is a property of the DATA SOURCE, not a free constant. Binding them means a
# source switch that forgets to retune the bound BLOCKS instead of silently carrying an
# archive-calibrated gate into a live-feed pilot. (Otherwise this is the next constant to escape
# its single source of truth.)
DATA_SOURCE_TYPE = _env("PILOT_DATA_SOURCE_TYPE", "t_plus_1_public_archive")     # the shadow's feed
DATA_SOURCE_MAX_DATA_AGE_H = {
    "t_plus_1_public_archive": 96.0,   # T+1 archive + weekend margin; healthy observed = 57.8h
    "live_venue_feed": 6.0,            # pilot: a live feed lagging >6h is a fault, not a cadence
}
MAX_PANEL_FILE_AGE_H = 30.0


def panel_hash(path):
    # A missing panel is a legitimate operational state (build failed, wrong path) and its correct
    # handling is to BLOCK, not to raise: an exception aborts the whole daily chain including the
    # report that would have told the operator why.
    if not os.path.exists(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1 << 22):
            h.update(chunk)
    return h.hexdigest()[:16]


# ★ A HERMETIC FIXTURE MAY DECLARE ITS PANEL SYNTHETIC — AND THE REPORT THEN SAYS "NOT VERIFIED",
# NOT "PASS". The suites run against a tiny generated panel (tests_fixture.py) that carries no
# `xsr_fund` channel and no settlement-interval archive, so the funding-caliber question is not
# merely unanswered on it, it is UNDEFINED. Until 2026-07-27 the criterion happened to accommodate
# this by accident (it expected the gate to FAIL on the declared pre-fix version, and the gate did
# fail — for the unrelated reason that a channel was missing). That accident held a suite green and
# hid the fact that nothing was being checked. Now the exemption is EXPLICIT, and:
#   * it is honoured only for a panel that is NOT the production one (asserted below), so the
#     escape hatch cannot be opened on the live panel;
#   * it records NOT_VERIFIED rather than a pass — an unanswerable question must never resolve to
#     the benign answer.
SYNTHETIC_PANEL = False


def run_guards(verbose=True):
    """§9.5 ⑥ — factor-dimension assertion + panel hash. Failure BLOCKS readings."""
    g = {"ok": True, "checks": {}}
    if SYNTHETIC_PANEL:
        if os.path.abspath(LIVE_PANEL) == os.path.abspath(_PROD_LIVE_PANEL):
            raise RuntimeError(
                "SYNTHETIC_PANEL was declared while LIVE_PANEL still points at the production "
                f"panel ({LIVE_PANEL}). That combination can only be a mistake, and honouring it "
                "would disable the caliber guard on the real book.")
        rc = 0
        g["checks"]["assert_funding_dim"] = {
            "exit_code": None, "pass": None, "state": "NOT_VERIFIED",
            "note": ("panel declared SYNTHETIC by the test fixture: it has no xsr_fund channel and "
                     "no settlement-interval archive, so the caliber signature is undefined on it. "
                     "Recorded as NOT VERIFIED — never as a pass.")}
    else:
        rc = subprocess.call([PY, MA + "/exports/eda/assert_funding_dim.py", "--panel", LIVE_PANEL],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # ★ REWRITTEN 2026-07-27 (0C). This block used to say a non-zero exit was the EXPECTED
        # state, because the guard then asserted ONE caliber on every panel. The guard now asserts
        # the caliber each artifact is SUPPOSED to have, so the live panel — which correctly carries
        # the as-trained caliber the frozen heads were fitted on — exits 0. Both this note and the
        # criterion below were written against the old semantics and had to move with them.
        g["checks"]["assert_funding_dim"] = {
            "exit_code": rc, "pass": rc == 0,
            "state": {0: "VERIFIED", 1: "CALIBER_VIOLATION"}.get(rc, "CANNOT_JUDGE"),
            "note": ("the guard asserts the caliber THIS artifact is supposed to have, so exit 0 is "
                     "the healthy state for every declared version. 1 = it carries the other "
                     "caliber; 2 = there was nothing to measure (a malformed panel), which blocks "
                     "for a different reason than a caliber violation and must not be reported as "
                     "one. There is no longer any version for which a red is 'expected'.")}
    ph = panel_hash(LIVE_PANEL)
    g["checks"]["panel_hash"] = {"panel": os.path.basename(LIVE_PANEL), "sha256_16": ph,
                                 "exists": ph is not None}
    if ph is None:
        g["ok"] = False
        g["blocking_reason"] = (f"live panel not found at {LIVE_PANEL} — refusing to emit readings "
                                "without the panel they would be derived from")
    # ★ close the last human link: protocol -> declaration -> observation, all machine.
    # PER-TRACK, because champion/challenger deliberately run the pre-fix factor and a global
    # assertion would turn the whole shadow red for no reason.
    import factor_version_registry as FVR
    ok_v, vdetail = FVR.assert_track_version(TRACK, DECLARED_FACTOR_VERSION)
    g["checks"]["protocol_version_registry"] = vdetail
    if not ok_v:
        g["ok"] = False
        g["blocking_reason"] = vdetail["meaning"]
    # ★ THE EXPECTED EXIT COMES FROM THE REGISTRY, NOT FROM A VERSION STRING SPELLED OUT HERE.
    # It used to read `expect_pass = (DECLARED_FACTOR_VERSION != "funding_ema_broken_v1")`, i.e. the
    # criterion restated the registry's content in a different form — and when the guard's semantics
    # changed on 2026-07-27 the two forms disagreed. Measured consequence on that morning's run:
    # `assert_funding_dim exit=0` (healthy) yet `consistent_with_declaration: false` and
    # `blocking_reason: panel factor state does not match DECLARED_FACTOR_VERSION`, blocking §9.5
    # readings for a panel that was exactly what it declared. A gate that goes red for the wrong
    # reason is the same defect as one that goes green for the wrong reason, and it costs the same
    # thing: the next reader stops believing the colour.
    # ⇒ Same rule the registry's own docstring states: REFERENCE THE SYMBOL, NEVER RESTATE IT.
    want_rc = FVR.expected_gate_exit(DECLARED_FACTOR_VERSION)
    consistent = (rc == want_rc)
    g["checks"]["factor_version_declaration"] = {
        "declared": DECLARED_FACTOR_VERSION, "guard_pass": rc == 0,
        "expected_gate_exit": want_rc, "observed_gate_exit": rc,
        "consistent_with_declaration": consistent,
        "meaning": ("the guard's exit for this declared version must equal the registry's "
                    "`assert_funding_dim_expected_exit` (0 for every version since 2026-07-27, "
                    "because each panel is asserted against the caliber it is supposed to have). "
                    "A mismatch means the engine is not running what the protocol says it runs.")}
    if not consistent:
        g["ok"] = False
        g["blocking_reason"] = ("panel factor state does not match DECLARED_FACTOR_VERSION — "
                                "refusing to emit gate readings (§9-F10)")
    # ★ UPSTREAM STALENESS (found by the §9.5-①b late-data injection). The worst of the three
    # possible behaviours is silently writing today's records from yesterday's panel: it produces a
    # record that looks current and is not. So staleness is a BLOCKING guard, not a warning.
    import numpy as _np
    try:
        _ts = _np.load(LIVE_PANEL, allow_pickle=True)["ts"]
        data_age_h = (time.time() * 1000 - int(_ts[-1])) / 3600_000.0
        file_age_h = (time.time() - os.path.getmtime(LIVE_PANEL)) / 3600.0
    except Exception:
        data_age_h = file_age_h = float("inf")
    if DATA_SOURCE_TYPE not in DATA_SOURCE_MAX_DATA_AGE_H:
        g["ok"] = False
        g["blocking_reason"] = (f"DATA_SOURCE_TYPE {DATA_SOURCE_TYPE!r} has no calibrated data-age "
                                "bound — refusing to run rather than reuse another source's gate")
        MAX_PANEL_DATA_AGE_H = float("inf")
    else:
        MAX_PANEL_DATA_AGE_H = DATA_SOURCE_MAX_DATA_AGE_H[DATA_SOURCE_TYPE]
    g["checks"]["data_source_binding"] = {
        "data_source_type": DATA_SOURCE_TYPE,
        "data_age_limit_h": MAX_PANEL_DATA_AGE_H,
        "note": ("the bound is looked up FROM the source type; switching sources without adding a "
                 "bound blocks the run instead of silently reusing the old calibration")}
    g["checks"]["panel_freshness"] = {
        "file_age_hours": (round(file_age_h, 2) if file_age_h != float("inf") else None),
        "file_limit_hours": MAX_PANEL_FILE_AGE_H,
        "data_age_hours": (round(data_age_h, 2) if data_age_h != float("inf") else None),
        "data_limit_hours": MAX_PANEL_DATA_AGE_H,
        "pass": (file_age_h <= MAX_PANEL_FILE_AGE_H and data_age_h <= MAX_PANEL_DATA_AGE_H),
        "note": ("file age = did the pipeline run; data age = how old the newest bar is. This feed "
                 "is T+1-archive based so ~48-58h data lag is normal. The pilot's live feed will "
                 "need a far tighter data bound.")}
    if file_age_h > MAX_PANEL_FILE_AGE_H:
        g["ok"] = False
        g["blocking_reason"] = (f"live panel FILE not rebuilt for {file_age_h:.1f}h "
                                f"(> {MAX_PANEL_FILE_AGE_H}h) — the pipeline appears stopped; "
                                "refusing to emit readings or write records from stale upstream data")
    elif data_age_h > MAX_PANEL_DATA_AGE_H:
        g["ok"] = False
        g["blocking_reason"] = (f"newest panel DATA is {data_age_h:.1f}h old "
                                f"(> {MAX_PANEL_DATA_AGE_H}h) — upstream archive is late; refusing "
                                "to write records from stale upstream data")

    day_rc = subprocess.call([PY, MA + "/exports/eda/check_day_budget.py"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) \
        if os.path.exists(MA + "/exports/eda/check_day_budget.py") else 0
    g["checks"]["check_day_budget"] = {"exit_code": day_rc, "pass": day_rc == 0}
    if day_rc != 0:
        g["ok"] = False
        g["blocking_reason"] = "check_day_budget.py non-zero — day-count invariants violated"
    if verbose:
        print(f"[guards] assert_funding_dim exit={rc} | panel {ph} | "
              f"day_budget exit={day_rc} | OK={g['ok']}", flush=True)
    return g


def main(days_back=1, skip_log=False, verbose=True):
    day = time.strftime("%Y%m%d", time.gmtime())
    d = os.path.join(OUT, day)
    os.makedirs(d, exist_ok=True)
    os.makedirs(MIRROR, exist_ok=True)
    rep = {"day": day, "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "caliber": ("SHADOW/MOCK — simulated fills, no account, no venue contact. Schema and "
                       "pipeline evidence only; NOT execution evidence.")}

    import regime_classifier as RC
    rep["regime"] = {"days_written": RC.run(panel=LIVE_PANEL,
                                        days_back=max(days_back, 2),
                                        verbose=verbose)[-3:]}

    rep["guards"] = run_guards(verbose=verbose)

    if not skip_log and rep["guards"]["ok"]:
        import shadow_pilot_log as SPL
        rep["shadow_log_days"] = SPL.run(days_back=days_back, verbose=verbose)
    elif not skip_log:
        rep["shadow_log_days"] = []
        rep["shadow_log_skipped_reason"] = rep["guards"].get("blocking_reason")

    if not rep["guards"]["ok"]:
        rep["metrics"] = None
        rep["watchdog"] = None
        rep["status"] = ("BLOCKED — guards failed; readings deliberately withheld: "
                         + str(rep["guards"].get("blocking_reason", "")))
        if verbose:
            print(f"[pilot_daily] ★ {rep['status']}", flush=True)
    else:
        import pilot_metrics as PM
        import watchdog as WD
        import watchdog_inputs as WI
        rep["metrics"] = PM.compute(LOG_ROOT, verbose=verbose)
        # ★ PRODUCTION MUST SUPPLY THESE. Calling WD.run(LOG_ROOT) bare left §4-5 and §4-7 with no
        # inputs at all, so both were structurally unable to fire in production while their
        # component tests passed — the tests supplied what production never did.
        ops_stats, venue_events, wdiag = WI.collect(LOG_ROOT)
        rep["watchdog_inputs"] = wdiag
        rep["watchdog_inputs"]["ops_stats_tail"] = ops_stats[-3:]
        rep["watchdog_inputs"]["venue_events"] = venue_events
        ev, br, st = WD.run(LOG_ROOT, venue_events=venue_events, ops_stats=ops_stats,
                            verbose=verbose, state_dir=WATCHDOG_STATE_DIR)
        rep["watchdog"] = {"tripped": ev["tripped"], "triggers": ev["triggers"],
                           "conditions": {k: v["triggered"] for k, v in ev["conditions"].items()},
                           "mock_actions": br.actions, "state": st}
        # ★ THE HEADLINE MUST REFLECT THE WORST THING THAT HAPPENED, not just the guards.
        # Previously `status` was decided by guards alone, so a run in which the watchdog tripped,
        # flattened the book and engaged reduce-only still printed "Status: OK" on line 3. When the
        # headline and the body disagree the headline wins -- especially in the 10:00 SGT
        # glance-at-it scenario this report is designed for. A report that says OK while the book
        # has been flattened is worse than no report: it actively supplies false reassurance.
        # ★ STANDING STATE IS SEPARATE FROM THIS RUN'S EVALUATION.
        # Three individually-correct behaviours composed into an invisible shutdown: the watchdog
        # re-evaluates and reports THIS run (right); reduce_only persists across runs by design
        # (right); but the report only ever showed this run's evaluation (wrong). One run after a
        # trip, the report would read "Status: OK / tripped: False" while the book was still
        # flat and in reduce-only. A halted book must never be able to look like a healthy one.
        standing = {"reduce_only": bool(st.get("reduce_only")),
                    "open_orders_halted": bool(st.get("open_orders_halted")),
                    "tripped_at": st.get("tripped_at"), "reason": st.get("reason"),
                    "last_action_utc": st.get("last_action_utc"),
                    "resume_requires": st.get("resume_requires")}
        rep["standing_state"] = standing
        # ★ ALARM entries must LEAVE this machine. Writing ALARM.log proves only that a local
        # append succeeded; pilot_daily previously never read it, so alerts reached neither the
        # report, the mirror, nor email. A notify step whose success criterion is a local write has
        # fake reliability — the same error as "mirrored to another directory on this box".
        alarm_p = os.path.join(WATCHDOG_STATE_DIR, "ALARM.log")
        alarms = []
        if os.path.exists(alarm_p):
            for line in open(alarm_p):
                line = line.strip()
                if line:
                    try:
                        alarms.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        rep["alarms"] = {"n_total": len(alarms), "recent": alarms[-5:],
                         "source": alarm_p,
                         "delivered_offbox": None}   # set by the delivery step below
        halted = standing["reduce_only"] or standing["open_orders_halted"]
        if ev["tripped"]:
            acted = st.get("degradation", {})
            flat = "book flattened" if acted.get("stage1_ok", True) else "FLATTEN FAILED"
            rep["status"] = (f"TRIPPED — {flat}, reduce-only engaged — {'; '.join(ev['triggers'])}")
        elif halted:
            rep["status"] = ("HALTED (standing) — no NEW trigger this run, but the book remains "
                             f"reduce-only since {standing['tripped_at']} — {standing['reason']}")
        else:
            rep["status"] = "OK"

    json.dump(rep, open(os.path.join(d, "report.json"), "w"), indent=1, default=str)

    m = rep.get("metrics") or {}
    m1 = (m.get("M1_effective_cost") or {})
    lines = [f"# Pilot-prep daily report — {day}", "",
             f"**Status: {rep['status']}**", "",
             f"> {rep['caliber']}", "",
             "## Guards",
             f"- factor dimension assertion: exit {rep['guards']['checks']['assert_funding_dim']['exit_code']}",
             f"- declared factor version: `{DECLARED_FACTOR_VERSION}` — consistent: "
             f"{rep['guards']['checks']['factor_version_declaration']['consistent_with_declaration']}",
             f"- live panel sha256: `{rep['guards']['checks']['panel_hash']['sha256_16']}`", ""]
    if rep.get("metrics"):
        rcv = m.get("regime_coverage", {})
        lines += ["## Metrics (pilot_metrics.py — the only source the gates read)",
                  f"- script sha256: `{m.get('pilot_metrics_sha256','')[:16]}…`",
                  f"- days: {m.get('n_days')}",
                  f"- **M1 c = {m1.get('c_bps_overall')} bps/side**",
                  "  - by regime: " + ", ".join(
                      f"{k} {v['c_bps']} (n={v['n_filled_orders']})"
                      for k, v in (m1.get("by_regime") or {}).items()),
                  f"- M2 markout = {(m.get('M2_markout') or {}).get('markout_bps')} bps",
                  f"- M3 fill rate = {(m.get('M3_fill_rate') or {}).get('fill_rate')}",
                  f"- M4 turnover (target, ann) = "
                  f"{(m.get('M4_turnover') or {}).get('target_weight_turnover_annualised')} "
                  f"vs backtest 1466",
                  f"- M5 mean |w err| = {(m.get('M5_weight_fidelity') or {}).get('mean_abs_weight_error')}",
                  f"- M6 funding = {(m.get('M6_funding') or {}).get('funding_paid_total_usd')} USD",
                  ""]
        if rcv.get("blind_spot_warning"):
            lines += [f"> ⚠ **{rcv['blind_spot_warning']}**", ""]
        w = rep["watchdog"]
        al = rep.get("alarms", {})
        if al.get("recent"):
            lines += ["## ⚠ ALARMS (from the watchdog's alert rung)"]
            for a in al["recent"]:
                lines += [f"- `{a.get('ts')}` **{a.get('severity')}** — {a.get('msg')}"
                          f"{'  ⟨flatten_ok=' + str(a.get('flatten_ok')) + '⟩' if 'flatten_ok' in a else ''}"]
            lines += ["", f"*{al.get('n_total')} alarm(s) recorded in total. A local write is NOT "
                      "a notification — delivery status is below.*", ""]
        sd = rep.get("standing_state", {})
        if sd.get("reduce_only") or sd.get("open_orders_halted"):
            lines += ["## ⚠ STANDING STATE (independent of this run's evaluation)",
                      f"- **reduce_only: {sd.get('reduce_only')}**",
                      f"- **open_orders_halted: {sd.get('open_orders_halted')}**",
                      f"- tripped_at: {sd.get('tripped_at')}  (last action {sd.get('last_action_utc')})",
                      f"- reason: {sd.get('reason')}",
                      f"- resume requires: {sd.get('resume_requires')}",
                      "", "*A past trip leaves the book halted. This section is shown from the "
                      "persisted state, not from this run's evaluation, so a shutdown cannot go "
                      "invisible once the triggering condition stops re-firing.*", ""]
        wi = rep.get("watchdog_inputs", {})
        pp = wi.get("public_path_probe", {})
        lines += ["## Venue diagnostics (informational — NOT part of the trigger logic)",
                  f"- venue public endpoint: **{'alive' if pp.get('alive') else 'DOWN'}**"
                  f" ({pp.get('n_markets', '?')} markets, {pp.get('ms', '?')} ms)",
                  "- *Ruling (team-lead): the public-path signal discriminates account-side from "
                  "venue-side, but both route to the SAME conservative protective action, so the "
                  "discrimination changes nothing about whether we stop. Its value is telling the "
                  "operator what to do NEXT — an outage is waited out, a restriction means stop and "
                  "investigate. It therefore lives here, in the diagnostics, and is deliberately "
                  "kept OUT of the protection path, where it would only add failure surface.*", "",
                  "## Watchdog (§4, seven conditions, MOCK broker)",
                  f"- inputs derived by this run: public-path alive="
                  f"{wi.get('public_path_probe',{}).get('alive')}, "
                  f"ops days={wi.get('n_days')}, venue events={len(wi.get('venue_events',[]))}",
                  f"- **tripped: {w['tripped']}**"]
        if w["triggers"]:
            lines += [f"  - {t}" for t in w["triggers"]]
        lines += ["- conditions: " + ", ".join(f"{k}={v}" for k, v in w["conditions"].items()), ""]
    else:
        lines += ["## Metrics", "",
                  f"**WITHHELD — guards failed.**", "",
                  f"> Reason: {rep['guards'].get('blocking_reason','(unspecified)')}", "",
                  "*The operator reads this report, not exit codes — so the reason for a block "
                  "must appear here.*", ""]
    lines += ["---",
              "*Auto-mirrored: single-operator work has no second reader, so the stop-loss verdict "
              "must be visible to someone who is not inside the loss (§9-F6-3).*"]
    md = "\n".join(lines)
    open(os.path.join(d, "report.md"), "w").write(md)
    shutil.copy(os.path.join(d, "report.md"), os.path.join(MIRROR, f"{day}_report.md"))
    try:
        import deliver_report as DR
        rep["delivery"] = DR.send_report(os.path.join(d, "report.md"), verbose=verbose)
        rep["delivery"]["second_eyes_status"] = "KNOWN GAP — recipient is the operator themselves"
        if isinstance(rep.get("alarms"), dict):
            # only a delivery receipt may be read as "the human was told"
            rep["alarms"]["delivered_offbox"] = bool(rep["delivery"].get("delivered"))
    except Exception as e:
        rep["delivery"] = {"delivered": False, "state": "DELIVERY_ERROR",
                           "detail": f"{type(e).__name__}: {str(e)[:150]}"}
    json.dump(rep, open(os.path.join(d, "report.json"), "w"), indent=1, default=str)
    if verbose:
        print(f"[pilot_daily] -> {d}/report.md (mirrored to {MIRROR}/)", flush=True)
    return rep


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--days_back", type=int, default=1)
    ap.add_argument("--skip_log", action="store_true")
    a = ap.parse_args()
    main(days_back=a.days_back, skip_log=a.skip_log)
