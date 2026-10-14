import { useState } from 'react'
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { SensCurve } from '../types'

const fmt = (n: number) => n.toLocaleString(undefined, { maximumFractionDigits: 0 })

export default function SensitivitySliders({ curves }: { curves: Record<string, SensCurve> }) {
  const keys = Object.keys(curves)
  const [factor, setFactor] = useState(keys[0] ?? '')
  const active: SensCurve | undefined = curves[factor]

  if (!active) return null

  const data = active.points.map((p) => ({
    value: p.value,
    FreshRoute: p.optimizer.net_revenue,
    Baseline: p.baseline.net_revenue,
    spoilage_reduction_pct: p.spoilage_reduction_pct,
  }))

  return (
    <div className="card">
      <h3>Sensitivity — net revenue vs factor</h3>
      <div className="toolbar">
        <label className="muted">
          factor{' '}
          <select value={factor} onChange={(e) => setFactor(e.target.value)}>
            {keys.map((k) => (
              <option key={k} value={k}>
                {curves[k].label}
              </option>
            ))}
          </select>
        </label>
        <span className="muted">
          spoilage reduction {Math.min(...active.points.map((p) => p.spoilage_reduction_pct)).toFixed(1)}% …{' '}
          {Math.max(...active.points.map((p) => p.spoilage_reduction_pct)).toFixed(1)}%
        </span>
      </div>
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={data}>
          <CartesianGrid stroke="#2a3b4d" />
          <XAxis dataKey="value" stroke="#93a4b5" fontSize={12} />
          <YAxis stroke="#93a4b5" fontSize={12} tickFormatter={fmt} />
          <Tooltip contentStyle={{ background: '#17222e', border: '1px solid #2a3b4d' }} formatter={(v: number) => `₹${fmt(v)}`} />
          <Legend />
          <Line type="monotone" dataKey="FreshRoute" stroke="#37c98b" strokeWidth={2} dot />
          <Line type="monotone" dataKey="Baseline" stroke="#8a93a4" strokeWidth={2} dot />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
