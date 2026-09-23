"""LED-08 (FX-EXEC2, 2026-09-13; AUDIT_EXEC 842bbffa): the per-anchor Telegram report no longer folds unknown fees and
fills to zero, judges taker share and |net/gross| against the book's own trailing distribution, labels halted and
rebuild anchors, and says "flat at settlement" instead of "funding.jsonl missing".

*** NO TELEGRAM, NO NETWORK: part [S] runs THIS tree's ops/anchor_report.py with `--dry` using explicit fixture paths
    for temporary wide_shadow/guard_twin directories and a temporary repo layout holding verbatim ledger
    lines (tests_fixtures/led08_anchor_report, sha-pinned); `.env` does not exist there. Parts [P] call the pure
    builder with urllib.request.urlopen replaced by a function that raises. ***

ASSERTED HERE:
  [S1] REAL 09-12 12Z (A1789215839, 4 unknown-fill rows): the printed fee is the MEASURED-only bps, re-derived here
       from the raw rows, and the unknown fills are named. ★ RED on ef60f85: `fee 2.74bps` over a denominator that
       folded the unknown fills to 0, no unknown-fill marker.
  [S2] REAL 09-13 08Z (settlement anchor, halted, previous slot flat): no `funding.jsonl 缺` warning; the line says
       no position at settlement; the intent is labelled unsent. ★ RED on ef60f85: `⚠️ funding.jsonl 缺`, no halted label.
  [S3] neighbour: the REAL 08-05 12Z order rows (103 fills, raw BNB fees `fee_paid 0.0, fee_all_usdt False`) under an
       external anchors row: fee prints `n/a(未测, 非 0)`. ★ RED on ef60f85: `fee 0.00bps`.
  [P1] robust_band: fewer than 12 values ⇒ no threshold; None values are not values.
  [P2] history_facts on the real anchors projection: the baseline slots exclude rebuild and halted slots, are strictly
       before A, at most 42; a rebuild A is marked.
  [P3] build_report cells: taker above the band warns on a normal anchor, not on a rebuild or halted one; |net/gross|
       above 5% warns with no baseline; None net/gross neither warns nor prints a number; missing funding file with
       the previous slot holding / unknown / flat.
  [P4] the builder reads no network (urlopen raises for the whole of [P]).

NOT asserted: the Telegram transport; whether the trailing band is the right POLICY (the template owner decides levels);
the shadow/combo checks, which are unchanged text over unchanged inputs.
  [P5] (quant_research DESIGN_producer_new_contract §A7-5) the producer-daemon check follows config external_book.producer_contract:
       legacy (key missing / null / "legacy") requires prod + sidecar + combo; nc_v1 requires prod + combo and warns when the
       sidecar runs; an unknown value is a named warning checked as legacy.
Exit 0 = all pass.
"""
import gzip
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, "ops"))

FAILS, N = [], [0]


def check(name, cond, detail=""):
    N[0] += 1
    print(f"  {'OK  ' if cond else 'FAIL'}  {name}{('  — ' + str(detail)[:400]) if detail != '' else ''}", flush=True)
    if not cond:
        FAILS.append(name)


FIX = os.path.join(HERE, "tests_fixtures", "led08_anchor_report")
MAN = json.load(open(os.path.join(FIX, "MANIFEST.json")))


def blob(name):
    e = [x for x in MAN["extracts"] if x["file"] == name][0]
    b = gzip.open(os.path.join(FIX, name), "rb").read()
    assert hashlib.sha256(b).hexdigest() == e["extract_sha256"], name
    return b


A08_12, A12 = 1789200000, 1789214400          # 09-12 08Z / 12Z
A13_04, A13_08 = 1789272000, 1789286400       # 09-13 04Z / 08Z
A_SYN = 1789228800                             # 09-12 16Z slot used for the synthetic external row

print("[0] fixture integrity")
_ok = True
for e in MAN["extracts"]:
    try:
        blob(e["file"])
    except AssertionError:
        _ok = False
check("every extract hashes to its MANIFEST sha", _ok)

