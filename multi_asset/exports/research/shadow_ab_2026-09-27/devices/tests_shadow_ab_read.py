"""Known-answer test of shadow_ab_read.py on a synthetic ledger (100 days; NOKING +30 bps/day, KHALF 0, FUNDONLY -30; one KHALF day
with 7.5 % unknown share). Expect: 97 days after warm-up, KHALF 1 VOID day, verdicts BETTER / NO_DIFFERENCE_RESOLVED / WORSE, and the
health output carrying no mean. exit 0 iff all hold."""
import json, hashlib, subprocess, tempfile, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); rng = np.random.default_rng(1); ok = []
with tempfile.TemporaryDirectory() as t:
    p = os.path.join(t, "l.jsonl"); START = 20000 * 86400; prev = None; out = []
    for k in range(600):
        live = {"net": float(rng.normal(0, 1e-3)), "unpriced_abs_w": 0.0, "funding_unknown_abs_w": 0.0}; arms = {"LIVE_REPLAY": live}
        for arm, eff in (("NOKING", 5e-4), ("KHALF", 0.0), ("FUNDONLY", -5e-4)):
            arms[arm] = {"net": live["net"] + eff + float(rng.normal(0, 2e-4)), "unpriced_abs_w": 0.0, "funding_unknown_abs_w": 0.0}
        if k == 200: arms["KHALF"]["unpriced_abs_w"] = 0.9
        d = json.dumps({"anchor": START + k * 14400, "identity": True, "arms": arms, "prev_line_sha256": prev}, sort_keys=True)
        out.append(d); prev = hashlib.sha256(d.encode()).hexdigest()
    open(p, "w").write("\n".join(out) + "\n")
    R = {}
    for mode in ("health", "dispersion", "final"):
        subprocess.run([sys.executable, "-B", os.path.join(HERE, "shadow_ab_read.py"), p, str(START), mode, os.path.join(t, mode + ".json")], check=True, capture_output=True)
        R[mode] = json.load(open(os.path.join(t, mode + ".json")))
    ok.append(R["health"]["days_after_warm_up"] == 97)
    ok.append(R["health"]["health"]["void_days_per_arm"]["KHALF"] == {"unknown share 0.075 > 5%": 1})
    ok.append("final" not in R["health"] and "dispersion" not in R["health"] and "mean" not in json.dumps(R["dispersion"]))
    ok.append([R["final"]["final"][a]["VERDICT"] for a in ("NOKING", "KHALF", "FUNDONLY")] == ["BETTER", "NO_DIFFERENCE_RESOLVED", "WORSE"])
print("SHADOW_AB_READ_TESTS %d/%d" % (sum(ok), len(ok))); sys.exit(0 if all(ok) else 1)
