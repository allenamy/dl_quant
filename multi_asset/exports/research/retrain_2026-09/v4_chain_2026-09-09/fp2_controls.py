#!/usr/bin/env python3
"""fp2_controls.py — FP2-8 §2 / AMENDMENT 1.1 (2026-09-17): the two BITWISE positive controls on REAL data, run BEFORE the FP2 data stage.

  K  king builder v2 WITHOUT a mask vs the September v1 build on the SAME cache/panel (/workspace/data/wide_fea_v4.npy + _meta.npz):
       every September anchor is present in v2; on common anchors FEA rows / members / y4 / qvk are bitwise equal; the anchors only in v2 are
       EXACTLY the 30 with 576 <= E_row < 2016 (the v1 silent drop); their member features are finite.
  D  DL targets builder v2 WITHOUT a mask (RAW, with the raw patch) vs the September dlw_v4raw/data/dlw_targets.npz: every array bitwise
       equal (v1 already clamps; v2 adds only the mask hook).
The v2 builders are run through their REAL entry with the driver's env contract (env -i + the same keys), into $R/controls/{king_nomask,dl_nomask}/.
Receipt $R/controls/CONTROLS.json (three-state VERDICT; PASS iff every check ok; UNAVAILABLE when an input cannot be read) binds: input shas,
builder shas, output shas, every check. The FP2 gates (fp2_gate_step1/2.py) require this receipt and re-hash what it names.
env (REQUIRED): R D PY CACHE PANEL_SPLICE PANEL_KING SEPT_KING_FEA SEPT_KING_META SEPT_DL_TARGETS BUILDER_TARGETS BUILDER_KING_FEA"""
import hashlib, json, os, subprocess, sys, time
import numpy as np
REQ = ("R", "D", "PY", "CACHE", "PANEL_SPLICE", "PANEL_KING", "SEPT_KING_FEA", "SEPT_KING_META", "SEPT_DL_TARGETS", "BUILDER_TARGETS", "BUILDER_KING_FEA")
# RAW_PATCH: required on real data (the September dlw_v4raw was built WITH the patch, so an omitted patch fails D1); may be EMPTY only for a
# September build that was itself unpatched (synthetic tests). Its presence/absence is recorded in the receipt (inputs_path.raw_patch).
T0 = time.time()
def log(*a): print(f"[{time.time()-T0:7.1f}s]", *a, flush=True)
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""): h.update(ch)
    return h.hexdigest()
def eq_bits(a, b):
    a = np.asarray(a); b = np.asarray(b)
    if a.dtype == object or b.dtype == object: return a.dtype == b.dtype and len(a) == len(b) and all(np.array_equal(x, y) for x, y in zip(a, b))
    return a.shape == b.shape and a.dtype == b.dtype and np.array_equal(a.view(np.uint8), b.view(np.uint8))

