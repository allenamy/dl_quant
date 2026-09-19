DRYRUN of the A0 pipeline (2026-09-19 ~13:4xZ, while waiting for object-B A0 targets). NOT object-B numbers.
Targets = fixture TARGETS_FIX_full.npz written by bt_objb_adapter_test.py from stream R's S2 books (p2_s2_lib.books); window 2024-12-28T00Z + 48 anchors;
full-recipe start set to 2025-01-02T00Z for the fixture (the first dry-run attempt used 2025-01-05, after the last smoke anchor, and main_a0 failed with an
index-dtype error; bt_tables.py now refuses an empty FULL_RECIPE window with a named message). Results of the integration check:
  - launcher (config from the main-table template, 5 A0-shaped runs x 32 seeds, max 4 workers): BT_LAUNCH VERDICT=PASS
  - the object-B-sourced 'scaled' run equals the S2-sourced P2-CMB raw run path file by path file (32 seeds, every array bitwise)
  - main_a0 + renderer run end to end; step ③ on identical targets is exactly 0 (point, all bootstrap draws, all fill paths); telescoping 0.
