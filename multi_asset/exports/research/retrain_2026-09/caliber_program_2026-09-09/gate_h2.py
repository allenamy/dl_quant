"""Gate H2: dlw_hf3 (holefix2, ch0 target) vs dlw_hf2 (holefix, ch0 target) may differ ONLY at anchors whose target window or
7-day trailing member window touches the two 2022 holes (02-26..03-01, 04-01..04-03). Report first/last changed anchor."""
import numpy as np, calendar, time, sys
def T(s): return time.strftime("%F %H:%MZ", time.gmtime(int(s)))
A = np.load("/workspace/dlw_hf2/data/dlw_targets.npz", allow_pickle=True); B = np.load("/workspace/dlw_hf3/data/dlw_targets.npz", allow_pickle=True)
ea, eb = A["E_ts"].astype(np.int64), B["E_ts"].astype(np.int64); print("axis identical:", ea.shape == eb.shape and bool((ea == eb).all()))
H = [(calendar.timegm((2022, 2, 26, 0, 0, 0)), calendar.timegm((2022, 3, 2, 0, 0, 0))), (calendar.timegm((2022, 4, 1, 0, 0, 0)), calendar.timegm((2022, 4, 4, 0, 0, 0)))]
def allowed(t): return any((t >= lo - 4 * 3600) and (t <= hi + 8 * 86400) for lo, hi in H)   # 7-day trailing member window + 1 anchor
ma, mb, ya, yb = A["members"], B["members"], A["y4s"], B["y4s"]; ch_m = []; ch_y = []; bad = []
for i in range(len(ea)):
    dm = not np.array_equal(np.asarray(ma[i]), np.asarray(mb[i])); a, b = ya[i], yb[i]
    dy = bool(((np.isfinite(a) ^ np.isfinite(b)) | (np.isfinite(a) & np.isfinite(b) & (np.abs(a.astype(np.float64) - b.astype(np.float64)) > 1e-6))).any())   # 1e-6: float64 cumsum-cancellation noise is not a change
    if dm: ch_m.append(ea[i])
    if dy: ch_y.append(ea[i])
    if (dm or dy) and not allowed(int(ea[i])): bad.append(ea[i])
print("members changed anchors %d (%s .. %s)" % (len(ch_m), T(min(ch_m)) if ch_m else "-", T(max(ch_m)) if ch_m else "-"))
print("y4s changed anchors %d (%s .. %s)" % (len(ch_y), T(min(ch_y)) if ch_y else "-", T(max(ch_y)) if ch_y else "-"))
print("changes OUTSIDE the two 2022 hole neighbourhoods: %d %s" % (len(bad), [T(x) for x in bad[:5]]))
print("GATE_H2 %s" % ("PASS" if not bad else "FAIL")); sys.exit(0 if not bad else 3)