def main():
    miss = [k for k in REQ if not os.environ.get(k)]
    if miss: print("CONTROLS_REFUSED env missing", miss, flush=True); return 3
    E = {k: os.environ[k] for k in REQ}; E["RAW_PATCH"] = os.environ.get("RAW_PATCH", ""); R = E["R"]; D = E["D"]; OUT = os.path.join(R, "controls"); REC = os.path.join(OUT, "CONTROLS.json")
    rec = {"gate": "FP2_CONTROLS", "self_sha256": sha(os.path.abspath(__file__)), "utc_start": time.strftime("%FT%TZ", time.gmtime()), "env": E,
           "checks": {}, "VERDICT": None, "PASS": False}
    def check(name, ok, detail=None):
        rec["checks"][name] = {"ok": bool(ok), "detail": detail}; log(("  OK   " if ok else "  FAIL ") + name, json.dumps(detail, default=str)[:300] if detail is not None else "")
    def write(verdict):
        rec["VERDICT"] = verdict; rec["PASS"] = verdict == "PASS"; rec["utc_end"] = time.strftime("%FT%TZ", time.gmtime())
        os.makedirs(OUT, exist_ok=True); json.dump(rec, open(REC, "w"), indent=1, default=str); log("CONTROLS", verdict, REC)
    VERIFY_ONLY = os.environ.get("VERIFY_ONLY", "") == "1"   # re-evaluate the checks on EXISTING rc-0 outputs (a criterion fix), never rebuild; recorded in the receipt
    rec["mode"] = "verify_only" if VERIFY_ONLY else "build_and_verify"
    if VERIFY_ONLY:
        if os.path.isfile(REC):
            prev = json.load(open(REC)); rec["previous_receipt"] = {"sha256": sha(REC), "VERDICT": prev.get("VERDICT"), "self_sha256": prev.get("self_sha256"), "runs": prev.get("runs"),
                                                                    "inputs_sha256": prev.get("inputs_sha256"), "outputs_sha256": prev.get("outputs_sha256")}
            runs_prev = prev.get("runs") or {}
            # F02 (independent review 2026-09-17): a verify-only pass re-issues a verdict for THE SAME BUILD ONLY. It must therefore prove (below, after
            # hashing) that every input the build consumed and every output it wrote are byte-identical to what the previous receipt recorded; and the
            # previous receipt must carry a NON-EMPTY run set with rc 0 (an empty set made `all()` vacuously true).
            if set(runs_prev) != {"king", "dl"} or not all(v.get("rc") == 0 for v in runs_prev.values()): print("CONTROLS_REFUSED verify_only needs a previous receipt with BOTH builds (king, dl) at rc 0", flush=True); return 3
        else: print("CONTROLS_REFUSED verify_only without a previous receipt", flush=True); return 3
    else:
        for k in ("king_nomask", "dl_nomask"):
            if os.path.exists(os.path.join(OUT, k)): print(f"CONTROLS_REFUSED {OUT}/{k} exists (fresh directory required)", flush=True); return 3
    bk = os.path.join(D, E["BUILDER_KING_FEA"]); bt = os.path.join(D, E["BUILDER_TARGETS"])
    try:
        rec["inputs_sha256"] = {"cache": sha(E["CACHE"]), "panel_splice": sha(E["PANEL_SPLICE"]), "panel_king": sha(E["PANEL_KING"]), "raw_patch": (sha(E["RAW_PATCH"]) if E["RAW_PATCH"] else None),
                               "sept_king_fea": sha(E["SEPT_KING_FEA"]), "sept_king_meta": sha(E["SEPT_KING_META"]), "sept_dl_targets": sha(E["SEPT_DL_TARGETS"]),
                               "builder_king": sha(bk), "builder_targets": sha(bt)}
        rec["inputs_path"] = {"cache": E["CACHE"], "panel_splice": E["PANEL_SPLICE"], "panel_king": E["PANEL_KING"], "raw_patch": E["RAW_PATCH"] or None, "sept_king_fea": E["SEPT_KING_FEA"],
                              "sept_king_meta": E["SEPT_KING_META"], "sept_dl_targets": E["SEPT_DL_TARGETS"], "builder_king": bk, "builder_targets": bt}
    except Exception as e:   # noqa: BLE001
        rec["error"] = repr(e); write("UNAVAILABLE"); return 3
    log("inputs hashed", json.dumps({k: (v[:8] if v else None) for k, v in rec["inputs_sha256"].items()}))
    base = {"PATH": os.environ.get("PATH", ""), "HOME": os.environ.get("HOME", "/root"), "OMP_NUM_THREADS": os.environ.get("OMP_NUM_THREADS", "8"), "MEMBER_MASK_NPZ": ""}
    if os.environ.get("PYTHONPATH"): base["PYTHONPATH"] = os.environ["PYTHONPATH"]   # passed through ONLY when the caller set it (local synthetic tests: the zload shim); recorded in runs.env
    kd = os.path.join(OUT, "king_nomask"); dd = os.path.join(OUT, "dl_nomask")
    if not VERIFY_ONLY: os.makedirs(kd); os.makedirs(dd)
    envk = dict(base, CACHE_IN=E["CACHE"], PANEL_IN=E["PANEL_KING"], FEA_OUT=f"{kd}/wide_fea_v4.npy", META_OUT=f"{kd}/wide_fea_v4_meta.npz")
    envd = dict(base, DLWT_CACHE=E["CACHE"], DLWT_PANEL=E["PANEL_SPLICE"], DLWT_OUT=dd, DLWT_RET_CH="0", DLWT_RAW_PATCH=E["RAW_PATCH"])
    runs = {}
    for tag, script, env, logp in (() if VERIFY_ONLY else (("king", bk, envk, f"{kd}/build.log"), ("dl", bt, envd, f"{dd}/build.log"))):
        log("run", tag, os.path.basename(script), "(env -i, mask empty)")
        with open(logp, "w") as lf: rc = subprocess.call(["env", "-i"] + [f"{k}={v}" for k, v in env.items()] + [E["PY"], script], stdout=lf, stderr=subprocess.STDOUT, cwd=D)
        runs[tag] = {"rc": rc, "log": logp, "env": env, "tail": open(logp).read().strip().splitlines()[-1][:200] if os.path.getsize(logp) else ""}
        log(tag, "rc", rc, runs[tag]["tail"])
    rec["runs"] = runs if not VERIFY_ONLY else rec["previous_receipt"]["runs"]
    if not VERIFY_ONLY and (runs["king"]["rc"] != 0 or runs["dl"]["rc"] != 0): write("UNAVAILABLE"); return 3
    if VERIFY_ONLY and not (os.path.isfile(envk["FEA_OUT"]) and os.path.isfile(envk["META_OUT"]) and os.path.isfile(f"{dd}/data/dlw_targets.npz")): write("UNAVAILABLE"); return 3
    if VERIFY_ONLY:   # F02: identity binding — inputs now == inputs then; outputs now == outputs then; else this is NOT the same build and no verdict is re-issued
        pi = rec["previous_receipt"]["inputs_sha256"] or {}; po = rec["previous_receipt"]["outputs_sha256"] or {}
        prev_paths = rec["previous_receipt"].get("outputs_path") or {}
        now_out = {k: (sha(p) if os.path.isfile(p) else None) for k, p in prev_paths.items()}          # R07: EVERY output the previous receipt registered (incl. control_dl_report), by ITS paths
        for k, p in (("control_king_fea", envk["FEA_OUT"]), ("control_king_meta", envk["META_OUT"]), ("control_dl_targets", f"{dd}/data/dlw_targets.npz"), ("control_dl_report", f"{dd}/results/dlw_targets_report.json")):
            if k not in now_out: now_out[k] = sha(p) if os.path.isfile(p) else None
        diff_in = sorted(k for k in set(pi) | set(rec["inputs_sha256"]) if pi.get(k) != rec["inputs_sha256"].get(k)); diff_out = sorted(k for k in set(po) | set(now_out) if po.get(k) != now_out.get(k))
        rec["verify_only_binding"] = {"inputs_changed": diff_in, "outputs_changed": diff_out}
        if diff_in or diff_out: log("CONTROLS_REFUSED verify_only: not the same build —", json.dumps(rec["verify_only_binding"])); write("UNAVAILABLE"); return 3
    rec["outputs_path"] = {"control_king_fea": envk["FEA_OUT"], "control_king_meta": envk["META_OUT"], "control_dl_targets": f"{dd}/data/dlw_targets.npz", "control_dl_report": f"{dd}/results/dlw_targets_report.json"}
    rec["outputs_sha256"] = {k: sha(v) for k, v in rec["outputs_path"].items()}
    # ---- K: king v2 (no mask) vs September v1 ----
    M1 = np.load(E["SEPT_KING_META"], allow_pickle=True); M2 = np.load(envk["META_OUT"], allow_pickle=True)
    F1 = np.load(E["SEPT_KING_FEA"], mmap_mode="r"); F2 = np.load(envk["FEA_OUT"], mmap_mode="r")
    E1 = M1["E_ts"].astype(np.int64); E2 = M2["E_ts"].astype(np.int64); CTS = np.load(E["CACHE"], mmap_mode="r")["ts"] if False else None
    import zipfile
    with zipfile.ZipFile(E["CACHE"]) as z: cts = np.load(z.open("ts.npy")).astype(np.int64)
    row = {int(t): i for i, t in enumerate(E2)}; common = [(i, row[int(t)]) for i, t in enumerate(E1) if int(t) in row]
    check("K1 every September anchor is present in v2", len(common) == len(E1), {"sept": int(len(E1)), "v2": int(len(E2))})
    m1 = M1["members"]; m2 = M2["members"]; y1 = M1["y4"]; y2 = M2["y4"]; q1 = M1["qvk"]; q2 = M2["qvk"]; bad = []   # materialised ONCE (an NpzFile key access re-reads the whole array)
    def _idx(m):   # a member row as an int64 index; a non-integer-valued row is a builder defect and must surface, not be coerced silently
        a = np.asarray(m); b = a.astype(np.int64)
        if a.dtype == object and not np.array_equal(np.asarray(a.tolist(), dtype=np.float64), b): raise ValueError("member row not integer-valued")
        return b
    rec["members_persisted_ndim"] = {"sept": int(np.asarray(m1).ndim), "v2": int(np.asarray(m2).ndim)}   # 2 ⇒ every anchor had the same member count (np.array(list, dtype=object) became 2-D)
    for i, j in common:
        if not (np.array_equal(_idx(m1[i]), _idx(m2[j])) and np.array_equal(np.asarray(F1[i]).view(np.uint16), np.asarray(F2[j]).view(np.uint16))
                and np.array_equal(y1[i].view(np.uint32), y2[j].view(np.uint32)) and np.array_equal(q1[i].view(np.uint32), q2[j].view(np.uint32))):
            bad.append(int(E1[i]))
            if len(bad) > 20: break
    check("K2 common anchors: FEA rows / members / y4 / qvk BITWISE equal", not bad, {"n_common": len(common), "first_bad_E_ts": bad[:5]})
    sept = {int(t) for t in E1}; extra = [j for j in range(len(E2)) if int(E2[j]) not in sept]
    erow = np.searchsorted(cts, E2[extra]) if extra else np.zeros(0, np.int64)
    okrow = bool(len(extra)) and np.array_equal(cts[erow], E2[extra]) and all(576 <= int(r) < 2016 for r in erow)
    # finiteness is judged on the NON-funding columns: the builder leaves fund_ema/fund_now NaN for anchors before the king panel's first row
    # (September's own first anchors carry the same NaNs and passed K2 bitwise) — so fund columns are counted, not required finite.
    names2 = [str(x) for x in M2["names"]]; nonfund = np.array([n not in ("fund_ema", "fund_now") for n in names2])
    fin = all(np.isfinite(np.asarray(F2[j])[_idx(m2[j])][:, nonfund].astype(np.float32)).all() for j in extra) if extra else False
    fund_nan_rows = int(sum(1 for j in extra if not np.isfinite(np.asarray(F2[j])[_idx(m2[j])][:, ~nonfund].astype(np.float32)).all())) if extra else 0
    check("K3 anchors only in v2 are EXACTLY the pre-2016-bar anchors (E_row in [576, 2016)) and their member features are finite on the non-funding columns",
          okrow and fin and len(extra) == int(((cts % 14400 == 0) & (np.arange(len(cts)) >= 576) & (np.arange(len(cts)) < 2016)).sum()),
          {"n_extra": len(extra), "E_rows": [int(r) for r in erow[:6]], "expected_n": int(((cts % 14400 == 0) & (np.arange(len(cts)) >= 576) & (np.arange(len(cts)) < 2016)).sum()),
           "first_extra_utc": time.strftime("%F %H:%MZ", time.gmtime(int(E2[extra[0]]))) if extra else None, "extra_rows_with_fund_nan": fund_nan_rows, "nonfund_cols": int(nonfund.sum())})
    check("K4 names / builder self-report", [str(x) for x in M1["names"]] == [str(x) for x in M2["names"]] and str(M2["builder"]) == E["BUILDER_KING_FEA"] and json.loads(str(M2["member_mask_json"]))["applied"] is False,
          {"builder": str(M2["builder"]), "n_anchors_before_2016": int(M2["n_anchors_before_2016"])})
    # ---- D: DL v2 (no mask) vs September dlw_v4raw ----
    T1 = np.load(E["SEPT_DL_TARGETS"], allow_pickle=True); T2 = np.load(rec["outputs_path"]["control_dl_targets"], allow_pickle=True)
    keys = [k for k in T1.files if k != "meta_json"]; diff = [k for k in keys if k not in T2.files or not eq_bits(T1[k], T2[k])]
    check("D1 every array of dlw_targets.npz BITWISE equal to September (meta_json excluded)", not diff, {"keys": keys, "diff": diff})
    m2j = json.loads(str(T2["meta_json"]))
    check("D2 builder self-report: v2 name, mask not applied", m2j.get("builder") == E["BUILDER_TARGETS"] and m2j.get("member_mask", {}).get("applied") is False, m2j.get("member_mask"))
    write("PASS" if all(c["ok"] for c in rec["checks"].values()) else "FAIL")
    return 0 if rec["PASS"] else 1

if __name__ == "__main__":
    sys.exit(main())
