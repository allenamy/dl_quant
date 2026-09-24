#!/usr/bin/env python3
"""NC deploy installer (DESIGN §A7 / §D / §F-2; FREEZE b30e4afa5 + amendment 1). Three verbs, one contract (nc_package.py):
  preflight <pkg> [--seeded DIR --seed-pack F]     read-only: package bytes = contract; every destination still at its baseline; the
                                                   release's unchanged files unchanged; with --seeded: the seeded state is complete, signed,
                                                   built from the CURRENT production state, and its rows check out (below).
  apply <pkg> <backup dir> --seeded DIR --seed-pack F
                                                   quiet window (>= --reserve min left), producer-side services not running, executor
                                                   anchor.lock held; backup of every destination + the current state; files then state
                                                   installed atomically (generation.json last); the INSTALLED producer loads the state.
  rollback <pkg> <backup dir> [--downgraded DIR]   quiet window, services not running, lock held; every file back to its baseline bytes
                                                   (new files moved aside), NC-only state files moved aside; state: the backup's pre-install
                                                   state if the NC producer never advanced it (incl. a half-done apply), else the downgraded
                                                   CURRENT state (nc_downgrade_state.py) — required then; the RESTORED producer loads it.
Services are stopped / started by the operator (the manual's commands); this tool only verifies they are not running.
Seeded-state row checks (independent of nc_seed_state.py): rows <= axis end, crypto columns = the seed pack's rows bitwise (NaN = NaN);
non-crypto columns = production bytes on every row; rows > axis end, crypto columns: channels 1..6 = production bytes except rows the live
pack filled, channel 0 = production or NaN (the no-cross-gap rule may only blank it); the sparse table covers every bound cell.
--home H runs against a copy of the machine layout (rehearsal); --no-launchctl skips the service check (rehearsal only; recorded).
Verdict record (lead 2026-09-24): preflight re-verifies the contract's verdict block from the package's own copies (verdict/export_manifest.json
sha, verdict/ruling.md sha == USER_OVERRIDE, the manifest's pins == executor_pins) and REFUSES an unbound contract on the real home. Every
receipt carries VERDICT and USER_OVERRIDE verbatim at top level; the verdict is never restated as an admission.
usage: ~/wide_shadow/venv/bin/python nc_install.py {preflight|apply|rollback} <pkg> [<backup dir>] [--seeded D] [--seed-pack F]
       [--downgraded D] [--home H] [--reserve 20] [--no-launchctl]"""
import argparse, datetime, fcntl, hashlib, importlib.util, json, os, re, shutil, subprocess, sys, time
import numpy as np

NC_STATE = ["rolling.npz", "aux.json", "leg_returns_live.json", "boundary_raw.npz", "members_hist.npz"]
OLD_STATE = ["rolling.npz", "aux.json", "leg_returns_live.json"]


class Refused(Exception):
    pass


def check(ok, msg):
    if not ok: raise Refused(msg)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def utc(): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


IGNORE_WINDOW = False


def quiet(reserve):
    if IGNORE_WINDOW: return
    n = datetime.datetime.now(datetime.timezone.utc); m = (n.hour % 4) * 60 + n.minute + n.second / 60
    check(60 <= m < 220 - reserve, f"outside the quiet window [N+1:00, N+3:40] with >= {reserve} min left (now N+{int(m) // 60}:{int(m) % 60:02d})")


def services_idle(labels, skip):
    if skip: return {"skipped": True}
    out = {}
    for lb in labels:
        r = subprocess.run(["/bin/launchctl", "print", f"gui/{os.getuid()}/{lb}"], capture_output=True, text=True, timeout=30)
        pid = re.search(r"^\s*pid = (\d+)$", r.stdout, re.M)
        out[lb] = {"loaded": r.returncode == 0, "pid": int(pid[1]) if pid else None}
        check(pid is None, f"service still running: {lb} pid {pid[1] if pid else ''}")
    return out


def atomic_copy(src, dst, mode=None):
    tmp = dst + ".nc-install.tmp"; check(not os.path.exists(tmp), f"stray temporary file {tmp}")
    with open(src, "rb") as f, open(tmp, "xb") as g:
        g.write(f.read()); g.flush(); os.fsync(g.fileno())
    if mode is not None: os.chmod(tmp, mode)
    os.replace(tmp, dst)


