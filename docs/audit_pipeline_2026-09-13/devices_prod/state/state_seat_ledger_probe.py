#!/usr/bin/env python3
"""state_seat_ledger_probe.py -- AUDIT_PROD item 4 (serving-state artifacts), READ-ONLY on ~/wide_shadow.
Computes, from the live producer state files in place (no copy, no write outside the receipt path):
  S1 seat seeding: which king-column rows of state/leg_returns_live.json are the 09-05 seeded v3-bundle rows (exact float
     match to shadow_bundle/leg_returns.npz king at the same anchor) vs producer-appended rows; anchor mapping of the tail via
     shadow_log 'score' events (one LR append per score event, shadow_loop_v3.py L433-454); booster per appended row from the
     'signal' event of that anchor; msharpe w3 recomputed from the file (shadow_loop_v3.py L456-462) vs the latest signal w3;
     composition of the 900-row window; anchors until the last seeded row leaves the window.
  S2 ledger iv artefacts: in aux.json ledger_tail, rows whose stored iv != allowed-snapped gap to the previous row
     (shadow_loop_v3.py L341-343 rule), split before/after 2026-09-05 12:00Z; D17 residual projection from the P2 G2-B receipt
     (pure arithmetic 0.5**(dt/3d), labelled INFERRED).
  S6 serving-state checks: symbol-axis identity cfg symbols_panel vs fea171/xfer_ref.npz / xfer_syms.npz (combo_stage maps names
     through xfer_ref, L136/L212); target_combo kc/fc state sources; target_live producer form per anchor since combo went live
     (king-form anchors = combo not applied); producer write time N+m per anchor from the signal log (combo daemon skips silently
     when now-anchor > 1355 s, combo_live_daemon.sh L32-34).
Usage (Mac, outside anchor windows): env -i PATH=/usr/bin:/bin HOME=/Users/haosiyu /Users/haosiyu/wide_shadow/venv/bin/python -B \
  docs/audit_pipeline_2026-09-13/devices_prod/state/state_seat_ledger_probe.py PATH,HOME,LC_CTYPE,__CF_USER_TEXT_ENCODING
"""
import os, sys, json, time, hashlib, glob, datetime
WHITE = set(x for x in sys.argv[1].split(",") if x) if len(sys.argv) > 1 else None
assert WHITE, "env whitelist argv[1] required"
assert sorted(k for k in os.environ if k not in WHITE) == [], ("ENV WHITELIST VIOLATION", sorted(os.environ))
import numpy as np

WS = "/Users/haosiyu/wide_shadow"
REPO = "/Users/haosiyu/Desktop/quant_research"
OUT = f"{REPO}/docs/audit_pipeline_2026-09-13/receipts_prod/state_seat_ledger_probe.json"
G2B = f"{REPO}/multi_asset/exports/research/parity_replay_2026-09-12/phase2/receipts/G2B_funding_parity.json"
T0 = time.time()

def sha(p):
    h = hashlib.sha256(); n = 0
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b); n += len(b)
    assert n == os.stat(p).st_size, ("short read", p)
    return h.hexdigest()

def U(t): return datetime.datetime.fromtimestamp(int(t), datetime.timezone.utc).strftime("%Y-%m-%d %H:%MZ")

INPUTS = {
    "leg_returns_live": f"{WS}/state/leg_returns_live.json",
    "leg_returns_pre_seed": f"{WS}/state/leg_returns_live.json.pre_seatseed_v3_20260905",
    "bundle_v3_leg_returns": f"{WS}/shadow_bundle/leg_returns.npz",
    "bundle_aug_leg_returns": f"{WS}/shadow_bundle.aug20260816_backup/leg_returns.npz",
    "shadow_log": f"{WS}/shadow_log.jsonl",
    "aux": f"{WS}/state/aux.json",
    "config": f"{WS}/shadow_bundle/config.json",
    "xfer_ref": f"{WS}/fea171/xfer_ref.npz",
    "xfer_syms": f"{WS}/fea171/xfer_syms.npz",
    "shadow_loop_v3": f"{WS}/shadow_loop_v3.py",
    "combo_stage": f"{WS}/fea171/combo_stage.py",
    "combo_live_daemon": f"{WS}/fea171/combo_live_daemon.sh",
    "g2b_receipt": G2B,
}
SHA0 = {k: sha(p) for k, p in INPUTS.items()}
assert SHA0["shadow_loop_v3"].startswith("e9c9837412130884"), SHA0["shadow_loop_v3"]
assert SHA0["combo_stage"].startswith("b5c698f9d1ee9acb"), SHA0["combo_stage"]
R = {"self_sha256": sha(os.path.abspath(__file__)), "inputs_sha256_start": SHA0,
     "env": {"whitelist": sorted(WHITE), "actual": {k: os.environ[k] for k in sorted(os.environ)}},
     "command": "env -i PATH=/usr/bin:/bin HOME=/Users/haosiyu /Users/haosiyu/wide_shadow/venv/bin/python -B "
                "docs/audit_pipeline_2026-09-13/devices_prod/state/state_seat_ledger_probe.py PATH,HOME,LC_CTYPE,__CF_USER_TEXT_ENCODING"}

