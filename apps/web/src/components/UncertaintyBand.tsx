import { formatCurrency } from '../utils/format';

interface UncertaintyBandProps {
  low: number;
  point: number;
  high: number;
  /** `monte-carlo` = real E4 statistics from the seeded harness; `illustrative` default. */
  mode?: 'monte-carlo' | 'illustrative';
  /** Number of seeded draws (monte-carlo mode). */
  draws?: number;
  /** Scenario the band was computed for (monte-carlo mode). */
  scenarioId?: string;
}

/**
 * Net-revenue range. Two honest modes:
 *  - `illustrative` (default): the spread from the disclosed local demo model across
 *    its input bounds. Deliberately NOT a statistical confidence interval.
 *  - `monte-carlo`: real P10–P90 band from the E4 seeded harness (POST /robustness),
 *    reproducible from `scripts/run_robustness.py`.
 */
export default function UncertaintyBand({
  low,
  point,
  high,
  mode = 'illustrative',
  draws,
  scenarioId,
}: UncertaintyBandProps) {
  const span = high - low;
  const pointPct = span > 0 ? Math.min(100, Math.max(0, ((point - low) / span) * 100)) : 50;
  const isMonteCarlo = mode === 'monte-carlo';

  return (
    <article className="chart-card uncertainty-card">
      <header className="chart-card__header">
        <h3 className="chart-card__title">Net revenue range</h3>
        <p className="chart-card__subtitle">
          {isMonteCarlo
            ? `P10–P90 across ${draws ?? '—'} seeded perturbation draws (E4 Monte Carlo)`
            : 'Illustrative range from the sensitivity model across input bounds'}
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

      {isMonteCarlo ? (
        <p className="uncertainty__note" role="note">
          Verified Monte-Carlo result: the optimizer is re-solved under {draws ?? '—'} random demand,
          travel, price, shelf-life and capacity perturbations
          {scenarioId ? ` (scenario ${scenarioId})` : ''}. Marker = mean; band = P10–P90. Reproducible
          from the seeded harness (<code>scripts/run_robustness.py</code>).
        </p>
      ) : (
        <p className="uncertainty__note" role="note">
          Not a statistical confidence interval. It is the spread produced by the disclosed demo model
          when demand, travel time and price are moved to their slider extremes.
        </p>
      )}
    </article>
  );
}
