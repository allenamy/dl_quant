#!/usr/bin/env python3
"""Append the member sets of anchors the producer never ran to state/members_hist.npz (lead 2026-09-26, fallback for the gap class fix:
09-26 12Z / 16Z never ran => combo_stage's f8 drank_*_1d are all 0 at 09-27 12Z / 16Z unless the history exists).
Needed ONLY if the gap-class-fix package (which recomputes missing history inside combo_stage) is not installed before 09-27 12Z.

RULE: members_rule.members_at (= shadow_loop_v3.py 52baf979 L676-L701 verbatim; V1 13/13 snapshots bitwise), on the CURRENT rolling cache,
fetch mask = aux.fetch_syms minus aux.nc_backfill_residual (the one in force now; V2: recompute mean Jaccard 0.9987).
ONLY APPENDS: existing anchors are never rewritten (asserted byte-for-byte), and generation.json is re-signed for members_hist.npz only.

FROZEN CRITERIA (written before any reading of the measurement arm; lead item (c)):
  check (fail-closed, every item named):
    C1 producer not running (launchctl label has no pid) — a running producer holds members_hist in memory and would overwrite the file
    C2 state generation committed: generation.json anchor == aux.last_anchor == aux.prev_rec.anchor_ts; every listed file's sha matches
    C3 axis: rolling data has len(symbols_panel) columns; crypto_axis symbols == symbols_panel; members_hist offsets consistent
    C4 every target T: on the 4 h grid, < aux.last_anchor, a row of the rolling ts, NOT already in members_hist (red: target exists),
       and the rolling cache holds data at T (>= 100 names with a finite ret5 in the 4 h ending at T)
    C5 POSITIVE CONTROL: members_at(C) for the control anchors (default: the two most recent recorded anchors) == recorded, bitwise;
       any difference => refuse (the rule / inputs are not the producer's)
    C6 member count: 50 <= n(T) <= NTOP and |n(T) - n(nearest recorded)| <= 10 (red: member count wrong)
  apply = check, then append, durable writes (tmp + fsync + read-back compare + os.replace) of members_hist.npz and generation.json,
          backups + receipt (sha of every written byte string comes from the verified write)
  verify = targets present and equal to the receipt's arrays; every pre-existing anchor byte-identical to the backup; generation.json
           members_hist sha == file sha and every other generation entry unchanged; feature_cache_identity.generation_ready(state, anchor)
  rollback = restore both files from the backup, only if both still carry the receipt's after-sha (else refuse: changed since)
usage: ~/wide_shadow/venv/bin/python members_hist_backfill.py {check|apply|verify|rollback} --targets T[,T] --receipt F
       [--state DIR] [--bundle DIR] [--fea DIR] [--controls C,C] [--producer-label L]"""
import argparse, hashlib, io, json, os, re, shutil, subprocess, sys, time
import numpy as np

HOME = os.path.expanduser("~"); H4 = 14400
u = lambda t: time.strftime("%m-%dT%H:%MZ", time.gmtime(t))
sha_b = lambda b: hashlib.sha256(b).hexdigest()
def sha(p):
    with open(p, "rb") as f: return sha_b(f.read())


def load_mh(p):
    with np.load(p) as m:
        an, off, idx = m["anchors"].astype(np.int64), m["off"].astype(np.int64), m["idx"]
        dt = {"anchors": m["anchors"].dtype, "off": m["off"].dtype, "idx": m["idx"].dtype}
    return an, off, idx, dt


def mh_dict(an, off, idx): return {int(an[k]): idx[off[k]:off[k + 1]] for k in range(len(an))}


def pack(d, dt):
    ks = sorted(d); off = np.concatenate([[0], np.cumsum([len(d[k]) for k in ks])])
    b = io.BytesIO(); np.savez(b, anchors=np.array(ks).astype(dt["anchors"]), off=off.astype(dt["off"]),
                              idx=(np.concatenate([d[k] for k in ks]) if ks else np.zeros(0)).astype(dt["idx"]))
    return b.getvalue()


