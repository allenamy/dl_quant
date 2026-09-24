#!/usr/bin/env python3
"""b7_selftest.py — offline red/green tests of b7_fetch_klines.py and b7_compare.py (no network, no production file). Mac, /usr/bin/python3.
  F1 fetch, fake transport, all 200 with a weight header ⇒ COMPLETE, one log line per request, raw bodies stored unparsed.
  F2 a 429 on the 3rd symbol ⇒ ABORTED_http_429 after exactly 3 requests (no retry).  F2b 418 likewise.
  F3 a weight header 1201 ⇒ ABORTED_weight_1201_above_1200.   F4 a 200 without the weight header ⇒ ABORTED_no_weight_header.
  F5 quiet window closing mid-run (fake status) ⇒ ABORTED_quiet_window_closing.   F6 a 400 for one symbol ⇒ PARTIAL_FAILED_SYMBOLS.
  C1 compare on synthetic klines with known β (y = a + β·x on 4h log returns, β ∈ {0.5, 1.7, −0.4}) ⇒ research β equals the truth
     (≤ 1e-9); a name with a missing kline mid-window keeps n_obs = 180 − 2; a name with no klines is MISSING in layer (i).
  C2 synthetic production records: target_live betas = truth + 0.3 % on one name, anchors row with a consistent m3 record, orders rows
     (skipped rows included) ⇒ closure passes, rel_exec small, layer (i) lists exactly that name over 1 %, verdict PASS with a passing control.
  C3 red: one order row's target_w perturbed ⇒ closure c1 fails ⇒ UNDECIDED "not recomputable".  C4 red: betas_sha256 differs ⇒ UNDECIDED.
  C5 red: production betas +5 % everywhere and the record consistent with them ⇒ rel_exec ≈ 5 % ⇒ FAIL.
usage: /usr/bin/python3 -B b7_selftest.py <tmp_dir>
"""
import gzip, hashlib, importlib, io, json, math, os, shutil, subprocess, sys, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
TMP = os.path.abspath(sys.argv[1]); shutil.rmtree(TMP, ignore_errors=True); os.makedirs(TMP)
FAILS, OUT = [], []
A08, A12, ACTRL, H4 = 1790236800, 1790251200, 1789761600, 14400


def rec(name, ok, **kw):
    OUT.append({"test": name, "ok": bool(ok), **kw}); print(("GREEN " if ok else "RED   ") + name + " " + json.dumps(kw, default=str)[:300], flush=True)
    if not ok: FAILS.append(name)


