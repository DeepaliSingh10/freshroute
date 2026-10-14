import { formatCurrency } from '../utils/format';

interface UncertaintyBandProps {
  low: number;
  point: number;
  high: number;
}

/**
 * Illustrative range of net revenue from the local sensitivity model.
 * Deliberately NOT a statistical confidence interval — the label says so.
 */
export default function UncertaintyBand({ low, point, high }: UncertaintyBandProps) {
  const span = high - low;
  const pointPct = span > 0 ? Math.min(100, Math.max(0, ((point - low) / span) * 100)) : 50;

  return (
    <article className="chart-card uncertainty-card">
      <header className="chart-card__header">
        <h3 className="chart-card__title">Net revenue range</h3>
        <p className="chart-card__subtitle">
          Illustrative range from the sensitivity model across input bounds
        </p>
      </header>

      <div className="uncertainty">
        <div className="uncertainty__track" aria-hidden="true">
          <span className="uncertainty__fill" />
          <span className="uncertainty__point" style={{ left: `${pointPct}%` }} />
        </div>
        <div className="uncertainty__labels">
          <span>{formatCurrency(low)}</span>
          <strong>{formatCurrency(point)}</strong>
          <span>{formatCurrency(high)}</span>
        </div>
      </div>

      <p className="uncertainty__note" role="note">
        Not a statistical confidence interval. It is the spread produced by the disclosed demo model
        when demand, travel time and price are moved to their slider extremes.
      </p>
    </article>
  );
}
