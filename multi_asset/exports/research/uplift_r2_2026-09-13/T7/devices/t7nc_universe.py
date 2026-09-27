#!/usr/bin/env python3
"""t7nc_universe.py — ZERO RETURNS. Builds U_NC per AMENDMENT_2_T7_NC_universe_2026-09-27 §1 on pod2 and writes it to tmpfs.
U_NC(i) = book_universe.align(pit)(i) & TRD-01 W24H(i) & crypto & members(i), the object news2_combo.py passes to the chain (L41-48 + members);
fallback for an anchor without a universe_ext row: combo s42 kc finite and != 0 (count reported; expected 0).
Only these keys are fetched: universe_ext {ts, pit, symbols}; TRD {ts, symbols, mask}; P1 {crypto}; NEWS_FEATURES {anchors, symbols, off, m};
legs {E_ts, symbols, KZ, ZFD}; combo s42 {E_ts, symbols, kc}. Reported per year: TRD, book_legal, LIVE, kc!=0 counts per anchor, kc!=0 outside LIVE
(must be 0), fallback anchors, and the AMENDMENT-2 §2 exclusions (LIVE cells where KZ or ZFD is not finite).
usage (pod2): /workspace/venv/bin/python -B t7nc_universe.py   -> /dev/shm/alloc_2026-09-26/t7nc/U_NC.npz + T7NC_UNIVERSE.json
"""
import os, sys, io, json, time, hashlib
import numpy as np
W = "/dev/shm/news2_2026-09-23"; OUTD = "/dev/shm/alloc_2026-09-26/t7nc"
PIN = {"universe": ("/workspace/object_b_2026-09-19/work/ext_inputs/universe_ext.npz", "3ee838cfc4ee4b90cef9202716af8645ff601b69137346d518ea706a5f4d598f"),
       "book_universe_py": (f"{W}/devices/book_universe.py", "90e332cc27cf8f34aabcac13f9829f84e463ffa900efbe554e17c07436e8dcca"),
       "trd": ("/workspace/axis_0919/x0918r/masks/member_mask_tradable_AND_live_W24H_cachegrid.npz", "f752d8ae3bf92f001fcb5d6f83a7e4ae286d9f11f7548c2e965305615aa9ae51"),
       "p1": (f"{W}/receipts/P1_members_2025H2on.npz", "2323623fda9333710f5834911ab629377ab8c12b056f40ccfc9f7033c0c1f6f1"),
       "features": (f"{W}/work/NEWS_FEATURES.npz", "3c886a2bc0ff65c10b7e0a621c9468210bbd77ef58c90e625f0a29354d63c4d8"),
       "legs": (f"{W}/work/legs.npz", "9ee5886f37d1727c306d0fb692d2cad1e6400ae13f19d5cd4e280dc59f208f65"),
       "combo_s42": (f"{W}/work/combo_s42/scaled_diagnostic.npz", "f4630a20f796bce26590aedeadfc28791be7eeecee8c14789f418b5a08de4388")}
ALLOWED = {"universe": {"ts", "pit", "symbols"}, "trd": {"ts", "symbols", "mask"}, "p1": {"crypto"}, "features": {"anchors", "symbols", "off", "m"},
           "legs": {"E_ts", "symbols", "KZ", "ZFD"}, "combo_s42": {"E_ts", "symbols", "kc"}}
UB = 1788120000   # 2026-08-30T20Z


def sha(p):
    h = hashlib.sha256(); n = 0
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): h.update(b); n += len(b)
    assert n == os.path.getsize(p) and n > 0; return h.hexdigest()


for k, (p, s) in PIN.items(): assert sha(p) == s, ("input sha", k)
FETCHED = {}
class G:
    def __init__(self, k): self.k = k; self.z = np.load(PIN[k][0], allow_pickle=False); FETCHED[k] = []
    def __getitem__(self, key): assert key in ALLOWED[self.k], ("key not allowed", self.k, key); FETCHED[self.k].append(key); return self.z[key]
