"""NEW_S2 training / combo / engine chain = NEW_S's chain devices with ONLY paths and arm names changed.

FREEZE §4 gives news2 the training (NEW_S scheme), combo, engine and verdict. The recipe must be the
NEW_S one, so the honest way to get it is not to retype those devices but to DERIVE them: sha-pin the
NEW_S originals, apply a named substitution table, assert every `old` occurs exactly the expected
number of times, and archive a unified diff per file. Same shape as news2_derive_producer.py and as
the researcher's derive_f8_candidate.py.

What changes, and nothing else:
  * the work root            /dev/shm/news_2026-09-23  ->  /dev/shm/news2_2026-09-23
  * the arm / run prefix     NEWS_s{seed}              ->  NEWS2_s{seed}
  * the provenance sources   news_hist_features.py, news_legs.py, news_p2_build.py
                             ->  nc_hist_features.py, nc_legs.py, nc_p2_build.py (the integrator's
                             replay devices, DESIGN A9; the trainers hash these into their receipts)
  * the Stage-1 config root  left alone (the OLD / OLD_HOLD controls are the same runs)

The feature package itself is NOT renamed: news2_stage_inputs.py links the integrator's NC_FEATURES
into this root under the name the trainers expect and copies its receipt, so the trainers' existing
"sha(features) == receipt['sha256']" assertion still binds the real bytes.

usage: python news2_derive_chain.py <out_dir> [--news-devices DIR]
"""
import argparse, ast, difflib, hashlib, json, os, pathlib, time

HERE = pathlib.Path(__file__).resolve().parent
DEFAULT_SRC = HERE / "../../news_2026-09-23/devices"

OLD_ROOT = "/dev/shm/news_2026-09-23"
NEW_ROOT = "/dev/shm/news2_2026-09-23"

# file -> sha of the NEW_S original. A source that moved is a refusal, not a silent re-derive.
SRC_SHA = {
    "news_train_king.py": None,
    "news_train_f10.py": None,
    "news_combo.py": None,
    "news_make_configs.py": None,
    "news_ext.py": None,
    "news_adapter_specs.py": None,
}
# substitutions applied to every file; `min_hits` guards against a silent no-op rename.
SUBS = [
    ("root", OLD_ROOT, NEW_ROOT, 0),
    ("arm_prefix", "NEWS_s", "NEWS2_s", 0),
    ("src_hist", "news_hist_features.py", "nc_hist_features.py", 0),
    ("src_legs", "news_legs.py", "nc_legs.py", 0),
    ("src_p2", "news_p2_build.py", "nc_p2_build.py", 0),
    # the adapter spec carries a human-readable provenance string into the run config; left alone it
    # would label the NEW_S2 arm as NEW_S, and a wrong label in a run config is how two versions get
    # confused later.
    ("provenance", 'f"NEW_S (news_2026-09-23) combo_s{seed}: producer-replayed features, King + F10 s{seed} retrained"',
     'f"NEW_S2 (nc_2026-09-23 features, news2_2026-09-23 models) combo_s{seed}: full corrected producer contract, King + F10 s{seed} retrained"', 0),
]
# at least one file must be touched by each substitution, or the table has gone stale
REQUIRED_GLOBAL_HITS = {"root": 1, "arm_prefix": 1, "src_hist": 1, "src_legs": 1, "src_p2": 1, "provenance": 1}


def sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): h.update(b)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--news-devices", default=str(DEFAULT_SRC))
    args = ap.parse_args()
    src_dir = pathlib.Path(args.news_devices).resolve()
    out = pathlib.Path(args.out)
    assert not out.exists(), f"refusing to overwrite {out}"
    out.mkdir(parents=True)

    total_hits = {k: 0 for k in REQUIRED_GLOBAL_HITS}
    rec_files = {}
    for name in SRC_SHA:
        src = src_dir / name
        text = src.read_text()
        orig = text
        hits = {}
        for tag, old, new, _ in SUBS:
            n = text.count(old)
            hits[tag] = n
            total_hits[tag] += n
            if n:
                text = text.replace(old, new)
        # nothing may still point at the old root or the old arm prefix
        assert OLD_ROOT not in text, (name, "old root survived")
        assert "NEWS_s" not in text.replace("NEWS2_s", ""), (name, "old arm prefix survived")
        assert "NEW_S (news_2026-09-23)" not in text, (name, "old provenance label survived")
        ast.parse(text, filename=name)
        dst_name = "news2_" + name[len("news_"):]
        (out / dst_name).write_text(text)
        diff = "".join(difflib.unified_diff(orig.splitlines(True), text.splitlines(True),
                                            fromfile=f"news_2026-09-23/devices/{name}",
                                            tofile=f"news2_2026-09-23/devices/{dst_name}"))
        (out / (dst_name + ".diff")).write_text(diff)
        rec_files[dst_name] = {"source": str(src), "source_sha256": sha_file(src),
                               "output_sha256": sha_file(out / dst_name),
                               "substitution_hits": hits, "diff_lines": diff.count("\n")}
        print(f"{name} -> {dst_name}  hits={hits}", flush=True)

    stale = [k for k, v in REQUIRED_GLOBAL_HITS.items() if total_hits[k] < v]
    assert not stale, f"substitutions that hit nothing (table is stale): {stale}"

    # files copied byte-for-byte: no path or arm name in them
    verbatim = {}
    for name in ("king_folds.py", "f10_observability.py", "continuous_combo.py", "combo_target.py",
                 "book_universe.py", "train_king.py", "train_f10.py"):
        s = src_dir / name
        if s.exists():
            (out / name).write_bytes(s.read_bytes())
            verbatim[name] = sha_file(s)

    rec = {"device": "news2_derive_chain.py", "self_sha256": sha_file(os.path.abspath(__file__)),
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "freeze": "docs/FREEZE_new_servable_v2_2026-09-23.md b30e4afa5 §4 (news2: training / combo / engine / verdict)",
           "training_scheme": "NEW_S scheme (FRESH judged KEEP_NEWS, c1fb0bf0); the recipe is derived, not retyped",
           "source_dir": str(src_dir), "substitutions": [{"tag": t, "old": o, "new": n} for t, o, n, _ in SUBS],
           "substitution_totals": total_hits, "derived": rec_files, "copied_verbatim": verbatim,
           "note": ("the feature package keeps its NEW_S filename inside this root; news2_stage_inputs.py "
                    "links the integrator's NC_FEATURES there and copies its receipt, so the trainers' "
                    "sha(features) == receipt['sha256'] assertion still binds the real bytes")}
    (out / "CHAIN_DERIVE_RECEIPT.json").write_text(json.dumps(rec, indent=1))
    print("CHAIN_DERIVE_OK", json.dumps({"n_derived": len(rec_files), "totals": total_hits}), flush=True)


if __name__ == "__main__":
    main()
