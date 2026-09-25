#!/bin/sh
# CROSS-LEVEL determinism check (lead 2026-09-25 step 1).
# The stored (T0, s42, 202506) scores.npz was produced SOLO (1 trainer). Re-run the SAME fold while the
# family driver is also training (2 concurrent) and require scores.npz bitwise identical.
# scores.npz is the right artifact: its file sha is stable run-to-run (verified 2d1d30ffc502 across two
# separate solo runs), whereas model.pt's file sha differs run-to-run even when its TENSORS are bitwise
# identical (torch.save writes a zip) -- so a model.pt file-sha test would fail spuriously.
# SAFETY: the fold is backed up first; the delivered OOF sha must be unchanged at the end, else restore.
set -u
W=/workspace/dlarch_2026-09-24
FOLD=$W/T3/T0/f10_s42/202506
K=$W/determinism_probe
REF_SCORE=2d1d30ffc502f225a8c9a5c557fa65123d0b1860e78a6ae065294a71058499a8
REF_OOF=de3f12028cd9c7c4238dab91d3172717566fa49996ce58a39feb54db91953dc3
mkdir -p "$K/ref_parent"
rm -rf "$K/ref_parent/202506"
cp -r "$FOLD" "$K/ref_parent/202506" || exit 9
log(){ echo "$(date -u +%H:%M:%SZ) $*" | tee -a "$K/crosslevel.log"; }
log "backed up $FOLD -> $K/ref_parent/202506"
log "concurrent trainers BEFORE (script-name pattern, not the buggy one): $(pgrep -fc 'dlarch_train_f10.py')"
nvidia-smi --query-compute-apps=pid,used_memory --format=csv,noheader | tee -a "$K/crosslevel.log"
rm -rf "$FOLD"
log "retraining 202506 at current load"
env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B "$W/dlarch_train_f10.py" \
    --arm T0 --seed 42 --folds 202506 --env-whitelist PATH,HOME,LC_CTYPE >> "$K/crosslevel_run.log" 2>&1
log "retrain rc=$?"
log "concurrent trainers AFTER: $(pgrep -fc 'dlarch_train_f10.py')"
NEW=$(sha256sum "$FOLD/scores.npz" 2>/dev/null | cut -d' ' -f1)
OOF=$(sha256sum $W/T3/T0/f10_s42/F10_OOF.npz 2>/dev/null | cut -d' ' -f1)
log "new scores.npz sha : $NEW"
log "ref scores.npz sha : $REF_SCORE"
log "scores MATCH       : $([ "$NEW" = "$REF_SCORE" ] && echo YES || echo NO)"
log "OOF sha now        : $OOF"
log "OOF UNCHANGED      : $([ "$OOF" = "$REF_OOF" ] && echo YES || echo NO)"
if [ "$NEW" != "$REF_SCORE" ] || [ "$OOF" != "$REF_OOF" ]; then
  log "MISMATCH -> restoring the backup and re-merging"
  rm -rf "$FOLD"; cp -r "$K/ref_parent/202506" "$FOLD"
  env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B "$W/dlarch_train_f10.py" \
      --arm T0 --seed 42 --folds 202506 --env-whitelist PATH,HOME,LC_CTYPE >> "$K/crosslevel_restore.log" 2>&1
  log "restore merge rc=$?  OOF now $(sha256sum $W/T3/T0/f10_s42/F10_OOF.npz | cut -d' ' -f1)"
fi
log "CROSSLEVEL_DONE"
