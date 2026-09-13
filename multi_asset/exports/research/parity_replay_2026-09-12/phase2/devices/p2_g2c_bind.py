#!/usr/bin/env python3
"""G2-C-BIND — PREREG_producer_parity_phase2_oos_2026-09-12 AMENDMENT 7 §A7.2 (file sha 35ea8761…, commit 5146689c).
Binds the G2-C bundle of receipt 4 to its frozen slots and populations (independent reviewer 9dc41644 §5.3 gap + lead additions 4/5):
  B1 slot<->anchor (s12/s16/s20 -> 1789214400/1789228800/1789243200), canonical receipt paths, recorded sha == disk, three distinct anchors
  B2 exactly one anchor per snapshot receipt, anchor == slot, mode snapshot, snapshot dir == work/snapshots/{A-4h}
  B3 prep / input identity (prep run fields, rolling/aux shas vs prep and disk, device/production shas, dev copies, rc lines, prep sha)
  B4 snapshot start state is A-4h (snapshot aux last_anchor, SHA256SUMS of present files, fake-home state_H_{f10,kc,fc}_{A-4h} anchor fields,
     weights/{A-4h} present, hybrid rolling last ts == A == prep hybrid_ts_last)
  B5 file anchors (producer target_live / target_combo, replay target_live_combo / target_combo: anchor_ts == A)
  B6 population: compared name sets == producer name sets, receipt counts == set sizes, L-inf recomputed == receipt (combo target_live, target_combo;
     king weights/{A} non-zero idx sets and king target_live JSON names at the snapshot anchors)
  B7 king chain 41 anchors: frozen anchor list, prep fields, rolling sha, per-anchor king member-set binding and L-inf == receipt == judge, <= 1e-6 re-judged
  B8 red capability: mutated bundles M1-M6 built ONLY under work/g2c_bind_mutants must each read RED for their named reason; the real bundle must PASS
  B9 judge verdict field reads PASS
The real receipts are read-only (their sha256 are taken before and after and must be unchanged). Writes receipts/G2C_BIND.json; one G2C_BIND line; exit 0 iff PASS.
usage: env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B p2_g2c_bind.py PATH,HOME,LC_CTYPE"""
import os, sys, json, time, hashlib, copy, calendar, traceback
WL = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else set()
assert WL, "env whitelist (argv[1]) must be non-empty"
extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
import numpy as np
P2 = "/workspace/uplift_r2_2026-09-13/P2"; W = P2 + "/work"; RC = P2 + "/receipts"; MUT = W + "/g2c_bind_mutants"
PREREG_SHA = "35ea8761dba442d153b1e0af6268c3fc25c1190157fcebb13c9d75d5936af588"
SLOTS = {"s12": (1789214400, "12"), "s16": (1789228800, "16"), "s20": (1789243200, "20")}
CHAIN = [1788624000 + 14400 * k for k in range(41)]
DEV = {"replay_driver.py": "f2ced820daa45e0fec0879b6eaeba58905109b60dc0ac09a6e5b0d7cd1bee4ec", "combo_stage_replay.py": "f5ba9a8234ef0c01ee1aa5bdb0ebd87e8e7093c10b164e37f4fc10f97bc7f77b",
       "shadow_loop_v3_replay.py": "4d3bc157f03e3462a69e64f817b3fd4cd51be4c03d72650304b7d0c1a0089d42"}
DEVICE_SHA = "4d3bc157f03e3462a69e64f817b3fd4cd51be4c03d72650304b7d0c1a0089d42"; PRODUCTION_SHA = "e9c9837412130884bc72d4bbcb52b33e9dc8660274b76ae68f46639d2d21b36e"
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 22), b""): h.update(ch)
    return h.hexdigest()
def iso(t): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(t)))
def last_line(p):
    ls = [l.strip() for l in open(p, errors="replace") if l.strip()]; return ls[-1] if ls else ""
def nz_set(npz):
    z = np.load(npz); idx = z["idx"].astype(np.int64); val = z["val"]; return set(int(i) for i, v in zip(idx, val) if float(v) != 0.0), z
def dense(z):
    a = np.zeros(829); a[z["idx"].astype(int)] = z["val"].astype(np.float64); return a
