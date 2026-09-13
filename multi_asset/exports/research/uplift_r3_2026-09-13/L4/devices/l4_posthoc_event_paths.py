#!/usr/bin/env python3
"""l4_posthoc_event_paths.py (v2) -- L4 POST-HOC descriptive (written after reading POSTHOC_L4_basis_reconcile.json; not in the PREREG; changes no verdict).
v1 (commit 4 lines above in git log) was stopped after 3 events because it re-decompressed whole npz arrays on every element access; its partial stdout
is kept as receipts/l4_posthoc_event_paths_run1_killed_slow_stdout.log. v2 loads each array once and adds the split below.
(1) Re-run the frozen state machine by exec-ing the constants/core section of the committed l4_run.py (sha asserted); assert the base net series equal
L4_SERIES.npz bitwise for all 12 arms. (2) For every hold (completed and open), telescoped basis P&L under B2 (premium index, frozen primary) and B1
(Binance perp/spot closes, carried), summed by exit reason (normal / forced_a spot gone / forced_b no funding / forced_c premium gone / open), in bps per
unit sleeve capital, plus the same sums per anchor over FULL. (3) Raw per-anchor paths (eligibility, spot tradable, events, summed rate, raw B1, raw B2)
over the last 24 anchors and 6 after, for the top-10 |B1-B2| holds of A01 and A05 from the reconcile receipt.
Usage: python3 l4_posthoc_event_paths.py <env_whitelist_csv> <work_dir> <path_to_l4_run.py> <posthoc_reconcile_json>
"""
import os, sys, json, time, math, hashlib, calendar
WHITE = set(x for x in sys.argv[1].split(",") if x); assert WHITE, "non-empty env whitelist required"
EXTRA = sorted(k for k in os.environ if k not in WHITE); assert EXTRA == [], ("ENV WHITELIST VIOLATION", EXTRA)
WORK = os.path.abspath(sys.argv[2]); RUNDEV = os.path.abspath(sys.argv[3]); PH = os.path.abspath(sys.argv[4])
import numpy as np
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
def iso(t): return time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(int(t)))
def tsp(s): return calendar.timegm(time.strptime(s, "%Y-%m-%dT%H:%MZ"))
assert sha(RUNDEV) == "cfa2517120979a46881eae42e4968a34a8d529e8fc817a0a54e16e45a0fc8a22"
assert sha(os.path.join(WORK, "l4_inputs.npz")) == "3d9d3466ce0078730c3630876d3767ba69da0135cfad9edf42fbfe59bfce05dd"
assert sha(os.path.join(WORK, "L4_SERIES.npz")) == "8ba4ba1fa6220d9763443a920ea37a9abcba0536f55954a6d5d7fa05c2bb4473"
OUT = dict(device="l4_posthoc_event_paths.py (v2)", label="POST-HOC", device_sha256=sha(os.path.abspath(__file__)), run_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           posthoc_reconcile_sha256=sha(PH), python=sys.version.split()[0], numpy=np.__version__, affinity=sorted(os.sched_getaffinity(0)))
assert len(OUT["affinity"]) <= 8
src = open(RUNDEV).read(); a = src.index("# ---------------------------------------------------------------- constants"); b = src.index("# ---------------------------------------------------------------- G-SYN")
NS_ = {"np": np, "math": math, "REC": {"gates": {}}}; exec(compile(src[a:b], "l4_run_core", "exec"), NS_)
ARMS = NS_["ARMS"]; prepare = NS_["prepare"]; simulate = NS_["simulate"]; account = NS_["account"]; CS_BASE = NS_["CS_BASE"]
Zf = np.load(os.path.join(WORK, "l4_inputs.npz"), allow_pickle=True); Z = {k: Zf[k] for k in Zf.files}; SER = np.load(os.path.join(WORK, "L4_SERIES.npz"))
EG = Z["EG"].astype(np.int64); SYM = [str(s) for s in Z["SYM"]]; iW0 = int(Z["iW0"]); iW1 = int(Z["iW1"]); gi = {int(t): i for i, t in enumerate(EG)}
B2 = Z["B2"].astype(np.float64); B1 = Z["B1"].astype(np.float64)
D = prepare(Z["A"].astype(np.float64), Z["NEV"].astype(np.int16), Z["ELIG"].astype(bool), Z["TRAD"].astype(bool), Z["SPOT_OK"].astype(bool), B2, B1)
nA = iW1 - iW0 + 1; eq = {}; split = {}
for arm in ARMS:
    POS, holds, openh = simulate(arm, D, iW0, iW1); acc = account(POS, D, iW0, arm["K"], CS_BASE); eq[arm["id"]] = bool(np.array_equal(acc["net"], SER["%s_net" % arm["id"]]))
    n = acc["n"]; s = {}
    for (k, t0, t1, why) in holds + openh:
        te = t1 if t1 is not None else nA; i0 = iW0 + t0; i1 = iW0 + te
        v2 = n * 1e4 * (D["B2F"][i0, k] - D["B2F"][i1, k]); v1 = n * 1e4 * (D["B1F"][i0, k] - D["B1F"][i1, k])
        inc = n * 1e4 * float(Z["A"][i0:i1, k].sum())
        d = s.setdefault(why, dict(holds=0, b2_sum=0.0, b1_sum=0.0, b1_nan_holds=0, income_sum=0.0))
        d["holds"] += 1; d["b2_sum"] += float(v2); d["income_sum"] += inc
        if math.isfinite(v1): d["b1_sum"] += float(v1)
        else: d["b1_nan_holds"] += 1
    for d in s.values():
        d["b2_per_anchor_FULL"] = d["b2_sum"] / nA; d["b1_per_anchor_FULL"] = d["b1_sum"] / nA; d["income_per_anchor_FULL"] = d["income_sum"] / nA
    split[arm["id"]] = s
    print("SPLIT %s " % arm["id"] + " | ".join("%s n=%d inc %.4f b2 %.4f b1 %.4f" % (w, d["holds"], d["income_per_anchor_FULL"], d["b2_per_anchor_FULL"], d["b1_per_anchor_FULL"]) for w, d in sorted(s.items())), flush=True)
