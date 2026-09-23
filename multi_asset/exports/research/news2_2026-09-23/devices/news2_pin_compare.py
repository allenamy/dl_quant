"""One-time comparison lead asked for: is news2's B-part text the same as the one nc ships?

It turned out not to be a text comparison at all. `nc_derive_producer.py` does not COPY the B part --
it IMPORTS news2_derive_producer.py at a pinned sha and calls its patch functions (nc L36-L39, L463-
L467). So there is no second copy to reconcile; there is a PIN, and the only question is whether the
pin is current and whether moving it changes anything.

What this device does:
  1. builds the nc tree twice, once with each news2 version (the pinned one and the current one),
  2. compares the two trees file by file,
  3. reports what changes in the receipt, in particular nc's record of which families it skipped.

The point of (3): nc asserts `set(skipped families) <= {"D11", "D13"}`. That assertion is satisfied by
an EMPTY skipped list. The pinned news2 still carried the D11/D13 patch bodies, so nc skipped them and
recorded it; the current news2 has them removed (lead's ruling, DESIGN A5), so nc skips nothing and
records nothing -- and the guard still passes. After the bump, nc can no longer demonstrate that
D11/D13 were deliberately excluded rather than never present. Same family as the vacuous-validator
problems this project has been tracking; it lands here as a consequence of the removal.

usage: python news2_pin_compare.py <work_dir> <out.json> <nc_derive_producer.py> <pinned_news2.py> <current_news2.py>
"""
import difflib, filecmp, hashlib, json, os, shutil, subprocess, sys, time


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def build(nc_dev, news2_dev, out_dir, env):
    e = dict(env)
    e["NC_NEWS2_DEVICE"] = news2_dev
    src = open(nc_dev).read()
    want = sha(news2_dev)
    patched = os.path.join(os.path.dirname(out_dir), "nc_" + want[:8] + ".py")
    # the pin is what we are varying, so it is rewritten to the version under test and recorded
    import re
    new_src, n = re.subn(r'("news2_device": ")[a-f0-9]{64}(")', r"\g<1>" + want + r"\g<2>", src)
    assert n == 1, f"expected exactly one news2_device pin, found {n}"
    open(patched, "w").write(new_src)
    r = subprocess.run([sys.executable, patched, out_dir], capture_output=True, text=True, env=e)
    return r, patched


def tree_files(root):
    out = []
    for dirpath, _, names in os.walk(root):
        for n in sorted(names):
            p = os.path.join(dirpath, n)
            out.append(os.path.relpath(p, root))
    return sorted(out)


def main():
    work, out_path, nc_dev, pinned, current = sys.argv[1:6]
    os.makedirs(work, exist_ok=True)
    t0 = time.time()
    env = dict(os.environ)
    trees = {}
    runs = {}
    for tag, dev in (("pinned", pinned), ("current", current)):
        d = os.path.join(work, "tree_" + tag)
        shutil.rmtree(d, ignore_errors=True)
        r, used = build(nc_dev, dev, d, env)
        runs[tag] = {"news2_device": dev, "news2_sha256": sha(dev), "rc": r.returncode,
                     "stderr_tail": r.stderr[-400:] if r.returncode else "", "nc_variant": used}
        assert r.returncode == 0, (tag, r.stderr[-1500:])
        trees[tag] = d
        print(f"built {tag}: news2 {sha(dev)[:12]} -> {d}", flush=True)

    fa, fb = tree_files(trees["pinned"]), tree_files(trees["current"])
    same_names = fa == fb
    differing, identical = [], []
    for rel in fa:
        a = os.path.join(trees["pinned"], rel)
        b = os.path.join(trees["current"], rel)
        if not os.path.exists(b):
            differing.append({"file": rel, "why": "absent in current"}); continue
        (identical if filecmp.cmp(a, b, shallow=False) else differing).append(
            {"file": rel, "sha_pinned": sha(a), "sha_current": sha(b)} if not filecmp.cmp(a, b, shallow=False) else rel)

    # the producer source files are what gets deployed; the receipt is metadata
    PRODUCER = [f for f in fa if f.endswith(".py") and f != "PATCH_RECEIPT.json"]
    prod_diff = [d for d in differing if isinstance(d, dict) and d["file"] in PRODUCER]

    rp = json.load(open(os.path.join(trees["pinned"], "PATCH_RECEIPT.json")))
    rc = json.load(open(os.path.join(trees["current"], "PATCH_RECEIPT.json")))
    skipped = {"pinned": rp.get("news2_skipped_tags"), "current": rc.get("news2_skipped_tags")}
    guard = {k: (set(t.split(":")[0] for t in (v or [])) <= {"D11", "D13"}) for k, v in skipped.items()}
    receipt_diff = "".join(difflib.unified_diff(
        json.dumps(rp, indent=1).splitlines(True), json.dumps(rc, indent=1).splitlines(True),
        fromfile="PATCH_RECEIPT.json (pinned news2)", tofile="PATCH_RECEIPT.json (current news2)"))

    rec = {"device": "news2_pin_compare.py", "self_sha256": sha(os.path.abspath(__file__)),
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "question": "lead: compare news2's B-part text with nc's; list differences and judge which is right",
           "finding": ("nc does not copy the B part, it imports news2_derive_producer.py at a pinned sha "
                       "(nc L36-L39, L463-L467). There is no divergent text. The live question is the pin."),
           "runs": runs, "same_file_set": same_names,
           "n_files": len(fa), "n_identical": len(identical), "differing": differing,
           "producer_sources_differ": prod_diff,
           "PRODUCER_SOURCES_BITWISE_EQUAL": not prod_diff,
           "nc_skipped_tags": skipped, "nc_guard_set_le_D11_D13": guard,
           "GUARD_IS_VACUOUS_UNDER_BUMP": bool(guard["current"] and not skipped["current"]),
           "receipt_diff": receipt_diff,
           "seconds": round(time.time() - t0, 1)}
    json.dump(rec, open(out_path, "w"), indent=1)
    print(f"NEWS2_PIN_COMPARE producer_sources_bitwise_equal={rec['PRODUCER_SOURCES_BITWISE_EQUAL']} "
          f"files={len(fa)} identical={len(identical)} differing={len(differing)} "
          f"guard_vacuous_under_bump={rec['GUARD_IS_VACUOUS_UNDER_BUMP']} receipt_sha256={sha(out_path)}", flush=True)


if __name__ == "__main__":
    main()