def durable_replace(p, data):
    tmp = f"{p}.mhb_tmp.{os.getpid()}"
    with open(tmp, "xb") as f:
        f.write(data); f.flush(); os.fsync(f.fileno())
    with open(tmp, "rb") as f: back = f.read()
    if back != data:
        os.remove(tmp); raise IOError(f"read-back mismatch {tmp}")
    os.replace(tmp, p)
    d = os.open(os.path.dirname(p), os.O_RDONLY); os.fsync(d); os.close(d)
    return sha_b(back)


def inputs(a):
    sys.path.insert(0, a.fea)
    import nc_contract as NC, tradability as TR, members_rule as MR     # members_rule from --fea (the package's, or the device dir's copy)
    cfg = json.load(open(f"{a.bundle}/config.json")); P = cfg["params"]; syms = [str(s) for s in cfg["symbols_panel"]]
    cr = json.load(open(f"{a.bundle}/crypto_axis.json"))
    aux = json.load(open(f"{a.state}/aux.json"))
    with np.load(f"{a.state}/rolling.npz") as z: cts = z["ts"].astype(np.int64); cd = z["data"]
    return NC, TR, MR, P, syms, [str(s) for s in cr["symbols"]], np.array([bool(x) for x in cr["crypto"]], bool), aux, cts, cd


