import json, glob, os, time, collections
L = os.path.expanduser("~/dl_quant_live/state/live/pilot_log")
T_PEAK_APPROX = 1789562700            # 2026-09-16 12:45Z (lead: peak row 09-16 12:45Z)
fmt = lambda t: time.strftime("%m-%dT%H:%MZ", time.gmtime(t))
def days(): return [d for d in sorted(glob.glob(f"{L}/2026*")) if os.path.basename(d) >= "20260916"]
def jl(name):
    out = []
    for d in days():
        p = f"{d}/{name}.jsonl"
        if os.path.exists(p):
            for l in open(p):
                l = l.strip()
                if l: out.append(json.loads(l))
    return out
def nav_rows():
    r = sorted(jl("daily_nav"), key=lambda r: r["nav_ts"]); return r
def income(tA, tB):
    out = []
    for l in open(os.path.expanduser("~/guard_twin/state/income.jsonl")):
        r = json.loads(l); t = r["time"] / 1000
        if tA < t <= tB: out.append(r)
    return out
