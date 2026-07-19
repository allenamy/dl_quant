"""Live shadow — pluggable market-data source abstraction.

> **创建:** 2026-07-19 JST | **Session:** fable multi-asset-v2 (0B live shadow) | **状态:** v1 | **作废条件:** 数据源端点/口径变更

The engine live loop reads market data through the `DataSource` interface so the ingest is
**pluggable**: on `jpline` the live REST endpoints (`fapi.binance.com`) are firewall-blocked, so
we use `CDNDataSource` (the `data.binance.vision` static archive, T+1 daily — the only reachable
egress). A partner deploying on infra WITHOUT that firewall should swap in `RESTDataSource`
(same interface, real-time) — see RUNBOOK. Nothing downstream (inference / signal loop / P&L)
depends on which implementation is bound.

CDN archive layout (`https://data.binance.vision/data/futures/um/`):
  monthly|daily / klines / <SYM>/1h/<SYM>-1h-<PERIOD>.zip           OHLCV+quote_volume
  monthly       / fundingRate / <SYM>/<SYM>-fundingRate-<YYYY-MM>.zip  calc_time,interval_h,rate
  monthly|daily / premiumIndexKlines / <SYM>/1h/<SYM>-1h-<PERIOD>.zip  premium index OHLC (funding source)
  daily         / metrics / <SYM>/<SYM>-metrics-<YYYY-MM-DD>.zip        OI / long-short / taker ratios
Each archive has a `.CHECKSUM` sidecar (sha256) we verify. Landmines (see REPRODUCTION.md §1):
listing is unreliable — we GET-by-constructed-URL (404 = genuinely absent), never enumerate.
"""
from __future__ import annotations

import abc
import datetime as dt
import hashlib
import io
import os
import time
import urllib.error
import urllib.request
import zipfile

import numpy as np
import pandas as pd

CDN = "https://data.binance.vision/data/futures/um"
CACHE = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/live/cache"
UA = {"User-Agent": "Mozilla/5.0 (multi-asset-v2 live shadow; research)"}

KLINE_COLS = ["open_time", "open", "high", "low", "close", "volume", "close_time",
              "quote_volume", "count", "taker_buy_volume", "taker_buy_quote_volume", "ignore"]


def _months(d0: dt.date, d1: dt.date):
    y, m = d0.year, d0.month
    out = []
    while (y, m) <= (d1.year, d1.month):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m > 12:
            m = 1; y += 1
    return out


def _days(d0: dt.date, d1: dt.date):
    return [(d0 + dt.timedelta(days=i)).isoformat() for i in range((d1 - d0).days + 1)]


class DataSource(abc.ABC):
    """Interface the live loop depends on. All returns are tz-naive UTC-ms-stamped DataFrames."""

    @abc.abstractmethod
    def klines_1h(self, sym: str, d0: dt.date, d1: dt.date) -> pd.DataFrame:
        """[open_time_ms, open, high, low, close, volume, quote_volume] for [d0, d1] inclusive."""

    @abc.abstractmethod
    def funding(self, sym: str, d0: dt.date, d1: dt.date) -> pd.DataFrame:
        """[fundingTime_ms, funding_interval_h, fundingRate] over the settlement grid in [d0,d1].
        NOTE (CDN): fundingRate is MONTHLY-archived only — the current (open) month is absent until
        it closes; derive it from premium_index_1h for the live tail (see funding_derive.py)."""

    @abc.abstractmethod
    def premium_index_1h(self, sym: str, d0: dt.date, d1: dt.date) -> pd.DataFrame:
        """[open_time_ms, close] hourly premium-index close (funding-rate upstream source)."""

    @abc.abstractmethod
    def metrics_5m(self, sym: str, d0: dt.date, d1: dt.date) -> pd.DataFrame:
        """raw 5m metrics rows (OI / long-short / taker ratios) over [d0,d1]."""

    @abc.abstractmethod
    def latest_complete_date(self, sym: str = "BTCUSDT") -> dt.date:
        """most recent date whose full-day archive is published (T+1 on the CDN)."""