def load_producer(home, tag):
    ws = f"{home}/wide_shadow"
    os.environ["WIDE_SHADOW_HOME"] = ws; os.environ["WIDE_SHADOW_BUNDLE"] = f"{ws}/shadow_bundle"
    spec = importlib.util.spec_from_file_location(f"nc_install_{tag}_{time.time_ns()}", f"{ws}/shadow_loop_v3.py")
    M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M)
    return M


def producer_loads(home, tag):
    """The producer now on disk verifies the state's generation and constructs its ShadowState (no legacy import)."""
    M = load_producer(home, tag)
    cfg = json.load(open(f"{home}/wide_shadow/shadow_bundle/config.json"))
    st = M.ShadowState(cfg)
    check(not getattr(st, "legacy_import", False), "producer took the legacy-import path")
    gen = json.load(open(f"{home}/wide_shadow/state/generation.json"))
    return {"module_sha256": sha(f"{home}/wide_shadow/shadow_loop_v3.py"), "state_files": sorted(M.STATE_FILES), "generation_anchor": gen["anchor_ts"],
            "last_anchor": int(st.last_anchor)}


def preflight(pkg, home, seeded=None, seed_pack=None):
    C = json.load(open(f"{pkg}/INSTALL_CONTRACT.json")); rep = {"contract_sha256": sha(f"{pkg}/INSTALL_CONTRACT.json"), "files": len(C["files"])}
    rep["verdict"] = verdict_checks(pkg, C, home)                # first: an unbound contract is refused on the real home before anything else
    for it in C["files"]:
        check(sha(f"{pkg}/files/{it['dest']}") == it["candidate_sha256"], f"package file differs from contract: {it['dest']}")
        cur = f"{home}/{it['dest']}"
        now = sha(cur) if os.path.exists(cur) else None
        check(now == it["baseline_sha256"], f"destination not at its baseline (production changed since packaging): {it['dest']} {now} != {it['baseline_sha256']}")
        check(not os.path.islink(cur), f"destination is a symlink: {it['dest']}")
    for u, s in C["unchanged"].items():
        check(sha(f"{home}/{u}") == s, f"a file the release keeps has changed: {u}")
    man = json.load(open(f"{pkg}/files/wide_shadow/shadow_bundle/MANIFEST.json"))
    bundle = {it["dest"].split("/")[-1]: it["candidate_sha256"] for it in C["files"] if it["dest"].startswith("wide_shadow/shadow_bundle/")}
    for fn, s in man.items():
        want = bundle.get(fn) or sha(f"{home}/wide_shadow/shadow_bundle/{fn}")
        check(want == s, f"new MANIFEST entry does not match the bundle file it will sit next to: {fn}")
    check(man["slow2026.txt"] == C["executor_pins"]["booster_sha_pin"], "MANIFEST King != executor booster pin")
    f10 = [it for it in C["files"] if it["dest"] == "wide_shadow/fea171/f10_live_s42_np.npz"][0]
    check(f10["candidate_sha256"] == C["executor_pins"]["f10_sha_pin"], "F10 file != executor f10 pin")
    rep["package"] = "PASS"
    if seeded:
        rep["seeded"] = seeded_checks(seeded, seed_pack, home)
    return C, rep


def verdict_checks(pkg, C, home):
    V = C.get("verdict") or {}
    if not V.get("bound"):
        check(os.path.realpath(home) != os.path.realpath(os.path.expanduser("~")),
              "contract carries no bound verdict record (nc_package.py --export-manifest/--ruling); refused on the real home")
        return {"bound": False, "VERDICT": None, "USER_OVERRIDE": None}
    check(C.get("VERDICT") == V.get("VERDICT") and C.get("USER_OVERRIDE") == V.get("USER_OVERRIDE"), "contract top-level VERDICT/USER_OVERRIDE != its verdict block")
    mp = f"{pkg}/verdict/export_manifest.json"
    check(os.path.isfile(mp) and sha(mp) == V["export_manifest"]["sha256"], "package export manifest copy missing or != contract sha")
    M = json.load(open(mp))
    check(M.get("VERDICT") == V["VERDICT"] and M.get("seed") == "s42" and M.get("lineage_bound") is True, "export manifest VERDICT / seed / lineage differ from the contract")
    check((M.get("deploy") or {}).get("executor_pins") == C["executor_pins"], "export manifest executor_pins != contract executor_pins")
    ex = {e["name"]: e["sha256"] for e in M.get("exported_files", [])}
    check(ex == {"slow2026.txt": C["executor_pins"]["booster_sha_pin"], "f10_live_s42_np.npz": C["executor_pins"]["f10_sha_pin"]}, "export manifest exported_files != contract pins")
    if V["VERDICT"] != "DEPLOY":
        rp = f"{pkg}/verdict/ruling.md"
        check(V.get("USER_OVERRIDE") and os.path.isfile(rp) and sha(rp) == V["USER_OVERRIDE"] == M.get("USER_OVERRIDE"),
              "VERDICT != DEPLOY but the package's ruling copy / USER_OVERRIDE do not agree")
    else:
        check(V.get("USER_OVERRIDE") is None and "USER_OVERRIDE" not in M, "VERDICT=DEPLOY with a USER_OVERRIDE")
    return {"bound": True, "VERDICT": V["VERDICT"], "USER_OVERRIDE": V.get("USER_OVERRIDE"), "export_manifest_sha256": V["export_manifest"]["sha256"],
            "statement": V.get("statement")}


