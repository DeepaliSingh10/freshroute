import type { Reason } from '../types'

interface Props {
  open: boolean
  reasons: Reason[]
  onClose: () => void
}

export default function ExplainDrawer({ open, reasons, onClose }: Props) {
  return (
    <div className={`drawer ${open ? 'open' : ''}`}>
      <div className="toolbar">
        <h3 style={{ margin: 0 }}>Why this plan? ({reasons.length})</h3>
        <button onClick={onClose}>close</button>
      </div>
      <p className="muted">
        Every dispatch and discount carries a plain-language reason (target: 100% coverage).
      </p>
      {reasons.map((r, i) => (
        <div className="reason-item" key={`${r.kind}-${r.ref}-${i}`}>
          <div className="badge ok" style={{ marginBottom: 4 }}>{r.kind}</div>
          <div>{r.reason}</div>
        </div>
      ))}
    </div>
  )
}