class CDNDataSource(DataSource):
    """data.binance.vision static-archive implementation (T+1 daily). Idempotent local cache +
    sha256 checksum verification. `prefer_daily` uses daily archives for the tail (fresher)."""

    def __init__(self, cache=CACHE, verify_checksum=True, retries=4, throttle_s=0.05):
        self.cache = cache
        self.verify = verify_checksum
        self.retries = retries
        self.throttle = throttle_s
        os.makedirs(cache, exist_ok=True)

    # ---- low-level fetch (GET-by-URL, 404 = absent; never list) ---------------------------
    def _get(self, url: str) -> bytes | None:
        for a in range(self.retries):
            try:
                req = urllib.request.Request(url, headers=UA)
                with urllib.request.urlopen(req, timeout=30) as r:
                    return r.read()
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    return None                       # genuinely absent
                time.sleep(0.5 * (a + 1))
            except Exception:
                time.sleep(0.5 * (a + 1))
        return None

    def _archive_csv(self, rel: str, cols=None) -> pd.DataFrame | None:
        """Fetch <CDN>/<rel>.zip (cached), verify checksum, return the single CSV as a DataFrame."""
        cache_zip = os.path.join(self.cache, rel.replace("/", "__") + ".zip")
        if os.path.exists(cache_zip) and os.path.getsize(cache_zip) > 0:
            raw = open(cache_zip, "rb").read()
        else:
            raw = self._get(f"{CDN}/{rel}.zip")
            if raw is None:
                return None
            if self.verify:
                chk = self._get(f"{CDN}/{rel}.zip.CHECKSUM")
                if chk is not None:
                    want = chk.split()[0].decode()
                    got = hashlib.sha256(raw).hexdigest()
                    if want != got:
                        raise ValueError(f"checksum mismatch {rel}: {got} != {want}")
            os.makedirs(os.path.dirname(cache_zip), exist_ok=True)
            with open(cache_zip, "wb") as fh:
                fh.write(raw)
            time.sleep(self.throttle)
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            name = z.namelist()[0]
            with z.open(name) as fh:
                head = fh.read(64)
        has_header = head[:1].isalpha() or head[:1] == b"o"      # 'open_time'/'calc_time' vs a digit
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            df = pd.read_csv(io.BytesIO(z.read(z.namelist()[0])),
                             header=0 if has_header else None, names=None if has_header else cols)
        return df

    def _assemble(self, sym, kind, d0, d1, cols=None, sub="1h", daily_ok=True):
        """Concatenate the monthly archives spanning [d0,d1], filling the trailing open month with
        daily archives (T+1). kind in {klines, premiumIndexKlines, fundingRate, metrics}."""
        frames = []
        if kind == "metrics":                                    # daily-only
            for d in _days(d0, d1):
                rel = f"daily/metrics/{sym}/{sym}-metrics-{d}"
                df = self._archive_csv(rel)
                if df is not None:
                    frames.append(df)
            return pd.concat(frames, ignore_index=True) if frames else None
        pathmid = f"{kind}/{sym}/{sub}" if kind in ("klines", "premiumIndexKlines") else f"{kind}/{sym}"
        for ym in _months(d0, d1):
            tag = ym if kind == "fundingRate" else ym
            rel = f"monthly/{pathmid}/{sym}-{'1h-' if sub=='1h' and kind!='fundingRate' else ('fundingRate-' if kind=='fundingRate' else '1h-')}{tag}"
            df = self._archive_csv(rel, cols=cols)
            if df is not None:
                frames.append(df)
            elif daily_ok and kind != "fundingRate":             # open month -> daily archives
                y, m = int(ym[:4]), int(ym[5:7])
                md0 = max(d0, dt.date(y, m, 1))
                md1 = min(d1, (dt.date(y, m, 28) + dt.timedelta(days=10)).replace(day=1) - dt.timedelta(days=1))
                for d in _days(md0, md1):
                    drel = f"daily/{pathmid}/{sym}-1h-{d}"
                    ddf = self._archive_csv(drel, cols=cols)
                    if ddf is not None:
                        frames.append(ddf)
        return pd.concat(frames, ignore_index=True) if frames else None

    # ---- public interface -----------------------------------------------------------------
    def klines_1h(self, sym, d0, d1):
        df = self._assemble(sym, "klines", d0, d1, cols=KLINE_COLS, sub="1h")
        if df is None:
            return pd.DataFrame(columns=["open_time_ms", "open", "high", "low", "close", "volume", "quote_volume"])
        df = df.rename(columns={"open_time": "open_time_ms", "quote_volume": "quote_volume"})
        for c in ("open", "high", "low", "close", "volume", "quote_volume"):
            df[c] = pd.to_numeric(df[c], errors="coerce")
        df["open_time_ms"] = df["open_time_ms"].astype(np.int64)
        return df[["open_time_ms", "open", "high", "low", "close", "volume", "quote_volume"]].sort_values("open_time_ms").reset_index(drop=True)

    def funding(self, sym, d0, d1):
        df = self._assemble(sym, "fundingRate", d0, d1)
        if df is None:
            return pd.DataFrame(columns=["fundingTime_ms", "funding_interval_h", "fundingRate"])
        df = df.rename(columns={"calc_time": "fundingTime_ms", "funding_interval_hours": "funding_interval_h",
                                "last_funding_rate": "fundingRate"})
        df["fundingTime_ms"] = df["fundingTime_ms"].astype(np.int64)
        df["fundingRate"] = pd.to_numeric(df["fundingRate"], errors="coerce")
        lo, hi = int(time.mktime(d0.timetuple()) * 1000), int((time.mktime(d1.timetuple()) + 86400) * 1000)
        return df.sort_values("fundingTime_ms").reset_index(drop=True)

    def premium_index_1h(self, sym, d0, d1):
        df = self._assemble(sym, "premiumIndexKlines", d0, d1, cols=KLINE_COLS, sub="1h")
        if df is None:
            return pd.DataFrame(columns=["open_time_ms", "close"])
        df = df.rename(columns={"open_time": "open_time_ms"})
        df["open_time_ms"] = df["open_time_ms"].astype(np.int64)
        df["close"] = pd.to_numeric(df["close"], errors="coerce")
        return df[["open_time_ms", "close"]].sort_values("open_time_ms").reset_index(drop=True)

    def metrics_5m(self, sym, d0, d1):
        df = self._assemble(sym, "metrics", d0, d1)
        return df if df is not None else pd.DataFrame()

    def latest_complete_date(self, sym="BTCUSDT"):
        today = dt.datetime.utcnow().date()
        for back in range(1, 6):
            d = today - dt.timedelta(days=back)
            if self._archive_csv(f"daily/klines/{sym}/1h/{sym}-1h-{d.isoformat()}") is not None:
                return d
        raise RuntimeError("no recent daily klines archive found on CDN (last 5 days)")


class RESTDataSource(DataSource):
    """Real-time fapi.binance.com implementation — STUB for partner deployment (jpline firewalls it).
    Same interface as CDNDataSource; a partner fills these in with /fapi/v1/{klines,fundingRate,
    premiumIndex} + /futures/data/openInterestHist etc. and the live loop is unchanged."""

    _MSG = ("RESTDataSource is a deployment stub. On jpline the fapi.binance.com REST endpoints are "
            "firewall-blocked, so the shadow uses CDNDataSource (T+1). A partner on unfirewalled infra "
            "implements these four methods against the live REST API (real-time) and binds this instead.")

    def klines_1h(self, sym, d0, d1): raise NotImplementedError(self._MSG)
    def funding(self, sym, d0, d1): raise NotImplementedError(self._MSG)
    def premium_index_1h(self, sym, d0, d1): raise NotImplementedError(self._MSG)
    def metrics_5m(self, sym, d0, d1): raise NotImplementedError(self._MSG)
    def latest_complete_date(self, sym="BTCUSDT"): raise NotImplementedError(self._MSG)


def get_source(kind="cdn", **kw) -> DataSource:
    return {"cdn": CDNDataSource, "rest": RESTDataSource}[kind](**kw)
