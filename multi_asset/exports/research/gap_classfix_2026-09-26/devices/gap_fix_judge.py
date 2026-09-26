#!/usr/bin/env python3
"""Judge the gap-class-fix replay arms against the FROZEN criteria (ACCEPTANCE_gap_classfix_2026-09-26.md §2, commit 11bc3b4be).
Reads sandboxes <root>/<code>_<arm>/<A>/ written by gap_fix_replay.sh; writes nothing but --out.
usage: gap_fix_judge.py <replay root> --out RECEIPT.json"""
import argparse, hashlib, json, os, re, sys, time
import numpy as np

H4 = 14400
GAP_A = 1790409600
BASE_AS = (1790380800, 1790395200, 1790409600)
WS_PROD = os.path.expanduser("~/wide_shadow")


def sb(root, code, arm, A): return f"{root}/{code}_{arm}/{A}"


def rd(p):
    with open(p, "rb") as f: return f.read()


def run(root, code, arm, A):
    d = sb(root, code, arm, A); w = f"{d}/wide_shadow"
    o = {"sandbox": d, "exists": os.path.isdir(d)}
    if not o["exists"]: return o
    o["code"] = rd(f"{d}/CODE").decode().strip() if os.path.exists(f"{d}/CODE") else None
    o["hook"] = rd(f"{d}/HOOK").decode().strip()[:400] if os.path.exists(f"{d}/HOOK") else None
    o["rc"] = int(rd(f"{d}/RC").decode().strip()) if os.path.exists(f"{d}/RC") else None
    tp = f"{w}/state/target_live_PARITY/{A}.json"
    o["target"] = json.loads(rd(tp)) if os.path.exists(tp) else None
    cp = f"{w}/state/target_combo/{A}.json"
    o["combo_bytes"] = rd(cp) if os.path.exists(cp) else None
    o["combo"] = json.loads(o["combo_bytes"]) if o["combo_bytes"] else {}
    bp = f"{w}/state/target_blend/{A}.json"
    o["blend_bytes"] = rd(bp) if os.path.exists(bp) else None
    o["blend"] = json.loads(o["blend_bytes"]) if o["blend_bytes"] else {}
    o["states"] = {}
    for leg in ("kc", "fc", "f10"):
        p = f"{w}/fea171/state_H_{leg}_{A}.npz"
        if os.path.exists(p):
            z = np.load(p); o["states"][leg] = {k: z[k] for k in z.files}
    wp = f"{w}/state/weights_combo/{A}.npz"
    o["wcombo"] = ({k: np.load(wp)[k] for k in np.load(wp).files} if os.path.exists(wp) else None)
    log = rd(f"{d}/run.log").decode(errors="replace") if os.path.exists(f"{d}/run.log") else ""
    o["gap_page_lines"] = [ln for ln in log.splitlines() if "GAP_PAGE" in ln]
    m = re.search(r"\[\s*([\d.]+)s\] ⑤ COMBO_LIVE", log)
    o["elapsed_s"] = float(m.group(1)) if m else None
    o["abort"] = [ln for ln in log.splitlines() if "COMBO_LIVE ABORT" in ln or "Traceback" in ln][:3]
    return o


def weights_equal(a, b):
    if a is None or b is None: return False, "missing target"
    wa, wb = a["weights"], b["weights"]
    if set(wa) != set(wb): return False, f"key sets differ ({len(set(wa) ^ set(wb))})"
    nd = [k for k in wa if not (wa[k] == wb[k])]
    if nd: return False, f"{len(nd)} weights differ, max |dw| {max(abs(wa[k] - wb[k]) for k in nd):.3e}"
    ka = {k: v for k, v in a.items() if k not in ("written_utc", "weights_sha", "weights")}
    kb = {k: v for k, v in b.items() if k not in ("written_utc", "weights_sha", "weights")}
    if ka != kb: return False, f"other keys differ: {sorted(k for k in set(ka) | set(kb) if ka.get(k) != kb.get(k))}"
    return True, f"{len(wa)} weights bit-equal"


def arrays_equal(x, y):
    if x is None or y is None: return x is y
    return set(x) == set(y) and all(np.array_equal(x[k], y[k]) and x[k].dtype == y[k].dtype for k in x)


def src(o):
    return o["combo"].get("kc_state_source"), o["combo"].get("fc_state_source"), o["blend"].get("h_source")


