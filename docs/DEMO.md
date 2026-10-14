# FreshRoute — Demo Script, Pitch & Judging-Day Runbook

## The 90-second story

> *"A third of fresh produce is lost between farm and market. FreshRoute tells a distributor
> exactly which batches to ship where, and when to discount — respecting shelf life, demand,
> transport and capacity — and proves it beats their current process on the same numbers."*

## Live demo flow (2–3 min)

1. **Pick a hidden scenario** (pre-loaded, seeded).
2. **Show the baseline** KPIs: spoilage %, fulfillment %, net revenue.
3. **Click Optimize** → show the improved KPIs and the delta banner:
   *"21% less spoilage · +8 pts fulfillment · ₹4.2L more net revenue · 0 constraint violations."*
4. **Open the dispatch plan**: perishability-first ordering; each row shows the shelf-life
   feasibility check and a plain-English reason.
5. **Open a discount card**: *"Batch B12 — 30% off — would spoil in 1.2 days, no feasible lane."*
6. **Drag the sensitivity slider** (demand +40% / travel +6h): plan adapts; uncertainty band
   updates. Shows robustness.
7. **Fire a disruption** (traffic delay / new order): `/replan` returns a diff with reasons.
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
