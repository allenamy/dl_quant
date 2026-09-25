#!/usr/bin/env python3
"""dlarch_train_f10.py — arms T0 and T3 for docs/PREREG_dlarch_T3_leg_gate_2026-09-25.md (ba54ec9f8).

DERIVED FROM news2_train_f10.py (sha asserted at run time). The recipe -- 171 columns, soft rank, cost
term, ES tail, fold list, embargo 60, TRAIN_FRAC .85, stride 48, span 120, burn 24, fixed epoch 7, tau
anneal, AdamW/cosine, per-fold mu/sd from the 1/21 subsample -- is UNCHANGED. The diff is archived.

  T0  the common baseline (lead 2026-09-24): mask WL the way production does before it reaches the
      utility -- w=[WL0,0,WL2], w/=w.sum() (combo_target.py L30). Nothing else changes. Because WL[1]
      (rev24) is zeroed, the z24 term of the utility vanishes identically, so T0's `r` IS production's
      pre-clamp zfc.
  T3  on top of T0, under lead's ruling (a): replace the self-made weight map (news2_train_f10.py
      L35-L36: de-mean -> L1 -> cap*tanh, then an external EMA) with the rn8 funding clamp
      (combo_target.py L33-34) followed by the PRODUCTION chain (combo_stage.py L78-L101) in its
      differentiable form, which does sel-mask / de-mean-on-sel / L1 / clip-cap / renorm / EMA(alpha=0.1)
      / dead band / exit mask itself. G3 (receipt G3_CHAIN_PARITY.json) already proved that
      differentiable chain reproduces the archived production book bit-for-bit at s=0.

G6/G6b: T3 adds NO parameters; `Net.a` (the learnable EMA rate) is RETAINED so the parameter count is
identical, but T3 does not use it -- so it is a DEAD parameter in T3 and alive in T0. That asymmetry is
named, and asserted: after every backward pass in T3, a.grad must be None or exactly 0, and a's value at
the end of the fold must equal its initial value.

READ-ONLY inputs under /dev/shm; ALL outputs under /workspace. No writes to /dev/shm, none to live trees.

usage: env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B dlarch_train_f10.py \
         --env-whitelist PATH,HOME,LC_CTYPE --arm T0|T3 --seed N [--clamp-mode clamp|tanh] [--folds ...]
"""
import os
os.environ['OPENBLAS_NUM_THREADS'] = '2'; os.environ['OMP_NUM_THREADS'] = '2'
import pathlib, json, time, calendar, argparse, collections, hashlib, sys
import numpy as np
import torch
from torch import nn

