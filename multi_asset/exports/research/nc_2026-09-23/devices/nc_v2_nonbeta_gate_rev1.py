#!/usr/bin/env python3
"""Gate 3' REVISION 1 (lead ruling 2026-09-25 ~05:10Z, written and committed BEFORE judging). READ-ONLY re-judgement of the sandboxes an
nc_v2_nonbeta_gate.py run already built (no combo is re-run). Rule text (the lead's four items, operationalised):

  1. CLOSED exclusion list for meta_json of the mini feature files — only these fields may differ, and each difference must map to a
     specific v2 change, else FAIL:
       self_sha256  (dlw_fea82.npz, f8_fea89.npz): base value == sha256 of the BASE tree's device file and of the base sandbox's copy
                    (fea171/dlw_features.py resp. fea171/f8_higher_order_features.py); v2 value == the same for the V2 tree / v2 sandbox;
       cache_sha256 (both files): each side's value == sha256 of that sandbox's featws/mini/cache.npz, AND the two caches differ only by
                    "v2 writes NaN into channel 0": same keys; ts, symbols, ch, ret_f32 and data[:, :, 1:] bitwise equal; v2 data[:, :, 0]
                    all NaN; base data[:, :, 0] not all NaN;
       fea82_sha256 (f8_fea89.npz only): each side's value == sha256 of that sandbox's featws/mini/data/dlw_fea82.npz.
  2. Every OTHER meta_json field equal (canonical JSON); every data array of dlw_fea82 / f8_fea89 / dlw_targets, state_H_kc / state_H_fc
     (every array), target_combo/A.json (raw file bytes) and every non-beta key of target_live_PARITY/A.json (canonical JSON) bitwise equal,
     no exception — except ONE closed target_live entry (lead ruling w1): `written_utc`, the file's wall-clock write time, which two
     sandboxes necessarily differ on. It is accepted only if each side's value is a well-formed UTC timestamp (YYYY-MM-DDTHH:MM:SS[.f]Z) that
     falls inside THAT sandbox's run window [mtime(<sandbox>/offline.sb) floored, mtime(<sandbox>.combo.log) ceiled] (the profile is written
     just before combo_stage starts, the log just after it exits — nc_v2_nonbeta_gate.run()). History: the unrevised gate code (4f8529505)
     already excluded written_utc while its docstring said "every key except beta_overlay" (declaration ≠ implementation); the docstring
     was corrected with this revision.
  3. No downstream consumer reads mini-cache channel 0: an AST census (test_m3_v2_ret5.py T1 rule: a 3-element subscript whose last element
     is the constant 0) over the code the v2 sandbox actually executed (wide_shadow/shadow_loop_v3.py + wide_shadow/fea171/*.py) finds only
     whitelisted sites (T1's WHITELIST / WHITELIST_PREFIX, imported from test_m3_v2_ret5.py by sha). Regex hits (`[..., 0]`, "ret5",
     ch.index) are LISTED (report only). The verdict states that this item is proven INDIRECTLY by item 2 (arrays bitwise equal while v2's
     ch0 is all NaN — a reader of ch0 would have changed an array), the census being the listing.
  4. Two verdict lines, both into the receipt: NC_V2_NONBETA_GATE FAIL_LITERAL|PASS_LITERAL (the unrevised criterion) and
     NC_V2_NONBETA_GATE_REV1 PASS|FAIL.
usage: ~/wide_shadow/venv/bin/python nc_v2_nonbeta_gate_rev1.py <base tree> <v2 tree> <gate run dir> <out json>
"""
import ast, calendar, glob, hashlib, importlib.util, json, math, os, re, sys, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
WRITTEN_UTC = "w1"                          # lead ruling 2026-09-25 ~05:15Z: written_utc = a separate closed target_live exclusion, with checks
FIELDS = {"dlw_fea82.npz": {"self_sha256", "cache_sha256"}, "f8_fea89.npz": {"self_sha256", "cache_sha256", "fea82_sha256"}}
DEVFILE = {"dlw_fea82.npz": "fea171/dlw_features.py", "f8_fea89.npz": "fea171/f8_higher_order_features.py"}
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
canon = lambda v: json.dumps(v, sort_keys=True, allow_nan=True)


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


G = load(os.path.join(HERE, "nc_v2_nonbeta_gate.py"), "gate3p")          # arr_eq / selftest_arr_eq / _flat — the committed comparator


def census(root):
    hits = []
    files = [os.path.join(root, "shadow_loop_v3.py")] + sorted(glob.glob(os.path.join(root, "fea171", "*.py")))
    for p in files:
        rel = os.path.relpath(p, root); src = open(p).read(); lines = src.splitlines()
        for n in ast.walk(ast.parse(src)):
            if isinstance(n, ast.Subscript) and isinstance(n.slice, ast.Tuple) and len(n.slice.elts) == 3 \
                    and isinstance(n.slice.elts[-1], ast.Constant) and n.slice.elts[-1].value == 0:
                hits.append((rel, lines[n.lineno - 1].strip(), n.lineno))
    rx = re.compile(r"\[\s*\.\.\.\s*,\s*0\s*\]|[\"']ret5[\"']|ch\.index|CH\.index")
    regex = [(os.path.relpath(p, root), i + 1, l.strip()[:160]) for p in files for i, l in enumerate(open(p).read().splitlines()) if rx.search(l)]
    return hits, regex, [os.path.relpath(p, root) for p in files]


