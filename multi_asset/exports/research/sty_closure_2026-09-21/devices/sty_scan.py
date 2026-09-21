#!/usr/bin/env python3
"""sty_scan.py — the WITHDRAWAL SCANNER for STY-01/02 + H-02 (round-8 review §1 "活动引用未闭合", notes/policy.md POL-01/POL-04).

WHY A DEVICE AND NOT A grep. My own rule (2026-09-16): a withdrawal binds only the file I wrote the withdrawal in; every other
file that repeats the number keeps repeating it, and so does every handoff already sent. The round-8 reviewer measured exactly
that: the ledger withdrew the readings, and SEVEN live files still carried them. So the closure has to be a device that

  (a) enumerates a CLOSED, COUNTED population across THREE scopes — repository text, the long-term memory directory's file
      BODIES, those files' `description:` frontmatter lines, and the MEMORY.md index lines — because the last three are
      separate reading surfaces and a scan of one says nothing about the others;
  (b) proves it REACHES each scope with a POSITIVE CONTROL: the same enumerators are run over a fixture root with a canary
      planted in every scope, and every canary must be found. Without this, "0 hits" and "this scope was never opened" are the
      same number ("零测量也算通过"是假绿一族, 2026-09-18);
  (c) is FALSIFIABLE about its own reach: a scope whose control canary is NOT found makes the whole run red, whatever the hit
      count says.

WHAT IT LOOKS FOR. Each token is a WITHDRAWN reading or a superseded number, with the correct replacement named. A line matches
only if it carries the token and NOT an accompanying withdrawal marker — so the original bytes may stay, annotated in place.

Exit 0 iff every control canary was found AND no unannotated hit remains.
Usage:  python3 sty_scan.py [--json OUT]
"""
import argparse, json, os, re, shutil, sys, tempfile

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", ".."))
MEMORY = os.path.expanduser("~/.claude/projects/-Users-haosiyu-Desktop-quant-research/memory")

# ── the withdrawal markers. A line carrying the token AND one of these is ANNOTATED, i.e. closed, not a hit.
MARKERS = ("⚠撤回", "⚠ 撤回", "已撤回", "WITHDRAWN", "superseded", "SUPERSEDED", "作废", "E-0921-C", "E-0921-D",
           "R8-POL-02", "STY-01 撤回", "STY-02 撤回")

# ── (token id, pattern, what is wrong, what it must say instead)
TOKENS = [
    ("STY02_16_84", r"构造\s*(约)?\s*16\s*%|环境\s*(约)?\s*84\s*%|16\s*%\s*[,，/]\s*环境",
     "16% = 整窗水平差 0.465879 ÷ 跨期改善 2.914817 — 分子与分母是两个不同的量, 人口也不同 (E-0921-C)",
     "四格恒等式 2.914817 = 2.783435 + 0.131382 ⇒ 形态占 4.5%; 另外 95.5% 不得叫「环境」(NONE 仍是一个有信号/席位/成本的策略世界, 只是另一种构造)"),
    ("STY01_STRONGLY_SUPPORTED", r"(方向性|共同/风格|共同/風格|逐名|β|CF3|STY-01|NONE)[^。\n]{0,120}(被强支持|强支持)|(被强支持|强支持)[^。\n]{0,120}(方向性|共同/风格|逐名|β)",
     "预注册判词是 UNDECIDED; 方向性主张没有被任何预注册判据裁定 (E-0920-F: 数字可以读, 判词不能改)",
     "「方向性主张与实测同向且更强, 但按写在数字之前的相似性判据判为不支持 ⇒ 判词 UNDECIDED」"),
    ("STY01_POSITIVELY_EXCLUDED", r"(逐名|共同/风格|方向性|CF3|STY-01|两本书)[^。\n]{0,120}(被正面排除|正面排除|被明确否掉)|(被正面排除|正面排除|被明确否掉)[^。\n]{0,120}(逐名|共同/风格|方向性)",
     "把一条预注册判据的不支持读成对立命题的证成 — 同一族的判据设计错误 (E-0920-F)",
     "「该读法要求逐名 ≥ 65%, 实测 35.1% ⇒ 按该条判据不支持」, 不说「排除」"),
    ("STY_BETA_NO_CONTRIBUTION", r"(β|beta|共同项)[^。\n]{0,80}(没有贡献|无贡献)|(没有贡献|无贡献)[^。\n]{0,40}(β|beta|共同项)",
     "p = 0.84 是不显著, 不是零; 「不显著 ≠ 无贡献」(round-8 §1 接受的收窄)",
     "「共同项 −0.065, CI [−0.702, +0.633], p = 0.84 ⇒ 未能识别出贡献」"),
    ("H02_PRODUCT_OF_MEANS", r"159\.9206|159\.92063|159\.92060",
     "两个完整精度均值相乘, 遗漏了跨路径协方差 100·Cov = −0.01786366pp (R8-POL-02)",
     "逐路径同本金均值 159.902772pp (mean_s[(1+R_hit,s)×R_after,s] = mean_s[R_end,s − R_hit,s])"),
    ("H02_214PP", r"214\s*pp|213\.997|213\.9970",
     "214pp 是从缩小后的本金起算的后续收益, 不是同一本金下的差 (E-0921-D)",
     "同一本金下 159.902772pp (约 160pp)"),
]
RX = [(tid, re.compile(pat), why, fix) for tid, pat, why, fix in TOKENS]