T0 = time.time(); SELF_SHA = sha(os.path.abspath(__file__))

def real_bundle():
    b = dict(verdict=RC + "/G2C_verdict.json", prep=RC + "/G2C_prep.json",
             chain=dict(receipt=W + "/g2c_chain/receipts/PARITY_G2C_chain_1788624000_1789200000.json", root=W + "/g2c_chain", log=W + "/g2c_chain/receipts/G2C_chain.log"), slots={})
    for slot, (A, hh) in SLOTS.items():
        b["slots"][slot] = dict(receipt=f"{W}/g2c_{slot}/receipts/PARITY_G2C_snapshot_{hh}Z_{A}_{A}.json", root=f"{W}/g2c_{slot}", log=f"{W}/g2c_{slot}/receipts/G2C_snapshot_{hh}Z.log", override={})
    return b

def check(b):
    fails = []; info = {}
    def F(cid, cond, msg=""):
        if not cond: fails.append([cid, str(msg)[:300]])
        return bool(cond)
    def guard(cid, fn):
        try: fn()
        except Exception as e: fails.append([cid, f"EXC {type(e).__name__}: {str(e)[:200]}"])
    V = json.load(open(b["verdict"])); P = json.load(open(b["prep"]))
    F("B9.verdict", V.get("verdict") == "PASS", V.get("verdict"))
    F("B3.prep_sha", V.get("prep_receipt_sha256") == sha(b["prep"]), "judge prep sha != disk")
    snapV = (V.get("combo_snapshot_seeded") or {}).get("anchors") or {}
    F("B1.slots", sorted(snapV) == ["s12", "s16", "s20"], sorted(snapV))
    seen = []
    for slot, (A, hh) in SLOTS.items():
        sb = b["slots"][slot]; sv = snapV.get(slot) or {}; seen.append(sv.get("anchor"))
        F("B1.anchor", sv.get("anchor") == A, f"{slot}: judge anchor {sv.get('anchor')} != {A}")
        F("B1.path", sv.get("receipt") == f"{W}/g2c_{slot}/receipts/PARITY_G2C_snapshot_{hh}Z_{A}_{A}.json", f"{slot}: judge receipt path {sv.get('receipt')}")
        F("B1.sha", sv.get("receipt_sha256") == sha(sb["receipt"]), f"{slot}: judge receipt sha != file read")
        R = json.load(open(sb["receipt"])); an = R.get("anchors") or []; a0 = an[0] if an else {}
        F("B2.one", len(an) == 1, f"{slot}: {len(an)} anchors in receipt")
        F("B2.anchor", a0.get("anchor") == A, f"{slot}: receipt anchor {a0.get('anchor')} != {A}")
        F("B2.mode", a0.get("mode") == "snapshot" and a0.get("snapshot") == f"{W}/snapshots/{A - 14400}", f"{slot}: mode {a0.get('mode')} snapshot {a0.get('snapshot')}")
        root = sb["root"]; fh = root + "/home/wide_shadow"; rh = root + "/replay_home"; ov = sb.get("override") or {}
        def b3():
            pr = (P.get("runs") or {}).get(f"g2c_{slot}") or {}
            F("B3.prep", pr.get("anchors") == [A] and pr.get("A_end") == A and pr.get("snapdir") == str(A - 14400) and pr.get("aux") == str(A) and pr.get("mode") == "snapshot"
              and pr.get("root") == f"{W}/g2c_{slot}" and pr.get("fake_home") == f"{W}/g2c_{slot}/home", f"{slot}: prep run fields {({k: pr.get(k) for k in ('anchors', 'A_end', 'snapdir', 'aux', 'mode')})}")
            F("B3.rolling", R.get("rolling_sha256") == pr.get("hybrid_sha256") == sha(fh + "/state/rolling.npz"), f"{slot}: rolling sha receipt/prep/disk differ")
            F("B3.aux", R.get("aux_sha256") == sha(fh + "/state/aux.json") == ((P.get("inputs") or {}).get(f"snap_{A}_aux") or {}).get("sha256"), f"{slot}: aux sha receipt/disk/prep differ")
            F("B3.device", R.get("device_sha256") == DEVICE_SHA and R.get("production_sha256") == PRODUCTION_SHA, f"{slot}: device/production sha")
            for f_, s_ in DEV.items(): F("B3.dev", sha(f"{root}/dev/{f_}") == s_, f"{slot}: dev copy {f_}")
            F("B3.rc", last_line(sb["log"]) == "rc=0", f"{slot}: log last line {last_line(sb['log'])!r}")
        guard("B3", b3)
        def b4():
            sd = f"{W}/snapshots/{A - 14400}"
            F("B4.aux_last_anchor", int(json.load(open(sd + "/aux.json"))["last_anchor"]) == A - 14400, f"{slot}: snapshot aux last_anchor")
            # attempt 1 matched SHA256SUMS names literally: the 1789200000 list carries repo-relative paths, so no s12 file was checked and the check
            # passed vacuously (receipts G2C_BIND.attempt1_sums_vacuous.*). Names are now resolved by basename, the list's self-entry is skipped by name,
            # and every data file present in the directory must be covered by a matching entry.
            miss = []; covered = set()
            for line in open(sd + "/SHA256SUMS.txt"):
                if not line.strip(): continue
                d_, n_ = line.split(None, 1); base = os.path.basename(n_.strip())
                if base == "SHA256SUMS.txt": continue
                if os.path.exists(f"{sd}/{base}"):
                    covered.add(base); F("B4.sums", sha(f"{sd}/{base}") == d_, f"{slot}: {base} sha != SHA256SUMS")
                else: miss.append(n_.strip())
            present = {f_ for f_ in os.listdir(sd) if f_ != "SHA256SUMS.txt"}
            F("B4.sums_cover", len(present) > 0 and present <= covered, f"{slot}: present but not covered by SHA256SUMS: {sorted(present - covered)}")
            info.setdefault("snapshot_sums", {})[slot] = dict(covered=sorted(covered), listed_not_present=miss)
            for tag in ("f10", "kc", "fc"):
                p_ = f"{fh}/fea171/state_H_{tag}_{A - 14400}.npz"
                F("B4.state_H", os.path.exists(p_) and int(np.load(p_)["anchor"]) == A - 14400, f"{slot}: {p_}")
            F("B4.weights_prev", os.path.exists(f"{fh}/state/weights/{A - 14400}.npz"), f"{slot}: producer weights/{A - 14400}.npz missing")
            z = np.load(fh + "/state/rolling.npz"); pr = (P.get("runs") or {}).get(f"g2c_{slot}") or {}
            F("B4.rolling_last", int(z["ts"][-1]) == A and pr.get("hybrid_ts_last") == iso(A), f"{slot}: rolling last {iso(z['ts'][-1])} prep {pr.get('hybrid_ts_last')}")
        guard("B4", b4)
        def b5_b6():
            p_tl = f"{fh}/state/target_live/{A}.json"; p_tc = f"{fh}/state/target_combo/{A}.json"
            r_tlc = ov.get("target_live_combo", f"{rh}/state/target_live_combo/{A}.json"); r_tc = ov.get("target_combo", f"{rh}/state/target_combo/{A}.json")
            ll = json.load(open(p_tl)); lc = json.load(open(p_tc)); rl = json.load(open(r_tlc)); rc_ = json.load(open(r_tc))
            F("B5.anchor", int(ll["anchor_ts"]) == A and int(lc["anchor_ts"]) == A and int(rl["anchor_ts"]) == A and int(rc_["anchor_ts"]) == A, f"{slot}: file anchor_ts")
            cb = a0.get("combo") or {}
            for nm, rr, lx, nkey, lkey in (("target_live", rl, ll, "target_live_n", "target_live_Linf"), ("target_combo", rc_, lc, "target_combo_n", "target_combo_Linf")):
                rk, lk = set(rr["weights"]), set(lx["weights"])
                F("B6.combo_names", rk == lk, f"{slot} {nm}: replay-only {sorted(rk - lk)[:5]} producer-only {sorted(lk - rk)[:5]}")
                F("B6.combo_count", list(cb.get(nkey) or []) == [len(rk), len(lk)] and len(rk) == len(lk), f"{slot} {nm}: receipt n {cb.get(nkey)} vs files [{len(rk)}, {len(lk)}]")
                keys = rk | lk; linf = max(abs(rr["weights"].get(k, 0.0) - lx["weights"].get(k, 0.0)) for k in keys) if keys else 0.0
                F("B6.combo_linf", linf == cb.get(lkey), f"{slot} {nm}: recomputed {linf} vs receipt {cb.get(lkey)}")
            rs, rz = nz_set(f"{rh}/state/weights/{A}.npz"); ls_, lz = nz_set(f"{fh}/state/weights/{A}.npz")
            F("B6.king_members", rs == ls_, f"{slot}: king weights member sets differ ({len(rs ^ ls_)} names)")
            F("B6.king_count", a0.get("n_nonzero_replay") == len(rs) and a0.get("n_nonzero_live") == len(ls_), f"{slot}: king counts {a0.get('n_nonzero_replay')}/{a0.get('n_nonzero_live')} vs {len(rs)}/{len(ls_)}")
            F("B6.king_linf", float(np.abs(dense(rz) - dense(lz)).max()) == a0.get("weights_npz_Linf"), f"{slot}: king L-inf recompute")
            rj = json.load(open(f"{rh}/state/target_live/{A}.json")); lj = json.load(open(f"{fh}/state/target_live_king/{A}.json"))
            F("B6.king_json_names", set(rj["weights"]) == set(lj["weights"]) and a0.get("n_names_replay") == len(rj["weights"]) == rj.get("n_names") and a0.get("n_names_live") == len(lj["weights"]) == lj.get("n_names"),
              f"{slot}: king target_live names/counts")
            keys = set(rj["weights"]) | set(lj["weights"]); jd = max(abs(rj["weights"].get(k, 0.0) - lj["weights"].get(k, 0.0)) for k in keys) if keys else 0.0
            F("B6.king_json_linf", jd == a0.get("target_live_json_Linf"), f"{slot}: king json L-inf recompute")
        guard("B5B6", b5_b6)
    F("B1.distinct", len(set(seen)) == 3 and None not in seen, f"anchors {seen}")
    def b7():
        cbp = b["chain"]; C = json.load(open(cbp["receipt"])); root = cbp["root"]; fh = root + "/home/wide_shadow"; rh = root + "/replay_home"
        F("B7.sha", V.get("chain_receipt") == W + "/g2c_chain/receipts/PARITY_G2C_chain_1788624000_1789200000.json" and V.get("chain_receipt_sha256") == sha(cbp["receipt"]), "judge chain receipt path/sha")
        an = [int(x["anchor"]) for x in C.get("anchors") or []]
        F("B7.anchors", an == CHAIN, f"chain anchors n={len(an)} first={an[:2]}")
        pc = (P.get("runs") or {}).get("g2c_chain") or {}
        F("B7.prep", pc.get("anchors") == CHAIN and pc.get("A_end") == 1789200000 and pc.get("mode") == "chain" and pc.get("root") == root, "chain prep fields")
        F("B7.rolling", C.get("rolling_sha256") == pc.get("hybrid_sha256") == sha(fh + "/state/rolling.npz"), "chain rolling sha receipt/prep/disk")
        F("B7.device", C.get("device_sha256") == DEVICE_SHA and C.get("production_sha256") == PRODUCTION_SHA, "chain device/production sha")
        for f_, s_ in DEV.items(): F("B7.dev", sha(f"{root}/dev/{f_}") == s_, f"chain dev copy {f_}")
        F("B7.rc", last_line(cbp["log"]) == "rc=0", "chain log rc")
        per = {int(k["anchor"]): k for k in (V.get("king_chain") or {}).get("per_anchor") or []}
        F("B7.judge_anchors", sorted(per) == CHAIN, "judge per_anchor set")
        n_ok = 0; combo_names_equal = 0
        for x in C.get("anchors") or []:
            A = int(x["anchor"]); rs, rz = nz_set(f"{rh}/state/weights/{A}.npz"); ls_, lz = nz_set(f"{fh}/state/weights/{A}.npz")
            F("B7.king_members", rs == ls_, f"{iso(A)}: king member sets differ ({len(rs ^ ls_)} names)")
            F("B7.king_count", x.get("n_nonzero_replay") == len(rs) and x.get("n_nonzero_live") == len(ls_), f"{iso(A)}: counts {x.get('n_nonzero_replay')}/{x.get('n_nonzero_live')} vs {len(rs)}/{len(ls_)}")
            linf = float(np.abs(dense(rz) - dense(lz)).max())
            F("B7.king_linf", linf == x.get("weights_npz_Linf") == (per.get(A) or {}).get("g2c_weights_npz_Linf"), f"{iso(A)}: L-inf recompute {linf} receipt {x.get('weights_npz_Linf')}")
            n_ok += int(linf <= 1e-6)
            try:
                rl = json.load(open(f"{rh}/state/target_live_combo/{A}.json")); ll = json.load(open(f"{fh}/state/target_live/{A}.json")); combo_names_equal += int(set(rl["weights"]) == set(ll["weights"]))
            except Exception:
                pass
        F("B7.king_rejudge", n_ok == 41, f"king <= 1e-6 on {n_ok}/41")
        info["king_chain_le_1e-6"] = n_ok; info["combo_chain_name_sets_equal_descriptive"] = combo_names_equal
    guard("B7", b7)
    return dict(PASS=not fails, n_fails=len(fails), fired=sorted(set(f[0] for f in fails)), fails_first40=fails[:40], info=info)

