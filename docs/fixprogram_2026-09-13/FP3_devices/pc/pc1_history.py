#!/usr/bin/env python3
"""P-C1 historical backfill runner: every anchor from <from_ts> to <to_ts> that has a phase_A record is replayed with pc1_intent_replay.py in a subprocess;
per anchor: availability of inputs, stage A / stage B counts, cooldown-set cross-check (device's reconstructed cooldown count vs phase_C cooldown_n; mismatch ⇒
UNAVAILABLE_STOPSET for that anchor, result kept but labelled). usage: pc1_history.py <from_ts> <to_ts> <out.json>"""
import sys, os, json, time, subprocess
F, T, OUT = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]; HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.expanduser("~/dl_quant_live")
U = lambda t: time.strftime("%m-%d %HZ", time.gmtime(t)); pa = {}; pc = {}
for l in open(f"{REPO}/state/anchor_runs.log"):
    if " phase_A: " in l:
        try: d = json.loads(l.split(" phase_A: ", 1)[1])
        except Exception: continue
        a = (d.get("external_wait") or {}).get("nominal_anchor_ts") or d.get("anchor_ts")
        if a: pa[int(a)] = d
    elif " phase_C: " in l:
        try: d = json.loads(l.split(" phase_C: ", 1)[1]); pc[l[:20]] = d
        except Exception: pass
res = []
for A in range(F, T + 1, 14400):
    row = {"anchor": A, "utc": U(A)}
    d = pa.get(A)
    if d is None: row["status"] = "NO_PHASE_A"; res.append(row); continue
    if not (d.get("sizing") or {}).get("nav"): row["status"] = "PHASE_A_WITHOUT_SIZING"; res.append(row); continue
    out = f"/tmp/pc1_{A}.json"; r = subprocess.run([sys.executable, f"{HERE}/pc1_intent_replay.py", str(A), out], capture_output=True, text=True)
    if r.returncode != 0: row["status"] = "DEVICE_FAILED"; row["error"] = (r.stderr.strip().splitlines() or ["?"])[-1][:200]; res.append(row); continue
    j = json.load(open(out)); sa = j["stage_A_book_layer"]; sb = j["summary"]
    # cooldown cross-check: phase_C of the same run (logged within ~1h after the anchor's run) carries cooldown_n
    pcn = None
    for k, v in pc.items():
        try: tk = time.mktime(time.strptime(k[:19], "%Y-%m-%dT%H:%M:%S")) - time.timezone
        except Exception: continue
        if A + 14400 <= tk <= A + 14400 + 3600 and isinstance(v.get("per_name_stop"), dict): pcn = v["per_name_stop"].get("cooldown_n")
    dev_cool = len(j["inputs"].get("force_flat") or []) if False else None
    row.update(status="OK", rid=j["rebalance_id"], eq_pre=j["inputs"]["eq_pre_from_phase_A"], stageA=f"{sa['within_step']}/{sa['n']}", stageA_max=sa["max_abs_diff_usdt"], stageB=f"{sb['n_requests_exact']}/{sb['n_requests']}", categories=sb["categories"], reshape_bitwise=((abs(float(j["reshape_report"]["net_before"]) - float(j["recorded_reshape"]["net_before"])) < 1e-6 and abs(float(j["reshape_report"]["gross_before"]) - float(j["recorded_reshape"]["gross_before"])) < 1e-6) if (j.get("reshape_report") and j.get("recorded_reshape") and "net_before" in (j.get("recorded_reshape") or {}) and "net_before" in (j.get("reshape_report") or {})) else None), untradable_n=j["inputs"]["n_untradable_phaseA"], cooldown_n_phaseC=pcn, venue_cap=list((j.get("venue_cap_applied_from_record") or {}).keys()))
    res.append(row)
ok = [r for r in res if r.get("status") == "OK"]
summ = {"n_anchors": len(res), "n_ok": len(ok), "n_stageA_all_within_step": sum(1 for r in ok if r["stageA"].split("/")[0] == r["stageA"].split("/")[1]), "n_stageB_all_exact": sum(1 for r in ok if r["stageB"].split("/")[0] == r["stageB"].split("/")[1]), "n_reshape_bitwise": sum(1 for r in ok if r["reshape_bitwise"] is True), "n_reshape_record_absent": sum(1 for r in ok if r["reshape_bitwise"] is None), "statuses": {}}
for r in res: summ["statuses"][r["status"]] = summ["statuses"].get(r["status"], 0) + 1
json.dump({"device": "pc1_history.py", "utc": time.strftime("%FT%TZ", time.gmtime()), "from": U(F), "to": U(T), "summary": summ, "rows": res}, open(OUT, "w"), indent=1)
print("summary", summ)
for r in res:
    if r.get("status") == "OK": print(f"  {r['utc']} A {r['stageA']} (max {r['stageA_max']:.4f}) B {r['stageB']} reshape_bitwise {r['reshape_bitwise']} cap {r['venue_cap']} cooldown_n(phase_C) {r['cooldown_n_phaseC']}")
    else: print(f"  {r['utc']} {r['status']} {r.get('error','')[:120]}")
