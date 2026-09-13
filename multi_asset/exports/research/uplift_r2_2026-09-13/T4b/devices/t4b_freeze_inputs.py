#!/usr/bin/env python3
"""t4b_freeze_inputs.py — Mac, read-only on ~/wide_shadow (PREREG_T4b §3 inputs). Run only OUTSIDE the producer window.
(1) copies producer_state_snapshots/1789200000 (09-12 08Z close) into private/producer_snapshot_1789200000 and verifies each file against
    the original SHA256SUMS.txt (16-hex prefixes, that file's own format); writes a full-hash SHA256SUMS.txt for the copy;
(2) freezes the live producer state now: state/aux.json, state/leg_returns_live.json, state/rolling.npz, shadow_log.jsonl — copied with the
    producer's last_anchor and file mtimes read before and after (must be unchanged), plus every immutable per-anchor file needed:
    weights/{A}.npz for 09-12 08Z..last, target_live_king/target_combo/target_live for 09-12 12Z..last, fea171/state_H_{f10,kc,fc} at 09-12 08Z;
(3) GATE CACHE: rows <= 09-12 08Z of the frozen cache are bitwise equal to the producer snapshot's own cache (no late fill);
(4) staleness and membership facts for the forward anchors (members from the live weights files; ledger from the frozen aux):
    stale (> 12h or no row) and non-live member counts per anchor.
Writes private/snapshot_live/SHA256SUMS.txt ('./path' format) and receipts/RECEIPT_T4b_freeze_inputs.json."""
import os, sys, json, time, hashlib, shutil
WHITE = set(x for x in sys.argv[1].split(",") if x) if len(sys.argv) > 1 else None
assert WHITE, "whitelist argv[1]"
assert sorted(k for k in os.environ if k not in WHITE) == [], ("ENV WHITELIST VIOLATION", sorted(os.environ))
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); T4B = os.path.dirname(HERE); PRIV = T4B + "/private"
W = "/Users/haosiyu/wide_shadow"; SRC = "/Users/haosiyu/Desktop/quant_research/multi_asset/exports/live/producer_state_snapshots/1789200000"
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
now = time.gmtime(); mm = now.tm_hour % 4 * 60 + now.tm_min
assert not (15 <= mm <= 24), ("inside the producer window N+15..N+24, refuse", time.strftime("%H:%MZ", now))
PS = PRIV + "/producer_snapshot_1789200000"; os.makedirs(PS, exist_ok=True)
orig = {}
for l in open(SRC + "/SHA256SUMS.txt"):
    h, p = l.split(None, 1); orig[os.path.basename(p.strip())] = h
ps_rows = []
for f in ("aux.json", "leg_returns_live.json", "rolling.npz", "combo_live_status.json"):
    shutil.copy2(SRC + "/" + f, PS + "/" + f); h = sha(PS + "/" + f); assert h.startswith(orig[f]), (f, h[:16], orig[f]); ps_rows.append(f"{h}  {f}")
open(PS + "/SHA256SUMS.txt", "w").write("\n".join(ps_rows) + "\n")
S = PRIV + "/snapshot_live"; shutil.rmtree(S, ignore_errors=True)
for d in ("state/weights", "state/target_live_king", "state/target_combo", "state/target_live", "fea171"): os.makedirs(S + "/" + d, exist_ok=True)
core = [f"{W}/state/aux.json", f"{W}/state/leg_returns_live.json", f"{W}/state/rolling.npz", f"{W}/shadow_log.jsonl"]
la0 = json.load(open(core[0]))["last_anchor"]; mt0 = [os.stat(p).st_mtime_ns for p in core]
for p in core[:3]: shutil.copy2(p, S + "/state/" + os.path.basename(p))
shutil.copy2(core[3], S + "/shadow_log.jsonl")
la1 = json.load(open(core[0]))["last_anchor"]; mt1 = [os.stat(p).st_mtime_ns for p in core]
assert la0 == la1 and mt0 == mt1, ("live state changed during the copy", la0, la1)
LAST = int(json.load(open(S + "/state/aux.json"))["last_anchor"]); assert LAST == la0
ANCH = list(range(1789200000 + 14400, LAST + 1, 14400))
assert os.path.exists(f"{W}/state/target_live/{LAST}.json") and json.load(open(f"{W}/state/combo_live_status.json")).get("anchor") == LAST, "combo for the last anchor not finished"
for A in [1789200000] + ANCH: shutil.copy2(f"{W}/state/weights/{A}.npz", S + "/state/weights/")
for A in ANCH:
    for d in ("target_live_king", "target_combo", "target_live"):
        for suf in (".json", ".json.sha256"):
            p = f"{W}/state/{d}/{A}{suf}"
            if os.path.exists(p): shutil.copy2(p, f"{S}/state/{d}/")
            elif suf == ".json": raise AssertionError(p)