REAL = real_bundle()
REAL_FILES = [REAL["verdict"], REAL["prep"], REAL["chain"]["receipt"]] + [s["receipt"] for s in REAL["slots"].values()] + \
             [f"{W}/g2c_{s}/replay_home/state/target_live_combo/{a}.json" for s, (a, _) in SLOTS.items()]
SHA0 = {p: sha(p) for p in REAL_FILES}

def mutants():
    V = json.load(open(REAL["verdict"])); out = {}
    def mk(name):
        d = f"{MUT}/{name}"; os.makedirs(d, exist_ok=True); assert os.path.realpath(d).startswith(MUT + "/"); return d, copy.deepcopy(REAL), copy.deepcopy(V)
    def put(d, fname, obj):
        p = f"{d}/{fname}"; json.dump(obj, open(p, "w"), indent=1); return p
    # M1 wrong anchor (s16 receipt names 1789243200; judge sha synced so only the anchor binding can catch it)
    d, b, Vm = mk("M1_wrong_anchor"); R = json.load(open(REAL["slots"]["s16"]["receipt"])); R["anchors"][0]["anchor"] = 1789243200
    rp = put(d, "PARITY_s16.json", R); b["slots"]["s16"]["receipt"] = rp
    Vm["combo_snapshot_seeded"]["anchors"]["s16"]["anchor"] = 1789243200; Vm["combo_snapshot_seeded"]["anchors"]["s16"]["receipt_sha256"] = sha(rp)
    b["verdict"] = put(d, "G2C_verdict.json", Vm); out["M1_wrong_anchor"] = (b, {"B1.anchor", "B2.anchor"})
    # M2 dropped name (replay s16 target_live_combo loses its smallest-|w| name; receipts unchanged)
    d, b, Vm = mk("M2_dropped_name"); A = SLOTS["s16"][0]; J = json.load(open(f"{W}/g2c_s16/replay_home/state/target_live_combo/{A}.json"))
    k = min(J["weights"], key=lambda s: abs(J["weights"][s])); del J["weights"][k]
    b["slots"]["s16"]["override"] = {"target_live_combo": put(d, f"target_live_combo_{A}.json", J)}; out["M2_dropped_name"] = (b, {"B6.combo_names"})
    # M3 file sha does not match disk (s20 receipt edited in an unrelated field; judge sha unchanged)
    d, b, Vm = mk("M3_sha_mismatch"); R = json.load(open(REAL["slots"]["s20"]["receipt"])); R["utc"] = str(R.get("utc")) + "_mut"
    b["slots"]["s20"]["receipt"] = put(d, "PARITY_s20.json", R); out["M3_sha_mismatch"] = (b, {"B1.sha"})
    # M4 same 12Z receipt in all three slots (reviewer case)
    d, b, Vm = mk("M4_same_receipt_three_slots")
    for s in ("s16", "s20"):
        Vm["combo_snapshot_seeded"]["anchors"][s] = copy.deepcopy(V["combo_snapshot_seeded"]["anchors"]["s12"]); b["slots"][s]["receipt"] = REAL["slots"]["s12"]["receipt"]
    b["verdict"] = put(d, "G2C_verdict.json", Vm); out["M4_same_receipt_three_slots"] = (b, {"B1.anchor", "B1.distinct", "B2.anchor"})
    # M5 correct first anchor plus an appended failing second anchor (reviewer case; judge sha synced)
    d, b, Vm = mk("M5_appended_failing_anchor"); R = json.load(open(REAL["slots"]["s12"]["receipt"])); a2 = copy.deepcopy(R["anchors"][0])
    a2["anchor"] = 1789228800; a2.setdefault("combo", {})["rc"] = 1; a2["combo"]["target_live_Linf"] = 0.5; R["anchors"].append(a2)
    rp = put(d, "PARITY_s12.json", R); b["slots"]["s12"]["receipt"] = rp; Vm["combo_snapshot_seeded"]["anchors"]["s12"]["receipt_sha256"] = sha(rp)
    b["verdict"] = put(d, "G2C_verdict.json", Vm); out["M5_appended_failing_anchor"] = (b, {"B2.one"})
    # M6 rotated slots: every slot carries another anchor's receipt (reviewer "three wrong anchors")
    d, b, Vm = mk("M6_rotated_slots"); rot = {"s12": "s16", "s16": "s20", "s20": "s12"}
    for s, t in rot.items():
        Vm["combo_snapshot_seeded"]["anchors"][s] = copy.deepcopy(V["combo_snapshot_seeded"]["anchors"][t]); b["slots"][s]["receipt"] = REAL["slots"][t]["receipt"]
    b["verdict"] = put(d, "G2C_verdict.json", Vm); out["M6_rotated_slots"] = (b, {"B1.anchor", "B2.anchor"})
    return out

