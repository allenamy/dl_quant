#!/usr/bin/env python3
"""dlarch_derive_chain.py — DERIVE the combo->engine chain devices for the T0 family.

Same shape as news2_derive_chain.py / news2_derive_producer.py: do NOT retype the devices. Instead
  * sha-pin each original,
  * apply a NAMED substitution table,
  * ASSERT every `old` occurs exactly the expected number of times,
  * archive a unified diff per file,
so that "I changed only these things" is verifiable by a third party instead of being my word.

Why the chain needs deriving at all (measured, not assumed):
  * news2_combo.py pins `--seed choices=(42, 2027)` -- 6 of the family's 8 seeds would be REFUSED;
  * the family's F10 artifacts live under /workspace (T0 wrote them there), reached from the chain root
    through a symlink, so continuous_combo.verify_training's STRING comparison of fold-artifact paths
    fails on paths that are the same FILES;
  * news2_adapter_specs.py loops a hardcoded ("42","2027") and names the arm NEWS2_s{seed}.

Nothing else changes. ovn_adapter.py and bt_launch.py take explicit paths and are used UNMODIFIED.

READ-ONLY on the originals; writes only under /workspace/dlarch_2026-09-24/chain/devices/.
usage: env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B dlarch_derive_chain.py \
         PATH,HOME,LC_CTYPE <outdir>
"""
import os, sys, json, time, difflib, hashlib

SEEDS = (42, 2027, 7, 11, 23, 101, 3, 5)          # DECISION_RULE ... 038e8e78f revision 1
SRC = {
    "news2_combo.py": ("/dev/shm/pnoise_2026-09-24/devices/news2_combo.py",
                       "3a1e635c5041f28c76053a0f29f8a29063accd5fc8c2e894de0b7c8cfa174082"),
    "news2_adapter_specs.py": ("/dev/shm/news2_2026-09-23/devices/news2_adapter_specs.py",
                               "3d0ca94ad93da3fa73c8a78222141c475c0cadf6ad39de838c468c8ed3673dc5"),
}
# Used UNMODIFIED, sha-pinned. The first three are IMPORTED BY the derived combo (directly or through
# continuous_combo), so they are symlinked next to it -- a device directory that is missing a sibling its
# own import line names is not a device directory. combo_target.py resolves its ROOT from __file__, and a
# symlink resolves to the upstream tree, so it reads the SAME sha-pinned producer source it always did
# (combo_target asserts that sha itself, so this is checked, not assumed).
SIBLINGS = {
    "continuous_combo.py": ("/dev/shm/news2_2026-09-23/devices/continuous_combo.py",
                            "1501c9f63641bf447c4cb33661d08da25ced0948f9fae63cebb44cdfd1995d21"),
    "combo_target.py": ("/dev/shm/news2_2026-09-23/devices/combo_target.py",
                        "d7577e824298fb90a554f35ac9c4d634202a4ed7e4e00cabc597a2d4eafdb544"),
    "book_universe.py": ("/dev/shm/news2_2026-09-23/devices/book_universe.py",
                         "90e332cc27cf8f34aabcac13f9829f84e463ffa900efbe554e17c07436e8dcca"),
}
UNMODIFIED = {
    "/dev/shm/news2_2026-09-23/engine/ovn_adapter.py": "17555e56362c53ce4e961e0d8cb050be65cddae31088b275f190eecacd5794ea",
    "/dev/shm/news2_2026-09-23/engine/bt_launch.py": "393a8dc8d43193f6cac37ec39700a0263b5d459f5571065528448745d50281cb",
}

VERIFY_WRAPPER = '''from continuous_combo import evolve, verify_training as _verify_training_upstream


def verify_training(out, rec, seed, sha):
    """DLARCH substitution 2: continuous_combo.verify_training, with the fold-artifact path set compared
    by REALPATH instead of by string.

    Why: the chain root reaches the family's F10 fold artifacts through a symlink, so the paths recorded
    in TRAIN_RECEIPT.json and the paths `out/tag/name` spells are different STRINGS for the SAME FILES.
    The check's CONTENT is preserved exactly -- the same artifact set, the same per-file sha256, the same
    per-fold identity of seed/fold/inputs/sources. Only the assumption that the caller spells the path
    the same way is dropped. Nothing is relaxed: a missing or extra artifact, a changed byte, or a
    mismatched fold identity still raises.
    """
    import pathlib as _pl
    if rec.get("seed") != seed: raise ValueError("wrong training seed")
    exp = {os.path.realpath(str(_pl.Path(out) / tag / name)) for tag in rec["folds"]
           for name in ("FOLD_RECEIPT.json", "model.pt", "scores.npz")}
    got = {os.path.realpath(p) for p in rec.get("fold_artifacts", {})}
    if got != exp:
        raise ValueError("fold artifact set (realpath-normalised): %d recorded vs %d expected"
                         % (len(got), len(exp)))
    for p, h in rec["fold_artifacts"].items():
        if sha(p) != h: raise ValueError("fold artifact drift:" + p)
    for tag in rec["folds"]:
        rr = json.loads((_pl.Path(out) / tag / "FOLD_RECEIPT.json").read_text())
        if rr["seed"] != seed or rr["fold"] != tag or rr["inputs"] != rec["inputs"] or rr["sources"] != rec["sources"]:
            raise ValueError("fold identity")
'''

