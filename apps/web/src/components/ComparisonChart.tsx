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
} from 'recharts'
import type { EvaluateResponse } from '../types'

const fmt = (n: number) => n.toLocaleString(undefined, { maximumFractionDigits: 0 })

export default function ComparisonChart({ evaluate }: { evaluate: EvaluateResponse }) {
  const { optimizer: o, baseline_metrics: b, baseline } = evaluate

  const spoilage = [
    { name: `FEFO (${baseline})`, value: b.spoilage_kg, fill: '#e0604a' },
    { name: 'FreshRoute', value: o.spoilage_kg, fill: '#37c98b' },
  ]
  const revenue = [
    { name: `FEFO (${baseline})`, value: b.net_revenue, fill: '#8a93a4' },
    { name: 'FreshRoute', value: o.net_revenue, fill: '#4a9de0' },
  ]

  return (
    <div className="grid two">
      <div className="card">
        <h3>Spoilage (kg) — lower is better</h3>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={spoilage}>
            <CartesianGrid stroke="#2a3b4d" vertical={false} />
            <XAxis dataKey="name" stroke="#93a4b5" fontSize={12} />
            <YAxis stroke="#93a4b5" fontSize={12} tickFormatter={fmt} />
            <Tooltip
              contentStyle={{ background: '#17222e', border: '1px solid #2a3b4d' }}
              formatter={(v: number) => [`${fmt(v)} kg`, '']}
            />
            <Bar dataKey="value">
              {spoilage.map((d) => (
                <Cell key={d.name} fill={d.fill} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="card">
        <h3>Net revenue (₹) — higher is better</h3>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={revenue}>
            <CartesianGrid stroke="#2a3b4d" vertical={false} />
            <XAxis dataKey="name" stroke="#93a4b5" fontSize={12} />
            <YAxis stroke="#93a4b5" fontSize={12} tickFormatter={fmt} />
            <Tooltip
              contentStyle={{ background: '#17222e', border: '1px solid #2a3b4d' }}
              formatter={(v: number) => [`₹${fmt(v)}`, '']}
            />
            <Legend />
            <Bar dataKey="value" name="Net revenue">
              {revenue.map((d) => (
                <Cell key={d.name} fill={d.fill} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
