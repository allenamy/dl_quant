#!/usr/bin/env python3
"""Re-seed the live seat history ~/wide_shadow/state/leg_returns_live.json (user ruling via the lead 2026-09-26: implement and release).
Design: docs/DESIGN_reseed_live_leg_returns_2026-09-26.md (26ead03ce) + the lead's rulings:
  path (A) whole-file rebuild; every anchor the replay covers takes the replay value; after the replay end the live file's own
  entries are kept; the seam is asserted continuous BY TIMESTAMP; all n_keep (= 950) positions must carry a timestamped entry —
  one missing ⇒ STOP, never an equal-weight fallback.
Expected impact receipts: 27d04faa4 (seats) / 28d9f7496 (target layer: mean sum|dw| 5.7 %, ~5 flips).

TWO FACTS THE DESIGN'S §6 DID NOT HAVE (measured 2026-09-26 02:4xZ from the producer source; both change the deployment):
  (1) the producer holds the series IN MEMORY: ShadowState() is built once per process (shadow_loop_v3.py L914) and st.LR is loaded
      only there (L378-L381); every anchor re-saves the file from memory (L427-L429). A file replaced under a running producer is
      overwritten at its next save — the re-seed (and a rollback) only takes effect across a producer STOP → replace → START.
  (2) state/generation.json carries the sha256 of leg_returns_live.json (STATE_FILES, L257) and the loader refuses a mismatch
      (_read_verified_generation: "generation file hash mismatch"). The file cannot be replaced without re-issuing generation.json;
      this device re-issues it with the producer's OWN build_generation_record and verifies it with the producer's OWN
      _read_verified_generation (imported from the producer file, never re-implemented).

POSITION → ANCHOR IS MEASURED (the live file has no timestamps): consecutive per-anchor copies state/snap/<t>/leg_returns_live.json
are diffed; the append made while processing anchor t scores the PREVIOUS anchor (shadow_loop_v3.py L752-L766: prev_rec.anchor_ts ==
last_anchor and anchor - last_anchor == 14400), so it belongs to t - 14400. A step of k appends across a snapshot gap of exactly k
anchors assigns t - 14400*(k - j) (j = 1..k); any other combination is ambiguous ⇒ STOP. The live tail's last entry must belong to
aux.prev_rec.anchor_ts - 14400 with prev_rec.anchor_ts == aux.last_anchor == generation.anchor_ts ⇒ else STOP.

subcommands (every failure exits non-zero with a named STOP line; nothing is written by a failed build):
  build   --state D --snap D --legs NPZ --legs-sha SHA --producer PY --out DIR
  install --state D --build DIR --stamp UTCSTAMP --lock FILE --producer PY      (the producer must be STOPPED: lock absent or its pid dead)
  rollback --state D --stamp UTCSTAMP --lock FILE --producer PY
  seats   --file LEG_RETURNS_JSON --producer PY                                  (the frozen seat formula on the file's last `look` entries)
"""
import argparse, datetime, hashlib, importlib.util, json, math, os, re, shutil, sys

import numpy as np

STEP = 14400
LEGS = ("king", "rev24", "fund")


