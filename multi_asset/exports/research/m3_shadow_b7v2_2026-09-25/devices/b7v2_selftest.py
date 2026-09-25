#!/usr/bin/env python3
"""b7v2_selftest.py — offline self-test of b7v2_fetch.py (fake transport, fake quiet window, fake clock) and b7v2_compare.py (a synthetic
market with known betas). No network, no production file is read. Baseline cells must be GREEN first; every red cell must be caught.
Mac, /usr/bin/python3 + numpy. usage: /usr/bin/python3 -B b7v2_selftest.py <scratch_dir>
Last line: B7V2_SELFTEST VERDICT=ALL GREEN|RED tests=<n> red=<k>
"""
import copy, gzip, hashlib, importlib, io, json, os, shutil, sys, urllib.error
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import b7v2_fetch as FX
import b7v2_compare as CX

H4 = 14400; A = 1790323200; DAY = "20260925"; NN = 40
RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok))); print(f"{'PASS' if ok else 'FAIL'} {name} {detail}", flush=True)


def sha(b): return hashlib.sha256(b).hexdigest()


# ---------------- synthetic market ----------------
rng = np.random.default_rng(20260925)
names = ["BTCUSDT"] + [f"X{i:02d}USDT" for i in range(NN)]
beta_true = {"BTCUSDT": 1.0}; beta_true.update({n: float(rng.uniform(-0.5, 2.5)) for n in names[1:]}); beta_true["X00USDT"] = 1.5; beta_true["X01USDT"] = 2.0
bt = rng.normal(0, 0.02, 181)
closes = {}
for n in names:
    r = bt if n == "BTCUSDT" else beta_true[n] * bt + rng.normal(0, 0.02, 181)
    lp = np.concatenate([[np.log(10.0 + names.index(n))], np.log(10.0 + names.index(n)) + np.cumsum(r)])
    closes[n] = np.exp(lp)                                                    # 182 closes at A−181·4h … A (first one unused by the window)


def kl_body(n, drop=()):
    rows = []
    for i in range(181):                                                        # open A−181·4h+i·4h, close at A−180·4h+i·4h
        ot = A - 181 * H4 + i * H4
        if i in drop: continue
        c = closes[n][i + 1]
        rows.append([ot * 1000, "1", "1", "1", repr(float(c)), "1", (ot + H4) * 1000 - 1, "1", 1, "1", "1", "0"])
    return json.dumps(rows)


# ---------------- fake venue ----------------
class Resp:
    def __init__(self, status, body, wt): self.status = status; self._b = body.encode() if isinstance(body, str) else body; self.headers = {} if wt is None else {"X-MBX-USED-WEIGHT-1M": str(wt)}
    def read(self): return self._b
    def __enter__(self): return self
    def __exit__(self, *a): return False


class Venue:
    def __init__(self, weights=None, fail=None, status=None, missing_header=None, http=None):
        self.n = 0; self.weights = weights or {}; self.fail = fail or {}; self.status = status or {}; self.missing = missing_header or set(); self.http = http or {}; self.urls = []
    def __call__(self, req, timeout=20):
        url = req.full_url; self.urls.append(url); i = self.n; self.n += 1
        wt = None if i in self.missing else self.weights.get(i, 10 + i)
        if i in self.http:
            raise urllib.error.HTTPError(url, self.http[i], "x", {"X-MBX-USED-WEIGHT-1M": str(wt)}, io.BytesIO(b"{}"))
        if i in self.fail: return Resp(self.fail[i], "{}", wt)
        if "exchangeInfo" in url:
            syms = [{"symbol": n, "status": self.status.get(n, "TRADING"), "contractType": "PERPETUAL", "deliveryDate": 4133404800000} for n in names]
            return Resp(200, json.dumps({"serverTime": A * 1000 + 3600000, "symbols": syms}), wt)
        s = url.split("symbol=")[1].split("&")[0]
        return Resp(200, kl_body(s), wt)


class Clock:
    def __init__(self): self.t = A + 3900.0; self.sleeps = []
    def now(self): return self.t
    def sleep(self, s): self.sleeps.append(s); self.t += max(0.0, s)