R = json.load(open(PH)); seen = set(); events = []
for armid in ("A01", "A05"):
    for h in R["arms"][armid]["top10_by_abs_diff"]:
        key = (h["sym"], h["exit"])
        if key in seen or h["exit"] is None: continue
        seen.add(key); k = SYM.index(h["sym"]); ie = gi[tsp(h["exit"])]; ii = gi[tsp(h["entry"])]
        rows = []
        for i in range(max(ii, ie - 24), min(len(EG), ie + 7)):
            v1 = B1[i, k]; v2 = B2[i, k]
            rows.append(dict(t=iso(EG[i]), rel=int(i - ie), elig=bool(Z["ELIG"][i, k]), spot_trad=bool(Z["TRAD"][i, k]), nev_window=int(Z["NEV"][i, k]), rate_sum_bps=float(Z["A"][i, k] * 1e4),
                             b1_bps=(round(float(v1) * 1e4, 1) if np.isfinite(v1) else None), b2_bps=(round(float(v2) * 1e4, 1) if np.isfinite(v2) else None)))
        events.append(dict(arm=armid, sym=h["sym"], entry=h["entry"], exit=h["exit"], reason=h["reason"], b1_pnl=h["b1_pnl"], b2_pnl=h["b2_pnl"], path=rows))
        w = [r for r in rows if -23 <= r["rel"] <= 0]
        print("EVENT %s %-12s %s->%s %-8s b1 %.0f b2 %.0f | rel -23..0 b1: %s | b2: %s | spot_trad: %s | nev(-24..-1): %s" % (
            armid, h["sym"], h["entry"], h["exit"], h["reason"], h["b1_pnl"], h["b2_pnl"], [r["b1_bps"] for r in w], [r["b2_bps"] for r in w], "".join("1" if r["spot_trad"] else "0" for r in w),
            [r["nev_window"] for r in rows if -24 <= r["rel"] <= -1]), flush=True)
OUT.update(series_bitwise_equal=eq, split_by_exit_reason=split, events=events)
json.dump(OUT, open(os.path.join(WORK, "POSTHOC_L4_event_paths.json"), "w"), indent=1)
print("SUMMARY l4_posthoc_event_paths v2 (POST-HOC) series_equal=%d/12 events=%d self_sha256=%s" % (sum(eq.values()), len(events), OUT["device_sha256"][:16]), flush=True)
