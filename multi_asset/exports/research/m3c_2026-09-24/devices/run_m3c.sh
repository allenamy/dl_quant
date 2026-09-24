#!/bin/sh
# M3c — docs/AMENDMENT_3_m3_beta_overlay_2026-09-24.md §2-1 (80c6c3e4b) / AMENDMENT_2 §3-2 (4530892bc): M3b hook + combined leverage 2.5 on the
# NC s42 targets (s2027 side report). VERBATIM commands as executed on pod2 2026-09-24 (CPU only). Run root R = /root/m3c_2026-09-24 (container
# overlay): /dev/shm is closed to M3c (lead), /workspace is at its quota. NC targets, news2's configs and base paths are only READ.
# Devices copied from the Mac (multi_asset/exports/research/m3c_2026-09-24/devices) with scp; M3b's hook (873769b9) from the M3b devices dir.
set -e
R=/root/m3c_2026-09-24; P=/workspace/venv/bin/python; N2=/dev/shm/news2_2026-09-23
C42=$N2/configs/RUN_CONFIG_NEWS2_s42X_2026-09-23.json; C27=$N2/configs/RUN_CONFIG_NEWS2_s2027X_2026-09-23.json
B42=$N2/runs/NEWS2_s42X_scaled_rule_raw_UAFE; B27=$N2/runs/NEWS2_s2027X_scaled_rule_raw_UAFE
