#!/usr/bin/env python3
"""bt_funding_overlap.py — funding ledger for the main tables past the P2 ledger's end: OVERLAP PROOF first, then an explicit splice.

Inputs (pinned): P2 ledger_full.npz (bea6f575; per-symbol CSR off / ft / rate / src / zip_iv; last settlement 2026-09-01T02:00Z) — the ledger every
run so far used; stream D's funding_ledger.npz (74b69e63; flat sym / ts / ts_ms / rate / iv / iv_src / … over 2026-08-21T00Z → 09-19T00Z,
docs/RESULT_data_axis_0919_2026-09-19.md §4).
OVERLAP = every settlement with time in [stream D window start, P2 last settlement] = [2026-08-21T00:00:00Z, 2026-09-01T02:00:00Z].
Proved (each a named check; the proof is EXACT only if all hold):
  O1 settlements: the set of (symbol, second) keys is identical in both ledgers (lists of keys in only one, by symbol);
  O2 rates: bitwise equal on every common key (count and max |Δ| otherwise);
  O3 intervals: stream D's interval (iv, hours) vs P2's archive interval column zip_iv where that is finite, and vs P2's own gap to the previous
     settlement of the same symbol (hours; the previous settlement may precede the window); mismatches listed by source. The simulator does not
     read intervals (funding = −q·P·rate at each settlement), so O3 is reported and gates only the proof label, not the splice.
  also reported: stream D rows flagged after_last_trade inside the overlap, and whether P2 has them.
SPLICE (written ONLY if O1 and O2 hold): P2 rows with time ≤ CUT, stream D rows with time > CUT, CUT = the P2 last settlement; P2's CSR layout
(off / ft / rate / src / zip_iv / symbols) so bt_hist_sim31.HistFunding reads it unchanged; src 4 = stream D. The receipt states the cut, the
counts from each side and the proof result. If O1 or O2 fails: no splice, the differences are the output.
usage: env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B bt_funding_overlap.py PATH,HOME,LC_CTYPE <out_dir>
"""
import os, sys, json, time, hashlib, collections
WL = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else set()
assert WL, "env whitelist (argv[1]) must be non-empty"
extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
import numpy as np

T0 = time.time(); OUT = sys.argv[2]; os.makedirs(OUT, exist_ok=True)
P2 = ("/workspace/uplift_r2_2026-09-13/P2/work/ledger_full.npz", "bea6f5752772d54e659a4da5571ca41945a27d1b2316ec0ae52f387074f795ad")
SD = ("/workspace/axis_0919/funding/funding_ledger.npz", "74b69e635efbf3556fe706520fda9d5a1b5cda86dda9d04a844ba5d617a3a09d")
SYMS_SHA = "381b7f01eedcf31b6d6a94116a32855b545bf584b26f3000aa9545c81068c19a"


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def iso(t): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(t)))


rec = dict(device="bt_funding_overlap.py", self_sha256=sha(os.path.abspath(__file__)), argv=sys.argv, numpy=np.__version__, python=sys.version.split()[0],
           utc_start=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), inputs={}, checks=[])
FAILS = []
def check(name, ok, detail=None, gate=True):
    rec["checks"].append(dict(check=name, ok=bool(ok), gate=gate, detail=detail)); print(("OK   " if ok else "FAIL ") + name, json.dumps(detail, default=str)[:300] if detail is not None else "", flush=True)
    if not ok and gate: FAILS.append(name)


for nm, (p, s) in (("p2_ledger", P2), ("stream_d_ledger", SD)):
    got = sha(p); rec["inputs"][nm] = dict(path=p, sha256=got); check(f"input_sha.{nm}", got == s)
L = np.load(P2[0], allow_pickle=True); D = np.load(SD[0], allow_pickle=True)
SY = [str(s) for s in L["symbols"]]
check("symbols.same_829_axis", SY == [str(s) for s in D["symbols"]] and hashlib.sha256("\n".join(SY).encode()).hexdigest() == SYMS_SHA)
if FAILS:
    json.dump(rec, open(f"{OUT}/BT_FUNDING_OVERLAP.json", "w"), indent=1); print("BT_FUNDING_OVERLAP VERDICT=REFUSED"); sys.exit(3)
