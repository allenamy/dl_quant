#!/usr/bin/env python3
"""ovn_old_hold.py — AMENDMENT 1 (docs/AMENDMENT_1_old_vs_new_models_same_engine_2026-09-23.md, 70adc6cac, sha 73336df6) arm OLD_HOLD:
the certified OLD targets (TARGETS_A0_main.npz b9f0dc9f) with every SCALED anchor of kind 1 (the producer's King-file fallback, incl. the one
known-crash anchor) rewritten as kind 0 with an EMPTY row = HOLD — exactly the encoding ovn_adapter.py writes for a NEW hold (no file ⇒ the
executor's on_unavailable = hold keeps the previous contract quantities). Every other array (anchor, scaled kind 2 / 0 rows, lit_*, scaled_l333_only_*)
is copied byte for byte.
Checks (each failure raises; nothing is written on failure):
  RT1 round trip: re-inserting the removed kind-1 rows at their anchors reproduces every array of the original OLD file bit for bit;
  RT2 per-segment HOLD counts written == the king_fallback counts of the pre-run disclosure (IDENTITY_DISCLOSURE item3 OLD_scaled);
  RT3 read back through the certified loader bt_objb_targets (05cc5dc2): on the certified window every non-hold row equals OLD's row bit for bit,
      every former kind-1 anchor is fresh = False with an empty row, and fresh(OLD_HOLD) = (kind(OLD) == 2).
usage: env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B ovn_old_hold.py PATH,HOME,LC_CTYPE <identity_disclosure.json> <out.npz> <out_receipt.json>
"""
import os, sys, json, time, hashlib, calendar, collections

import numpy as np

WL = set(sys.argv[1].split(",")); extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
IDJ, OUT_NPZ, OUT_R = sys.argv[2:5]
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bt_objb_targets as OT

H4 = 14400
SRC = {"npz": "/workspace/object_b_2026-09-19/work/A0_main/TARGETS_A0_main.npz", "npz_sha256": "b9f0dc9f2011f9defaac80b116415de3f4d75ffb497cbb9533cd995879036c41",
       "receipt": "/workspace/object_b_2026-09-19/receipts/TARGETS_A0_main.json", "receipt_sha256": "5ebac7205afc2cd0b5a0c85bd3daf2e2210e56dad9b0461fd015025cb4518385"}
SEG = {"2023H2": ("2023-06-30T04:00:00Z", "2023-12-31T20:00:00Z"), "2024": ("2024-01-01T00:00:00Z", "2024-12-31T20:00:00Z"),
       "2025": ("2025-01-01T00:00:00Z", "2025-12-31T20:00:00Z"), "2026 (report only)": ("2026-01-01T00:00:00Z", "2026-08-31T00:00:00Z")}
AMD = {"path": "docs/AMENDMENT_1_old_vs_new_models_same_engine_2026-09-23.md", "commit": "70adc6cac", "sha256": "73336df6d4d5568bffff6148d9d63b3139d7279407958537f1d93c4d5d18a854"}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def ts(iso): return calendar.timegm(time.strptime(iso, "%Y-%m-%dT%H:%M:%SZ"))
def iso(t): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(t)))


assert sha(os.path.join(HERE, "bt_objb_targets.py")) == "05cc5dc25df99459d93b34c9b10477f08002dd301b9b45ec6aa47bd77fc95373"
assert sha(SRC["npz"]) == SRC["npz_sha256"] and sha(SRC["receipt"]) == SRC["receipt_sha256"]
Z = np.load(SRC["npz"], allow_pickle=False); D = {k: Z[k] for k in Z.files}
A = D["anchor"].astype(np.int64); kind = D["scaled_kind"]; off = D["scaled_off"].astype(np.int64); idx = D["scaled_idx"]; val = D["scaled_val"]
k1 = np.nonzero(kind == 1)[0]
# ---- rewrite: kind 1 -> kind 0, row removed ----
keep = np.ones(len(idx), bool)
for i in k1: keep[off[i]:off[i + 1]] = False
rowlen = np.diff(off); rowlen_new = np.where(kind == 1, 0, rowlen)
off_new = np.concatenate([[0], np.cumsum(rowlen_new)]).astype(np.int64)
kind_new = np.where(kind == 1, 0, kind).astype(kind.dtype)
out = dict(D); out["scaled_kind"] = kind_new; out["scaled_off"] = off_new; out["scaled_idx"] = idx[keep]; out["scaled_val"] = val[keep]
out["old_hold_rewritten_from_kind1"] = (kind == 1)
# ---- RT1: put the kind-1 rows back, must reproduce the original arrays bit for bit ----
kb = kind_new.copy(); kb[k1] = 1; parts_i, parts_v, ob = [], [], [0]
for i in range(len(A)):
    if kind[i] == 1: ri, rv = idx[off[i]:off[i + 1]], val[off[i]:off[i + 1]]
    else: ri, rv = out["scaled_idx"][off_new[i]:off_new[i + 1]], out["scaled_val"][off_new[i]:off_new[i + 1]]
    parts_i.append(ri); parts_v.append(rv); ob.append(ob[-1] + len(ri))
