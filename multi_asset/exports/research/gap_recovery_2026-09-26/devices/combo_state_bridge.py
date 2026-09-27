#!/usr/bin/env python3
"""Carry the combo EMA state across anchors the producer never ran (host migration 2026-09-26: 12Z and 16Z not run).

WHY (read from the running code, combo_stage.py sha 12a76de8…): every previous-state lookup is keyed on EXACTLY A-14400
(L59 weights/<A-4h>.npz, L237-248 state_H_f10_<A-4h>, L311-318 state_H_kc/fc_<A-4h>). After a gap the lookup misses and the
fallback is a ZERO vector ⇒ smv = alpha*tgt ≈ 0.1× gross, most names under the band ⇒ the preflight `0.4 <= gross <= 1.2`
fails ⇒ COMBO_LIVE ABORT ⇒ the executor HOLDS; and because state_H_*_<A> is written BEFORE the abort, the next anchors
continue from the ~0.1× state and keep failing for ~5 anchors, then publish a cold-started book.

WHAT THIS DOES (state only, no code): writes state_H_{kc,fc,f10}_<T>.npz with anchor=T and idx/val BITWISE equal to the
last real state S (the 08Z files). Semantics = what was actually held: no anchor traded between S and T, the executor still
holds the S book, and the producer's own EMA state (aux.json st.H) is likewise carried from S unchanged. It does NOT write
state/weights/<T>.npz (stop_overlay.py globs that directory and would book a fake rebalance at T); consequence, named in
advance: at A=T+4h combo's step ① self-parity reads H=0 and reports a large max|Δw| (diagnostic only, not a publish gate).

Subcommands:  check | apply | verify | rollback   (--src S --dst T [--fea DIR] [--state DIR] --receipt FILE)
  check    : preconditions (fail-closed). T-S multiple of 4h and > 4h; no state_H_* for any anchor in (S, T]; sources exist with
             anchor==S; producer aux.json last_anchor == prev_rec.anchor_ts == S; combo_live_status anchor == S;
             combo_stage.py still carries the exact A-14400 predicates this bridge targets; now < T+4h+17min (combo start).
  apply    : check, then for each leg write via tmp + fsync + read-back byte compare + os.link (refuses to replace an
             existing file); receipt sha comes from the VERIFIED write (E-0925-A). Prints COMBO_STATE_BRIDGE APPLY PASS.
  verify   : read-only; each file satisfies combo's own predicate for A=T+4h and equals the source bitwise; sha == receipt.
  rollback : removes a bridged file only if its sha equals the receipt's.
"""
import argparse, hashlib, io, json, os, sys, time

import numpy as np

LEGS = ("kc", "fc", "f10")
PREDICATES = ('_load_state2(f"{HERE}/state_H_kc_{A-14400}.npz"', '_load_state2(f"{HERE}/state_H_fc_{A-14400}.npz"',
              'hf_prev = f"{HERE}/state_H_f10_{A - 14400}.npz"', 'if int(zz["anchor"]) == A - 14400:',
              'if int(zz2["anchor"]) == A - 14400:')


def u(t): return time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(t))


def path(fea, leg, a): return os.path.join(fea, f"state_H_{leg}_{a}.npz")


def payload(src_npz, dst):
    b = io.BytesIO(); np.savez(b, anchor=dst, idx=src_npz["idx"], val=src_npz["val"]); return b.getvalue()


def check(a, now=None):
    now = time.time() if now is None else now
    bad = []
    S, T = a.src, a.dst
    # rev 1 (2026-09-27, lead): the bridge is needed whenever the slot the NEXT combo reads (T = A-4h) has no real state, i.e. T > S.
    # rev 0 required T-S >= 8h (written for the 2-anchor gap of 09-26) and refused the 1-missed-anchor case (T-S = 4h) — instance-shaped.
    if S % 14400 or T % 14400 or T - S < 14400:
        bad.append(f"anchors: S={S} T={T} must be 4h-aligned with T > S (T == S means nothing is missing)")
    A = T + 14400
    if not (now < A + 17 * 60):
        bad.append(f"too late: now {u(now)} >= combo start {u(A + 17 * 60)} for A={u(A)}")
    if now < T:
        bad.append(f"too early: now {u(now)} < T {u(T)} (T is not yet a past anchor)")
    for leg in LEGS:
        sp = path(a.fea, leg, S)
        if not os.path.exists(sp):
            bad.append(f"source missing: {sp}")
        else:
            z = np.load(sp)
            if set(z.files) != {"anchor", "idx", "val"} or int(z["anchor"]) != S:
                bad.append(f"source {sp}: keys {sorted(z.files)} anchor {int(z['anchor']) if 'anchor' in z.files else None} != {S}")
        for k in range(S + 14400, T + 1, 14400):
            if os.path.exists(path(a.fea, leg, k)):
                bad.append(f"state already exists for an anchor inside the gap: {path(a.fea, leg, k)}")
    aux = json.load(open(os.path.join(a.state, "aux.json")))
    la, pa = aux.get("last_anchor"), (aux.get("prev_rec") or {}).get("anchor_ts")
    if not (la == S and pa == S):
        bad.append(f"producer aux: last_anchor={la} prev_rec.anchor_ts={pa} != S={S} (the producer ran since S: re-derive)")
    cls = json.load(open(os.path.join(a.state, "combo_live_status.json")))
    if cls.get("anchor") != S:
        bad.append(f"combo_live_status anchor {cls.get('anchor')} != S {S}")
    src = open(os.path.join(a.fea, "combo_stage.py")).read()
    miss = [p for p in PREDICATES if p not in src]
    if miss:
        bad.append(f"combo_stage.py no longer carries the targeted predicates: {miss}")
    return bad