# ── temp repo layout + explicit external input directory ──────────────────────────────────────
TMP = tempfile.mkdtemp(prefix="led08_")
TREPO, THOME = os.path.join(TMP, "repo"), os.path.join(TMP, "home")
os.makedirs(os.path.join(TREPO, "ops")); os.makedirs(os.path.join(TREPO, "live"))
os.makedirs(os.path.join(TREPO, "config"), exist_ok=True)
shutil.copy2(os.path.join(REPO, "ops", "anchor_report.py"), os.path.join(TREPO, "ops", "anchor_report.py"))
# ★ LED-08 follow-up (2026-09-16): `cost_drift.py` and `config/cost_drift_reference.json` join the temp repo so the
#   report can load its FROZEN reference. Both copies are guarded by existence, so this same file still runs — and
#   still goes red for its own reasons — against a tree that predates them. No assertion below is changed.
for m in ("cost_buckets.py", "pilot_log.py", "cost_drift.py"):
    if os.path.exists(os.path.join(HERE, m)):
        shutil.copy2(os.path.join(HERE, m), os.path.join(TREPO, "live", m))
_dref = os.path.join(REPO, "config", "cost_drift_reference.json")
if os.path.exists(_dref):
    shutil.copy2(_dref, os.path.join(TREPO, "config", "cost_drift_reference.json"))
PLR = os.path.join(TREPO, "state", "live", "pilot_log")
os.makedirs(os.path.join(PLR, "20260912")); os.makedirs(os.path.join(PLR, "20260913"))
a12 = [json.loads(l) for l in blob("20260912_anchors_08Z_12Z.jsonl.gz").splitlines() if l.strip()]
syn = json.loads(json.dumps([r for r in a12 if r["external_book"]["nominal_ts"] == A12][0]))
syn["external_book"]["nominal_ts"] = A_SYN
syn["rebalance_id"] = "A1785931245"
syn["opening_halted"] = False
with open(os.path.join(PLR, "20260912", "anchors.jsonl"), "wb") as f:
    f.write(blob("20260912_anchors_08Z_12Z.jsonl.gz"))
    f.write((json.dumps(syn) + "\n").encode())
with open(os.path.join(PLR, "20260912", "orders.jsonl"), "wb") as f:
    f.write(blob("20260912_orders_A1789215839.jsonl.gz"))
    f.write(blob("20260805_orders_A1785931245.jsonl.gz"))
with open(os.path.join(PLR, "20260913", "anchors.jsonl"), "wb") as f:
    f.write(blob("20260913_anchors_04Z_08Z.jsonl.gz"))