def vqw(open_=True, remaining=100.0, closing_after=None):
    st = {"n": 0}
    def status():
        st["n"] += 1
        rem = remaining if (closing_after is None or st["n"] <= closing_after) else 3.0
        return {"open": open_, "remaining_min": rem, "reason": None if open_ else "closed"}
    def require(min_remaining_min=20):
        if not open_: raise SystemExit("quiet window closed (fake)")
        return {"open": True, "remaining_min": remaining}
    return status, require


def run_fetch(sd, venue, n_names=None, open_=True, closing_after=None, env_override=False):
    importlib.reload(FX); ck = Clock(); FX._urlopen = venue; FX._sleep = ck.sleep; FX._now = ck.now
    FX.VQW.quiet_window_status, FX.VQW.require_quiet_window = vqw(open_, 100.0, closing_after)
    inp = os.path.join(sd, "in"); os.makedirs(os.path.join(inp, "target_live"), exist_ok=True)
    nm = names if n_names is None else ["BTCUSDT"] + [f"Z{i:03d}USDT" for i in range(n_names - 1)]
    json.dump({"beta_overlay": {"version": "m3_beta_v2", "betas": {n: 1.0 for n in nm}, "n_obs": {n: 180 for n in nm}}}, open(os.path.join(inp, "target_live", f"{A}.json"), "w"))
    out = os.path.join(sd, "fetch")
    if env_override: os.environ["VENUE_QUIET_WINDOW_OVERRIDE"] = "test"
    try:
        rc = FX.main(["x", inp, str(A), out]); exc = None
    except SystemExit as e:
        rc, exc = None, str(e)
    finally:
        os.environ.pop("VENUE_QUIET_WINDOW_OVERRIDE", None)
    man = json.load(open(os.path.join(out, "FETCH_MANIFEST.json"))) if (exc is None and os.path.isfile(os.path.join(out, "FETCH_MANIFEST.json"))) else None
    return rc, exc, man, ck, out


def fresh(sd):
    if os.path.isdir(sd): shutil.rmtree(sd)
    os.makedirs(sd)


