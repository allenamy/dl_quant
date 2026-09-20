#!/usr/bin/env python3
"""fcf_rechain_F4bp.py — the F4b′ counterfactual RE-CHAIN: the object-B producer chain re-run from the same cold start with the rev24 leg
removed from the book signal AND the masked seat renormalised over the two surviving legs exactly the way PRODUCTION itself
does it (combo_stage_replay_3520d363.py L232-233), recording the king target file at every anchor.
F4b′ exists because F4b (seat untouched) is SELF-DEFEATING; fcf_mk_producer_F4bp.py's docstring carries the measured reason.

WHY A RE-CHAIN AND NOT A PER-ANCHOR ARITHMETIC. The producer's book is a stateful recursion (shadow_loop_v3_replay.py run_anchor step 8:
demean -> L1 -> cap -> EMA alpha -> deadband -> forced exit -> st.H, carried to the next anchor), so "the king book without rev24" is not a
function of one anchor's inputs. ERROR_LEDGER E-0920-B's own correction says so: "正解 = 反事实重链(整窗从同一播种起点重跑, 不是逐锚扰动)".

THE INTERVENTION is one line removed and two added, proved by fcf_mk_producer_F4bp.py (receipt FCF_PRODUCER_F4bp.json, gates G1-G5)
BEFORE this ran: prefix and suffix of the producer byte-identical, and w3 itself never rebound:
  L449  z = w3[0]*nan_to_num(legz["king"]) + w3[1]*nan_to_num(legz["rev24"]) + w3[2]*nan_to_num(legz["fund"])
  ->    z = w3[0]*nan_to_num(legz["king"]) + 0.0    *nan_to_num(legz["rev24"]) + w3[2]*nan_to_num(legz["fund"])
Nothing else in the producer, the data, the universe, the booster or the F10 folds changes.

TWO ARCHIVE IDENTITIES THIS RUN RELIES ON, both checked bitwise on all 10,039 archived anchors before it was written (work/probe2.py):
  I1  the producer's state evolution is IDENTICAL in P1 mode (producer only) and P3 mode (producer + combo): P1's prev_rec sm/sm_idx
      equals P3's st.H filtered at 1e-9, on every anchor, 0 mismatches. So a P1-mode re-chain gives the producer state a P3-mode re-chain
      would give, and the combo stage (which runs in a forked child and cannot touch the parent's state) need not be re-run.
  I2  the king FILE the executor reads is st.H filtered at |.| > 1e-9 and != 0: P3's king_file equals that filter of P3's king on every
      anchor, 0 mismatches. This device nevertheless records the REAL file that the producer's own write_target_live wrote, parsed by
      b_lib.target_weights — the production path, not the identity.

THE TWO-SIDED STRUCTURAL ASSERTION (run at the end; a failure REFUSES the output):
  S-IDENTICAL   everything upstream of L449 must be BITWISE identical to the archived P1 run: the member sets pm, the three leg z-vectors
                legz, and the funding EMA / last-rate state vectors fe, fn, on every anchor. This is the proof that the seat w3 is
                unchanged (w3 is built only from legz and the cache, L410-416 / L434-437) and that the harness is faithful.
  S-DIFFERENT   the book sm must actually DIFFER on a large share of anchors. A re-chain whose book is identical would mean the switch was
                never wired ("零差 = 开关没接上").
  S-SEAT        the producer's own logged w3 must equal the archive's logged w3 at every anchor, to the 4 decimals the producer logs.

usage: env -i PATH=/usr/bin:/bin HOME=/root LC_CTYPE=C.UTF-8 OBJB_ROOT=... OBJB_ARM=A0 OBJB_DATA=holefix2 \
         /workspace/venv/bin/python -B fcf_rechain_F4bp.py PATH,HOME,LC_CTYPE,OBJB_ROOT,OBJB_ARM,OBJB_DATA
"""
import hashlib, importlib, json, os, sys, time

