import type { ReactNode } from 'react';
import type { Metrics } from '../api/types';
import {
  formatCurrency,
  formatKg,
  formatPercent,
  formatRatioSigned,
  formatSignedCurrency,
  formatSignedPoints,
} from '../utils/format';
import { compareToBaseline, totalCostOf, type Direction } from '../utils/metrics';
import ViolationBadge from './ViolationBadge';

interface KpiCardsProps {
  metrics: Metrics;
  baseline?: Metrics;
  violations: string[];
  degraded: boolean;
}

type Tone = 'good' | 'bad' | 'neutral';

interface KpiCardProps {
  label: string;
  value: string;
  sub?: string;
  delta?: ReactNode;
  tone?: Tone;
  accent: string;
}

function toneOf(direction: Direction | undefined): Tone {
  return direction ? direction.tone : 'neutral';
}

function DeltaArrow({ direction }: { direction: Direction }) {
  if (direction.improved) return <span aria-hidden="true">▲</span>;
  if (direction.regressed) return <span aria-hidden="true">▼</span>;
  return <span aria-hidden="true">•</span>;
}

function KpiCard({ label, value, sub, delta, tone = 'neutral', accent }: KpiCardProps) {
  return (
    <article className="kpi-card" style={{ ['--accent' as string]: accent }}>
      <header className="kpi-card__header">
        <span className="kpi-card__label">{label}</span>
      </header>
      <p className="kpi-card__value">{value}</p>
      {sub ? <p className="kpi-card__sub">{sub}</p> : null}
      {delta ? <p className={`kpi-card__delta kpi-card__delta--${tone}`}>{delta}</p> : null}
    </article>
  );
}

export default function KpiCards({ metrics, baseline, violations, degraded }: KpiCardsProps) {
  const deltas = baseline ? compareToBaseline(metrics, baseline) : null;

  return (
    <section className="kpi-grid" aria-label="Key performance indicators">
      <KpiCard
        label="Net revenue"
        value={formatCurrency(metrics.net_revenue)}
        sub={`Revenue ${formatCurrency(metrics.revenue)} · costs ${formatCurrency(totalCostOf(metrics))}`}
        accent="#0f766e"
        tone={toneOf(deltas?.netRevenue.direction)}
        delta={
          deltas ? (
            <>
              <DeltaArrow direction={deltas.netRevenue.direction} />
              {formatSignedCurrency(deltas.netRevenue.delta)}
              {deltas.netRevenue.deltaPct !== null
                ? ` (${formatRatioSigned(deltas.netRevenue.deltaPct)})`
                : ''}{' '}
              vs baseline
            </>
          ) : undefined
        }
      />

      <KpiCard
        label="Spoilage"
        value={formatKg(metrics.spoilage_kg)}
        sub={`${formatPercent(metrics.spoilage_pct)} of inventory · cost ${formatCurrency(
          metrics.spoilage_cost,
        )}`}
        accent="#b45309"
        tone={toneOf(deltas?.spoilage.direction)}
        delta={
          deltas && deltas.spoilageReductionPct !== null ? (
            <>
              <DeltaArrow direction={deltas.spoilage.direction} />
              {formatRatioSigned(deltas.spoilageReductionPct)} spoilage vs baseline
            </>
          ) : undefined
        }
      />

      <KpiCard
        label="Demand fulfillment"
        value={formatPercent(metrics.fulfillment_pct)}
        sub={`${formatKg(metrics.fulfilled_kg)} served · ${formatKg(metrics.unmet_kg)} unmet`}
        accent="#1d4ed8"
        tone={toneOf(deltas?.fulfillment.direction)}
        delta={
          deltas ? (
            <>
              <DeltaArrow direction={deltas.fulfillment.direction} />
              {formatSignedPoints(deltas.fulfillment.delta)} vs baseline
            </>
          ) : undefined
        }
      />

      <article className="kpi-card kpi-card--badge" style={{ ['--accent' as string]: '#15803d' }}>
        <header className="kpi-card__header">
          <span className="kpi-card__label">Feasibility</span>
        </header>
        <ViolationBadge violations={violations} degraded={degraded} size="lg" />
      </article>
    </section>
  );
}