def main():
    root = os.path.abspath(sys.argv[1]); os.makedirs(root, exist_ok=True)
    # ======== fetch ========
    sd = os.path.join(root, "F1"); fresh(sd); v = Venue(); rc, exc, man, ck, fout = run_fetch(sd, v)
    check("F1 BASELINE normal pull → COMPLETE, n+1 requests, exinfo subset written", rc == 0 and man["verdict"] == "COMPLETE" and man["n_requests"] == len(names) + 1
          and os.path.isfile(os.path.join(fout, "EXINFO_SUBSET.json")) and "exchangeInfo" in v.urls[0], f"rc={rc} verdict={man and man['verdict']}")
    check("F1b pacing ≥ 0.5 s between requests (fake clock)", all(s <= 0.5 + 1e-9 for s in ck.sleeps) and len(ck.sleeps) >= len(names) - 1)
    sd = os.path.join(root, "F2"); fresh(sd); v = Venue(http={4: 429}); rc, exc, man, ck, _ = run_fetch(sd, v)
    check("F2 RED 429 → ABORTED_http_429, no further request", man["verdict"] == "ABORTED_http_429" and v.n == 5 and rc == 2, f"n={v.n}")
    sd = os.path.join(root, "F3"); fresh(sd); v = Venue(http={3: 418}); rc, exc, man, ck, _ = run_fetch(sd, v)
    check("F3 RED 418 → ABORTED_http_418", man["verdict"] == "ABORTED_http_418" and v.n == 4)
    sd = os.path.join(root, "F4"); fresh(sd); v = Venue(missing_header={2}); rc, exc, man, ck, _ = run_fetch(sd, v)
    check("F4 RED response without weight header → ABORT", man["verdict"] == "ABORTED_no_or_bad_weight_header" and v.n == 3)
    sd = os.path.join(root, "F5"); fresh(sd); v = Venue(weights={3: 301}); rc, exc, man, ck, _ = run_fetch(sd, v)
    check("F5 RED weight 301 > 300 → ABORT", man["verdict"] == "ABORTED_weight_301_above_300" and v.n == 4 and man["max_used_weight_1m"] == 301)
    sd = os.path.join(root, "F6"); fresh(sd); v = Venue(weights={3: 250}); rc, exc, man, ck, _ = run_fetch(sd, v)
    big = [s for s in ck.sleeps if s > 1.0]
    check("F6 soft brake at 250 → sleeps to next minute + 2 s, continues, COMPLETE", man["verdict"] == "COMPLETE" and man["n_soft_brakes"] == 1 and len(big) == 1 and 2.0 <= big[0] <= 62.0, f"big={big}")
    sd = os.path.join(root, "F7"); fresh(sd); v = Venue(); rc, exc, man, ck, _ = run_fetch(sd, v, n_names=500)
    check("F7 RED 500 names ⇒ 501 requests > envelope → refused before any request", exc is not None and "envelope" in exc and v.n == 0, exc)
    sd = os.path.join(root, "F8"); fresh(sd); v = Venue(); rc, exc, man, ck, _ = run_fetch(sd, v, open_=False)
    check("F8 RED quiet window closed at start → refused, no request", exc is not None and v.n == 0, exc)
    sd = os.path.join(root, "F9"); fresh(sd); v = Venue(); rc, exc, man, ck, _ = run_fetch(sd, v, closing_after=6)
    check("F9 RED window closing mid-run → ABORTED_quiet_window_closing", man["verdict"].startswith("ABORTED_quiet_window_closing") and v.n == 6, f"n={v.n}")
    sd = os.path.join(root, "F10"); fresh(sd); v = Venue(fail={7: 500}); rc, exc, man, ck, _ = run_fetch(sd, v)
    check("F10 RED one symbol HTTP 500 → PARTIAL_FAILED_SYMBOLS (named)", man["verdict"] == "PARTIAL_FAILED_SYMBOLS" and man["n_failed"] == 1 and rc == 2)
    sd = os.path.join(root, "F11"); fresh(sd); v = Venue(); rc, exc, man, ck, _ = run_fetch(sd, v, env_override=True)
    check("F11 RED VENUE_QUIET_WINDOW_OVERRIDE set → refused", exc is not None and "OVERRIDE" in exc and v.n == 0, exc)

    # ======== compare: build the green production side on the F1 fetch ========
    base = os.path.join(root, "C_base"); fresh(base); shutil.copytree(os.path.join(root, "F1", "fetch"), os.path.join(base, "fetch"))
    kl = {}
    with gzip.open(os.path.join(base, "fetch", "KLINES_RAW.jsonl.gz"), "rt") as f:
        for ln in f: d = json.loads(ln); kl[d["symbol"]] = json.loads(d["body"])
    res, _ = CX.research_betas(kl, A)
    check("C0 research β recovers the synthetic truth (sanity of the fixture, |β̂ − β| < 0.4 ≈ 5 se on all)", all(abs(res[n][0] - beta_true[n]) < 0.4 for n in names))
    bp = {n: res[n][0] + (1e-5 if n != "BTCUSDT" else 0.0) for n in names}; nop = {n: res[n][1] for n in names}
    G, NAV = 200000.0, 100000.0
    tw = {n: float(rng.uniform(-1, 1)) for n in names[1:]}; tw["X00USDT"] = 6.0; tw["X39USDT"] = 0.02; tw["X38USDT"] = 0.0
    tw["X01USDT"] = 0.0; tw["X01USDT"] = -sum(tw[k] * bp[k] for k in tw) / bp["X01USDT"]      # a hedged book: β_exec ≈ 0 ⇒ tol = the 0.1%·NAV floor
    s_ = sum(abs(v) for v in tw.values()); tw = {k: v / s_ for k, v in tw.items()}

    def build(d, bp=bp, nop=nop, tw=tw, version="m3_beta_v2", rec_over=None, sc_last=None, nrows=1, man_over=None, ex_status=None, drop_kl=None):
        os.makedirs(os.path.join(d, "in", "target_live"), exist_ok=True)
        tp = os.path.join(d, "in", "target_live", f"{A}.json")
        json.dump({"beta_overlay": {"version": version, "betas": bp, "n_obs": nop}}, open(tp, "w"))
        open(tp + ".sha256", "w").write(sha(open(tp, "rb").read()) + f"  {A}.json\n")
        nz = {k: v for k, v in tw.items() if v != 0.0}
        be = sum(nz[k] * G * bp[k] for k in sorted(nz))
        r = {"version_expected": "m3_beta_v2", "mode": "shadow", "field_ok": True, "betas_sha256": CX.betas_sha256(bp), "book_gross_usdt": G,
             "beta_exec_usdt": be, "nav_usdt": NAV, "n_targeted_names": len(nz)}
        r.update(rec_over or {})
        with open(os.path.join(d, "in", f"anchors_{DAY}.jsonl"), "w") as f:
            for _ in range(nrows): f.write(json.dumps({"anchor_ts": A + 1441.25, "external_book": {"nominal_ts": A}, "m3_beta_overlay": r}) + "\n")
        with open(os.path.join(d, "in", f"orders_{DAY}.jsonl"), "w") as f:
            for k, v in sorted(tw.items()): f.write(json.dumps({"anchor_ts": A + 1441.25, "symbol": k, "target_w": v, "status": "x"}) + "\n")
        open(os.path.join(d, "sc.txt"), "w").write("M3 selfcheck ...\n  OK  published field version == expected: measured=m3_beta_v2 compared_with=m3_beta_v2\n"
                                                    + (sc_last or f"M3_SELFCHECK {A} OK n=0") + "\n")
        fd = os.path.join(d, "fetch")
        if not os.path.isdir(fd): shutil.copytree(os.path.join(base, "fetch"), fd)
        if drop_kl:
            rows = [l for l in gzip.open(os.path.join(fd, "KLINES_RAW.jsonl.gz"), "rt") if json.loads(l)["symbol"] not in drop_kl]
            with gzip.open(os.path.join(fd, "KLINES_RAW.jsonl.gz"), "wt") as f: f.writelines(rows)
        if ex_status:
            E = json.load(open(os.path.join(fd, "EXINFO_SUBSET.json")))
            for k, v in ex_status.items(): E["symbols"][k]["status"] = v
            json.dump(E, open(os.path.join(fd, "EXINFO_SUBSET.json"), "w"), indent=1, sort_keys=True)
        M_ = json.load(open(os.path.join(fd, "FETCH_MANIFEST.json")))
        M_["outputs"]["KLINES_RAW.jsonl.gz"] = sha(open(os.path.join(fd, "KLINES_RAW.jsonl.gz"), "rb").read())
        M_["outputs"]["EXINFO_SUBSET.json"] = sha(open(os.path.join(fd, "EXINFO_SUBSET.json"), "rb").read())
        M_.update(man_over or {})
        json.dump(M_, open(os.path.join(fd, "FETCH_MANIFEST.json"), "w"), indent=1)
        return be

    def cmp(tag, **kw):
        d = os.path.join(root, tag); fresh(d); be = build(d, **kw)
        rc = CX.main(["x", os.path.join(d, "in"), os.path.join(d, "fetch"), os.path.join(d, "sc.txt"), str(A), os.path.join(d, "out")])
        return rc, json.load(open(os.path.join(d, "out", f"B7V2_{A}.json"))), be

    rc, R, be0 = cmp("G")
    check("G BASELINE green market → CLEAN, (0) pass, (ii) pass, 0 over-band", rc == 0 and R["STATUS"] == "CLEAN" and R["gate0"]["pass"] and R["layer_ii"]["pass"]
          and R["layer_i"]["n_over_band"] == 0, f"status={R['STATUS']} und={R['instrument_undecided_because']}")
    tol = R["layer_ii"]["tolerance_usdt"]; tX00 = tw["X00USDT"] * G
    rc, R, _ = cmp("R1", version="m3_beta_v1")
    check("R1 field version v1 → FAIL at (0)a", R["STATUS"] == "FAIL" and not R["gate0"]["items"]["0a_field_version_v2"])
    rc, R, _ = cmp("R2", rec_over={"betas_sha256": "0" * 64})
    check("R2 record betas_sha256 ≠ field → FAIL at (0)c", R["STATUS"] == "FAIL" and not R["gate0"]["items"]["0c_record_betas_sha256_matches_field"])
    rc, R, _ = cmp("R3", sc_last=f"M3_SELFCHECK {A} MISMATCH n=1 bad=['x']")
    check("R3 method (b) MISMATCH → FAIL at (0)d", R["STATUS"] == "FAIL" and not R["gate0"]["items"]["0d_selfcheck_ok_v2"])
    rc, R, _ = cmp("R3b", rec_over={"version_expected": "m3_beta_v1"})
    check("R3b executor record v1 → FAIL at (0)b", R["STATUS"] == "FAIL" and not R["gate0"]["items"]["0b_record_v2_shadow_field_ok"])
    b2 = dict(bp); b2["X00USDT"] += 0.9 * tol / abs(tX00)
    rc, R, _ = cmp("R4a", bp=b2)
    check("R4a (ii) boundary: |Δβ_exec| = 0.9·tol → CLEAN", R["STATUS"] == "CLEAN" and R["layer_ii"]["pass"], f"abs={R['layer_ii'].get('abs_diff_usdt')} tol={tol}")
    b2 = dict(bp); b2["X00USDT"] += 1.1 * tol / abs(tX00)
    rc, R, _ = cmp("R4b", bp=b2)
    check("R4b (ii) boundary: |Δβ_exec| = 1.1·tol → FAIL", R["STATUS"] == "FAIL" and R["layer_ii"]["pass"] is False and R["layer_i"]["n_over_band"] == 0,
          f"abs={R['layer_ii'].get('abs_diff_usdt')} tol={tol}")
    b2 = dict(bp); b2["X39USDT"] += 0.05
    rc, R, _ = cmp("R5", bp=b2)
    check("R5 one small-target name off the band, TRADING, same n_obs → PENDING (unexplained, not red)", R["STATUS"] == "PENDING" and R["layer_i"]["n_unexplained"] == 1
          and R["layer_ii"]["pass"], f"status={R['STATUS']}")
    rc, R, _ = cmp("R6", bp=b2, ex_status={"X39USDT": "SETTLING"})
    check("R6 same name SETTLING at fetch → explained (venue_status_SETTLING) → CLEAN", R["STATUS"] == "CLEAN" and R["layer_i"]["over_band_by_reason"] == {"venue_status_SETTLING": 1})
    n2 = dict(nop); n2["X39USDT"] = 150
    rc, R, _ = cmp("R7", bp=b2, nop=n2)
    check("R7 same name with n_obs_prod 150 ≠ 180 → explained (n_obs_differs) → CLEAN", R["STATUS"] == "CLEAN" and R["layer_i"]["over_band_by_reason"] == {"n_obs_differs": 1})
    t2 = dict(tw); t2["X01USDT"] *= 1.5
    rc, R, _ = cmp("R8", tw=t2)
    check("R8 target_w not summing to 1 → UNDECIDED (closure c1)", R["STATUS"] == "UNDECIDED" and not R["layer_ii"]["closure"]["c1"])
    rc, R, _ = cmp("R9", rec_over={"n_targeted_names": 7})
    check("R9 n_targeted_names ≠ non-zero targets → UNDECIDED (c2)", R["STATUS"] == "UNDECIDED" and not R["layer_ii"]["closure"]["c2"])
    rc, R, _ = cmp("R10", rec_over={"beta_exec_usdt": be0 + 1.0})
    check("R10 record beta_exec not reproduced by plan rows → UNDECIDED (c3)", R["STATUS"] == "UNDECIDED" and not R["layer_ii"]["closure"]["c3"])
    rc, R, _ = cmp("R11", man_over={"verdict": "PARTIAL_FAILED_SYMBOLS"})
    check("R11 fetch not COMPLETE → UNDECIDED", R["STATUS"] == "UNDECIDED")
    rc, R, _ = cmp("R12", drop_kl={"X05USDT"})
    check("R12 targeted name without klines → UNDECIDED (named) and (i) lists it", R["STATUS"] == "UNDECIDED" and R["layer_ii"].get("targeted_without_research_data") == ["X05USDT"]
          and any(o["symbol"] == "X05USDT" for o in R["layer_i"]["over_band"]))
    rc, R, _ = cmp("R13", nrows=2)
    check("R13 two anchors rows for A → UNDECIDED", R["STATUS"] == "UNDECIDED")
    rc, R, _ = cmp("R14", rec_over={"nav_usdt": None})
    check("R14 nav_usdt missing → UNDECIDED", R["STATUS"] == "UNDECIDED")
    rc, R, _ = cmp("R15", man_over={"anchor": A - H4})
    check("R15 fetch manifest for another anchor → UNDECIDED", R["STATUS"] == "UNDECIDED")
    red = [n for n, ok in RESULTS if not ok]
    print(f"B7V2_SELFTEST VERDICT={'ALL GREEN' if not red else 'RED'} tests={len(RESULTS)} red={len(red)}" + (f" failing={red}" if red else ""), flush=True)
    return 0 if not red else 1


if __name__ == "__main__":
    sys.exit(main())