SUBS = {
    "news2_combo.py": [
        ("choices=(42, 2027)", "choices=" + repr(SEEDS), 1,
         "the family's 8 seeds are pinned by the decision rule; 6 of them would otherwise be REFUSED"),
        ("from continuous_combo import evolve, verify_training", VERIFY_WRAPPER.rstrip("\n"), 1,
         "realpath-normalised fold-artifact comparison; see the wrapper's own docstring"),
    ],
    "news2_adapter_specs.py": [
        ('for seed in ("42", "2027"):',
         'ARM = sys.argv[4]   # DLARCH: the arm name is PASSED IN so it has exactly one source of truth\n'
         '                    # (dlarch_chain_run). It used to be rebuilt as f"DLARCH_T0_s{seed}" here and in\n'
         '                    # three other places; the copies drifted the moment a second arm existed\n'
         '                    # (--reference), and bt_objb_targets caught it as arm_mismatch.\n'
         'for seed in [sys.argv[3]]:', 1,
         "one seed per invocation from argv, and the ARM name from argv too (single source of truth)"),
        ('"arm": f"NEWS2_s{seed}"', '"arm": ARM', 1,
         "arm comes from argv, never rebuilt here; distinct from the in-service NEWS2 runs by construction"),
        ('ADAPTER_SPEC_NEWS2_s{seed}.json', 'ADAPTER_SPEC_{ARM}.json', 1,
         "output file name follows the arm name, which now has one source"),
        ('base = json.load(open(f"/workspace/old_vs_new_2026-09-23/devices/ADAPTER_SPEC_NEW_s{seed}.json"))',
         'base = json.load(open("/workspace/old_vs_new_2026-09-23/devices/ADAPTER_SPEC_NEW_s42.json"))\n'
         '    _b2 = json.load(open("/workspace/old_vs_new_2026-09-23/devices/ADAPTER_SPEC_NEW_s2027.json"))\n'
         '    for _k in ("price_meta", "universe", "window_first_anchor"):\n'
         '        assert json.dumps(base[_k], sort_keys=True) == json.dumps(_b2[_k], sort_keys=True), \\\n'
         '            f"DLARCH: base spec field {_k} is NOT seed-independent; using s42 for all seeds would be wrong"',
         1,
         "a base spec exists only for seeds 42/2027; the three fields copied from it are seed-independent, "
         "which is now ASSERTED at run time against the other base rather than assumed"),
    ],
}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def main():
    WL = set(sys.argv[1].split(",")); extra = sorted(set(os.environ) - WL)
    assert not extra, f"env outside whitelist: {extra}"
    outdir = sys.argv[2]; os.makedirs(outdir, exist_ok=True)
    rec = {"device": "dlarch_derive_chain.py", "self_sha256": sha(os.path.abspath(__file__)),
           "pattern": "news2_derive_chain.py (sha-pin + named substitution table + occurrence assertions + archived diffs)",
           "seeds": list(SEEDS), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "used_unmodified": {}, "derived": {}}
    for p, want in UNMODIFIED.items():
        got = sha(p); assert got == want, f"{p}: sha {got[:16]} != pinned {want[:16]}"
        rec["used_unmodified"][p] = got
    rec["siblings_symlinked"] = {}
    for nm, (p, want) in SIBLINGS.items():
        got = sha(p); assert got == want, f"{nm}: sha {got[:16]} != pinned {want[:16]}"
        dst = os.path.join(outdir, nm)
        if os.path.lexists(dst): os.unlink(dst)
        os.symlink(p, dst)
        rec["siblings_symlinked"][nm] = {"target": p, "sha256": got}
    # a device dir that cannot satisfy its own imports is not a device dir: prove it can.
    import importlib.util as _ilu
    for nm in list(SIBLINGS) + list(SRC):
        assert os.path.exists(os.path.join(outdir, nm)), f"{nm} missing from {outdir}"
    for name, (path, want) in SRC.items():
        got = sha(path); assert got == want, f"{name}: sha {got[:16]} != pinned {want[:16]}"
        src = open(path, encoding="utf-8").read()
        out = src; applied = []
        for old, new, n_exp, why in SUBS[name]:
            n = out.count(old)
            assert n == n_exp, f"{name}: '{old[:50]}' occurs {n} times, expected {n_exp}"
            out = out.replace(old, new)
            applied.append({"old": old, "new_first_80": new[:80], "occurrences": n, "why": why})
        assert out != src, f"{name}: substitution produced an identical file"
        dst = os.path.join(outdir, name)
        open(dst, "w", encoding="utf-8").write(out)
        diff = "".join(difflib.unified_diff(src.splitlines(True), out.splitlines(True),
                                            fromfile=f"upstream/{name}", tofile=f"dlarch/{name}"))
        open(dst + ".diff", "w", encoding="utf-8").write(diff)
        rec["derived"][name] = {"upstream": path, "upstream_sha256": got, "derived_path": dst,
                                "derived_sha256": sha(dst), "diff_path": dst + ".diff",
                                "diff_sha256": sha(dst + ".diff"),
                                "diff_added_lines": sum(1 for l in diff.splitlines() if l.startswith("+") and not l.startswith("+++")),
                                "diff_removed_lines": sum(1 for l in diff.splitlines() if l.startswith("-") and not l.startswith("---")),
                                "substitutions": applied}
        print(f"derived {name}: {len(applied)} substitutions, "
              f"+{rec['derived'][name]['diff_added_lines']}/-{rec['derived'][name]['diff_removed_lines']} lines", flush=True)
    op = os.path.join(outdir, "DERIVE_CHAIN.json")
    tmp = op + ".tmp"; open(tmp, "w").write(json.dumps(rec, indent=1, allow_nan=False)); os.replace(tmp, op)
    print(f"DLARCH_DERIVE_CHAIN files={len(rec['derived'])} unmodified={len(rec['used_unmodified'])} json={sha(op)[:16]}", flush=True)


if __name__ == "__main__":
    main()
