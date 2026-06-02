# Funding-Rate Mean Reversion in Crypto Perpetuals

**Artemis Analytics Quant Research Competition — Track 1: Crypto Factor Rebalancing.**

A single-factor study that builds a funding-rate mean-reversion strategy on
Hyperliquid perpetual futures, then deliberately tries to break it. The headline
backtest looks excellent (**+63.6%, Sharpe 1.91**). After a battery of honesty
tests, the conclusion is:

> ## Verdict: 2 of 4 gates → **NOT DEPLOYABLE**

…and the *way* it fails — a big, cost-robust, out-of-sample-positive number that
still can't clear an honest significance bar — is the textbook fingerprint of
data-mining. Per the competition's own framing ("we are looking for the best
thinking … a correctly understood negative-Sharpe strategy beats impressive
returns with no critical analysis"), **the honest null is the deliverable.**

| Gate | Question | Result |
|------|----------|:------:|
| 1. Significance | Significant after multiple-testing correction? | **FAIL** |
| 2. Sign stability | Positive in-sample *and* out-of-sample? | PASS |
| 3. Overfitting | Beats the Deflated-Sharpe search penalty? | **FAIL** |
| 4. Costs | Survives realistic (and 2×) trading frictions? | PASS |

---

## The idea in one paragraph

A perpetual future has no expiry, so the exchange uses a **funding rate** to tether
the perp to spot: when longs are crowded the perp trades rich and longs pay shorts
(positive funding); when shorts are crowded, the reverse. Funding is therefore a
real-money readout of positioning crowding. The bet is **mean reversion**: rank the
universe each day by a funding *z-score*, go **long the lowest-funding coins and
short the highest**, equal-weight and market-neutral. Same intuition as *Betting
Against Beta* — the over-leveraged, over-loved side earns less than its risk would
suggest.

```
z = ( mean_21d(funding) − mean_90d(funding) ) / std_90d(funding)
```

The full thesis, three-act narrative, and findings are in
[PROJECT_SUMMARY.md](PROJECT_SUMMARY.md); the formal write-up is the research report
([report.md](report.md) → **ArtemisReport.pdf**).

---

## Repository map

| Path | What it is |
|------|------------|
| **`ArtemisReport.pdf`** | The research report (deliverable #1). Built from `report.md` + `report.css`. |
| **`pitch_deck.pptx`** | The non-technical pitch deck (deliverable #3), 11 slides. Built by `make_deck.py`. |
| `PROJECT_SUMMARY.md` | Research narrative — thesis, why it should work, how it was tested, what we learned. |
| `data_pipeline.py` | Pulls funding + OHLCV from the Hyperliquid API and builds the analysis panel. |
| `test_data_pipeline.py` | Pytest suite pinning forward-return alignment (4 tests). |
| `validation.ipynb` | **The honesty battery** — HAC t-stats, IS-only re-sweep, BH/Holm, bootstrap, Deflated Sharpe, costs, OOS, the four-gate decision rule. |
| `signal_analysis.ipynb` | Discovery analysis — quintiles, IC, long/short backtest, robustness. |
| `parameter_sweep.ipynb` | The window/horizon parameter mining (the search the validation penalizes). |
| `universe_sweep.ipynb` | The universe-size sweep (chose top-35). |
| `make_figures.py` | Regenerates all five report/deck figures from `data/panel.parquet`. |
| `figures/` | The five generated PNGs (`fig1`–`fig5`). |
| `data/` | Committed parquet data so every result reproduces with **no network calls**. |
| `requirements.txt` / `environment.yml` | Pinned dependencies. |

---

## Setup

Reproduced on **Python 3.11** (conda env `artemis`). Pick either path.

**Conda (recommended — matches the dev environment):**

```bash
conda env create -f environment.yml
conda activate artemis
```

**pip / venv:**

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

> The report PDF build uses `pandoc` (a system binary, included in `environment.yml`;
> install separately for the pip path). Re-pulling raw data needs internet; every
> analysis step below runs offline from the committed `data/`.

---

## Reproduce the results

All data is committed under `data/`, so steps 2–4 need **no network access**.

```bash
# 1. (optional) re-pull from Hyperliquid and rebuild data/  — needs internet
python data_pipeline.py

# 2. forward-return alignment tests  — expect 4 passed
pytest test_data_pipeline.py

# 3. the full honesty battery — prints the four-gate verdict (2/4 → NOT DEPLOYABLE)
jupyter nbconvert --to notebook --execute --inplace validation.ipynb

# 4. regenerate every figure into figures/
python make_figures.py
```

Rebuild the deliverables (optional):

```bash
python make_deck.py                                   # -> pitch_deck.pptx
pandoc report.md -o ArtemisReport.pdf \
       --pdf-engine=weasyprint --css report.css       # -> ArtemisReport.pdf
```

### Headline numbers (these reproduce exactly)

| Metric | Value | Produced by |
|--------|-------|-------------|
| Total return (backtest) | **+63.62%** | `make_figures.py` |
| Sharpe (naive) | **1.91** | `make_figures.py` |
| Max drawdown | **−19.25%** | `make_figures.py` |
| Q1−Q5 spread (14d) | **+1.93%** | `make_figures.py` |
| Mean rank IC (14d) | **−0.0314** | `make_figures.py` |
| Out-of-sample cumulative | **+12.72%** | `make_figures.py` / `validation.ipynb` |
| Bootstrap p-value (traded spread) | **0.057** | `validation.ipynb` |
| Combos surviving BH/Holm | **0 of 56** | `validation.ipynb` |
| Deflated Sharpe Ratio | **47%** | `validation.ipynb` |
| Transaction cost | **6.45%/yr**: 107.8% gross → **94.8%** net ann. (82.7% at 2×) | `validation.ipynb` |

---

## Known limitations (stated up front)

- **Survivorship bias** — the universe is pulled live, so coins delisted before the
  pull are silently excluded. Not fixable without a historical-universe snapshot.
- **Point-in-time universe bias** — ranked by *today's* volume; 7 coins listed
  mid-study, reintroducing selection-on-outcome at the margin.
- **Short history** — ~1 year (one regime cycle) is too little to cleanly separate a
  real, regime-conditional edge from noise.
- **Partially-burned out-of-sample** — the original parameter sweep had already seen
  all the data; the IS-only re-sweep mitigates but does not eliminate this.
- **Funding P&L not modeled** — only the price-return leg is backtested.

See [report.md](report.md) §8 and `validation.ipynb` for the full treatment.

---

## Deliverables

Three items make up this submission:

1. **Research report** — `ArtemisReport.pdf`.
2. **Code / analysis** — this GitHub repository.
3. **Pitch deck** — `pitch_deck.pptx` (presented as Google Slides).
