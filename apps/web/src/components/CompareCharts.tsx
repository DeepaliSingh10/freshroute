import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { EvalResponse, Metrics } from '../api/types';
import { evaluateDelta } from '../utils/metrics';
import {
  formatCurrency,
  formatRatioSigned,
  formatSignedCurrency,
  formatSignedPoints,
} from '../utils/format';

interface CompareChartsProps {
  evaluation: EvalResponse;
}

const BASELINE_COLOR = '#94a3b8';
const OPTIMIZED_COLOR = '#0f766e';
const COST_COLORS = { transport: '#2563eb', handling: '#7c3aed', spoilage: '#b45309' };

const inrCompact = new Intl.NumberFormat('en-IN', { notation: 'compact', maximumFractionDigits: 1 });
const inr = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 });
const number1 = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 1 });

interface ComparisonBarProps {
  title: string;
  subtitle: string;
  baselineValue: number;
  optimizedValue: number;
  /** Formats a raw value for axis tooltips and labels. */
  format: (value: number) => string;
  /** Whether a higher value is better (affects delta tone). */
  higherIsBetter?: boolean;
  domain?: [number, number];
}

function ComparisonBar({
  title,
  subtitle,
  baselineValue,
  optimizedValue,
  format,
  higherIsBetter = true,
  domain,
}: ComparisonBarProps) {
  const data = [
    { name: 'Baseline', value: baselineValue },
    { name: 'FreshRoute', value: optimizedValue },
  ];
  const delta = optimizedValue - baselineValue;
  const direction = evaluateDelta(delta, higherIsBetter);

  return (
    <article className="chart-card">
      <header className="chart-card__header">
        <h3 className="chart-card__title">{title}</h3>
        <p className="chart-card__subtitle">{subtitle}</p>
      </header>
      <div className="chart-card__canvas">
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={data} margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
            <XAxis dataKey="name" tickLine={false} axisLine={false} fontSize={12} />
            <YAxis
              tickLine={false}
              axisLine={false}
              fontSize={12}
              width={64}
              domain={domain}
              tickFormatter={(value: number) => inrCompact.format(value)}
            />
            <Tooltip
              cursor={{ fill: 'rgba(15, 118, 110, 0.06)' }}
              formatter={(value: number) => format(value)}
            />
            <Bar dataKey="value" radius={[6, 6, 0, 0]} maxBarSize={72}>
              {data.map((entry) => (
                <Cell
                  key={entry.name}
                  fill={entry.name === 'Baseline' ? BASELINE_COLOR : OPTIMIZED_COLOR}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <footer className={`chart-card__delta is-${direction.tone}`}>
        {direction.improved ? '▲' : direction.regressed ? '▼' : '•'}{' '}
        {describeDelta(delta, format, higherIsBetter)} vs baseline
      </footer>
    </article>
  );
}

function describeDelta(delta: number, format: (value: number) => string, higherIsBetter: boolean): string {
  const sign = delta > 0 ? '+' : delta < 0 ? '−' : '';
  const magnitude = format(Math.abs(delta));
  if (higherIsBetter === false && delta < 0) return `${magnitude} reduction`;
  return `${sign}${magnitude}`;
}

export default function CompareCharts({ evaluation }: CompareChartsProps) {
  const row = evaluation.per_scenario[0];
  if (!row) return null;

  const { proposed, baseline } = row;
  const { aggregate } = evaluation;

  return (
    <section className="panel panel--charts" aria-label="Baseline versus optimized comparison">
      <header className="panel__header">
        <div>
          <h2 className="panel__title">Baseline vs optimized</h2>
          <p className="panel__subtitle">
            Same frozen cost model · optimized plan vs FEFO + nearest-first greedy baseline
          </p>
        </div>
      </header>

      <div className="delta-banner" role="status">
        <span className={`delta-banner__item is-${evaluateDelta(aggregate.spoilage_pct_reduction, true).tone}`}>
          {formatRatioSigned(aggregate.spoilage_pct_reduction)} spoilage
        </span>
        <span className="delta-banner__sep" aria-hidden="true">
          ·
        </span>
        <span className={`delta-banner__item is-${evaluateDelta(aggregate.fulfillment_delta, true).tone}`}>
          {formatSignedPoints(aggregate.fulfillment_delta)} fulfillment
        </span>
        <span className="delta-banner__sep" aria-hidden="true">
          ·
        </span>
        <span className={`delta-banner__item is-${evaluateDelta(aggregate.net_revenue_delta, true).tone}`}>
          {formatSignedCurrency(aggregate.net_revenue_delta)} net revenue
        </span>
        <span className="delta-banner__sep" aria-hidden="true">
          ·
        </span>
        <span className={`delta-banner__item ${aggregate.violations_total === 0 ? 'is-good' : 'is-bad'}`}>
          {aggregate.violations_total} constraint violations
        </span>
      </div>

      <div className="chart-grid">
        <ComparisonBar
          title="Net revenue"
          subtitle="Revenue − transport − handling − spoilage (₹)"
          baselineValue={baseline.net_revenue}
          optimizedValue={proposed.net_revenue}
          format={formatCurrency}
        />
        <ComparisonBar
          title="Spoilage"
          subtitle="Unsold / expired inventory (kg)"
          baselineValue={baseline.spoilage_kg}
          optimizedValue={proposed.spoilage_kg}
          format={(value) => `${number1.format(value)} kg`}
          higherIsBetter={false}
        />
        <ComparisonBar
          title="Demand fulfillment"
          subtitle="Served demand as a share of total demand (%)"
          baselineValue={baseline.fulfillment_pct * 100}
          optimizedValue={proposed.fulfillment_pct * 100}
          format={(value) => `${number1.format(value)}%`}
          domain={[0, 100]}
        />
        <CostBreakdown baseline={baseline} proposed={proposed} />
      </div>

      {evaluation.robustness ? (
        <p className="chart-note">
          Robustness (demo): mean net-revenue delta{' '}
          <strong>{formatCurrency(evaluation.robustness.net_revenue_mean)}</strong>, worst-case (P10){' '}
          <strong>{formatCurrency(evaluation.robustness.net_revenue_p10)}</strong>.
        </p>
      ) : null}
    </section>
  );
}

function CostBreakdown({ baseline, proposed }: { baseline: Metrics; proposed: Metrics }) {
  const data = [
    {
      name: 'Baseline',
      transport: baseline.transport_cost,
      handling: baseline.handling_cost,
      spoilage: baseline.spoilage_cost,
    },
    {
      name: 'FreshRoute',
      transport: proposed.transport_cost,
      handling: proposed.handling_cost,
      spoilage: proposed.spoilage_cost,
    },
  ];
  const baselineTotal = baseline.transport_cost + baseline.handling_cost + baseline.spoilage_cost;
  const proposedTotal = proposed.transport_cost + proposed.handling_cost + proposed.spoilage_cost;
  const reduction = baselineTotal > 0 ? 1 - proposedTotal / baselineTotal : 0;
  const direction = evaluateDelta(reduction, true);

  return (
    <article className="chart-card">
      <header className="chart-card__header">
        <h3 className="chart-card__title">Cost breakdown</h3>
        <p className="chart-card__subtitle">Total cost components (₹)</p>
      </header>
      <div className="chart-card__canvas">
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={data} margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
            <XAxis dataKey="name" tickLine={false} axisLine={false} fontSize={12} />
            <YAxis
              tickLine={false}
              axisLine={false}
              fontSize={12}
              width={64}
              tickFormatter={(value: number) => inrCompact.format(value)}
            />
            <Tooltip
              cursor={{ fill: 'rgba(15, 118, 110, 0.06)' }}
              formatter={(value: number) => formatCurrency(value)}
            />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            <Bar dataKey="transport" name="Transport" stackId="cost" fill={COST_COLORS.transport} maxBarSize={72} />
            <Bar dataKey="handling" name="Handling" stackId="cost" fill={COST_COLORS.handling} maxBarSize={72} />
            <Bar
              dataKey="spoilage"
              name="Spoilage"
              stackId="cost"
              fill={COST_COLORS.spoilage}
              radius={[6, 6, 0, 0]}
              maxBarSize={72}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <footer className={`chart-card__delta is-${direction.tone}`}>
        {direction.improved ? '▲' : direction.regressed ? '▼' : '•'} {formatRatioSigned(reduction)}{' '}
        total cost vs baseline · {inr.format(proposedTotal)} vs {inr.format(baselineTotal)}
      </footer>
    </article>
  );
}