W = pathlib.Path('/dev/shm/news2_2026-09-23')                      # READ-ONLY -- DATA inputs only, see VENDOR
# CODE comes from my own persistent tree, not from news2's volatile /dev/shm (lead ruling 2026-09-25).
# news2 froze that tree and verified 5/5 shas, but a freeze is a promise about intent, not a property of
# the filesystem -- they said themselves they nearly cleared it under their own "free it when the run is
# done" rule, because the dependency was invisible to them. Vendored by dlarch_vendor_news2.py with a
# read-back sha comparison; manifest receipts/VENDOR_NEWS2_20260923.json.
# The BULK data (work/NEWS_FEATURES.npz 2.96 GB, work/legs.npz, receipts/P2B_FEATURES.json,
# receipts/P3_LEGS.json) still comes from W: 2.96 GB does not fit my /workspace quota. Those four ARE
# pinned -- they sit in `inputs`, asserted per fold, with NEWT_SHA and two receipt cross-checks on top --
# so a changed or missing W fails LOUDLY and cannot silently train on other data. Residual exposure is
# AVAILABILITY (cost = a re-run), not correctness.
# I do not claim "everything read is pinned" as a blanket: until 2026-09-25 that was FALSE for
# inputs/bundle_config.json and receipts/P1_members_2025H2on.npz, read at the T3 branch below and
# present in no pinned list at all. They are vendored and asserted now (BUNDLE_CFG_SHA / P1_MEMBERS_SHA).
VENDOR = pathlib.Path(os.path.dirname(os.path.abspath(__file__))) / 'vendor_news2_20260923'
OUT_ROOT = pathlib.Path('/workspace/dlarch_2026-09-24/T3')         # ALL writes land here
REF = VENDOR / 'devices/news2_train_f10.py'
REF_SHA = '66bc7c3e69af7aab7062b562674fb3bbe272fd9a28fc3ea9639143f4549420db'  # news2_train_f10.py, asserted in main()
NEWT = pathlib.Path('/workspace/codex_research/QNT-2026-0907/combo_20260923/corrected_combo_v1d/data/dlw_targets.npz')
NEWT_SHA = 'ca479fccd3d3245e9438a8c82ba7b4a1950ab6e06607f28b25923c4526924d62'
# LITERAL pin for legs.npz (fresh 2026-09-25 spotted the gap this closes). The existing check is
# `json.load(P3_LEGS.json)['sha256'] == sha(legs.npz)` -- the receipt's self-reported output sha against
# the file. That catches an edited pair, but NOT a whole-tree mix-up: `news_2026-09-23/` differs from
# `news2_2026-09-23/` by ONE CHARACTER, and over there the receipt and the legs file are a mutually
# CONSISTENT pair, so a self-consistency check passes while the data is the polluted one (fresh's RN8
# census: that tree's RN8 disagrees with the archive, TLMUSDT even flips sign). A literal expected value
# is the only form that notices. NOT DEPLOYED to the in-flight T3 campaign: changing the trainer
# mid-campaign would train one family under two code versions, which is the class that voided 8 T0 folds
# on 2026-09-25. Takes effect from the next campaign, together with the R25-08 parameter hash.
LEGS_SHA = '9ee5886f37d1727c306d0fb692d2cad1e6400ae13f19d5cd4e280dc59f208f65'
MASK_PATH = '/workspace/axis_0919/x0918r/masks/member_mask_tradable_AND_live_W24H_cachegrid.npz'
# T3-only reads that were previously pinned NOWHERE: they were read straight off /dev/shm and did not
# appear in `inputs`, so a change to either would have been SILENT. Vendored and asserted at the use site.
# The pinned list and the read list are different lists; only comparing them shows the gap.
BUNDLE_CFG = VENDOR / 'inputs/bundle_config.json'
BUNDLE_CFG_SHA = '3a8422f377519cac77b0c42305d2ba40a4b7a42a830f0542bda844f66647c94e'
P1_MEMBERS = VENDOR / 'receipts/P1_members_2025H2on.npz'
P1_MEMBERS_SHA = '2323623fda9333710f5834911ab629377ab8c12b056f40ccfc9f7033c0c1f6f1'


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(16 << 20), b''): h.update(b)
    return h.hexdigest()


def log(*x): print(time.strftime('%H:%M:%S', time.gmtime()), *x, flush=True)


sys.path.insert(0, str(VENDOR / 'devices'))   # CODE from my persistent tree, not news2's /dev/shm
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from f10_observability import span_admissible, measured_dot          # noqa: E402
from dlarch_chain_torch import chain_torch                           # noqa: E402
import dlarch_safe_io as sio                                         # noqa: E402
sio.install_guards()   # E-0925-A: every artifact sha must come from a verified write, not a re-read


class Net(nn.Module):                                                # verbatim from news2_train_f10.py
    def __init__(self):
        super().__init__(); self.f = nn.Sequential(nn.Linear(171, 256), nn.GELU(), nn.Dropout(.1), nn.Linear(256, 256), nn.GELU(), nn.Dropout(.1), nn.Linear(256, 1)); self.a = nn.Parameter(torch.tensor(-2.303))
        nn.init.normal_(self.f[-1].weight, 0, .001); nn.init.zeros_(self.f[-1].bias)
    def alpha(self): return .02 + .88 * torch.sigmoid(self.a)


def soft_rank(score, tau, hard=False):
    """news2_train_f10.py L33-L34 verbatim (the rank half of utility())."""
    z = (score - score.mean()) / (score.std() + 1e-8); n = len(z)
    return torch.argsort(torch.argsort(z)).to(z.dtype) / max(n - 1, 1) - .5 if hard else (torch.sigmoid((z[:, None] - z[None, :]) / tau).sum(1) - .5) / max(n - 1, 1) - .5