for t in ("f10", "kc", "fc"): shutil.copy2(f"{W}/fea171/state_H_{t}_1789200000.npz", S + "/fea171/")
rows = []
for root, _, files in os.walk(S):
    for f in files:
        if f == "SHA256SUMS.txt": continue
        rp = os.path.relpath(os.path.join(root, f), S); rows.append(f"{sha(os.path.join(root, f))}  ./{rp}")
open(S + "/SHA256SUMS.txt", "w").write("\n".join(sorted(rows, key=lambda r: r.split(None, 1)[1])) + "\n")
A_ = np.load(PS + "/rolling.npz", allow_pickle=True); B_ = np.load(S + "/state/rolling.npz", allow_pickle=True)
ta, tb = A_["ts"].astype(np.int64), B_["ts"].astype(np.int64); com = np.intersect1d(ta, tb); com = com[com <= 1789200000]
xa = A_["data"][np.searchsorted(ta, com)]; xb = B_["data"][np.searchsorted(tb, com)]
GATE_CACHE = dict(rows_compared=int(len(com)), first=time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(com[0]))), bitwise=bool(np.array_equal(xa, xb, equal_nan=True)),
                  cells_differ=int((~((xa == xb) | (np.isnan(xa.astype(np.float32)) & np.isnan(xb.astype(np.float32))))).sum()))
cfg = json.load(open(f"{W}/shadow_bundle/config.json")); syms = cfg["symbols_panel"]; live = set(cfg["symbols_live"]); LED = json.load(open(S + "/state/aux.json"))["ledger_tail"]
facts = []
for A in ANCH:
    m = np.load(f"{S}/state/weights/{A}.npz")["members"]; stale = 0; nonlive = 0
    for j in m:
        s = syms[int(j)]; nonlive += s not in live
        r = [x for x in LED.get(s, []) if int(x[0]) <= A]
        stale += (not r) or (A - int(r[-1][0]) > 12 * 3600)
    facts.append(dict(anchor=A, members=int(len(m)), stale_members=int(stale), nonlive_members=int(nonlive)))
RC = dict(self_sha256=sha(os.path.abspath(__file__)), frozen_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), producer_snapshot_copy=PS, producer_snapshot_sums=ps_rows,
          snapshot_live=S, snapshot_live_last_anchor=LAST, forward_anchors=ANCH, snapshot_live_sums_sha256=sha(S + "/SHA256SUMS.txt"), n_files=len(rows), gate_CACHE=GATE_CACHE, member_facts=facts,
          env=dict(whitelist=sorted(WHITE), actual={k: os.environ[k] for k in sorted(os.environ)}))
json.dump(RC, open(T4B + "/receipts/RECEIPT_T4b_freeze_inputs.json", "w"), indent=1, default=str); print(json.dumps({k: v for k, v in RC.items() if k not in ("env", "producer_snapshot_sums")}, indent=1, default=str))
assert GATE_CACHE["bitwise"], "GATE CACHE FAIL"
