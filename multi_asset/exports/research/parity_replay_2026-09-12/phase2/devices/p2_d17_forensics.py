#!/usr/bin/env python3
"""D17 non-blocking forensics (AMENDMENT 3, lead: after the S1 gates, read-only): where do the live ledger rows whose STORED settlement interval differs from the
interval implied by the settlement gap come from; date range and row counts; can the in-service producer create such rows again.
Evidence read (all READ-ONLY): producer snapshot 1789200000 aux.json (repo copy, 5e825c2f…); ~/wide_shadow/shadow_bundle.aug20260816_backup/funding_ledger_seed.json
(08-16 bundle seed); ~/wide_shadow/shadow_bundle/funding_ledger_seed.json (09-01 v3 bundle seed); ~/wide_shadow/state/aux_pre_m1_20260904.json (pre-M1 state backup);
the append logic of every producer version on disk (shadow_loop.py / _v2 / _v3 backups / live e9c98374…). Writes only the receipt given as argv[1].
usage: /usr/bin/python3 -B p2_d17_forensics.py <out.json>"""
import json, sys, os, time, hashlib, re
OUT = sys.argv[1]; assert "/parity_replay_2026-09-12/phase2/receipts/" in os.path.abspath(OUT)
H = os.path.expanduser("~")
REPO = "/Users/haosiyu/Desktop/quant_research"
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
def iso(t): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(t)))
ALLOWED = [1.0, 2.0, 4.0, 6.0, 8.0]
def snap_iv(gap_s):
    iv = gap_s / 3600.0
    return float(min(ALLOWED, key=lambda a: abs(a - (iv if 0 < iv <= 24 else 8.0))))
SRC = {"snapshot_1789200000_aux": f"{REPO}/multi_asset/exports/live/producer_state_snapshots/1789200000/aux.json",
       "seed_2026-08-16": f"{H}/wide_shadow/shadow_bundle.aug20260816_backup/funding_ledger_seed.json",
       "seed_2026-09-01_v3": f"{H}/wide_shadow/shadow_bundle/funding_ledger_seed.json",
       "aux_pre_m1_2026-09-04": f"{H}/wide_shadow/state/aux_pre_m1_20260904.json"}
R = {"device": os.path.abspath(__file__), "self_sha256": sha(os.path.abspath(__file__)), "inputs": {k: {"path": p, "sha256": sha(p), "mtime_utc": iso(os.stat(p).st_mtime)} for k, p in SRC.items()}}
aux = json.load(open(SRC["snapshot_1789200000_aux"])); LED = aux["ledger_tail"]
s16 = json.load(open(SRC["seed_2026-08-16"])); s01 = json.load(open(SRC["seed_2026-09-01_v3"])); pm1 = json.load(open(SRC["aux_pre_m1_2026-09-04"]))["ledger_tail"]
def rowmap(rows): return {int(r[0]): (float(r[1]), (float(r[2]) if len(r) > 2 and r[2] is not None else None)) for r in rows}
A0 = 1788624000
names = {}
for s, rows in LED.items():
    mis = []
    for k in range(1, len(rows)):
        r = rows[k]
        if int(r[0]) > A0 - 14400: continue
        g = snap_iv(int(r[0]) - int(rows[k - 1][0]))
        if g != float(r[2]): mis.append((int(r[0]), float(r[1]), float(r[2]), g))
    if not mis: continue
    m16 = rowmap(s16.get(s, [])); m01 = rowmap(s01.get(s, [])); mpm = rowmap(pm1.get(s, []))
    def where(t, stored):
        out = {}
        for tag, mp in (("seed_08-16", m16), ("seed_09-01", m01), ("aux_pre_m1", mpm)):
            v = mp.get(t); out[tag] = None if v is None else ("same_iv" if v[1] == stored else f"iv={v[1]}")
        return out
    cls = {}
    for t, rate, stored, g in mis:
        key = json.dumps(where(t, stored), sort_keys=True); cls[key] = cls.get(key, 0) + 1
    seed16_rows = sorted(m16); seed01_rows = sorted(m01)
    names[s] = {"n_rows_stored_iv_ne_gap_iv": len(mis), "first": iso(mis[0][0]), "last": iso(mis[-1][0]), "stored_iv_values": sorted({m[2] for m in mis}), "gap_iv_values": sorted({m[3] for m in mis}),
                "presence_classes": cls, "seed_08-16_row_range": [iso(seed16_rows[0]), iso(seed16_rows[-1])] if seed16_rows else None,
                "seed_09-01_row_range": [iso(seed01_rows[0]), iso(seed01_rows[-1])] if seed01_rows else None, "live_ledger_first_row": iso(rows[0][0]), "examples": [[iso(m[0]), m[1], m[2], m[3]] for m in mis[:5]]}
R["names"] = names; R["n_names"] = len(names)
# producer append logic across versions (the only code path that writes ledger rows after bootstrap)
vers = {}
for f in ("shadow_loop.py", "shadow_loop_v2.py", "shadow_loop_v3.py.bak_predemeanfix", "shadow_loop_v3.py.pre_m1_20260904_backup", "shadow_loop_v3.py"):
    p = f"{H}/wide_shadow/{f}"; src = open(p).read()
    lines = [l.strip() for l in src.splitlines() if re.search(r"iv = \(ft - led\[-1\]\[0\]\) / 3600\.0 if led else 8\.0", l)]
    boot = [l.strip() for l in src.splitlines() if "funding_ledger_seed.json" in l]
    vers[f] = {"sha256": sha(p), "append_iv_from_gap_lines": lines, "bootstrap_seed_lines": boot}
R["producer_versions"] = vers
json.dump(R, open(OUT, "w"), indent=1)
print("D17_FORENSICS_DONE", len(names), "names", json.dumps({s: (v["n_rows_stored_iv_ne_gap_iv"], v["first"], v["last"], v["presence_classes"]) for s, v in names.items()})[:3000])
