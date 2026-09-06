#!/usr/bin/env python3
"""exec_n6 readout for one anchor (PREREG_deploy_exec_n6 §2 P1/P4 + sandbox anomalies). Read-only. Usage: readout_n6.py <anchor_ts>
P1 (probe_log.jsonl): klines at N+10s — bar closing at N present?; fundingRate at N+20/45/75/120/240s — N row present?
   A name "should settle at N" ⇔ it has the N row by the last check. Gate wording "100% by N+1:00" is only observable at the
   45s check (next check is 75s): green ⇔ every should-settle name already had the row at the 45s check.
   Otherwise the frozen remedy: producer offset = ceil((t_100 + 30s)/60s) minutes.
P4 (timing): sandbox signal/target rows (logged_utc, runtime_s, data_max_ts) vs live rows and live combo rc time; projected
   combo landing = sandbox target time + live combo latency (live combo rc − live target write). Red if > N+5:30 ⇒ offset 7.
Weight: max X-MBX-USED-WEIGHT-1M seen by the probe in [N+60s, N+300s] = IP-level upper bound for sandbox+probe."""
import json, sys, os, math, re, collections
from datetime import datetime, timezone
A = int(sys.argv[1]); D = os.path.dirname(os.path.abspath(__file__))
SB = "/Users/haosiyu/cc_tmp/exec_n6_sandbox"; W = "/Users/haosiyu/wide_shadow"
def utc(t): return datetime.fromtimestamp(float(t), tz=timezone.utc).strftime("%H:%M:%SZ")
def jl(p):
    out = []
    if not os.path.exists(p): return out
    for l in open(p, errors="ignore"):
        try: out.append(json.loads(l))
        except Exception: pass
    return out
def parse_utc(s):
    if not s: return None
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%S+00:00", "%Y-%m-%d %H:%M:%SZ"):
        try: return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc).timestamp()
        except Exception: pass
    return None
print(f"### exec_n6 readout anchor {A} = {datetime.fromtimestamp(A, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%SZ')}")
# ---------- P1 ----------
pr = [r for r in jl(D + "/probe_log.jsonl") if r.get("anchor") == A]
kl = [r for r in pr if r.get("kind") == "kline"]; fr = [r for r in pr if r.get("kind") == "funding"]
if not pr: print("P1: no probe rows for this anchor (probe not fired yet or skipped)")
else:
    ok = sum(1 for r in kl if r.get("has_bar_closing_at_N")); print(f"P1 klines @N+{kl[0]['t_after'] if kl else '?'}s: bar closing at N present {ok}/{len(kl)}" + ("" if ok == len(kl) else "  ← RED"))
    by = collections.defaultdict(dict); errs = []
    for r in fr:
        by[r["symbol"]][round(r["t_after"] / 5) * 5] = r.get("has_N_row")
        if r.get("err"): errs.append((r["symbol"], r["t_after"], r["err"]))
    checks = sorted({t for d in by.values() for t in d})
    should = [s for s, d in by.items() if any(d.values())]
    never = [s for s, d in by.items() if not any(d.values())]
    print(f"P1 funding checks at t_after≈{checks}s; names {len(by)}: should-settle(N row by last check) {len(should)}, no N row by last check {len(never)} {sorted(never)}")
    for t in checks:
        got = sum(1 for s in should if by[s].get(t)); print(f"   t≈{t:>4}s: N row present {got}/{len(should)}")
    t100 = next((t for t in checks if all(by[s].get(t) for s in should)), None)
    if should:
        if t100 is not None and t100 <= 45: print(f"P1 GREEN: 100% of should-settle names by the {t100}s check (< N+1:00)")
        elif t100 is not None: print(f"P1 RED by frozen wording: 100% only at the {t100}s check ⇒ remedy offset = ceil(({t100}+30)/60) = {math.ceil((t100 + 30) / 60)} min")
        else: print("P1 RED: never 100% within the probe window (N+4:00)")
    if errs: print("P1 probe errors:", errs[:10])
    wts = [(r["t_after"], int(r["weight"])) for r in pr if r.get("weight") and 60 <= r["t_after"] <= 300]
    if wts: print(f"weight (X-MBX-USED-WEIGHT-1M seen by probe, [N+60,N+300]s): max {max(w for _, w in wts)} at N+{[t for t, w in wts if w == max(x for _, x in wts)][0]:.0f}s (IP-level upper bound sandbox+probe; limit 2400; sandbox budget 480)")
# ---------- P4 ----------
def rows(p, e):
    return {int(r["anchor_ts"]): r for r in jl(p) if r.get("e") == e and r.get("anchor_ts")}
sbs, sbt = rows(SB + "/shadow_log.jsonl", "signal"), rows(SB + "/shadow_log.jsonl", "target_live")
lvs, lvt = rows(W + "/shadow_log.jsonl", "signal"), rows(W + "/shadow_log.jsonl", "target_live")
anom = [r for r in jl(SB + "/shadow_log.jsonl") if r.get("anchor_ts") == A and r.get("e") in ("anchor_skip", "anchor_error", "target_live_error", "killed")]
def tline(tag, s, t):
    if not s: print(f"P4 {tag}: no signal row"); return None
    ts_t = parse_utc((t or {}).get("logged_utc")); ts_s = parse_utc(s.get("logged_utc"))
    dm = s.get("data_max_ts"); dm_txt = f"data_max_ts={dm} ({'=N' if dm == A else ('N-'+str(A-int(dm))+'s' if isinstance(dm,(int,float)) else '?')})"
    print(f"P4 {tag}: runtime {s.get('runtime_s')}s, fetched {s.get('fetched')}/missing {s.get('missing')}, fund_updates {s.get('fund_updates')}, weight_used {s.get('weight_used')}, {dm_txt}, target written {utc(ts_t)+' = N+'+str(round((ts_t-A)/60,2))+'min' if ts_t else '?'}, signal logged {utc(ts_s) if ts_s else '?'}")
    return ts_t
t_sb = tline("sandbox", sbs.get(A), sbt.get(A)); t_lv = tline("live   ", lvs.get(A), lvt.get(A))
rc = None
if os.path.exists(W + "/fea171/combo_live.log"):
    for l in open(W + "/fea171/combo_live.log", errors="ignore"):
        m = re.search(rf"combo_live anchor={A} rc=(\d+) (.+UTC \d{{4}})", l)
        if m:
            try: rc = (int(m.group(1)), datetime.strptime(m.group(2), "%a %b %d %H:%M:%S UTC %Y").replace(tzinfo=timezone.utc).timestamp())
            except Exception as ex: rc = (int(m.group(1)), None)
if rc and rc[1]: print(f"P4 live combo rc={rc[0]} at {utc(rc[1])} = N+{(rc[1]-A)/60:.2f}min" + (f"; combo latency after live target = {rc[1]-t_lv:.0f}s" if t_lv else ""))
if t_sb and rc and rc[1] and t_lv:
    proj = t_sb + (rc[1] - t_lv); print(f"P4 projected combo landing with offset 1 = sandbox target + live combo latency = {utc(proj)} = N+{(proj-A)/60:.2f}min ⇒ " + ("GREEN (≤ N+5:30, offset 6 holds)" if proj - A <= 330 else "RED (> N+5:30 ⇒ offset 7)"))
print("sandbox anomaly rows:", anom if anom else "none")
if os.path.exists(SB + "/loop.out"): print("sandbox loop.out tail:", open(SB + "/loop.out", errors="ignore").read().strip().splitlines()[-1:])
