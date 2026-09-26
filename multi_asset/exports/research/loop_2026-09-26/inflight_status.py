#!/usr/bin/env python3
"""Loop step 2 helper (E-0926-I): for every registered in-flight job on pod2, print its last terminal marker, the log's
last line + age, and whether any process still has the log open or runs from its directory. Silence is classified:
RUNNING (process alive, no terminal) / TERMINAL (terminal marker present) / SILENT_DEATH (no process, no terminal).
Agents add their jobs to INFLIGHT_REGISTRY.json (name, owner, log, pgid_file, terminal regex)."""
import json, os, subprocess, sys
REG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "INFLIGHT_REGISTRY.json")
jobs = [j for j in json.load(open(REG)) if not j.get("closed")]   # a job the lead has handled is marked closed: true
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
    pg=j.get("pgid_file")
    if pg and os.path.exists(pg):
        try:
            g=int(json.load(open(pg)).get("pgid")); alive = alive or any(open(f"/proc/{x}/stat").read().split()[4]==str(g) for x in os.listdir("/proc") if x.isdigit())
        except Exception: pass
    out["process_alive"]=alive
    out["state"]="TERMINAL" if term else ("RUNNING" if alive else "SILENT_DEATH")
    print(json.dumps(out))
'''
import shlex
p = subprocess.run(["ssh", "-o", "ConnectTimeout=15", "-o", "BatchMode=yes", "pod2", "python3 - " + shlex.quote(json.dumps(jobs))],
                   input=remote, capture_output=True, text=True, timeout=120)
print(p.stdout, end=""); print(p.stderr[-300:], end="", file=sys.stderr)
sys.exit(p.returncode)
