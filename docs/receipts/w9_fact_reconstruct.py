"""W9 fixture fidelity: rebuild the executor's pre-clamp reshape at real anchors from the ledger and compare with recorded targets.
Reads the frozen T5b private copy (read-only)."""
import json, re, calendar, time, collections, sys
import numpy as np
P = "/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_r2_2026-09-13/T5b/private"
def G(t): return int(float(t) // 14400) * 14400
def day(A): return time.strftime("%Y%m%d", time.gmtime(A))
def rows(p):
    out = []
    for ln in open(p, errors="replace"):
        try: out.append(json.loads(ln))
        except Exception: pass
    return out
blocks = collections.defaultdict(list); cur = None; pat = re.compile(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z) (.*)$")
for ln in open(P + "/exec/anchor_runs.log", errors="replace"):
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
for A in [int(x) for x in sys.argv[1:]]:
    b, bp = lb(A), lb(A - 14400)
    pa = b["ph"]["phase_A"]; eb = pa.get("external_book") or {}
    S = float(pa["sizing"]["gross"]); gin = float(eb["gross_in"])
    arow = [r for r in rows(f"{P}/exec/pilot_log/{day(A)}/anchors.jsonl") if G(r["anchor_ts"]) == A][-1]
    rid = arow["rebalance_id"]; tg = float(arow["target_gross"])
    O = [r for r in rows(f"{P}/exec/pilot_log/{day(A)}/orders.jsonl") if r.get("rebalance_id") == rid]
    un = pa.get("untradable_names") or {}
    stop = set(((bp["ph"].get("phase_C") or {}).get("per_name_stop") or {}).get("stopped") or [])
    w = json.load(open(f"{P}/ws/target_live/{A}.json"))["weights"]
    names = sorted({r["symbol"] for r in O})
    Pop = [s for s in names if float(w.get(s, 0.0)) != 0.0]
    vec = np.array([0.0 if s in stop else float(w[s]) / gin for s in Pop])
    m = vec.mean(); v2 = vec - m; L = np.abs(v2).sum(); T = {s: float(v2[i] / L * S) for i, s in enumerate(Pop)}
    rec = {}
    for r in O:
        if r.get("order_type") in ("maker",) and r.get("target_w") is not None: rec[r["symbol"]] = float(r["target_w"]) * tg
        elif r.get("target_w") is not None and r["symbol"] not in rec: rec[r["symbol"]] = float(r["target_w"]) * tg
    clamped = set(x for k, v in un.items() if k != "popped" for x in v)
    diffs = [abs(T[s] - rec[s]) for s in Pop if s in rec and s not in clamped and s not in stop]
    print(f"A {A} {time.strftime('%m-%d %H:%MZ', time.gmtime(A))} rid {rid} S {S:.2f} gross_in {gin:.6f} target_gross {tg:.2f} |P| {len(Pop)} rows {len(names)} "
          f"net_before(rec) {(arow.get('reshape') or {}).get('net_before')} net_before(rebuilt) {float(np.array([0.0 if s in stop else float(w[s]) / gin for s in Pop]).sum()) * S:.4f}")
    print(f"   compared {len(diffs)} unclamped names: max |T_rebuilt − T_recorded| = {max(diffs):.3e} USDT; shift a = {-m / L * S:+.4f}  scale b = {1 / (L * gin):.6f}")
    print("   stop set (prev phase_C):", sorted(stop), " buckets:", {k: v for k, v in un.items()})
    for s in sorted(stop):
        print("     stop", s, "file w", w.get(s), "rebuilt T", round(T.get(s, float('nan')), 4), "recorded", rec.get(s), "in P", s in Pop)
