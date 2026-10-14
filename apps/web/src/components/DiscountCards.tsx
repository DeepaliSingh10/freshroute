import type { Discount } from '../types'

const fmt = (n: number, d = 0) => n.toLocaleString(undefined, { maximumFractionDigits: d })

export default function DiscountCards({ discounts }: { discounts: Discount[] }) {
  const recovered = discounts.reduce((s, d) => s + d.expected_recovered_value, 0)
  return (
    <div className="card">
      <h3>Discount recommendations ({discounts.length}) · ₹{fmt(recovered)} recoverable</h3>
      <div className="scroll">
        {discounts.length === 0 && <p className="muted">No at-risk batches in this plan.</p>}
        {discounts.map((d) => (
          <div className="discount" key={`${d.batch_id}-${d.rule_id}`}>
            <div className="rule">
              {d.rule_id} · {d.batch_id} · {(d.discount_pct * 100).toFixed(0)}% off · {fmt(d.quantity_kg)} kg
            </div>
            <div className="reason">{d.reason}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
