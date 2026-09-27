#!/usr/bin/env python3
"""Loop step 2 helper (E-0926-I): for every registered in-flight job on pod2, print its last terminal marker, the log's
last line + age, and whether any process still has the log open or runs from its directory. Silence is classified:
RUNNING (process alive, no terminal) / TERMINAL (terminal marker present) / SILENT_DEATH (no process, no terminal).
Agents add their jobs to INFLIGHT_REGISTRY.json (name, owner, log, pgid_file, terminal regex)."""
import json, os, subprocess, sys
REG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "INFLIGHT_REGISTRY.json")
jobs = [j for j in json.load(open(REG)) if not j.get("closed")]   # a job the lead has handled is marked closed: true
# rev 1 (2026-09-27, new arm64 host): jobs on this mac were sent to pod2 and came back NO_LOG, which reads like "not
# started" whether they run or not (silence has two meanings). They are now checked here: PGID alive via killpg(pg, 0);
# a RESIDENT job with a heartbeat file is alive only while the heartbeat is younger than 3 minutes.
local = [j for j in jobs if str(j.get("host", "")).startswith("mac")]
jobs = [j for j in jobs if j not in local]
import time
for j in local:
    out = {"name": j["name"], "owner": j["owner"], "host": "mac"}
    if j.get("pgid"):
        try: os.killpg(int(j["pgid"]), 0); out["process_alive"] = True
        except ProcessLookupError: out["process_alive"] = False
        except PermissionError: out["process_alive"] = True
        out["state"] = "RUNNING" if out["process_alive"] else "ENDED_CHECK_OWNER_LOG"
    elif "heartbeat" in j.get("liveness", ""):
        hb = os.path.expanduser(j["liveness"].split()[0])
        try:
            age = time.time() - json.load(open(hb))["run_ms"] / 1000; out["heartbeat_age_s"] = round(age)
            out["state"] = "RUNNING" if age < 180 else "STALE_HEARTBEAT"
        except Exception as e: out["state"] = f"HEARTBEAT_UNREADABLE {type(e).__name__}"
    else: out["state"] = "LOCAL_NO_PROBE"
    print(json.dumps(out))
remote = r'''
import json,os,re,time,sys,glob
jobs=json.loads(sys.argv[1])
for j in jobs:
    lg=j["log"]; out={"name":j["name"],"owner":j["owner"]}
    if not os.path.exists(lg): out["state"]="NO_LOG"; print(json.dumps(out)); continue
    L=open(lg,errors="ignore").read().splitlines()
    term=[l for l in L if re.search(j["terminal"],l)]
    out["last_line"]=(L[-1] if L else "")[:160]; out["log_age_min"]=round((time.time()-os.path.getmtime(lg))/60,1)
    out["terminal"]=term[-1][:160] if term else None
    alive=False; d=os.path.dirname(lg)
    for p in glob.glob("/proc/[0-9]*"):
        try:
            if os.path.realpath(p+"/cwd").startswith(os.path.dirname(d)) or any(os.path.realpath(f)==os.path.realpath(lg) for f in glob.glob(p+"/fd/*")): alive=True; break
        except Exception: pass
    gs=set()
    if j.get("pgid"): gs.add(int(j["pgid"]))
    pg=j.get("pgid_file")
    if pg and os.path.exists(pg):
        raw=open(pg).read().strip()
        try: gs.add(int(json.loads(raw).get("pgid")))
        except Exception:
            try: gs.add(int(raw.split()[0]))
            except Exception: pass
    for x in os.listdir("/proc"):
        if not x.isdigit(): continue
        try:
            st=open(f"/proc/{x}/stat").read(); pgid=int(st.rsplit(")",1)[1].split()[2])
            if pgid in gs: alive=True; break
        except Exception: pass
    out["pgids"]=sorted(gs)
    out["process_alive"]=alive
    out["state"]="TERMINAL" if term else ("RUNNING" if alive else "SILENT_DEATH")
    print(json.dumps(out))
'''
import shlex
p = subprocess.run(["ssh", "-o", "ConnectTimeout=15", "-o", "BatchMode=yes", "pod2", "python3 - " + shlex.quote(json.dumps(jobs))],
                   input=remote, capture_output=True, text=True, timeout=120)
print(p.stdout, end=""); print(p.stderr[-300:], end="", file=sys.stderr)
sys.exit(p.returncode)
