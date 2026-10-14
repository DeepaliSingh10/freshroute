# FreshRoute — Data Specification & Synthetic Generator

We generate our own dataset (organizer dataset absent). It must be **documented, reproducible,
and designed so every rubric metric is measurable and the hidden test is honest.**

---

## 1. Design goals

1. **Enough structure to make optimization meaningful** (tight shelf lives, capacity limits,
   price differences between destinations, uneven demand).
2. **A fixed split**: `train` (tune thresholds) / `test` (dev) / `hidden` (final report).
3. **Scenario generator** for perturbations so robustness is provable, not asserted.
4. **One documented cost model** shared by baseline and optimizer.

---

## 2. Tables (CSV under `data/generated/`)

### commodities.csv
| column | type | notes |
|--------|------|-------|
| commodity_id | str | e.g. `TOM` |
| name | str | Tomato |
| perishability_class | str | `leafy`, `berry`, `soft_fruit`, `root`, `tuber` |
| default_shelf_life_days | float | base RSL at harvest |
| cost_basis_per_kg | float | procurement value lost if spoiled |
| handling_per_kg | float | packing/loading |

### batches.csv
| column | type | notes |
|--------|------|-------|
| batch_id | str | |
| commodity_id | str | FK |
| quantity_kg | float | |
| harvest_ts | datetime | |
| remaining_shelf_life_days | float | = shelf life at `now_ts`; drives feasibility |
| origin_id | str | FK to origins |
| quality_grade | str | `A`/`B`/`C` (price multiplier) |

### origins.csv
`origin_id`, `name`, `lat`, `lon`

### destinations.csv
| column | notes |
|--------|-------|
| destination_id, name, region, lat, lon | markets/cities |
| delivery_window_start/end | HH:MM |
| min_days_fresh_on_shelf | buyer requires this many days on arrival |
| is_clearance | `True` for auto-generated local clearance outlets (see below) |

### demand.csv
`destination_id`, `commodity_id`, `date`, `window`, `demand_kg`, `price_per_kg`,
`event_flag` (festival/holiday; used by E1)

### lanes.csv
`lane_id`, `origin_id`, `destination_id`, `travel_time_hours`, `cost_per_kg`,
`capacity_kg`, `departure_window_start/end`

### cost_model.yaml (the single source of truth)
```yaml
transport_cost_per_kg_km: 0.008
handling_per_kg_default: 1.2
spoilage_cost_fraction:               # fraction of cost_basis charged as loss
  leafy: 1.0
  berry: 1.0
  soft_fruit: 0.9
  root: 0.6
  tuber: 0.6
unmet_demand_penalty_per_kg: 10.0     # internal objective only; not in reported net_revenue
discount_ladder:
  t1_days: 3.0
  d1: 0.15
  t2_days: 1.5
  d2: 0.30
shelf_life_buffer_days: 0.25
clearance:                            # local recovery channel (Phase 2, FreshRoute-only)
  price_fraction: 0.45
  demand_fraction: 0.35
  travel_hours: 0.75
  transport_cost_per_kg: 0.5
  lane_capacity_kg: 1000000
  min_days_fresh: 0.0
discount_policy:                      # E2 optimized markdown (disclosed model)
  levels: [0.0, 0.10, 0.20, 0.30, 0.40, 0.50]
  hold_fractions: [0.0, 0.25, 0.50]
  elasticity: 1.5
  full_price_rate: 0.10
  clear_rate: 0.55
  rsl_noise: 0.15
  demand_noise: 0.25
  n_draws: 400
cold_chain:                           # E5 telemetry (IoT sensor simulation)
  ideal_temp_c: 4.0
  threshold_temp_c: 8.0
  excursion_prob: 0.25
  excursion_rise_c: 7.0
  degree_hours_per_day_lost: 24.0
  sample_interval_hours: 4.0
  horizon_hours: 24.0
price_feed:                           # E5 live market-price walk
  n_ticks: 3
  volatility: 0.06
```

### clearance outlets (Phase 2, MVP M4)
For each origin the generator adds one **local clearance destination** (`CLR-<origin>`,
`Destination.is_clearance = True`) plus a short lane and a capped per-commodity demand
(`demand_kg = supply_at_origin × clearance.demand_fraction`). At-risk / stranded stock can be
cleared near the origin at `base_price × price_fraction` instead of spoiling. This is a
FreshRoute capability: **baselines run with `include_clearance=False`** and never use it, so the
comparison measures the value of the recovery channel.

### demand history (E1)
`app/forecast/forecaster.py::generate_demand_history` emits a deterministic **daily demand
series** (one row per destination × commodity × day) with a weekly rhythm, per-series day-of-week
tilt and random festival/event spikes — giving the forecaster real signal to learn. The single-day
snapshot in `demands` remains the decision instance; the history is only used for training/testing E1.

### disruptions (E3)
Disruptions are described by `replan.Disruption` (blocked origins + network-wide travel delay) and
applied with `apply_disruption`, which closes outbound non-clearance lanes from the blocked origins
and delays the rest. Already-valid committed shipments are held fixed; the remainder is re-optimized.

### telemetry (E5)
`telemetry.simulate_temperatures` emits `TemperatureReading(batch_id, hour, temp_c)` samples at
`cold_chain.sample_interval_hours` over `horizon_hours`; some batches (prob `excursion_prob`) get a
`excursion_rise_c` spike. Degree-hours above `threshold_temp_c` are integrated by trapezoid and
converted to lost shelf life via `degree_hours_per_day_lost`. `apply_temperature_effect` returns an
instance copy with reduced `remaining_shelf_life_days`. `simulate_price_feed` / `apply_price_feed`
produce a lognormal (`price_feed.volatility`) per-commodity price walk and scale market demand
prices on each tick (clearance prices untouched). No new files on disk — these are runtime transforms.