def red_current(o):
    kc, fc, _ = src(o)
    return (o.get("rc") != 0 or o.get("target") is None or not str(kc).startswith("own") or not str(fc).startswith("own")), \
        f"rc={o.get('rc')} target={'yes' if o.get('target') else 'no'} kc={kc} fc={fc} abort={o.get('abort')}"


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("root"); ap.add_argument("--out", required=True); a = ap.parse_args()
    R, verdicts = {}, {}
    # C0 ×3
    for A in BASE_AS:
        cur, pat = run(a.root, "current", "base", A), run(a.root, "patched", "base", A)
        prod = json.loads(rd(f"{WS_PROD}/state/target_live/{A}.json"))
        sanity, sanity_why = weights_equal({**prod, "written_utc": None}, {**(cur["target"] or {}), "written_utc": None}) if cur.get("target") else (False, "no current target")
        # the archived file differs from a replay in written_utc / weights_sha only; compare weights + stable keys
        eqw, why = weights_equal(cur.get("target"), pat.get("target"))
        st_eq = {leg: arrays_equal(cur["states"].get(leg), pat["states"].get(leg)) for leg in ("kc", "fc", "f10")}
        combo_b = cur.get("combo_bytes") is not None and cur.get("combo_bytes") == pat.get("combo_bytes")
        blend_b = cur.get("blend_bytes") is not None and cur.get("blend_bytes") == pat.get("blend_bytes")
        wc = arrays_equal(cur.get("wcombo"), pat.get("wcombo")) and cur.get("wcombo") is not None
        t_ok = cur.get("elapsed_s") is not None and pat.get("elapsed_s") is not None and pat["elapsed_s"] <= cur["elapsed_s"] + 2.0
        ok = sanity and eqw and all(st_eq.values()) and combo_b and blend_b and wc and cur.get("rc") == 0 and pat.get("rc") == 0
        verdicts[f"C0_{A}"] = ok; verdicts[f"T_{A}"] = t_ok
        R[f"C0_{A}"] = {"PASS": ok, "current_vs_archived": sanity_why, "weights": why, "states_bitwise": st_eq, "target_combo_bytes_equal": combo_b,
                        "target_blend_bytes_equal": blend_b, "weights_combo_arrays_equal": wc, "rc": [cur.get("rc"), pat.get("rc")],
                        "code": [cur.get("code"), pat.get("code")],
                        "T": {"PASS": t_ok, "elapsed_current_s": cur.get("elapsed_s"), "elapsed_patched_s": pat.get("elapsed_s")}}
    A = GAP_A
    P = A - H4
    def patched_arm(arm, ref_arm, want_kc, want_fc, want_f10, want_page_names):
        cur, pat, ref = run(a.root, "current", arm, A), run(a.root, "patched", arm, A), run(a.root, "current", ref_arm, A)
        red, red_why = red_current(cur)
        eqw, why = weights_equal(ref.get("target"), pat.get("target"))
        kc, fc, f10 = src(pat)
        srcs_ok = (kc, fc, f10) == (want_kc, want_fc, want_f10)
        page_ok = (not want_page_names) or (len(pat["gap_page_lines"]) >= 1 and all(n in pat["gap_page_lines"][0] for n in want_page_names))
        no_page_ok = bool(want_page_names) or not pat["gap_page_lines"]
        ref_ok = ref.get("rc") == 0 and ref.get("target") is not None
        ok = pat.get("rc") == 0 and pat.get("target") is not None and srcs_ok and eqw and page_ok and no_page_ok and ref_ok
        verdicts[f"{arm}_current_RED"] = red; verdicts[f"{arm}_patched"] = ok
        R[arm] = {"current_RED": red, "current": red_why, "patched_PASS": ok, "patched_rc": pat.get("rc"),
                  "patched_sources(kc,fc,f10)": [kc, fc, f10], "want": [want_kc, want_fc, want_f10],
                  "vs_reference": f"{ref_arm}: rc={ref.get('rc')} {why}", "gap_page_lines": [ln[:600] for ln in pat["gap_page_lines"]],
                  "page_names_required": want_page_names, "state_lookup": pat["combo"].get("state_lookup"), "hooks": [cur.get("hook"), pat.get("hook"), ref.get("hook")]}
    for k in (1, 2, 6):
        patched_arm(f"gap{k}", f"bridge{k}", f"own_gap{k}", f"own_gap{k}", f"own_gap{k}", [])
    patched_arm("gap7", "bridge7", "own_gap7_beyond_bound", "own_gap7_beyond_bound", "own_gap7_beyond_bound", ["beyond_bound"])
    for x in ("x1", "x2", "x3"):
        patched_arm(x, "xref", "own_gap1_rejected1", "own", "own", [f"state_H_kc_{P}.npz", "rejected"])
    # AMENDMENT 3 arms cold / poison (only judged when their sandboxes exist)
    if os.path.isdir(sb(a.root, "patched", "cold", A)):
        cur, pat = run(a.root, "current", "cold", A), run(a.root, "patched", "cold", A)
        def st_written(code):
            w = f"{sb(a.root, code, 'cold', A)}/wide_shadow/fea171"
            return {leg: os.path.exists(f"{w}/state_H_{leg}_{A}.npz") for leg in ("kc", "fc", "f10")}
        cw, pw = st_written("current"), st_written("patched")
        red = cw["kc"] or cw["fc"] or cur.get("target") is not None
        plog = open(f"{sb(a.root, 'patched', 'cold', A)}/run.log").read() if os.path.exists(f"{sb(a.root, 'patched', 'cold', A)}/run.log") else ""
        abort_ok = any("COMBO_LIVE ABORT" in ln and "冷启动拒绝发布" in ln for ln in plog.splitlines())
        ok = pat.get("rc") not in (0, None) and pat.get("target") is None and not any(pw.values()) and abort_ok
        verdicts["cold_current_RED"] = red; verdicts["cold_patched"] = ok
        R["cold"] = {"current_RED": red, "current": {"rc": cur.get("rc"), "target": cur.get("target") is not None, "state_written": cw},
                     "patched_PASS": ok, "patched": {"rc": pat.get("rc"), "target": pat.get("target") is not None, "state_written": pw, "abort_line_names_cold_start": abort_ok},
                     "abort_lines": [ln[:400] for ln in plog.splitlines() if "COMBO_LIVE ABORT" in ln]}
    if os.path.isdir(sb(a.root, "patched", "poison", A)):
        patched_arm("poison", "bridge1", "own_gap1_rejected1", "own_gap1_rejected1", "own_gap1_rejected1", ["degenerate"])
        o = run(a.root, "current", "poison", A); kc, fc, _ = src(o)
        verdicts["poison_current_RED"] = (kc == "own" or fc == "own" or o.get("target") is None)
        R["poison"]["current_RED"] = verdicts["poison_current_RED"]
    # AMENDMENT 2 arm M (members history): descriptive readouts + one gate conditional on V2
    v2p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "receipts", "MEMBERS_V1V2.json")
    v2 = json.load(open(v2p)); row6 = [r for r in v2["V2"]["rows"] if r["S"] == A and r["lag"] == 6]
    gate_applies = bool(row6) and row6[0]["recompute_equal"]
    M = {"V2_row_S=A_lag6": row6[0] if row6 else None, "gate_applies": gate_applies}
    def mdump(code, arm):
        o = run(a.root, code, arm, A); p = f"{sb(a.root, code, arm, A)}/M_DUMP.npz"
        z = dict(np.load(p)) if os.path.exists(p) else None
        return o, z
    def spear(x, y):
        from scipy.stats import spearmanr
        return float(spearmanr(x, y).correlation)
    for code in ("current", "patched"):
        ob, zb = mdump(code, "mhbase"); od, zd = mdump(code, "mhdrop"); base = run(a.root, code, "base", A)
        r = {"rc": [ob.get("rc"), od.get("rc")], "dump": [zb is not None, zd is not None]}
        if zb is not None and zd is not None:
            assert np.array_equal(zb["scol"], zd["scol"])
            r["drank_row_A_zero_share"] = {"mhbase": float((zb["drank"] == 0).mean()), "mhdrop": float((zd["drank"] == 0).mean())}
            r["mh_missing"] = [int(zb["mh_missing"]), int(zd["mh_missing"])]
            fb, fd = zb["f10"].astype(float), zd["f10"].astype(float); ok_ = np.isfinite(fb) & np.isfinite(fd)
            r["f10_spearman_drop_vs_base"] = spear(fb[ok_], fd[ok_]); r["f10_max_abs_diff"] = float(np.max(np.abs(fb[ok_] - fd[ok_])))
        wb, wd = (ob.get("target") or {}).get("weights"), (od.get("target") or {}).get("weights")
        if wb and wd:
            ks = set(wb) | set(wd); dif = [abs(wb.get(k, 0.0) - wd.get(k, 0.0)) for k in ks]
            r["weights_L1_diff"] = float(sum(dif)); r["weights_max_abs_dw"] = float(max(dif)); r["weights_bit_equal"] = wb == wd
        r["dump_does_not_touch_output (mhbase == base weights)"] = weights_equal(base.get("target"), ob.get("target"))[0]
        r["recompute_log"] = [ln[:300] for ln in (open(f"{sb(a.root, code, 'mhdrop', A)}/run.log").read().splitlines() if os.path.exists(f"{sb(a.root, code, 'mhdrop', A)}/run.log") else []) if "MH_RECOMPUTED" in ln or "member history" in ln]
        M[code] = r
    m_ok = (M["patched"].get("dump_does_not_touch_output (mhbase == base weights)") is True
            and M["current"].get("dump_does_not_touch_output (mhbase == base weights)") is True
            and ((not gate_applies) or M["patched"].get("weights_bit_equal") is True))
    verdicts["M_patched_mhdrop_bitwise_to_base (gate iff V2 lag-6 exact)"] = m_ok
    R["M"] = M
    ok = all(verdicts.values())
    rec = {"device": "gap_fix_judge.py", "self_sha256": hashlib.sha256(rd(os.path.abspath(__file__))).hexdigest(),
           "criteria": "ACCEPTANCE_gap_classfix_2026-09-26.md (frozen 11bc3b4be)", "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "root": a.root, "verdicts": verdicts, "arms": R, "VERDICT": "PASS" if ok else "FAIL"}
    with open(a.out, "w") as f:
        json.dump(rec, f, indent=1, default=str)
    for k, v in verdicts.items(): print(f"  {'OK ' if v else 'BAD'} {k}")
    print(f"GAP_FIX_JUDGE {'PASS' if ok else 'FAIL'} n_bad={sum(1 for v in verdicts.values() if not v)}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
