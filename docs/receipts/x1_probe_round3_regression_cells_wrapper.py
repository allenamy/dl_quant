"""X1: run the reviewer's probe main() unchanged and report EVERY recorded cell, including when main() raises
(the probe only prints its summary at the very end). Prints JSON to stdout; writes nothing."""
import json, runpy, sys
probe = sys.argv[1]
g = runpy.run_path(probe, run_name="probe_round3_regression")
out = {"probe": probe}
try:
    g["main"]()
    out["raised"] = None
except BaseException as e:                     # noqa: BLE001 — the regression reports it
    out["raised"] = f"{type(e).__name__}: {e}"
    tb = e.__traceback__
    import traceback as _tbm
    out["raised_at"] = [f"{fs.name}:{fs.lineno}" for fs in _tbm.extract_tb(tb)][-3:]
else:
    tb = None
frame = None
while tb is not None:
    if tb.tb_frame.f_code.co_name == "main":
        frame = tb.tb_frame
    tb = tb.tb_next
if out["raised"] is None:
    res = json.loads(open(probe.rsplit("/", 1)[0] + "/PROBE_RESULTS.json").read())
    checks = res["checks"]
else:
    checks = frame.f_locals.get("checks") if frame is not None else []
out["n_cells_recorded"] = len(checks)
out["cells"] = [{"case": c["case"], "pass": c["pass"]} for c in checks]
print(json.dumps(out, ensure_ascii=False))
