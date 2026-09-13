#!/usr/bin/env python3
"""t5d_interval_sources.py — Mac, READ-ONLY sources (PREREG_T5d §2, §9 step 1).
Copies the executor funding records (~/dl_quant_live/state/live/pilot_log/<day>/funding.jsonl, 2026-08-30..09-11) into cc_tmp with a sha manifest,
then writes one per-settlement interval list per source: producer ledger (ledger_tail of the 2026-09-04 00Z and 2026-09-13 04Z aux snapshots already
copied under T5c/private, rows with ft >= 2026-08-20 00Z, merged by settlement second with a consistency check) and executor fundingInfo
(funding_interval_h per symbol x settlement second, deduplicated with a conflict count).
Launch: env -i PATH=/usr/bin:/bin HOME=$HOME /usr/bin/python3 devices/t5d_interval_sources.py <T5d dir> CPATH,HOME,LC_CTYPE,LIBRARY_PATH,MANPATH,PATH,SDKROOT,__CF_USER_TEXT_ENCODING
"""
import os, sys, json, time, hashlib, shutil, stat
T = os.path.abspath(sys.argv[1]); WHITE = set(x for x in sys.argv[2].split(",") if x)
assert WHITE and sorted(k for k in os.environ if k not in WHITE) == [], ("ENV WHITELIST VIOLATION", sorted(os.environ))
PREREG_SHA = "a1ef16cdba5e95def27f77b180cba3f1ac954ad04c7b0a17f59c24e1a0c85a4f"
def sha(p):   # t6_sha_guard semantics: refuse dataless / short reads
    st = os.stat(p)
    if st.st_flags & getattr(stat, "SF_DATALESS", 0x40000000): raise SystemExit("REFUSE dataless %s" % p)
    h = hashlib.sha256(); n = 0
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b); n += len(b)
    if n != st.st_size: raise SystemExit("REFUSE short read %s" % p)
    return h.hexdigest()
assert sha(T + "/PREREG_T5d_iv_corrected_replay_2026-09-13.md") == PREREG_SHA, "prereg sha"
CC = "/Users/haosiyu/cc_tmp/t5d_2026-09-13"; PRIV = CC + "/private/executor_funding"; os.makedirs(PRIV, exist_ok=True)
T5C = os.path.dirname(T) + "/T5c/private"
man = {}
for line in open(T5C + "/COPY_SHA256.txt"):
    d, p = line.rstrip("\n").split("  ", 1); man[p] = d
for f in ("live/aux_pre_m1_20260904.json", "live/aux.json"): assert sha(T5C + "/" + f) == man[f], ("T5c private copy changed", f)
SRC = "/Users/haosiyu/dl_quant_live/state/live/pilot_log"; days = ["20260830", "20260831"] + ["202609%02d" % d for d in range(1, 12)]
copied = {}
for d in days:
    src = f"{SRC}/{d}/funding.jsonl"
    if not os.path.exists(src): copied[d] = None; continue
    dst = f"{PRIV}/{d}_funding.jsonl"; shutil.copy2(src, dst); copied[d] = dict(sha256=sha(dst), bytes=os.path.getsize(dst))
LO = 1787875200   # 2026-08-20 00Z (well before the 08-30 04Z calendar start)
ledger = {}; conflicts = []
for snap in ("live/aux_pre_m1_20260904.json", "live/aux.json"):
    aux = json.load(open(T5C + "/" + snap))
    for s, rows in aux["ledger_tail"].items():
        for r in rows:
            ft = int(float(r[0])); rate = float(r[1]); iv = float(r[2]) if (len(r) > 2 and r[2]) else None
            if ft < LO: continue
            dct = ledger.setdefault(s, {})
            if ft in dct and (dct[ft][0] != iv or dct[ft][1] != rate): conflicts.append(dict(symbol=s, ft=ft, a=dct[ft], b=[iv, rate], snapshot=snap))
            dct[ft] = [iv, rate]
execr = {}; dup = 0; exec_conf = []
for d in days:
    if copied[d] is None: continue
    for ln in open(f"{PRIV}/{d}_funding.jsonl"):
        try: r = json.loads(ln)
        except Exception: continue
        if r.get("funding_interval_h") is None: continue
        s = r["symbol"]; t = int(round(float(r["settlement_ts"]))); iv = float(r["funding_interval_h"]); rate = float(r.get("funding_rate")) if r.get("funding_rate") is not None else None
        dct = execr.setdefault(s, {})
        if t in dct:
            dup += 1
            if dct[t][0] != iv: exec_conf.append(dict(symbol=s, t=t, a=dct[t][0], b=iv))
        dct[t] = [iv, rate]
out = dict(ledger={s: sorted([[ft] + v for ft, v in d.items()]) for s, d in ledger.items()}, executor={s: sorted([[t] + v for t, v in d.items()]) for s, d in execr.items()})
op = CC + "/t5d_interval_sources.json"; json.dump(out, open(op, "w"))
RC = dict(self_sha256=sha(os.path.abspath(__file__)), prereg_sha256=PREREG_SHA, ledger_snapshots={f: man[f] for f in ("live/aux_pre_m1_20260904.json", "live/aux.json")},
          ledger_symbols=len(ledger), ledger_rows=sum(len(v) for v in ledger.values()), ledger_snapshot_conflicts=len(conflicts), ledger_conflict_examples=conflicts[:10],
          executor_days=copied, executor_symbols=len(execr), executor_rows=sum(len(v) for v in execr.values()), executor_duplicate_rows=dup, executor_interval_conflicts=len(exec_conf), executor_conflict_examples=exec_conf[:10],
          out=op, out_sha256=sha(op), env=dict(whitelist=sorted(WHITE), actual={k: os.environ[k] for k in sorted(os.environ)}), built_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
json.dump(RC, open(T + "/receipts/RECEIPT_T5d_interval_sources.json", "w"), indent=1)
print(json.dumps({k: v for k, v in RC.items() if k not in ("executor_days", "env")}, indent=1))