cfg = json.load(open(INPUTS["config"])); look = int(cfg["params"]["msharpe_look"])
LOG = [json.loads(l) for l in open(INPUTS["shadow_log"]) if l.strip()]
score = [r for r in LOG if r.get("e") == "score"]
signal = {int(r["anchor_ts"]): r for r in LOG if r.get("e") == "signal"}
latest_sig = max(signal)

# ---------------- S1 seat rows ----------------
L = json.load(open(INPUTS["leg_returns_live"])); n = len(L["king"])
assert all(len(L[k]) == n for k in ("king", "rev24", "fund"))
B3 = np.load(INPUTS["bundle_v3_leg_returns"]); b3ts = B3["ts"].astype(np.int64)
k3 = {}
for t, v in zip(b3ts, B3["king"]): k3.setdefault(float(v), []).append(int(t))
king = [float(x) for x in L["king"]]
match_ts = [k3.get(v) for v in king]
seeded_idx = [i for i, m in enumerate(match_ts) if m is not None]
ambiguous = [i for i in seeded_idx if len(match_ts[i]) > 1]
s1 = {"n_rows_file": n, "msharpe_look": look, "n_king_rows_equal_to_v3_bundle_value": len(seeded_idx),
      "ambiguous_value_matches": len(ambiguous)}
if seeded_idx:
    contiguous_block = seeded_idx == list(range(seeded_idx[0], seeded_idx[-1] + 1))
    ts_seed = [match_ts[i][0] for i in seeded_idx]
    s1.update(seeded_first_idx=seeded_idx[0], seeded_last_idx=seeded_idx[-1], seeded_idx_contiguous=bool(contiguous_block),
              seeded_ts_first=U(ts_seed[0]), seeded_ts_last=U(ts_seed[-1]),
              seeded_ts_nonconsecutive_steps=[(U(a), U(b)) for a, b in zip(ts_seed[:-1], ts_seed[1:]) if b - a != 14400])
    # fund / rev24 of the seeded-era rows vs the v3 bundle rows at the same anchor
    pos3 = {int(t): j for j, t in enumerate(b3ts)}
    feq = sum(1 for i, t in zip(seeded_idx, ts_seed) if float(L["fund"][i]) == float(B3["fund"][pos3[t]]))
    req = sum(1 for i, t in zip(seeded_idx, ts_seed) if float(L["rev24"][i]) == float(B3["rev24"][pos3[t]]))
    s1.update(seeded_rows_fund_equal_v3_bundle=feq, seeded_rows_rev24_equal_v3_bundle=req)
# tail mapping via score events (one LR append per score event)
tail_n = n - (seeded_idx[-1] + 1 if seeded_idx else 0)
sc_tail = score[-n:] if len(score) >= n else score
map_ts = {}
for k in range(1, min(n, len(score)) + 1):
    map_ts[n - k] = int(score[-k]["anchor_ts"])
agree = sum(1 for i in seeded_idx if i in map_ts and map_ts[i] in match_ts[i])
disagree = [(i, U(map_ts[i]), [U(x) for x in match_ts[i]]) for i in seeded_idx if i in map_ts and map_ts[i] not in match_ts[i]]
live_idx = list(range(n - tail_n, n))
live_rows = []
for i in live_idx:
    t = map_ts.get(i); sg = signal.get(t) if t is not None else None
    live_rows.append({"idx": i, "anchor": U(t) if t else None, "booster_sha": (sg or {}).get("booster_sha")})
from collections import Counter
s1.update(n_score_events_in_log=len(score), score_mapping_covers_rows_from_idx=min(map_ts) if map_ts else None,
          seeded_rows_where_score_mapping_agrees=agree, seeded_rows_where_score_mapping_disagrees=disagree[:10],
          n_producer_rows_after_last_seeded=tail_n,
          producer_rows_anchor_first=live_rows[0]["anchor"] if live_rows else None,
          producer_rows_anchor_last=live_rows[-1]["anchor"] if live_rows else None,
          producer_rows_by_booster=dict(Counter(r["booster_sha"] for r in live_rows)))