ib = np.concatenate(parts_i); vb = np.concatenate(parts_v); ob = np.array(ob, np.int64)
rt1 = {"kind": bool(np.array_equal(kb, kind)), "off": bool(np.array_equal(ob, off)), "idx": bool(np.array_equal(ib, idx) and ib.dtype == idx.dtype),
       "val": bool(np.array_equal(vb.view(np.uint64), val.view(np.uint64))),
       "other_arrays_identical": all(np.array_equal(out[k], D[k]) for k in D if not k.startswith("scaled_") or k.startswith("scaled_l333_only_"))}
assert all(rt1.values()), ("RT1 round trip", rt1)
# ---- RT2: per-segment counts == the pre-run disclosure ----
IDD = json.load(open(IDJ)); disc = IDD["item3_gates"]["publishable_anchor_counts_per_segment"]["OLD_scaled"]
rt2 = {}
for s, (a, b) in SEG.items():
    m = (A >= ts(a)) & (A <= ts(b))
    rt2[s] = {"hold_written_from_kind1": int(np.sum((kind == 1) & m)), "disclosed_king_fallback": int(disc[s]["king_fallback"]),
              "combo_unchanged": int(np.sum((kind_new == 2) & m)), "disclosed_combo": int(disc[s]["combo_published"])}
    assert rt2[s]["hold_written_from_kind1"] == rt2[s]["disclosed_king_fallback"] and rt2[s]["combo_unchanged"] == rt2[s]["disclosed_combo"], ("RT2", s, rt2[s])
yr = collections.Counter(time.gmtime(int(t)).tm_year for t in A[k1])
tmp = OUT_NPZ[:-4] + ".tmp.npz"; np.savez(tmp, **out); os.replace(tmp, OUT_NPZ); s_npz = sha(OUT_NPZ)
R = {"tag": "TARGETS_OLD_HOLD", "arm": "OLD_HOLD", "data": "holefix2 (certified object B A0_main) with scaled kind-1 anchors rewritten as HOLD", "amendment": AMD,
     "source": SRC, "axis": [iso(A[0]), iso(A[-1])], "n_anchors": int(len(A)), "B_CORE_start": "2023-06-30T04:00:00Z", "PRE_window": None,
     "rewritten_anchors_total": int(len(k1)), "rewritten_by_year": {str(y): c for y, c in sorted(yr.items())}, "rt1_roundtrip_to_OLD_bitwise": rt1,
     "rt2_segment_counts_vs_disclosure": rt2, "disclosure": {"path": IDJ, "sha256": sha(IDJ)}, "device": "ovn_old_hold.py", "self_sha256": sha(os.path.abspath(__file__)),
     "utc": iso(time.time()), "targets_npz_sha256": s_npz,
     "note": "only the scaled reading is rewritten (the amendment's object); lit_* and scaled_l333_only_* are OLD's arrays unchanged, and no lit run is made for OLD_HOLD"}
json.dump(R, open(OUT_R + ".tmp", "w"), indent=1); os.replace(OUT_R + ".tmp", OUT_R)
# ---- RT3: certified loader ----
win = np.arange(ts("2022-06-30T00:00:00Z"), ts("2026-08-31T00:00:00Z") + 1, H4, dtype=np.int64)
To = OT.load_targets([SRC], reading="scaled", arm="A0"); Wo, fo, ko, co = OT.book_for_window(To, win)
Th = OT.load_targets([{"npz": OUT_NPZ, "npz_sha256": s_npz, "receipt": OUT_R, "receipt_sha256": sha(OUT_R)}], reading="scaled", arm="OLD_HOLD"); Wh, fh, kh, ch = OT.book_for_window(Th, win)
was1 = ko == 1
rt3 = {"fresh_equals_old_kind2": bool(np.array_equal(fh, ko == 2)), "former_kind1_empty": bool(np.abs(Wh[was1]).sum() == 0 and not fh[was1].any()),
       "other_rows_bitwise": bool(np.array_equal(Wh[~was1].view(np.uint64), Wo[~was1].view(np.uint64))), "loader_counts_old": co, "loader_counts_old_hold": ch,
       "window_former_kind1": int(was1.sum())}
assert rt3["fresh_equals_old_kind2"] and rt3["former_kind1_empty"] and rt3["other_rows_bitwise"], ("RT3", rt3)
R["rt3_certified_loader"] = rt3
json.dump(R, open(OUT_R + ".tmp", "w"), indent=1); os.replace(OUT_R + ".tmp", OUT_R)
assert sha(OUT_NPZ) == s_npz
print(f"OVN_OLD_HOLD VERDICT=PASS npz_sha256={s_npz} receipt_sha256={sha(OUT_R)} rewritten={len(k1)} window_rewritten={rt3['window_former_kind1']} "
      f"segments={ {s: v['hold_written_from_kind1'] for s, v in rt2.items()} } rt1=bitwise rt3=bitwise", flush=True)
