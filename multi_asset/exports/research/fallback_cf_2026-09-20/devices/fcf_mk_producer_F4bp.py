#!/usr/bin/env python3
"""fcf_mk_producer_F4bp.py — make the F4b′ producer: rev24 removed from the book signal AND the masked seat renormalised over the two
surviving legs, exactly the way PRODUCTION itself removes rev24 from a king-shaped book.

WHY F4b′ EXISTS (read this before reading any F4b′ number). F4b — the literal reading of the prereg's "去 rev24 的 king 形态, 不改席位" —
is SELF-DEFEATING, and that was measured, not guessed:
  · the msharpe seat is 100 % rev24 (w3[0] + w3[2] == 0) on **172 of the 10,039 archived anchors (1.7 %)**: 2022 68, 2023 83, 2024 21,
    2025 0, 2026 0. At such an anchor the rev24-free signal is IDENTICALLY ZERO, so run_anchor returns at `if g < 1e-9` and writes nothing.
  · the FIRST such anchor is 2022-07-01T08:00:00Z (archived w3 = [0.0, 1.0, 0.0]). The producer only advances `st.prev_rec` and
    `st.last_anchor` when it WRITES, and the leg-return ledger only advances when `anchor − st.last_anchor == 14400` (L402). So one
    degenerate anchor freezes the ledger, which freezes the seat at [0, 1, 0], which makes every later anchor degenerate: an ABSORBING
    state. The F4b run wrote 907 books and then none — 0 of 2,190 anchors in 2023, 0 of 2,196 in 2024.
  · the 1.7 % is a genuine property of the counterfactual; the permanent freeze is an ARTEFACT of that code coupling (in a real
    rev24-free world the leg returns are still observable whether or not a book was written).

WHAT PRODUCTION ACTUALLY DOES when it removes rev24 from a king-shaped book — `combo_stage_replay_3520d363.py`, verbatim:
L232: w3m = np.array([w3[0], 0.0, w3[2]])
L233: w3m = w3m / w3m.sum() if w3m.sum() > 1e-12 else np.array([0.5, 0.0, 0.5])
L234: z_kc = w3m[0] * np.nan_to_num(legz["king"]) + w3m[2] * np.nan_to_num(legz["fund"])
It renormalises, and it has an explicit fallback for exactly the all-rev24 seat. That is why the kc component (arm F4a) never degenerates.
F4b′ copies those two production lines into the producer and changes nothing else — so F4b′ differs from F4a (= kc) ONLY by FTRIM, and
F4a − F4b′ measures the FTRIM contribution that confounds F4a.

THE INTERVENTION (`shadow_loop_v3_replay.py`), one line removed, two lines added, nothing else:
  L449  z = w3[0] * np.nan_to_num(legz["king"]) + w3[1] * np.nan_to_num(legz["rev24"]) + w3[2] * np.nan_to_num(legz["fund"])
becomes
  L449  w3m = np.array([w3[0], 0.0, w3[2]]); w3m = w3m / w3m.sum() if w3m.sum() > 1e-12 else np.array([0.5, 0.0, 0.5])
  L450  z = w3m[0] * np.nan_to_num(legz["king"]) + w3m[1] * np.nan_to_num(legz["rev24"]) + w3m[2] * np.nan_to_num(legz["fund"])
`w3` itself is NOT rebound, so everything downstream that reads w3 — including the logged seat at L528 that the S-SEAT assertion checks
against the archive — is untouched.

STRUCTURAL GATE (refuses to write unless all five hold):
  G1 source sha256 == the pinned production producer
  G2 the prefix src[:448] is byte-identical to dst[:448]
  G3 dst[448] and dst[449] are exactly the two expected lines
  G4 the suffix src[449:] is byte-identical to dst[450:] (so the only change is the replacement, everything after merely shifts by 1)
  G5 len(dst) == len(src) + 1, the output parses, REPLAY_META production_sha256 unchanged

usage: fcf_mk_producer_F4bp.py
"""
import ast, hashlib, json, os, sys, time

