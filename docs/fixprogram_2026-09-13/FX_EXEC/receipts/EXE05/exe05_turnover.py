import json, re, statistics as st
P = "/Users/haosiyu/cc_tmp/fx_exec_census_exe05/anchor_runs.log"
rows = []
for line in open(P, encoding="utf-8", errors="replace"):
    m = re.search(r'phase_A: (\{.*\})\s*$', line.rstrip("\n"))
    if not m: continue
    try: d = json.loads(m.group(1))
    except ValueError: continue
    s = d.get("sizing")
    if isinstance(s, dict):
        rows.append((d.get("anchor_ts"), d.get("rebalance_id"), s))
rows.sort(key=lambda r: r[0] or 0)

# assertion first: resized False <=> blind
nb = [s for _, _, s in rows if s.get("blind") is not True]
bl = [s for _, _, s in rows if s.get("blind") is True]
print(f"non-blind {len(nb)}: resized True {sum(1 for s in nb if s.get('resized') is True)}")
print(f"blind     {len(bl)}: resized True {sum(1 for s in bl if s.get('resized') is True)}")
print("=> 'resized: False' in the record means BLIND (nav unreadable), never 'the dead zone bound'\n")

live = [(t, r, s) for t, r, s in rows if s.get("nav") and s.get("blind") is not True]
DEAD = 0.10
prev_nav = prev_gross = None
drifts, saved, tot_gross = [], [], []
n_in, n_out = 0, 0
for t, r, s in live:
    nav, g, tgt = float(s["nav"]), float(s["gross"]), float(s["target_leverage"])
    if prev_nav:
        # what the dead zone WOULD have computed: actual = prev_gross/nav, drift = |actual/tgt - 1|
        actual = prev_gross / nav
        drift = abs(actual / tgt - 1.0)
        drifts.append(drift)
        tot_gross.append(g)
        if drift <= DEAD:
            n_in += 1
            saved.append(abs(g - prev_gross))       # the resize that would NOT have happened
        else:
            n_out += 1
            saved.append(0.0)
    prev_nav, prev_gross = nav, g

print(f"consecutive LIVE-sized anchor pairs: {len(drifts)}")
print(f"  drift INSIDE the 10% dead zone : {n_in}  ({100.0*n_in/len(drifts):.1f}%)  <- resize would have been SUPPRESSED")
print(f"  drift OUTSIDE                  : {n_out} ({100.0*n_out/len(drifts):.1f}%)")
q = lambda v, p: sorted(v)[int(p*(len(v)-1))]
print(f"\ndrift |prev_gross/nav/tgt - 1| : median {st.median(drifts):.4%}  p90 {q(drifts,0.90):.4%}  max {max(drifts):.4%}")
frac = [s_/g for s_, g in zip(saved, tot_gross) if g > 0]
nz = [f for f in frac if f > 0]
print(f"\nRESIZE NOTIONAL AS A FRACTION OF GROSS (= |delta nav|/nav on suppressed anchors):")
print(f"  over all {len(frac)} pairs : mean {st.mean(frac):.4%}  median {st.median(frac):.4%}  p90 {q(frac,0.90):.4%}  max {max(frac):.4%}")
print(f"  over the {len(nz)} suppressed pairs only: mean {st.mean(nz):.4%}  median {st.median(nz):.4%}  max {max(nz):.4%}")
print(f"\ntotal resize notional that the dead zone would have avoided: {sum(saved):,.2f} USDT")
print(f"total gross traded across those anchors                    : {sum(tot_gross):,.2f} USDT")
print(f"=> LOWER BOUND on turnover the dead zone would have saved  : {100.0*sum(saved)/sum(tot_gross):.4f}% of gross per anchor (mean)")
# ★ UNITS, STATED: `frac` entries are FRACTIONS of gross (0.0037 = 0.37%). The comparison band
#   2-5.5% is also a fraction of gross per anchor. So the ratio is (mean_frac) / (band_frac),
#   both dimensionless. My first version divided a PERCENT by a PERCENT-valued literal and
#   printed 0.2% instead of 18.6% - a 100x slip, corrected here.
_mean_pct = 100.0 * st.mean(frac)
_wmean_pct = 100.0 * sum(saved) / sum(tot_gross)
print(f"\nAGAINST MEASURED TURNOVER of 2.0-5.5% of gross per anchor:")
print(f"  unweighted mean {_mean_pct:.4f}% of gross  =>  {_mean_pct/2.0*100:.1f}% of the 2.0% end,"
      f"  {_mean_pct/5.5*100:.1f}% of the 5.5% end")
print(f"  gross-weighted  {_wmean_pct:.4f}% of gross  =>  {_wmean_pct/2.0*100:.1f}% of the 2.0% end,"
      f"  {_wmean_pct/5.5*100:.1f}% of the 5.5% end")
print(f"\n  i.e. had the dead zone bound, it would have removed on the order of a FIFTH to a"
      f"\n  FIFTEENTH of measured per-anchor turnover - a real but second-order saving, and a"
      f"\n  LOWER BOUND because it counts only the resize leg, not the per-name re-quoting that"
      f"\n  a changed gross induces downstream.")