def durable_create(p, data):
    if os.path.exists(p):
        raise FileExistsError(p)
    tmp = f"{p}.bridge_tmp.{os.getpid()}"
    with open(tmp, "xb") as f:
        f.write(data); f.flush(); os.fsync(f.fileno())
    with open(tmp, "rb") as f:
        back = f.read()
    if back != data:
        os.remove(tmp); raise IOError(f"read-back mismatch {tmp}")
    os.link(tmp, p)          # fails if p appeared meanwhile: never replaces
    os.remove(tmp)
    d = os.open(os.path.dirname(p), os.O_RDONLY); os.fsync(d); os.close(d)
    return hashlib.sha256(back).hexdigest()


def verify(a, rec):
    bad = []
    A = a.dst + 14400
    for leg in LEGS:
        p = path(a.fea, leg, a.dst)
        if not os.path.exists(p):
            bad.append(f"missing {p}"); continue
        raw = open(p, "rb").read(); sha = hashlib.sha256(raw).hexdigest()
        if rec and rec["files"][leg]["sha256"] != sha:
            bad.append(f"{leg}: sha {sha[:12]} != receipt {rec['files'][leg]['sha256'][:12]}")
        z = np.load(io.BytesIO(raw)); s = np.load(path(a.fea, leg, a.src))
        if not int(z["anchor"]) == A - 14400:            # combo's own predicate, evaluated for the next anchor
            bad.append(f"{leg}: anchor {int(z['anchor'])} fails combo predicate for A={A}")
        for k in ("idx", "val"):
            if z[k].dtype != s[k].dtype or z[k].shape != s[k].shape or z[k].tobytes() != s[k].tobytes():
                bad.append(f"{leg}: {k} differs from source")
        print(f"  {leg}: {os.path.basename(p)} sha {sha[:16]} n={len(z['idx'])} gross={float(np.abs(z['val']).sum()):.6f} "
              f"== source {os.path.basename(path(a.fea, leg, a.src))} bitwise: {not any(leg + ':' in b for b in bad)}")
    return bad


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["check", "apply", "verify", "rollback"])
    ap.add_argument("--src", type=int, required=True); ap.add_argument("--dst", type=int, required=True)
    ap.add_argument("--fea", default=os.path.expanduser("~/wide_shadow/fea171"))
    ap.add_argument("--state", default=os.path.expanduser("~/wide_shadow/state"))
    ap.add_argument("--receipt", required=True); a = ap.parse_args()
    print(f"COMBO_STATE_BRIDGE {a.cmd} S={u(a.src)} T={u(a.dst)} fea={a.fea}")
    if a.cmd == "check":
        bad = check(a)
        for b in bad: print("  RED", b)
        print(f"COMBO_STATE_BRIDGE CHECK {'PASS' if not bad else 'FAIL'}"); return 0 if not bad else 1
    if a.cmd == "apply":
        bad = check(a)
        for b in bad: print("  RED", b)
        if bad:
            print("COMBO_STATE_BRIDGE APPLY FAIL (preconditions)"); return 1
        if os.path.exists(a.receipt):
            print(f"COMBO_STATE_BRIDGE APPLY FAIL (receipt exists: {a.receipt})"); return 1
        rec = {"created_utc": u(time.time()), "src": a.src, "dst": a.dst, "fea": a.fea, "files": {},
               "combo_stage_sha256": hashlib.sha256(open(os.path.join(a.fea, "combo_stage.py"), "rb").read()).hexdigest()}
        written = []
        try:
            for leg in LEGS:
                s = np.load(path(a.fea, leg, a.src))
                data = payload(s, a.dst)
                sha = durable_create(path(a.fea, leg, a.dst), data); written.append(path(a.fea, leg, a.dst))
                rec["files"][leg] = {"path": path(a.fea, leg, a.dst), "sha256": sha,
                                     "src_sha256": hashlib.sha256(open(path(a.fea, leg, a.src), "rb").read()).hexdigest()}
        except Exception as e:                           # all-or-nothing
            for p in written: os.remove(p)
            print(f"COMBO_STATE_BRIDGE APPLY FAIL ({type(e).__name__}: {e}); removed {len(written)} partial file(s)"); return 1
        os.makedirs(os.path.dirname(os.path.abspath(a.receipt)), exist_ok=True)
        json.dump(rec, open(a.receipt, "x"), indent=1)
        bad = verify(a, rec)
        for b in bad: print("  RED", b)
        print(f"COMBO_STATE_BRIDGE APPLY {'PASS' if not bad else 'FAIL'}"); return 0 if not bad else 1
    rec = json.load(open(a.receipt)) if os.path.exists(a.receipt) else None
    if a.cmd == "verify":
        if rec is None:
            print("COMBO_STATE_BRIDGE VERIFY FAIL (no receipt)"); return 1
        bad = verify(a, rec)
        for b in bad: print("  RED", b)
        print(f"COMBO_STATE_BRIDGE VERIFY {'PASS' if not bad else 'FAIL'}"); return 0 if not bad else 1
    if a.cmd == "rollback":
        if rec is None:
            print("COMBO_STATE_BRIDGE ROLLBACK FAIL (no receipt)"); return 1
        n = 0; bad = []
        for leg in LEGS:
            p = rec["files"][leg]["path"]
            if not os.path.exists(p): continue
            if hashlib.sha256(open(p, "rb").read()).hexdigest() != rec["files"][leg]["sha256"]:
                bad.append(f"{p} changed since the bridge (not removed)"); continue
            os.remove(p); n += 1
        for b in bad: print("  RED", b)
        print(f"COMBO_STATE_BRIDGE ROLLBACK {'PASS' if not bad else 'FAIL'} removed={n}"); return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
