import type { Batch, Commodity, Discount, Dispatch } from '../api/types';
import { formatCurrency, formatKg } from '../utils/format';
import { EmptyState } from './StateViews';

interface DiscountSectionProps {
  discounts: Discount[];
  onExplain?: (discount: Discount) => void;
  batches?: Map<string, Batch>;
  commodities?: Map<string, Commodity>;
  dispatchesByBatch?: Map<string, Dispatch>;
}

const inr1 = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 2 });

export default function DiscountSection({
  discounts,
  onExplain,
  batches,
  commodities,
  dispatchesByBatch,
}: DiscountSectionProps) {
  const totalRecovered = discounts.reduce((sum, d) => sum + d.expected_recovered_value, 0);

  return (
    <section className="panel" aria-label="Discount recommendations">
      <header className="panel__header">
        <div>
          <h2 className="panel__title">Discount recommendations</h2>
          <p className="panel__subtitle">
            Rule-based, disclosed · {discounts.length} recommendation
            {discounts.length === 1 ? '' : 's'} · expected value recovered{' '}
            {formatCurrency(totalRecovered)}
          </p>
        </div>
      </header>

      {discounts.length === 0 ? (
        <EmptyState
          title="No discounts needed"
          message="No at-risk batches require a discount in this scenario."
          icon="◎"
        />
      ) : (
        <div className="discount-grid">
          {discounts.map((discount) => {
            const batch = batches?.get(discount.batch_id);
            const commodity = batch ? commodities?.get(batch.commodity_id) : undefined;
            const linked = dispatchesByBatch?.get(discount.batch_id);
            const recoveredPct =
              linked && linked.price_per_kg > 0
                ? discount.expected_recovered_value /
                  (linked.quantity_kg * linked.price_per_kg)
                : undefined;

            return (
              <article className="discount-card" key={`${discount.batch_id}-${discount.rule_id}`}>
                <header className="discount-card__header">
                  <span className="discount-card__batch">{discount.batch_id}</span>
                  <span className="discount-card__pct">
                    {(discount.discount_pct * 100).toFixed(0)}% off
                  </span>
                </header>

                {commodity ? (
                  <div className="discount-card__commodity">
                    {commodity.name}
                    <span className="discount-card__class"> · {commodity.perishability_class}</span>
                  </div>
                ) : null}

                <div className="discount-card__rule" title="Discount rule identifier">
                  {discount.rule_id}
                </div>

                <dl className="discount-card__meta">
                  {batch ? (
                    <div>
                      <dt>Batch qty</dt>
                      <dd>{formatKg(batch.quantity_kg)}</dd>
                    </div>
                  ) : null}
                  {batch ? (
                    <div>
                      <dt>Remaining shelf life</dt>
                      <dd>{inr1.format(batch.remaining_shelf_life_days)} d</dd>
                    </div>
                  ) : null}
                  {linked ? (
                    <div>
                      <dt>Linked dispatch</dt>
                      <dd>
                        {linked.destination_id} · {linked.feasible ? 'feasible' : 'infeasible'}
                      </dd>
                    </div>
                  ) : null}
                </dl>

                <p className="discount-card__reason">{discount.reason}</p>

                <footer className="discount-card__footer">
                  <span className="discount-card__footer-label">Expected recovered value</span>
                  <span className="discount-card__footer-value">
                    {formatCurrency(discount.expected_recovered_value)}
                    {recoveredPct !== undefined ? (
                      <span className="discount-card__pct-of">
                        {' '}
                        ({(recoveredPct * 100).toFixed(0)}% of list)
                      </span>
                    ) : null}
                  </span>
                </footer>

                {onExplain ? (
                  <button
                    type="button"
                    className="btn btn--ghost btn--xs discount-card__explain"
                    onClick={() => onExplain(discount)}
                  >
                    Explain recommendation
                  </button>
                ) : null}
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}