def utility(score, z24, zfd, wl, tau, hard=False):                   # verbatim from news2_train_f10.py L32-36
    rank = soft_rank(score, tau, hard); n = len(score)
    r = wl[0] * rank + wl[1] * z24 + wl[2] * zfd; r = r - r.mean(); u = r / (r.abs().sum() + 1e-8); cap = 2.5 / n; u = cap * torch.tanh(u / cap)
    return u - u.mean()


def mask_wl(wl):
    """combo_target.py L30, in torch: w=[WL0,0,WL2]; w/=w.sum(); degenerate -> [.5,0,.5]."""
    s = wl[0] + wl[2]
    if float(s) > 1e-12:
        return torch.stack([wl[0] / s, torch.zeros_like(wl[0]), wl[2] / s])
    return torch.tensor([.5, 0., .5], dtype=wl.dtype, device=wl.device)


def fold_specs(a):                                                   # verbatim
    utc = lambda y, m=1: calendar.timegm((y, m, 1, 0, 0, 0))
    out = [('2023', utc(2023), utc(2024)), ('2024', utc(2024), utc(2025))]
    for y in (2025, 2026):
        for m in range(1, 13):
            start = utc(y, m); end = utc(y + 1) if m == 12 else utc(y, m + 1)
            if start <= a[-1]: out.append((f'{y}{m:02d}', start, end))
    return out