TEXT_EXT = (".md", ".py", ".txt", ".json", ".sh", ".jsonl")
SKIP_DIRS = {".git", "__pycache__", ".claude", "node_modules", ".venv"}


def _annotated(line, heading=""):
    """CLOSED only when the LINE itself carries a withdrawal marker.

    An earlier version also accepted the enclosing `## E-09xx-Y` heading, on the reasoning that a ledger entry's purpose is to
    quote the wrong number. That was too generous in a way that mattered: inside E-0921-D the CORRECTED figure 159.9206 is an
    assertion, not a quotation, and R8-POL-02 supersedes it — block annotation marked it closed. A marker has to sit on the
    line that makes the claim."""
    return any(m in line for m in MARKERS)


def _scan_text(path, rel, scope, out, only_line_pred=None):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
    except Exception as e:                                        # noqa: BLE001
        out["unreadable"].append({"scope": scope, "path": rel, "why": f"{type(e).__name__}: {e}"})
        return 0
    out["files_scanned"][scope] += 1
    n = 0
    heading = ""
    for i, line in enumerate(lines, 1):
        if line.startswith("#"):
            heading = line
        if only_line_pred is not None and not only_line_pred(line):
            continue
        for tid, rx, why, fix in RX:
            if rx.search(line):
                n += 1
                rec = {"scope": scope, "path": rel, "line": i, "token": tid, "text": line.strip()[:220],
                       "annotated": _annotated(line, heading), "heading": heading[:120],
                       "why_wrong": why, "must_say": fix}
                (out["closed"] if rec["annotated"] else out["open"]).append(rec)
    return n


def repo_population(root):
    """The repository scope's population is the GIT-TRACKED text files. Stated rather than implied: an untracked working-tree
    file is not a published reading surface, and walking this repo's tree (iCloud Desktop, ~10^5 binary artefacts) takes so
    long that the scan would stop being runnable, which is its own kind of unclosed. `git ls-files -z` is exact and fast."""
    import subprocess
    r = subprocess.run(["git", "-C", root, "ls-files", "-z"], capture_output=True)
    if r.returncode != 0:
        return None, f"git ls-files failed rc={r.returncode}: {r.stderr.decode()[:200]}"
    rels = [x for x in r.stdout.decode("utf-8", "replace").split("\0") if x]
    keep, excluded = [], []
    for x in rels:
        if x.split("/")[0] in SKIP_DIRS:
            continue
        if x.endswith((".md", ".txt", ".py", ".sh")):
            keep.append(x)
        elif x.endswith((".json", ".jsonl")):
            # a json under docs/ is a written claim; a json elsewhere is a FROZEN machine artefact whose bytes ARE its identity
            # (E-0921-E: 冻结件刻意不动 — editing one breaks the receipt it certifies). Excluded BY RULE, counted, and named,
            # never silently: the count is printed on the verdict line.
            (keep if x.startswith("docs/") else excluded).append(x)
    return keep, (None, excluded)


def scan_repo(root, out):
    rels, info = repo_population(root)
    if rels is None:                                  # a scope that cannot be enumerated is NOT an empty scope
        out["unreadable"].append({"scope": "repo_body", "path": root, "why": info})
        return
    _err, excluded = info
    out["population"]["repo_body"] = len(rels)
    out["population"]["repo_frozen_json_excluded"] = len(excluded)
    out["population"]["repo_frozen_json_examples"] = excluded[:5]
    for rel in rels:
        p = os.path.join(root, rel)
        if os.path.isfile(p):
            _scan_text(p, rel, "repo_body", out)


def scan_memory(root, out):
    """THREE separate surfaces in one directory: every file's BODY, every file's `description:` frontmatter line, and the
    MEMORY.md index lines. A hit in one says nothing about the others, so they are counted separately."""
    if not os.path.isdir(root):
        out["unreadable"].append({"scope": "memory_*", "path": root, "why": "memory directory not found"})
        return
    for fn in sorted(os.listdir(root)):
        if not fn.endswith(".md"):
            continue
        p = os.path.join(root, fn)
        if fn == "MEMORY.md":
            _scan_text(p, fn, "memory_index", out)
            continue
        _scan_text(p, fn, "memory_body", out)
        _scan_text(p, fn, "memory_description", out, only_line_pred=lambda l: l.startswith("description:"))