def sha_bytes(b): return hashlib.sha256(b).hexdigest()
def sha(p): return sha_bytes(open(p, "rb").read())
def u(t): return datetime.datetime.fromtimestamp(int(t), datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


def stop(msg, code=3):
    print(f"RESEED STOP: {msg}", flush=True); sys.exit(code)


def producer(path):
    """The producer module itself (import is side-effect free: measured). Its constants and functions are CALLED, not copied."""
    d = os.path.dirname(os.path.abspath(path))
    if d not in sys.path: sys.path.insert(0, d)
    spec = importlib.util.spec_from_file_location("reseed_producer_ref", path); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    src = open(path).read()
    hits = re.findall(r"^\s*n_keep = (\d+) \+ (\d+)\s*$", src, re.M)                  # the producer's own window constant
    if len(hits) != 1: stop(f"producer n_keep line matched {len(hits)} times, not 1")
    look_src, pad = int(hits[0][0]), int(hits[0][1])
    return m, look_src, pad


def bundle_look(prod_path):
    cfg = json.load(open(os.path.join(os.path.dirname(os.path.abspath(prod_path)), "shadow_bundle", "config.json")))
    return int(cfg["params"]["msharpe_look"])


def seats(window):
    """The frozen msharpe seat formula, shadow_loop_v3.py L784-L790 (== nc_legs.py L57-L61): window = LR dict of lists, len == look."""
    r = np.stack([np.array(window[leg]) for leg in LEGS])
    shp = r.mean(1) / (r.std(1) + 1e-9); shp = np.maximum(shp, 0.0)
    return shp / shp.sum() if shp.sum() > 0 else np.array([1 / 3] * 3)


def load_lr(p):
    d = json.load(open(p))
    if set(d) != set(LEGS) or len({len(d[l]) for l in LEGS}) != 1: stop(f"{p}: legs {sorted(d)} / unequal lengths")
    return {l: [float(x) for x in d[l]] for l in LEGS}


def measure_tail(snap_dir, state_dir, gen_anchor):
    """[(anchor_of_entry, (k, r, f))] for every entry appended between consecutive snapshots, plus the current file as a final
    observation at gen_anchor (it must EQUAL the snapshot of gen_anchor when that snapshot exists)."""
    obs = []
    for x in sorted(os.listdir(snap_dir)):
        if x.isdigit() and os.path.exists(os.path.join(snap_dir, x, "leg_returns_live.json")):
            obs.append((int(x), load_lr(os.path.join(snap_dir, x, "leg_returns_live.json"))))
    if not obs: stop("no snapshots")
    cur = load_lr(os.path.join(state_dir, "leg_returns_live.json"))
    if obs[-1][0] == gen_anchor:
        if obs[-1][1] != cur: stop(f"current leg_returns_live.json differs from the snapshot of its own anchor {u(gen_anchor)}")
    elif obs[-1][0] < gen_anchor:
        obs.append((gen_anchor, cur))
    else:
        stop(f"a snapshot ({u(obs[-1][0])}) is newer than generation.anchor_ts ({u(gen_anchor)})")
    assigned, steps = [], []
    for (t0, a), (t1, b) in zip(obs, obs[1:]):
        n = len(b["king"])
        k = next((k for k in range(0, 13) if all((b[l][:n - k] if k else b[l]) == a[l][k:] for l in LEGS)), None)
        if k is None: stop(f"cannot determine the append count {u(t0)} -> {u(t1)}")
        elapsed = (t1 - t0) // STEP
        if (t1 - t0) % STEP or k > elapsed or (k not in (0, elapsed)):
            stop(f"ambiguous step {u(t0)} -> {u(t1)}: {k} append(s) across {elapsed} anchor(s) — which anchors own them is not measured")
        steps.append({"from": u(t0), "to": u(t1), "anchors_elapsed": int(elapsed), "appended": int(k)})
        for j in range(k):                                    # the j-th (oldest first) of k appends belongs to t1 - STEP*(k - j)
            assigned.append((t1 - STEP * (k - j), tuple(b[l][n - k + j] for l in LEGS)))
    return assigned, steps, cur, len(obs)


def cmd_build(a):
    m, look_src, pad = producer(a.producer)
    look = bundle_look(a.producer)
    if look != look_src: stop(f"bundle msharpe_look {look} != producer n_keep look {look_src} (two constants that must agree)")
    n_keep = look_src + pad
    if os.path.exists(a.out): stop(f"refusing to overwrite {a.out}")
    # the replay (canonical legs.npz, sha pinned)
    if sha(a.legs) != a.legs_sha: stop(f"legs.npz sha {sha(a.legs)[:12]} != pinned {a.legs_sha[:12]}")
    Z = np.load(a.legs, allow_pickle=False); E = Z["E_ts"].astype(np.int64); LR = np.asarray(Z["LR"], np.float64)
    fin = np.isfinite(LR)
    if not np.array_equal(fin.all(1), fin.any(1)): stop("a replay row has some legs finite and others not")
    rep = [(int(E[i]), tuple(float(LR[i, j]) for j in range(3))) for i in range(len(E)) if fin[i].all()]
    if any(t % STEP for t, _ in rep) or any(y[0] <= x[0] for x, y in zip(rep, rep[1:])): stop("replay timestamps not strictly increasing 4h anchors")
    rep_end = rep[-1][0]
    # the live side: generation / aux / snapshots
    gen, _raw = m._read_verified_generation(a.state)                       # the producer's own verifier
    aux = json.load(open(os.path.join(a.state, "aux.json")))
    pr = aux.get("prev_rec") or {}
    if not (aux.get("last_anchor") == pr.get("anchor_ts") == gen["anchor_ts"]):
        stop(f"aux.last_anchor {aux.get('last_anchor')} / prev_rec.anchor_ts {pr.get('anchor_ts')} / generation {gen['anchor_ts']} disagree")
    assigned, steps, cur, n_obs = measure_tail(a.snap, a.state, gen["anchor_ts"])
    if not assigned: stop("no live entry could be assigned an anchor")
    if assigned[-1][0] != pr["anchor_ts"] - STEP:
        stop(f"the live tail's last entry belongs to {u(assigned[-1][0])}, not prev_rec.anchor_ts - 4h = {u(pr['anchor_ts'] - STEP)}")
    tail = [(t, v) for t, v in assigned if t > rep_end]
    if not tail: stop("no live entry beyond the replay end")
    if tail[0][0] != rep_end + STEP:
        stop(f"seam NOT continuous: replay ends {u(rep_end)}, first kept live entry {u(tail[0][0])} (gap {(tail[0][0] - rep_end) // 3600} h)")
    new = [x for x in rep if x[0] <= rep_end] + tail
    if any(y[0] <= x[0] for x, y in zip(new, new[1:])): stop("assembled timestamps not strictly increasing")
    if len(new) < n_keep:
        stop(f"only {len(new)} timestamped entries, {n_keep} positions required — NOT falling back to equal weights")
    win = new[-n_keep:]
    # the live tail kept verbatim must equal the current file's own last entries (same values the producer holds)
    k = len(tail)
    if [tuple(cur[l][len(cur['king']) - k + i] for l in LEGS) for i in range(k)] != [v for _, v in tail]:
        stop("kept live tail != the current file's last entries")
    doc = {leg: [float(v[j]) for _, v in win] for j, leg in enumerate(LEGS)}
    body = json.dumps(doc).encode()                                          # == the producer's atomic_json serialisation
    os.makedirs(a.out)
    open(os.path.join(a.out, "leg_returns_live.NEW.json"), "wb").write(body)
    if open(os.path.join(a.out, "leg_returns_live.NEW.json"), "rb").read() != body: stop("candidate read-back differs")
    gaps = {}
    for x, y in zip(win, win[1:]): gaps[(y[0] - x[0]) // STEP] = gaps.get((y[0] - x[0]) // STEP, 0) + 1
    rec = {"device_sha256": sha(os.path.abspath(__file__)), "producer_sha256": sha(a.producer), "look": look, "n_keep": n_keep,
           "inputs": {"legs_npz": {"path": a.legs, "sha256": a.legs_sha}, "live_file_sha256": sha(os.path.join(a.state, "leg_returns_live.json")),
                      "generation_sha256": sha(os.path.join(a.state, "generation.json")), "generation_anchor": u(gen["anchor_ts"]),
                      "aux_prev_rec_anchor": u(pr["anchor_ts"])},
           "position_to_anchor": {"observations": n_obs, "steps": steps}, "replay": {"entries": len(rep), "span": [u(rep[0][0]), u(rep_end)]},
           "seam": {"replay_end": u(rep_end), "first_live": u(tail[0][0]), "three_before": [[u(t), list(v)] for t, v in new[len(new) - k - 3:len(new) - k]],
                    "three_after": [[u(t), list(v)] for t, v in tail[:3]]},
           "window": {"n": len(win), "first": u(win[0][0]), "last": u(win[-1][0]), "n_replay": n_keep - k, "n_live_kept": k,
                      "gap_histogram_in_anchors": {str(g): c for g, c in sorted(gaps.items())}},
           "positions_anchor_ts": [t for t, _ in win],
           "seats_now": {"old_file": seats({l: cur[l][-look:] for l in LEGS}).tolist(), "new_file": seats({l: doc[l][-look:] for l in LEGS}).tolist(),
                         "note": "seats on each file's last `look` entries (what the NEXT anchor sees minus its own appended entry)"},
           "candidate_sha256": sha_bytes(body)}
    json.dump(rec, open(os.path.join(a.out, "BUILD.json"), "w"), indent=1)
    print(f"RESEED BUILD OK candidate_sha256={rec['candidate_sha256']} window {rec['window']['first']}..{rec['window']['last']} "
          f"replay {rec['window']['n_replay']} + live {k} seam {u(rep_end)}->{u(tail[0][0])} seats old={[round(x, 4) for x in rec['seats_now']['old_file']]} "
          f"new={[round(x, 4) for x in rec['seats_now']['new_file']]}")


def stopped_or_stop(lock):
    """The producer's own lock semantics (acquire_lock L40-L48, PID liveness only; no SIGTERM handler, so a stopped daemon leaves a
    stale file): the lock must be absent, or name a pid that is not alive."""
    if not os.path.lexists(lock): return "lock absent"
    try: pid = int(open(lock).read().strip())
    except (ValueError, OSError): stop(f"lock {lock} unreadable — refusing")
    try: os.kill(pid, 0)
    except ProcessLookupError: return f"stale lock (pid {pid} not alive)"
    except PermissionError: pass
    stop(f"producer lock {lock} names a LIVE pid {pid} — the producer must be STOPPED (it holds the series in memory)")


def cmd_install(a):
    m, _, _ = producer(a.producer)
    lock_state = stopped_or_stop(a.lock)
    rec = json.load(open(os.path.join(a.build, "BUILD.json")))
    live, gen = os.path.join(a.state, "leg_returns_live.json"), os.path.join(a.state, "generation.json")
    if sha(live) != rec["inputs"]["live_file_sha256"] or sha(gen) != rec["inputs"]["generation_sha256"]:
        stop("leg_returns_live.json or generation.json changed since the build — rebuild")
    g_old, _ = m._read_verified_generation(a.state)
    body = open(os.path.join(a.build, "leg_returns_live.NEW.json"), "rb").read()
    if sha_bytes(body) != rec["candidate_sha256"]: stop("candidate differs from its build record")
    bk = {p: f"{p}.pre_reseed_{a.stamp}" for p in (live, gen)}
    for p, b in bk.items():
        if os.path.lexists(b): stop(f"backup {b} exists")
        shutil.copy2(p, b)
        if open(b, "rb").read() != open(p, "rb").read(): stop(f"backup {b} read-back differs")
    m.atomic_write(live, body)                                               # the producer's own durable writer (atomic_json = atomic_write(json.dumps(obj).encode()))
    wrote = open(live, "rb").read()
    if wrote != body: stop("written leg_returns_live.json read-back != candidate (restore from the backups)", 4)
    new_gen = m.build_generation_record(a.state, g_old["anchor_ts"])        # the producer's own record builder, same anchor
    m.atomic_json(gen, new_gen)
    g2, raw2 = m._read_verified_generation(a.state)                          # the producer's own verifier
    if g2 != new_gen or g2["files"]["leg_returns_live.json"]["sha256"] != sha_bytes(wrote): stop("re-issued generation does not verify", 4)
    out = {"installed_utc": a.stamp, "producer_lock": lock_state, "backups": list(bk.values()), "leg_returns_live_sha256": sha_bytes(wrote),
           "generation_sha256": sha_bytes(raw2), "generation_anchor": u(g2["anchor_ts"])}
    json.dump(out, open(os.path.join(a.build, f"INSTALL_{a.stamp}.json"), "w"), indent=1)
    print(f"RESEED INSTALL OK leg_returns_live_sha256={out['leg_returns_live_sha256']} generation verified (anchor {out['generation_anchor']}) backups={out['backups']}")


def cmd_rollback(a):
    m, _, _ = producer(a.producer)
    lock_state = stopped_or_stop(a.lock)
    live, gen = os.path.join(a.state, "leg_returns_live.json"), os.path.join(a.state, "generation.json")
    for p in (live, gen):
        b = f"{p}.pre_reseed_{a.stamp}"
        if not os.path.exists(b): stop(f"backup {b} missing")
    for p in (live, gen):
        b = f"{p}.pre_reseed_{a.stamp}"; body = open(b, "rb").read()
        m.atomic_write(p, body)
        if open(p, "rb").read() != body: stop(f"{p} read-back != backup", 4)
    m._read_verified_generation(a.state)
    print(f"RESEED ROLLBACK OK restored bitwise from .pre_reseed_{a.stamp}; generation verifies — re-run the seat comparison after the next anchor")


def cmd_seats(a):
    look = bundle_look(a.producer); d = load_lr(a.file)
    if len(d["king"]) < look: stop(f"{len(d['king'])} < look {look} — refusing (the producer would fall back to equal weights)")
    print("RESEED SEATS " + json.dumps(seats({l: d[l][-look:] for l in LEGS}).tolist()))


def main():
    p = argparse.ArgumentParser(); s = p.add_subparsers(dest="cmd", required=True)
    b = s.add_parser("build"); [b.add_argument(x, required=True) for x in ("--state", "--snap", "--legs", "--legs-sha", "--producer", "--out")]
    i = s.add_parser("install"); [i.add_argument(x, required=True) for x in ("--state", "--build", "--stamp", "--lock", "--producer")]
    r = s.add_parser("rollback"); [r.add_argument(x, required=True) for x in ("--state", "--stamp", "--lock", "--producer")]
    q = s.add_parser("seats"); [q.add_argument(x, required=True) for x in ("--file", "--producer")]
    a = p.parse_args()
    {"build": cmd_build, "install": cmd_install, "rollback": cmd_rollback, "seats": cmd_seats}[a.cmd](a)


if __name__ == "__main__":
    main()
