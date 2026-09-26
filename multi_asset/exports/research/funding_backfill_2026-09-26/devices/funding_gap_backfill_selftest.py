#!/usr/bin/env python3
"""funding_gap_backfill_selftest.py -- positive and red controls for funding_gap_backfill.py on a SANDBOX copy of the executor's
pilot_log days (the live tree is only imported and read; nothing under ~/dl_quant_live is written). No network: the venue answers
are synthesised or, for the positive control, reconstructed from rows the executor itself wrote.

  P1 CONSTRUCTOR IDENTITY: the 12:00Z settlements the executor wrote at 20:46Z are removed from the sandbox, their venue answers
     reconstructed from those rows (income = funding_paid, rate, interval), and re-planned through the device with the normal
     4 h rule: the planned rows must EQUAL the executor's own rows, field for field.
  P2 baseline gap backfill on synthetic gap income: census -> plan -> apply -> verify VERIFIED; every planned key once.
  R1 a name whose position changed inside the gap (a stray fill; a post-gap readback qty moved) is EXCLUDED and named.
  R2 a target row that already exists is skipped at plan; a second apply against the grown file STOPs; re-plan gives 0 rows.
  R3 schema: planned rows whose key set differs from the executor's rows STOP the plan; a tampered plan is refused (sha) and a
     re-pinned tampered row is refused by the executor's own validate().
  R4 the target changed between plan and apply -> STOP.
  R5 rollback restores the file bitwise; rollback refuses when bytes were appended after the backfill.
usage: funding_gap_backfill_selftest.py <scratch> <out.json>
"""
import copy, hashlib, importlib.util, json, os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__)); DEV = os.path.join(HERE, "funding_gap_backfill.py")
LIVE = os.path.expanduser("~/dl_quant_live/state/live")
DAY, PREV = "20260926", "20260925"
spec = importlib.util.spec_from_file_location("fgb", DEV); FGB = importlib.util.module_from_spec(spec); spec.loader.exec_module(FGB)
RES = []


def check(name, ok, detail=""):
    RES.append({"control": name, "pass": bool(ok), "detail": str(detail)[:300]}); print(f"  [{'PASS' if ok else 'FAIL'}] {name}  {str(detail)[:160]}")


def sandbox(base, tag):
    d = tempfile.mkdtemp(prefix=f"fgb_{tag}_", dir=base); root = os.path.join(d, "pilot_log")
    for day in (PREV, DAY): shutil.copytree(os.path.join(LIVE, "pilot_log", day), os.path.join(root, day))
    shutil.copy2(os.path.join(LIVE, "exchange_info_cache.json"), os.path.join(d, "exchange_info_cache.json"))
    return d, root


def run(*args):
    p = subprocess.run([sys.executable, "-B", DEV, *args], capture_output=True, text=True, env=dict(os.environ))
    return p.returncode, (p.stdout + p.stderr)


def rows(root, day, table="funding"):
    return [json.loads(l) for l in open(os.path.join(root, day, f"{table}.jsonl")) if l.strip()]


def rewrite(root, day, table, rs):
    with open(os.path.join(root, day, f"{table}.jsonl"), "w") as f:
        for r in rs: f.write(json.dumps(r, default=str) + "\n")


def synth_raw(cen, root):
    """Synthetic gap income for every name held before the gap: one settlement at 16:00Z and one at 20:00Z (+3 ms)."""
    held = [s for s, v in cen["names"].items() if abs(v["qty_pre_gap"]) > 0][:40]
    inc, rates = [], {}
    for k, s in enumerate(held):
        for t in (1790438400003, 1790452800003):
            inc.append({"symbol": s, "incomeType": "FUNDING_FEE", "income": f"{-0.01 * (k + 1):.8f}", "time": t, "tranId": t + k})
        rates[s] = [{"fundingTime": 1790438400000, "fundingRate": "0.0001"}, {"fundingTime": 1790452800000, "fundingRate": "0.0001"}]
    return {"window_ms": cen["gap_window_ms"], "income": inc, "rates": rates, "intervals": {s: 4 for s in held}}