def seeded_checks(seeded, seed_pack, home):
    R = json.load(open(f"{seeded}/SEED_RECEIPT.json")); st = f"{seeded}/state"
    check(R.get("VERDICT") == "SEEDED", f"seed verdict {R.get('VERDICT')} (SEEDED_WITH_UNRESOLVED_BOUND_CELLS or a stop is not installable)")
    for f in NC_STATE + ["generation.json"]: check(os.path.isfile(f"{st}/{f}"), f"seeded state misses {f}")
    gen = json.load(open(f"{st}/generation.json"))
    check(sorted(gen["files"]) == sorted(NC_STATE), "seeded generation does not sign the NC state files")
    for f in NC_STATE: check(gen["files"][f]["sha256"] == sha(f"{st}/{f}"), f"seeded generation hash mismatch {f}")
    prod = f"{home}/wide_shadow/state"
    for f in OLD_STATE:
        check(sha(f"{prod}/{f}") == R["inputs"][f"prod/{f}"], f"production state advanced since seeding: {f} (re-seed)")
    aux_p = json.load(open(f"{prod}/aux.json")); aux_s = json.load(open(f"{st}/aux.json"))
    check(aux_s["last_anchor"] == aux_p["last_anchor"] == gen["anchor_ts"], "seeded anchor differs from production")
    # rows
    S = np.load(seed_pack, allow_pickle=True); E = int(S["axis_end"]); cols = S["crypto_cols"].astype(np.int64)
    check(sha(seed_pack) == R["inputs"]["seed_pack"], "seed pack differs from the one the state was seeded from")
    P = np.load(f"{prod}/rolling.npz", allow_pickle=True); Q = np.load(f"{st}/rolling.npz", allow_pickle=True)
    tp, ts_ = P["ts"].astype(np.int64), Q["ts"].astype(np.int64); check(np.array_equal(tp, ts_), "seeded time axis differs from production")
    dp, dq = np.asarray(P["data"], np.float16), np.asarray(Q["data"], np.float16)
    NW = dp.shape[1]; noncr = np.ones(NW, bool); noncr[cols] = False
    eq = lambda x, y: (x.view(np.uint16) == y.view(np.uint16)) | (np.isnan(x.astype(np.float32)) & np.isnan(y.astype(np.float32)))
    out = {"rows": int(len(tp)), "axis_end": E}
    out["noncrypto_cells_differing"] = int((~eq(dp[:, noncr], dq[:, noncr])).sum())
    check(out["noncrypto_cells_differing"] == 0, f"non-crypto columns changed: {out['noncrypto_cells_differing']} cells")
    old = np.flatnonzero(tp <= E); rts = S["rts"].astype(np.int64); pos = {int(t): i for i, t in enumerate(rts)}
    si = np.array([pos[int(tp[i])] for i in old]); sp = np.asarray(S["rows"], np.float16)[si]
    out["pre_axis_crypto_cells_differing_from_pack"] = int((~eq(sp, dq[old][:, cols])).sum())
    check(out["pre_axis_crypto_cells_differing_from_pack"] == 0, "pre-axis crypto rows differ from the seed pack")
    new = np.flatnonzero(tp > E)
    lp_rows = set()
    if R["inputs"].get("live_pack"):
        pass                                                   # filled rows are exempt below (named by the seed receipt count only)
    filled = int(R["counts"].get("live_pack_rows_filled", 0))
    a_, b_ = dp[new][:, cols], dq[new][:, cols]
    ch16 = ~eq(a_[:, :, 1:], b_[:, :, 1:]); prod_nan = np.isnan(a_[:, :, 3].astype(np.float32))
    out["post_axis_ch1_6_cells_differing_outside_live_filled"] = int((ch16.any(2) & ~prod_nan).sum())
    check(out["post_axis_ch1_6_cells_differing_outside_live_filled"] == 0, "post-axis crypto channels 1..6 changed on rows production holds")
    out["post_axis_rows_filled_where_production_had_none"] = int((ch16.any(2) & prod_nan).sum())
    check(out["post_axis_rows_filled_where_production_had_none"] <= filled, "more post-axis rows filled than the live pack says")
    c0 = ~eq(a_[:, :, 0], b_[:, :, 0]) & ~prod_nan
    out["post_axis_ch0_changed"] = int(c0.sum()); out["post_axis_ch0_changed_to_non_nan"] = int((c0 & ~np.isnan(b_[:, :, 0].astype(np.float32))).sum())
    check(out["post_axis_ch0_changed_to_non_nan"] == 0, "post-axis ch0 changed to a value (the no-cross-gap rule may only blank it)")
    B = np.load(f"{st}/boundary_raw.npz"); have = set(zip(B["ts"].astype(np.int64).tolist(), B["col"].astype(np.int64).tolist()))
    B16 = np.float32(np.float16(0.3))
    bound = np.argwhere(np.isfinite(dq[:, :, 0].astype(np.float32)) & (np.abs(dq[:, :, 0].astype(np.float32)) == B16))
    miss = [(int(tp[i]), int(j)) for i, j in bound if (int(tp[i]), int(j)) not in have and noncr[j] == False]
    out["bound_cells_crypto"] = int(sum(1 for i, j in bound if not noncr[j])); out["bound_cells_missing_from_table"] = miss[:20]
    check(not miss, f"{len(miss)} crypto bound cells have no raw value in the sparse table")
    out["boundary_table_cells"] = len(have); out["seed_counts"] = {k: R["counts"].get(k) for k in (
        "rows_from_seed_pack", "boundary_cells", "post_axis_ch0_cross_gap_set_nan", "live_pack_rows_filled", "events_advanced_after_axis",
        "replay_rows_missing_in_production_in_coverage", "replay_rows_in_production_coverage", "member_history_anchors_from_seed", "member_history_anchors_recomputed", "fetch_n")}
    return out