def main():
    base, v2, gdir, outp = [os.path.abspath(a) for a in sys.argv[1:5]]
    T = os.path.join(HERE, "test_m3_v2_ret5.py"); TM = load(T, "t1wl")
    rec = {"device": "nc_v2_nonbeta_gate_rev1.py", "self_sha256": sha(os.path.abspath(__file__)), "comparator_device_sha256": sha(os.path.join(HERE, "nc_v2_nonbeta_gate.py")),
           "whitelist_source": {"path": T, "sha256": sha(T)}, "gate_run_dir": gdir, "written_utc_ruling": WRITTEN_UTC, "anchors": {}}
    if WRITTEN_UTC not in ("w1", "w2"): sys.exit("written_utc ruling not set — refused")
    if not G.selftest_arr_eq(): sys.exit("comparator self-test failed — refused")
    anchors = sorted({int(os.path.basename(p).split("_")[0]) for p in glob.glob(f"{gdir}/17*_base")})
    lit_all, rev_all = True, True
    for A in anchors:
        sB, sV = f"{gdir}/{A}_base", f"{gdir}/{A}_v2"; r = {"fail": []}; F = r["fail"]
        # ---- literal (unrevised) reading, recomputed with the committed comparator ----
        lit = True
        for t in ("kc", "fc"):
            ok = G.npz_eq(f"{sB}/wide_shadow/fea171/state_H_{t}_{A}.npz", f"{sV}/wide_shadow/fea171/state_H_{t}_{A}.npz")
            r[f"state_H_{t}"] = ok[0]
            if ok[0] is not True: lit = False; F.append(f"state_H_{t}: {ok[1]}")
        for f in ("dlw_fea82.npz", "f8_fea89.npz", "dlw_targets.npz"):
            pb, pv = f"{sB}/featws/mini/data/{f}", f"{sV}/featws/mini/data/{f}"
            Zb, Zv = np.load(pb, allow_pickle=True), np.load(pv, allow_pickle=True)
            if sorted(Zb.files) != sorted(Zv.files): lit = False; F.append(f"{f}: keys differ"); continue
            arr_bad = [k for k in Zb.files if k != "meta_json" and not G.arr_eq(Zb[k], Zv[k])[0]]
            meta_same = G.arr_eq(Zb["meta_json"], Zv["meta_json"])[0] if "meta_json" in Zb.files else True
            if arr_bad or not meta_same: lit = False
            if arr_bad: F.append(f"{f}: data arrays differ {arr_bad}")
            fd = []
            if not meta_same:
                fb, fv = G._flat(json.loads(str(Zb["meta_json"]))), G._flat(json.loads(str(Zv["meta_json"])))
                fd = [k for k in sorted(set(fb) | set(fv)) if canon(fb.get(k)) != canon(fv.get(k))]
                names = {k.lstrip("/") for k in fd}
                outside = sorted(names - FIELDS.get(f, set()))
                if outside or any("/" in k.lstrip("/") or "[" in k for k in fd): F.append(f"{f}: meta_json fields outside the closed list {outside or fd}")
                # mapping of each allowed difference to its v2 change
                for k in sorted(names & FIELDS.get(f, set())):
                    vb, vv = fb.get("/" + k), fv.get("/" + k)
                    if k == "self_sha256":
                        ok = (vb == sha(f"{base}/{DEVFILE[f]}") == sha(f"{sB}/wide_shadow/{DEVFILE[f]}") and vv == sha(f"{v2}/{DEVFILE[f]}") == sha(f"{sV}/wide_shadow/{DEVFILE[f]}"))
                    elif k == "cache_sha256":
                        cb, cv = f"{sB}/featws/mini/cache.npz", f"{sV}/featws/mini/cache.npz"
                        Cb, Cv = np.load(cb, allow_pickle=True), np.load(cv, allow_pickle=True)
                        same_rest = (sorted(Cb.files) == sorted(Cv.files) and all(G.arr_eq(Cb[x], Cv[x])[0] for x in ("ts", "symbols", "ch", "ret_f32"))
                                     and G.arr_eq(np.ascontiguousarray(Cb["data"][:, :, 1:]), np.ascontiguousarray(Cv["data"][:, :, 1:]))[0])
                        ch0v, ch0b = Cv["data"][:, :, 0], Cb["data"][:, :, 0]
                        ok = (vb == sha(cb) and vv == sha(cv) and same_rest and bool(np.isnan(ch0v).all()) and not bool(np.isnan(ch0b).all()))
                        r[f"{f}.cache_map"] = {"sha_base_ok": vb == sha(cb), "sha_v2_ok": vv == sha(cv), "other_channels_and_arrays_bitwise": same_rest,
                                               "v2_ch0_all_nan": bool(np.isnan(ch0v).all()), "base_ch0_all_nan": bool(np.isnan(ch0b).all())}
                    elif k == "fea82_sha256":
                        ok = (vb == sha(f"{sB}/featws/mini/data/dlw_fea82.npz") and vv == sha(f"{sV}/featws/mini/data/dlw_fea82.npz"))
                    else:
                        ok = False
                    r[f"{f}.{k}_maps_to_v2_change"] = bool(ok)
                    if not ok: F.append(f"{f}: {k} does not map to its v2 change")
            r[f"{f}.meta_fields_differing"] = fd
        tb, tv = f"{sB}/wide_shadow/state/target_combo/{A}.json", f"{sV}/wide_shadow/state/target_combo/{A}.json"
        r["target_combo_bytes_equal"] = open(tb, "rb").read() == open(tv, "rb").read()
        if not r["target_combo_bytes_equal"]: lit = False; F.append("target_combo bytes differ")
        jb = json.load(open(f"{sB}/wide_shadow/state/target_live_PARITY/{A}.json")); jv = json.load(open(f"{sV}/wide_shadow/state/target_live_PARITY/{A}.json"))
        dk = [k for k in sorted(set(jb) | set(jv)) if k != "beta_overlay" and canon(jb.get(k)) != canon(jv.get(k))]
        r["target_live_nonbeta_keys_differing"] = dk
        allowed_tl = {"written_utc"} if WRITTEN_UTC == "w1" else set()
        if set(dk) - {"written_utc"}: lit = False                               # the unrevised device already excluded written_utc (4f8529505)
        if set(dk) - allowed_tl: F.append(f"target_live non-beta keys differ {sorted(set(dk) - allowed_tl)}")
        if WRITTEN_UTC == "w1" and "written_utc" in dk:
            wl = {}
            for tag, sb, j in (("base", sB, jb), ("v2", sV, jv)):
                x = j.get("written_utc"); lo = math.floor(os.stat(f"{sb}/offline.sb").st_mtime); hi = math.ceil(os.stat(f"{sb}.combo.log").st_mtime)
                wf = isinstance(x, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z", x) is not None
                t = calendar.timegm(time.strptime(x[:19], "%Y-%m-%dT%H:%M:%S")) if wf else None
                wl[tag] = {"value": x, "well_formed": wf, "run_window_utc": [time.strftime("%FT%TZ", time.gmtime(lo)), time.strftime("%FT%TZ", time.gmtime(hi))],
                           "inside": bool(wf and lo <= t <= hi)}
                if not (wf and lo <= t <= hi): F.append(f"written_utc ({tag}) not well-formed or outside its sandbox run window")
            r["written_utc"] = wl
        r["literal_pass"] = lit; r["rev1_pass"] = not F
        lit_all &= lit; rev_all &= not F
        rec["anchors"][str(A)] = r
        print(f"anchor {A}: literal {'PASS' if lit else 'FAIL'} | rev1 {'PASS' if not F else 'FAIL'} {F}", flush=True)
    # ---- item 3: ch0 census over the code the v2 sandbox executed ----
    root = f"{gdir}/{anchors[0]}_v2/wide_shadow"
    hits, regex, files = census(root)
    bad = [h for h in hits if (h[0], h[1]) not in TM.WHITELIST and not any(h[0] == f and h[1].startswith(p) for f, p in TM.WHITELIST_PREFIX)]
    rec["item3_ch0_census"] = {"code_root": root, "n_files": len(files), "hits": hits, "non_whitelisted": bad, "regex_listing_report_only": regex,
                               "note": "item 3 is proven INDIRECTLY by item 2 (all data arrays bitwise equal while v2's mini-cache ch0 is all NaN); the census is the listing"}
    if bad: rev_all = False
    print(f"item3 ch0 census over {len(files)} executed files: {len(hits)} channel-0 subscripts, non-whitelisted {len(bad)} {bad}; regex listing {len(regex)} (report only)", flush=True)
    rec["VERDICT_LITERAL"] = "PASS_LITERAL" if (lit_all and anchors) else "FAIL_LITERAL"
    rec["VERDICT_REV1"] = "PASS" if (rev_all and anchors) else "FAIL"
    json.dump(rec, open(outp, "w"), indent=1, default=str)
    print(f"NC_V2_NONBETA_GATE {rec['VERDICT_LITERAL']} anchors={len(anchors)} (unrevised criterion; meta_json provenance fields differ by construction)", flush=True)
    print(f"NC_V2_NONBETA_GATE_REV1 {rec['VERDICT_REV1']} anchors={len(anchors)} written_utc_ruling={WRITTEN_UTC} out_sha256={sha(outp)}", flush=True)
    return 0 if rec["VERDICT_REV1"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
