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

### demand.csv
`destination_id`, `commodity_id`, `date`, `window`, `demand_kg`, `price_per_kg`,
`event_flag` (festival/holiday; used by E1)

### lanes.csv
`lane_id`, `origin_id`, `destination_id`, `travel_time_hours`, `cost_per_kg`,
`capacity_kg`, `departure_window_start/end`

### cost_model.yaml (the single source of truth)
```yaml
transport_cost_per_kg_per_hour: 0.6
handling_per_kg_default: 1.2
spoilage_cost_basis:                  # fraction of cost_basis charged as loss
  leafy: 1.0
  berry: 1.0
  soft_fruit: 0.9
  root: 0.7
  tuber: 0.7
unmet_demand_penalty_per_kg: 2.0
discount_ladder:
  t1_days: 3.0
  d1: 0.15
  t2_days: 1.5
  d2: 0.30
shelf_life_buffer_days: 0.25
```

### baseline_definition.yaml
Documented baseline (see §4). Frozen; both parties compute it identically.

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

**Scale target:** ~200–600 batches, ~40 demands, ~40 lanes — small enough to solve in ms,
rich enough to be non-trivial.

---

## 4. Baseline strategy (documented, frozen)

**FEFO + nearest-feasible-first greedy** — the realistic industry default:

```
1. Sort batches ascending by remaining_shelf_life_days (First-Expired-First-Out).
2. For each batch, consider destinations with open demand it can feasibly reach
   (shelf-life check), sorted by [highest price_per_kg, then shortest travel time].
3. Allocate min(batch_remaining, destination_remaining_demand, lane_remaining_capacity).
4. No reallocation, no optimization, no discounting; unsold quantity spoils.
5. Compute spoilage, fulfillment, net revenue with the SAME cost model.
```

This baseline is *reasonable but suboptimal* — which is exactly what we must beat, and it
mirrors what a real distributor does without decision support. Document its assumptions in the
report so judges see a fair comparison.

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
