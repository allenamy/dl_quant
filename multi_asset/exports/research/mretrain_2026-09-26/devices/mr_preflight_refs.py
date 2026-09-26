"""mr_preflight_refs.py — family-level pre-flight of the King monthly-retrain family (fresh2, 2026-09-27; E-0926 A0_m0 prep STOP).
The 18:35Z run died 25 minutes in on a file the combo step reads (vendored combo_stage.py: combo_target reads it from devices/..,
prep had put it under the arm). mr_combo.py --preflight covers the combo step's own reads; THIS device covers every other
reference outside the arm that a later step (adapter, configs, gates, engine queue, reading device) reads, so a missing or changed
one fails before any training. The list is DERIVED from the guarded devices (their module-level literals / shell assignments),
not written a second time here: a reference added to one of them tomorrow is checked without editing this file, and a device
whose constant can no longer be found fails this pre-flight (the parser is asserted, not trusted).
usage: python mr_preflight_refs.py <devices_dir>        prints MR_PREFLIGHT_REFS PASS|FAIL <json>; rc 0 only on PASS"""
import ast, hashlib, json, os, re, sys

D = sys.argv[1]
checks, bad = [], []


def parser_fail(msg):                                    # on stdout, line-anchored like the verdict, so a waiter sees the reason
    print(f"MR_PREFLIGHT_REFS FAIL parser: {msg}", flush=True); sys.exit(1)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def consts(fn, names):
    """module-level literal assignments of a device, by name; every requested name must be found exactly once"""
    t = ast.parse(open(os.path.join(D, fn)).read()); out = {}
    for node in t.body:
        if isinstance(node, ast.Assign):
            for tg in node.targets:
                if isinstance(tg, ast.Name) and tg.id in names:
                    try: out.setdefault(tg.id, []).append(ast.literal_eval(node.value))
                    except ValueError: out.setdefault(tg.id, []).append(("NOT_LITERAL", ast.unparse(node.value)))
    for n in names:
        if len(out.get(n, [])) != 1: parser_fail(f"{fn} {n} found {len(out.get(n, []))}x")
    return {n: out[n][0] for n in names}


def sh_assign(fn, name):
    hits = re.findall(rf"(?:^|[;\s]){name}=([^\s;]+)", open(os.path.join(D, fn)).read())
    if len(set(hits)) != 1: parser_fail(f"{fn} {name}= found {sorted(set(hits))}")
    return hits[0]


def need(p, want_sha=None, why=""):
    item = {"path": p, "why": why}
    if not os.path.isfile(p): item["result"] = "MISSING"; bad.append(item)
    elif want_sha is not None:
        got = sha(p); item["result"] = "OK" if got == want_sha else f"SHA {got[:16]} != {want_sha[:16]}"
        if got != want_sha: bad.append(item)
    else: item["result"] = "EXISTS"
    checks.append(item)


# mr_gates.py: G2/G3 references (in-service King, legs, combo arrays, pinned X targets)
g = consts("mr_gates.py", ["N", "KING_SHA", "LEGS_SHA"]); N = g["N"]
need(f"{N}/work/king/KING_OOF.npz", g["KING_SHA"], "G2 reference")
need(f"{N}/work/legs.npz", g["LEGS_SHA"], "G3 legs reference")
# mr_prep.sh reads the in-service X run configs from the same root as mr_gates (asserted, not assumed)
NP = sh_assign("mr_prep.sh", "N")
if NP != N: bad.append({"path": "mr_prep.sh N=", "result": f"{NP} != mr_gates N {N}"})
for s in ("42", "2027"):
    for pol in ("literal", "scaled_diagnostic"): need(f"{N}/work/combo_s{s}/{pol}.npz", None, "G3 combo reference")
    cp = f"{N}/configs/RUN_CONFIG_NEWS2_s{s}X_2026-09-23.json"; need(cp, None, "mr_prep config derivation / G3")
    if os.path.isfile(cp):
        runs = [r for r in json.load(open(cp))["runs"] if r["tag"] == f"NEWS2_s{s}X|scaled|rule|raw|UAFE"]
        if len(runs) != 1: bad.append({"path": cp, "result": f"{len(runs)} base-tag runs"})
        else:
            for src in runs[0]["targets"]["sources"]: need(src["npz"], src["npz_sha256"], "G3 pinned in-service X targets")
# news2_adapter_specs.py: the Stage-1 base spec each arm's spec copies price_meta / universe from (those are sha-pinned in it)
m = re.findall(r'"(/[^"]*ADAPTER_SPEC_NEW_s)\{seed\}\.json"', open(os.path.join(D, "news2_adapter_specs.py")).read())
if len(m) != 1: parser_fail(f"news2_adapter_specs base spec found {m}")
for s in ("42", "2027"):
    bp = f"{m[0]}{s}.json"; need(bp, None, "adapter base spec")
    if os.path.isfile(bp):
        b = json.load(open(bp))
        for k in ("price_meta", "universe"): need(b[k]["path"], b[k]["sha256"], f"adapter {k} (sha pinned in base spec)")
# engine devices run from the news2 root, and the engine queue's own helpers
for f in ("ovn_adapter.py", "bt_launch.py"): need(f"{N}/engine/{f}", None, "adapter / engine")
for v in ("FSAVE", "GATE"): need(sh_assign("mr_engine_queue.sh", v), None, f"engine queue {v}")
# mr_read.py: frozen statistics module and the in-service X baseline series
r = consts("mr_read.py", ["ENG", "NS_SHA", "EXT"])
need(f"{r['ENG']}/news_stats.py", r["NS_SHA"], "reading device news_stats")
for f in ("bt_tables.py", "bt_driver_lib.py"): need(f"{r['ENG']}/{f}", None, "reading device import")
for s, (p, h) in r["EXT"].items(): need(p, h, f"reading device X baseline s{s}")

ok = not bad
print("MR_PREFLIGHT_REFS", "PASS" if ok else "FAIL", json.dumps({"n_checked": len(checks), "bad": bad}), flush=True)
json.dump({"device": "mr_preflight_refs.py", "self_sha256": sha(os.path.abspath(__file__)), "checks": checks, "bad": bad, "PASS": ok},
          sys.stderr, indent=1)
sys.exit(0 if ok else 1)
