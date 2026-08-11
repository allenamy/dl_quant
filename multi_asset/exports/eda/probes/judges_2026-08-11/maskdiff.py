"""WHERE do the three masks actually differ? A boolean question, answered without a model.

  CL arm   = member & CL & isfinite(Y)   (predict_scores_wide / frozen scores)
  dense arm= member      & isfinite(Y)   (research densify, d.CL = member)
  live arm = member                      (signal_loop.infer, no future-Y gate)
"""
import sys
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
import numpy as np
from multi_asset.data.wide_panel_dataset import WidePanelData

MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
P = MA + "/exports/wide_dl_full.npz"
z = np.load(P, allow_pickle=True)
CL4, member = z["CL4"], z["MEMBER110"]
for H in (4, 24):
    d = WidePanelData(path=P, target_horizon=H,
                      aux_horizons=tuple(x for x in (1, 24) if x != H))
    Y, CL = d.Y, d.CL
    fin = np.isfinite(Y)
    A = np.sort(np.where((member & CL4).any(1))[0])          # the BOOK's anchor grid
    m_cl, m_de, m_lv = member[A] & CL[A] & fin[A], member[A] & fin[A], member[A]
    nat = (member & CL).any(1)[A]                            # rows the CL arm can score at all
    print("\n=== horizon %d ===  book anchors=%d, of which CL-arm-scorable=%d (%.1f%%)"
          % (H, len(A), nat.sum(), 100 * nat.mean()))
    print("  cells  CL=%d  dense=%d  live=%d" % (m_cl.sum(), m_de.sum(), m_lv.sum()))
    print("  dense vs live  : identical=%s   differing cells=%d"
          % (np.array_equal(m_de, m_lv), int((m_de != m_lv).sum())))
    print("  CL   vs live   : differing cells=%d" % int((m_cl != m_lv).sum()))
    # where dense != live, is it only the unrealised tail?
    dif = np.where((m_de != m_lv).any(1))[0]
    if len(dif):
        print("  dense!=live on %d rows; row index range %d..%d (panel T=%d) -> %s"
              % (len(dif), A[dif].min(), A[dif].max(), len(member),
                 "TAIL ONLY" if A[dif].min() > len(member) - 400 else "NOT tail-only"))
    else:
        print("  dense == live on EVERY book anchor  ⇒ the research densify IS production's mask here")
