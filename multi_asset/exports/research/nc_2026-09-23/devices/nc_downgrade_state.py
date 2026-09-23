#!/usr/bin/env python3
"""F-2 option (ii) — state downgrade converter: NC-format producer state -> the OLD producer's format (6080073b / combo_stage fb5a9407).
DESIGN §F-2 (FREEZE b30e4afa5 + amendment 1: prices.npz -> boundary_raw.npz). Pure file transformation into a NEW directory; never
touches the input directory, ~/wide_shadow or ~/dl_quant_live.
What changes (and why the old code needs it):
  aux.ema          entries whose acc or last_ts is None (an NC reset: unknown settlement interval) are REMOVED — the old update
                   `est["acc"] + a * (rn - est["acc"])` / `max(ft - est["last_ts"], 1)` cannot take None; with the entry gone the old
                   code restarts that name exactly as for a name it never saw (est is None -> acc = rn).
  aux.ledger_tail  rows whose interval is None get the OLD rule's value — 6080073b L472-L473 compiled VERBATIM from the pinned file
                   (gap to the previous row, nearest of {1,2,4,6,8}, > 24 h / first row -> 8). Known intervals are kept as NC wrote them.
  aux              NC-only keys dropped: fetch_syms, prev_close_ts, nc_backfill_residual.
  rolling.npz, leg_returns_live.json   byte-copied.
  boundary_raw.npz, members_hist.npz   not copied (the old code has no reader for them).
  generation.json  re-signed with the OLD module's build_generation_record over the OLD STATE_FILES (module loaded from the pinned copy
                   with WIDE_SHADOW_HOME pointed at the output root).
usage: ~/wide_shadow/venv/bin/python nc_downgrade_state.py <NC state dir> <out root>   (writes <out root>/state/ + DOWNGRADE_RECEIPT.json)
env:   NC_OLD_PRODUCER (default ~/cc_tmp/news_20260923/producer_copy/shadow_loop_v3.py, sha 6080073b pinned)"""
import os, sys, json, hashlib, shutil, importlib.util

HOME = os.path.expanduser("~")
OLD = os.environ.get("NC_OLD_PRODUCER", f"{HOME}/cc_tmp/news_20260923/producer_copy/shadow_loop_v3.py")
OLD_SHA = "6080073964bffc621c893915b16f71ecafe093194f0b99a66a4463ee12c74e61"
NC_KEYS = ("fetch_syms", "prev_close_ts", "nc_backfill_residual")
NC_FILES = ("rolling.npz", "aux.json", "leg_returns_live.json", "boundary_raw.npz", "members_hist.npz")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def old_interval_fn(src_text):
    """6080073b L472-L473, verbatim, wrapped as old_iv(ft, led)."""
    lines = src_text.split("\n")
    l1, l2 = lines[471], lines[472]
    assert l1.strip() == "iv = (ft - led[-1][0]) / 3600.0 if led else 8.0", l1
    assert l2.strip() == "iv = float(min([1.0, 2.0, 4.0, 6.0, 8.0], key=lambda a: abs(a - (iv if 0 < iv <= 24 else 8.0))))", l2
    ns = {}
    exec("def old_iv(ft, led):\n    " + l1.strip() + "\n    " + l2.strip() + "\n    return iv\n", ns)
    return ns["old_iv"]


def load_old_module(out_root):
    os.environ["WIDE_SHADOW_HOME"] = out_root
    spec = importlib.util.spec_from_file_location(f"old_producer_{abs(hash(out_root))}", OLD)
    M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M)
    return M


def downgrade(nc_state, out_root):
    src = open(OLD, "rb").read(); assert hashlib.sha256(src).hexdigest() == OLD_SHA, "old producer copy is not 6080073b"
    old_iv = old_interval_fn(src.decode())
    for f in NC_FILES:
        assert os.path.exists(os.path.join(nc_state, f)), f"not an NC state: {f} missing"
    out_state = os.path.join(out_root, "state"); assert not os.path.exists(out_state), "refusing to overwrite"
    os.makedirs(out_state)
    rec = {"device_sha256": sha(os.path.abspath(__file__)), "old_producer_sha256": OLD_SHA,
           "inputs": {f: sha(os.path.join(nc_state, f)) for f in NC_FILES + ("generation.json",) if os.path.exists(os.path.join(nc_state, f))},
           "counts": {}}
    aux = json.load(open(os.path.join(nc_state, "aux.json")))
    removed = [s for s, e in aux.get("ema", {}).items() if (not isinstance(e, dict)) or e.get("acc") is None or e.get("last_ts") is None]
    aux["ema"] = {s: e for s, e in aux["ema"].items() if s not in set(removed)}
    filled = 0; filled_names = set(); known_differs = 0
    for s, rows in aux.get("ledger_tail", {}).items():
        new = []
        for r in rows:
            r = list(r)
            if len(r) < 3 or r[2] is None:
                iv = old_iv(int(r[0]), new)
                r = [r[0], r[1], iv]; filled += 1; filled_names.add(s)
            elif new and float(r[2]) != old_iv(int(r[0]), new):
                known_differs += 1          # kept as NC wrote it (ties -> larger vs the old rule's ties -> smaller); counted, not rewritten
                                            # (a tail's first row has no predecessor in the tail: not re-evaluable, not counted)
            new.append(r)
        aux["ledger_tail"][s] = new
    dropped = [k for k in NC_KEYS if k in aux]
    for k in dropped: aux.pop(k)
    with open(os.path.join(out_state, "aux.json"), "w") as f: json.dump(aux, f)
    for f in ("rolling.npz", "leg_returns_live.json"): shutil.copy2(os.path.join(nc_state, f), os.path.join(out_state, f))
    M = load_old_module(out_root)
    assert tuple(M.STATE_FILES) == ("rolling.npz", "aux.json", "leg_returns_live.json"), M.STATE_FILES
    M.atomic_json(os.path.join(out_state, "generation.json"), M.build_generation_record(out_state, int(aux["last_anchor"])))
    rec["counts"] = {"ema_entries_removed": len(removed), "ema_removed_names_first": sorted(removed)[:20], "ledger_iv_filled": filled,
                     "ledger_iv_filled_names": len(filled_names), "ledger_iv_known_differs_from_old_rule_kept": known_differs,
                     "aux_keys_dropped": dropped, "files_not_copied": ["boundary_raw.npz", "members_hist.npz"],
                     # entries of the NC state dir that are not NC STATE_FILES (weights/, target_*/ ...): format-identical, NOT handled here —
                     # the rollback procedure must carry them itself
                     "not_handled_entries": sorted(set(os.listdir(nc_state)) - set(NC_FILES) - {"generation.json"})}
    rec["outputs"] = {f: sha(os.path.join(out_state, f)) for f in sorted(os.listdir(out_state))}
    json.dump(rec, open(os.path.join(out_root, "DOWNGRADE_RECEIPT.json"), "w"), indent=1)
    return rec


def main():
    rec = downgrade(sys.argv[1], sys.argv[2])
    print("NC_DOWNGRADE_OK", json.dumps(rec["counts"]), flush=True)


if __name__ == "__main__":
    main()
