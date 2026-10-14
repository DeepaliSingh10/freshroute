# FreshRoute — Demo Script, Pitch & Judging-Day Runbook

## The 90-second story

> *"A third of fresh produce is lost between farm and market. FreshRoute tells a distributor
> exactly which batches to ship where, and when to discount — respecting shelf life, demand,
> transport and capacity — and proves it beats their current process on the same numbers."*

## 90-second script (timestamped)

The dashboard runs **frontend-only**: the backend under `apps/api` is not implemented yet, so
every value is clearly-labelled **demo data** (badge + inline notice + footer). The script below
is written so the demo is honest about this. Do **not** read demo numbers aloud as results — say
"on the demo dataset" / "in the demo fixture".

| Time | On screen | Say |
|------|-----------|-----|
| 0:00–0:08 | Title / header + orange **"Live API not connected"** banner | *"A third of fresh produce is lost between farm and market. FreshRoute tells a distributor which batches to ship where, and when to discount."* |
| 0:08–0:18 | Scenario selector → pick **`demo-hidden-stress`**; status badge shows **Demo data** | *"We're running on a labelled demo dataset until the planning service is wired in — the app is honest about that: orange banner, demo badge, footer disclaimer."* |
| 0:18–0:30 | Press **Optimize** → KPI cards fill in | *"The dashboard shows net revenue, spoilage, fulfillment and feasibility against a FEFO baseline. Perishability-first: the shortest-shelf-life batches are allocated first."* |
| 0:30–0:42 | Scroll to **Baseline vs optimized** charts | *"Same cost model, both sides. Spoilage down, fulfillment up, net revenue up — and zero constraint violations."* (Say "on the demo fixture".) |
| 0:42–0:52 | Dispatch table → click **Explain** on a low-shelf-life row | *"Every recommendation is inspectable: the verbatim reason, the shelf-life check, and — plainly — which constraints are enforced server-side and not exposed here. No invented reasoning."* |
| 0:52–1:02 | Discount card → **Explain recommendation** | *"Batch B-3007 expires in under a day with no feasible lane; a 30% cut recovers value instead of accepting spoilage."* |
| 1:02–1:15 | **Sensitivity** panel → drag demand to ~1.4×, travel delay to +6h | *"Move demand or delay and the illustrative range updates. This is a disclosed local model, not a statistics claim — the label says 'Simulated'. The direction is what matters."* |
| 1:15–1:30 | **Replan feed** → fire *Traffic delay* | *"An event produces a plan diff with reasons — here too it's labelled 'Simulated' because `/replan` isn't connected yet."* Then close: *"Ship where it survives, discount where it won't."* |

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

## Backup plan if live fails

Play the recorded backup, then show the `results/hidden_summary.md` table and the
reproducibility log live. The story stands on the numbers, not the animation.