sys.path.insert(0, f"{W}/devices"); from book_universe import align          # the in-service function itself (sha asserted above)
U, T, P1, F, L, Cb = G("universe"), G("trd"), G("p1"), G("features"), G("legs"), G("combo_s42")
a = F["anchors"].astype(np.int64); syms = F["symbols"]
ca = Cb["E_ts"].astype(np.int64); assert np.array_equal(np.asarray(Cb["symbols"]), np.asarray(syms))
assert np.array_equal(T["ts"].astype(np.int64), a) and np.array_equal(np.asarray(T["symbols"]), np.asarray(syms))
assert np.array_equal(L["E_ts"].astype(np.int64), a) and np.array_equal(np.asarray(L["symbols"]), np.asarray(syms))
pos = np.searchsorted(a, ca); assert np.array_equal(a[pos], ca)
ut = U["ts"].astype(np.int64); has_row = np.isin(ca, ut)
cand = T["mask"].astype(bool) & P1["crypto"].astype(bool)[None, :]
book_legal = np.zeros((ca.size, len(syms)), bool)
book_legal[has_row] = align(ca[has_row], syms, {"ts": ut, "pit": U["pit"], "symbols": U["symbols"]}) & cand[pos[has_row]]
off = F["off"]; m = F["m"]; live = np.zeros_like(book_legal)
for k, i in enumerate(pos):
    live[k, m[off[i]:off[i + 1]].astype(np.int64)] = True
live &= book_legal
kc = Cb["kc"]; kcnz = np.isfinite(kc) & (kc != 0)
Unc = live.copy(); Unc[~has_row] = kcnz[~has_row]                    # fallback (AMENDMENT-2 §1)
Bfin = np.isfinite(L["KZ"][pos]) & np.isfinite(L["ZFD"][pos])
keep = ca <= UB; yr = np.array([time.gmtime(int(t)).tm_year for t in ca])
rep = {"device": "t7nc_universe.py", "self_sha256": sha(os.path.abspath(__file__)), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "zero_returns": True,
       "inputs": {k: s for k, (p, s) in PIN.items()}, "fallback_anchors": int((~has_row).sum()), "fallback_anchors_eval": int((~has_row & keep).sum()),
       "kc_nonzero_outside_LIVE": int((kcnz & ~live).sum()), "per_year": {}}
assert rep["kc_nonzero_outside_LIVE"] == 0, rep["kc_nonzero_outside_LIVE"]
for y in (2023, 2024, 2025, 2026):
    s = (yr == y) & keep
    rep["per_year"][y] = {"anchors": int(s.sum()), "TRD": round(float(T["mask"][pos][s].sum(1).mean()), 1), "book_legal": round(float(book_legal[s].sum(1).mean()), 1),
                          "LIVE": round(float(live[s].sum(1).mean()), 1), "kc_nonzero": round(float(kcnz[s].sum(1).mean()), 1),
                          "U_NC": round(float(Unc[s].sum(1).mean()), 1), "U_NC_and_B_finite": round(float((Unc & Bfin)[s].sum(1).mean()), 1),
                          "excluded_cells_B_undefined": int((Unc & ~Bfin)[s].sum())}
rep["fetched_keys"] = FETCHED
os.makedirs(OUTD, exist_ok=True)
bio = io.BytesIO(); np.savez_compressed(bio, E_ts=ca, symbols=np.asarray(syms), U=Unc, B_finite=Bfin); blob = bio.getvalue()
rep["U_NC_sha256"] = hashlib.sha256(blob).hexdigest()
p = f"{OUTD}/U_NC.npz"
with open(p + ".tmp", "wb") as f: f.write(blob); f.flush(); os.fsync(f.fileno())
os.replace(p + ".tmp", p); assert sha(p) == rep["U_NC_sha256"]
rb = json.dumps(rep, indent=1).encode(); q = f"{OUTD}/T7NC_UNIVERSE.json"
with open(q + ".tmp", "wb") as f: f.write(rb); f.flush(); os.fsync(f.fileno())
os.replace(q + ".tmp", q); assert sha(q) == hashlib.sha256(rb).hexdigest()
print("T7NC_UNIVERSE DONE", rep["U_NC_sha256"][:16], hashlib.sha256(rb).hexdigest()[:16], flush=True)