off = L["off"].astype(np.int64); ft = L["ft"].astype(np.int64); rate = L["rate"].astype(np.float64); src = L["src"]; ziv = L["zip_iv"].astype(np.float64)
jj = np.repeat(np.arange(len(SY)), np.diff(off))
dsym = D["sym"].astype(np.int64); dts = D["ts"].astype(np.int64); drate = D["rate"].astype(np.float64); div = D["iv"].astype(np.float64); dsrc = D["iv_src"]
W0 = int(D["window"][0]); CUT = int(ft.max())
check("ts_is_floor_of_ts_ms", bool(np.all(dts == D["ts_ms"].astype(np.int64) // 1000)))
rec["overlap"] = dict(start=iso(W0), end=iso(CUT), rule="settlement time in [stream D window start, P2 last settlement]")
mp = (ft >= W0) & (ft <= CUT); md = (dts >= W0) & (dts <= CUT)
kp = {(int(j), int(t)): i for i, (j, t) in enumerate(zip(jj[mp], ft[mp]))}; ip = np.nonzero(mp)[0]
kd = {(int(j), int(t)): i for i, (j, t) in enumerate(zip(dsym[md], dts[md]))}; idd = np.nonzero(md)[0]
dup_p = int(mp.sum()) - len(kp); dup_d = int(md.sum()) - len(kd)
only_p = sorted(set(kp) - set(kd)); only_d = sorted(set(kd) - set(kp)); common = sorted(set(kp) & set(kd))
def by_sym(keys): c = collections.Counter(SY[j] for j, _ in keys); return dict(c.most_common(30))
check("O1.settlement_keys_identical", not only_p and not only_d and dup_p == 0 and dup_d == 0,
      dict(p2=len(kp), stream_d=len(kd), common=len(common), only_p2=len(only_p), only_stream_d=len(only_d), dup_p2=dup_p, dup_stream_d=dup_d,
           only_p2_by_symbol=by_sym(only_p), only_stream_d_by_symbol=by_sym(only_d), only_p2_first=[(SY[j], iso(t)) for j, t in only_p[:10]],
           only_stream_d_first=[(SY[j], iso(t)) for j, t in only_d[:10]]))
rp = np.array([rate[ip[kp[k]]] for k in common]); rd = np.array([drate[idd[kd[k]]] for k in common])
neq = rp != rd
check("O2.rates_bitwise_equal", not neq.any(), dict(compared=len(common), differ=int(neq.sum()), max_abs=float(np.abs(rp - rd).max()) if len(common) else 0.0,
      first=[(SY[common[i][0]], iso(common[i][1]), float(rp[i]), float(rd[i])) for i in np.nonzero(neq)[0][:10]]))
# O3 intervals (reported; the simulator does not read them)
zi = np.array([ziv[ip[kp[k]]] for k in common]); dv = np.array([div[idd[kd[k]]] for k in common])
fz = np.isfinite(zi); mz = fz & (zi != dv)
prev_gap = []
for j, t in common:
    a, b = off[j], off[j + 1]; pos = int(np.searchsorted(ft[a:b], t)); prev_gap.append((t - ft[a + pos - 1]) / 3600.0 if pos > 0 else np.nan)
pg = np.array(prev_gap); fg = np.isfinite(pg); mg = fg & (np.abs(pg - dv) > 1e-9)
src_names = [str(x) for x in D["iv_src_names"]]
check("O3.intervals_vs_P2_archive_column", not mz.any(), dict(compared=int(fz.sum()), differ=int(mz.sum()),
      first=[(SY[common[i][0]], iso(common[i][1]), float(zi[i]), float(dv[i]), src_names[int(D['iv_src'][idd[kd[common[i]]]])]) for i in np.nonzero(mz)[0][:10]]), gate=False)
check("O3.intervals_vs_P2_gap_to_previous_settlement", not mg.any(), dict(compared=int(fg.sum()), differ=int(mg.sum()),
      by_stream_d_iv_source=dict(collections.Counter(src_names[int(D['iv_src'][idd[kd[common[i]]]])] for i in np.nonzero(mg)[0])),
      first=[(SY[common[i][0]], iso(common[i][1]), float(pg[i]), float(dv[i]), src_names[int(D['iv_src'][idd[kd[common[i]]]])]) for i in np.nonzero(mg)[0][:12]]), gate=False)
alt = D["after_last_trade"][md]
rec["after_last_trade_in_overlap"] = dict(stream_d_rows=int(alt.sum()), of_which_in_p2=int(sum(1 for i in np.nonzero(alt)[0] if (int(dsym[idd[i]]), int(dts[idd[i]])) in kp)))
exact = not FAILS
intervals_exact = not mz.any() and not mg.any()
rec["proof"] = ("EXACT (settlements, rates" + (", intervals)" if intervals_exact else "); intervals differ as listed (not read by the simulator)")) if exact else "DIFFERS"
if exact:
    after = dts > CUT
    rows = collections.defaultdict(list)
    for j, t, r, z, s_ in zip(jj, ft, rate, ziv, src):
        if t <= CUT: rows[int(j)].append((int(t), float(r), int(s_), float(z)))
    for j, t, r, v in zip(dsym[after], dts[after], drate[after], div[after]): rows[int(j)].append((int(t), float(r), 4, float(v)))
    O = [0]; FT = []; RT = []; SR = []; ZI = []
    for j in range(len(SY)):
        rr = sorted(rows.get(j, []))
        assert all(rr[k][0] < rr[k + 1][0] for k in range(len(rr) - 1)), ("duplicate or unsorted settlement after splice", SY[j])
        FT += [x[0] for x in rr]; RT += [x[1] for x in rr]; SR += [x[2] for x in rr]; ZI += [x[3] for x in rr]; O.append(O[-1] + len(rr))
    outp = f"{OUT}/ledger_spliced_p2_to_{time.strftime('%Y%m%dT%H%M', time.gmtime(CUT))}_streamD_after.npz"
    np.savez(outp + ".tmp.npz", off=np.array(O, np.int64), ft=np.array(FT, np.int64), rate=np.array(RT, np.float64), src=np.array(SR, np.int8),
             zip_iv=np.array(ZI, np.float32), symbols=np.array(SY), cut=np.array(CUT, np.int64))
    os.replace(outp + ".tmp.npz", outp)
    Z2 = np.load(outp)
    pre_ok = all(np.array_equal(Z2["ft"][Z2["off"][j]:Z2["off"][j + 1]][Z2["ft"][Z2["off"][j]:Z2["off"][j + 1]] <= CUT], ft[off[j]:off[j + 1]][ft[off[j]:off[j + 1]] <= CUT])
                 and np.array_equal(Z2["rate"][Z2["off"][j]:Z2["off"][j + 1]][Z2["ft"][Z2["off"][j]:Z2["off"][j + 1]] <= CUT], rate[off[j]:off[j + 1]][ft[off[j]:off[j + 1]] <= CUT])
                 for j in range(len(SY)))
    check("splice.p2_part_bitwise_equal_to_p2_up_to_cut", pre_ok)
    rec["splice"] = dict(path=outp, sha256=sha(outp), cut=iso(CUT), rows_from_p2=int((ft <= CUT).sum()), rows_from_stream_d=int(after.sum()),
                         last_settlement=iso(max(FT)), rule="P2 rows with time <= CUT, stream D rows with time > CUT; src 4 = stream D")
rec["VERDICT"] = "PASS" if not FAILS else "DIFFERS"
rec["runtime_s"] = round(time.time() - T0, 1)
json.dump(rec, open(f"{OUT}/BT_FUNDING_OVERLAP.json", "w"), indent=1, default=str)
print("BT_FUNDING_OVERLAP VERDICT=%s proof=%s" % (rec["VERDICT"], rec["proof"]), flush=True)
sys.exit(0 if not FAILS else 1)