### baseline_definition.yaml
Frozen baseline spec (see §4), shipped at `apps/api/app/data/baseline_definition.yaml`. Lists the
strategies (`fefo` = strong reference, `margin`, `nearest`, `naive`), each with its batch order and
destination order. `fefo`/`margin`/`nearest` are shelf-life-feasible; `naive` is shelf-life-blind.
All baselines ship greedily and never use the clearance channel. Both parties compute it identically.

### scenarios.csv
`scenario_id`, `seed`, `now_ts`, `split` (`train`/`test`/`hidden`), `perturbation_profile`

### scenarios/<id>_perturbations.yaml
Applied on top of the base instance:
```yaml
noise:
  sensor_raw_pct: 0.05        # ±5% on shelf-life readings
missing_samples_pct: 0.03     # random demand/shelf-life dropouts
demand_multiplier: 1.4        # load/demand change
travel_delay_hours: {lane_group: 6}
price_shock_pct: -0.1
temp_spike:
  enabled: true
  rsl_penalty_days: 0.5
```

---

## 3. Generator algorithm (deterministic given seed)

1. Instantiate 6–10 commodities across perishability classes with distinct shelf lives.
2. Create origins (3–5) and destinations (5–10) with lat/lon; build `lanes` with travel time
   ∝ haversine distance × a road factor, and `cost_per_kg` = distance × rate.
3. Create batches: quantity ~ LogNormal; `remaining_shelf_life_days` sampled around the
   commodity default, correlated with `quality_grade`.
4. Create demand: base per (destination, commodity) from a shared popularity vector, with a
   **weekly seasonality** and **event spikes** so E1 forecasting has signal.
5. Set `price_per_kg` per (destination, commodity) with variance so allocation has a real
   trade-off (serve near/cheap vs. far/expensive).
6. Compute capacities so that **some** dispatches are infeasible (forces real decisions).
7. Materialize `train`/`test` scenarios normally; build **`hidden`** scenarios that combine
   perturbations the training scenarios did not (e.g., simultaneous demand spike + delay).
8. Add one **local clearance outlet per origin** (Phase 2) so at-risk/stranded stock has a
   recovery path (`generate_instance(with_clearance=True)`).

**Scale target:** ~45–60 batches, ~70 demand rows, ~28 lanes — small enough to solve in ms,
rich enough to be non-trivial. (Tunable via `generate_instance(n_origins, n_destinations)`.)

---

## 4. Baseline strategies (documented, frozen)

We implement three greedy baselines (`app/optimizer/baseline.py`), no joint optimization:

**4a. `fefo` — the STRONG baseline (official comparison).**
```
1. Sort batches ascending by remaining_shelf_life_days (First-Expired-First-Out).
2. For each batch, consider destinations with open demand it can feasibly reach
   (shelf-life check), sorted by [highest margin_per_kg, then shortest travel time].
3. Allocate min(batch_remaining, destination_remaining_demand, lane_remaining_capacity).
4. No reallocation, no optimization, no discounting; unsold quantity spoils.
5. Compute spoilage, fulfillment, net revenue with the SAME cost model.
```
Urgency-aware and shelf-life-feasible — a fair, strong default that our optimizer must beat.

**4b. `margin` — urgency-blind.** Same as FEFO but orders batches by best achievable margin
(ignores expiry urgency).

**4c. `naive` — price-first and SHELF-LIFE-BLIND** (the real-world failure FreshRoute fixes, M3).
Ships to the highest-price market without checking whether produce can arrive before it
expires. Doomed cargo is reported as `expired_kg`: **zero revenue, transport/handling still
paid, produce spoils on arrival.** Comparing against this quantifies the value of shelf-life-
aware decision support.

The report shows the optimizer against **both** `fefo` (fair, strong) and `naive`
(value of the core capability), with all assumptions disclosed.

> **Clearance exclusion.** All baselines run with `include_clearance=False`: they represent a
> distributor without FreshRoute's local-recovery capability, so at-risk stock simply spoils.
> This keeps the comparison honest — the optimizer's spoilage gain is attributable to the
> allocator, not to a channel the baseline was never allowed to use.

---

## 5. Train/Test/Hidden discipline

| Split | Use |
|-------|-----|
| `train` | tune discount thresholds, solver params, forecast model |
| `test` | during dev to sanity-check; not for threshold tuning |
| `hidden` | **only touched for the final report**; e.g. combined perturbations |

Report final numbers **on `hidden`** and state clearly they were not used to tune.

---

## 6. Feasibility: HARD vs SOFT

- **Hard (must be 0 violations):** stock availability, demand upper bound, lane/vehicle
  capacity, delivery windows, shelf-life feasibility.
- **Soft (penalized, reported):** unmet demand, spoilage, discounts.

The evaluation harness **independently re-checks hard constraints** after the solver returns
(defense in depth) and fails the run if any is violated.

---

## 7. Files the repo should contain after generation

```
data/generated/
  commodities.csv  batches.csv  origins.csv  destinations.csv
  demand.csv  lanes.csv  scenarios.csv  cost_model.yaml
  baseline_definition.yaml
  scenarios/<scenario_id>.yaml
  split.json                      # which scenario_ids are train/test/hidden
```
