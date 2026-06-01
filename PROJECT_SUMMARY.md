# Funding Rate Mean Reversion Strategy — Project Summary

## Competition Context
- **Competition:** Artemis Analytics Quant Research Competition — Track 1: Crypto Factor Rebalancing Strategy
- **Deadline:** June 1, 2026 at 11:59 PM EST
- **Deliverables:** Research report (PDF), code/analysis (GitHub repo), pitch deck (Google Slides shared with lindsey@artemisanalytics.xyz)
- **Judging:** Research Quality (30%), Signal/Edge Validity (30%), Critical Evaluation (20%), Communication (20%). They explicitly value honest thinking over impressive backtests.
- **Partner:** Daniel is working with a partner who is building a momentum factor. The two factors will be combined into a multi-factor model.

## Strategy Overview
**Funding rate mean reversion on Hyperliquid perpetual futures.**

The thesis: funding rates on perps reflect the cost of holding leveraged positions. When funding is extremely positive, longs are overcrowded and paying shorts. These extremes tend to snap back — coins with very high funding underperform going forward, and coins with very negative funding outperform.

The signal is a z-score computed from daily funding rates:
```
z-score = (short-window rolling mean - long-window rolling mean) / long-window rolling std
```

## Data Pipeline
- **Source:** Hyperliquid API (free, no API key, works in the US — Binance futures API is geo-blocked in the US)
- **Endpoints used:**
  - `POST https://api.hyperliquid.xyz/info` with `{"type": "metaAndAssetCtxs"}` — gets all perp markets + 24h volume
  - `POST https://api.hyperliquid.xyz/info` with `{"type": "fundingHistory", "coin": ..., "startTime": ...}` — 8-hour funding rate snapshots, max 500 per request
  - `POST https://api.hyperliquid.xyz/info` with `{"type": "candleSnapshot", "req": {"coin": ..., "interval": "1d", ...}}` — daily OHLCV candles
- **Data pulled:** 1 year (May 2025 – May 2026), ~246k funding records, ~10.7k daily candles
- **Files:**
  - `data_pipeline.py` — pulls data from Hyperliquid, builds signal features, saves to parquet files in `data/`
  - `build_panel.py` — standalone fix script that rebuilds features from existing raw data (used when data_pipeline.py had a bug)
  - Output files in `data/`: `symbols.json`, `funding_rates_raw.parquet`, `ohlcv_daily.parquet`, `funding_features.parquet`, `panel.parquet`

## Key Findings

### 1. Initial parameters failed (7d/30d z-score)
- 1-day IC: -0.0038 (essentially zero)
- 7-day IC: +0.0082 (slightly wrong direction — momentum, not mean reversion)
- L/S total return: -8.73%, Sharpe: -0.20, Max DD: -35.28%
- Quintile analysis showed no monotonic pattern

### 2. Parameter sweep revealed the real signal
Tested 78 combinations: short windows (3, 7, 14, 21), long windows (14, 30, 60, 90), forward horizons (1, 3, 5, 7, 14, 21 days).

**Best parameters by IC:**
- **Short window: 21 days**
- **Long window: 90 days**
- **Forward horizon: 14 days**
- Mean IC: -0.049 (strong for a single factor)
- Q1-Q5 spread: ~2%+

**Key insight:** Funding crowding on Hyperliquid builds slowly (over weeks) and unwinds slowly (over 2-3 weeks). The original 7d/30d windows were too fast — they caught noise, not persistent positioning imbalances.

### 3. Universe size sweep
Tested top 10, 15, 20, 25, 30, 35, 40, 45, 50 coins by 24h volume.

