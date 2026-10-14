import { useMemo, useState } from 'react'
import type { Dispatch } from '../types'

const fmt = (n: number, d = 0) => n.toLocaleString(undefined, { maximumFractionDigits: d })

type SortKey = 'quantity_kg' | 'margin_per_kg' | 'travel_hours'

export default function DispatchTable({ dispatches }: { dispatches: Dispatch[] }) {
  const [showClearance, setShowClearance] = useState(true)
  const [sort, setSort] = useState<SortKey>('quantity_kg')

  const rows = useMemo(() => {
    const filtered = dispatches.filter((d) => showClearance || !d.is_clearance)
    return [...filtered].sort((a, b) => b[sort] - a[sort])
  }, [dispatches, showClearance, sort])

  return (
    <div className="card">
      <h3>Allocation plan ({rows.length} dispatches)</h3>
      <div className="toolbar">
        <label className="muted">
          <input type="checkbox" checked={showClearance} onChange={(e) => setShowClearance(e.target.checked)} />{' '}
          include clearance
        </label>
        <label className="muted">
          sort by{' '}
          <select value={sort} onChange={(e) => setSort(e.target.value as SortKey)}>
            <option value="quantity_kg">quantity</option>
            <option value="margin_per_kg">margin</option>
            <option value="travel_hours">travel hours</option>
          </select>
        </label>
      </div>
      <div className="scroll">
        <table>
          <thead>
            <tr>
              <th>Batch</th>
              <th>Commodity</th>
              <th>Destination</th>
              <th>Qty (kg)</th>
              <th>Price ₹/kg</th>
              <th>Margin ₹/kg</th>
              <th>Transit (h)</th>
              <th>Channel</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((d, i) => (
              <tr key={`${d.batch_id}-${d.destination_id}-${i}`} title={d.reason}>
                <td>{d.batch_id}</td>
                <td>{d.commodity_name}</td>
                <td>{d.destination_name}</td>
                <td>{fmt(d.quantity_kg)}</td>
                <td>{fmt(d.price_per_kg, 2)}</td>
                <td>{fmt(d.margin_per_kg, 2)}</td>
                <td>{fmt(d.travel_hours, 1)}</td>
                <td>{d.is_clearance ? <span className="tag clr">clearance</span> : <span className="tag">market</span>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
