# VOID — v1 of the pod devices, kept for the audit trail, do not cite

`pod_causal_regime_r12.py` (sha 7eb31945…) and `pod_halves_r12.py` (sha 821c59cc…) took the member
set from the meta's `members[i]`. The pinned artifact has `MEMBERS_TOPN=829`, and w10_sleeve.py
L31-37 REBUILDS the member set each anchor from the qvk ranking, so the book holds names that are
not in `members[i]`. `pod_halves_r12.py`'s own parity assertion refused to produce output
(`PARITY FAILED 35.3675 / 0.3480`), which is how the defect was found.

Replaced by `pod_causal_regime_r12_v2.py` (parity: price maxabs 8.09e-6 bps, carry 1.55e-7 bps over
10039/10039 anchors) and `pod_halves_ex_r12.py` (8.61e-6 / 1.55e-7).
Every number in RESULT_r12_regime_table_2026-09-12.md comes from the v2 devices.
