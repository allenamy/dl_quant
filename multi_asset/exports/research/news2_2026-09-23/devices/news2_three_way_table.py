"""Researcher NEW vs NEW_S vs NC in ONE table: per-segment return, Sharpe, drawdown.

lead 2026-09-24, for the user: put the three versions side by side and state, per arm, whether the
DEVICE and the CALIBRE are the same. Facts only; this device draws no conclusion and contains no
comparison verdict.

Why a table like this can mislead if the provenance is not attached: three columns of numbers invite a
ranking, and a ranking is only meaningful if the columns were produced the same way. So every arm carries
three provenance facts, measured rather than asserted:

  runs_root         which engine output directory the numbers were read from
  cell              which cost/publication cell (all arms use the SAME cell name here)
  config_vs_OLD     the leaf-level diff of that arm's run config against the Stage-1 OLD config; if the
                    only differing leaves are labels/targets/output-root, the settings are identical and
                    the arms are comparable. The differing leaves are LISTED, not summarised.

Every statistic comes from the pinned news_stats.py by import (same module the verdict used), so the
table and the verdict cannot disagree about what "2024 Sharpe" means.

usage: python news2_three_way_table.py <out.json> <out.md>
"""
import hashlib, json, os, re, sys, time

import numpy as np

W = "/dev/shm/news2_2026-09-23"
S1 = "/dev/shm/ovn_2026-09-23"
NS_ROOT = "/dev/shm/news_2026-09-23"
E = f"{W}/engine"
NEWS_STATS_SHA = "7141ba42ab227b9f35b48acce62d5e2a2494f364fdf6a83189974cb2af67e03c"

# arm -> (runs root, run-prefix, run config path or None, what it is)
ARMS = [
    # the OLD arm prefix is OBJB_A0, not OVN_OLD: news2_stats.py L41 PREFIX["OLD"]="OBJB_A0" (the certified
    # A0 baseline runs). Taken from the verdict device rather than guessed from the directory listing.
    ("OLD",        S1,      "OBJB_A0",     f"/workspace/old_vs_new_2026-09-23/RUN_CONFIG_OVN_OLD_2026-09-23.json",
     "Stage-1 OLD: the live book logic (certified A0 runs)"),
    ("NEW_s42",    S1,      "OVN_NEW_s42", f"/workspace/old_vs_new_2026-09-23/RUN_CONFIG_OVN_NEW_s42_2026-09-23.json",
     "the RESEARCHER's NEW models, seed 42"),
    ("NEW_s2027",  S1,      "OVN_NEW_s2027", f"/workspace/old_vs_new_2026-09-23/RUN_CONFIG_OVN_NEW_s2027_2026-09-23.json",
     "the RESEARCHER's NEW models, seed 2027"),
    ("NEW_S_s42",  NS_ROOT, "NEWS_s42",    f"{NS_ROOT}/configs/RUN_CONFIG_NEWS_s42_2026-09-23.json",
     "NEW_S: producer-servable rebuild, seed 42"),
    ("NEW_S_s2027", NS_ROOT, "NEWS_s2027", f"{NS_ROOT}/configs/RUN_CONFIG_NEWS_s2027_2026-09-23.json",
     "NEW_S: producer-servable rebuild, seed 2027"),
    ("NC_s42",     W,       "NEWS2_s42",   f"{W}/configs/RUN_CONFIG_NEWS2_s42_2026-09-23.json",
     "NC (this release): full corrected producer contract, seed 42"),
    ("NC_s2027",   W,       "NEWS2_s2027", f"{W}/configs/RUN_CONFIG_NEWS2_s2027_2026-09-23.json",
     "NC (this release): full corrected producer contract, seed 2027"),
]
CELL = "scaled_rule_raw_UAFE"     # the main reading cell, identical for every arm
CERT_ROOT = "/workspace/baseline_tables_2026-09-19/runs"
METRICS = ("total_return", "sharpe", "maxdd_5m")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): h.update(b)
    return h.hexdigest()