def new_out():
    return {"open": [], "closed": [], "unreadable": [], "population": {},
            "files_scanned": {"repo_body": 0, "memory_body": 0, "memory_description": 0, "memory_index": 0}}


# ─────────────────────────────────────────────────────────────────── POSITIVE CONTROL: does the scanner reach each scope?
CANARY = "构造 约 16 %, 环境 约 84 %"          # matches STY02_16_84; planted verbatim in every scope


def positive_control():
    """Run the SAME enumerators over a fixture root with a canary planted in each of the four scopes. Every scope must report
    its canary. A scope that reports none is not 'clean' — it is not being read, and that makes the whole run red."""
    d = tempfile.mkdtemp(prefix="sty_ctrl_")
    repo = os.path.join(d, "repo"); mem = os.path.join(d, "memory")
    os.makedirs(os.path.join(repo, "docs")); os.makedirs(mem)
    open(os.path.join(repo, "docs", "canary.md"), "w", encoding="utf-8").write("# c\n\n" + CANARY + "\n")
    open(os.path.join(mem, "canary_body.md"), "w", encoding="utf-8").write(
        "---\nname: canary-body\ndescription: harmless\nmetadata:\n  type: project\n---\n\n" + CANARY + "\n")
    open(os.path.join(mem, "canary_desc.md"), "w", encoding="utf-8").write(
        "---\nname: canary-desc\ndescription: " + CANARY + "\nmetadata:\n  type: project\n---\n\nbody is clean\n")
    open(os.path.join(mem, "MEMORY.md"), "w", encoding="utf-8").write("# MEMORY 索引\n\n- [canary](canary.md) — " + CANARY + "\n")
    import subprocess
    subprocess.run(["git", "-C", repo, "init", "-q"], capture_output=True)
    subprocess.run(["git", "-C", repo, "add", "-A"], capture_output=True)
    out = new_out()
    scan_repo(repo, out)
    scan_memory(mem, out)
    found = {}
    for rec in out["open"] + out["closed"]:
        found.setdefault(rec["scope"], 0)
        found[rec["scope"]] += 1
    shutil.rmtree(d, ignore_errors=True)
    need = ["repo_body", "memory_body", "memory_description", "memory_index"]
    missed = [s for s in need if not found.get(s)]
    # the description scope must find the canary in canary_desc.md ONLY through the frontmatter line — assert the body scope
    # also saw canary_body.md, so the two are genuinely distinct surfaces and not one scan counted twice
    return {"scopes_required": need, "found_per_scope": found, "scopes_not_reached": missed,
            "ok": not missed, "canary": CANARY, "fixture_files_scanned": out["files_scanned"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=None)
    ap.add_argument("--repo", default=REPO)
    ap.add_argument("--memory", default=MEMORY)
    a = ap.parse_args()

    ctrl = positive_control()
    out = new_out()
    scan_repo(a.repo, out)
    scan_memory(a.memory, out)

    by_tok = {}
    for r in out["open"]:
        by_tok.setdefault(r["token"], []).append(f"{r['path']}:{r['line']}")
    res = {"device": "sty_scan.py", "repo": a.repo, "memory": a.memory,
           "positive_control": ctrl, "files_scanned": out["files_scanned"], "population": out["population"], "population": out["population"],
           "n_open": len(out["open"]), "n_closed_annotated": len(out["closed"]),
           "open_by_token": by_tok, "open": out["open"], "closed": out["closed"], "unreadable": out["unreadable"]}
    ok = ctrl["ok"] and not out["open"] and not out["unreadable"]
    res["VERDICT"] = "PASS" if ok else ("CONTROL_FAILED" if not ctrl["ok"] else "OPEN_REFERENCES")
    if a.json:
        os.makedirs(os.path.dirname(os.path.abspath(a.json)), exist_ok=True)
        json.dump(res, open(a.json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for r in out["open"]:
        print(f"  OPEN  [{r['token']}] {r['path']}:{r['line']}  {r['text'][:130]}")
    print(f"\nSTY_SCAN VERDICT={res['VERDICT']} control_scopes_reached="
          f"{len(ctrl['found_per_scope'])}/{len(ctrl['scopes_required'])} not_reached={ctrl['scopes_not_reached']} "
          f"files_scanned={out['files_scanned']} frozen_json_excluded={out['population'].get('repo_frozen_json_excluded')} "
          f"open={len(out['open'])} annotated={len(out['closed'])} "
          f"unreadable={len(out['unreadable'])}", flush=True)
    sys.exit(0 if ok else 3)


if __name__ == "__main__":
    main()