def take_lock(home):
    p = f"{home}/dl_quant_live/state/anchor.lock"; check(os.path.isfile(p), "executor anchor.lock missing")
    h = open(p, "r")
    try:
        fcntl.flock(h.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise Refused("executor anchor.lock is held (an anchor is in progress)")
    return h


def apply(pkg, bk, home, seeded, seed_pack, reserve, skip_lc):
    check(not os.path.exists(bk), "backup dir exists"); quiet(reserve)
    C, rep = preflight(pkg, home, seeded, seed_pack)
    rep["services_before"] = services_idle(C["services"]["stop"], skip_lc)
    lock = take_lock(home); quiet(reserve // 2)
    rec = {"verb": "apply", "VERDICT": rep["verdict"]["VERDICT"], "USER_OVERRIDE": rep["verdict"]["USER_OVERRIDE"], "started_utc": utc(), "home": home,
           "preflight": rep, "no_launchctl": skip_lc, "ignore_window": IGNORE_WINDOW, "stage": "backup"}
    os.makedirs(f"{bk}/files"); os.makedirs(f"{bk}/state")
    wr = lambda: json.dump(rec, open(f"{bk}/NC_INSTALL_RECEIPT.json", "w"), indent=1)
    wr()
    prod = f"{home}/wide_shadow/state"; sums = []
    for it in C["files"]:
        cur = f"{home}/{it['dest']}"
        if os.path.exists(cur):
            b = f"{bk}/files/{it['dest']}"; os.makedirs(os.path.dirname(b), exist_ok=True); shutil.copy2(cur, b); sums.append((sha(b), f"files/{it['dest']}"))
    for f in sorted(set(NC_STATE + OLD_STATE + ["generation.json"])):
        if os.path.exists(f"{prod}/{f}"): shutil.copy2(f"{prod}/{f}", f"{bk}/state/{f}"); sums.append((sha(f"{bk}/state/{f}"), f"state/{f}"))
    open(f"{bk}/SHA256SUMS", "w").write("".join(f"{s}  {p}\n" for s, p in sums))
    rec["backup"] = {"entries": len(sums), "sha256sums": sha(f"{bk}/SHA256SUMS")}; rec["stage"] = "installing_files"; wr()
    for it in C["files"]:
        cur = f"{home}/{it['dest']}"; os.makedirs(os.path.dirname(cur), exist_ok=True)
        mode = (os.stat(cur).st_mode & 0o777) if os.path.exists(cur) else 0o644
        atomic_copy(f"{pkg}/files/{it['dest']}", cur, mode)
        check(sha(cur) == it["candidate_sha256"], f"installed bytes differ: {it['dest']}")
    rec["stage"] = "installing_state"; wr()
    st = f"{seeded}/state"
    for f in NC_STATE + ["generation.json"]:                     # generation.json LAST: until it lands the old marker no longer matches ⇒ refuse
        atomic_copy(f"{st}/{f}", f"{prod}/{f}", 0o644)
        check(sha(f"{prod}/{f}") == sha(f"{st}/{f}"), f"installed state differs: {f}")
    rec["stage"] = "verifying"; wr()
    rec["producer_load"] = producer_loads(home, "apply")
    rec["installed"] = {it["dest"]: sha(f"{home}/{it['dest']}") for it in C["files"]}
    rec["state_installed"] = {f: sha(f"{prod}/{f}") for f in NC_STATE + ["generation.json"]}
    for u, s in C["unchanged"].items(): check(sha(f"{home}/{u}") == s, f"a kept file changed during install: {u}")
    rec["stage"] = "installed_not_started"; rec["completed_utc"] = utc(); wr()
    lock.close()
    return rec


def rollback(pkg, bk, home, downgraded, reserve, skip_lc):
    """--downgraded is required only when the NC producer has advanced the installed state (see below)."""
    quiet(reserve); C = json.load(open(f"{pkg}/INSTALL_CONTRACT.json"))
    check(os.path.isfile(f"{bk}/NC_INSTALL_RECEIPT.json") and os.path.isfile(f"{bk}/SHA256SUMS"), "no install backup at this path")
    for line in open(f"{bk}/SHA256SUMS"):
        s, p = line.rstrip("\n").split("  ", 1); check(sha(f"{bk}/{p}") == s, f"backup corrupted: {p}")
    prod = f"{home}/wide_shadow/state"; I = json.load(open(f"{bk}/NC_INSTALL_RECEIPT.json"))
    # which state goes back:
    #   the install did not complete, or it completed and the NC producer has NOT advanced the state since (every installed state file
    #   still has the installed bytes) => the backup's pre-install state IS the latest state: restore it (no bar is lost);
    #   the NC producer advanced the state => the pre-install state would lose bars: the downgraded CURRENT state is required.
    advanced = I.get("stage") == "installed_not_started" and any(
        (sha(f"{prod}/{f}") if os.path.exists(f"{prod}/{f}") else None) != s_ for f, s_ in I.get("state_installed", {}).items())
    if not advanced:
        src_state = f"{bk}/state"; state_source = "backup (pre-install state; the NC producer never advanced it)"
    else:
        check(downgraded, "the NC producer advanced the state since the install: run nc_downgrade_state.py on the CURRENT state and pass --downgraded")
        D = json.load(open(f"{downgraded}/DOWNGRADE_RECEIPT.json")); src_state = f"{downgraded}/state"; state_source = "downgraded current state"
        for f in NC_STATE:
            check(D["inputs"].get(f) == sha(f"{prod}/{f}"), f"the downgraded state was not made from the CURRENT state ({f}); re-run nc_downgrade_state.py")
    for f in OLD_STATE + ["generation.json"]: check(os.path.isfile(f"{src_state}/{f}"), f"state source misses {f}")
    rec = {"verb": "rollback", "VERDICT": I.get("VERDICT"), "USER_OVERRIDE": I.get("USER_OVERRIDE"), "started_utc": utc(), "home": home, "no_launchctl": skip_lc, "ignore_window": IGNORE_WINDOW, "state_source": state_source, "install_stage": I.get("stage"),
           "services_before": services_idle(C["services"]["stop"], skip_lc)}
    lock = take_lock(home); aside = f"{bk}/rollback_moved_aside_{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}"; os.makedirs(aside)
    wr = lambda: json.dump(rec, open(f"{aside}/NC_ROLLBACK_RECEIPT.json", "w"), indent=1)
    rec["stage"] = "restoring_files"; wr()
    for it in C["files"]:
        cur = f"{home}/{it['dest']}"
        if it["baseline_sha256"] is None:
            if os.path.exists(cur):
                m = f"{aside}/files/{it['dest']}"; os.makedirs(os.path.dirname(m), exist_ok=True); shutil.move(cur, m)
        else:
            b = f"{bk}/files/{it['dest']}"; check(sha(b) == it["baseline_sha256"], f"backup is not the baseline: {it['dest']}")
            atomic_copy(b, cur, os.stat(cur).st_mode & 0o777 if os.path.exists(cur) else 0o644)
            check(sha(cur) == it["baseline_sha256"], f"restored bytes differ: {it['dest']}")
    rec["stage"] = "restoring_state"; wr()
    os.makedirs(f"{aside}/state")
    for f in NC_STATE + ["generation.json"]:
        if os.path.exists(f"{prod}/{f}"): shutil.copy2(f"{prod}/{f}", f"{aside}/state/{f}")
    for f in ("boundary_raw.npz", "members_hist.npz"):
        if os.path.exists(f"{prod}/{f}"): os.remove(f"{prod}/{f}")          # a copy is in aside/state
    for f in OLD_STATE + ["generation.json"]:
        atomic_copy(f"{src_state}/{f}", f"{prod}/{f}", 0o644)
    rec["stage"] = "verifying"; wr()
    rec["producer_load"] = producer_loads(home, "rollback")
    check(sorted(rec["producer_load"]["state_files"]) == sorted(OLD_STATE), "restored producer is not the old one")
    rec["restored"] = {it["dest"]: (sha(f"{home}/{it['dest']}") if os.path.exists(f"{home}/{it['dest']}") else None) for it in C["files"]}
    rec["stage"] = "rolled_back_not_started"; rec["completed_utc"] = utc(); wr()
    lock.close()
    return rec


def vtag(r):
    return f"VERDICT={r.get('VERDICT')} USER_OVERRIDE={r.get('USER_OVERRIDE')}"


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("verb", choices=["preflight", "apply", "rollback"]); ap.add_argument("pkg"); ap.add_argument("bk", nargs="?")
    ap.add_argument("--seeded"); ap.add_argument("--seed-pack"); ap.add_argument("--downgraded"); ap.add_argument("--home", default=os.path.expanduser("~"))
    ap.add_argument("--reserve", type=int, default=20); ap.add_argument("--no-launchctl", action="store_true"); ap.add_argument("--ignore-window", action="store_true")
    a = ap.parse_args()
    real = os.path.realpath(os.path.expanduser("~"))
    if (a.no_launchctl or a.ignore_window) and os.path.realpath(a.home) == real:
        print("NC_INSTALL REFUSED: --no-launchctl / --ignore-window are rehearsal-only (need --home other than the real home)"); return 3
    global IGNORE_WINDOW; IGNORE_WINDOW = a.ignore_window
    try:
        if a.verb == "preflight":
            _, rep = preflight(a.pkg, a.home, a.seeded, a.seed_pack)
            print("NC_INSTALL PREFLIGHT_PASS", vtag(rep["verdict"]), json.dumps(rep, default=str)[:1500]); return 0
        if a.verb == "apply":
            check(a.bk and a.seeded and a.seed_pack, "apply needs <backup dir> --seeded --seed-pack")
            rec = apply(a.pkg, a.bk, a.home, a.seeded, a.seed_pack, a.reserve, a.no_launchctl)
        else:
            check(a.bk, "rollback needs <backup dir> [--downgraded D]")
            rec = rollback(a.pkg, a.bk, a.home, a.downgraded, a.reserve, a.no_launchctl)
        print("NC_INSTALL", rec["stage"], vtag(rec), json.dumps(rec.get("producer_load")), flush=True); return 0
    except Refused as e:
        print("NC_INSTALL REFUSED:", e, flush=True); return 3


if __name__ == "__main__":
    sys.exit(main())
