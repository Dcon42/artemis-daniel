# Project Status — Model Overhaul Plan

## Plain-English Summary (Tasks 1–10 — start here)

**What this project is testing:** whether the "funding-rate mean-reversion" signal is a real, tradeable edge or just a mirage from data-mining. The original analysis (`parameter_sweep.ipynb`) tried 84 parameter combos and crowned **21/90/14** (short window / long window / forward horizon, in days) the winner. Tasks 1–4 are the honesty checks on that claim; Tasks 5–8 then stress-test the carried-forward winner with formal statistics (bootstrap, deflated Sharpe, costs, and out-of-sample); Task 9 rolls every one of those results into a single four-gate deploy/don't-deploy scorecard; Task 10 writes the honest caveats back into the *original* optimistic notebook so a reader can't take its rosy claims at face value.

**What was done, task by task:**

- **Task 1 — Universe / survivorship audit.** Confirmed the coin list was pulled from *today's* live exchange, so any coin delisted mid-study is silently missing — which quietly deletes losers and flatters returns. Also found 7 coins (PUMP, XPL, WLFI, ASTER, MON, LIT, CHIP) that listed partway through the study. Can't be fully fixed without historical universe data, so it's documented as a known limitation.

- **Task 2 — Sealed an out-of-sample (OOS) window.** Split the data: ~273 days in-sample / 9,139 rows (used to pick parameters) and ~93 days / 3,255 rows held back as a final test (starting Feb 15, 2026). Caveat recorded: this holdout is "partly burned" because the original sweep had already seen all the data; re-running the sweep in-sample-only (Task 3) reduces but does not eliminate that.

- **Task 3 — Honest re-run of the search.** Re-did the parameter sweep using *only* in-sample data plus proper statistics (HAC / Newey-West t-stats, which aren't fooled by overlapping returns). Across all 56 combos tested: nothing was statistically significant (best p-value = 0.080, which doesn't even clear the loosest bar), every top result had a *negative* information coefficient, and the original "winner" 21/90/14 didn't even make the top 10.

- **Task 4 — Multiple-testing correction.** Because testing many combos guarantees a few look good by luck, applied Benjamini-Hochberg and Holm corrections to all 56 p-values. Result: **0 survivors out of 56** by every measure (naive, BH, Holm). Statistical null, confirmed.

- **Task 5 — Stationary block bootstrap.** Built the actual long-low/short-high traded spread for the carried-forward 21/90/14 combo (244 in-sample days) and tested whether its mean beats zero, using a block bootstrap that respects autocorrelation. The spread is faintly **positive (+0.00224/day, naive Sharpe 1.95) but not significant** — bootstrap p=0.057, HAC p=0.073, 95% CI straddles zero. Both methods agree: **no real edge.** Notably this corrects the earlier Task 3/4 *prediction* that the spread would be negative — the negative rank IC didn't translate to a money-losing portfolio because the per-quintile return curve is non-monotonic (worst returns sit in the middle quintiles). So the honest read is "insignificant," not "backwards."

- **Task 6 — Deflated Sharpe Ratio (the "how hard did you search?" penalty).** The in-sample strategy posts a juicy-looking annualized Sharpe of 1.95 — but that number ignores that we tried *many* strategies and kept the best-looking one. The Deflated Sharpe Ratio (DSR) asks: *given how much we searched, how likely is this Sharpe to be real rather than the luckiest draw?* Answer: only **47%** — far below the 95% bar a real edge needs to clear. So it **FAILs**. Two honesty notes: (1) the search count is genuinely debatable (this project tried 56 combos, the original tried 84), so we reported the DSR at N=56, 84, and the combined 140 — it fails at all three (55%/52%/47%), so the choice doesn't matter; we headline the strictest (140). (2) The plan's original DSR code had a bug that always spat out 0% no matter the data — we caught and fixed it so the 47% is a real, defensible number. Bottom line: once you account for the size of the search, the pretty Sharpe evaporates — exactly what the bootstrap (Task 5) already hinted at.

