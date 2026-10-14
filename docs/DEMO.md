# FreshRoute — Demo Script, Pitch & Judging-Day Runbook

## The 90-second story

> *"A third of fresh produce is lost between farm and market. FreshRoute tells a distributor
> exactly which batches to ship where, and when to discount — respecting shelf life, demand,
> transport and capacity — and proves it beats their current process on the same numbers."*

## 90-second script (timestamped)

With the backend (`apps/api`) running, the dashboard shows **Live API** badges and real results.
When the API is *not* running it stays fully demonstrable on clearly-labelled **demo data**
(badge + inline notice + footer). The script below works either way and is honest about which
mode is on screen. In demo mode do **not** read demo numbers aloud as results — say "on the demo
dataset" / "in the demo fixture".

| Time | On screen | Say |
|------|-----------|-----|
| 0:00–0:08 | Title / header + orange **"Live API not connected"** banner | *"A third of fresh produce is lost between farm and market. FreshRoute tells a distributor which batches to ship where, and when to discount."* |
| 0:08–0:18 | Scenario selector → pick **`hidden_01`**; status badge shows **Live API** (or **Demo data** if the API is down) | *"The dashboard is live-connected to the planning service, or — if it's unavailable — falls back to a labelled demo dataset. It's always honest: banner, source badge, footer disclaimer."* |
| 0:18–0:30 | Press **Optimize** → KPI cards fill in | *"The dashboard shows net revenue, spoilage, fulfillment and feasibility against a FEFO baseline. Perishability-first: the shortest-shelf-life batches are allocated first."* |
| 0:30–0:42 | Scroll to **Baseline vs optimized** charts | *"Same cost model, both sides. Spoilage down, fulfillment up, net revenue up — and zero constraint violations."* (Say "on the demo fixture".) |
| 0:42–0:52 | Dispatch table → click **Explain** on a low-shelf-life row | *"Every recommendation is inspectable: the verbatim reason, plus the shelf-life and lane-capacity checks and a factored price/cost/margin breakdown from the live `/explain` endpoint. No invented reasoning."* |
| 0:52–1:02 | Discount card → **Explain recommendation** | *"Batch B-3007 expires in under a day with no feasible lane; a 30% cut recovers value instead of accepting spoilage."* |
| 1:02–1:15 | **Sensitivity** panel → drag demand to ~1.4×, travel delay to +6h | *"Move demand or delay and the illustrative range updates. This is a disclosed local model, not a statistics claim — the label says 'Simulated'. The direction is what matters."* |
| 1:15–1:30 | **Replan feed** → fire *Traffic delay* | *"An event produces a live plan diff with reasons from `/replan`; if the API is down it's a clearly-labelled local simulation."* Then close: *"Ship where it survives, discount where it won't."* |

**Hard rule for the demo:** never present a demo/illustrative number as a verified result, and
never attribute invented reasoning to the optimizer. If the live API is running, the same UI
switches to **Live API** badges automatically and the numbers become real results.

## Live demo flow (2–3 min)

1. **Pick a hidden scenario** (pre-loaded, seeded).
2. **Show the baseline** KPIs: spoilage %, fulfillment %, net revenue.
3. **Click Optimize** → show the improved KPIs and the delta banner (spoilage, fulfillment, net
   revenue, 0 violations). Read the numbers that are on screen — do not substitute placeholder
   figures. In demo mode every value is labelled **Demo data**.
4. **Open the dispatch plan**: perishability-first ordering; each row shows the shelf-life
   feasibility check and a plain-English reason.
5. **Open a discount card**: e.g. batch **B-3007** (*"30% off — no feasible lane to Bengaluru
   before it spoils"*) and its **Explain recommendation** panel.
6. **Drag the sensitivity slider** (demand / travel delay / price shock): the illustrative range
   updates. This is a disclosed local model, labelled *Simulated* — not a statistical claim.
7. **Fire a disruption** (traffic delay / temp spike / capacity change): a plan diff with reasons
   appears. With the API connected this is live `/replan`; otherwise it is a clearly-labelled
   local simulation.
8. Close with the **explainability + commercial workflow** slide.

## Pitch deck (7 slides max)

1. Problem + scale of post-harvest loss (MFPI context).
2. What FreshRoute decides (dispatch-where-discount) + why existing tools don't.
3. Architecture diagram (from `ARCHITECTURE.md`).
4. The optimization (objective + hard constraints) — one clean formula.
5. Results table on **hidden scenarios** vs baseline (spoilage / fulfillment / net revenue / 0 violations).
6. Robustness + uncertainty + replanning.
7. Commercial model: SaaS subscription for distributors / cold-storage / logistics; workflow slide.

## Judging-day runbook

- [ ] App + API running **before** the slot; browser pre-granted any permissions.
- [ ] Hidden-scenario results **precomputed** and cached (`results/`) so nothing depends on live compute.
- [ ] 90s **screen-recorded backup** ready in case the live demo hiccups.
- [ ] One-command reproduce printed on a slide (`make reproduce` / script).
- [ ] Every teammate knows which section they present.

## Concrete demo commands

Start the API (terminal 1):
```
cd apps/api
uvicorn app.main:app --reload --port 8000
```
Start the dashboard (terminal 2):
```
cd apps/web
npm install
npm run dev            # open http://localhost:5173
```
Reproduce every result artifact (no UI needed):
```
cd apps/api
pip install -r requirements.txt
python scripts/run_phase1.py --write-results
python scripts/run_forecast.py --write-results
python scripts/run_robustness.py --draws 30 --write-results
python scripts/run_replan.py --write-results
python scripts/run_discount_policy.py --write-results
python scripts/run_telemetry.py --write-results
python scripts/run_sensitivity.py --write-results
pytest                 # 41 tests
```
Or regenerate everything at once: `python scripts/run_all.py` (writes `results/manifest.json`).

## Actual numbers to quote (scenario `hidden_01`, seed 303)

| Signal | Value |
|--------|-------|
| Inventory | 46 batches / 25,350.9 kg |
| Plan | OPTIMAL · 87 dispatches · 20 discounts · **0 violations** · net revenue 572,204.63 |
| vs FEFO | spoilage **−58.8%** (across train/test/hidden **−58.8%..−76.3%**); net revenue **+46%..+131%** |
| Forecast (E1) | holdout MAPE **17.4%** vs naive 24.7–28.7% |
| Markdown (E2) | **+200,923** vs fixed-30% rule |
| Telemetry (E5) | ignoring excursions → 5 infeasible shipments; temp-aware → 0; price feed 626,512 → 648,001 |
| Explainability | a plain-language reason on **every** dispatch and discount |

## Backup plan if live fails

Play the recorded backup, then show the `results/hidden_summary.md` table and the
reproducibility log live. The story stands on the numbers, not the animation.
