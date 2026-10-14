import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  explain,
  getEvaluation,
  getHealth,
  getInventory,
  getPlan,
  getRobustness,
  getScenarios,
} from '../api/client';
import type {
  Batch,
  Commodity,
  DataSource,
  Dispatch,
  Discount,
  EvalResponse,
  InventoryResponse,
  PlanResponse,
  RobustnessBand,
  Scenario,
} from '../api/types';
import ApiStatusBanner, { type ApiStatus } from '../components/ApiStatusBanner';
import CompareCharts from '../components/CompareCharts';
import DiscountSection from '../components/DiscountSection';
import DispatchTable from '../components/DispatchTable';
import ExplainDrawer from '../components/ExplainDrawer';
import KpiCards from '../components/KpiCards';
import ReplanFeed from '../components/ReplanFeed';
import ScenarioSelector from '../components/ScenarioSelector';
import SensitivityPanel from '../components/SensitivityPanel';
import { EmptyState, ErrorState, LoadingState, SkeletonBlock } from '../components/StateViews';
import ViolationBadge from '../components/ViolationBadge';
import { buildDiscountExplain, buildDispatchExplain, type ExplainModel } from '../utils/explain';

type LoadStatus = 'loading' | 'error' | 'ready';
type RunStatus = 'idle' | 'loading' | 'error' | 'ready';

/** Seeded draws for the E4 Monte-Carlo band (matches the harness's reproducibility scale). */
const ROBUSTNESS_DRAWS = 20;

function describeError(error: unknown): string {
  if (error instanceof Error) return error.message;
  return 'Unexpected error';
}

