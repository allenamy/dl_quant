import sys, pathlib, hashlib
src_dir, out_dir, ws = map(pathlib.Path, sys.argv[1:4])
out_dir.mkdir(parents=True, exist_ok=True)
SUBS = {
 "probe_followup.py": [("C=O/'sources/multi_asset/exports/research/retrain_2026-09/v4_chain_2026-09-09'", f"C=pathlib.Path({str(ws)!r})")],
 "probe_w7_followup.py": [("C=O/'sources/multi_asset/exports/research/retrain_2026-09/v4_chain_2026-09-09'", f"C=pathlib.Path({str(ws)!r})")],
 "probe_boundaries.py": [("B=O.parents[4]\n", "B=O\n"),
                         ("assert str(B)=='/Users/haosiyu/Desktop/quant_research/.claude/worktrees/codex-independent-20260907'\n", ""),
                         ("assert subprocess.check_output(['git','branch','--show-current'],cwd=B,text=True).strip()=='agent/codex/QNT-2026-0907/onboarding-audit'\n", ""),
                         ("C=O/'sources/multi_asset/exports/research/retrain_2026-09/v4_chain_2026-09-09'", f"C=pathlib.Path({str(ws)!r})")],
}
man = {}
for name, subs in SUBS.items():
    t = (src_dir / name).read_text(); man[name] = {"original_sha256": hashlib.sha256(t.encode()).hexdigest()}
    for a, b in subs:
        assert t.count(a) == 1, (name, a, t.count(a)); t = t.replace(a, b)
    t = "import pathlib\n" + t if not t.startswith('"""') else t.replace('"""', '"""', 1)
    # insert `import pathlib` after the docstring's first import line
    t = t.replace("\nimport ", "\nimport pathlib\nimport ", 1)
    (out_dir / name).write_text(t); man[name]["patched_sha256"] = hashlib.sha256(t.encode()).hexdigest()
import json; (out_dir / "PATCH_MANIFEST.json").write_text(json.dumps({"substitutions": {k: [(a[:90], b[:90]) for a, b in v] for k, v in SUBS.items()}, "files": man}, indent=1))
print(json.dumps(man, indent=1))
