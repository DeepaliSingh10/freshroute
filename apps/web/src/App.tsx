import { useCallback, useEffect, useState } from 'react'
import { api } from './api'
import KpiCards from './components/KpiCards'
import DispatchTable from './components/DispatchTable'
import DiscountCards from './components/DiscountCards'
import ComparisonChart from './components/ComparisonChart'
import SensitivitySliders from './components/SensitivitySliders'
import ReplanPanel from './components/ReplanPanel'
import ExplainDrawer from './components/ExplainDrawer'
import type {
  EvaluateResponse,
  ExplainResponse,
  PlanResponse,
  ReplanResponse,
  ScenarioInfo,
  SensitivityResponse,
} from './types'

export default function App() {
  const [scenarios, setScenarios] = useState<ScenarioInfo[]>([])
  const [scenarioId, setScenarioId] = useState('')
  const [hash, setHash] = useState('')
  const [plan, setPlan] = useState<PlanResponse>()
  const [evaluate, setEvaluate] = useState<EvaluateResponse>()
  const [replan, setReplan] = useState<ReplanResponse>()
  const [explain, setExplain] = useState<ExplainResponse>()
  const [sensitivity, setSensitivity] = useState<SensitivityResponse>()
  const [loading, setLoading] = useState(false)
  const [replanLoading, setReplanLoading] = useState(false)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    api
      .health()
      .then((h) => setHash(h.cost_model_hash))
      .catch((e) => setError(String(e)))
    api
      .scenarios()
      .then((s) => {
        setScenarios(s)
        if (s.length) setScenarioId(s[s.length - 1].scenario_id)
      })
      .catch((e) => setError(String(e)))
  }, [])

  const loadScenario = useCallback(async (id: string) => {
    if (!id) return
    setLoading(true)
    setError('')
    setReplan(undefined)
    try {
      const [p, ev, ex, sens] = await Promise.all([
        api.plan(id),
        api.evaluate(id, 'fefo'),
        api.explain(id),
        api.sensitivity(id),
      ])
      setPlan(p)
      setEvaluate(ev)
      setExplain(ex)
      setSensitivity(sens)
    } catch (e) {
      setError(String(e))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadScenario(scenarioId)
  }, [scenarioId, loadScenario])

  const runReplan = async (delay: number) => {
    setReplanLoading(true)
    try {
      setReplan(await api.replan(scenarioId, delay))
    } catch (e) {
      setError(String(e))
    } finally {
      setReplanLoading(false)
    }
  }

  return (
    <>
      <header className="top">
        <div>
          <h1>FreshRoute</h1>
          <div className="sub">Intelligent decision support for perishable produce distribution</div>
        </div>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          {plan && (
            <span className={`badge ${plan.violations === 0 ? 'ok' : 'warn'}`}>
              {plan.violations === 0 ? '0 constraint violations' : `${plan.violations} violations`}
            </span>
          )}
          <span className="muted">model {hash.slice(0, 10)}</span>
        </div>
      </header>

      <main>
        <div className="toolbar">
          <label className="muted">
            scenario{' '}
            <select value={scenarioId} onChange={(e) => setScenarioId(e.target.value)}>
              {scenarios.map((s) => (
                <option key={s.scenario_id} value={s.scenario_id}>
                  {s.scenario_id} ({s.split})
                </option>
              ))}
            </select>
          </label>
          <button onClick={() => void loadScenario(scenarioId)} disabled={loading}>
            {loading ? 'Optimizing…' : 'Re-run optimizer'}
          </button>
          <button onClick={() => setDrawerOpen(true)} disabled={!explain}>
            Explainability ({explain?.reasons.length ?? 0})
          </button>
          {error && <span className="error">{error}</span>}
        </div>

        {loading && !plan && <p className="muted">Loading scenario…</p>}

        {plan && (
          <>
            <KpiCards plan={plan} evaluate={evaluate} />
            {evaluate && <ComparisonChart evaluate={evaluate} />}
            <div className="grid two" style={{ marginTop: 14 }}>
              <DispatchTable dispatches={plan.dispatches} />
              <DiscountCards discounts={plan.discounts} />
            </div>
            {sensitivity && <div style={{ marginTop: 14 }}><SensitivitySliders curves={sensitivity.curves} /></div>}
            <div style={{ marginTop: 14 }}>
              <ReplanPanel replan={replan} loading={replanLoading} onRun={runReplan} />
            </div>
          </>
        )}
      </main>

      <ExplainDrawer open={drawerOpen} reasons={explain?.reasons ?? []} onClose={() => setDrawerOpen(false)} />
    </>
  )
}