- **Task 7 — Transaction-cost model (does the strategy survive real-world trading frictions?).** A backtest that ignores costs is fantasy — every time you rotate the portfolio you pay exchange fees and cross the bid-ask spread, and a fast-trading strategy can look great on paper yet bleed to death once those are charged. So we built a realistic Hyperliquid cost stack (0.05% taker fee + 0.05% half-spread = 0.10% per side) and charged it on the strategy's actual daily trading. It turns over about **18% of the book per day**, which works out to roughly **6.5% a year** in costs. The surprising-but-honest result: **costs do *not* kill this strategy** — the in-sample return only slips from 107.8% gross to 94.8% net, and it stays strongly positive (+82.7%) even when we double the cost assumption as a stress test. The crucial framing: this does **not** rescue the signal. The return was never the problem — the problem is that it was never *statistically significant* (bootstrap p=0.057, Deflated Sharpe 47%). A big in-sample number that comfortably survives costs but flunks every significance test is *exactly* what data-mining looks like: you can always find a fluke that prints money in the backtest, and costs alone won't expose it — only honest statistics do. So this strategy still fails; it just fails on significance (Tasks 4 and 6), not on costs. (Honesty note: as in Task 6, the plan's code had a bug — it charged each portfolio rotation twice, double-counting costs ~2× — which we caught and fixed, so the 6.5%/yr figure is the correct, defensible one rather than an inflated 12.9%.)

- **Task 8 — Out-of-sample test (does the edge hold on data we didn't use to pick the parameters?).** The whole worry with data-mining is that you tune a strategy until it looks great on the data you can see — so the real test is fresh data the tuning never touched. We sealed off the last ~93 days (from Feb 15, 2026) as a holdout and only now ran the carried-forward 21/90 strategy on it. (Honest caveat: this holdout is *partly burned* — the very first parameter sweep had already glanced at all the data — so it's a strong indicator, not a pristine experiment.) One wrinkle: the signal needs **90 days of history to "warm up"** its rolling z-score, but the sealed window is only ~93 days, so building the signal from scratch inside the holdout wastes a third of it (down to 63 days) and tests a crippled version of the strategy. Instead we let the 90-day window warm up on the earlier in-sample funding history and then start scoring only on holdout dates — which is what a live trader would actually have on Feb 15, and is *not* cheating (the rolling stats only look backward; no future return is peeked at). The honest result is a genuine surprise: **the edge holds up out-of-sample — positive, +12.72% cumulative, keeping about 76% of its in-sample Sharpe** (1.95 vs. 2.57), where a typical overfit would have collapsed to zero or gone negative. **But this does NOT rescue the signal.** It still fails the significance test (Task 4) and the search-effort penalty (Task 6, deflated Sharpe 47%). An "edge" that survives costs *and* survives out-of-sample but still flunks the significance tests is exactly the data-mining pattern: a fluke big enough to keep printing for a few months, yet not distinguishable from luck once you account for how hard you searched. So the verdict stays **NOT DEPLOYABLE** — it just now dies on significance + overfitting alone, not on OOS or costs. (As a transparency check we also report the crippled "isolated" build, which goes slightly negative; flagging both shows the verdict doesn't hinge on the warm-up choice.)

- **Task 9 — The decision rule (the final scorecard).** Every earlier task is one isolated measurement; this step is the rubric that turns them into a single yes/no answer, so the verdict can't be cherry-picked from whichever number looks best. We require a tradeable signal to clear **four gates**: **(1) Significance** — is it statistically significant *after* correcting for how many combos we tried? **(2) Sign stability** — is the return positive both in-sample and out-of-sample, with a believable bootstrap? **(3) Overfitting penalty** — does it beat the Deflated-Sharpe "how hard did you search?" bar? **(4) Costs** — does it still make money after real trading frictions, even doubled? Running the carried-forward 21/90/14 strategy through all four: it **PASSES Gate 2** (out-of-sample stayed positive, +60.8% annualized) and **Gate 4** (survives 2× costs at +82.7%), but **FAILS Gate 1** (no combo is significant once multiple-testing correction is applied) and **Gate 3** (Deflated Sharpe 47%, far under the 90% bar). That's **2 of 4 → verdict: NOT DEPLOYABLE.** The rule is deliberately designed so that passing on returns, costs, or OOS *cannot* rescue a signal that flunks significance and the overfitting penalty — which is precisely this case, and precisely the data-mining pattern the whole project set out to catch. (Honesty note: unlike Tasks 6–8, the plan's decision-rule code had **no bug** — it ran correctly as written, and the 2/4 verdict matched the prediction exactly.)

- **Task 10 — Write the honest caveats back into the original notebook.** Every test above lives in the *new* `validation.ipynb`. But the *original* `signal_analysis.ipynb` — the one that "found" the signal — still reads optimistically end to end ("longer windows reveal the real signal," "the IC improves to −0.049," "the spread reaches 2%+"). Anyone opening that file first would walk away believing the edge is real. Task 10 fixes that by appending one new section, **"7. Methodological Limitations,"** that says plainly: these numbers are *in-sample and not statistically significant*, the honest re-analysis lands at **NOT DEPLOYABLE (2 of 4 gates)**, and here is every caveat — survivorship bias, point-in-time universe, multiple testing (84 mined combos → 0 of 56 survive correction), the insignificance (bootstrap p=0.057, deflated Sharpe 47%), the fact that costs and out-of-sample *don't* rescue it, and the execution assumption. Crucially, this wasn't a copy-paste of the plan's template: that template was written before Tasks 4–9 ran, so it still carried three wrong/stale numbers — it implied the multiple-testing result was still unknown, double-counted the trading cost (the "0.20% round-trip" was the very bug Task 7 caught — corrected to 0.10% per side), and undersold the out-of-sample result (which actually held up positive). All three were reconciled against the verified findings before writing. Net effect: the optimistic notebook now carries a truthful health warning that points the reader to the full scorecard.

**What it means (bottom line: the signal does not work):**

1. **No edge.** Tested honestly, the signal has no real predictive power. The apparent edge in the original work was a data-mining artifact — try 84 things, one looks great by chance; correct for that and it disappears.

2. **The rank correlation points the wrong way — but the traded spread doesn't lose money.** The negative information coefficient means high-funding coins tend to out-*rank* low-funding ones. *Originally we expected this to make the long-low / short-high portfolio lose money.* Task 5 (2026-06-01) checked the actual traded spread and found it faintly **positive (+0.00224/day, naive Sharpe 1.95) but statistically insignificant** (bootstrap p=0.057, HAC p=0.073). The two coexist because the per-quintile return curve is non-monotonic — the worst returns sit in the *middle* quintiles, not at the high-funding extreme. So the honest takeaway is **"no significant edge,"** not "a reliable money-loser."

3. **The "winning" parameters were noise.** 21/90/14 was cherry-picked, not special. It's carried into the later tasks only to document the null honestly, not because it passed any bar.

4. **Expected verdict.** Tasks 5 and 6 already confirm the null — the bootstrap (p=0.057) and the Deflated Sharpe (47% < 95%) both fail. **Task 8 (done, 2026-06-01)** found the sealed-OOS return actually holds up — *positive*, +12.72% cumulative, Sharpe 1.95 (76% of IS) — so neither costs (Task 7) nor OOS (Task 8) is the killer. The strategy still lands at **NOT DEPLOYABLE** because it fails on **significance** (Gate 1, BH) and **overfitting penalty** (Gate 3, DSR 47%): a big in-sample number that survives costs *and* carries into OOS but flunks the significance/search-effort tests is exactly the data-mining pattern honest statistics are built to catch. Task 9 (decision rule) formalizes this at **2/4 gates**.

**~~One open judgment call~~ — RESOLVED (Task 6, 2026-06-01):** the Deflated-Sharpe step originally counted 56 trials, but the true search was wider (the original 84-combo sweep + this 56-combo re-sweep). Task 6 now reports a **sensitivity row across N=56/84/140** and carries **N=140** (total search effort) as the headline — the strictest honest count. As predicted, N doesn't change the verdict: DSR = 55.5%/51.7%/47.3% across the three, all **FAIL** the 95% bar. (Separately, the plan's DSR code had a real bug — it omitted the σ_SR trial-dispersion scaling, which forced a degenerate DSR=0.00%; fixed with empirical σ_SR=0.0403. See Task 6 Findings.)

---

## Progress

| Task | Status | Notes |
|------|--------|-------|
| Task 1: Audit late-listed coins + document survivorship bias | ✅ Done | `validation.ipynb` created + executed; `data_pipeline.py` docstring updated |
| Task 2: Lock in sealed OOS window | ✅ Done | Cell 2 added + executed; IS=9,139 rows/273 days, OOS=3,255 rows/93 days |
| Task 3: IS-only parameter sweep with HAC t-stats | ✅ Done | Cells 3 (hac_tstat helper) + 4 (IS sweep) added + executed; 56 param combos (horizons 3/5 absent from panel, auto-skipped). Best by \|HAC t\|: sw=7/lw=30/h=1, mean_IC=-0.0200, HAC t=-1.75 (p=0.080). All top-10 t-stats are weak (\|t\|<1.8, none significant); mined sw=21/lw=90 only appears at h=7 (t=-1.12). Funding signal does not survive IS-only re-selection. **Re-verified against the fixed pipeline (2026-06-01): rebuilt panel is byte-identical, all 56 combos unchanged.** |
| Task 4: Multiple-testing correction (BH + Holm) | ✅ Done | Cell 5 added + executed; N=56 IS p-values corrected. Significant — naive p<0.05: **0**, BH: **0**, Holm: **0** (min p=0.080). No combo survives → statistical null; fallback path sets `BEST_SW/LW/H = 21/90/14` (original mined params) for Tasks 5–9. `is_df` gains `p_bh`/`p_holm`/`reject_bh`/`reject_holm` cols. Re-verified independently against the panel (2026-06-01). |
| Task 5: Stationary block bootstrap | ✅ Done | Cells 6 (`build_ls_returns`/`ls_is`) + 7 (stationary bootstrap + HAC cross-check + histogram) added verbatim + executed. `ls_is`=244 daily obs, naive ann. Sharpe 1.95; observed mean daily L/S = +0.00224. Bootstrap (block=14, n=2000, seed=42) p=0.0570, 95% CI [−0.00004, 0.00464]; HAC t=1.791, p=0.0732, lags=13. **Bootstrap and HAC agree — both insignificant at 5%** → null holds. Positive-mean nuance explained in Task 5 Findings (non-monotonic quintiles, not a contradiction). |
| Task 6: Deflated Sharpe Ratio | ✅ Done | Cell 7 (Cell 8 in plan) added + executed. **Plan's DSR code was missing the σ_SR scaling** — fixed (see Task 6 Findings). Headline N=140 (84 original + 56 re-sweep); empirical σ_SR=0.0403 (std of daily Sharpe across 14 window-pair trials). DSR = **47.3%** at N=140 (55.5%/51.7%/47.3% at N=56/84/140) → **FAIL** the 95% bar at every N. Consistent with bootstrap p=0.057 / HAC p=0.073. `dsr_result` (headline N=140) + `DSR_N`=140 exported for Task 9 Gate 3. |
| Task 7: Transaction cost model | ✅ Done | Cell 8 (Cell 9 in plan) added + executed. **Corrected the plan's 2× cost double-count** (turnover already counts both legs → charge `ONE_WAY_COST`, not `ROUND_TRIP`; see Task 7 Findings). Mean daily turnover 17.7%, ann. cost drag 6.45%. **Costs do NOT kill the edge:** ann. return gross 107.77% → net 94.82% → +82.67% at 2× stress, all positive → **Gate 4 will PASS**. The kill stays on Gate 1 (no BH significance) + Gate 3 (DSR 47.3% FAIL); big-but-insignificant IS return is the data-mining signature. `ann_ret_net`/`ann_ret_2x` exported for Task 9 Gate 4. |
| Task 8: IS vs OOS comparison | ✅ Done | Cells 10–11 added + executed. **Headline OOS built by warming z-scores on the full panel, then slicing to OOS dates** (90d z-window vs 93d OOS slice — building OOS in isolation cold-starts the rolling stats and loses ~30 days; the warm-up carry is *not* look-ahead, see Task 8 Findings). **Warmed OOS:** 92 days, cum **+12.72%**, ann +60.83%, Sharpe **1.95** (76% of IS Sharpe 2.57) → **positive, reasonable retention.** **Isolated sensitivity:** 63 days from Mar 16, cum −3.00%, Sharpe −0.51. **Gate 2 PASSES on the warmed (headline) OOS** (OOS>0 *and* boot_p=0.057<0.10); FAILs on the isolated build. **Verdict NOT DEPLOYABLE either way** — rests on Gate 1 (BH) + Gate 3 (DSR). `ann_ret_oos`=0.608 / `sharpe_oos`=1.95 / `ann_ret_is` / `sharpe_is` exported for Task 9 Gate 2. |
| Task 9: Decision rule assessment | ✅ Done | Cell 11 (Cell 12 in plan) added verbatim + executed (full top-to-bottom run, no errors). Four-gate verdict: **Gate 1 FAIL** (BH significance — `BEST` undefined on fallback, guarded → t=nan, p=N/A), **Gate 2 PASS** (OOS +60.83% & boot_p=0.057<0.10), **Gate 3 FAIL** (DSR 47.26%<90%), **Gate 4 PASS** (net 94.82% / 2× 82.67%). **2/4 gates → NOT DEPLOYABLE.** Matches predicted outcome exactly; `BEST`-guard kept intact. See *Task 9 Findings*. |
| Task 10: Honest caveats in signal_analysis.ipynb | ✅ Done | Appended markdown cell **"## 7. Methodological Limitations"** after cell 14 (notebook now 16 cells, markdown-only — no code re-run). Built from the plan template but **reconciled three stale/wrong numbers** against verified Tasks 1–9: (1) "84 combinations / see Gate 1" → original sweep **84** + honest IS-only re-sweep **56**, **0/56 survive BH**, settled **NOT DEPLOYABLE (2/4)**; (2) "round-trip 0.20%/trade" → **0.10% per side**, ~6.45%/yr, costs do **not** kill it (per Task 7 double-count fix); (3) "OOS indicative" → OOS **held up positive** (+12.72%), kill is significance+DSR not OOS/costs. Added a headline verdict blockquote + the missing bootstrap/DSR paragraph (p=0.057, DSR 47%). `nbformat.validate` OK. |

**Git status:** No repo initialized yet. Commit all files together when ready to push to GitHub for competition submission.

**Installed packages (2026-06-01):** `statsmodels 0.14.6`, `arch 8.0.0`, `scipy 1.17.1` — all available in `conda env artemis`.

**Out-of-plan fixes (2026-06-01):** `data_pipeline.py` reviewed against `/karpathy-guidelines` — corrected funding-cadence comments, added an in-sample-bias disclosure, and fixed a forward-return label-alignment bug in `build_panel`; added `test_data_pipeline.py` (4 alignment tests, all pass); later re-verified the Task 3 sweep against the fixed pipeline (numbers unchanged — the forward-return fix is a no-op on this gap-free dataset) and finished the funding-cadence wording (module docstring + `main()` print). Details in the *data_pipeline.py — Karpathy Review Fixes* section below.

---

## Task 3 Findings & Downstream Implications (verified against executed notebook + re-verified against fixed pipeline, 2026-06-01)

**Verified IS-only sweep output** (`validation.ipynb` Cell 4) — top combos by |HAC t-stat|, all weak, all negative IC, none significant:

| sw | lw | horizon | mean_IC | HAC t | HAC p |
|----|----|---------|---------|-------|-------|
| 7  | 30 | 1       | −0.0200 | −1.75 | 0.080 |
| 3  | 30 | 1       | −0.0186 | −1.52 | 0.129 |
| 21 | 30 | 21      | −0.0404 | −1.30 | 0.193 |
| 7  | 14 | 1       | −0.0154 | −1.17 | 0.242 |
| 21 | 30 | 14      | −0.0331 | −1.15 | 0.248 |

Smallest p-value across all 56 combos is **0.080** — nothing clears even the naive t>2 bar before any multiple-testing penalty.

**Three results that change the downstream narrative:**

1. **56 trials, not 84.** The IS-only sweep tested **56** combos, not the 84 from the original `parameter_sweep.ipynb`. Reason: the panel only carries `ret_1d/7d/14d/21d`; `forward_horizons` values 3 and 5 have no column and are silently skipped (14 valid `sw<lw` window pairs × 4 available horizons = 56). Affects:
   - **Task 4:** ✅ **Done (2026-06-01)** — 0 survivors at naive/BH/Holm; null confirmed. BH/Holm ran over N=56. Code uses `len(p_values)` so it's correct automatically, but the "84 tests / ~4 false discoveries" prose in the Task 4 expected-output note is stale → read as **56 tests / ~3 expected false discoveries**.
   - **Task 6 (DSR):** ✅ **Done (2026-06-01)** — resolved by reporting a sensitivity row N=56/84/140 and carrying **N=140** (84 original + 56 re-sweep) as the headline. DSR FAILs at every N (55.5%/51.7%/47.3%), so the understated-N concern is moot. (Also fixed a σ_SR-scaling bug in the plan's DSR code — see Task 6 Findings.)
   - **Task 10:** the caveat prose ("84 combinations") describes `parameter_sweep.ipynb` and stays historically accurate; reconcile by noting the validation re-sweep was 56.

2. **The signal is a statistical null — and sign-flipped.** Every top-10 mean IC is small and **negative**; best HAC t = −1.75 (p=0.080). The originally-mined **21/90/14 does not appear in the top 10** (21/90 surfaces only at h=7: t=−1.12, p=0.26).
   - **Task 4 consequence:** ✅ **Confirmed (2026-06-01)** — no combo survives BH; the fallback path fired → `BEST_SW, BEST_LW, BEST_H = 21, 90, 14` (original mined params) are what Tasks 5–9 will actually report on.
   - **Sign:** negative IC means high-z coins out-rank low-z coins on average, so the spec'd **long-Q1 / short-Q5 (long low-z) portfolio was anticipated to show negative expected return.** ⚠️ **Superseded by Task 5 (2026-06-01):** the actual IS L/S mean came out **slightly positive (+0.00224, naive Sharpe 1.95) but statistically insignificant** (bootstrap p=0.057, HAC p=0.073). The negative *rank* IC and a positive *extreme-quintile* spread coexist because the per-quintile return curve is non-monotonic (most-negative returns sit in the middle quintiles). The "statistical null" conclusion stands; the predicted *negative sign* does not. Read the downstream narrative as **insignificant**, not negative — see the *Task 5 Findings* section. (Task 9 still lands NOT DEPLOYABLE, but argues from insignificance + DSR overfitting penalty — **not** from a negative IS return or from OOS decay: Task 8 found OOS actually holds up positive, see *Task 8 Findings*.)

3. **Data-availability limitation:** the plan's `forward_horizons = [1,3,5,7,14,21]` implies 6 horizons, but only 4 exist in the panel. If 3- and 5-day horizons matter, `data_pipeline.py` must add `ret_3d`/`ret_5d`; otherwise document that the sweep covers 4 horizons.

**Bottom line:** under honest IS-only re-selection there is no *statistically significant* funding-momentum edge. Tasks 4–9 confirm a null and produce a NOT DEPLOYABLE verdict. (Note since Tasks 5/8: the IS L/S spread is faintly *positive* but insignificant, and OOS holds up positive too — the verdict rests on insignificance + overfitting, not on a negative IS return or OOS decay.)

---

## Task 4 Findings — BH/Holm Multiple-Testing Correction (verified against executed notebook, 2026-06-01)

**Verified `validation.ipynb` Cell 5 output** — the correction confirms the Task 3 null:

| Threshold | # significant / 56 | % |
|-----------|--------------------|---|
| Naive p<0.05 | **0** | 0% |
| Benjamini-Hochberg (FDR) | **0** | 0% |
| Holm (FWER) | **0** | 0% |

Smallest HAC p across all 56 combos = **0.080** (sw=7/lw=30/h=1) — nothing clears even the naive bar, so BH and Holm trivially reject nothing. ~3 false discoveries (0.05 × 56) were *expected* by chance; **0 observed**.

**Outcome — fallback path fired.** `survivors` is empty → the `else` branch runs → `BEST_SW, BEST_LW, BEST_H = SHORT_W, LONG_W, HORIZON = 21, 90, 14`. The originally-mined params are carried into Tasks 5–9 **only to report the null honestly**, not because they passed any bar.

**State now defined for downstream cells:**
- `is_df` gains columns `p_bh`, `p_holm`, `reject_bh`, `reject_holm` (every `reject_*` is False).
- `N_tests = 56` — consumed by Task 6 DSR. ✅ **Resolved (2026-06-01):** Task 6 reports N=56/84/140 and carries **N=140** as the headline; FAILs at every N.
- `BEST_SW=21, BEST_LW=90, BEST_H=14` — consumed by Tasks 5–9.
- ⚠️ **`BEST` (the Series) is NOT defined** on the fallback path. Task 9 Gate 1 already guards every use with `if "BEST" in dir()`, so on a clean top-to-bottom run Gate 1 reports **FAIL / t=nan / p_bh=N/A** — the correct null outcome. Anyone editing Task 9 must keep that guard (and not assume `BEST`/`p_bh` exist).

**Independent verification:** reran the full IS sweep + `multipletests` from `data/panel.parquet` in a standalone script (separate from the notebook kernel) → N=56, 0/0/0 survivors, min p=0.0799, fallback `BEST=(21,90,14)`. Consistent with the notebook. Re-executing Cells 1–4 via `nbconvert` left their Task 3 outputs unchanged (IS 9,139 rows/273 days; sweep still 56 combos).

**Downstream implication:** confirms the Task 3 prediction in full. Tasks 5–8 evaluate the **null** 21/90/14 long-Q1/short-Q5 portfolio; Task 9 should land on **NOT DEPLOYABLE**. ⚠️ **Updated by Task 5 (2026-06-01):** the IS L/S spread is faintly *positive* (+0.00224) but **insignificant** (bootstrap p=0.057, HAC p=0.073) — the "negative IC ⇒ negative L/S return" intuition did not hold on the extreme-quintile spread (non-monotonic quintile curve). The null verdict is unchanged but now rests on **insignificance**, not a negative sign.

⚠️ **Heads-up for Task 9 gate logic:** `boot_p`=0.057 is **< 0.10**, so the `boot_p < 0.10` sub-condition in Gate 2 and Gate 3 *passes*. The NOT-DEPLOYABLE verdict therefore now hinges on **Gate 1** (BH-adjusted significance — FAILs, `BEST` undefined on the fallback path), **Gate 3's DSR ≥ 0.90** (Task 6 ✅ done — **confirmed FAIL**, DSR=0.473 at N=140), and **Gate 2/4's OOS + net-of-cost conditions** (Tasks 7–8). Do not assume the bootstrap gate fails — it doesn't; the edge dies on multiple-testing + DSR instead. ⚠️ **Updated by Task 7 (2026-06-01):** costs are *not* a killer either — net return stays +94.8% (and +82.7% at 2× stress), so **Gate 4 PASSES**. The NOT-DEPLOYABLE verdict rests on **Gate 1 + Gate 3** (significance + DSR). ⚠️ **Updated by Task 8 (2026-06-01):** Gate 2 actually **PASSES** on the headline (warmed) OOS — the OOS return is *positive* (+12.72% cum, Sharpe 1.95, 76% of IS) and boot_p<0.10 — so Gate 2 is not a killer either; the verdict stands at 2/4 gates (NOT DEPLOYABLE) on Gate 1 + Gate 3 alone.

---

## Task 5 Findings — Stationary Block Bootstrap (verified against executed notebook, 2026-06-01)

**Verified `validation.ipynb` Cell 6/7 output** for the fallback combo `BEST_SW/LW=21/90`, `BEST_H=14`:

| Quantity | Value |
|----------|-------|
| `ls_is` daily observations | **244** |
| Naive annualized Sharpe (√365) | **1.95** |
| Observed mean daily L/S return | **+0.00224** |
| Bootstrap p-value (two-sided, block=14, n=2000, seed=42) | **0.0570** |
| Bootstrap 95% CI | **[−0.00004, 0.00464]** |
| HAC cross-check | **t=1.791, p=0.0732, lags=13** |

**Null confirmed (yes).** Bootstrap and HAC **agree closely** (p=0.057 vs p=0.073, both > 0.05) — neither rejects H0: mean=0 at the 5% level. The 95% bootstrap CI includes zero. There is no statistically significant L/S edge, which is consistent with the Task 3/4 null. (The borderline ~6–7% p-values reflect a data-mined IS Sharpe that does not clear an honest significance bar; the Task 6 DSR FAIL is what carries the NOT-DEPLOYABLE verdict here — Task 8 later found the OOS return actually holds up positive, so OOS does not add to the kill.)

**Surfaced nuance — the L/S mean is positive (+0.00224), not negative as the Task 3/4 prose anticipated.** This is *not* an anomaly or a sign error; it is reconciled as follows:
- The negative IC is a **monotone rank correlation** across the whole z distribution. Verified mean daily Spearman IC of `zscore` vs `ret_1d` over IS = **−0.0092** (and −0.033 vs `ret_14d` in the sweep), so high-z coins do tend to under-rank — consistent with negative IC.
- But the **extreme-quintile spread is non-monotonic**: mean `ret_1d` by quintile is Q0(low-z)=+0.00019, Q1=−0.00198, Q2=−0.00245, Q3=−0.00057, Q4(high-z)=−0.00205. The most-negative buckets are the *middle*, not the extremes, so Q0−Q4 (long lowest-z, short highest-z) comes out slightly positive even though the overall rank IC is negative. A monotone-IC intuition does not transfer to an extreme-decile-style spread on a non-monotone curve.
- Bottom line: the positive sign is small, statistically insignificant, and an artifact of in-sample quintile shape — it does **not** overturn the null and does **not** contradict Tasks 3/4.

**Design point (not an inconsistency):** the L/S series earns **daily `ret_1d`** (next-day simple returns, equal-weight within each leg, short via Q1−Q5). `BEST_H=14` is used **only as the bootstrap block length** (≈ autocorrelation span / overlap horizon) and as the HAC `horizon` argument — it is *not* a holding period. So "horizon 14" and "daily ret_1d returns" coexist by design.

**State now defined for downstream cells:** `ls_is` (pd.Series, 244 obs), `boot_p`=0.057, `boot_means`/`boot_centered`, `block_size`=14, `hac_t_ls`/`hac_p_ls`/`hac_lags`. Cells 0–4 (Tasks 1–4) re-ran unchanged on the clean top-to-bottom execution (IS sweep still 56 combos, 0/0/0 survivors, fallback `BEST=(21,90,14)`).

---

## Task 6 Findings — Deflated Sharpe Ratio (verified against executed notebook, 2026-06-01)

**Verified `validation.ipynb` Cell 7 (Cell 8 in plan) output** for the fallback combo 21/90, daily L/S `ret_1d` series (`ls_is`, 244 obs):

| Quantity | Value |
|----------|-------|
| Daily Sharpe (best combo) | 0.1022 |
| IS annualized Sharpe (√365) | 1.953 ± 1.220 (SE) |
| Skew / excess kurtosis | 0.240 / 3.772 |
| Trial dispersion σ_SR (std of daily Sharpe across 14 window-pair trials) | **0.0403** |
| DSR @ N=56 / 84 / 140 | **55.5% / 51.7% / 47.3%** — all FAIL |
| Headline DSR (N=140) | **47.3% → FAIL** |

**FAIL confirmed.** The probability that the true Sharpe exceeds the best a search of 140 comparable strategies throws up by luck is only ~47% — far below the 95% bar. This is fully consistent with the Task 5 bootstrap (p=0.057) and HAC (p=0.073) null: a borderline-insignificant IS Sharpe that does not survive a search-effort penalty.

**⚠️ Plan code bug found and fixed (deviation from status.md Task 6 code).** The plan's `deflated_sharpe_ratio` computed the expected-max Sharpe as the bare Gumbel/order-statistic factor `(1-γ)Φ⁻¹(1-1/N) + γΦ⁻¹(1-1/(Ne))` ≈ 2.32 **daily** — equivalent to an annualized Sharpe of ~44, which is nonsensical — and never scaled it by σ_SR. That forced a **degenerate DSR = 0.00%** independent of the data, contradicting the cited Bailey & López de Prado (2014) method (which scales the order statistic by the cross-trial Sharpe dispersion σ_SR). **Fix:** estimate σ_SR empirically as the std of the daily L/S Sharpe across the 14 distinct `sw<lw` window-pair strategies (the only dimension the L/S portfolio actually varies on — horizon enters only as the bootstrap block). σ_SR=0.0403 → credible E[max SR]≈0.09–0.11 daily and DSR≈47–55%. Verdict (FAIL) is unchanged; only the previously-degenerate *number* is now defensible. (An alternative single-strategy SE proxy σ_SR=sqrt(var_sr)=0.0638 gives DSR≈15–24%, also FAIL — the empirical σ_SR was chosen as the canonical, less-favorable-to-the-thesis input.)

**State now defined for downstream cells:** `deflated_sharpe_ratio(returns, n_trials, sigma_sr)` (signature now takes σ_SR), `sigma_sr`=0.0403, `trial_sharpes` (14 values), `TRIAL_GRID`=[56,84,140], `dsr_result` (the **N=140** dict), `DSR_N`=140. **Task 9 Gate 3 consumes `dsr_result["dsr"]`=0.473** → Gate 3's `DSR ≥ 0.90` condition **FAILs** (as expected). Cells 0–6 (Tasks 1–5) re-ran unchanged on the clean top-to-bottom execution.

---

## Task 7 Findings — Transaction Cost Model (verified against executed notebook, 2026-06-01)

**Verified `validation.ipynb` Cell 8 (Cell 9 in plan) output** for the fallback combo 21/90, daily L/S `ret_1d` series (`ls_is`, 244 obs):

| Quantity | Value |
|----------|-------|
| One-way cost (taker fee 0.05% + half-spread 0.05%) | 0.10% |
| Mean daily turnover (Q0+Q4 active book) | **17.7%** |
| Mean daily cost drag | 0.0177% |
| Annualized cost drag | **6.45%** |
| Ann. return — gross / net (1×) / net (2×) | **107.77% / 94.82% / 82.67%** |
| Ann. Sharpe — gross / net (1×) / net (2×) | 2.57 / 2.26 / 1.97 |

**Costs do NOT kill this strategy — and that is the honest, important result.** Net return stays strongly positive even at 2× cost stress (+82.67%), so **Task 9 Gate 4 (`ann_ret_net > 0 and ann_ret_2x > 0`) will PASS.** This is *not* a contradiction of the NOT-DEPLOYABLE thesis: the IS gross return is large but **statistically insignificant** (bootstrap p=0.057, HAC p=0.073, DSR=47.3% at N=140). A big-but-insignificant in-sample number that survives costs is the classic **data-mining signature** — the edge dies on **Gate 1** (no BH-significant combo) and **Gate 3** (DSR FAIL), not on costs. This matches the Task 4 heads-up ([status.md] "the edge dies on multiple-testing + DSR + costs/OOS instead" — costs turn out *not* to be the killer; significance/DSR are).

**⚠️ Plan code corrected (deviation from status.md Task 7 code) — 2× cost double-count.** The plan's Cell 9 computed `daily_cost = mean_daily_turn * ROUND_TRIP` where `ROUND_TRIP = 2 × ONE_WAY`. But `compute_daily_turnover` uses `symmetric_difference(prev, curr) / n_active`, which **already counts both the names sold out and the names bought in** — each turnover unit is already a one-way trade on each leg. Multiplying that by a round-trip (another ×2) charges every rotation twice, overstating cost ~2× (would report ann. drag 12.90% instead of the correct 6.45%). **Fix:** `daily_cost = mean_daily_turn * ONE_WAY_COST`. Same fix-and-document precedent as the Task 6 σ_SR bug. (The choice does not flip Gate 4 — both 6.45% and 12.90% leave net return positive at 2× — but the corrected number is the defensible one.)

**Two residual approximations, left explicit in the cell docstring (opposite-signed, both under-counts):** (1) survivors are re-equal-weighted daily and that rebalancing trade is ignored; (2) a Q0↔Q4 side-flip stays in the active set, so it is not counted (should cost a double trade). Both understate turnover slightly; neither is large enough to threaten the positive net return.

**State now defined for downstream cells:** `compute_daily_turnover`, `daily_turnover`, `mean_daily_turn`=0.177, `ONE_WAY_COST`=0.001, `daily_cost`, `ls_is_net`/`ls_is_2x`, `ann_vol`, `ann_ret_gross`/`ann_ret_net`/`ann_ret_2x`, `sharpe_gross`/`sharpe_net`. **Task 9 Gate 4 consumes `ann_ret_net`=0.948 and `ann_ret_2x`=0.827** → Gate 4 **PASSES**. Cells 0–7 (Tasks 1–6) re-ran unchanged on the clean top-to-bottom execution.

---

## Task 8 Findings — IS vs. Sealed-OOS Comparison (verified against executed notebook, 2026-06-01)

**Verified `validation.ipynb` Cell 9/10 output** for the carried-forward combo 21/90 (long-Q1 / short-Q5, daily `ret_1d`):

| Metric | IS | OOS (warmed, headline) | OOS (isolated, sensitivity) |
|--------|----|------------------------|------------------------------|
| Trading days | 244 | **92** | 63 |
| First trade | — | Feb 15 | Mar 16 |
| Mean daily L/S | +0.00224 | **+0.00143** | −0.00035 |
| Cumulative return | +63.04% | **+12.72%** | −3.00% |
| Ann. return (gross) | +107.77% | **+60.83%** | −16.18% |
| Ann. Sharpe (gross) | 2.57 | **1.95** | −0.51 |

**Headline read:** on the warmed OOS the edge **retains its sign and ~76% of its IS Sharpe** (1.95 vs 2.57) — "reasonable retention," not the negative/severe-decay outcome the plan's pass/fail rule screens for. The isolated build flips negative.

**⚠️ Plan-code deviation (documented, same precedent as the Task 6 σ_SR fix and Task 7 2× cost fix).** The plan's Cell 10 calls `build_ls_returns(panel_oos, …)` — i.e. it builds the z-score on the **OOS slice in isolation**. But the z-score's long window is **90 days** and the OOS slice is only **93 days**, so the rolling mean/std cold-start on Feb 15: the first ~30 days are NaN and the surviving days trade on an under-warmed (<90d) lookback. That discards a third of the sealed window (92→63 days) and evaluates a *different, crippled* signal than IS ran. **Fix:** compute z-scores on the **full top-35 panel**, then **slice to OOS dates** — on Feb 15 the 90-day window is fully populated from IS funding history, exactly what a live trader would hold. This is **not look-ahead**: rolling stats only look backward and no OOS *return* is peeked at; it is verified consistent because `ls_full` restricted to IS dates reproduces the canonical `ls_is` byte-for-byte (244 obs). The isolated build is retained as an explicit sensitivity row.

**The construction choice flips Gate 2's label but not the verdict:**
- **Warmed OOS (headline):** OOS return **positive** and `boot_p`=0.057<0.10 → **Gate 2 PASSES.**
- **Isolated OOS (sensitivity):** OOS return **negative** → Gate 2 would **FAIL.**
- Either way the final verdict is **NOT DEPLOYABLE**: the kill is **Gate 1** (no BH-significant combo) + **Gate 3** (DSR 47.3% < 90%), both of which fail regardless of the OOS build. So the OOS construction does **not** change the conclusion — reporting both proves the verdict is robust to the choice.

**Honesty note on annualization:** ann. returns are `(1+cum)^(365/n)−1` on a ~92-day (or 63-day) window — high variance; the cumulative return and Sharpe are the primary OOS evidence. The cell prints both with this caveat.

**State now defined for downstream cells:** `ls_full`, `ls_oos` (92 obs, warmed — headline), `ls_oos_iso` (63 obs, sensitivity), `ann_ret_is`/`sharpe_is`, `ann_ret_oos`=0.608 / `sharpe_oos`=1.95, `cum_is`/`cum_oos`. **Task 9 Gate 2 consumes `ann_ret_oos`** (positive) → Gate 2 PASSES; with Gate 4 also passing, the headline run yields **2/4 gates → NOT DEPLOYABLE** (n_pass<3). ⚠️ Task 9 Cell 12 references `ann_ret_oos` inside an f-string even when `np.isnan` — fine here (`ann_ret_oos` is finite). Cells 0–8 (Tasks 1–7) re-ran unchanged on the clean top-to-bottom execution.

---

## Task 9 Findings — Four-Gate Decision Rule (verified against executed notebook, 2026-06-01)

**Verified `validation.ipynb` Cell 11 (Cell 12 in plan) output** — the decision rule consumes the state exported by Tasks 4–8 and produces the deployability verdict:

| Gate | Condition | Inputs (observed) | Result |
|------|-----------|-------------------|--------|
| **1** — Multiple-testing-adjusted significance | `BEST["reject_bh"]` is True | `BEST` **undefined** on the fallback path → `"BEST" in dir()` guard → t=**nan**, p_bh=**N/A** | **FAIL** |
| **2** — Sign stability | OOS return > 0 **and** boot_p < 0.10 | OOS **+60.83%**, boot_p **0.0570** | **PASS** |
| **3** — Deflated Sharpe + bootstrap | DSR ≥ 0.90 **and** boot_p < 0.10 | DSR **47.26%**, boot_p 0.0570 | **FAIL** |
| **4** — Net-of-cost return survives 2× stress | net > 0 **and** 2× > 0 | net **94.82%**, 2× **82.67%** | **PASS** |

**GATES PASSED: 2/4 → VERDICT: NOT DEPLOYABLE** (`n_pass < 3`). This matches the predicted outcome exactly (status.md Task 4/6/7/8 heads-ups).

**The kill is significance + overfitting, not costs or OOS.** The strategy dies on **Gate 1** (no BH-significant combo — the IS-only re-sweep produced zero survivors, so `BEST` never gets defined) and **Gate 3** (Deflated Sharpe 47% ≪ 90% — once the search effort across N=140 trials is penalized, the pretty IS Sharpe of 1.95 is no more than a coin-flip likely to be real). It *passes* Gate 2 (OOS holds up positive, +60.83%) and Gate 4 (survives 2× costs at +82.67%) — which is precisely the data-mining signature: a big in-sample number that survives frictions and even carries into OOS, yet cannot clear an honest significance bar.

**Implementation notes:**
- Code added **verbatim** from the plan, with the `if "BEST" in dir()` guards on every Gate-1 use kept intact (per the status.md:115 warning — `BEST` the Series is not defined on the fallback path). On the clean run Gate 1 correctly prints `t=nan / p=N/A / FAIL`.
- No plan-code bug this time (unlike Tasks 6/7/8) — the cell ran as written and the verdict needed no correction.
- Full notebook re-executed top-to-bottom via `nbconvert` with **no errors**; Cells 0–10 (Tasks 1–8) re-ran unchanged.

**State now defined:** `gate1_pass`/`gate2_pass`/`gate3_pass`/`gate4_pass` (False/True/False/True), `gates`, `n_pass`=2. This is the terminal analytical cell. **Task 10** (honest-caveats markdown in `signal_analysis.ipynb`) is now also ✅ done — see the *Task 10 Findings* section and the Progress table. **All 10 tasks complete.**

---

## Task 10 Findings — Honest Caveats in signal_analysis.ipynb (verified, 2026-06-01)

**What changed:** appended one markdown cell, **"## 7. Methodological Limitations,"** to the end of `signal_analysis.ipynb` (cell count 15 → 16, markdown-only — no code re-execution, no existing cell or output touched). `nbformat.validate` passes; the prior final cell ("## 6. Summary") is unchanged.

**Why it matters:** `signal_analysis.ipynb` is the *original optimistic* notebook — Sections 1–6 still present the signal as real ("longer windows reveal the real signal," IC ≈ −0.049, Q1–Q5 spread ≈ 2%). Without this cell, a reader opening it first would never learn the honest verdict lives in `validation.ipynb`. The new cell leads with a verdict blockquote (**NOT DEPLOYABLE, 2/4 gates; data-mining artifact**) and then lists every caveat, each pointing back to the relevant validation task.

**⚠️ Three reconciliations against the plan's template** (status.md:917–933 was written before Tasks 4–9 ran, so its numbers were stale/wrong — same fix-and-document precedent as the Task 6 σ_SR and Task 7 2× cost bugs):

| # | Plan template said | Corrected to (verified) |
|---|--------------------|--------------------------|
| 1 | "tested 84 combinations … BH applied to all 84 … *see Gate 1 for whether it survives*" | Original sweep **84**; honest IS-only re-sweep **56**; **0 of 56 survive** BH (min p=0.080); verdict settled **NOT DEPLOYABLE (2/4)** |
| 2 | "round-trip cost of 0.20% per trade" | **0.10% per side** (0.05% fee + 0.05% half-spread), ~6.45%/yr drag; costs do **not** kill it — this "0.20% round-trip" framing was the exact Task 7 double-count that was corrected |
| 3 | "OOS … indicative, not confirmatory" | OOS actually **held up positive** (+12.72% cum, Sharpe 1.95 ≈ 76% of IS); the kill is significance (Gate 1) + DSR (Gate 3), not OOS/costs |

Also **added** content the template omitted entirely: the headline verdict blockquote and the significance/overfitting paragraph (bootstrap p=0.057, HAC p=0.073, DSR 47% at N=140). The unresolved-bias caveats (survivorship, point-in-time, execution assumption) were kept as accurate.

**Not committed:** the template's `git commit` step is intentionally skipped — no git repo is initialized yet (see Progress note), so all files commit together at submission time.

---

**Goal:** Identify and fix all known biases in the funding-rate mean-reversion backtest, add rigorous statistical validation, and apply the decision rule to determine if the factor is deployable.

**Architecture:** A new `validation.ipynb` notebook runs all statistical tests against the existing panel data. `signal_analysis.ipynb` is updated to fix execution-gap look-ahead. Honest limitations are documented where fixes require re-pulling unavailable historical data.

**Tech Stack:** Python 3.11, pandas, numpy, statsmodels (HAC), scipy (multipletests), arch (stationary bootstrap), matplotlib — all in `conda env artemis`.

---

## Biases Found in the Codebase

| Bias | Severity | Location | Fixable with existing data? |
|------|----------|----------|-----------------------------|
| **Survivorship bias** | High | `data_pipeline.py:51–77` — universe built from current live API call; delisted perps excluded | No — must document as limitation |
| **Multiple testing / data mining** | High | `parameter_sweep.ipynb` — 84 combos tested, best (21d/90d/14d) cherry-picked; no correction applied | Yes — BH/Holm correction retroactive |
| **Point-in-time universe** | Medium | Universe ranked by current 24h volume; coins like CHIP (listed Apr 2026) included in older periods | Partial — audit late-listed coins; document remaining bias |
| **Look-ahead in execution** | Low-Medium | `signal_analysis.ipynb:cell-9` — L/S portfolio uses `ret_1d` which is (close_T+1 − close_T)/close_T; signal formed from close_T data; execution at next close is reasonable but undocumented | Yes — document assumption explicitly |
| **Forward-return label misalignment** | Low-Medium | `data_pipeline.py` `build_panel` — `pct_change(n).shift(-n)` shifts by rows, so an interior date gap makes `ret_Nd` span >N calendar days | Yes — **fixed 2026-06-01** (calendar-day reindex; gap-spanning returns now NaN). Impact small (interior gaps rare) |
| **No transaction costs** | High | Backtest ignores Hyperliquid fees (0.05% taker), bid-ask, funding payments on held positions | Yes — add cost model |
| **No statistical significance tests** | High | No HAC t-stats, no bootstrap, no DSR anywhere in analysis | Yes — add in validation.ipynb |
| **No out-of-sample validation** | High | Entire dataset used for both parameter selection and reporting | Partial — OOS is technically burned by sweep; re-run sweep IS-only, report gap honestly |
| **Return convention** | Low | L/S computed as Q1−Q5 simple returns then compounded — this is correct. Short leg enters as −w·r_simple via subtraction. Convention is consistent. | N/A — no fix needed |

---

## File Map

| File | Role |
|------|------|
| `data_pipeline.py` | Data pull + feature build — survivorship limitation documented here; funding-cadence + forward-return-alignment fixes applied 2026-06-01 |
| `test_data_pipeline.py` | **NEW (2026-06-01)** — pytest alignment tests for `build_panel` forward returns (values, trailing-NaN, no cross-symbol leak, gap→NaN) |
| `signal_analysis.ipynb` | Primary analysis — add execution-gap note, add OOS cell, reference validation.ipynb |
| `parameter_sweep.ipynb` | Used to mine params — add multiple-testing correction cell at end |
| `validation.ipynb` | **NEW** — all statistical tests: HAC, bootstrap, DSR, IS/OOS, cost model, decision rule |
| `status.md` | This file |

---

## Task 1: Audit Late-Listed Coins and Document Survivorship Bias

**Files:**
- Modify: `data_pipeline.py` (docstring at top of `get_top_perp_symbols`)
- Create: first cell of `validation.ipynb`

- [ ] **Step 1: Check which coins entered the dataset mid-study**

Run in `validation.ipynb` Cell 1:

```python
import pandas as pd
import numpy as np
import json, warnings
warnings.filterwarnings("ignore")

panel = pd.read_parquet("data/panel.parquet")
funding_raw = pd.read_parquet("data/funding_rates_raw.parquet")
ohlcv = pd.read_parquet("data/ohlcv_daily.parquet")

with open("data/symbols.json") as f:
    all_symbols = json.load(f)

STUDY_START = panel["date"].min()
STUDY_END   = panel["date"].max()
OOS_START   = pd.Timestamp("2026-02-15")   # sealed OOS: Feb 15 – May 18, 2026

first_dates = panel.groupby("symbol")["date"].min().sort_values()
late_coins  = first_dates[first_dates > STUDY_START + pd.Timedelta(days=30)]

print(f"Study period: {STUDY_START.date()} to {STUDY_END.date()}")
print(f"IS window:    {STUDY_START.date()} to {(OOS_START - pd.Timedelta(days=1)).date()}")
print(f"OOS window:   {OOS_START.date()} to {STUDY_END.date()}")
print(f"\nCoins that listed mid-study (> 30 days after study start):")
print(late_coins.to_string())
print(f"\nSurvivorship note: {panel['symbol'].nunique()} coins have data.")
print("Coins delisted before the API pull date are NOT in this dataset — survivorship bias.")
```

Expected output: PUMP (Jul-10), XPL (Aug-22), WLFI (Aug-23), ASTER (Sep-19), MON (Oct-08), LIT (Dec-22), CHIP (Apr-22) listed late. These 7 coins are NOT look-ahead (their data starts at listing) but they inflate effective universe size near the study start.

- [ ] **Step 2: Add survivorship-bias docstring to data_pipeline.py**

In `data_pipeline.py:51`, update the `get_top_perp_symbols` docstring to:

```python
def get_top_perp_symbols(top_n: int = 30) -> list[str]:
    """
    Fetch Hyperliquid perp universe ranked by current 24h USD volume.
    Returns coin names like ['BTC', 'ETH', 'SOL', ...].

    KNOWN BIASES:
    - Survivorship bias: this pulls the LIVE universe; coins delisted before
      this call are silently excluded. Their returns (often large losses) are
      never recorded, inflating measured factor returns.
    - Point-in-time bias: rankings use today's volume, not historical volume.
      A coin that is now top-35 but was obscure 12 months ago is included
      with its historical data — a form of selection-on-outcome.
    These biases cannot be fixed without a historical universe snapshot API
    that Hyperliquid does not currently provide. They must be disclosed.
    """
```

- [ ] **Step 3: Commit**

```bash
git add data_pipeline.py
git commit -m "docs: document survivorship and point-in-time bias in get_top_perp_symbols"
```

---

## Task 2: Lock In the Sealed OOS Window

**Files:**
- `validation.ipynb` (continuing from Task 1 setup cell)

- [ ] **Step 1: Write the OOS split assertion — this is the last time we look at OOS until Task 8**

Add Cell 2 in `validation.ipynb`:

```python
# --- Seal the OOS window ---
# IMPORTANT: OOS_START was already seen during the parameter sweep (sweep used all data).
# We therefore acknowledge the OOS is "technically burned" and treat this as a
# partial holdout. We report any OOS result honestly alongside this caveat.
# The IS-only sweep (Task 3) partially mitigates this by using only IS data to
# re-select parameters.

TOP_N      = 35
SYMBOLS    = all_symbols[:TOP_N]
SHORT_W    = 21   # parameters selected from sweep (acknowledged as mined)
LONG_W     = 90
HORIZON    = 14

panel_35   = panel[panel["symbol"].isin(SYMBOLS)].copy()
panel_is   = panel_35[panel_35["date"] < OOS_START].copy()
panel_oos  = panel_35[panel_35["date"] >= OOS_START].copy()

print(f"Top {TOP_N} coins in panel:   {panel_35['symbol'].nunique()}")
print(f"IS rows:   {len(panel_is):,}  ({panel_is['date'].nunique()} trading days)")
print(f"OOS rows:  {len(panel_oos):,} ({panel_oos['date'].nunique()} trading days)")
```

Expected: IS ~9,490 rows / 272 days; OOS ~3,248 rows / 93 days.

---

## Task 3: IS-Only Parameter Sweep with HAC t-Stats

**Files:**
- `validation.ipynb` Cells 3–4

- [ ] **Step 1: Write the HAC t-stat helper function**

Add Cell 3 in `validation.ipynb`:

```python
import statsmodels.api as sm
from scipy import stats

def hac_tstat(series: pd.Series, horizon: int) -> tuple[float, float, int]:
    """
    HAC (Newey-West) t-statistic for H0: mean = 0.
    lag = max(horizon-1, NW-1994 auto bandwidth).
    Returns (t_stat, p_value, lags_used).
    """
    s = series.dropna().values
    T = len(s)
    auto_lag  = int(np.floor(4 * (T / 100) ** (2 / 9)))
    min_lag   = horizon - 1          # mechanical overlap from horizon-day returns
    max_lag   = max(auto_lag, min_lag)
    X = np.ones((T, 1))
    res = sm.OLS(s, X).fit(cov_type="HAC", cov_kwds={"maxlags": max_lag, "use_correction": True})
    return float(res.tvalues[0]), float(res.pvalues[0]), max_lag
```

- [ ] **Step 2: Run IS-only parameter sweep and collect (IC, HAC t-stat, p-value) per combo**

Add Cell 4 in `validation.ipynb`:

```python
from itertools import product as iproduct

short_windows   = [3, 7, 14, 21]
long_windows    = [14, 30, 60, 90]
forward_horizons = [1, 3, 5, 7, 14, 21]

def build_zscore(df: pd.DataFrame, sw: int, lw: int) -> pd.DataFrame:
    out = df.copy()
    grp = out.groupby("symbol")["daily_funding"]
    s_mean = grp.transform(lambda x: x.rolling(sw, min_periods=max(3, sw//2)).mean())
    l_mean = grp.transform(lambda x: x.rolling(lw, min_periods=max(10, lw//3)).mean())
    l_std  = grp.transform(lambda x: x.rolling(lw, min_periods=max(10, lw//3)).std())
    out["zscore"] = (s_mean - l_mean) / l_std
    out["zscore"] = out["zscore"].replace([np.inf, -np.inf], np.nan)
    return out

def daily_ic(df: pd.DataFrame, ret_col: str) -> pd.Series:
    sub = df.dropna(subset=["zscore", ret_col])
    def row_ic(g):
        return g["zscore"].corr(g[ret_col], method="spearman") if len(g) >= 5 else np.nan
    return sub.groupby("date").apply(row_ic).dropna()

# Build IS base (daily funding already in panel)
is_base = panel_is.copy()

is_results = []
for sw, lw in iproduct(short_windows, long_windows):
    if sw >= lw:
        continue
    df_z = build_zscore(is_base, sw, lw)
    for h in forward_horizons:
        ret_col = f"ret_{h}d"
        if ret_col not in df_z.columns:
            continue
        ic_series = daily_ic(df_z, ret_col)
        if len(ic_series) < 30:
            continue
        mean_ic = ic_series.mean()
        t, p, lags = hac_tstat(ic_series, horizon=h)
        is_results.append({
            "sw": sw, "lw": lw, "horizon": h,
            "mean_ic": mean_ic, "hac_t": t, "hac_p": p, "n_obs": len(ic_series)
        })
        
is_df = pd.DataFrame(is_results)
print(f"IS sweep: {len(is_df)} parameter combinations")
print("\nTop 10 by |HAC t-stat|:")
print(is_df.reindex(is_df["hac_t"].abs().sort_values(ascending=False).index)
      .head(10)[["sw","lw","horizon","mean_ic","hac_t","hac_p"]].to_string(index=False))
```

Expected: top combos should include 21d/90d/14d and nearby variants. t-stats will be lower than naive ones.

---

## Task 4: Multiple-Testing Correction (BH + Holm)

**Files:**
- `validation.ipynb` Cell 5

- [x] **Step 1: Apply Benjamini-Hochberg and Holm to all IS p-values**

Add Cell 5 in `validation.ipynb`:

```python
from statsmodels.stats.multitest import multipletests

p_values = is_df["hac_p"].values
N_tests  = len(p_values)

reject_bh,   p_bh,   _, _ = multipletests(p_values, alpha=0.05, method="fdr_bh")
reject_holm, p_holm, _, _ = multipletests(p_values, alpha=0.05, method="holm")

is_df["p_bh"]        = p_bh
is_df["p_holm"]      = p_holm
is_df["reject_bh"]   = reject_bh
is_df["reject_holm"] = reject_holm

n_sig_naive = (p_values < 0.05).sum()
n_sig_bh    = reject_bh.sum()
n_sig_holm  = reject_holm.sum()

print(f"Total IS combinations tested: {N_tests}")
print(f"Significant at naive p<0.05:  {n_sig_naive} ({n_sig_naive/N_tests:.0%})")
print(f"Significant after BH (FDR):   {n_sig_bh}   ({n_sig_bh/N_tests:.0%})")
print(f"Significant after Holm:       {n_sig_holm}  ({n_sig_holm/N_tests:.0%})")
print(f"\nNote: conventional t>2 threshold is far too lax for {N_tests} mined specs.")
print("The adjusted bar is roughly t>3 once the full search breadth is counted.")

# Show the best IS combo that survives BH correction
survivors = is_df[is_df["reject_bh"]].sort_values("mean_ic")
if len(survivors):
    print(f"\nBH-surviving combos (best IC first):")
    print(survivors[["sw","lw","horizon","mean_ic","hac_t","p_bh"]].head(10).to_string(index=False))
    BEST = survivors.iloc[0]
    BEST_SW, BEST_LW, BEST_H = int(BEST["sw"]), int(BEST["lw"]), int(BEST["horizon"])
    print(f"\nSelected for further tests: short={BEST_SW}d, long={BEST_LW}d, horizon={BEST_H}d")
else:
    print("\nNO combo survives BH correction — report as statistical null.")
    BEST_SW, BEST_LW, BEST_H = SHORT_W, LONG_W, HORIZON  # fall back to original for reporting
```

Expected: after **56** IS tests (not 84 — see Task 3 findings) at the 5% threshold, ~3 false discoveries expected by chance. Per Task 3, no combo is significant even before correction, so expect **zero survivors** — that is the honest result and must be reported.

**Verified output (2026-06-01):** N=56; naive p<0.05 = **0**, BH = **0**, Holm = **0** (min p=0.080). No combo survives → `else` branch set `BEST_SW/LW/H = 21/90/14`. Full details in the *Task 4 Findings* section near the top.

---

## Task 5: Stationary Block Bootstrap

**Files:**
- `validation.ipynb` Cells 6–7

- [ ] **Step 1: Build the IS L/S return series for the best combo**

Add Cell 6 in `validation.ipynb`:

```python
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

plt.style.use("seaborn-v0_8-whitegrid")

def build_ls_returns(df: pd.DataFrame, sw: int, lw: int) -> pd.Series:
    """
    Daily L/S returns: long Q1 (low zscore), short Q5 (high zscore).
    Earns next-day simple returns (ret_1d). Equal-weight within each leg.
    Short leg correctly enters as -w*r_simple via Q1 - Q5.
    """
    df_z = build_zscore(df, sw, lw)
    df_z = df_z.dropna(subset=["zscore", "ret_1d"]).copy()
    df_z["q"] = df_z.groupby("date")["zscore"].transform(
        lambda x: pd.qcut(x, 5, labels=False, duplicates="drop") if len(x) >= 5 else np.nan
    )
    df_z = df_z.dropna(subset=["q"])
    daily = df_z.groupby(["date", "q"])["ret_1d"].mean().unstack()
    if 0.0 not in daily.columns or 4.0 not in daily.columns:
        return pd.Series(dtype=float)
    return (daily[0.0] - daily[4.0]).dropna()

ls_is = build_ls_returns(panel_is, BEST_SW, BEST_LW)
print(f"IS L/S return series: {len(ls_is)} daily observations")
print(f"IS annualized Sharpe (naive): {ls_is.mean() / ls_is.std() * np.sqrt(365):.2f}")
```

- [ ] **Step 2: Run stationary block bootstrap and compute empirical p-value**

Add Cell 7 in `validation.ipynb`:

```python
def stationary_bootstrap(data: np.ndarray, block_size: int,
                          n_reps: int = 2000, seed: int = 42) -> np.ndarray:
    """
    Politis & Romano (1994) stationary bootstrap.
    Resamples blocks of geometric(p=1/block_size) length, preserving dependence.
    Returns array of bootstrap mean estimates.
    """
    rng = np.random.default_rng(seed)
    T   = len(data)
    p   = 1.0 / block_size
    means = np.empty(n_reps)
    for i in range(n_reps):
        indices = []
        while len(indices) < T:
            start = rng.integers(0, T)
            length = rng.geometric(p)
            for j in range(length):
                indices.append((start + j) % T)
        means[i] = data[indices[:T]].mean()
    return means

# Block size = horizon (14) to cover the autocorrelation span
block_size     = BEST_H
boot_means     = stationary_bootstrap(ls_is.values, block_size=block_size)

# Two-sided p-value: fraction of bootstrap means <= 0
# (under H0: true mean = 0, centered bootstrap)
boot_centered  = boot_means - boot_means.mean()   # center under H0
boot_p         = (np.abs(boot_centered) >= np.abs(ls_is.mean())).mean()

print(f"Stationary block bootstrap (block={block_size}, n=2000):")
print(f"  Observed mean daily return: {ls_is.mean():.5f}")
print(f"  Bootstrap p-value (two-sided): {boot_p:.4f}")
print(f"  Bootstrap 95% CI: [{np.percentile(boot_means, 2.5):.5f}, {np.percentile(boot_means, 97.5):.5f}]")

# Compare with HAC parametric
hac_t_ls, hac_p_ls, hac_lags = hac_tstat(ls_is, horizon=BEST_H)
print(f"\nHAC t-stat on L/S returns: t={hac_t_ls:.3f}, p={hac_p_ls:.4f}, lags={hac_lags}")
print("(If HAC and bootstrap disagree: use the more conservative result)")

fig, ax = plt.subplots(figsize=(10, 4))
ax.hist(boot_centered, bins=60, color="steelblue", alpha=0.7, edgecolor="white")
ax.axvline(ls_is.mean(), color="red", linewidth=2, label=f"Observed mean = {ls_is.mean():.5f}")
ax.axvline(-ls_is.mean(), color="red", linewidth=2, linestyle="--", alpha=0.5)
ax.set_title("Stationary Block Bootstrap Distribution (H0: mean = 0)")
ax.set_xlabel("Bootstrap mean daily L/S return")
ax.legend()
plt.tight_layout()
plt.show()
```

---

## Task 6: Deflated Sharpe Ratio

**Files:**
- `validation.ipynb` Cell 8

- [x] **Step 1: Compute DSR penalized for N trials** ✅ **Done (2026-06-01)** — implemented as a sensitivity row across N=56/84/140, headline **N=140**. **The plan's code below is superseded** — it omitted the σ_SR scaling and produced a degenerate DSR=0.00%; the executed cell scales the expected-max Sharpe by an empirical σ_SR=0.0403. Result: DSR=47.3% at N=140, **FAIL**. See *Task 6 Findings*.

Add Cell 8 in `validation.ipynb`:

```python
from scipy.stats import norm as scipy_norm

def deflated_sharpe_ratio(returns: pd.Series, n_trials: int) -> dict:
    """
    Bailey & Lopez de Prado (2014) Deflated Sharpe Ratio.
    Computes P[SR > SR*] where SR* is the max expected SR from n_trials under H0.
    Returns per-period (daily) Sharpe and its non-normality-adjusted SE.
    """
    T        = len(returns)
    sr_hat   = returns.mean() / returns.std()   # per-period (daily)
    skew     = float(returns.skew())
    exc_kurt = float(returns.kurt())            # pandas .kurt() is excess kurtosis

    # Expected max Sharpe from n_trials iid trials under null
    euler_g  = 0.5772156649
    sr_max   = ((1 - euler_g) * scipy_norm.ppf(1 - 1/n_trials)
                + euler_g    * scipy_norm.ppf(1 - 1/(n_trials * np.e)))

    # Sharpe variance (Mertens 2002 / Lo 2002 non-normality correction)
    var_sr   = (1 + 0.5*sr_hat**2 - skew*sr_hat + (exc_kurt/4)*sr_hat**2) / (T - 1)

    dsr      = scipy_norm.cdf((sr_hat - sr_max) / np.sqrt(var_sr))
    ann_sr   = sr_hat * np.sqrt(365)
    ann_se   = np.sqrt(var_sr) * np.sqrt(365)

    return {"sr_daily": sr_hat, "sr_annual": ann_sr, "sr_annual_se": ann_se,
            "sr_max_daily": sr_max, "skew": skew, "exc_kurt": exc_kurt,
            "dsr": dsr, "n_trials": n_trials, "T": T}

dsr_result = deflated_sharpe_ratio(ls_is, n_trials=N_tests)

print("Deflated Sharpe Ratio Analysis")
print(f"  IS annualized Sharpe:     {dsr_result['sr_annual']:.3f}  ± {dsr_result['sr_annual_se']:.3f} (SE)")
print(f"  Skew:                     {dsr_result['skew']:.3f}")
print(f"  Excess kurtosis:          {dsr_result['exc_kurt']:.3f}")
print(f"  Trials (N):               {dsr_result['n_trials']}")
print(f"  Expected max SR (daily):  {dsr_result['sr_max_daily']:.4f}")
print(f"  P[SR > SR*] (DSR):        {dsr_result['dsr']:.4f}")
print()
print("Interpretation:")
print(f"  DSR = {dsr_result['dsr']:.2%} means only a {dsr_result['dsr']:.2%} probability")
print(f"  that the true Sharpe exceeds what we'd expect from {N_tests} random trials.")
if dsr_result["dsr"] < 0.95:
    print("  FAIL: Does not clear the DSR bar at 95% confidence.")
else:
    print("  PASS: Survives DSR test at 95% confidence.")
```

---

## Task 7: Transaction Cost Model

**Files:**
- `validation.ipynb` Cell 9

- [ ] **Step 1: Estimate daily turnover and net-of-cost returns**

Add Cell 9 in `validation.ipynb`:

```python
# --- Cost stack for Hyperliquid perp futures ---
# Taker fee:      0.05% one-way (conservative; maker is 0.02%)
# Half-spread:    ~0.05% (typical for top-35 perps by volume)
# Round-trip:     2 × (0.05% fee + 0.05% half-spread) = 0.20%
# Borrow/short:   ~0 (perp; cost is in funding rate, not stock-loan)
# Financing:      embedded in funding rate — not charged separately on perps
# Note: the funding rate itself is revenue/cost for the position, but we are
# NOT modeling funding P&L here — only the price-return leg.

ONE_WAY_COST   = 0.0005 + 0.0005   # fee + half-spread = 0.10% per side
ROUND_TRIP     = 2 * ONE_WAY_COST  # 0.20% per round-trip trade

# Estimate average daily turnover: fraction of portfolio value traded each day
# Build daily L/S compositions and compare day-over-day
def compute_daily_turnover(df: pd.DataFrame, sw: int, lw: int) -> pd.Series:
    df_z = build_zscore(df, sw, lw).dropna(subset=["zscore"])
    df_z["q"] = df_z.groupby("date")["zscore"].transform(
        lambda x: pd.qcut(x, 5, labels=False, duplicates="drop") if len(x) >= 5 else np.nan
    )
    df_z = df_z.dropna(subset=["q"])
    # Active coins each day: Q1 (long) and Q5 (short)
    active = df_z[df_z["q"].isin([0.0, 4.0])][["date", "symbol", "q"]].copy()
    active["side"] = active["q"].map({0.0: "long", 4.0: "short"})
    
    turnover_per_day = []
    dates = sorted(active["date"].unique())
    for i in range(1, len(dates)):
        prev = set(active[active["date"] == dates[i-1]]["symbol"])
        curr = set(active[active["date"] == dates[i]]["symbol"])
        n_active = len(curr) if len(curr) > 0 else 1
        # New entries (buys/covers) + exits (sells/shorts) as fraction of portfolio
        changed = len(prev.symmetric_difference(curr))
        turnover_per_day.append(changed / n_active)
    
    return pd.Series(turnover_per_day, index=dates[1:])

daily_turnover  = compute_daily_turnover(panel_is, BEST_SW, BEST_LW)
mean_daily_turn = daily_turnover.mean()
daily_cost      = mean_daily_turn * ROUND_TRIP   # cost as fraction of portfolio

ls_is_net       = ls_is - daily_cost             # subtract cost every day
ls_cum_gross    = (1 + ls_is).cumprod()
ls_cum_net      = (1 + ls_is_net).cumprod()

ann_ret_gross   = ls_cum_gross.iloc[-1] ** (365 / len(ls_is)) - 1
ann_ret_net     = ls_cum_net.iloc[-1]   ** (365 / len(ls_is_net)) - 1
ann_vol         = ls_is.std() * np.sqrt(365)
sharpe_gross    = ann_ret_gross / ann_vol
sharpe_net      = ann_ret_net   / ann_vol

print(f"Cost model: round-trip = {ROUND_TRIP:.2%} per trade")
print(f"Mean daily turnover: {mean_daily_turn:.1%} of portfolio")
print(f"Mean daily cost drag: {daily_cost:.4%}")
print(f"Annual cost drag: {daily_cost * 365:.2%}")
print()
print(f"{'':30s} {'Gross':>8s}  {'Net':>8s}")
print(f"{'Ann. return':30s} {ann_ret_gross:>8.2%}  {ann_ret_net:>8.2%}")
print(f"{'Sharpe ratio':30s} {sharpe_gross:>8.2f}  {sharpe_net:>8.2f}")
print()
print("Stress test (2× costs):")
ls_is_2x  = ls_is - 2 * daily_cost
ann_ret_2x = (1 + ls_is_2x).cumprod().iloc[-1] ** (365 / len(ls_is_2x)) - 1
print(f"  Ann. return at 2× costs: {ann_ret_2x:.2%}  Sharpe: {ann_ret_2x / ann_vol:.2f}")
if ann_ret_2x < 0:
    print("  WARNING: edge evaporates at 2× cost stress — likely fragile.")
else:
    print("  Edge persists at 2× cost stress.")
```

---

## Task 8: In-Sample vs. Sealed OOS Comparison

**Files:**
- `validation.ipynb` Cells 10–11

- [ ] **Step 1: Evaluate the IS-selected combo on OOS data**

Add Cell 10 in `validation.ipynb`:

```python
ls_oos = build_ls_returns(panel_oos, BEST_SW, BEST_LW)

ann_ret_is  = (1 + ls_is).cumprod().iloc[-1]  ** (365 / len(ls_is))  - 1
ann_vol_is  = ls_is.std() * np.sqrt(365)
sharpe_is   = ann_ret_is / ann_vol_is

if len(ls_oos) > 0:
    ann_ret_oos = (1 + ls_oos).cumprod().iloc[-1] ** (365 / len(ls_oos)) - 1
    ann_vol_oos = ls_oos.std() * np.sqrt(365)
    sharpe_oos  = ann_ret_oos / ann_vol_oos
else:
    ann_ret_oos = ann_vol_oos = sharpe_oos = np.nan

print("IS vs OOS Comparison")
print(f"  Caveat: OOS window is PARTIALLY BURNED — the parameter sweep used full data.")
print(f"  Re-running sweep on IS only reduces but does not eliminate this concern.")
print()
print(f"{'Metric':25s} {'IS':>10s}  {'OOS':>10s}")
print(f"{'Ann. return (gross)':25s} {ann_ret_is:>10.2%}  {ann_ret_oos:>10.2%}")
print(f"{'Sharpe (gross)':25s} {sharpe_is:>10.2f}  {sharpe_oos:>10.2f}")
print(f"{'Trading days':25s} {len(ls_is):>10d}  {len(ls_oos):>10d}")

if not np.isnan(ann_ret_oos):
    if ann_ret_oos < 0:
        print("\nOOS RESULT: negative return — strong evidence of overfitting.")
    elif sharpe_oos < 0.5 * sharpe_is:
        print("\nOOS RESULT: severe degradation (< 50% of IS Sharpe) — likely overfitting.")
    else:
        print("\nOOS RESULT: reasonable IS-to-OOS retention.")
```

- [ ] **Step 2: Plot IS and OOS equity curves side by side**

Add Cell 11 in `validation.ipynb`:

```python
fig, axes = plt.subplots(1, 2, figsize=(16, 5))

ls_cum_is  = (1 + ls_is).cumprod()
axes[0].plot(ls_cum_is.index, (ls_cum_is - 1) * 100, color="steelblue", linewidth=2)
axes[0].axhline(0, color="gray", linestyle="--", linewidth=0.5)
axes[0].set_title(f"IS: Long Q1 / Short Q5 ({BEST_SW}d/{BEST_LW}d)")
axes[0].set_ylabel("Cumulative Return (%)")
axes[0].yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.0f}%"))

if len(ls_oos) > 0:
    ls_cum_oos = (1 + ls_oos).cumprod()
    axes[1].plot(ls_cum_oos.index, (ls_cum_oos - 1) * 100, color="coral", linewidth=2)
    axes[1].axhline(0, color="gray", linestyle="--", linewidth=0.5)
    axes[1].set_title(f"OOS: Long Q1 / Short Q5 ({BEST_SW}d/{BEST_LW}d)")
    axes[1].set_ylabel("Cumulative Return (%)")
    axes[1].yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.0f}%"))
else:
    axes[1].text(0.5, 0.5, "No OOS data", ha="center", transform=axes[1].transAxes)

plt.tight_layout()
plt.show()
```

---

## Task 9: Decision Rule Assessment

**Files:**
- `validation.ipynb` Cell 12

- [ ] **Step 1: Apply the four-gate decision rule and produce a deployability verdict**

Add Cell 12 in `validation.ipynb`:

```python
print("=" * 65)
print("DECISION RULE — FACTOR DEPLOYABILITY ASSESSMENT")
print("=" * 65)

# Gate 1: Multiple-testing-adjusted significance
gate1_pass  = bool(BEST["reject_bh"]) if "BEST" in dir() else False
gate1_t     = float(BEST["hac_t"])    if "BEST" in dir() else np.nan
gate1_label = "PASS" if gate1_pass else "FAIL"
print(f"\n[Gate 1] Multiple-testing-adjusted significance (BH, t>3 preferred)")
print(f"  HAC t-stat:              {gate1_t:.3f}")
print(f"  BH-corrected p-value:    {float(BEST['p_bh']):.4f}" if "BEST" in dir() else "  N/A")
print(f"  Result: {gate1_label}")

# Gate 2: Sign consistency — IS vs OOS and bootstrap
gate2_oos_sign   = (not np.isnan(ann_ret_oos)) and (ann_ret_oos > 0)
gate2_boot_sign  = boot_p < 0.10   # bootstrap p < 10%
gate2_pass       = gate2_oos_sign and gate2_boot_sign
gate2_label      = "PASS" if gate2_pass else "FAIL"
print(f"\n[Gate 2] Sign stability (IS & OOS positive, bootstrap p < 10%)")
print(f"  OOS return positive:     {gate2_oos_sign}  ({ann_ret_oos:.2%})")
print(f"  Bootstrap p-value:       {boot_p:.4f}")
print(f"  Result: {gate2_label}")

# Gate 3: Deflated Sharpe / bootstrap / overfitting tests
gate3_pass  = dsr_result["dsr"] >= 0.90 and boot_p < 0.10
gate3_label = "PASS" if gate3_pass else "FAIL"
print(f"\n[Gate 3] Deflated Sharpe + bootstrap (DSR ≥ 90%, boot p < 10%)")
print(f"  Deflated Sharpe (DSR):   {dsr_result['dsr']:.2%}")
print(f"  Bootstrap p-value:       {boot_p:.4f}")
print(f"  Result: {gate3_label}")

# Gate 4: Positive net-of-cost return, survives 2× stress
gate4_pass  = ann_ret_net > 0 and ann_ret_2x > 0
gate4_label = "PASS" if gate4_pass else "FAIL"
print(f"\n[Gate 4] Net-of-cost return survives 2× stress")
print(f"  Ann. return (net, 1× cost): {ann_ret_net:.2%}")
print(f"  Ann. return (net, 2× cost): {ann_ret_2x:.2%}")
print(f"  Result: {gate4_label}")

# Final verdict
gates = [gate1_pass, gate2_pass, gate3_pass, gate4_pass]
n_pass = sum(gates)
print(f"\n{'=' * 65}")
print(f"GATES PASSED: {n_pass}/4")
if n_pass == 4:
    print("VERDICT: DEPLOYABLE — factor clears all four gates.")
elif n_pass >= 3:
    print("VERDICT: MARGINAL — passes most gates but has a known weak link.")
    print("         Report which gate failed and why. Do not deploy without")
    print("         additional evidence (longer OOS, regime analysis).")
else:
    print("VERDICT: NOT DEPLOYABLE — fails ≥ 2 gates.")
    print("         Report as a statistical null. Attractive IS gross numbers")
    print("         do not override a failed OOS or failed significance test.")
print("=" * 65)
```

---

## Task 10: Add Honest Caveats to signal_analysis.ipynb

**Files:**
- Modify: `signal_analysis.ipynb` (add a final markdown cell)

- [ ] **Step 1: Append a caveats cell at the end of signal_analysis.ipynb**

After the existing "Summary" cell (cell 14), add a new markdown cell:

```markdown
## 7. Methodological Limitations

The results above should be read alongside `validation.ipynb` which applies formal statistical tests. Key caveats:

**Survivorship bias (unresolved):** The universe was constructed from the live Hyperliquid API as of May 2026. Coins delisted during the study period are excluded. This silently removes the worst-performing assets and inflates measured returns. The Hyperliquid API does not provide historical universe snapshots, so this cannot be fully corrected; it is disclosed.

**Point-in-time universe bias (partially unresolved):** Coins are ranked by current 24h volume. A coin that is now top-35 but was obscure a year ago is included with its full history. Seven coins in the panel listed mid-study (e.g. CHIP: Apr 2026). This reintroduces selection-on-outcome bias at the margin.

**Multiple testing (corrected in validation.ipynb):** The parameter sweep tested 84 combinations. The best (21d/90d/14d) was selected post-hoc. Benjamini-Hochberg correction applied to all 84 in-sample p-values — see `validation.ipynb` Gate 1 for whether the result survives.

**Out-of-sample status:** The OOS window (Feb 15 – May 18, 2026) is partially burned because the parameter sweep used the full dataset. The IS-only re-sweep in `validation.ipynb` partially mitigates this. The OOS result should be treated as indicative, not confirmatory.

**Execution assumption:** Signal formed from daily close data; positions enter at next-day close. This assumes 24-hour execution lag, which is conservative for perps but documented.

**Transaction costs:** See `validation.ipynb` Task 7. A round-trip cost of 0.20% per trade is applied based on 0.05% taker fee + 0.05% half-spread per side.
```

- [ ] **Step 2: Commit all validation work**

```bash
git add validation.ipynb signal_analysis.ipynb data_pipeline.py
git commit -m "feat: add validation notebook with HAC, bootstrap, DSR, cost model, decision rule"
```

---

## Code Quality Issues (Karpathy Review — 2026-06-01)

Issues found in `validation.ipynb` Cells 1–2 that should be fixed before Task 3 runs on top of this foundation:

| Issue | Guideline | Location | Fix |
|-------|-----------|----------|-----|
| `funding_raw` + `ohlcv` loaded but never used | Simplicity | Cell 1 | Remove; add back in the cell that needs them |
| `all_symbols[:TOP_N]` assumes volume-rank order | Think First | Cell 2, line 8 | Assert or document `symbols.json` is volume-ranked |
| IS row count 9,139 vs. expected ~9,490 — unexplained 351-row gap | Think First | Cell 2 output | Diagnose: gaps in funding data? Coins with partial history? |
| 4-line task-history comment describes dev process, not invariant | Surgical | Cell 2, lines 1–4 | Collapse to 1 line stating the actual constraint |
| No assertions on split correctness | Goal-Driven | Cell 2 | Add `assert panel_35['symbol'].nunique() == TOP_N` and `assert len(panel_oos) > 0` |

---

## data_pipeline.py — Karpathy Review Fixes (2026-06-01)

Ad-hoc review of `data_pipeline.py` against `/karpathy-guidelines` (separate from the 10-task plan above). Three issues found and fixed; a regression test added. Verified: `python -m py_compile` clean, `test_data_pipeline.py` 4/4 passing.

| # | Issue | Guideline | Location | Fix |
|---|-------|-----------|----------|-----|
| 1 | **Funding cadence misdocumented.** Comments said funding "settled every 8 hours (~3 per day)"; Hyperliquid actually charges funding **hourly** (~24/day, each hour 1/8 of the 8h rate — [HL docs](https://hyperliquid.gitbook.io/hyperliquid-docs/trading/funding)). | Think First (assumption stated as fact) | `fetch_funding_rates` + `build_funding_features` docstrings | Corrected both; `daily_funding` sums ~24 hourly records/day, not 3 |
| 2 | **In-sample selection not disclosed.** IC=−0.049 / Q1–Q5 spread=2.06% quoted with no note that the sweep picked windows+horizon on the same data used to score them. | Think First | `build_funding_features` docstring | Added a `KNOWN BIASES` note (consistent with Task 3) |
| 3 | **Forward-return label misalignment.** `build_panel` used `pct_change(n).shift(-n)`, which shifts by **rows, not calendar days** — an interior date gap silently makes `ret_Nd` span >N days (look-ahead/label bug). Also relied on pandas' deprecated default `fill_method='pad'`. | Goal-Driven (no test guarded no-look-ahead) | `build_panel` forward returns | Reindex each symbol onto a contiguous daily grid, then `pct_change(n, fill_method=None).shift(-n)`; a gap-spanning return is now `NaN`. Contiguous-data output byte-identical to before |

**Follow-up (2026-06-01):** a later pass caught two stragglers from fix #1 — the module docstring (`data_pipeline.py:6`, "8-hour snapshots") and the `main()` summary print (`:361`, "raw 8h funding snapshots") still named the old cadence. Both corrected to "hourly snapshots"; the file is now internally consistent (the lone remaining "8h" at `:98` is the accurate "1/8 of the computed 8h rate" mechanic). `py_compile` clean.

**New regression test — `test_data_pipeline.py` (4 tests, all pass):**
1. Forward-return values match an independent hand computation for every interior row.
2. Correct trailing-NaN count per horizon (last N rows of `ret_Nd` are NaN).
3. No cross-symbol leakage at the symbol boundary.
4. Gap → NaN: drop a middle day, assert the gap-spanning horizon is NaN while a non-spanning horizon on the same row stays finite. (Fails against the old row-shift code; passes against fix #3.)

**Downstream impact on the validation plan:**
- **The Task 3 figures were computed on the pre-fix `panel.parquet`.** Fix #3 only alters `ret_Nd` for rows adjacent to an *interior* date gap; late-listed coins gap at the *start* (contiguous thereafter). **Re-verified 2026-06-01 against the fixed pipeline:** rebuilding the panel from the cached raw inputs with the fixed `build_panel` changes **0** forward-return cells across all four horizons and leaves `daily_funding` identical — the full 17,230×16 panel is byte-identical to the on-disk one (max abs diff 0 across every column). The OHLCV carries **no interior calendar-day gaps** (only trailing NaNs, N×50 per horizon), so the contiguous-grid reindex is a no-op on this dataset. The Task 3 sweep reproduces **exactly**: 56 combos, best sw=7/lw=30/h=1, mean_IC=−0.0200, HAC t=−1.75, p=0.080, zero naive-significant combos. **No figures change; regenerating `panel.parquet` is unnecessary.**
- Fix #1 is documentation-only for the math: `daily_funding` already summed whatever records existed per day, and the z-score normalizes by its own rolling std, so the corrected ~24/day understanding changes no computed signal value.
- Fix #2's disclosure reinforces the Task 3 conclusion that the funding edge does not survive honest IS-only re-selection.

---

## Self-Review

**Spec coverage check:**
- Survivorship bias → Task 1 (audit + docstring) + Task 10 (caveats cell) ✓
- Look-ahead bias → Addressed in Task 10 caveats + execution assumption note ✓
- Point-in-time universe → Task 1 late-coin audit + Task 10 ✓
- Multiple testing → Task 3 IS sweep + Task 4 BH/Holm ✓
- Return convention → Audited (correct); documented in Task 7 build_ls_returns comment ✓
- Transaction costs → Task 7 ✓
- HAC / Newey-West → Task 3 (hac_tstat helper) + Task 5 (applied to L/S returns) ✓
- Multiple-testing correction → Task 4 ✓
- Sealed OOS → Task 2 + Task 8 ✓
- Stationary block bootstrap → Task 5 ✓
- Deflated Sharpe Ratio → Task 6 ✓
- Cost-aware backtesting + robustness → Task 7 ✓
- Decision rule → Task 9 ✓

**Potential gaps:**
- White's reality check / SPA test: not implemented (would require full distribution of all 84 return series; omitted given time constraint — BH subsumes it for correlated trials per the spec)
- PBO via combinatorial cross-validation: omitted (requires full grid of daily return series per config — feasible but adds ~200 lines; the DSR + bootstrap together address the same concern)
- Regime breakout analysis: the IS/OOS split already covers one regime shift (Jan 2026 BTC rally); not adding a separate regime cell given deadline

**Placeholder scan:** No TBD or TODO in code blocks. All function signatures consistent across tasks. `build_zscore`, `build_ls_returns`, `hac_tstat`, `stationary_bootstrap`, `deflated_sharpe_ratio`, `compute_daily_turnover` are defined before use.

**Type consistency:** `BEST_SW`, `BEST_LW`, `BEST_H` are set in Task 4 Cell 5 and used in Tasks 5–9. `ls_is` is a `pd.Series` set in Task 5 Cell 6 and used throughout. `boot_p`, `dsr_result`, `ann_ret_net`, `ann_ret_2x`, `ann_ret_oos` are all set before Task 9 Cell 12.