import numpy as np

WL = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else set()
assert WL, "env whitelist (argv[1]) must be non-empty"
extra = sorted(set(os.environ) - WL)
assert not extra, f"env outside whitelist: {extra}"          # E-0826-D: the whole environment is declared
for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[k] = "1"; WL.add(k)

OUT = "/workspace/fallback_cf_2026-09-20"
HERE = os.path.dirname(os.path.abspath(__file__))
OBJB_DEV = "/workspace/object_b_2026-09-19/devices"
sys.path.insert(0, OBJB_DEV)
import b_lib as BL
import b_driver as BD

T0 = time.time()
ARCH_P1 = "/workspace/object_b_2026-09-19/work/A0_main/P1.vec.npz"
ARCH_P1J = "/workspace/object_b_2026-09-19/work/A0_main/P1.json"
RH = f"{OUT}/work/rh_F4bp"
PREFIX = f"{OUT}/work/F4bp_P1"
KING = {"anchor": [], "king_file": [], "king": [], "w3": []}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def import_producer_F4b(rh):
    """the ONLY patch to the object-B driver: import the one-line-changed producer instead of the pinned one.
    Every other assertion b_driver.import_producer makes is kept, including REPLAY_META's production sha."""
    os.environ["WIDE_SHADOW_HOME"] = rh
    os.environ.setdefault("WIDE_SHADOW_BUNDLE", "/workspace/shadow_bundle_v3")
    sys.path.insert(0, HERE)
    dev = importlib.import_module("shadow_loop_v3_replay_F4bp")
    assert dev.STATE_DIR == f"{rh}/state" and dev.HOME == rh, (dev.STATE_DIR, dev.HOME)
    assert dev.REPLAY_META["production_sha256"] == "e9c9837412130884bc72d4bbcb52b33e9dc8660274b76ae68f46639d2d21b36e"
    assert sha(f"{HERE}/shadow_loop_v3_replay_F4bp.py") == PRODUCER_SHA, "the F4b′ producer is not the one the structural gate signed"
    return dev


_orig_step = BD.producer_step


def producer_step_rec(dev, st, fx, cfg, booster, A, rh):
    """b_driver.producer_step, then record THIS anchor's king target FILE before the driver prunes it — the same read
    b_driver.combo_outcome L252 does: king_w = BL.target_weights(kf)[1] if os.path.exists(kf) else None"""
    wrote, sig, skip = _orig_step(dev, st, fx, cfg, booster, A, rh)
    if wrote:
        kf = f"{rh}/state/target_live/{A}.json"
        king_w = BL.target_weights(kf)[1] if os.path.exists(kf) else None
        KING["anchor"].append(int(A))
        KING["king_file"].append(BD.sparse(king_w, GCOL))
        nzk = np.where(np.abs(st.H) > 1e-12)[0]
        KING["king"].append((nzk.astype(np.int16), st.H[nzk].astype(np.float64)))
        KING["w3"].append((sig or {}).get("w3"))
    return wrote, sig, skip


