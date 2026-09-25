Files-only installer (lead ruling 2026-09-25 "nc_install --files-only": nc_install_files.py, a sibling importing nc_install.py's helpers; packager
nc_package_files.py). Rehearsal on a copy of the machine layout (fixture = rsync of ~/wide_shadow minus venv / state/snap / logs + the sidecar plist,
APFS clones per cell), 2026-09-25 07:08Z:
  ~/wide_shadow/venv/bin/python -B test_nc_install_files.py ~/cc_tmp/nc_20260923/treeNC7 ~/cc_tmp/nc_20260923/files_install_rehearsal_20260925T0708Z
  → test rc=0 · TEST_NC_INSTALL_FILES PASS 15/15: F0 preflight green; F1 apply (dests == candidate; archive sources gone and archived sha == pre-move
    sha; state manifest diff []; producer loads); F5 rollback (every dest back to its pre-release sha, archive reversed, no state touched); RED: F2
    state dest refused, F3 one state utime during apply ⇒ FILES-ONLY VIOLATION, F4 changed archive source refused, F6 rollback without unarchive
    refused, F7 rehearsal flags on the real home refused. Package: 10 files, 4 archive moves (k1 three + com.hsy.sidecar.plist).
Work dir deleted after this receipt (disk budget).