def leaves(o, p=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from leaves(v, f"{p}.{k}" if p else str(k))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from leaves(v, f"{p}[{i}]")
    else:
        yield p, o


def config_diff(a_path, b_path):
    """Leaf-level diff, LISTED not counted: 'settings identical' has to be checkable by the reader."""
    # a missing config is a NAMED non-comparison, never a silent pass: NEW_S has no run config in this
    # tree, so its row must say so rather than look like "no differences found".
    if not a_path or not b_path or not os.path.exists(a_path) or not os.path.exists(b_path):
        return {"NOT_COMPARED": f"config not available for a leaf-level diff (a={a_path} b={b_path})"}
    A, B = dict(leaves(json.load(open(a_path)))), dict(leaves(json.load(open(b_path))))
    diff = [{"leaf": k, "OLD": A.get(k), "arm": B.get(k)}
            for k in sorted(set(A) | set(B)) if A.get(k) != B.get(k)]
    # Categorise: a leaf that names WHICH artefact or WHAT the arm is called is expected to differ; a leaf
    # that describes HOW the simulation runs is not, and its presence would make the arms incomparable.
    # Both lists are emitted, so "comparable" is a statement the reader can check rather than accept.
    setting = re.compile(r"(fee|slip|fill|gross|nav|leverage|seed|n_paths|npath|window|horizon|cost|"
                         r"publish|publication|rule|sim|engine|stop|derisk|cap|clip|anchor_offset)", re.I)
    ident = re.compile(r"(lineage|arm|role|tag|label|config|status|created_utc|object|pending|ovn|"
                       r"targets|pod_root|prereg|amendment|sha256|path|commit|data|axis|"
                       r"first_served|disclosure|B_CORE_start|notes)", re.I)
    names = [x["leaf"] for x in diff]
    setting_like = [n for n in names if setting.search(n) and not ident.search(n)]
    return {"n_differing_leaves": len(diff),
            "n_setting_like": len(setting_like), "setting_like_leaves": setting_like,
            "comparable_on_settings": len(setting_like) == 0,
            "differing_leaves": diff}


def main():
    out_json, out_md = sys.argv[1:3]
    assert sha(f"{E}/news_stats.py") == NEWS_STATS_SHA, "news_stats.py is not the pinned version"
    sys.path.insert(0, E)
    import news_stats as NS
    import bt_tables as _BT
    import bt_driver_lib as _DL
    NS.BT, NS.DL = _BT, _DL

    old_cfg = f"/workspace/old_vs_new_2026-09-23/RUN_CONFIG_OVN_OLD_2026-09-23.json"
    rows, prov, unavailable, loaded = {}, {}, [], {}
    for name, root, pre, cfg, what in ARMS:
        run_dir = os.path.join(root, "runs", f"{pre}_{CELL}")
        prov[name] = {"what": what, "runs_root": os.path.join(root, "runs"), "cell": CELL,
                      "run_dir": run_dir, "run_dir_exists": os.path.isdir(run_dir),
                      "config": cfg, "config_vs_OLD": config_diff(cfg, cfg) if cfg == old_cfg else config_diff(old_cfg, cfg)}
        if not os.path.isdir(run_dir):
            unavailable.append({"arm": name, "why": f"run dir absent: {run_dir}"})
            continue
        try:
            # load_cell(d, tag_dir, certified_dir=None) -- tag_dir names the PATH_<tag>_seed_NN stems.
            # OLD is additionally cross-checked against the certified runs, exactly as news2_stats.py L155.
            tag_dir = f"{pre}_{CELL}"
            cert = os.path.join(CERT_ROOT, tag_dir) if name == "OLD" else None
            loaded[name] = NS.load_cell(run_dir, tag_dir, cert)
        except Exception as e:
            unavailable.append({"arm": name, "why": f"{type(e).__name__}: {e}"})

    # ---- one common window axis for every arm, asserted rather than assumed (news2_stats.py L180-183).
    # Comparing segment numbers across arms that sit on different axes would be the "same label, different
    # population" error; this refuses instead.
    axis = None
    if "OLD" in loaded:
        axis = loaded["OLD"][0][0]["A"]
        for nm, (paths, _) in list(loaded.items()):
            if not np.array_equal(paths[0]["A"], axis):
                unavailable.append({"arm": nm, "why": "window axis differs from OLD; not comparable, dropped"})
                loaded.pop(nm)
    else:
        unavailable.append({"arm": "(axis)", "why": "OLD not loaded, so no common axis could be established"})
        loaded = {}

    for name, (paths, _facts) in loaded.items():
        rows[name] = {}
        for seg, (a, b) in NS.SEG.items():
            m = NS.seg_mask(axis, a, b)
            dd = NS.full_days(axis, m)
            per = [NS.path_metrics(pp, m, dd) for pp in paths]
            summ = NS.summarise(per)
            rows[name][seg] = {k: summ[k]["path_mean"] for k in METRICS if k in summ}
            rows[name][seg]["n_full_days"] = int(len(dd))

    rec = {"device": "news2_three_way_table.py", "self_sha256": sha(os.path.abspath(__file__)),
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "for": "lead 2026-09-24, relaying a user question. Facts only; no conclusion is drawn here.",
           "statistics_from": {"news_stats.py": NEWS_STATS_SHA, "how": "import, not copy"},
           "cell": CELL, "metrics": list(METRICS), "segments": NS.SEG,
           "arms": prov, "table": rows,
           "unavailable": unavailable,
           "reading_note": ("all arms are read from the same cell by the same module, so the column "
                            "definitions agree. Whether the arms are COMPARABLE depends on config_vs_OLD: "
                            "the differing leaves are listed per arm so the reader can judge rather than "
                            "take a summary.")}
    json.dump(rec, open(out_json, "w"), indent=1)

    L = [f"<!-- {rec['device']} sha {rec['self_sha256'][:16]}; statistics imported from news_stats.py "
         f"{NEWS_STATS_SHA[:16]}; cell {CELL} -->", "",
         "### 研究员 NEW / NEW_S / NC 同表(逐段收益、夏普、回撤)", "",
         "> 只列事实, 不下结论。三列并排会自然诱发排序, 而排序只有在三列**产生方式相同**时才有意义, "
         "所以每臂都带来源与口径, 且差异逐条列出而不是概括。", ""]
    for metric, label in (("total_return", "区间总收益"), ("sharpe", "夏普"), ("maxdd_5m", "最大回撤(5m)")):
        L += [f"**{label}**（`{metric}`,路径均值）", "",
              "| 臂 | " + " | ".join(NS.SEG) + " |", "|---|" + "---|" * len(NS.SEG)]
        for name, *_ in [(a[0],) for a in ARMS]:
            if name not in rows:
                L.append(f"| {name} | " + " | ".join(["**NOT PRESENT**"] * len(NS.SEG)) + " |")
                continue
            cells = []
            for seg in NS.SEG:
                v = rows[name][seg].get(metric)
                cells.append("n/a" if v is None else (f"{100*v:+.2f}%" if metric != "sharpe" else f"{v:+.2f}"))
            L.append(f"| {name} | " + " | ".join(cells) + " |")
        L.append("")
    L += ["**口径与装置是否相同**", "",
          "| 臂 | runs 根 | 格 | 运行配置与 Stage-1 OLD 的叶级差异 |", "|---|---|---|---|"]
    for name, *_ in [(a[0],) for a in ARMS]:
        p = prov[name]
        d = p["config_vs_OLD"]
        if "NOT_COMPARED" in d:
            s = "**未比对**:" + d["NOT_COMPARED"]
        else:
            names = [x["leaf"] for x in d["differing_leaves"]]
            s = (f"{d['n_differing_leaves']} 处, 其中**影响设置的 {d['n_setting_like']} 处**"
                 + ("(⇒ 设置一致, 可比)" if d["comparable_on_settings"] else
                    "(⇒ **设置不一致**: " + ", ".join(f"`{n}`" for n in d["setting_like_leaves"][:5]) + ")")
                 + "; 其余为标签/谱系/目标: " + ", ".join(f"`{n}`" for n in names[:5])
                 + (" …" if len(names) > 5 else ""))
        L.append(f"| {name} | `{os.path.basename(os.path.dirname(p['runs_root']))}` | `{p['cell']}` | {s} |")
    if unavailable:
        L += ["", "**缺测(具名, 不省略)**", ""] + [f"- `{u['arm']}`: {u['why']}" for u in unavailable]
    open(out_md, "w").write("\n".join(L) + "\n")
    print(f"THREE_WAY_TABLE arms={len(rows)}/{len(ARMS)} unavailable={len(unavailable)} "
          f"json_sha256={sha(out_json)} md_sha256={sha(out_md)}", flush=True)


if __name__ == "__main__":
    main()
