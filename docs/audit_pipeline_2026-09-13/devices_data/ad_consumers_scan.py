#!/usr/bin/env python3
"""ad_consumers_scan.py -- AUDIT_DATA 2026-09-13, device E (Mac, READ-ONLY, git objects only).

Builds the dataset x consumer dependency matrix: which devices committed since 2026-09-09T00:00Z (git log --since, *.py / *.sh)
reference which dataset, by `git grep -n` on the HEAD tree (object database, so iCloud-evicted working-tree files cannot read as empty).
A reference is a literal token in the device source (path or basename); aliases of the replay tree (wide_panel_4h_hist_v2.npz ->
v2ext, wide_fea_hist_meta.npz -> meta_newprod_*, slow_pred_hist_oos.npy -> SLOW_*) are kept as their own tokens because the realpath
depends on the tree the device is pointed at (resolved on pod2 by ad_inventory.py `symlink_trees`).
Usage: python3 ad_consumers_scan.py <repo_root> <out.json>
"""
import os, sys, json, subprocess, re, hashlib, time
REPO, OUT = sys.argv[1], sys.argv[2]
SINCE = "2026-09-09T00:00:00Z"
TOKENS = {
    "cache_holefix2": r"dlnative_5m_wide829_f16_holefix2\.npz", "cache_holefix2_x0910": r"dlnative_5m_wide829_f16_holefix2_x0910",
    "cache_holefix_round1": r"dlnative_5m_wide829_f16_holefix\.npz", "cache_ext_prefix": r"dlnative_5m_wide829_f16_ext\.npz",
    "cache_holefix_raw": r"f16_holefix_raw|f16_holefix2_raw", "producer_rolling_cache": r"rolling\.npz|cache_tail_40d",
    "raw_patch": r"raw_patch\.npz", "raw_patch_x0910": r"raw_patch_x0910",
    "panel_v1": r"wide_panel_4h_v1\.npz", "panel_v2ext": r"wide_panel_4h_v2ext\.npz", "panel_alias_hist_v2": r"wide_panel_4h_hist_v2\.npz",
    "panel_v3splice": r"wide_panel_4h_v3splice\.npz", "panel_v2ext_x0910": r"wide_panel_4h_v2ext_x0910", "panel_v3splice_x0910": r"wide_panel_4h_v3splice_x0910",
    "panel_v2holefix": r"wide_panel_4h_v2holefix",
    "king_meta_v4": r"wide_fea_v4_meta\.npz", "king_fea_v4": r"wide_fea_v4\.npy", "king_meta_v2ext": r"wide_fea_v2ext_meta|wide_fea_v2ext\.npy",
    "king_v4_x0910": r"wide_fea_v4_meta_x0910|wide_fea_v4_x0910", "king_v4e": r"wide_fea_v4e", "meta_alias_hist": r"wide_fea_hist_meta\.npz",
    "acct_meta_v4": r"meta_newprod_v4\.npz", "acct_meta_v4_x0910": r"meta_newprod_v4_x0910", "acct_meta_pre_v4": r"meta_newprod\.npz|meta_newprod_raw|meta_newprod_hf2",
    "dl_v4raw": r"dlw_v4raw(?!_x0910)", "dl_hf3_clip": r"dlw_hf3(?!_x0910)", "dl_ext": r"dlw_ext", "dl_x0910": r"dlw_targets_x0910|dlw_v4raw_x0910|dlw_hf3_x0910",
    "fea89": r"f8_fea89", "legs": r"f10v2_legs",
    "oof_king_v4": r"SLOW_v4\.npy", "oof_king_v3_on_v4": r"SLOW_v3_on_v4axis", "oof_king_x0910": r"SLOW_v4_x0910", "oof_alias_hist": r"slow_pred_hist_oos",
    "bundle_pinned": r"slow_pred_pinned", "oof_f10_A0": r"f10_A0_s", "oof_f10_v4RAW": r"f10_v4RAW", "oof_f10_V2MAIN_yearly": r"f10_V2MAIN_s",
    "umask_crypto": r"umask_UPIT_CRYPTO", "umask_upit": r"umask_UPIT\.npz", "umask_frozen_or_pins": r"umask_UFROZEN|live_pins|syms450",
    "fund_aug": r"fund_aug\.json\.gz", "fund_sep_r6": r"r6_fund_sep", "ledger_full_p2": r"ledger_full\.npz", "funding_zips": r"wide_multisrc/funding",
    "bundle_funding_seed": r"funding_ledger_seed", "metrics_archive": r"um/daily/metrics|futures/um/.*/metrics",
}
def git(*a): return subprocess.run(["git", "-C", REPO] + list(a), capture_output=True, text=True, check=True).stdout
devs = sorted({l for l in git("log", "--since=" + SINCE, "--name-only", "--pretty=format:").splitlines() if l.endswith((".py", ".sh"))})
head = git("rev-parse", "HEAD").strip()
present = set(git("ls-tree", "-r", "--name-only", "HEAD").splitlines())
devs = [d for d in devs if d in present and not d.startswith("docs/audit_pipeline_2026-09-13/")]   # v2: audit devices are not research consumers
matrix = {}
for name, pat in TOKENS.items():
    hits = {}
    for i in range(0, len(devs), 200):
        chunk = devs[i:i + 200]
        r = subprocess.run(["git", "-C", REPO, "grep", "-n", "-P", pat, "HEAD", "--"] + chunk, capture_output=True, text=True)
        for line in r.stdout.splitlines():
            m = re.match(r"^HEAD:(.*?):(\d+):", line)
            if m: hits.setdefault(m.group(1), []).append(int(m.group(2)))
    groups = {}
    for p in hits:
        parts = p.split("/"); g = "/".join(parts[:5]) if parts[:3] == ["multi_asset", "exports", "research"] else "/".join(parts[:3])
        groups[g] = groups.get(g, 0) + 1
    matrix[name] = {"pattern": pat, "n_devices": len(hits), "by_research_line": dict(sorted(groups.items(), key=lambda kv: -kv[1])), "devices": {p: sorted(v)[:6] for p, v in sorted(hits.items())}}
rec = {"device": "ad_consumers_scan.py", "self_sha256": hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest(), "repo_head": head, "since": SINCE,
       "n_devices_scanned": len(devs), "matrix": matrix, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
json.dump(rec, open(OUT, "w"), indent=1)
print("AD_CONSUMERS_SCAN_DONE devices=%d tokens=%d head=%s" % (len(devs), len(matrix), head[:10]))
