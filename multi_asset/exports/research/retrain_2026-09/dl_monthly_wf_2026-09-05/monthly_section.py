# ═══════════════ dl_monthly_wf (2026-09-05) · monthly causal walk-forward · replaces the yearly fold loop ═══════════════
# Governing text: docs/PREREG_deploy_rolling_king_2026-09-05.md §2 item 3 ("DL 月频因果走前评估").
# Everything ABOVE this banner is byte-identical to /workspace/pod_f10_train_ext.py (sha256 93cc2cdf…) up to, not including, its
# `for YV in (2023, 2024, 2025, 2026):` loop (file built by `head -n <loop line − 1>` + this section; receipt = trainer.diff).
# Only the fold definition changes:
#   test fold  = calendar month YM (first_te = first anchor of YM, last_te = last anchor of YM; 2026-08 runs to the data end 08-30 20Z)
#   train set  = anchors i < first_te − EMBM with ≥50 member rows (EMBM=60: existing fold convention; EMBM=1: K2 convention);
#                the 4h label window of anchor i is the 5m rows [E+1, E+48] ⇒ label end = E_i + 4h ⇒ CAUSALITY ASSERT per fold:
#                max(E_train) + 4h ≤ E[first_te] − EMBM·4h (printed).
#   validation = last 15% of the training anchors (verbatim rule); calibration (mu/sd), optimiser, cosine schedule, TBPTT windows,
#                τ anneal, best-epoch selection on the validation score and the test pass are verbatim.
#   per-fold RNG: torch.manual_seed(SEED + YM) AND np.random.seed(SEED + YM) (yearly recipe: torch SEED+YV, numpy sequential from the
#                process seed) so that every fold reproduces on its own after a restart. GPU kernels not forced deterministic (as in the recipe).
#   extra outputs (diagnostic, zero effect on training): raw scores mdl.f(x) for EVERY anchor ≥ first_te (IC-by-model-age curve),
#                the fold model state, a per-fold config json, wall-clock per fit. Writes ONLY under MWF_OUT.
MWF_OUT = os.environ["MWF_OUT"]; EMBM = int(os.environ["EMBARGO"]); assert EMBM in (60, 1), f"EMBARGO whitelist {{60,1}}: {EMBM}"
TAG = os.environ.get("MWF_TAG", f"mE{EMBM}"); FORCE = int(os.environ.get("FORCE", "0"))
# E-0826-D env whitelist: the production V2MAIN recipe (09-01 gate run), asserted on the EFFECTIVE values, not on strings
assert ARM == "V2MAIN" and V2 == 1 and SEED == 42 and COST == 3.52 and LDD == 0.25 and AFIX == 0 and LDC == 0.0 and CTXA == 0 and REC == 0 \
    and PLEON == 0 and EPOCHS == 15 and LR == 3e-4 and NCOL == 167 and EXTRA == "" and LPP == 0.0 and int(XT.shape[1]) == 171 \
    and DLW == "/workspace/dlw_ext" and OUT == "/workspace/f8_ext", "env whitelist (production V2MAIN recipe on ext data) violated"
_GATE_0901 = {"targets_sha256": "31d043e8f160a1d4475d5992a069c4b602419d78c7916f710d1e56ae8915caf9",
              "fea82_sha256": "9bc111a47cee54fc26193165258a83eb11f59df79bebcd69452532bb4c59678e",
              "fea89_sha256": "bebf2720315499707e54b53c26d889cbf6f2d2d3184a42455284636c0c5e4d67"}
for _k, _v in _GATE_0901.items():
    assert rep[_k] == _v, f"{_k} differs from the 09-01 gate run (f8_ext/results/f10_V2MAIN_s42.json): {rep[_k]} vs {_v}"
_BASE = "/workspace/pod_f10_train_ext.py"
rep.update({"embargo": EMBM, "tag": TAG, "base_trainer": _BASE, "base_sha256": sha(_BASE), "legs_sha256": sha(f"{OUT}/data/f10v2_legs.npz"),
            "torch": torch.__version__, "cuda": torch.version.cuda, "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu",
            "env_given": {k: os.environ.get(k) for k in ("ARM", "V2", "SEED", "COST", "LDD", "AFIX", "LDC", "CTXA", "REC", "PLE", "EPOCHS", "LR", "NCOL", "EXTRA", "LPP",
                                                          "F10_DLW", "F10_OUT", "MWF_OUT", "EMBARGO", "MWF_TAG", "MONTHS", "FORCE")},
            "fold_rule": {"test": "calendar month YM", "train": "i < first_te - EMBM and ST[i+1]-ST[i] >= 50", "validation": "last 15% of train anchors (verbatim)",
                          "rng": "torch.manual_seed(SEED+YM); np.random.seed(SEED+YM) per fold", "label_window": "5m rows [E+1, E+48] => label end = E + 4h",
                          "causality": "max(E_train) + 4h <= E[first_te] - EMBM*4h", "grid": "4h anchors (all diffs 14400 s asserted)"}})