| Coins | IC      | Spread  | Return | Sharpe | Max DD  | Per Q |
|-------|---------|---------|--------|--------|---------|-------|
| 10    | -0.0230 | -0.689% | -8.6%  | -0.13  | -56.0%  | 2     |
| 15    | -0.0046 | -0.897% | -3.2%  | -0.07  | -41.0%  | 3     |
| 20    | -0.0212 | 1.234%  | 13.9%  | 0.34   | -29.0%  | 4     |
| 25    | -0.0667 | 3.537%  | 65.2%  | 1.68   | -24.1%  | 5     |
| 30    | -0.0398 | 1.978%  | 46.3%  | 1.24   | -25.2%  | 6     |
| 35    | -0.0314 | 1.935%  | 63.6%  | 1.91   | -19.2%  | 7     |
| 40    | -0.0255 | 1.469%  | 30.7%  | 0.96   | -18.6%  | 8     |
| 45    | -0.0324 | 1.976%  | 36.3%  | 1.24   | -20.6%  | 9     |
| 50    | -0.0324 | 1.953%  | 50.7%  | 1.85   | -12.5%  | 10    |

**Best universe: Top 35 coins by volume (Sharpe = 1.91)**

Small universes (10-15) fail due to insufficient diversification — 2-3 coins per quintile means individual coin noise dominates. The sweet spot is 25-35 coins. Max drawdown keeps falling with more coins (diversification benefit).

### 4. Regime dependence (critical finding)
The strategy worked well from July–December 2025 (choppy/range-bound market, equity curve climbed to +80%) then suffered a large drawdown in January 2026 (strong BTC rally / trending market). Mean reversion gets crushed during strong directional moves because the crowded longs are *right*.

The IC over time shows the signal flips between mean-reversion regimes (negative IC) and momentum regimes (positive IC).

### 5. Q2 anomaly
In quintile analysis, Q1 (lowest funding) strongly outperforms as expected, but Q2 (second lowest) often underperforms. This suggests the signal is strongest at the extremes (tail effect) rather than a smooth linear relationship.

## Best Parameters Summary
```
Z-Score Short Window:  21 days
Z-Score Long Window:   90 days
Forward Horizon:       14 days
Universe Size:         Top 35 coins by 24h volume on Hyperliquid
Rebalance Frequency:   Daily (but weekly may reduce turnover)
```

## Combining with Momentum Factor
- The two factors should complement rather than cancel because they operate on different dimensions (positioning vs price trend) and different regimes
- Mean reversion works in range-bound markets; momentum works in trending markets
- When combined, momentum covers the drawdown periods for mean reversion and vice versa
- The combined portfolio should have lower volatility and higher Sharpe than either factor alone
- A regime filter is likely unnecessary when combining — momentum naturally acts as the regime hedge
- Simple combination: composite_score = w1 * momentum_zscore + w2 * funding_zscore, then rank and form L/S portfolio

## Files in ArtemisComp/
- `data_pipeline.py` — main data pipeline (Hyperliquid API → parquet files), defaults to 21d/90d windows
- `signal_analysis.ipynb` — full signal analysis with quintile sorts, IC, L/S simulation, robustness checks (updated to use 21d/90d params)
- `parameter_sweep.ipynb` — systematic sweep of z-score windows and forward horizons
- `universe_sweep.ipynb` — tests different numbers of coins
- `data/` — parquet data files and symbols.json
- Reference papers: "Betting Against Beta.pdf", "The Case for Momentum Investing.pdf"

## Still TODO
- Combine with partner's momentum factor (compute correlation, simulate combined portfolio)
- Add transaction cost estimates
- Consider: only trading extreme z-scores (> |1.0| or |1.5|) to exploit the tail effect
- Write research report (PDF), build pitch deck, set up GitHub repo

## Technical Notes
- Daniel uses VS Code with conda environment named "artemis" (Python 3.11) on a MacBook Air
- Project folder: ~/Desktop/ArtemisComp
- File edits made through Cowork sometimes don't sync to his Mac — when this happens, creating a new file works better than editing existing ones
- Parquet files require pyarrow (`pip install pyarrow`)
- The Artemis API (artemis-py package) covers on-chain fundamentals (price, market cap, TVL, fees, revenue, developer activity) but NOT per-asset funding rates — that's why we use Hyperliquid directly
