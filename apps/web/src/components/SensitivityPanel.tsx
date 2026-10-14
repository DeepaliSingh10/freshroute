import { useMemo, useState } from 'react';
import type { DataSource, PlanResponse, RobustnessBand } from '../api/types';
import { evaluateDelta } from '../utils/metrics';
import { sensitivityRange, simulatePlan, type SensitivityInputs } from '../utils/simulate';
import { formatCurrency, formatKg, formatPercent } from '../utils/format';
import UncertaintyBand from './UncertaintyBand';

interface SensitivityPanelProps {
  plan: PlanResponse;
  source: DataSource;
  /** Real E4 Monte-Carlo band (POST /robustness), or null to fall back to the local model. */
  robustness?: RobustnessBand | null;
}

const DEFAULTS: SensitivityInputs = { demandMultiplier: 1, travelDelayHours: 0, priceShockPct: 0 };

export default function SensitivityPanel({ plan, source, robustness }: SensitivityPanelProps) {
  const [inputs, setInputs] = useState<SensitivityInputs>(DEFAULTS);

  const simulation = useMemo(() => simulatePlan(plan, inputs), [plan, inputs]);
  const range = useMemo(() => sensitivityRange(plan), [plan]);

  const current = plan.metrics;
  const sim = simulation.metrics;

  const revenueDelta = sim.net_revenue - current.net_revenue;
  const spoilageDelta = sim.spoilage_kg - current.spoilage_kg;
  const fulfillmentDelta = sim.fulfillment_pct - current.fulfillment_pct;

  const atDefaults =
    inputs.demandMultiplier === DEFAULTS.demandMultiplier &&
    inputs.travelDelayHours === DEFAULTS.travelDelayHours &&
    inputs.priceShockPct === DEFAULTS.priceShockPct;

  return (
    <section className="panel" aria-label="Sensitivity controls">
      <header className="panel__header">
        <div>
          <h2 className="panel__title">Sensitivity</h2>
          <p className="panel__subtitle">
            Move demand, travel time and price to see how the plan responds
          </p>
        </div>
        <span className="sim-label" title="Computed locally by a disclosed demo model, not the optimizer">
          Simulated · illustrative
        </span>
      </header>

      <div className="sensitivity">
        <div className="sensitivity__controls">
          <label className="slider">
            <span className="slider__head">
              <span>Demand</span>
              <output>{formatMultiplier(inputs.demandMultiplier)}</output>
            </span>
            <input
              type="range"
              min={0.6}
              max={1.6}
              step={0.05}
              value={inputs.demandMultiplier}
              onChange={(event) =>
                setInputs((prev) => ({ ...prev, demandMultiplier: Number(event.target.value) }))
              }
            />
          </label>

          <label className="slider">
            <span className="slider__head">
              <span>Travel delay</span>
              <output>+{inputs.travelDelayHours.toFixed(0)} h</output>
            </span>
            <input
              type="range"
              min={0}
              max={12}
              step={1}
              value={inputs.travelDelayHours}
              onChange={(event) =>
                setInputs((prev) => ({ ...prev, travelDelayHours: Number(event.target.value) }))
              }
            />
          </label>

          <label className="slider">
            <span className="slider__head">
              <span>Price shock</span>
              <output>{formatSignedPct(inputs.priceShockPct)}</output>
            </span>
            <input
              type="range"
              min={-0.2}
              max={0.2}
              step={0.01}
              value={inputs.priceShockPct}
              onChange={(event) =>
                setInputs((prev) => ({ ...prev, priceShockPct: Number(event.target.value) }))
              }
            />
          </label>

          <button
            type="button"
            className="btn btn--secondary btn--sm"
            onClick={() => setInputs(DEFAULTS)}
            disabled={atDefaults}
          >
            Reset
          </button>
        </div>

        <div className="sensitivity__output">
          <div className="sim-metric">
            <span className="sim-metric__label">Net revenue</span>
            <span className="sim-metric__value">{formatCurrency(sim.net_revenue)}</span>
            <DeltaLine delta={revenueDelta} format={formatCurrency} higherIsBetter />
          </div>
          <div className="sim-metric">
            <span className="sim-metric__label">Spoilage</span>
            <span className="sim-metric__value">{formatKg(sim.spoilage_kg)}</span>
            <DeltaLine delta={spoilageDelta} format={formatKg} />
          </div>
          <div className="sim-metric">
            <span className="sim-metric__label">Fulfillment</span>
            <span className="sim-metric__value">{formatPercent(sim.fulfillment_pct)}</span>
            <DeltaLine delta={fulfillmentDelta} format={(v) => `${(v * 100).toFixed(1)} pts`} higherIsBetter />
          </div>
        </div>
      </div>

      {simulation.affected.length > 0 ? (
        <p className="sensitivity__affected">
          {simulation.affected.length} dispatch
          {simulation.affected.length === 1 ? '' : 'es'} would become infeasible under these inputs.
        </p>
      ) : (
        <p className="sensitivity__affected is-ok">All dispatches remain feasible under these inputs.</p>
      )}

      <div className="chart-grid chart-grid--single">
        {robustness ? (
          <UncertaintyBand
            low={robustness.net_revenue_p10}
            point={robustness.net_revenue_mean}
            high={robustness.net_revenue_p90}
            mode="monte-carlo"
            draws={robustness.draws}
            scenarioId={robustness.scenario_id}
          />
        ) : (
          <UncertaintyBand low={range.low} point={range.point} high={range.high} />
        )}
      </div>

      <details className="assumptions">
        <summary>How this is simulated (disclosed model)</summary>
        <ul>
          {simulation.assumptions.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
        <p>
          This is a transparent local heuristic for demonstrating the UI — it is not the FreshRoute
          optimizer, and none of these figures are verified results.
          {source === 'demo' ? ' Source: demo data.' : ''}
        </p>
      </details>
    </section>
  );
}

function formatMultiplier(value: number): string {
  return `${value.toFixed(2)}×`;
}

function formatSignedPct(value: number): string {
  return `${value >= 0 ? '+' : '−'}${Math.abs(value * 100).toFixed(0)}%`;
}

interface DeltaLineProps {
  delta: number;
  format: (value: number) => string;
  higherIsBetter?: boolean;
}

function DeltaLine({ delta, format, higherIsBetter = false }: DeltaLineProps) {
  const direction = evaluateDelta(delta, higherIsBetter);
  const sign = delta > 0 ? '+' : delta < 0 ? '−' : '';
  const arrow = direction.improved ? '▲' : direction.regressed ? '▼' : '•';
  return (
    <span className={`sim-metric__delta is-${direction.tone}`}>
      {arrow} {sign}
      {format(Math.abs(delta))} vs plan
    </span>
  );
}