def main():
    base, outp = sys.argv[1], sys.argv[2]; os.makedirs(base, exist_ok=True)
    ex = json.load(open(os.path.join(LIVE, "exchange_info_cache.json")))
    # ---------------- P1 constructor identity on the executor's own 12:00Z rows
    d, root = sandbox(base, "P1")
    allr = rows(root, DAY); t12 = [r for r in allr if abs(float(r["settlement_ts"]) - 1790424000) < 60]
    rewrite(root, DAY, "funding", [r for r in allr if r not in t12])
    raw = {"window_ms": [1790423999000, 1790424059000],
           "income": [{"symbol": r["symbol"], "incomeType": "FUNDING_FEE", "income": repr(float(r["funding_paid"])),
                       "time": int(round(float(r["settlement_ts"]) * 1000)), "tranId": i} for i, r in enumerate(t12)],
           "rates": {r["symbol"]: ([{"fundingTime": int(round(float(r["settlement_ts"]) * 1000)), "fundingRate": repr(float(r["funding_rate"]))}]
                                   if r["funding_rate"] is not None else []) for r in t12},
           "intervals": {r["symbol"]: r["funding_interval_h"] for r in t12 if r["funding_interval_h"]}}
    cen = {"day": DAY, "gap_window_ms": raw["window_ms"], "max_age_s_needed": 4 * 3600 - 1.0, "excluded": {}, "names": {}}
    P = FGB.plan(root, cen, raw, os.path.join(d, "plan"), DAY)
    key = lambda r: (r["symbol"], int(round(float(r["settlement_ts"]) * 1000)))
    orig = {key(r): r for r in t12}; got = {key(r): r for r in P["rows"]}
    diff = [k for k in orig if json.dumps(orig[k], sort_keys=True, default=str) != json.dumps(got.get(k), sort_keys=True, default=str)]
    check("P1 constructor identity: re-planned 12:00Z rows == the executor's own rows, field for field",
          len(t12) > 100 and len(got) == len(orig) and not diff, f"n={len(t12)} differ={len(diff)} {diff[:2]}")
    # ---------------- P2 baseline
    d, root = sandbox(base, "P2")
    cen = FGB.census(root, DAY, ex); raw = synth_raw(cen, root)
    rawp = os.path.join(d, "raw.json"); FGB.write_json(rawp, raw); cenp = os.path.join(d, "census.json"); FGB.write_json(cenp, cen)
    rc, o = run("plan", "--root", root, "--census", cenp, "--raw", rawp, "--out", os.path.join(d, "plan"))
    psha = FGB.sha(os.path.join(d, "plan", "PLAN.json")) if rc == 0 else ""
    rc2, o2 = run("apply", "--root", root, "--plan", os.path.join(d, "plan"), "--plan-sha", psha, "--stamp", "T1")
    rcpt = os.path.join(d, "plan", "APPLY_T1.json")
    rc3, o3 = run("verify", "--root", root, "--apply-receipt", rcpt)
    check("P0 census on the unmodified day: every name equal, 0 excluded (the supersede rows are collapsed, not double counted)",
          cen["n_equal"] == cen["n_names"] and not cen["excluded"] and cen["fills_outside_post_gap_rebalance"] == 0,
          f"names {cen['n_names']} equal {cen['n_equal']} fills {cen['fills_between_readbacks']}")
    check("P2 baseline: census -> plan -> apply -> verify VERIFIED", rc == 0 and rc2 == 0 and rc3 == 0 and "VERIFIED" in o3,
          f"census gap {cen['readback_before_gap']['utc']}->{cen['readback_after_gap']['utc']} fills {cen['fills_between_readbacks']} {o.strip()[-120:]} | {o3.strip()[-80:]}")
    # ---------------- R5 rollback (on the P2 sandbox)
    rc5, o5 = run("rollback", "--root", root, "--apply-receipt", rcpt)
    check("R5a rollback restores the pre-apply bytes", rc5 == 0 and '"rolled_back": true' in o5, o5.strip()[-120:])
    rc2b, _ = run("apply", "--root", root, "--plan", os.path.join(d, "plan"), "--plan-sha", psha, "--stamp", "T2")
    with open(os.path.join(root, DAY, "funding.jsonl"), "a") as f: f.write(json.dumps({"x": 1}) + "\n")
    rc5b, o5b = run("rollback", "--root", root, "--apply-receipt", os.path.join(d, "plan", "APPLY_T2.json"))
    check("R5b rollback refuses when bytes were appended after the backfill", rc2b == 0 and rc5b != 0 and "appended after" in o5b, o5b.strip()[-120:])
    # ---------------- R1 position changed
    d, root = sandbox(base, "R1")
    fl = rows(root, DAY, "fills"); c0 = FGB.census(root, DAY, ex)
    held = [s for s, v in c0["names"].items() if abs(v["qty_pre_gap"]) > 0]
    x, y = held[0], held[1]
    f0 = copy.deepcopy(next(f for f in fl if f["symbol"] == x)); f0.update(fill_ts=1790434800.0, rebalance_id="STRAY", trade_id=999999991)
    rewrite(root, DAY, "fills", fl + [f0])
    rb = rows(root, DAY, "position_readback")
    for r in rb:
        if r["symbol"] == y and abs(float(r["read_ts"]) - c0["readback_after_gap"]["read_ts"]) < 1e-6:
            r["venue_position_qty"] = float(r["venue_position_qty"]) * 1.5 + 1.0
    rewrite(root, DAY, "position_readback", rb)
    c1 = FGB.census(root, DAY, ex); raw = synth_raw(c0, root)
    P = FGB.plan(root, c1, raw, os.path.join(d, "plan"), DAY)
    pl_syms = {r["symbol"] for r in P["rows"]}
    check("R1 position changed in the gap -> that name EXCLUDED and named (stray fill; post-gap qty moved)",
          x in c1["excluded"] and y in c1["excluded"] and x not in pl_syms and y not in pl_syms and x in P["excluded_symbols"],
          {x: c1["excluded"].get(x), y: c1["excluded"].get(y)})
    # ---------------- R2 target row exists + second apply + re-plan
    d, root = sandbox(base, "R2")
    cen = FGB.census(root, DAY, ex); raw = synth_raw(cen, root); z = raw["income"][0]
    pre = rows(root, DAY)[0]; pre2 = dict(pre, symbol=z["symbol"], settlement_ts=z["time"] / 1000.0)
    with open(os.path.join(root, DAY, "funding.jsonl"), "a") as f: f.write(json.dumps(pre2) + "\n")
    rawp = os.path.join(d, "raw.json"); FGB.write_json(rawp, raw); cenp = os.path.join(d, "census.json"); FGB.write_json(cenp, cen)
    run("plan", "--root", root, "--census", cenp, "--raw", rawp, "--out", os.path.join(d, "plan"))
    P = json.load(open(os.path.join(d, "plan", "PLAN.json"))); psha = FGB.sha(os.path.join(d, "plan", "PLAN.json"))
    ra, _ = run("apply", "--root", root, "--plan", os.path.join(d, "plan"), "--plan-sha", psha, "--stamp", "A1")
    rb2, ob2 = run("apply", "--root", root, "--plan", os.path.join(d, "plan"), "--plan-sha", psha, "--stamp", "A2")
    run("plan", "--root", root, "--census", cenp, "--raw", rawp, "--out", os.path.join(d, "plan2"))
    P2 = json.load(open(os.path.join(d, "plan2", "PLAN.json")))
    check("R2 existing row skipped at plan; second apply STOPs (target changed); re-plan plans 0 rows",
          P["n_already_present_skipped"] == 1 and ra == 0 and rb2 != 0 and "changed since the plan" in ob2 and P2["n_rows_planned"] == 0,
          f"present={P['n_already_present_skipped']} replan_rows={P2['n_rows_planned']}")
    # ---------------- R3 schema
    d, root = sandbox(base, "R3")
    cen = FGB.census(root, DAY, ex); raw = synth_raw(cen, root)
    rewrite(root, DAY, "funding", [dict(r, extra_field_from_a_newer_executor=1) for r in rows(root, DAY)])
    rawp = os.path.join(d, "raw.json"); FGB.write_json(rawp, raw); cenp = os.path.join(d, "census.json"); FGB.write_json(cenp, cen)
    r3a, o3a = run("plan", "--root", root, "--census", cenp, "--raw", rawp, "--out", os.path.join(d, "plan"))
    d, root = sandbox(base, "R3b")
    cen = FGB.census(root, DAY, ex); rawp = os.path.join(d, "raw.json"); FGB.write_json(rawp, synth_raw(cen, root)); cenp = os.path.join(d, "census.json"); FGB.write_json(cenp, cen)
    run("plan", "--root", root, "--census", cenp, "--raw", rawp, "--out", os.path.join(d, "plan"))
    pp = os.path.join(d, "plan", "PLAN.json"); P = json.load(open(pp)); good_sha = FGB.sha(pp)
    P["rows"][0].pop("funding_paid"); FGB.write_json(pp, P)
    r3b, o3b = run("apply", "--root", root, "--plan", os.path.join(d, "plan"), "--plan-sha", good_sha, "--stamp", "S1")
    r3c, o3c = run("apply", "--root", root, "--plan", os.path.join(d, "plan"), "--plan-sha", FGB.sha(pp), "--stamp", "S2")
    check("R3 schema: key set != executor rows STOPs the plan; tampered plan refused by sha; re-pinned tampered row refused by validate()",
          r3a != 0 and "key set" in o3a and r3b != 0 and "not the pinned plan" in o3b and r3c != 0 and "SchemaError" in o3c,
          f"{o3a.strip()[-80:]} | {o3c.strip()[-80:]}")
    # ---------------- R4 target changed between plan and apply
    d, root = sandbox(base, "R4")
    cen = FGB.census(root, DAY, ex); rawp = os.path.join(d, "raw.json"); FGB.write_json(rawp, synth_raw(cen, root)); cenp = os.path.join(d, "census.json"); FGB.write_json(cenp, cen)
    run("plan", "--root", root, "--census", cenp, "--raw", rawp, "--out", os.path.join(d, "plan"))
    psha = FGB.sha(os.path.join(d, "plan", "PLAN.json"))
    with open(os.path.join(root, DAY, "funding.jsonl"), "a") as f: f.write(json.dumps(rows(root, DAY)[0]) + "\n")
    r4, o4 = run("apply", "--root", root, "--plan", os.path.join(d, "plan"), "--plan-sha", psha, "--stamp", "C1")
    check("R4 target changed between plan and apply -> STOP", r4 != 0 and "changed since the plan" in o4, o4.strip()[-100:])
    ok = all(r["pass"] for r in RES)
    json.dump({"device_sha256": FGB.sha(DEV), "selftest_sha256": FGB.sha(os.path.abspath(__file__)), "controls": RES, "all_pass": ok,
               "note": "sandbox copies of pilot_log/20260925-26; the live tree is imported read-only; no network"}, open(outp, "w"), indent=1)
    print(f"\nFGB_SELFTEST {sum(r['pass'] for r in RES)}/{len(RES)} {'ALL GREEN' if ok else 'RED'}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