def check(a, T, C):
    bad = []
    rc = subprocess.run(["/bin/launchctl", "print", f"gui/{os.getuid()}/{a.producer_label}"], capture_output=True, text=True)
    if rc.returncode == 0 and re.search(r"^\s*pid = \d+", rc.stdout, re.M):
        bad.append(f"C1 producer {a.producer_label} is running (it holds members_hist in memory and would overwrite the file)")
    try:
        g = json.load(open(f"{a.state}/generation.json")); aux = json.load(open(f"{a.state}/aux.json"))
        if not (g.get("anchor_ts") == aux.get("last_anchor") == (aux.get("prev_rec") or {}).get("anchor_ts")):
            bad.append(f"C2 generation {g.get('anchor_ts')} / aux.last_anchor {aux.get('last_anchor')} / prev_rec disagree")
        for f, e in g["files"].items():
            if sha(f"{a.state}/{f}") != e["sha256"]: bad.append(f"C2 generation sha mismatch: {f}")
    except Exception as e:                                          # noqa: BLE001
        return bad + [f"C2 generation unreadable: {type(e).__name__}: {e}"], None
    NC, TR, MR, P, syms, crs, crypto, aux, cts, cd = inputs(a)
    an, off, idx, dt = load_mh(f"{a.state}/members_hist.npz"); MH = mh_dict(an, off, idx)
    if cd.shape[1] != len(syms): bad.append(f"C3 axis: rolling has {cd.shape[1]} columns, symbols_panel {len(syms)}")
    if crs != syms: bad.append("C3 axis: crypto_axis symbols != symbols_panel")
    if not (off[0] == 0 and off[-1] == len(idx) and np.all(np.diff(off) >= 0) and len(off) == len(an) + 1): bad.append("C3 members_hist offsets inconsistent")
    if any(x.startswith(("C2", "C3")) for x in bad): return bad, None      # structural: nothing below is meaningful; C1 alone does not hide C4-C6
    fm = MR.fetch_mask_from_aux(aux, syms); rows = {int(t): i for i, t in enumerate(cts)}
    got = {}
    for c in C:
        if c not in MH: bad.append(f"C5 control anchor {u(c)} has no recorded members"); continue
        m = MR.members_at(cts, cd, c, crypto, fm, P, TR, NC)
        if not np.array_equal(m, MH[c].astype(np.int64)):
            bad.append(f"C5 POSITIVE CONTROL FAILED at {u(c)}: recomputed {len(m)} vs recorded {len(MH[c])}, "
                       f"+{sorted(syms[i] for i in set(map(int, m)) - set(map(int, MH[c])))[:5]} -{sorted(syms[i] for i in set(map(int, MH[c])) - set(map(int, m)))[:5]}")
    for t in T:
        if t % H4: bad.append(f"C4 {t} not on the 4 h grid"); continue
        if t in MH: bad.append(f"C4 target {u(t)} already in members_hist (append-only; refusing)"); continue
        if t >= int(aux["last_anchor"]): bad.append(f"C4 target {u(t)} is not before the producer's last anchor {u(aux['last_anchor'])}"); continue
        if t not in rows: bad.append(f"C4 target {u(t)} is not a row of the rolling cache (axis not aligned / not backfilled)"); continue
        i = rows[t]; nfin = int(np.isfinite(np.asarray(cd[max(i - 47, 0):i + 1, :, 0], np.float32)).any(0).sum())
        if nfin < 100: bad.append(f"C4 target {u(t)}: only {nfin} names have ret5 data in the 4 h ending at T"); continue
        m = MR.members_at(cts, cd, t, crypto, fm, P, TR, NC)
        near = min(MH, key=lambda k: abs(k - t))
        if not (50 <= len(m) <= P["NTOP"]) or abs(len(m) - len(MH[near])) > 10:
            bad.append(f"C6 member count at {u(t)} = {len(m)} (NTOP {P['NTOP']}, nearest recorded {u(near)} = {len(MH[near])})"); continue
        got[t] = m
    return bad, {"got": got, "MH": MH, "dt": dt, "syms": syms}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["check", "apply", "verify", "rollback"])
    ap.add_argument("--targets", required=True); ap.add_argument("--receipt", required=True)
    ap.add_argument("--state", default=f"{HOME}/wide_shadow/state"); ap.add_argument("--bundle", default=f"{HOME}/wide_shadow/shadow_bundle")
    ap.add_argument("--fea", default=os.path.dirname(os.path.abspath(__file__)) + "/tree/fea171")
    ap.add_argument("--controls", default=None); ap.add_argument("--producer-label", default="com.hsy.shadowloop")
    a = ap.parse_args()
    sys.path.insert(0, f"{HOME}/wide_shadow/fea171")                      # nc_contract / tradability (production, read-only); members_rule from --fea
    sys.path.insert(0, a.fea)
    T = sorted(int(x) for x in a.targets.split(","))
    an, _, _, _ = load_mh(f"{a.state}/members_hist.npz")
    C = sorted(int(x) for x in a.controls.split(",")) if a.controls else sorted(int(x) for x in an)[-2:]
    print(f"MEMBERS_HIST_BACKFILL {a.cmd} targets={[u(t) for t in T]} controls={[u(c) for c in C]} state={a.state}")
    if a.cmd in ("check", "apply"):
        bad, res = check(a, T, C)
        for b in bad: print("  RED", b)
        if a.cmd == "check" or bad:
            print(f"MEMBERS_HIST_BACKFILL {a.cmd.upper()} {'PASS' if not bad else 'FAIL'}"); return 0 if not bad else 1
        if os.path.exists(a.receipt): print(f"MEMBERS_HIST_BACKFILL APPLY FAIL (receipt exists: {a.receipt})"); return 1
        bk = os.path.splitext(a.receipt)[0] + "_backup"; os.makedirs(bk)
        mp, gp = f"{a.state}/members_hist.npz", f"{a.state}/generation.json"
        shutil.copy2(mp, f"{bk}/members_hist.npz"); shutil.copy2(gp, f"{bk}/generation.json")
        before = {"members_hist": sha(mp), "generation": sha(gp)}
        d = dict(res["MH"]); d.update(res["got"]); raw = pack(d, res["dt"])
        chk = mh_dict(*load_mh(io.BytesIO(raw))[:3])
        assert all(np.array_equal(chk[k], res["MH"][k]) for k in res["MH"]) and set(chk) == set(res["MH"]) | set(res["got"]), "pack changed an existing entry"
        g = json.load(open(gp)); g2 = json.loads(json.dumps(g)); g2["files"]["members_hist.npz"]["sha256"] = sha_b(raw)
        graw = json.dumps(g2).encode()
        s_m = durable_replace(mp, raw); s_g = durable_replace(gp, graw)
        rec = {"device_sha256": sha(os.path.abspath(__file__)), "members_rule_sha256": sha(f"{a.fea}/members_rule.py"), "created_utc": u(time.time()),
               "state": a.state, "targets": {str(t): {"n": int(len(m)), "idx": [int(x) for x in m],
                                                       "names": [res["syms"][int(i)] for i in m]} for t, m in res["got"].items()},
               "controls": [u(c) for c in C], "backup": bk, "before": before, "after": {"members_hist": s_m, "generation": s_g}}
        with open(a.receipt, "x") as f: json.dump(rec, f, indent=1)
        bad = verify(a, rec)
        for b in bad: print("  RED", b)
        print(f"MEMBERS_HIST_BACKFILL APPLY {'PASS' if not bad else 'FAIL'} " + json.dumps({u(t): len(m) for t, m in res["got"].items()}))
        return 0 if not bad else 1
    rec = json.load(open(a.receipt)) if os.path.exists(a.receipt) else None
    if rec is None: print(f"MEMBERS_HIST_BACKFILL {a.cmd.upper()} FAIL (no receipt)"); return 1
    if a.cmd == "verify":
        bad = verify(a, rec)
        for b in bad: print("  RED", b)
        print(f"MEMBERS_HIST_BACKFILL VERIFY {'PASS' if not bad else 'FAIL'}"); return 0 if not bad else 1
    mp, gp = f"{a.state}/members_hist.npz", f"{a.state}/generation.json"
    if sha(mp) != rec["after"]["members_hist"] or sha(gp) != rec["after"]["generation"]:
        print("  RED members_hist.npz or generation.json changed since the backfill (the producer saved again?) — not restored")
        print("MEMBERS_HIST_BACKFILL ROLLBACK FAIL"); return 1
    durable_replace(mp, open(f"{rec['backup']}/members_hist.npz", "rb").read()); durable_replace(gp, open(f"{rec['backup']}/generation.json", "rb").read())
    ok = sha(mp) == rec["before"]["members_hist"] and sha(gp) == rec["before"]["generation"]
    print(f"MEMBERS_HIST_BACKFILL ROLLBACK {'PASS' if ok else 'FAIL'}"); return 0 if ok else 1


