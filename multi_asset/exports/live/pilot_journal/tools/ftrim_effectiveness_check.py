"""Read-only: after FTRIM went live (09-02 12Z), are there still HELD short positions in names whose realised settlement rn8 <= -10 bp? If so, are they
in the producer's ftrim exclusion list (=> residual/reduce-only), or actively targeted (=> producer rn8 (predicted) vs settled rn8 mismatch)?"""
import json, os, glob, time, collections
L = os.path.expanduser("~/dl_quant_live/state/live"); W = os.path.expanduser("~/wide_shadow/state")
def utc(t): return time.strftime("%m-%d %HZ", time.gmtime(int(t)))
def jl(p):
    out = []
    for l in open(p, errors="ignore"):
        try: out.append(json.loads(l))
        except Exception: pass
    return out
pos = collections.defaultdict(dict)
for p in sorted(glob.glob(f"{L}/pilot_log/2026*/position_readback.jsonl")):
    for r in jl(p):
        a = int(round(float(r["anchor_ts"]) / 14400) * 14400); n = r.get("venue_position_notional")
        if n is not None and abs(float(n)) > 0: pos[a][r["symbol"]] = float(n)
fr = collections.defaultdict(dict)
for p in sorted(glob.glob(f"{L}/pilot_log/2026*/funding.jsonl")):
    for r in jl(p):
        t = int(float(r["settlement_ts"])) // 14400 * 14400; h = float(r.get("funding_interval_h") or 8); fr[t][r["symbol"]] = float(r["funding_rate"]) * (8.0 / h) * 1e4
def rn8_at(a):
    out = {}
    for t in sorted(t for t in fr if t <= a)[-6:]: out.update(fr[t])
    return out
tot = collections.Counter(); ex = []
for a in sorted(a for a in pos if a >= 1788352800):   # 09-02 12Z
    p = f"{W}/target_combo/{a}.json"
    if not os.path.exists(p): continue
    d = json.load(open(p)); ft = d.get("ftrim") or {}; excl = set()
    for k, v in ft.items():
        if isinstance(v, list): excl |= set(v)
        elif isinstance(v, dict): excl |= set(v.keys())
    tw = d.get("weights") or {}; rn = rn8_at(a)
    for s, n in pos[a].items():
        f = rn.get(s)
        if n < 0 and f is not None and f <= -10:
            targeted = s in tw and tw[s] < 0; inex = s in excl; tot["held_deepneg_short"] += 1; tot["  in_ftrim_list"] += inex; tot["  targeted_short_in_target_live"] += targeted
            if len(ex) < 12: ex.append((utc(a), s, round(n), f"rn8 {f:+.1f}", "ftrim_listed" if inex else "-", "targeted" if targeted else "untargeted(residual)"))
    if a == sorted(pos)[-1] or tot["ftrim_keys_printed"] == 0: print("ftrim block keys sample:", {k: (v if not isinstance(v, (list, dict)) else f"{type(v).__name__}[{len(v)}]") for k, v in ft.items()}); tot["ftrim_keys_printed"] = 1
print("post-FTRIM anchors: held deep-negative (rn8<=-10) SHORT positions:", dict(tot)); print("examples:", ex)