assert np.all(np.diff(E_ts) == 14400), "anchor grid is not a regular 4h grid"
def iso(t): return time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(t)))
ym = np.array([time.gmtime(int(t)).tm_year * 100 + time.gmtime(int(t)).tm_mon for t in E_ts])
ALL_MONTHS = [202501 + k for k in range(12)] + [202601 + k for k in range(8)]
MONTHS = [int(m) for m in os.environ.get("MONTHS", "").split(",") if m] or ALL_MONTHS
assert all(m in ALL_MONTHS for m in MONTHS), MONTHS
for _d in ("models", "preds_fold", "results", "preds"): os.makedirs(f"{MWF_OUT}/{_d}", exist_ok=True)
PRED = np.full((nA, NW), np.nan, np.float32)
_RESF = f"{MWF_OUT}/results/f10_V2MAIN_{TAG}_s{SEED}.json"
if os.path.exists(_RESF) and not FORCE:   # resume: keep finished folds' reports
    rep["folds"] = json.load(open(_RESF)).get("folds", {})
for _m in ALL_MONTHS:                       # resume: refill PRED from finished folds (test-month rows only)
    _pf = f"{MWF_OUT}/preds_fold/{TAG}_{_m}.npz"
    if os.path.exists(_pf):
        _z = np.load(_pf); _f, _l = int(_z["first_te"]), int(_z["last_te"]); PRED[_f:_l + 1] = _z["P"][:_l - _f + 1]
