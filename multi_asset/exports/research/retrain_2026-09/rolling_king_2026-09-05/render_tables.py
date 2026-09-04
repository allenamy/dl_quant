"""render_tables.py — render REPORT tables in markdown from the script-produced JSON/logs (no hand transcription).
Reads: folds_rollm.json, folds_rollq.json, ic_legs_seat.json, judge.json, logs/*.log, logs/commands.txt. Prints markdown to stdout."""
import json, time, os, re, hashlib
ROOT = "/workspace/review_scratch/rolling_king"
def iso(t): return time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(t)))
def J(p): return json.load(open(f"{ROOT}/{p}"))
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
out = []
P = out.append

# ── folds ──
for tag, title in (("rollm", "monthly (PRIMARY)"), ("rollq", "quarterly (shape check)")):
    p = f"{ROOT}/folds_{tag}.json"
    if not os.path.exists(p): P(f"\n(folds_{tag}.json missing)"); continue
    F = J(f"folds_{tag}.json"); c = F["config"]
    P(f"\n### Folds — {title}: `slow_pred_{tag}.npy` sha256 `{F['sha256']}`; finite-mask equal to pinned = **{F['finite_mask_equal_pinned']}**; script sha256 `{c['self_sha256']}`; train_rule = `{c['train_rule']}`")
    P(f"\n| fold | test key | seed | train rows | train anchors | train span | test anchors (rows) | test span | ASSERT max(train E_ts)+48·300 < min(test E_ts)−60·14400 | gap | fit s | rank-IC (raw y4) |")
    P("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for f in F["folds"]:
        P(f"| {f['fold']} | {f['key']} | {f['seed']} | {f['train_rows']:,} | {f['train_anchors']} | {iso(f['train_first'])[:10]}..{iso(f['train_last'])} | {f['test_anchors_with_rows']}/{f['test_anchors_in_month']} ({f['test_rows']:,}) | {iso(f['test_first'])}..{iso(f['test_last'])} | {f['assert_lhs']} ({iso(f['assert_lhs'])}) < {f['assert_rhs']} ({iso(f['assert_rhs'])}) → **{f['assert_lhs'] < f['assert_rhs']}** | {(f['assert_rhs']-f['assert_lhs'])/14400:.0f} anchor | {f['fit_s']} | {f['rankIC_raw_y4']:+.4f} |")
    ics = [f["rankIC_raw_y4"] for f in F["folds"]]
    P(f"\nfolds {len(F['folds'])}, all asserts True = **{all(f['assert_lhs'] < f['assert_rhs'] for f in F['folds'])}**, mean per-fold rank-IC {sum(ics)/len(ics):+.4f}, total fit {sum(f['fit_s'] for f in F['folds']):.0f}s")

# ── IC / legs / seat ──
if os.path.exists(f"{ROOT}/ic_legs_seat.json"):
    S = J("ic_legs_seat.json"); kings = list(S["kings"].keys())
    for tgt, desc in (("raw", "raw y4 = Σ 5m simple returns over [E, E+47] (meta; production label source)"), ("y4s", "dlw y4s = Π(1+r5)−1 over [E+1, E+48] (compounded holding-window target)")):
        P(f"\n### Yearly mean rank-IC vs {desc}; identical anchor set for all sources (2024+, finite IC for every source)")
        P("\n| window | n | " + " | ".join(kings) + " | " + " | ".join(f"Δ {k}−pinned (mean ± SE)" for k in kings if k != "pinned") + " |")
        P("|---|---|" + "---|" * len(kings) + "---|" * (len(kings) - 1))
        for w in ("2024", "2025", "2026<=08-10", "2026->08-30", "2024->26", "2025->26"):
            r = S["ic"].get(f"{tgt}/{w}")
            if not r: continue
            P(f"| {w} | {r['n']} | " + " | ".join(f"{r[k]:+.4f}" for k in kings) + " | " + " | ".join(f"{r['d_'+k][0]:+.4f} ± {r['d_'+k][1]:.4f}" for k in kings if k != "pinned") + " |")
    for cal, desc in (("raw", "raw y4"), ("y4s", "dlw y4s (windows restricted to anchors with a dlw row, i.e. ≤ 2026-08-10 20:00Z)")):
        P(f"\n### King leg (production leg definition, bps per unit gross per anchor) — caliber {desc}; S = mean/std per anchor")
        P("\n| leg | 2024 | 2025 | 2026≤08-10 | 2026→08-30 | 2024→26 | 2025→26 | S/anchor 900 pre-0810 (seat window) | S/anchor last 900 |")
        P("|---|---|---|---|---|---|---|---|---|")
        for name in [f"king[{k}]" for k in kings] + ["rev24", "fund"]:
            r = S["legs"].get(f"{cal}/{name}")
            if not r: continue
            P(f"| {name} | " + " | ".join(f"{r[w][0]:+.3f} (S {r[w][1]:+.3f}, n {r[w][2]})" for w in ("2024", "2025", "2026<=08-10", "2026->08-30", "2024->26", "2025->26")) + f" | {r['S900pre']:+.4f} (mean {r['mean900pre']:+.3f}) | {r['S900last']:+.4f} (mean {r['mean900last']:+.3f}) |")
    P(f"\n### msharpe seat at 2026-08-10 20:00Z (production rule, LOOK 900; w3 = king/rev24/fund; w101 = LEGS=101 mask = deployed combo form)")
    P("\n| caliber | king source | shp king/rev24/fund (mean/std) | w3 king/rev24/fund | w101 king/fund |")
    P("|---|---|---|---|---|")
    for cal in ("raw", "y4s"):
        for k in kings:
            r = S["seat"].get(f"{cal}/{k}")
            if not r: continue
            P(f"| {cal} | {k} | {r['shp'][0]:+.4f}/{r['shp'][1]:+.4f}/{r['shp'][2]:+.4f} | {r['w3'][0]:.3f}/{r['w3'][1]:.3f}/{r['w3'][2]:.3f} | **{r['w101'][0]:.3f}**/{r['w101'][2]:.3f} |")

# ── judge ──
if os.path.exists(f"{ROOT}/judge.json"):
    G = J("judge.json"); kings = G["kings"]
    P(f"\n### Book level — arm `{G['arm']}`, column net_ex (bps/anchor per unit NAV); n={G['n_anchors']} anchors (identical set); windows: " + ", ".join(f"{w}={n}" for w, n in G["windows"].items()))
    CALD = {"log": "raw Σ-simple y4, CAL=log (no transform)", "prod": "compounded Π(1+r5)−1 over [E+1,E+48] (meta_newprod swap), CAL=log"}
    ARMD = {"Lfix": "L-fix (M829/T400/FTRIM, W3FIX 0.21/0/0.79)", "Ldyn": "L-dyn (M829/T400/FTRIM, msharpe)", "Cdyn": "C-dyn (canon, msharpe)"}
    for cal in ("log", "prod"):
        P(f"\n#### Levels — caliber **{cal}** = {CALD[cal]}")
        P("\n| arm | seed | king | 2024 | 2025 | 2026≤08-10 | 2026→08-30 | 2024→26 | 2025→26 | gross | w_king | w_fund | turnover |")
        P("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
        for arm in ("Lfix", "Ldyn", "Cdyn"):
            for seed in ("s42", "s2027"):
                for k in kings:
                    r = G["levels"].get(f"{cal}/{arm}/{seed}/{k}")
                    if not r: continue
                    q = r["2024->26"]
                    P(f"| {arm} | {seed} | {k} | " + " | ".join(f"{r[w]['mean']:+.3f} S{r[w]['sharpe']:+.2f} DD{r[w]['maxDD']:.0f}" for w in ("2024", "2025", "2026<=08-10", "2026->08-30", "2024->26", "2025->26")) + f" | {q['gross']:.3f} | {q['w_king']:.3f} | {q['w_fund']:.3f} | {q['turn']:.5f} |")
    for cal in ("log", "prod"):
        P(f"\n#### Deltas (king − pinned) — caliber **{cal}**; paired anchors; UTC-day-block bootstrap 2000×, seed 20260905; cell = Δ [CI95] P(Δ>0)")
        P("\n| arm | seed | king | 2024 | 2025 | 2026≤08-10 | 2026→08-30 | **2024→26** | 2025→26 | 2024→26≤cut | 2025→26≤cut | ΔSharpe 24on/25on | turnover pin→king (Δ%) | Δ mean w_king | maxDD pin/king (24on) |")
        P("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
        for arm in ("Lfix", "Ldyn", "Cdyn"):
            for seed in ("s42", "s2027"):
                for k in kings:
                    if k == "pinned": continue
                    d = G["deltas"].get(f"{cal}/{arm}/{seed}/{k}-pinned")
                    if not d: continue
                    W = d["windows"]; f = lambda w: f"{W[w]['mean']:+.3f} [{W[w]['lo']:+.3f},{W[w]['hi']:+.3f}] {W[w]['P>0']:.2f}"
                    P(f"| {arm} | {seed} | {k} | " + " | ".join(f(w) for w in ("2024", "2025", "2026<=08-10", "2026->08-30")) + f" | **{f('2024->26')}** | {f('2025->26')} | {f('2024->26<=cut')} | {f('2025->26<=cut')} | {d['dSharpe']['2024->26']:+.2f}/{d['dSharpe']['2025->26']:+.2f} | {d['turn_pinned']:.5f}→{d['turn_king']:.5f} ({d['dturn_pct']:+.1f}%) | {d['dw_king']:+.3f} | {d['maxDD_pinned']:.0f}/{d['maxDD_king']:.0f} |")
    sf = G["sigma_fund"]
    P(f"\n#### σ_fund terciles of Δ (2024→26). Definition: {sf['definition']}. Cuts {sf['cuts_bps'][0]:.2f} / {sf['cuts_bps'][1]:.2f} bps; n per tercile {sf['n']}; mean σ_fund per tercile {sf['mean_sigma_by_tercile']}")
    P("\n| caliber | arm | seed | king | low σ_fund: Δ [CI95] P (pinned→king) | mid | high |")
    P("|---|---|---|---|---|---|---|")
    for cal in ("log", "prod"):
        for arm in ("Lfix", "Ldyn", "Cdyn"):
            for seed in ("s42", "s2027"):
                for k in kings:
                    r = sf.get(f"{cal}/{arm}/{seed}/{k}-pinned")
                    if not r: continue
                    P(f"| {cal} | {arm} | {seed} | {k} | " + " | ".join(f"{r[t]['mean']:+.3f} [{r[t]['lo']:+.3f},{r[t]['hi']:+.3f}] P{r[t]['P>0']:.2f} ({r[t]['pinned_mean']:+.3f}→{r[t]['king_mean']:+.3f}, n{r[t]['n']})" for t in ("low", "mid", "high")) + " |")
    P("\n### Frozen decision")
    for k, d in G["decision"].items():
        P(f"\n**{k}** ({d['role']}): **{d['verdict']}**")
        if isinstance(d["checks"], dict):
            for cal, c in d["checks"].items():
                if not isinstance(c, dict): continue
                P(f"- {cal}: L-fix 2024→26 Δ {c.get('Lfix_2024->26_mean')} CI {c.get('Lfix_2024->26_CI')} lower>0={c.get('Lfix_2024->26_CI_lower>0')}; 2025→26 Δ {c.get('Lfix_2025->26_mean')} ≥0={c.get('Lfix_2025->26_delta>=0')}; yearly Δ {c.get('yearly')} worst {c.get('worst_year_delta')} ≥−0.05={c.get('worst_year_delta>=-0.05')}; Δturn {c.get('dturn_pct')}% ≤15={c.get('turn_increase<=15%')}; L-dyn s42/s2027 Δ {c.get('Ldyn_deltas')} both≥0={c.get('Ldyn_both_seeds_nonneg')}; REJECT flags: CI upper<0={c.get('REJECT_CI_upper<0')}, turn>25%={c.get('REJECT_turn>25%')}")

# ── receipts ──
P("\n### Receipts (verbatim log lines)")
for lg, pat in (("logs/setup_dev.log", r"^(\w{64}|43c43|325c326|---)"), ("dev/logs/eq_livefix_pinned_callog.log", r"^(CONFIG|SLOW override|F10 OOS|MEMBERS_TOPN|NOTE|RECEIPT_EX d30|DONE)"), ("logs/check_pinned_equiv.log", r".")):
    p = f"{ROOT}/{lg}"
    if os.path.exists(p):
        P(f"\n`{lg}`:\n```")
        for line in open(p):
            if re.search(pat, line): P(line.rstrip()[:420])
        P("```")
P("\n### Commands (verbatim, `logs/commands.txt`)\n```")
for line in open(f"{ROOT}/logs/commands.txt"): P(line.rstrip())
P("```")
print("\n".join(out))
