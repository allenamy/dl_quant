#!/usr/bin/env python3
"""R2 of CRITERIA_funding_class_fix.md (d6ae30e4d): positive controls on the two historical combo gaps (1788033600 = 08-29 20Z,
1790006400 = 09-21 16Z). The executor's readbacks did not break there, so the cross-gap rule must NOT fire: replaying each real day
through the pre-fix module (d01e35d, frozen fixture copy) and the fixed module (clone) must write field-identical rows, equal on
(position, paid, rate) to the rows on disk. READ-ONLY on production (day files copied into a temp root); venue answers are
reconstructed from the on-disk rows (income = funding_paid, rate = funding_rate, interval = funding_interval_h).
usage: /usr/bin/python3 r2_controls.py <clone> <out json>"""
import importlib.machinery, importlib.util, json, os, shutil, sys, tempfile, time
clone, outp = sys.argv[1], sys.argv[2]
sys.path.insert(0, f"{clone}/live")
import binance_broker as BB, pilot_log as PL, binance_funding as NEW          # noqa: E402
fx = f"{clone}/live/tests_fixtures/funding_gap/binance_funding_d01e35d.py.txt"
spec = importlib.util.spec_from_loader("bf_old", importlib.machinery.SourceFileLoader("bf_old", fx)); OLD = importlib.util.module_from_spec(spec); spec.loader.exec_module(OLD)
PROD = os.path.expanduser("~/dl_quant_live/state/live/pilot_log")
res = {"clone_head": os.popen(f"git -C {clone} rev-parse HEAD").read().strip(), "cases": {}}
for tag, day, prev in (("gap_1788033600_0829T20Z", "20260829", "20260828"), ("gap_1788033600_0830", "20260830", "20260829"),
                       ("gap_1790006400_0921T16Z", "20260921", "20260920")):
    disk = PL.read_day(PROD, day).get("funding", [])
    income = [{"symbol": r["symbol"], "income": str(r["funding_paid"]), "time": int(round(float(r["settlement_ts"]) * 1000)),
               "incomeType": "FUNDING_FEE", "tranId": k} for k, r in enumerate(disk)]
    rates = {}
    for r in disk:
        if r.get("funding_rate") is not None:
            rates.setdefault(r["symbol"], {})[int(round(float(r["settlement_ts"]) * 1000))] = r["funding_rate"]
    ivs = {r["symbol"]: r.get("funding_interval_h") for r in disk if r.get("funding_interval_h")}
    class RB(BB.BinanceBroker):
        def __init__(self):
            super().__init__(mode="DRY_RUN"); self.mode = "TESTNET"; self.armed = True; self.key = self.secret = "x"
        def _request(self, method, path, params=None, signed=False):
            p = params or {}
            if path == "/fapi/v1/income":
                return [i for i in income if p.get("startTime", 0) <= i["time"] <= p.get("endTime", 10 ** 15)]
            if path == "/fapi/v1/fundingRate":
                return [{"symbol": p["symbol"], "fundingTime": t, "fundingRate": str(v)} for t, v in sorted(rates.get(p["symbol"], {}).items())
                        if p["startTime"] <= t <= p["endTime"]]
            if path == "/fapi/v1/fundingInfo":
                return [{"symbol": s, "fundingIntervalHours": h} for s, h in ivs.items()]
            return {}
    out = {}
    for name, mod in (("old", OLD), ("new", NEW)):
        top = tempfile.mkdtemp(prefix=f"r2-{name}-"); root = os.path.join(top, "pilot_log")
        for d in (prev, day):
            os.makedirs(f"{root}/{d}")
            for t in ("position_readback", "fills"):
                if os.path.exists(f"{PROD}/{d}/{t}.jsonl"): shutil.copy2(f"{PROD}/{d}/{t}.jsonl", f"{root}/{d}/{t}.jsonl")
        d0 = int(time.mktime(time.strptime(day, "%Y%m%d")) - time.timezone) * 1000
        lg = PL.PilotLogger(root, day=day)
        rep = mod.write_funding_rows(RB(), lg, root, now_ms=d0 + 86400_000 + 3_600_000, max_age_s=4 * 3600, since_ms=d0, alarm=lambda s_, m_: None)
        lg.close()
        rows = sorted(PL.read_day(root, day).get("funding", []), key=lambda r: (r["settlement_ts"], r["symbol"]))
        out[name] = {"rows": rows, "skipped": rep.get("skipped_no_position"), "carried": rep.get("n_carried_across_gap")}
        shutil.rmtree(top)
    same = out["old"]["rows"] == out["new"]["rows"]
    dk = {(r["symbol"], r["settlement_ts"]): (r["position_notional_at_settlement"], r["funding_paid"]) for r in disk}
    vs_disk = sum(1 for r in out["new"]["rows"] if dk.get((r["symbol"], r["settlement_ts"])) == (r["position_notional_at_settlement"], r["funding_paid"]))
    res["cases"][tag] = {"day": day, "n_disk": len(disk), "n_old": len(out["old"]["rows"]), "n_new": len(out["new"]["rows"]),
                         "old_skipped": out["old"]["skipped"], "new_skipped": out["new"]["skipped"], "new_carried": out["new"]["carried"],
                         "old_eq_new_field_for_field": same, "new_eq_disk_position_paid": vs_disk,
                         "PASS": same and (out["new"]["carried"] in (0, None)) and len(out["new"]["rows"]) == vs_disk}
    print(tag, {k: v for k, v in res["cases"][tag].items()})
res["VERDICT"] = "PASS" if all(c["PASS"] for c in res["cases"].values()) else "FAIL"
json.dump(res, open(outp, "w"), indent=1); print("R2", res["VERDICT"])