def betas_sha256(b):
    return hashlib.sha256(json.dumps({k: float(v) for k, v in sorted(b.items())}, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


# ───────────── synthetic market ─────────────
SY = ["AAAUSDT", "BBBUSDT", "BTCUSDT", "CCCUSDT", "DDDUSDT", "EEEUSDT"]
TRUE = {"AAAUSDT": 0.5, "BBBUSDT": 1.7, "CCCUSDT": -0.4, "DDDUSDT": 1.2, "BTCUSDT": 1.0}
START = ACTRL - 181 * H4; OT = np.arange(START, A12 - H4 + 1, H4)
rng = np.random.default_rng(3); xb = rng.normal(0, 0.02, len(OT)); lb = np.cumsum(xb) + math.log(60000)
logs = {"BTCUSDT": lb}
for s, b in TRUE.items():
    if s != "BTCUSDT": logs[s] = np.cumsum(0.0005 + b * xb) + math.log(1.0 + len(s))


def kl_body(s, drop=()):
    rows = []
    for i, ot in enumerate(OT.tolist()):
        if i in drop: continue
        c = math.exp(logs[s][i]); rows.append([ot * 1000, "1", "1", "1", repr(c), "10", (ot + H4) * 1000 - 1, "1", 1, "1", "1", "0"])
    return json.dumps(rows)


BODIES = {s: kl_body(s) for s in TRUE}
BODIES["DDDUSDT"] = kl_body("DDDUSDT", drop=(200,))          # a missing kline inside the A08 / A12 windows
BODIES["EEEUSDT"] = None                                      # no data ⇒ 400 from the fake venue

# ───────────── production inputs (synthetic) ─────────────
INP = os.path.join(TMP, "inputs"); os.makedirs(os.path.join(INP, "target_live"))


def write_target_live(scale_one=None, scale_all=1.0):
    for A in (A08, A12):
        b = {s: (TRUE[s] if s == "BTCUSDT" else TRUE[s] * scale_all) for s in TRUE}
        if scale_one: b[scale_one[0]] = b[scale_one[0]] * scale_one[1]
        b["EEEUSDT"] = 1.0
        n = {s: 180 for s in b}; n["EEEUSDT"] = 0; n["DDDUSDT"] = 178
        json.dump({"anchor_ts": A, "beta_overlay": {"version": "m3_beta_v1", "betas": b, "n_obs": n}}, open(os.path.join(INP, "target_live", f"{A}.json"), "w"))
    return b


def write_ledgers(b, perturb=False, bad_sha=False):
    T = {"AAAUSDT": 3000.0, "BBBUSDT": -2500.0, "CCCUSDT": 1500.0, "DDDUSDT": -2000.0, "BTCUSDT": 0.0}
    G = sum(abs(v) for v in T.values()); be = sum(T[s] * b[s] for s in sorted(T) if T[s] != 0.0)
    arows, orows = [], []
    for A in (A08, A12):
        ats = A + 1444.25
        arows.append({"anchor_ts": ats, "weights": {"x": 1}, "m3_beta_overlay": {"mode": "shadow", "field_ok": True, "beta_exec_usdt": be, "book_gross_usdt": G,
                      "sizing_gross_usdt": G, "n_targeted_names": 4, "betas_sha256": (betas_sha256(b) if not bad_sha else "0" * 64)}})
        for s, v in T.items():
            w = v / G
            if perturb and s == "AAAUSDT": w *= 1.01
            orows.append({"anchor_ts": ats, "symbol": s, "target_w": w, "attempt_idx": 1, "placement_arm": "HIDDEN"})
            if v != 0.0: orows.append({"anchor_ts": ats, "symbol": s, "target_w": w, "attempt_idx": 2})
    with open(os.path.join(INP, "anchors_20260924.jsonl"), "w") as f:
        for r in arows: f.write(json.dumps(r) + "\n")
    with open(os.path.join(INP, "orders_20260924.jsonl"), "w") as f:
        for r in orows: f.write(json.dumps(r) + "\n")
    return be


# ───────────── fake transport + fake quiet window for the fetch device ─────────────
class FakeResp(io.BytesIO):
    def __init__(self, body, status, headers): super().__init__(body); self.status = status; self.headers = headers
    def __enter__(self): return self
    def __exit__(self, *a): return False


def run_fetch(tag, plan, window=None):
    import urllib.request, urllib.error
    F = importlib.import_module("b7_fetch_klines"); importlib.reload(F)
    calls = []
    st_open = {"open": True, "remaining_min": 100.0, "reason": "open", "override": None}

    def fake_urlopen(req, timeout=None):
        s = req.full_url.split("symbol=")[1].split("&")[0]; calls.append(s); k = len(calls)
        status, wt = plan(k, s)
        hdr = {} if wt is None else {"X-MBX-USED-WEIGHT-1M": str(wt)}
        body = (BODIES.get(s) or '{"code":-1121,"msg":"Invalid symbol."}').encode()
        if status != 200:
            class H(dict):
                def get(self, k, d=None): return dict.get(self, k, d)
            raise urllib.error.HTTPError(req.full_url, status, "x", H(hdr), io.BytesIO(body))
        return FakeResp(body, 200, hdr)
    F.urllib.request.urlopen = fake_urlopen
    F.VQW.require_quiet_window = lambda min_remaining_min=20: dict(st_open)
    F.VQW.quiet_window_status = (lambda: dict(st_open)) if window is None else window(calls)
    F.PACE_S = 0.0
    out = os.path.join(TMP, "fetch_" + tag); sys.argv = ["b7_fetch_klines.py", INP, out]
    try:
        F.main(); rc = 0
    except SystemExit as e:
        rc = e.code
    man = json.load(open(os.path.join(out, "FETCH_MANIFEST.json")))
    nlog = sum(1 for _ in open(os.path.join(out, "FETCH_LOG.jsonl")))
    return man, calls, nlog, rc, out


b_true = write_target_live(); write_ledgers(b_true)
man, calls, nlog, rc, fd_ok = run_fetch("ok", lambda k, s: ((400 if s == "EEEUSDT" else 200), 12 * k))
rec("F6.one_400_symbol_partial_and_named", man["verdict"] == "PARTIAL_FAILED_SYMBOLS" and man["failed"] == ["EEEUSDT"] and nlog == len(calls) == 6, verdict=man["verdict"], n=len(calls))
BODIES["EEEUSDT"] = None
man2, calls2, n2, _, _ = run_fetch("429", lambda k, s: ((429 if k == 3 else 200), 10))
rec("F2.http_429_aborts_no_retry", man2["verdict"] == "ABORTED_http_429" and len(calls2) == 3 and n2 == 3, verdict=man2["verdict"], calls=len(calls2))
man2b, calls2b, _, _, _ = run_fetch("418", lambda k, s: ((418 if k == 2 else 200), 10))
rec("F2b.http_418_aborts_no_retry", man2b["verdict"] == "ABORTED_http_418" and len(calls2b) == 2, verdict=man2b["verdict"])
man3, calls3, _, _, _ = run_fetch("w", lambda k, s: (200, 1201 if k == 2 else 10))
rec("F3.weight_over_1200_aborts", man3["verdict"].startswith("ABORTED_weight_1201") and len(calls3) == 2, verdict=man3["verdict"])
man4, calls4, _, _, _ = run_fetch("nohdr", lambda k, s: (200, None if k == 4 else 10))
rec("F4.missing_weight_header_aborts", man4["verdict"] == "ABORTED_no_weight_header" and len(calls4) == 4, verdict=man4["verdict"])
man5, calls5, _, _, _ = run_fetch("qw", lambda k, s: (200, 10), window=lambda calls: (lambda: {"open": len(calls) < 2, "remaining_min": 50.0 if len(calls) < 2 else 3.0, "reason": "closing", "override": None}))
rec("F5.quiet_window_closing_aborts", man5["verdict"].startswith("ABORTED_quiet_window_closing") and len(calls5) == 2, verdict=man5["verdict"])
man1, calls1, n1, rc1, fd1 = run_fetch("all200", lambda k, s: ((400 if s == "EEEUSDT" else 200), 5))
rec("F1.log_one_line_per_request_and_raw_bodies", n1 == len(calls1) and man1["n_ok"] == 5, n_log=n1, n_ok=man1["n_ok"])

# ───────────── control npz (synthetic certified β = truth, EEE absent) ─────────────
cs = ["AAAUSDT", "BBBUSDT", "BTCUSDT", "CCCUSDT", "DDDUSDT"]
cb = np.array([TRUE[s] for s in cs]); ce = np.array([s != "BTCUSDT" for s in cs])
ctrl = os.path.join(TMP, "ctrl.npz")


def compare(tag, fd=fd_ok):
    out = os.path.join(TMP, "cmp_" + tag)
    p = subprocess.run([sys.executable, "-B", os.path.join(HERE, "b7_compare.py"), INP, fd, ctrl, out], capture_output=True, text=True)
    return p.returncode, (json.load(open(os.path.join(out, "B7_PARITY.json"))) if os.path.exists(os.path.join(out, "B7_PARITY.json")) else None), p.stdout[-600:] + p.stderr[-600:]


# the control in the synthetic world: β from the same klines ⇒ ≥ 100 names cannot be met with 4 names ⇒ extend by replicas
reps = {}
for r in range(40):
    for s in ("AAAUSDT", "BBBUSDT", "CCCUSDT", "DDDUSDT"):
        n = f"R{r:02d}{s}"; reps[n] = s; logs[n] = logs[s]; TRUE[n] = TRUE[s]; BODIES[n] = kl_body(s)
cs = cs + sorted(reps); cb = np.array([TRUE[s] for s in cs]); ce = np.array([s != "BTCUSDT" for s in cs])
np.savez(ctrl, symbols=np.array(cs), beta=cb, est=ce, ua_in_window=np.array([s.endswith("DDDUSDT") for s in cs]), nobs=np.full(len(cs), 180))
b_true = write_target_live()
for A in (A08, A12):                                           # replicas also in the production name list
    p = os.path.join(INP, "target_live", f"{A}.json"); d = json.load(open(p))
    for n in reps: d["beta_overlay"]["betas"][n] = TRUE[n]; d["beta_overlay"]["n_obs"][n] = 180
    json.dump(d, open(p, "w"))
man1, _, _, _, fd1 = run_fetch("all200_reps", lambda k, s: ((400 if s == "EEEUSDT" else 200), 5))


def set_prod(scale_one=None, scale_all=1.0, perturb=False, bad_sha=False):
    b = write_target_live(scale_one, scale_all)
    for A in (A08, A12):
        p = os.path.join(INP, "target_live", f"{A}.json"); d = json.load(open(p))
        for n in reps: d["beta_overlay"]["betas"][n] = TRUE[n] * scale_all; d["beta_overlay"]["n_obs"][n] = 180
        json.dump(d, open(p, "w")); b = d["beta_overlay"]["betas"]
    return write_ledgers(b, perturb, bad_sha)


set_prod(scale_one=("BBBUSDT", 1.003))
rc, R, log = compare("green", fd1)
ok = R is not None
if ok:
    li = R["per_anchor"]["A08"]["layer_i"]; lii = R["per_anchor"]["A08"]["layer_ii"]
    rec("C1.research_beta_equals_truth_and_control_passes", R["positive_control"]["pass"] and R["positive_control"]["max_abs_dbeta_clean"] <= 1e-9, ctrl=R["positive_control"])
    rec("C1b.missing_name_is_MISSING_not_1", li["classes"].get("MISSING") == 1, classes=li["classes"])
    rec("C2.closure_and_pass", R["VERDICT"] == "PASS" and lii["closure"]["c1_sum_abs_w_is_1"] and lii["closure"]["c3_recon_with_prod_betas_equals_record"] and lii["rel_exec"] < 0.01 and rc == 0,
        verdict=R["VERDICT"], rel=lii.get("rel_exec"), closure=lii.get("closure"))
    rec("C2b.layer_i_lists_the_one_name_over_1pct", li["n_rel_over_1pct"] == 0 and li["rel"]["max"] > 0.0029, n_over=li["n_rel_over_1pct"], rel=li["rel"])
else:
    rec("C1.compare_ran", False, log=log)
set_prod(scale_one=("BBBUSDT", 1.02))
rc, R, log = compare("one_over", fd1)
rec("C2c.a_2pct_name_is_listed", R is not None and R["per_anchor"]["A12"]["layer_i"]["n_rel_over_1pct"] == 1 and R["per_anchor"]["A12"]["layer_i"]["rel_over_1pct"][0]["symbol"] == "BBBUSDT",
    n=R and R["per_anchor"]["A12"]["layer_i"]["n_rel_over_1pct"])
set_prod(perturb=True)
rc, R, log = compare("perturb", fd1)
rec("C3.perturbed_target_w_not_recomputable", R is not None and R["VERDICT"] == "UNDECIDED" and "closure" in R["per_anchor"]["A08"]["layer_ii"]["undecided"] and rc == 1,
    verdict=R and R["VERDICT"])
set_prod(bad_sha=True)
rc, R, log = compare("badsha", fd1)
rec("C4.betas_sha_mismatch_undecided", R is not None and R["VERDICT"] == "UNDECIDED", verdict=R and R["VERDICT"])
set_prod(scale_all=1.05)
rc, R, log = compare("five_pct", fd1)
rec("C5.five_pct_prod_betas_fail", R is not None and R["VERDICT"] == "FAIL" and abs(R["per_anchor"]["A08"]["layer_ii"]["rel_exec"] - 0.05 / 1.05) < 1e-6,
    verdict=R and R["VERDICT"], rel=R and R["per_anchor"]["A08"]["layer_ii"].get("rel_exec"))
json.dump({"tests": OUT, "red": FAILS}, open(os.path.join(TMP, "B7_SELFTEST.json"), "w"), indent=1, default=str)
print(f"B7_SELFTEST VERDICT={'ALL GREEN' if not FAILS else 'RED'} tests={len(OUT)} red={len(FAILS)}", flush=True)
sys.exit(0 if not FAILS else 1)
