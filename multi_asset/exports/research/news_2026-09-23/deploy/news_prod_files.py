"""NEW_S deploy file edits on the producer tree (DEPLOY_new_servable_models_2026-09-23.md §A1 / §B1). Producer must be STOPPED
(launchctl bootout of com.hsy.shadowloop AND com.hsy.combolive) — refuses if shadow.lock names a live PID. Every edited file is first
copied to <backup_dir> with its sha; MANIFEST.json is rewritten with the new shas so shadow_loop_v3.load_bundle (L162-171) accepts it.
  fetchlist <added_names.json> <backup_dir>   : R10-B01 — shadow_bundle/config.json gains the NEW key `symbols_fetch` := the 450 of symbols_live
                                                 (order kept) + the added names (sorted); `symbols_live` (the HOLDING universe, target-file universe,
                                                 EXIT keep mask) stays the 450, byte for byte; every other key untouched (asserted); MANIFEST config.json
                                                 sha updated. Requires the patched producer (shadow_loop_v3.py ed11d731) — the current file ignores the key.
  models <slow2026.txt> <f10_live_s42_np.npz> <backup_dir> : replace shadow_bundle/slow2026.txt and fea171/f10_live_s42_np.npz;
                                                 MANIFEST slow2026.txt sha updated; prints the two executor pins
                                                 (booster_sha_pin = MANIFEST sha of slow2026.txt; f10_sha_pin = sha256 of the npz bytes).
"""
import os, sys, json, hashlib, shutil
WS = os.environ.get("WIDE_SHADOW_HOME", os.path.expanduser("~/wide_shadow")); B = f"{WS}/shadow_bundle"   # rehearsal: WIDE_SHADOW_HOME=<copy>


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def producer_stopped():
    lk = f"{WS}/shadow.lock"
    if os.path.exists(lk):
        try:
            pid = int(open(lk).read().strip()); os.kill(pid, 0); return False
        except (ValueError, ProcessLookupError, PermissionError):
            return True
    return True


def backup(paths, bdir):
    os.makedirs(bdir, exist_ok=True); rec = {}
    for p in paths:
        dst = os.path.join(bdir, os.path.relpath(p, WS).replace("/", "__")); shutil.copy2(p, dst); rec[p] = {"backup": dst, "sha256": sha(p)}
        assert sha(dst) == rec[p]["sha256"]
    json.dump(rec, open(os.path.join(bdir, "BACKUP_MANIFEST.json"), "w"), indent=1); return rec


def write_atomic(p, raw):
    tmp = p + ".tmp"; open(tmp, "wb").write(raw); os.replace(tmp, p)


def main():
    assert producer_stopped(), "REFUSE: shadow.lock names a live producer PID — stop com.hsy.shadowloop first"
    cmd = sys.argv[1]; man = json.load(open(f"{B}/MANIFEST.json"))
    for fn, s in man.items(): assert sha(f"{B}/{fn}") == s, f"REFUSE: bundle already inconsistent: {fn}"
    if cmd == "fetchlist":
        added = json.load(open(sys.argv[2])); bdir = sys.argv[3]
        cfg = json.load(open(f"{B}/config.json")); old = list(cfg["symbols_live"])
        assert len(old) == 450 and not (set(added) & set(old)) and set(added) <= set(cfg["symbols_panel"]), "fetch list precondition"
        backup([f"{B}/config.json", f"{B}/MANIFEST.json"], bdir)
        assert "symbols_fetch" not in cfg, "config already has symbols_fetch"
        new = dict(cfg); new["symbols_fetch"] = old + sorted(added)
        raw = json.dumps(new).encode(); write_atomic(f"{B}/config.json", raw)
        chk = json.load(open(f"{B}/config.json"))
        assert {k: v for k, v in chk.items() if k != "symbols_fetch"} == cfg and chk["symbols_live"] == old
        man["config.json"] = sha(f"{B}/config.json"); write_atomic(f"{B}/MANIFEST.json", json.dumps(man, indent=1).encode())
        print(json.dumps({"config.json": {"old": json.load(open(os.path.join(bdir, "BACKUP_MANIFEST.json")))[f"{B}/config.json"]["sha256"], "new": man["config.json"]},
                          "MANIFEST.json_new": sha(f"{B}/MANIFEST.json"), "n_live(holding)": len(new["symbols_live"]), "n_fetch": len(new["symbols_fetch"])}))
    elif cmd == "models":
        king, f10, bdir = sys.argv[2:5]
        backup([f"{B}/slow2026.txt", f"{B}/MANIFEST.json", f"{WS}/fea171/f10_live_s42_np.npz"], bdir)
        shutil.copy2(king, f"{B}/slow2026.txt.new"); os.replace(f"{B}/slow2026.txt.new", f"{B}/slow2026.txt")
        shutil.copy2(f10, f"{WS}/fea171/f10_live_s42_np.npz.new"); os.replace(f"{WS}/fea171/f10_live_s42_np.npz.new", f"{WS}/fea171/f10_live_s42_np.npz")
        man["slow2026.txt"] = sha(f"{B}/slow2026.txt"); write_atomic(f"{B}/MANIFEST.json", json.dumps(man, indent=1).encode())
        assert sha(f"{B}/slow2026.txt") == sha(king) and sha(f"{WS}/fea171/f10_live_s42_np.npz") == sha(f10)
        print(json.dumps({"booster_sha_pin": man["slow2026.txt"], "f10_sha_pin": sha(f"{WS}/fea171/f10_live_s42_np.npz"), "MANIFEST.json_new": sha(f"{B}/MANIFEST.json")}))
    else:
        raise SystemExit("usage: fetchlist|models ...")


if __name__ == "__main__":
    main()
