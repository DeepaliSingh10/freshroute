import type { EvaluateResponse, PlanResponse } from '../types'

interface Props {
  plan: PlanResponse
  evaluate?: EvaluateResponse
}

const fmt = (n: number, digits = 0) => n.toLocaleString(undefined, { maximumFractionDigits: digits })

export default function KpiCards({ plan, evaluate }: Props) {
  const m = plan.metrics
  const cmp = evaluate?.compare
  const spoilRed = cmp ? cmp.spoilage_pct_reduction * 100 : undefined
  const revDelta = cmp ? cmp.net_revenue_delta : undefined

  return (
    <div className="grid kpis">
      <div className="card kpi">
        <h3>Spoilage</h3>
        <div className="value">{fmt(m.spoilage_kg)} kg</div>
        <div className={`delta ${spoilRed !== undefined && spoilRed < 0 ? 'neg' : ''}`}>
          {spoilRed !== undefined ? `${spoilRed >= 0 ? '−' : '+'}${Math.abs(spoilRed).toFixed(1)}% vs FEFO` : '—'}
        </div>
      </div>

      <div className="card kpi">
        <h3>Fulfillment</h3>
        <div className="value">{(m.fulfillment_pct * 100).toFixed(1)}%</div>
        <div className="delta">{fmt(m.fulfilled_kg)} / {fmt(m.demand_kg)} kg demand</div>
      </div>

      <div className="card kpi">
        <h3>Net revenue</h3>
        <div className="value">₹{fmt(m.net_revenue)}</div>
        <div className="delta">{revDelta !== undefined ? `+₹${fmt(revDelta)} vs FEFO` : '—'}</div>
      </div>

      <div className="card kpi">
        <h3>Recovered (clearance)</h3>
        <div className="value">{fmt(m.clearance_kg)} kg</div>
        <div className="delta">₹{fmt(m.clearance_revenue)} salvaged</div>
      </div>

      <div className="card kpi">
        <h3>Hard violations</h3>
        <div className="value">{plan.violations}</div>
        <div className={`delta ${plan.violations > 0 ? 'neg' : ''}`}>
          {plan.violations === 0 ? 'all constraints satisfied' : 'check failed'}
        </div>
      </div>
    </div>
  )
}