open(os.path.join(PLR, "20260913", "orders.jsonl"), "wb").close()
WS = os.path.join(THOME, "wide_shadow")
os.makedirs(os.path.join(WS, "state", "target_combo")); os.makedirs(os.path.join(THOME, "guard_twin", "state"))
with open(os.path.join(WS, "shadow_log.jsonl"), "w") as f:
    for A in (A12, A13_08, A_SYN):
        f.write(json.dumps({"anchor_ts": A, "fund_updates": (453 if (A // 3600) % 24 in (0, 8, 16) else 353),
                            "coverage": 1.0, "forced_exit_n": 0}) + "\n")
json.dump({"ok": True, "reader_ok": True}, open(os.path.join(WS, "state", "combo_live_status.json"), "w"))
for A in (A12, A13_08, A_SYN):
    json.dump({"meta": {"w3_masked": [0.38, 0.0, 0.62], "kc_state_source": "own", "fc_state_source": "own",
                        "n_f10_scored": 400}}, open(os.path.join(WS, "state", "target_combo", f"{A}.json"), "w"))
open(os.path.join(THOME, "guard_twin", "state", "guard_twin.out"), "w").write("2026-09-13T12:26:00Z AGREE eq=1 nav=1\n")


def run_report(A):
    env = {"PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1"}
    driver = os.path.join(HERE, "tests_fixtures", "report", "offline_driver.py")
    p = subprocess.run(["/usr/bin/python3", "-B", driver, os.path.join(TREPO, "ops", "anchor_report.py"),
                        THOME, "--anchor", str(A),
                        "--dry"], capture_output=True, text=True, env=env, timeout=120)
    check("real report CLI consumed the isolated process/path inputs",
          "REPORT_FIXTURE_BOUNDARIES:" in p.stderr, p.stderr[-300:])
    last = None
    try:
        last = json.load(open(os.path.join(TREPO, "state", "anchor_report_last.json")))
    except Exception:
        pass
    return p.returncode, p.stdout, p.stderr, last


def measured_fee_bps(rows):
    """Independent re-derivation: fee over rows with a finite non-zero fill, usable avg_fill_px and mid_at_anchor,
    and a fee that is a finite USDT number (not a raw mixed-asset slice)."""
    import math
    fee = notl = 0.0
    n_unknown = 0
    for o in rows:
        fn = o.get("filled_notional")
        if fn is None:
            n_unknown += 1
            continue
        fa = abs(float(fn))
        if fa <= 0:
            continue
        px, mid, fp = o.get("avg_fill_px"), o.get("mid_at_anchor"), o.get("fee_paid")
        if not (px and mid and float(px) > 0 and float(mid) > 0):
            continue
        if fp is None or (o.get("fee_all_usdt") is False and not o.get("fee_conversion")) or not math.isfinite(float(fp)):
            continue
        fee += float(fp); notl += fa
    return (1e4 * fee / notl if notl else None), n_unknown


print("\n[S1] ★★★ REAL 09-12 12Z (A1789215839): measured-only fee, unknown fills named")
O12 = [json.loads(l) for l in blob("20260912_orders_A1789215839.jsonl.gz").splitlines() if l.strip()]
exp_bps, exp_unk = measured_fee_bps(O12)
rc, out, err, last = run_report(A12)
m = re.search(r"fee ([0-9.]+)bps", out)
check("PRE: 496 rows, 4 unknown-fill rows, re-derived measured fee bps 2.47", len(O12) == 496 and exp_unk == 4
      and exp_bps is not None and abs(exp_bps - 2.47) < 0.005, (len(O12), exp_unk, exp_bps))
check("the report ran (rc 0) without .env and without sending", rc == 0 and "[sent]" not in out, (rc, err[-300:]))
check("★★★ the printed fee is the MEASURED-only bps (old tree: 2.74 over a denominator with the unknown fills as 0)",
      m is not None and abs(float(m.group(1)) - exp_bps) < 0.006, (m.group(0) if m else None, round(exp_bps, 4)))
check("★★ the 4 unknown-fill rows are named on the line", "成交未知 4 行" in out,
      [l for l in out.splitlines() if "fee" in l])

print("\n[S2] ★★★ REAL 09-13 08Z: settlement anchor, halted, previous slot flat")
rc2, out2, err2, last2 = run_report(A13_08)
check("the report ran (rc 0)", rc2 == 0, err2[-300:])
check("★★★ no `funding.jsonl 缺` warning (old tree: ⚠️ funding.jsonl 缺 on a flat book)",
      last2 is not None and not any("funding.jsonl 缺" in w for w in last2.get("warn", [])), (last2 or {}).get("warn"))
check("★★ the line says no position at settlement", "结算时无持仓" in out2, [l for l in out2.splitlines() if "funding" in l])
check("★★ the halted anchor's intent is labelled unsent, not called turnover (old tree: no halted label, `换手`)",
      "停开仓" in out2 and "意图(未发送)" in out2 and " 换手 " not in out2, [l for l in out2.splitlines() if "age" in l])

print("\n[S3] ★★★ neighbour: REAL 08-05 12Z raw-BNB-fee rows under an external anchors row")
rc3, out3, err3, last3 = run_report(A_SYN)
O05 = [json.loads(l) for l in blob("20260805_orders_A1785931245.jsonl.gz").splitlines() if l.strip()]
check("PRE: 211 rows, every filled row's fee is a raw mixed-asset slice", len(O05) == 211
      and measured_fee_bps(O05)[0] is None, measured_fee_bps(O05))
check("★★★ fee prints n/a(未测, 非 0) (old tree: fee 0.00bps)", rc3 == 0 and "fee n/a(未测, 非 0)" in out3
      and "fee 0.00bps" not in out3, [l for l in out3.splitlines() if "fee" in l] or err3[-300:])

print("\n[P] pure builder cells (no network)")
import urllib.request as _ur   # noqa: E402
_ur.urlopen = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("network touched in a test"))
try:
    import anchor_report as AR   # noqa: E402
    _has = all(hasattr(AR, f) for f in ("build_report", "order_facts", "history_facts", "robust_band"))
except Exception as _e:
    AR, _has = None, False
if not _has:
    check("★★★ the builder is a pure function (build_report/order_facts/history_facts/robust_band)", False,
          "absent in this tree — the report is one I/O-bound main()")
else:
    b = AR.robust_band([0.1] * 11)
    b2 = AR.robust_band([0.1] * 11 + [None, 0.3])
    check("P1 fewer than 12 values ⇒ no threshold; None is not a value", b["threshold"] is None and b2["n"] == 12
          and b2["threshold"] is not None, (b, b2))
    rows = [json.loads(l) for l in gzip.open(os.path.join(HERE, "tests_fixtures", "led07_anchor_series",
                                                            "anchors_projection.jsonl.gz")) if l.strip()]
    import pilot_log as PL   # noqa: E402
    S = PL.anchor_series(rows)
    A_last = S["nominal_ts"][-1]
    h = AR.history_facts(rows, {}, A_last)
    check("P2 baseline slots: strictly before A, ≤42, no rebuild and no halted slot; the rebuild A is marked",
          h["slots"] and max(h["slots"]) < A_last and len(h["slots"]) <= 42
          and not set(h["slots"]) & set(S["rebuild_nominal_ts"]) and not set(h["slots"]) & set(S["halted_nominal_ts"])
          and h["is_rebuild"] is (A_last in S["rebuild_nominal_ts"]), (len(h["slots"]), h["is_rebuild"]))
    base = {"taker": {"n": 40, "median": 0.2, "mad": 0.05, "threshold": 0.42},
            "net_over_gross_abs": {"n": 40, "median": 0.01, "mad": 0.004, "threshold": 0.028}, "is_rebuild": False}
    def orow(t, fn, fee=0.01):
        return {"order_type": t, "filled_notional": fn, "avg_fill_px": 1.0, "mid_at_anchor": 1.0, "fee_paid": fee,
                "intended_notional": fn, "terminal_reason": "filled"}
    O = [orow("maker", 40.0), orow("topup_taker", 60.0)]
    row = {"external_book": {"nominal_ts": A12, "sha_ok": True}, "opening_halted": False, "realized_gross": 1000.0,
           "venue_net_usdt": 1.0, "net_over_gross": 0.001, "known_gaps": {"gross_usdt": 0.0}, "reshape": {"gross_before": 1000.0}}
    kw = dict(ps_text="", shadow_row=None, combo_status={}, target_combo={}, prev_row=None, funding_rows=[], twin_line="x")
    _, r1 = AR.build_report(A12, anchor_row=row, orders=O, history=base, **kw)
    _, r2 = AR.build_report(A12, anchor_row=row, orders=O, history=dict(base, is_rebuild=True), **kw)
    _, r3 = AR.build_report(A12, anchor_row=dict(row, opening_halted=True), orders=O, history=base, **kw)
    tw = lambda r: [w for w in r["warn"] if w.startswith("taker")]   # noqa: E731
    check("P3a taker 60% above the band warns on a normal anchor; not on a rebuild; not on a halted anchor",
          len(tw(r1)) == 1 and tw(r2) == [] and tw(r3) == [], (tw(r1), tw(r2), tw(r3)))
    _, r4 = AR.build_report(A12, anchor_row=dict(row, net_over_gross=0.06), orders=O,
                            history=dict(base, net_over_gross_abs={"n": 3, "median": None, "mad": None, "threshold": None}), **kw)
    _, r5 = AR.build_report(A12, anchor_row=dict(row, net_over_gross=None), orders=O, history=base, **kw)
    check("P3b |net/gross| 6% warns on the hard line with no baseline; None neither warns nor prints a number",
          any("硬线" in w for w in r4["warn"]) and not any("净敞口" in w for w in r5["warn"])
          and any("(n/a)" in l for l in r5["lines"]), (r4["warn"], r5["warn"]))
    kw2 = dict(kw, funding_rows=None)
    _, f_hold = AR.build_report(A13_08, anchor_row=row, orders=O, history=base, **dict(kw2, prev_row={"realized_gross": 5000.0}))
    _, f_unk = AR.build_report(A13_08, anchor_row=row, orders=O, history=base, **kw2)
    _, f_flat = AR.build_report(A13_08, anchor_row=row, orders=O, history=base, **dict(kw2, prev_row={"realized_gross": 0.0}))
    fw = lambda r: [w for w in r["warn"] if "funding" in w]   # noqa: E731
    check("P3c missing funding file: previous slot holding ⇒ warn (持仓中); unknown ⇒ warn (未知); flat ⇒ no warn",
          fw(f_hold) == ["funding.jsonl 缺(结算时持仓中)"] and fw(f_unk) == ["funding.jsonl 缺(上一锚持仓未知)"]
          and fw(f_flat) == [], (fw(f_hold), fw(f_unk), fw(f_flat)))
    # [P5] producer daemons by external_book.producer_contract (quant_research DESIGN_producer_new_contract §A7-5, lead 2026-09-23)
    P_ = "/x/venv/bin/python shadow_loop_v3.py run"; S_ = "/bin/bash /x/fea171/sidecar_daemon.sh"; C_ = "/bin/bash /x/fea171/combo_live_daemon.sh"
    def _dm(ps, **k):
        _, r = AR.build_report(A12, anchor_row=row, orders=O, history=base, **dict(kw, ps_text="\n".join(ps), **k))
        return [w for w in r["warn"] if "守护" in w or "侧车" in w or "producer_contract" in w], [l for l in r["lines"] if "守护" in l or "侧车" in l]
    w_all_leg, l_all_leg = _dm([P_, S_, C_], producer_contract=None)
    w_nosc_leg, _ = _dm([P_, C_], producer_contract=None)
    w_nosc_leg_key, _ = _dm([P_, C_], producer_contract="legacy")
    w_nosc_missing, _ = _dm([P_, C_])                                        # key missing: the builder's default
    check("P5a legacy (null / 'legacy' / key missing): all three running ⇒ '守护 3/3', no warning; sidecar absent ⇒ '守护缺 sidecar' in all three spellings",
          w_all_leg == [] and l_all_leg == ["守护 3/3"] and w_nosc_leg == ["守护缺 sidecar"] and w_nosc_leg_key == ["守护缺 sidecar"]
          and w_nosc_missing == ["守护缺 sidecar"], (w_all_leg, l_all_leg, w_nosc_leg, w_nosc_leg_key, w_nosc_missing))
    w_nc, l_nc = _dm([P_, C_], producer_contract="nc_v1")
    w_nc_sc, _ = _dm([P_, S_, C_], producer_contract="nc_v1")
    w_nc_nocombo, _ = _dm([P_], producer_contract="nc_v1")
    check("P5b nc_v1: prod + combo running, sidecar absent ⇒ '守护 2/2', no warning; sidecar running ⇒ warns; combo missing ⇒ '守护缺 combo'",
          w_nc == [] and l_nc == ["守护 2/2"] and len(w_nc_sc) == 1 and "侧车在跑" in w_nc_sc[0] and w_nc_nocombo == ["守护缺 combo"],
          (w_nc, l_nc, w_nc_sc, w_nc_nocombo))
    w_unk, _ = _dm([P_, S_, C_], producer_contract="nc_v2")
    check("P5c unknown producer_contract ⇒ named warning, checked as legacy", len(w_unk) == 1 and "未知值" in w_unk[0], w_unk)
    check("P4 no cell above touched the network (urlopen raises in this process)", True)

shutil.rmtree(TMP, ignore_errors=True)
print(f"\n{N[0] - len(FAILS)}/{N[0]} checks passed")
if FAILS:
    print("FAILED:", *FAILS, sep="\n  ")
    sys.exit(1)
print("ALL PASS")