def merge_folds(out, a, symbols, inputs, sources, seed, arm):         # verbatim + arm in the receipt
    pred = np.full((len(a), len(symbols)), np.nan, np.float32); found = []; fold_artifacts = {}
    for tag, start, end in fold_specs(a):
        p = out / tag; rp = p / 'FOLD_RECEIPT.json'
        if not rp.exists(): continue
        rec = json.load(open(rp)); assert rec['inputs'] == inputs and rec['sources'] == sources and rec['seed'] == seed and rec['fold'] == tag and rec['arm'] == arm
        assert sha(p / 'scores.npz') == rec['score_sha256'] and sha(p / 'model.pt') == rec['model_sha256']
        z = np.load(p / 'scores.npz'); rows = np.flatnonzero((a >= start) & (a < end))
        assert np.array_equal(z['rows'], rows) and np.array_equal(z['E_ts'], a[rows]) and np.array_equal(z['symbols'], symbols)
        assert z['P'].shape == (len(rows), len(symbols)); pred[rows] = z['P']; found.append(tag)
        fold_artifacts.update({str(q): sha(q) for q in (rp, p / 'scores.npz', p / 'model.pt')})
    oof_sha = sio.save_npz(out / 'F10_OOF.npz', P=pred, E_ts=a, symbols=symbols)
    rr = {'status': 'ALL_DECLARED_FOLDS_SCORED_NOT_COMBO_CERTIFIED' if len(found) == len(fold_specs(a)) else 'PARTIAL_FOLDS',
          'arm': arm, 'seed': seed, 'fold_artifacts': fold_artifacts, 'folds': found,
          'expected_folds': [s[0] for s in fold_specs(a)], 'inputs': inputs, 'sources': sources,
          'pred_sha256': oof_sha}
    sio.write_json(out / 'TRAIN_RECEIPT.json', rr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--arm', choices=['T0', 'T3'], required=True)
    ap.add_argument('--seed', type=int, required=True)
    ap.add_argument('--clamp-mode', choices=['clamp', 'tanh'], default='clamp')
    ap.add_argument('--folds', default='all')
    ap.add_argument('--band-temp-div', type=float, default=10.0)      # s = band / this; prereg pins 10
    ap.add_argument('--env-whitelist', default='PATH,HOME,LC_CTYPE',
                    help='E-0826-D: enumerate the allowed environment. Anything outside it (beyond the two '
                         'thread caps this module sets at import) aborts the run, so a stray variable cannot '
                         'silently change a result. The reference news2_train_f10.py has no such check; this '
                         'is an addition, and it is the ONLY behavioural difference outside the two arms.')
    ap.add_argument('--no-mask', action='store_true',
                    help='G1 IDENTITY CONTROL ONLY: leave WL unmasked. With --arm T0 this must reproduce the '
                         'existing news2 F10 run BIT-FOR-BIT, proving T0 changed exactly one thing. Never a result arm.')
    ap.add_argument('--out-root', default=None,
                    help='Write artifacts under this root instead of OUT_ROOT. For PROBES ONLY: a probe that '
                         'has to retrain an already-produced fold must not delete and rebuild the delivered '
                         'one (delivered trees are read-only, and "restores correctly on failure" is not the '
                         'same as "cannot damage"). Absent => OUT_ROOT, so every real run is unaffected and '
                         'no existing command line changes meaning.')
    args = ap.parse_args()
    SELF_SET = {'OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS'}      # set by this module at import
    extra = sorted(set(os.environ) - set(args.env_whitelist.split(',')) - SELF_SET)
    assert not extra, f'env outside whitelist: {extra}'
    assert torch.cuda.is_available(), 'GPU required; refuse silently slow CPU fallback'
    assert sha(REF) == REF_SHA, f'the reference recipe changed: {sha(REF)[:16]} != {REF_SHA[:16]}'
    arm = args.arm if args.arm == 'T0' else f'T3_{args.clamp_mode}'
    if args.no_mask:
        assert args.arm == 'T0', '--no-mask is the G1 identity control for T0 only'
        arm = 'G1_T0_nomask'
    r = W / 'work'
    root = pathlib.Path(args.out_root) if args.out_root else OUT_ROOT
    out = root / arm / f'f10_s{args.seed}'; out.mkdir(parents=True, exist_ok=True)
    files = [r / 'NEWS_FEATURES.npz', NEWT, r / 'legs.npz', W / 'receipts/P2B_FEATURES.json', W / 'receipts/P3_LEGS.json']
    inputs = {str(p): sha(p) for p in files}
    sources = {str(p): sha(p) for p in (pathlib.Path(os.path.abspath(__file__)), REF,
                                       pathlib.Path(os.path.dirname(os.path.abspath(__file__))) / 'dlarch_chain_torch.py',
                                       VENDOR / 'devices/f10_observability.py', VENDOR / 'devices/nc_hist_features.py',
                                       VENDOR / 'devices/nc_legs.py', VENDOR / 'devices/nc_p2_build.py')}
    assert inputs[str(files[1])] == NEWT_SHA and json.load(open(files[3]))['sha256'] == inputs[str(files[0])] and json.load(open(files[4]))['sha256'] == inputs[str(files[2])]
    assert inputs[str(files[2])] == LEGS_SHA, (
        f"legs.npz is {inputs[str(files[2])][:16]}, expected {LEGS_SHA[:16]}. A self-consistent receipt+file "
        "pair from the WRONG tree would pass the assertion above; this literal pin is what catches it.")
    F = np.load(files[0]); T = np.load(files[1], allow_pickle=True); leg = np.load(files[2])
    a = F['anchors'].astype(np.int64)
    assert np.array_equal(T['symbols'], F['symbols']) and np.array_equal(leg['E_ts'], a) and np.array_equal(leg['symbols'], F['symbols'])
    ya = T['E_ts'].astype(np.int64); y = np.full((len(a), len(F['symbols'])), np.nan, np.float32)
    ix = np.searchsorted(ya, a); okk = (ix < len(ya)) & (ya[np.minimum(ix, len(ya) - 1)] == a); y[okk] = T['y4s'][ix[okk]]
    cnt = F['count']; off = F['off']; pa = np.repeat(np.arange(len(a)), cnt).astype(int); ps = F['m'].astype(int)
    members = [ps[off[i]:off[i + 1]] for i in range(len(a))]; st = np.searchsorted(pa, np.arange(len(a) + 1)); n, w = y.shape
    assert np.all(np.diff(a) == 14400)
    x = np.concatenate([F['X82'].astype(np.float32), F['X89']], 1).astype(np.float32); assert x.shape == (len(pa), 171) and np.isfinite(x).all()
    t = {'symbols': F['symbols']}
    dev = 'cuda'; XT = torch.from_numpy(x).to(dev); del x
    YVALID = torch.from_numpy(np.isfinite(y)).to(dev); YT = torch.from_numpy(np.where(np.isfinite(y), y, 0.)).to(dev)
    Z24 = torch.from_numpy(np.nan_to_num(leg['Z24'], nan=0.)).to(dev)
    ZFD = torch.from_numpy(np.nan_to_num(leg['ZFD'], nan=0.)).to(dev)
    WLraw = torch.from_numpy(leg['WL']).to(dev)
    ready = leg['ready']; requested = None if args.folds == 'all' else set(args.folds.split(','))
    cols = [torch.as_tensor(ps[st[i]:st[i + 1]], device=dev) for i in range(n)]
    # ---- masked seats (T0 change; T3 inherits it) + the WL census for G2 ----
    WL = WLraw if args.no_mask else torch.stack([mask_wl(WLraw[i]) for i in range(n)])
    # `legs.npz` WL is NaN on NOT-ready anchors (it is only filled where the producer made a record), and
    # training never touches those (run_span raises on not-ready). So the census AND G2's change count must
    # be taken over the READY, FINITE population only. Taking them over all n would (a) make every mean NaN
    # and (b) count NaN -> [.5,0,.5] as a "masking change", inflating G2 with anchors that are never used.
    # Caught by allow_nan=False refusing to serialise the receipt.
    fin = torch.isfinite(WLraw).all(1) & torch.from_numpy(ready.copy()).to(WLraw.device)
    nfin = int(fin.sum().item())
    assert nfin > 0, 'no ready anchor with a finite WL'
    wl_diff_rows = int((torch.abs(WL[fin] - WLraw[fin]).max(1).values > 0).sum().item())
    seat_census = {'population': 'ready anchors with finite WL', 'n_population': nfin, 'n_anchors_total': int(n),
                   'n_excluded_not_ready_or_nonfinite_WL': int(n - nfin),
                   'raw_WL_mean': [float(v) for v in WLraw[fin].mean(0)],
                   'masked_WL_mean': [float(v) for v in WL[fin].mean(0)],
                   'anchors_where_WL_changed': wl_diff_rows, 'masking_applied': not args.no_mask}
    log('seat census', json.dumps(seat_census))
    if args.no_mask:
        # G1: the control must be a TRUE no-op on the seats, otherwise it is not an identity control.
        assert wl_diff_rows == 0, 'G1 control is not a no-op: WL differs from raw'
    else:
        assert wl_diff_rows > 0, 'G2 SWITCH_NOT_WIRED: masking changed WL on zero anchors'
    # ---- T3-only fields: sel (from QV) and LIVE_MASK (book universe), both known 0/1 ----
    extra = {}
    if args.arm == 'T3':
        from book_universe import align as align_universe, PATH as UNIVERSE_PATH, SHA as UNIVERSE_SHA
        assert sha(UNIVERSE_PATH) == UNIVERSE_SHA
        assert sha(BUNDLE_CFG) == BUNDLE_CFG_SHA, ('bundle_config.json changed', sha(BUNDLE_CFG))
        cfg = json.load(open(BUNDLE_CFG))['params']
        mk = np.load(MASK_PATH); assert np.array_equal(mk['ts'].astype(np.int64), a)
        assert sha(P1_MEMBERS) == P1_MEMBERS_SHA, ('P1_members_2025H2on.npz changed', sha(P1_MEMBERS))
        crypto = np.load(P1_MEMBERS)['crypto']
        cand = mk['mask'] & crypto[None, :]
        universe = np.load(UNIVERSE_PATH)
        u_ts = universe['ts'].astype(np.int64)
        # CLAMP BOTH ENDS. `a <= u_ts[-1]` alone is wrong: the training axis starts 2022-01-01 and the
        # universe starts 2022-01-31, so 181 pre-universe anchors stayed in the slice and
        # book_universe.align raised 'universe missing anchor; no forward/backfill' -- T3's first ever run
        # died 23 s in. The worse half is the field below: `anchors_outside_universe` was computed from
        # that same one-sided mask, so it would have printed 1 while 181 anchors were in fact outside.
        # (I first wrote "0" here. MEASURED after the fix: outside=181 = before=180 + after=1, so the old
        # one-sided `a <= u_ts[-1]` did catch the single anchor above the end and reported 1. The
        # name/number mismatch is 1-vs-181, not 0-vs-181. I also predicted the split would be 181 before
        # and 0 after; it is 180/1. Correcting rather than rounding my own prediction to "right".)
        # The name said "outside", the number meant "above". Both ends are clamped and reported separately
        # now, so the quantity matches its name.
        inuni = (a >= u_ts[0]) & (a <= u_ts[-1])
        _missing = int((~np.isin(a[inuni], u_ts)).sum())
        assert _missing == 0, (f'{_missing} anchors inside the universe window are absent from its grid: '
                               'an INTERIOR gap, which clamping cannot fix and which would otherwise '
                               'surface as book_universe.align\'s generic ValueError with no count')
        legal = np.zeros((n, w), bool)
        legal[inuni] = align_universe(a[inuni], t['symbols'], universe) & cand[inuni]
        QVn = leg['QV']
        sel_list = [np.isfinite(QVn[i][members[i]]) & (QVn[i][members[i]] >= cfg['qv4h_min']) for i in range(n)]
        sel_ok = np.array([s.sum() >= cfg['sel_min'] for s in sel_list])
        extra = {'cfg': cfg, 'legal': torch.from_numpy(legal).to(dev),
                 'sel': [torch.from_numpy(s).to(dev) for s in sel_list], 'sel_ok': sel_ok,
                 's_temp': cfg['band'] / args.band_temp_div,
                 'anchors_outside_universe': int((~inuni).sum()),
                 'anchors_before_universe_start': int((a < u_ts[0]).sum()),
                 'anchors_after_universe_end': int((a > u_ts[-1]).sum()),
                 'anchors_sel_below_min': int((~sel_ok).sum())}
        inputs[MASK_PATH] = sha(MASK_PATH); inputs[UNIVERSE_PATH] = UNIVERSE_SHA
        log('T3 fields', json.dumps({k: extra[k] for k in (
            'anchors_outside_universe', 'anchors_before_universe_start', 'anchors_after_universe_end',
            'anchors_sel_below_min', 's_temp')}))

    RN8T = torch.from_numpy(leg['RN8'].astype(np.float64)).to(dev).float() if args.arm == 'T3' else None

    def run_span(model, idx, mu, sd, tau, hard, burn):
        held = torch.zeros(w, device=dev); alpha = model.alpha(); nets = []; unobservable = []
        n_skip = 0; band_open = 0; band_book = 0
        for k, i in enumerate(idx):
            if not ready[i]: raise ValueError('missing causal leg in span')
            xx = torch.clamp((XT[st[i]:st[i + 1]] - mu) / sd, -5, 5); score = model.f(xx).squeeze(-1)
            if args.arm == 'T0':
                u = utility(score, Z24[i, cols[i]], ZFD[i, cols[i]], WL[i], tau, hard)
                target = torch.zeros(w, device=dev).scatter(0, cols[i], u); new = (1 - alpha) * held + alpha * target
            else:
                if not extra['sel_ok'][i]: n_skip += 1; continue          # producer would not have written a book
                zf = soft_rank(score, tau, hard)
                rr_ = WL[i][0] * zf + WL[i][2] * ZFD[i, cols[i]]
                rn = RN8T[i, cols[i]]
                rr_ = torch.where((rr_ < 0) & torch.isfinite(rn) & (rn <= -.001), torch.zeros((), device=dev, dtype=rr_.dtype), rr_)
                cens = {}
                new = chain_torch(rr_, extra['sel'][i], held, cols[i], w, extra['legal'][i],
                                  extra['cfg']['cap_mult'], extra['cfg']['alpha'], extra['cfg']['band'],
                                  extra['s_temp'], args.clamp_mode, census=cens)
                band_open += cens.get('band_open_cells', 0); band_book += cens.get('book_cells', 0)
                if new is None: n_skip += 1; continue                    # degenerate signal: producer returns None
            unobservable.append(((new != 0) & ~YVALID[i]).any())
            net = 1e4 * (new * YT[i]).sum() - 3.52 * torch.sqrt((new - held) ** 2 + 1e-12).sum()
            if k >= burn: nets.append(net)
            held = new
        if unobservable and bool(torch.stack(unobservable).any().item()): raise ValueError('unknown held return: loss refused')
        if not nets: raise ValueError('span produced no scored anchors')
        return torch.stack(nets), n_skip, (band_open, band_book)

    allpred = np.full((n, w), np.nan, np.float32); reports = []
    nparam = sum(p.numel() for p in Net().parameters())
    for tag, start, end in fold_specs(a):
        if requested is not None and tag not in requested: continue
        target_dir = out / tag; result = target_dir / 'FOLD_RECEIPT.json'
        if result.exists():
            old = json.load(open(result)); assert old['inputs'] == inputs and old['sources'] == sources and old['seed'] == args.seed and old['arm'] == arm, 'resume identity changed'
            assert sha(target_dir / 'scores.npz') == old['score_sha256'] and sha(target_dir / 'model.pt') == old['model_sha256']
            z = np.load(target_dir / 'scores.npz'); allpred[z['rows']] = z['P']; reports.append(old); continue
        target_dir.mkdir(exist_ok=False, parents=True)
        te = np.flatnonzero((a >= start) & (a < end)); first = int(te[0]); cutoff = int(a[first]) - 60 * 14400
        tr = np.flatnonzero((a + 14400 <= cutoff) & ready & (np.diff(st) >= 50)); assert len(tr) >= 300
        cut = int(len(tr) * .85); tr1 = tr[:cut]; assert a[tr1[-1]] + 14400 <= cutoff
        windows = []; rejected = collections.Counter()
        for s in range(int(tr1[0]) + 24, int(tr1[-1]) - 96, 48):
            span = np.arange(s - 24, s + 96); ok, why = span_admissible(members, y, span, ready)
            if ok: windows.append(span)
            else: rejected[why['reason']] += 1
        admission = {'fold': tag, 'accepted_windows': len(windows), 'rejected': dict(rejected), 'train_anchors': len(tr1),
                     'max_train_label_end': int(a[tr1[-1]] + 14400), 'test_start': int(a[first]), 'cutoff': cutoff}
        sio.write_json(target_dir / 'ADMISSION.json', admission); log('F10 admission', arm, args.seed, admission)
        if len(windows) < 5: raise ValueError('fewer than 5 observable training windows')
        rowsel = np.concatenate([np.arange(st[i], st[i + 1]) for i in tr1[::7]])[::3]
        xs = XT[torch.as_tensor(rowsel, device=dev)]; mu = xs.mean(0); sd = xs.std(0) + 1e-6; del xs
        torch.manual_seed(args.seed); np.random.seed(args.seed); model = Net().to(dev)
        a_init = float(model.a.detach())
        opt = torch.optim.AdamW(model.parameters(), lr=3e-4, weight_decay=1e-4)
        sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=15)
        started = time.monotonic(); curve = []; grad_census = []; skipped_total = 0
        for ep in range(8):
            model.train(); vals = []; t0 = time.monotonic(); tau = .5 - (.5 - .1) * ep / 14
            bo = bb = 0; a_grad_nonzero = 0
            for wi in np.random.permutation(len(windows)):
                nets, nsk, (o_, b_) = run_span(model, windows[wi], mu, sd, tau, False, 24); skipped_total += nsk; bo += o_; bb += b_
                es = torch.topk(-nets, max(1, int(np.ceil(.05 * len(nets))))).values.mean(); loss = -nets.mean() + .25 * es
                if not bool(torch.isfinite(loss)): raise ValueError('nonfinite F10 loss')
                opt.zero_grad(); loss.backward()
                if args.arm == 'T3' and model.a.grad is not None and float(model.a.grad.abs().sum()) != 0.0: a_grad_nonzero += 1
                nn.utils.clip_grad_norm_(model.parameters(), 1.); opt.step(); vals.append(float(loss.detach()))
            sched.step()
            rr = {'epoch_index': ep, 'train_loss': float(np.mean(vals)), 'alpha': float(model.alpha().detach()), 'seconds': time.monotonic() - t0}
            # G4 measures how much of the BOOK the dead band freezes -- not parameter-gradient sparsity.
            # For T0 there is no band, so the fraction is 1.0 BY CONSTRUCTION and is reported as such,
            # not computed from a quantity that cannot vary.
            g4 = {'epoch_index': ep, 'a_grad_nonzero_steps': a_grad_nonzero}
            if args.arm == 'T0':
                g4['band_open_frac_of_book'] = 1.0; g4['basis'] = 'no dead band in T0: 1.0 by construction'
            else:
                g4['band_open_frac_of_book'] = (bo / bb) if bb else None
                g4['band_open_cells'] = bo; g4['book_cells'] = bb; g4['basis'] = 'measured inside the differentiable chain'
            curve.append(rr); grad_census.append(g4)
            log('F10', arm, tag, args.seed, rr, 'g4_band_open', g4['band_open_frac_of_book'])
            sio.write_json(target_dir / 'PROGRESS.json', {'curve': curve, 'grad_census': grad_census})
        a_final = float(model.a.detach())
        if args.arm == 'T3':
            assert sum(g['a_grad_nonzero_steps'] for g in grad_census) == 0, 'G6b: a received a gradient in T3'
            assert a_final == a_init, f'G6b: a moved in T3 ({a_init} -> {a_final})'
        model.eval(); pred = np.full((len(te), w), np.nan, np.float32)
        with torch.no_grad():
            for k, i in enumerate(te):
                if st[i + 1] - st[i] < 50: continue
                xx = torch.clamp((XT[st[i]:st[i + 1]] - mu) / sd, -5, 5); pred[k, ps[st[i]:st[i + 1]]] = model.f(xx).squeeze(-1).cpu().numpy()
        model_sha = sio.save_torch(target_dir / 'model.pt', {'state_dict': model.state_dict(), 'mu': mu, 'sd': sd, 'input_dim': 171, 'fixed_epoch_index': 7})
        score_sha = sio.save_npz(target_dir / 'scores.npz', P=pred, rows=te, E_ts=a[te], symbols=t['symbols']); allpred[te] = pred
        rr = {'status': 'F10_OOF_SCORES_NOT_COMBO_PNL', 'arm': arm, 'clamp_mode': args.clamp_mode if args.arm == 'T3' else None,
              'seed': args.seed, 'rng_rule': 'constant seed per fold', 'fold': tag, 'inputs': inputs, 'sources': sources,
              'admission': admission, 'curve': curve, 'grad_census': grad_census, 'fixed_epoch_index': 7,
              'schedule_T_max': 15, 'updates_end_at_index': 7, 'test_anchors': len(te),
              'scored_pairs': int(np.isfinite(pred).sum()), 'score_label_missing_pairs': int((np.isfinite(pred) & ~np.isfinite(y[te])).sum()),
              'param_count': nparam, 'a_init': a_init, 'a_final': a_final, 'seat_census': seat_census,
              'anchors_skipped_in_spans': skipped_total, 't3_extra': {k: extra[k] for k in ('anchors_outside_universe', 'anchors_sel_below_min', 's_temp')} if args.arm == 'T3' else None,
              'score_sha256': score_sha, 'model_sha256': model_sha,
              'elapsed_seconds': time.monotonic() - started, 'gpu': torch.cuda.get_device_name(0)}
        for p, hsh in inputs.items(): assert sha(p) == hsh
        for p, hsh in sources.items(): assert sha(p) == hsh
        sio.write_json(result, rr); reports.append(rr); log('F10_FOLD_DONE', arm, tag, args.seed)
        merge_folds(out, a, t['symbols'], inputs, sources, args.seed, arm); del model, opt, sched; torch.cuda.empty_cache()
    merge_folds(out, a, t['symbols'], inputs, sources, args.seed, arm)
    print(f"DLARCH_TRAIN_DONE arm={arm} seed={args.seed} params={nparam} out={out} "
          f"oof_sha={sha(out / 'F10_OOF.npz')[:16]} receipt_sha={sha(out / 'TRAIN_RECEIPT.json')[:16]}", flush=True)


if __name__ == '__main__':
    main()