def verify(a, rec):
    bad = []
    mp, gp = f"{a.state}/members_hist.npz", f"{a.state}/generation.json"
    MH = mh_dict(*load_mh(mp)[:3]); OLD = mh_dict(*load_mh(f"{rec['backup']}/members_hist.npz")[:3])
    for t, e in rec["targets"].items():
        if int(t) not in MH or [int(x) for x in MH[int(t)]] != e["idx"]: bad.append(f"target {u(int(t))} missing or differs from the receipt")
    if set(MH) != set(OLD) | {int(t) for t in rec["targets"]}: bad.append("anchor set != backup + targets")
    for k, v in OLD.items():
        if not np.array_equal(MH.get(k), v): bad.append(f"pre-existing anchor {u(k)} changed")
    g, g0 = json.load(open(gp)), json.load(open(f"{rec['backup']}/generation.json"))
    if g["files"]["members_hist.npz"]["sha256"] != sha(mp): bad.append("generation.json members_hist sha != file sha")
    for f in g0["files"]:
        if f != "members_hist.npz" and g["files"].get(f) != g0["files"][f]: bad.append(f"generation entry {f} changed")
    if g.get("anchor_ts") != g0.get("anchor_ts"): bad.append("generation anchor changed")
    try:
        import feature_cache_identity as FCI
        if not FCI.generation_ready(a.state, int(g["anchor_ts"])): bad.append("feature_cache_identity.generation_ready is False")
    except Exception as e:                                          # noqa: BLE001
        bad.append(f"generation_ready raised {type(e).__name__}: {e}")
    return bad


if __name__ == "__main__":
    sys.exit(main())