log(f"MWF start tag {TAG} embargo {EMBM} months {MONTHS} base_sha {rep['base_sha256'][:12]} self_sha {rep['self_sha256'][:12]} torch {torch.__version__} gpu {rep['gpu']}")
for YM in MONTHS:
    _done = all(os.path.exists(f"{MWF_OUT}/{d}/{TAG}_{YM}{s}") for d, s in (("models", ".pt"), ("preds_fold", ".npz"), ("models", "_config.json")))
    if _done and not FORCE and str(YM) in rep["folds"]:
        log(f"skip {YM}: already done"); continue
    te = np.where(ym == YM)[0]; assert te.size > 0 and np.all(np.diff(te) == 1), YM
    first_te, last_te = int(te[0]), int(te[-1])
    tr_idx = np.array([i for i in range(first_te - EMBM) if ST[i + 1] - ST[i] >= 50])
    # ── CAUSALITY ASSERT (printed per fold) ──
    max_tr = int(tr_idx[-1]); max_label_end = int(E_ts[max_tr]) + 48 * 300; cutoff = int(E_ts[first_te]) - EMBM * 14400
    assert max_tr < first_te - EMBM and max_label_end <= cutoff, (YM, max_tr, first_te, EMBM)
    log(f"CAUSALITY ASSERT {TAG} {YM}: n_train {len(tr_idx)} max_train_idx {max_tr} ({iso(E_ts[max_tr])}) max_train_label_end {iso(max_label_end)} "
        f"<= cutoff {iso(cutoff)} (= first_test {iso(E_ts[first_te])} - {EMBM} anchors) OK")
    cut = int(len(tr_idx) * 0.85)
    tr1, va1 = tr_idx[:cut], tr_idx[cut:]
    # 标定: 训练行抽样 med/std
    rowsel = np.concatenate([np.arange(ST[i], ST[i + 1]) for i in tr1[::7]])
    XS = XT[torch.from_numpy(rowsel[::3]).to(DEV)]
    mu = torch.nan_to_num(XS).mean(0); sd = torch.nan_to_num(XS).std(0) + 1e-6
    del XS
    torch.manual_seed(SEED + YM); np.random.seed(SEED + YM)
    mdl = Net(XT.shape[1] + (4 if CTXA else 0)).to(DEV)
    opt = torch.optim.AdamW(mdl.parameters(), lr=LR, weight_decay=1e-4)
    sch = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=EPOCHS)
    starts = list(range(int(tr1[0]) + BURN, int(tr1[-1]) - WIN, STRIDE))
    best_va, best_state, va_curve, alist, ep_s = -1e9, None, [], [], []
    t_fit = time.time()
    for ep in range(EPOCHS):
        tau = 0.5 - (0.5 - 0.1) * ep / max(EPOCHS - 1, 1)
        mdl.train(); order = np.random.permutation(starts); t0 = time.time()
        for s0 in order:
            span = [i for i in range(s0 - BURN, s0 + WIN) if i < first_te - EMBM]
            if len(span) < BURN + 32:
                continue
            nets, _ = run_span(mdl, span, mu, sd, tau, hard=False, loss_span=BURN)
            loss = -nets.mean() + LDD * es5(nets)
            if LPP > 0:
                us = []
                for i2 in span[BURN::4]:
                    u2, m2, _h = u_of(mdl, i2, mu, sd, tau, False)
                    if u2 is not None:
                        us.append(torch.zeros(NW, device=DEV).scatter(0, m2.long(), u2))
                if len(us) > 1:
                    loss = loss + LPP * torch.stack([torch.abs(us[k + 1] - us[k]).sum() for k in range(len(us) - 1)]).mean() * 1e2
            if LDC > 0:
                fl = FLAGT[torch.tensor(span[BURN:], device=DEV)]
                if int(fl.sum()) >= 3:
                    nf = nets[fl]
                    k = max(1, min(int(fl.sum()), int(math.ceil(0.05 * nets.shape[0]))))
                    loss = loss + LDC * torch.topk(-nf, k).values.mean()
            opt.zero_grad(); loss.backward()
            nn.utils.clip_grad_norm_(mdl.parameters(), 1.0); opt.step()
        sch.step()
        mdl.eval()
        with torch.no_grad():
            span = [int(i) for i in np.concatenate([tr1[-BURN:], va1])]
            nets, _ = run_span(mdl, span, mu, sd, 0.1, hard=True, loss_span=BURN)
            va = float(nets.mean() - LDD * es5(nets))
            if LDC > 0:
                flv = FLAGT[torch.tensor(span[BURN:], device=DEV)]
                if int(flv.sum()) >= 3:
                    kv = max(1, min(int(flv.sum()), int(math.ceil(0.05 * nets.shape[0]))))
                    va -= float(LDC * torch.topk(-nets[flv], kv).values.mean())
        al = float(mdl.alpha()); va_curve.append(round(va, 4)); alist.append(round(al, 4)); ep_s.append(round(time.time() - t0, 1))
        if va > best_va:
            best_va, best_state = va, {k: v.detach().clone() for k, v in mdl.state_dict().items()}
        log(f"[{TAG} {YM}] ep{ep} va {va:+.3f} α {al:.3f} τ {tau:.2f} ({time.time()-t0:.0f}s)")
    wall = time.time() - t_fit
    mdl.load_state_dict(best_state); mdl.eval()
    # 测试: 时序整段(燃烧段用 te 前 BURN 锚), 硬秩; 同时导出原始分数
    with torch.no_grad():
        span = [int(i) for i in range(max(0, first_te - BURN), last_te + 1)]
        nets, _ = run_span(mdl, span, mu, sd, 0.1, hard=True, loss_span=first_te - span[0])
        trn_series = []
        w = torch.zeros(NW, device=DEV); al = mdl.alpha()
        HT = torch.zeros(NW, 32, device=DEV) if REC else None
        PRED_f = np.full((len(te), NW), np.nan, np.float32)
        for k, i in enumerate(span):
            u, midx, hst = u_of(mdl, i, mu, sd, 0.1, hard=True, H=HT)
            if REC and hst[1] is not None:
                HT = HT.index_put((hst[0],), hst[1].detach())
            if u is not None:
                uf = torch.zeros(NW, device=DEV).scatter(0, midx.long(), u)
                wn = (1 - al) * w + al * uf
                if i >= first_te:
                    a0, b0 = int(ST[i]), int(ST[i + 1])
                    x = torch.clamp((XT[a0:b0] - mu) / sd, -5, 5)
                    if CTXA:
                        x = torch.cat([x, CTXT[i].expand(b0 - a0, 4)], 1)
                    if REC:
                        sc, _ = mdl.score_rec(torch.nan_to_num(x), HT[PST[a0:b0].long()])
                        PRED_f[i - first_te, midx.cpu().numpy()] = sc.cpu().numpy()
                    else:
                        PRED_f[i - first_te, midx.cpu().numpy()] = mdl.f(torch.nan_to_num(x)).squeeze(-1).cpu().numpy()
            else:
                wn = w
            if i >= first_te:
                trn_series.append(float((wn - w).abs().sum()))
            w = wn
    nets_np = nets.cpu().numpy()
    yr_net = float(np.mean(nets_np)); es_np = float(es5(nets).item())
    # ── diagnostic (no effect on training): raw scores of this fold's model for EVERY anchor ≥ first_te (IC-by-model-age) ──
    with torch.no_grad():
        PA = np.full((nA - first_te, NW), np.nan, np.float32)
        for i in range(first_te, nA):
            a0, b0 = int(ST[i]), int(ST[i + 1])
            if b0 - a0 < 50:
                continue
            x = torch.clamp((XT[a0:b0] - mu) / sd, -5, 5)
            PA[i - first_te, PST[a0:b0].cpu().numpy()] = mdl.f(torch.nan_to_num(x)).squeeze(-1).cpu().numpy()
    _nm = last_te - first_te + 1
    _ok = np.isfinite(PRED_f) & np.isfinite(PA[:_nm]); _dm = float(np.max(np.abs(PRED_f[_ok] - PA[:_nm][_ok]))) if _ok.any() else 0.0
    assert np.array_equal(np.isfinite(PRED_f), np.isfinite(PA[:_nm])) and _dm <= 1e-5, f"test-pass vs all-anchor scores differ: max {_dm}"
    PRED[first_te:last_te + 1] = PRED_f
    torch.save(best_state, f"{MWF_OUT}/models/{TAG}_{YM}.pt")
    np.savez_compressed(f"{MWF_OUT}/preds_fold/{TAG}_{YM}.npz", first_te=first_te, last_te=last_te, E_first=int(E_ts[first_te]), P=PA)
    fold = {"n_test": int(te.size), "first_test": iso(E_ts[first_te]), "last_test": iso(E_ts[last_te]), "n_train": int(len(tr_idx)), "n_val": int(len(va1)),
            "max_train_idx": max_tr, "max_train_label_end": iso(max_label_end), "cutoff": iso(cutoff), "embargo_anchors": EMBM, "causality_ok": True,
            "n_windows_per_epoch": len(starts), "best_va": round(best_va, 4), "best_epoch": int(np.argmax(va_curve)), "va_curve": va_curve, "alpha_curve": alist,
            "alpha_final": alist[int(np.argmax(va_curve))], "net_mean_bps": round(yr_net, 4), "es5_bps": round(es_np, 3), "turnover_mean": round(float(np.mean(trn_series)), 5),
            "wall_clock_s": round(wall, 1), "epoch_s": ep_s, "test_vs_all_maxdiff": _dm, "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    rep["folds"][str(YM)] = fold
    json.dump({"tag": TAG, "fold": YM, "seed_fold": SEED + YM, **fold,
               "recipe": {k: rep[k] for k in ("arm", "seed", "cost", "ldd", "afix", "epochs", "lr", "win", "burn", "stride", "embargo")},
               "self_sha256": rep["self_sha256"], "base_sha256": rep["base_sha256"], "targets_sha256": rep["targets_sha256"], "fea82_sha256": rep["fea82_sha256"],
               "fea89_sha256": rep["fea89_sha256"], "legs_sha256": rep["legs_sha256"], "torch": rep["torch"], "gpu": rep["gpu"]},
              open(f"{MWF_OUT}/models/{TAG}_{YM}_config.json", "w"), indent=1, default=float)
    np.save(f"{MWF_OUT}/preds/f10_V2MAIN_{TAG}_s{SEED}.npy", PRED)
    json.dump(rep, open(_RESF, "w"), indent=1, default=float)
    log(f"== {TAG} {YM}: net {yr_net:+.3f} bps/锚 ES5 {es_np:.2f} 换手 {np.mean(trn_series):.4f} α* {fold['alpha_final']} best_ep {fold['best_epoch']} wall {wall:.0f}s")
    del mdl, opt; torch.cuda.empty_cache()
rep["net_mean_all"] = round(float(np.mean([f["net_mean_bps"] for f in rep["folds"].values()])), 4)
json.dump(rep, open(_RESF, "w"), indent=1, default=float)
log(f"MWF_TRAIN_DONE {TAG} s{SEED} folds {len(rep['folds'])} 月均净 {rep['net_mean_all']:+.3f} bps/锚(训练帧, 非终审)")