res_real = check(REAL)
MUTS = mutants(); res_m = {}
for name, (bundle, expect) in MUTS.items():
    r = check(bundle); r["expected_checks"] = sorted(expect); r["RED"] = not r["PASS"]; r["red_for_named_reason"] = bool(expect <= set(r["fired"]))
    r["mutant_files"] = sorted(os.path.join(dp, f) for dp, _, fs in os.walk(f"{MUT}/{name}") for f in fs)
    res_m[name] = r
SHA1 = {p: sha(p) for p in REAL_FILES}
untouched = SHA0 == SHA1
PASS = bool(res_real["PASS"] and all(r["RED"] and r["red_for_named_reason"] for r in res_m.values()) and untouched)
OUT = dict(device="p2_g2c_bind.py", self_sha256=SELF_SHA, prereg_sha256=PREREG_SHA, argv=sys.argv, env=dict(os.environ), python=sys.version.split()[0], numpy=np.__version__,
           frozen_slots={s: a for s, (a, _) in SLOTS.items()}, chain_anchors=[CHAIN[0], CHAIN[-1], len(CHAIN)], real_bundle=REAL, real_files_sha256_before=SHA0,
           real_files_unchanged_after=untouched, real=res_real, mutants=res_m, verdict="PASS" if PASS else "RED", runtime_s=round(time.time() - T0, 1), utc=iso(time.time()))
rp = RC + "/G2C_BIND.json"; assert os.path.realpath(rp).startswith(P2 + "/")
json.dump(OUT, open(rp + ".tmp", "w"), indent=1, default=str); os.replace(rp + ".tmp", rp)
print("G2C_BIND verdict=%s real=%s (fails=%d %s) mutants_red=%d/%d named_reason=%d/%d real_receipts_unchanged=%s king_chain_le_1e-6=%s receipt_sha256=%s" % (
    OUT["verdict"], "PASS" if res_real["PASS"] else "RED", res_real["n_fails"], res_real["fired"], sum(r["RED"] for r in res_m.values()), len(res_m),
    sum(r["red_for_named_reason"] for r in res_m.values()), len(res_m), untouched, res_real["info"].get("king_chain_le_1e-6"), sha(rp)), flush=True)
sys.exit(0 if PASS else 3)
