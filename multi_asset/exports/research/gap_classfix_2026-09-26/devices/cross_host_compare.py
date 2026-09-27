"""cross_host_compare.py (integ 2026-09-27, arm64 migration): the SAME replay arms run on the old Intel host (run 3; its current arms are run-1/run-2
outputs by symlink) and on the new arm64 host (run 4, all fresh) — compare every output the judge reads, per arm and anchor, and say for each whether
it is bitwise-identical or, if not, how far apart (max |diff| over numbers). Descriptive only; the judge verdicts are gap_fix_judge.py's.
usage: ~/wide_shadow/venv/bin/python cross_host_compare.py <x86 root> <arm64 root> --out <json>"""
import glob, hashlib, json, os, sys
import numpy as np
SKIP_KEYS = {"utc", "written_utc", "t_utc", "elapsed_s", "ts", "time", "written_at", "built_utc", "wall_s", "age_s"}


def num_diff(a, b, path=""):
    """(structurally_equal, max_abs_numeric_diff, first_non_numeric_difference) over two parsed JSON values; SKIP_KEYS named, not compared."""
    if isinstance(a, dict) and isinstance(b, dict):
        if set(a) != set(b): return False, None, f"{path}: keys {sorted(set(a) ^ set(b))[:5]}"
        m, bad = 0.0, None
        for k in a:
            if k in SKIP_KEYS: continue
            eq, d, why = num_diff(a[k], b[k], f"{path}.{k}")
            if not eq: return False, None, why
            m = max(m, d or 0.0)
        return True, m, None
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b): return False, None, f"{path}: len {len(a)} != {len(b)}"
        m = 0.0
        for i, (x, y) in enumerate(zip(a, b)):
            eq, d, why = num_diff(x, y, f"{path}[{i}]")
            if not eq: return False, None, why
            m = max(m, d or 0.0)
        return True, m, None
    if isinstance(a, bool) or isinstance(b, bool) or a is None or b is None or isinstance(a, str) or isinstance(b, str):
        return (a == b), 0.0, (None if a == b else f"{path}: {str(a)[:60]!r} != {str(b)[:60]!r}")
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if a == b or (a != a and b != b): return True, 0.0, None
        return True, abs(float(a) - float(b)), None
    return a == b, 0.0, None


def npz_cmp(p, q):
    A, B = np.load(p, allow_pickle=False), np.load(q, allow_pickle=False)
    if set(A.files) != set(B.files): return {"bitwise": False, "why": f"keys {sorted(set(A.files) ^ set(B.files))}"}
    bit, m = True, 0.0
    for k in A.files:
        x, y = A[k], B[k]
        if x.shape != y.shape or x.dtype != y.dtype: return {"bitwise": False, "why": f"{k} shape/dtype {x.shape}{x.dtype} vs {y.shape}{y.dtype}"}
        if x.tobytes() != y.tobytes():
            bit = False
            if np.issubdtype(x.dtype, np.number): m = max(m, float(np.nanmax(np.abs(x.astype(np.float64) - y.astype(np.float64)))) if x.size else 0.0)
            else: return {"bitwise": False, "why": f"{k} non-numeric differs"}
    return {"bitwise": bit, "max_abs": m}


def outputs(sb):
    w = f"{sb}/wide_shadow"; A = os.path.basename(sb); o = {}
    for rel in (f"state/target_live_PARITY/{A}.json", f"state/target_combo/{A}.json", f"state/target_blend/{A}.json", f"state/weights_combo/{A}.npz",
                f"fea171/state_H_kc_{A}.npz", f"fea171/state_H_fc_{A}.npz", f"fea171/state_H_f10_{A}.npz"):
        o[rel] = f"{w}/{rel}" if os.path.exists(f"{w}/{rel}") else None
    o["RC"] = open(f"{sb}/RC").read().strip() if os.path.exists(f"{sb}/RC") else None
    return o


def main():
    x86, arm, out = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2]), sys.argv[sys.argv.index("--out") + 1]
    rows, n_files, n_bit = [], 0, 0
    for d in sorted(glob.glob(f"{arm}/*_*/*")):
        arm_name, A = d.split("/")[-2], d.split("/")[-1]
        xd = os.path.realpath(f"{x86}/{arm_name}") + f"/{A}"
        if not os.path.isdir(xd): rows.append({"arm": arm_name, "A": A, "x86": "ABSENT"}); continue
        ox, oa = outputs(xd), outputs(d); r = {"arm": arm_name, "A": A, "rc": [ox["RC"], oa["RC"]], "files": {}}
        for rel in ox:
            if rel == "RC": continue
            p, q = ox[rel], oa[rel]
            if p is None or q is None:
                r["files"][rel] = {"present": [p is not None, q is not None], "agree": (p is None) == (q is None)}; continue
            n_files += 1
            if open(p, "rb").read() == open(q, "rb").read():
                r["files"][rel] = {"bitwise": True}; n_bit += 1; continue
            if rel.endswith(".npz"): c = npz_cmp(p, q)
            else:
                # the replay roots differ by name (…/replay3 vs …/replay4_arm64) and target_combo's state_lookup.rejected[].path embeds the sandbox
                # path: compare with each root replaced by the same token, so only a real difference remains
                jp = json.loads(open(p).read().replace(os.path.realpath(xd), "<SB>").replace(xd, "<SB>"))
                jq = json.loads(open(q).read().replace(d, "<SB>"))
                eq, m, why = num_diff(jp, jq)
                top = sorted(k for k in set(jp) | set(jq) if jp.get(k) != jq.get(k)) if isinstance(jp, dict) and isinstance(jq, dict) else None
                c = {"bitwise": False, "structurally_equal_excluding_time_keys": eq, "max_abs": m, "why": why, "top_keys_differing": top}
                if isinstance(jp, dict) and isinstance(jp.get("weights"), dict) and isinstance(jq.get("weights"), dict):
                    c["weights_bitwise"] = jp["weights"] == jq["weights"]
                if eq and m == 0.0: c["equal_except_time_keys"] = True
            n_bit += bool(c.get("bitwise")); r["files"][rel] = c
        rows.append(r)
    worst = max([f.get("max_abs") or 0.0 for r in rows for f in r.get("files", {}).values()] or [0.0])
    rc_agree = all(r.get("rc", [0, 0])[0] == r.get("rc", [0, 0])[1] for r in rows if "rc" in r)
    summary = {"device": "cross_host_compare.py", "self_sha256": hashlib.sha256(open(__file__, "rb").read()).hexdigest(), "x86_root": x86, "arm64_root": arm,
               "n_arm_anchor": len(rows), "n_files_compared": n_files, "n_bitwise": n_bit, "worst_max_abs": worst, "rc_all_agree": rc_agree,
               "presence_all_agree": all(f.get("agree", True) for r in rows for f in r.get("files", {}).values()), "rows": rows}
    json.dump(summary, open(out, "w"), indent=1)
    for r in rows:
        nb = [k.split("/")[-1] for k, f in r.get("files", {}).items() if "bitwise" in f and not f["bitwise"]]
        print(f"{r['arm']:18s} {r['A']} rc={r.get('rc')} non_bitwise={nb}")
    print(f"CROSS_HOST n_arm_anchor={len(rows)} files={n_files} bitwise={n_bit} worst_max_abs={worst:.3g} rc_all_agree={rc_agree} presence_all_agree={summary['presence_all_agree']}")


if __name__ == "__main__":
    main()