if __name__ == "__main__":
    PRODUCER_SHA = json.load(open(f"{OUT}/receipts/FCF_PRODUCER_F4bp.json"))["output"]["sha256"]
    prod_rec = json.load(open(f"{OUT}/receipts/FCF_PRODUCER_F4bp.json"))
    assert prod_rec["VERDICT"] == "PASS", "the F4b producer's structural gate did not pass"
    os.makedirs(RH, exist_ok=True)
    G = BD.Globals(load_cache=True)
    GCOL = G.col
    A_FIRST, A_LAST = 1643587200, 1788480000   # 2022-01-31T00:00:00Z .. 2026-08-31T00:00:00Z: the archived A0_main axis, asserted below
    anchors = [int(x) for x in G.U_ts if A_FIRST <= int(x) <= A_LAST]
    arch_axis = np.load(ARCH_P1)["anchor"].astype(np.int64)
    assert np.array_equal(np.array(anchors, np.int64), arch_axis), "the re-chain axis must be the archived P1 axis, anchor for anchor"
    SMOKE = int(sys.argv[2]) if len(sys.argv) > 2 else 0     # smoke only: first N anchors, outputs go to a *_smoke prefix
    if SMOKE:
        anchors = anchors[:SMOKE]; RH = RH + "_smoke"; PREFIX = PREFIX + "_smoke"; os.makedirs(RH, exist_ok=True)
        print("SMOKE run:", SMOKE, "anchors — NOT a result", flush=True)
    print("F4b rechain anchors", len(anchors), BL.iso(anchors[0]), BL.iso(anchors[-1]), "load", round(time.time() - T0, 1), "s", flush=True)
    BD.import_producer = import_producer_F4b
    BD.producer_step = producer_step_rec
    BD.run_chain("P1", G, anchors, RH, PREFIX)
    off = np.concatenate([[0], np.cumsum([len(v[0]) for v in KING["king_file"]])]).astype(np.int64)
    offk = np.concatenate([[0], np.cumsum([len(v[0]) for v in KING["king"]])]).astype(np.int64)
    out = {"anchor": np.array(KING["anchor"], np.int64),
           "king_file_off": off, "king_file_idx": np.concatenate([v[0] for v in KING["king_file"]]).astype(np.int16),
           "king_file_val": np.concatenate([v[1] for v in KING["king_file"]]),
           "king_off": offk, "king_idx": np.concatenate([v[0] for v in KING["king"]]).astype(np.int16),
           "king_val": np.concatenate([v[1] for v in KING["king"]])}
    p = f"{OUT}/work/F4bp_KING{'_smoke' if SMOKE else ''}.npz"
    np.savez_compressed(p + ".tmp.npz", **out); os.replace(p + ".tmp.npz", p)
    json.dump({"anchor": KING["anchor"], "w3": KING["w3"]}, open(f"{OUT}/work/F4bp_w3{'_smoke' if SMOKE else ''}.json", "w"))
    rec = {"device": "fcf_rechain_F4bp.py", "self_sha256": sha(os.path.abspath(__file__)),
           "producer": {"path": f"{HERE}/shadow_loop_v3_replay_F4bp.py", "sha256": PRODUCER_SHA,
                        "gate_receipt_sha256": sha(f"{OUT}/receipts/FCF_PRODUCER_F4bp.json"), "intervention": prod_rec["intervention"]},
           "b_driver_sha256": sha(f"{OBJB_DEV}/b_driver.py"), "b_lib_sha256": sha(f"{OBJB_DEV}/b_lib.py"),
           "patched": ["b_driver.import_producer -> import_producer_F4b (imports the one-line-changed producer)",
                       "b_driver.producer_step -> producer_step_rec (records this anchor's king file; calls the original first)"],
           "env": dict(os.environ), "inputs_sha256": G.shas, "anchors": [BL.iso(anchors[0]), BL.iso(anchors[-1]), len(anchors)],
           "outputs": {"king_npz": p, "king_npz_sha256": sha(p), "p1_json": PREFIX + ".json", "p1_vec": PREFIX + ".vec.npz",
                       "p1_vec_sha256": sha(PREFIX + ".vec.npz")},
           "runtime_s": round(time.time() - T0, 1), "python": sys.version.split()[0], "numpy": np.__version__,
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    rec["smoke_n_anchors"] = SMOKE or None
    json.dump(rec, open(f"{OUT}/receipts/FCF_RECHAIN_F4bp{'_smoke' if SMOKE else ''}.json", "w"), indent=1)
    print("FCF_RECHAIN_F4bp DONE runtime=%.0fs n_recorded=%d king_npz_sha256=%s" % (rec["runtime_s"], len(KING["anchor"]), rec["outputs"]["king_npz_sha256"]), flush=True)