# pre-seed backup alignment: fund/rev24 were not re-seeded -> current[:n-k] == backup[k:]
PB = json.load(open(INPUTS["leg_returns_pre_seed"]))
shift = None
for k in range(0, n):
    if [float(x) for x in L["fund"][:n - k]] == [float(x) for x in PB["fund"][k:]] and \
       [float(x) for x in L["rev24"][:n - k]] == [float(x) for x in PB["rev24"][k:]]:
        shift = k; break
t_seed = int(datetime.datetime(2026, 9, 5, 12, 47, tzinfo=datetime.timezone.utc).timestamp())
n_score_since_seed = sum(1 for r in score if datetime.datetime.strptime(r["logged_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc).timestamp() > t_seed)
s1.update(rows_appended_since_pre_seed_backup_by_fund_rev24_alignment=shift, score_events_logged_after_2026_09_05_12_47Z=n_score_since_seed)
# window composition and msharpe recompute
win_lo = n - look
s1.update(window_row_range=[win_lo, n - 1],
          seeded_rows_in_window=max(0, (seeded_idx[-1] + 1 - win_lo)) if seeded_idx else 0,
          producer_rows_in_window=min(look, tail_n))
r = np.stack([np.array(L[leg][-look:], np.float64) for leg in ("king", "rev24", "fund")])
shp = r.mean(1) / (r.std(1) + 1e-9); shp = np.maximum(shp, 0.0)
w3 = shp / shp.sum() if shp.sum() > 0 else np.array([1 / 3] * 3)
w3m = np.array([w3[0], 0.0, w3[2]]); w3m = w3m / w3m.sum()
sig_w3 = signal[latest_sig]["w3"]
s1.update(w3_recomputed_from_file=[round(float(x), 6) for x in w3], latest_signal_anchor=U(latest_sig), latest_signal_w3=sig_w3,
          w3_max_abs_diff_vs_signal_4dp=float(np.max(np.abs(np.round(w3, 4) - np.array(sig_w3)))),
          w3m_recomputed=[round(float(x), 6) for x in w3m])
tc = sorted(glob.glob(f"{WS}/state/target_combo/*.json"))
last_tc = json.load(open(tc[-1])); s1["latest_target_combo"] = {"anchor": U(last_tc["anchor_ts"]), "w3_masked": last_tc["w3_masked"]}
# note: the target_combo written at anchor A uses the LR state after the append at A (the same w3 as signal A)
if seeded_idx:
    n_more = seeded_idx[-1] - win_lo + 1            # appends needed until the last seeded row index < n - look
    s1.update(scored_anchors_until_last_seeded_row_leaves_window=int(n_more),
              projected_exit_anchor_if_every_anchor_scored=U(latest_sig + 14400 * n_more))
# seat with the seeded rows' king values replaced by the mean of producer rows is NOT computed (no counterfactual claim)
R["S1"] = s1

# ---------------- S2 ledger iv artefacts ----------------
aux = json.load(open(INPUTS["aux"]))
ALLOWED = [1.0, 2.0, 4.0, 6.0, 8.0]
cut = 1788609600   # 2026-09-05 12:00Z
mm_before, mm_after, rows_checked = Counter(), Counter(), 0
ex_after = []
for s, rows in aux["ledger_tail"].items():
    for a, b in zip(rows[:-1], rows[1:]):
        gap = (b[0] - a[0]) / 3600.0
        snap = float(min(ALLOWED, key=lambda x: abs(x - (gap if 0 < gap <= 24 else 8.0))))
        rows_checked += 1
        if abs(float(b[2]) - snap) > 1e-9:
            (mm_after if b[0] >= cut else mm_before)[s] += 1
            if b[0] >= cut and len(ex_after) < 20: ex_after.append((s, U(b[0]), b[2], snap))
tail_first = min(rows[0][0] for rows in aux["ledger_tail"].values() if rows)
s2 = {"ledger_names": len(aux["ledger_tail"]), "adjacent_row_pairs_checked": rows_checked, "tail_oldest_row": U(tail_first),
      "stored_iv_ne_gap_iv_rows_before_2026_09_05_12Z": dict(mm_before), "stored_iv_ne_gap_iv_rows_after_2026_09_05_12Z": dict(mm_after),
      "examples_after": ex_after, "ema_names": len(aux["ema"]), "aux_last_anchor": U(aux["last_anchor"])}
g = json.load(open(G2B))
first = g["per_anchor"][0]; last = g["per_anchor"][-1]
t_first = int(first.get("anchor", first.get("anchor_ts", 0)) or 0)
s2["g2b_receipt"] = {"worst_abs_first_anchor": g["per_anchor"][0]["worst_abs"], "worst_abs_last_anchor": last["worst_abs"],
                     "n_per_anchor": len(g["per_anchor"]), "keys_first": sorted(first.keys())[:12]}
if t_first:
    s2["g2b_receipt"]["first_anchor"] = U(t_first)
    t_last = int(last.get("anchor", last.get("anchor_ts", 0)) or 0)
    s2["g2b_receipt"]["last_anchor"] = U(t_last)
    proj = float(last["worst_abs"]) * 0.5 ** ((latest_sig - t_last) / (3 * 86400.0))
    s2["INFERRED_projection_worst_abs_at_latest_anchor"] = {"anchor": U(latest_sig), "value": proj,
                                                             "rule": "worst_abs(last receipt anchor) * 0.5**(dt/3d); valid only if no new artefact rows (see counts above)"}
R["S2"] = s2

# ---------------- S6 serving-state checks ----------------
XR = np.load(INPUTS["xfer_ref"], allow_pickle=True); XS = np.load(INPUTS["xfer_syms"], allow_pickle=True)
sp = [str(x) for x in cfg["symbols_panel"]]
s6 = {"symbols_panel_n": len(sp), "xfer_ref_symbols_identical": [str(x) for x in XR["symbols"]] == sp,
      "xfer_syms_symbols_identical": [str(x) for x in XS["symbols"]] == sp,
      "xfer_syms_ch": [str(x) for x in XS["ch"]]}
srcs = Counter(); nonown = []
for p in tc:
    d = json.load(open(p)); key = (d.get("kc_state_source"), d.get("fc_state_source")); srcs[str(key)] += 1
    if key != ("own", "own"): nonown.append((U(d["anchor_ts"]), key))
s6["target_combo_files"] = len(tc); s6["target_combo_state_sources"] = dict(srcs); s6["target_combo_non_own_anchors"] = nonown
forms = Counter(); kingform = []
for p in sorted(glob.glob(f"{WS}/state/target_live/*.json")):
    d = json.load(open(p)); A = int(d["anchor_ts"])
    if A < 1787716800: continue          # combo_live first anchor 2026-08-26 04:00Z (MILESTONE_2026-08-26)
    prod = str(d.get("producer", ""))
    form = "combo" if prod.startswith("combo_stage") else ("king" if prod.startswith("shadow_loop") else prod[:30])
    forms[form] += 1
    if form != "combo": kingform.append(U(A))
anchors_expected = list(range(1787716800, latest_sig + 1, 14400))
have = {int(os.path.basename(p)[:-5]) for p in glob.glob(f"{WS}/state/target_live/*.json")}
s6["target_live_forms_since_2026_08_26_04Z"] = dict(forms); s6["target_live_king_form_anchors"] = kingform
s6["anchors_without_target_live_since_2026_08_26_04Z"] = [U(a) for a in anchors_expected if a not in have]
lag = []
for A, sgr in sorted(signal.items()):
    if A < 1787716800: continue
    tl = datetime.datetime.strptime(sgr["logged_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc).timestamp()
    lag.append(tl - A)
lag = np.array(lag)
s6["producer_signal_logged_minus_anchor_s"] = {"n": int(len(lag)), "median": float(np.median(lag)), "p90": float(np.quantile(lag, 0.9)),
                                                "max": float(lag.max()), "n_over_1355s": int((lag > 1355).sum()), "n_over_1200s": int((lag > 1200).sum())}
R["S6"] = s6

SHA1 = {k: sha(p) for k, p in INPUTS.items()}
R["inputs_unchanged_during_run"] = SHA1 == SHA0
R["changed_inputs"] = [k for k in SHA0 if SHA0[k] != SHA1[k]]
R["built_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()); R["wall_s"] = round(time.time() - T0, 2)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump(R, open(OUT, "w"), indent=1, default=str)
print(json.dumps({k: R[k] for k in ("S1", "S2", "S6", "inputs_unchanged_during_run", "changed_inputs", "wall_s")}, indent=1, default=str))
print("SUMMARY state_seat_ledger_probe rc=0")
