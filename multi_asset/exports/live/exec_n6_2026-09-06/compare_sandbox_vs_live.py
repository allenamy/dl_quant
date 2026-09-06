#!/usr/bin/env python3
"""P2: compare the sandbox producer (offset 1, budget 480) with the live producer (offset 16) for the same anchor(s).
Reads both shadow_log.jsonl signal rows and target_live files (sandbox = king form; live target_live is rewritten by combo,
so compare against the live KING backup target_live_king/<A>.json). Read-only."""
import json, sys, os, glob, numpy as np
from datetime import datetime, timezone
SB="/Users/haosiyu/cc_tmp/exec_n6_sandbox"; W="/Users/haosiyu/wide_shadow"
def rows(p, e="signal"):
    out={}
    for l in open(p, errors="ignore"):
        try: r=json.loads(l)
        except Exception: continue
        if r.get("e")==e and r.get("anchor_ts"): out[int(r["anchor_ts"])]=r
    return out
sb=rows(SB+"/shadow_log.jsonl"); lv=rows(W+"/shadow_log.jsonl")
sbt=rows(SB+"/shadow_log.jsonl","target_live"); lvt=rows(W+"/shadow_log.jsonl","target_live")
anchors=sorted(set(sb)&set(lv)) if len(sys.argv)<2 else [int(a) for a in sys.argv[1:]]
for A in anchors:
    s=sb.get(A); l=lv.get(A)
    if not s or not l: print(A, "missing signal row: sandbox", bool(s), "live", bool(l)); continue
    u=datetime.fromtimestamp(A,tz=timezone.utc).strftime("%m-%d %HZ")
    keys=("members","sel","coverage","fund_updates","fund_updates_base","forced_exit_n","fetched","missing","runtime_s")
    print(f"== {u}: sandbox {{{', '.join(f'{k}={s.get(k)}' for k in keys)}}}")
    print(f"           live    {{{', '.join(f'{k}={l.get(k)}' for k in keys)}}}")
    print(f"   w3 sandbox {s.get('w3')} live {l.get('w3')}  equal={s.get('w3')==l.get('w3')}")
    ps=f"{SB}/state/target_live/{A}.json"; pl=f"{W}/state/target_live_king/{A}.json"
    if os.path.exists(ps) and os.path.exists(pl):
        ds=json.load(open(ps)); dl=json.load(open(pl)); ws=ds["weights"]; wl=dl["weights"]; syms=set(ws)|set(wl)
        g=sum(abs(v) for v in wl.values()); dmax=max(abs(ws.get(k,0)-wl.get(k,0)) for k in syms); dsum=sum(abs(ws.get(k,0)-wl.get(k,0)) for k in syms)
        print(f"   target king-form: n sandbox {len(ws)} live {len(wl)}; max|Δw| {dmax:.2e}; Σ|Δw|/gross {dsum/g:.2e}; universe_sha equal={ds.get('universe_sha')==dl.get('universe_sha')}; producer {ds.get('producer')}/{dl.get('producer')}")
        st=sbt.get(A,{}); lt=lvt.get(A,{}); print(f"   written: sandbox {st.get('written_utc') or st}  live {lt.get('written_utc') or lt}")
    else:
        print("   target files:", os.path.exists(ps), os.path.exists(pl))
# sandbox API weight peak per anchor from its log lines
for l in open(SB+"/loop.out", errors="ignore").read().splitlines()[-6:]: print("  loop.out:", l[:160])
