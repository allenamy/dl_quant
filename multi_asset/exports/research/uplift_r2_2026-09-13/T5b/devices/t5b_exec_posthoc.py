#!/usr/bin/env python3
"""t5b_exec_posthoc.py — POST-HOC check (not in SPEC_T5b; written after Q3 showed STOPPED names recorded as add_blocked). Changes no reading.
For every (anchor A in W1 ∪ W2, name s) with s in the executor's LIVE phase_C per_name_stop.stopped list of the PREVIOUS anchor (i.e. stopped at plan time of A)
and held at A: fit the uniform re-demean shift of the executor reshape at A from tradable names (T_exec = a + b*T_file, OLS over names with a maker row,
not in any recorded untradable bucket, |T_file| > 0), predict the pre-clamp target of a zeroed stop name (= a), predict its clamp bucket from
anchor_loop.clamp_held_untradable (same sign & |t|<=|c| reduced; same sign & |t|>|c| add_blocked; else flatten_only), compare with the recorded bucket
(phase_A.untradable_names) and the recorded orders. Reads only private copies and T5b receipts.
Launch: env -i PATH=/usr/bin:/bin HOME=$HOME /usr/bin/python3 devices/t5b_exec_posthoc.py <T5b dir> CPATH,HOME,LC_CTYPE,LIBRARY_PATH,MANPATH,PATH,SDKROOT,__CF_USER_TEXT_ENCODING
"""
import os, sys, json, re, collections, calendar, time
T5B = os.path.abspath(sys.argv[1]); WHITE = set(x for x in sys.argv[2].split(",") if x)
assert WHITE and sorted(k for k in os.environ if k not in WHITE) == [], ("ENV WHITELIST VIOLATION", sorted(os.environ))
sys.path.insert(0, T5B + "/devices")
import numpy as np
import t5b_common as TC
EXR = json.load(open(T5B + "/receipts/RECEIPT_T5b_exec.json")); PX = T5B + "/private/exec"; PW = T5B + "/private/ws"; utc = TC.utc
def G(t): return int(float(t) // 14400) * 14400
W = list(range(1787702400, 1788134400 + 1, 14400)) + list(range(1788350400, 1789214400 + 1, 14400))
ORD = collections.defaultdict(list); RB = {}; ANC = {}
for d in sorted(os.listdir(PX + "/pilot_log")):
    for fn, tgt in (("orders.jsonl", "o"), ("position_readback.jsonl", "r"), ("anchors.jsonl", "a")):
        p = f"{PX}/pilot_log/{d}/{fn}"
        if not os.path.exists(p): continue
        for ln in open(p, errors="replace"):
            try: r = json.loads(ln)
            except Exception: continue
            if r.get("anchor_ts") is None: continue
            g = G(r["anchor_ts"])
            if tgt == "o": ORD[g].append(r)
            elif tgt == "r": RB[(g, r["symbol"])] = r
            else: ANC[g] = r
blocks = collections.defaultdict(list); cur = None; pat = re.compile(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z) (.*)$")
for ln in open(PX + "/anchor_runs.log", errors="replace"):
    m = pat.match(ln.rstrip("\n"))
    if not m: continue
    ts, rest = m.groups()
    if rest.startswith("anchor start mode="):
        if cur is not None and cur["ph"]: blocks[cur["key"]].append(cur)
        cur = dict(mode=rest.split("=", 1)[1].strip(), ph={}, key=G(calendar.timegm(time.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")))); continue
    if cur is None: continue
    for tag in ("phase_A", "phase_C"):
        if rest.startswith(tag + ": "):
            try:
                cur["ph"][tag] = json.loads(rest[len(tag) + 2:])
                if tag == "phase_A" and cur["ph"][tag].get("anchor_ts"): cur["key"] = G(cur["ph"][tag]["anchor_ts"])
            except Exception: pass
    if rest.startswith("anchor done rc="): blocks[cur["key"]].append(cur); cur = None
def lb(A):
    bl = [b for b in blocks.get(A, []) if b["mode"] == "LIVE"]; wc = [b for b in bl if "phase_C" in b["ph"]]
    return wc[-1] if wc else (bl[-1] if bl else None)
def tl(A):
    p = f"{PW}/target_live/{A}.json"
    return json.load(open(p)) if os.path.exists(p) else None
out = []
for A in W:
    bprev = lb(A - 14400); b = lb(A)
    if not b or not bprev: continue
    pcp = (bprev["ph"].get("phase_C") or {}).get("per_name_stop")
    if not isinstance(pcp, dict) or not pcp.get("stopped"): continue
    pa = b["ph"].get("phase_A") or {}; ar = ANC.get(A); d = tl(A)
    if not isinstance(pa, dict) or not ar or d is None: continue
    eb = pa.get("external_book") or {}; S = (pa.get("sizing") or {}).get("gross"); gin = eb.get("gross_in"); tg = ar.get("target_gross")
    if not (S and gin and tg): continue
    un = pa.get("untradable_names") or {}; allb = set(x for v in un.values() if isinstance(v, list) for x in v)
    xs, ys = [], []
    for r in ORD.get(A, []):
        s = r["symbol"]
        if r.get("order_type") != "maker" or s in allb or r.get("target_w") is None: continue
        w = float(d["weights"].get(s, 0.0))
        if w == 0.0: continue
        xs.append(w / float(gin) * float(S)); ys.append(float(r["target_w"]) * float(tg))
    if len(xs) < 20: continue
    X = np.vstack([np.ones(len(xs)), np.array(xs)]).T; coef, res, *_ = np.linalg.lstsq(X, np.array(ys), rcond=None); a, bb = float(coef[0]), float(coef[1])
    fit_resid = float(np.abs(X @ coef - np.array(ys)).max())
    for s in pcp["stopped"]:
        rb = RB.get((A - 14400, s)); held = float(rb["venue_position_notional"]) if rb else 0.0
        if held == 0.0: continue
        t = a
        pred = "reduced" if (t * held > 0 and abs(t) <= abs(held)) else ("add_blocked" if t * held > 0 else "flatten_only")
        recb = [k for k, v in un.items() if isinstance(v, list) and s in v]
        rows = [f'{r.get("order_type")}:{r.get("terminal_reason")}' for r in ORD.get(A, []) if r["symbol"] == s]
        rbn = RB.get((A, s))
        out.append(dict(utc=utc(A), symbol=s, held_prev_readback=held, fitted_shift_a_usdt=a, fitted_scale_b=bb, fit_max_abs_resid_usdt=fit_resid, n_fit=len(xs), predicted_bucket=pred, recorded_buckets=recb,
                        orders=sorted(set(rows)), held_post=(float(rbn["venue_position_notional"]) if rbn else None), net_before=((ar.get("reshape") or {}).get("net_before") if isinstance(ar.get("reshape"), dict) else None)))
agree = sum(1 for o in out if o["recorded_buckets"] and o["predicted_bucket"] in o["recorded_buckets"])
summ = dict(label="POST-HOC check; not pre-registered; changes no reading", n_stopped_held_instances=len(out), n_recorded_bucket_known=sum(1 for o in out if o["recorded_buckets"]),
            n_pred_matches_record=agree, recorded_bucket_counts=dict(collections.Counter(",".join(o["recorded_buckets"]) or "UNLISTED(truncated?)" for o in out)),
            instances_not_flatten_only=[o for o in out if "flatten_only" not in o["recorded_buckets"]], all_instances=out, self_sha256=TC.sha(os.path.abspath(__file__)))
json.dump(summ, open(T5B + "/receipts/RECEIPT_T5b_exec_posthoc.json", "w"), indent=1)
print(json.dumps({k: v for k, v in summ.items() if k not in ("all_instances", "instances_not_flatten_only")}))
for o in out: print(o["utc"], o["symbol"], "held %.1f" % o["held_prev_readback"], "a %+.1f b %.4f resid %.2f n %d" % (o["fitted_shift_a_usdt"], o["fitted_scale_b"], o["fit_max_abs_resid_usdt"], o["n_fit"]), "pred", o["predicted_bucket"], "rec", o["recorded_buckets"], o["orders"], "post", o["held_post"], "net_before", o["net_before"])
print("DONE_t5b_exec_posthoc")
