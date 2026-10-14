import { useState } from 'react'
import type { ReplanResponse } from '../types'

const fmt = (n: number, d = 0) => n.toLocaleString(undefined, { maximumFractionDigits: d })

interface Props {
  replan?: ReplanResponse
  loading: boolean
  onRun: (travelDelayHours: number) => void
}

export default function ReplanPanel({ replan, loading, onRun }: Props) {
  const [delay, setDelay] = useState(6)

  return (
    <div className="card">
      <h3>Disruption replan (E3)</h3>
      <div className="toolbar">
        <label className="muted">
          network delay <b>{delay}h</b>
          <input
            type="range"
            min={0}
            max={12}
            value={delay}
            onChange={(e) => setDelay(Number(e.target.value))}
          />
        </label>
        <button className="primary" disabled={loading} onClick={() => onRun(delay)}>
          {loading ? 'Replanning…' : 'Simulate disruption & replan'}
        </button>
      </div>

      {!replan && <p className="muted">Trigger a hub outage + delay to compare “do nothing” vs replanning.</p>}

      {replan && (
        <>
          <p className="muted">
            Blocked hub: <b>{replan.blocked_origins.join(', ')}</b> — delay {replan.travel_delay_hours}h
          </p>
          <table>
            <thead>
              <tr>
                <th>Plan</th>
                <th>Spoilage (kg)</th>
                <th>Fulfilled (kg)</th>
                <th>Net revenue ₹</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>Morning (pre-disruption)</td>
                <td>{fmt(replan.morning_plan.spoilage_kg)}</td>
                <td>{fmt(replan.morning_plan.fulfilled_kg)}</td>
                <td>{fmt(replan.morning_plan.net_revenue)}</td>
              </tr>
              <tr>
                <td>No replan (frozen)</td>
                <td>{fmt(replan.no_replan.spoilage_kg)}</td>
                <td>{fmt(replan.no_replan.fulfilled_kg)}</td>
                <td>{fmt(replan.no_replan.net_revenue)}</td>
              </tr>
              <tr>
                <td>
                  <b>Replan</b>
                </td>
                <td>{fmt(replan.replan.spoilage_kg)}</td>
                <td>{fmt(replan.replan.fulfilled_kg)}</td>
                <td>{fmt(replan.replan.net_revenue)}</td>
              </tr>
            </tbody>
          </table>
          <p className="muted" style={{ marginTop: 8 }}>
            Recovery: spoilage −{(replan.recovery.spoilage_pct_reduction * 100).toFixed(1)}% · net revenue{' '}
            +₹{fmt(replan.recovery.net_revenue_delta)} · violations {replan.violations_replan}
          </p>
        </>
      )}
    </div>
  )
}