OBJB_DEV = "/workspace/object_b_2026-09-19/devices"
SRC = f"{OBJB_DEV}/shadow_loop_v3_replay.py"
OUT = "/workspace/fallback_cf_2026-09-20"
DST = f"{OUT}/devices/shadow_loop_v3_replay_F4bp.py"
LINE_NO = 449
BEFORE = '    z = w3[0] * np.nan_to_num(legz["king"]) + w3[1] * np.nan_to_num(legz["rev24"]) + w3[2] * np.nan_to_num(legz["fund"])\n'
AFTER1 = '    w3m = np.array([w3[0], 0.0, w3[2]]); w3m = w3m / w3m.sum() if w3m.sum() > 1e-12 else np.array([0.5, 0.0, 0.5])\n'
AFTER2 = '    z = w3m[0] * np.nan_to_num(legz["king"]) + w3m[1] * np.nan_to_num(legz["rev24"]) + w3m[2] * np.nan_to_num(legz["fund"])\n'
PIN_SRC = "4d3bc157f03e3462a69e64f817b3fd4cd51be4c03d72650304b7d0c1a0089d42"


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def main():
    rec = {"device": "fcf_mk_producer_F4bp.py", "self_sha256": sha(os.path.abspath(__file__)),
           "source": {"path": SRC, "sha256": sha(SRC)}, "pinned_production_sha256": PIN_SRC,
           "intervention": {"line": LINE_NO, "removed": BEFORE.rstrip("\n"), "added": [AFTER1.rstrip("\n"), AFTER2.rstrip("\n")],
                            "meaning": "the rev24 leg is removed from the book signal AND the masked seat is renormalised over the two "
                                       "surviving legs with production's own [0.5, 0, 0.5] fallback (combo_stage L232-233); w3 itself is "
                                       "NOT rebound, so the logged seat and every other consumer of w3 are untouched"},
           "why": "F4b (seat untouched) is degenerate: the seat is 100% rev24 on 172/10,039 anchors, and the producer's prev_rec/ledger "
                  "coupling turns the first such anchor into an absorbing state (no book from 2022-07-01T08:00:00Z onward)",
           "gates": [], "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    FAILS = []

    def g(name, ok, detail=None):
        rec["gates"].append(dict(gate=name, ok=bool(ok), detail=detail))
        print(("PASS " if ok else "FAIL ") + name, json.dumps(detail, default=str)[:240] if detail is not None else "", flush=True)
        if not ok: FAILS.append(name)

    g("G1.source_is_the_pinned_production_producer", sha(SRC) == PIN_SRC, dict(got=sha(SRC)[:16], want=PIN_SRC[:16]))
    src = open(SRC).readlines()
    g("G1b.line_449_is_the_expected_production_line", src[LINE_NO - 1] == BEFORE, dict(got=src[LINE_NO - 1].rstrip("\n")[:120]))
    if FAILS:
        json.dump(dict(rec, VERDICT="REFUSED", failed=FAILS), open(f"{OUT}/receipts/FCF_PRODUCER_F4bp.json", "w"), indent=1)
        print("FCF_PRODUCER_F4bp VERDICT=REFUSED failed=" + ",".join(FAILS), flush=True); sys.exit(3)

    dst = src[:LINE_NO - 1] + [AFTER1, AFTER2] + src[LINE_NO:]
    g("G2.prefix_byte_identical", src[:LINE_NO - 1] == dst[:LINE_NO - 1], dict(n_lines=LINE_NO - 1))
    g("G3.the_two_added_lines_are_exactly_the_expected_text", dst[LINE_NO - 1] == AFTER1 and dst[LINE_NO] == AFTER2)
    g("G4.suffix_byte_identical_shifted_by_one", src[LINE_NO:] == dst[LINE_NO + 1:], dict(n_lines=len(src) - LINE_NO))
    g("G5a.line_count", len(dst) == len(src) + 1, dict(src=len(src), dst=len(dst)))
    try:
        ast.parse("".join(dst)); ok = True; err = None
    except SyntaxError as e:
        ok = False; err = repr(e)
    g("G5b.output_parses", ok, err)
    g("G5c.REPLAY_META_production_sha256_unchanged",
      [l for l in src if "production_sha256" in l] == [l for l in dst if "production_sha256" in l])
    g("G5d.w3_is_not_rebound_the_logged_seat_is_untouched",
      sum(1 for l in dst if l.lstrip().startswith("w3 =")) == sum(1 for l in src if l.lstrip().startswith("w3 =")))
    if FAILS:
        json.dump(dict(rec, VERDICT="REFUSED", failed=FAILS), open(f"{OUT}/receipts/FCF_PRODUCER_F4bp.json", "w"), indent=1)
        print("FCF_PRODUCER_F4bp VERDICT=REFUSED failed=" + ",".join(FAILS), flush=True); sys.exit(3)

    with open(DST + ".tmp", "w") as f: f.writelines(dst)
    os.replace(DST + ".tmp", DST)
    rec["output"] = {"path": DST, "sha256": sha(DST)}
    rec["VERDICT"] = "PASS"; rec["failed"] = []
    json.dump(rec, open(f"{OUT}/receipts/FCF_PRODUCER_F4bp.json", "w"), indent=1)
    print("FCF_PRODUCER_F4bp VERDICT=PASS out_sha256=" + rec["output"]["sha256"], flush=True)


if __name__ == "__main__":
    main()