export default function Dashboard() {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [scenariosStatus, setScenariosStatus] = useState<LoadStatus>('loading');
  const [scenariosError, setScenariosError] = useState('');
  const [scenariosSource, setScenariosSource] = useState<DataSource>('live');
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const [runStatus, setRunStatus] = useState<RunStatus>('idle');
  const [plan, setPlan] = useState<PlanResponse | null>(null);
  const [evaluation, setEvaluation] = useState<EvalResponse | null>(null);
  const [robustness, setRobustness] = useState<RobustnessBand | null>(null);
  const [runSource, setRunSource] = useState<DataSource>('live');
  const [runNotice, setRunNotice] = useState<string | null>(null);
  const [runError, setRunError] = useState('');

  const [apiStatus, setApiStatus] = useState<ApiStatus>('checking');
  const [apiDetail, setApiDetail] = useState<string | undefined>(undefined);

  const [inventory, setInventory] = useState<InventoryResponse | null>(null);

  const [explainModel, setExplainModel] = useState<ExplainModel | null>(null);
  const [explainLoading, setExplainLoading] = useState(false);

  const runIdRef = useRef(0);
  const explainIdRef = useRef(0);
  const robustnessIdRef = useRef(0);

  const loadScenarios = useCallback(async () => {
    setScenariosStatus('loading');
    setScenariosError('');
    try {
      const result = await getScenarios();
      setScenarios(result.data);
      setScenariosSource(result.source);
      setSelectedId((prev) => prev ?? result.data[0]?.scenario_id ?? null);
      setScenariosStatus('ready');
    } catch (error) {
      setScenariosError(describeError(error));
      setScenariosStatus('error');
    }
  }, []);

  useEffect(() => {
    void loadScenarios();
  }, [loadScenarios]);

  useEffect(() => {
    let cancelled = false;

    void (async () => {
      const health = await getHealth();
      if (cancelled) return;
      if (health) {
        setApiStatus('connected');
        setApiDetail(health.version ? `API v${health.version}` : undefined);
      } else {
        setApiStatus('unavailable');
        setApiDetail(undefined);
      }
    })();

    void (async () => {
      const result = await getInventory();
      if (cancelled) return;
      setInventory(result.data);
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  const runOptimize = useCallback(async () => {
    if (!selectedId) return;
    const runId = runIdRef.current + 1;
    runIdRef.current = runId;

    setRunStatus('loading');
    setRunError('');
    setRunNotice(null);
    setExplainModel(null);

    try {
      const [planResult, evalResult] = await Promise.all([
        getPlan(selectedId),
        getEvaluation([selectedId]),
      ]);
      if (runId !== runIdRef.current) return;

      setPlan(planResult.data);
      setEvaluation(evalResult.data);

      const source: DataSource =
        planResult.source === 'demo' || evalResult.source === 'demo' ? 'demo' : 'live';
      setRunSource(source);

      const fallbackError = planResult.error ?? evalResult.error;
      setRunNotice(source === 'demo' ? fallbackError ?? 'Showing synthetic demo data.' : null);
      setRunStatus('ready');
    } catch (error) {
      if (runId !== runIdRef.current) return;
      setRunError(describeError(error));
      setRunStatus('error');
    }
  }, [selectedId]);

  // Fetch the real E4 Monte-Carlo band in the background once a plan is ready.
  // Never blocks the main run; on failure the panel keeps its illustrative band.
  useEffect(() => {
    if (runStatus !== 'ready' || !plan) {
      setRobustness(null);
      return;
    }
    const id = robustnessIdRef.current + 1;
    robustnessIdRef.current = id;

    void (async () => {
      const result = await getRobustness([plan.scenario_id], ROBUSTNESS_DRAWS);
      if (id !== robustnessIdRef.current) return;
      setRobustness(result.available ? result.data : null);
    })();
  }, [runStatus, plan]);

  function handleSelect(scenarioId: string) {
    setSelectedId(scenarioId);
    setRunStatus('idle');
    setPlan(null);
    setEvaluation(null);
    setRobustness(null);
    setRunNotice(null);
    setRunError('');
    setExplainModel(null);
  }

  const inventoryMaps = useMemo(() => {
    const batches = new Map<string, Batch>();
    const commodities = new Map<string, Commodity>();
    if (inventory) {
      for (const batch of inventory.batches) batches.set(batch.batch_id, batch);
      for (const commodity of inventory.commodities) commodities.set(commodity.commodity_id, commodity);
    }
    return { batches, commodities };
  }, [inventory]);

  const dispatchesByBatch = useMemo(() => {
    const map = new Map<string, Dispatch>();
    if (plan) {
      for (const dispatch of plan.dispatches) map.set(dispatch.batch_id, dispatch);
    }
    return map;
  }, [plan]);

  const openDispatchExplain = useCallback(
    async (dispatch: Dispatch) => {
      if (!plan) return;
      const explainId = explainIdRef.current + 1;
      explainIdRef.current = explainId;
      setExplainModel(null);
      setExplainLoading(true);

      const endpoint = await explain(dispatch.batch_id, dispatch.destination_id);
      if (explainId !== explainIdRef.current) return;

      setExplainModel(
        buildDispatchExplain(dispatch, {
          ...inventoryMaps,
          dispatchesByBatch,
          source: runSource,
          endpoint,
        }),
      );
      setExplainLoading(false);
    },
    [plan, inventoryMaps, dispatchesByBatch, runSource],
  );

  const openDiscountExplain = useCallback(
    async (discount: Discount) => {
      if (!plan) return;
      const explainId = explainIdRef.current + 1;
      explainIdRef.current = explainId;
      setExplainModel(null);
      setExplainLoading(true);

      const linked = dispatchesByBatch.get(discount.batch_id);
      const endpoint = await explain(discount.batch_id, linked?.destination_id ?? '');
      if (explainId !== explainIdRef.current) return;

      setExplainModel(
        buildDiscountExplain(discount, {
          ...inventoryMaps,
          dispatchesByBatch,
          source: runSource,
          endpoint,
        }),
      );
      setExplainLoading(false);
    },
    [plan, inventoryMaps, dispatchesByBatch, runSource],
  );

  const closeExplain = useCallback(() => {
    explainIdRef.current += 1;
    setExplainModel(null);
    setExplainLoading(false);
  }, []);

  const activeSource = runStatus === 'ready' ? runSource : scenariosSource;
  const selectedScenario = useMemo(
    () => scenarios.find((s) => s.scenario_id === selectedId),
    [scenarios, selectedId],
  );

  return (
    <div className="app">
      <header className="app-header">
        <div className="app-header__brand">
          <span className="app-logo" aria-hidden="true">
            ❧
          </span>
          <div>
            <h1 className="app-title">FreshRoute</h1>
            <p className="app-subtitle">
              Decision support for perishable produce distribution · dispatch-where-discount
            </p>
          </div>
        </div>
        <div className="app-header__status">
          {plan ? (
            <ViolationBadge violations={plan.validation.violations} degraded={plan.validation.degraded} />
          ) : null}
        </div>
      </header>

      <main className="app-main">
        <ApiStatusBanner status={apiStatus} detail={apiDetail} />

        <ScenarioSelector
          scenarios={scenarios}
          selectedId={selectedId}
          loading={runStatus === 'loading' || scenariosStatus === 'loading'}
          source={activeSource}
          onSelect={handleSelect}
          onOptimize={() => void runOptimize()}
        />

        {scenariosStatus === 'loading' ? (
          <section className="panel">
            <LoadingState title="Loading scenarios" message="Contacting the FreshRoute API…" />
            <SkeletonBlock lines={4} />
          </section>
        ) : scenariosStatus === 'error' ? (
          <section className="panel">
            <ErrorState
              title="Could not load scenarios"
              message={`${scenariosError} — check that the API is running, or start in demo mode.`}
              onRetry={() => void loadScenarios()}
            />
          </section>
        ) : scenarios.length === 0 ? (
          <section className="panel">
            <EmptyState
              title="No scenarios"
              message="The API returned no scenarios. Generate the synthetic dataset and reload."
              icon="▤"
            />
          </section>
        ) : runStatus === 'idle' ? (
          <section className="panel">
            <EmptyState
              title="Ready to optimize"
              message={
                selectedScenario
                  ? `Run the optimizer on “${selectedScenario.scenario_id}” to see the dispatch plan, discounts, and the baseline comparison.`
                  : 'Select a scenario, then press Optimize.'
              }
              icon="❧"
              action={
                <button
                  type="button"
                  className="btn btn--primary btn--lg"
                  disabled={!selectedId}
                  onClick={() => void runOptimize()}
                >
                  Optimize plan
                </button>
              }
            />
          </section>
        ) : runStatus === 'loading' ? (
          <section className="panel">
            <LoadingState title="Optimizing" message="Solving allocations and computing metrics…" />
            <div className="kpi-grid">
              <SkeletonBlock lines={3} />
              <SkeletonBlock lines={3} />
              <SkeletonBlock lines={3} />
              <SkeletonBlock lines={3} />
            </div>
          </section>
        ) : runStatus === 'error' ? (
          <section className="panel">
            <ErrorState
              title="Optimization failed"
              message={`${runError} — retry, or check the API logs.`}
              onRetry={() => void runOptimize()}
            />
          </section>
        ) : plan ? (
          <div className="dashboard-stack">
            {runNotice ? (
              <div className="notice" role="status">
                <span className="notice__icon" aria-hidden="true">
                  ⓘ
                </span>
                <span>
                  {runSource === 'demo'
                    ? `Live API unavailable (${runNotice}). Showing clearly-labelled demo data that matches the documented schema — not an evaluation result.`
                    : runNotice}
                </span>
              </div>
            ) : null}

            <KpiCards
              metrics={plan.metrics}
              baseline={evaluation?.per_scenario[0]?.baseline}
              violations={plan.validation.violations}
              degraded={plan.validation.degraded}
            />

            {evaluation ? (
              <CompareCharts evaluation={evaluation} robustness={robustness} />
            ) : null}

            <DispatchTable
              dispatches={plan.dispatches}
              onExplain={(dispatch) => void openDispatchExplain(dispatch)}
            />

            <DiscountSection
              discounts={plan.discounts}
              batches={inventoryMaps.batches}
              commodities={inventoryMaps.commodities}
              dispatchesByBatch={dispatchesByBatch}
              onExplain={(discount) => void openDiscountExplain(discount)}
            />

            <div className="whatif-grid">
              <SensitivityPanel plan={plan} source={runSource} robustness={robustness} />
              <ReplanFeed plan={plan} />
            </div>
          </div>
        ) : null}
      </main>

      <footer className="app-footer">
        <span>
          {activeSource === 'demo'
            ? 'Demo data — synthetic and schema-compatible.'
            : 'Live API data.'}{' '}
          Workstream C frontend.
        </span>
        {plan ? (
          <span className="app-footer__meta">
            scenario {plan.scenario_id} · config {plan.config_hash} · as of {plan.now_ts}
          </span>
        ) : null}
      </footer>

      <ExplainDrawer model={explainModel} loading={explainLoading} onClose={closeExplain} />
    </div>
  );
}
