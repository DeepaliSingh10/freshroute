/**
 * API client for the FreshRoute FastAPI service (Workstream B).
 *
 * Every call attempts the live API first. If the service is unreachable or returns
 * an error, the call transparently falls back to clearly-labelled demo fixtures so
 * the dashboard remains fully demonstrable. Callers receive `source` on every
 * response and must surface it in the UI.
 */
import type {
  EvalResponse,
  ExplainResponse,
  ExplainResult,
  HealthResponse,
  InventoryResponse,
  PlanResponse,
  ReplanEvent,
  ReplanResponse,
  ReplanResult,
  Scenario,
  Sourced,
} from './types';
import { DEMO_SCENARIOS, getDemoEval, getDemoInventory, getDemoPlan } from './mockData';

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? '/api').replace(/\/$/, '');

const REQUEST_TIMEOUT_MS = 8000;
const DEMO_LATENCY_MS = 350;
const STRICT_API = import.meta.env.VITE_STRICT_API === 'true';

function demoRequested(): boolean {
  if (import.meta.env.VITE_USE_DEMO === 'true') return true;
  if (typeof window === 'undefined') return false;
  return new URLSearchParams(window.location.search).get('demo') === '1';
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    const response = await fetch(`${API_BASE}${path}`, {
      headers: { 'Content-Type': 'application/json' },
      ...init,
      signal: controller.signal,
    });
    if (!response.ok) {
      throw new Error(`${init?.method ?? 'GET'} ${path} failed (${response.status})`);
    }
    return (await response.json()) as T;
  } finally {
    window.clearTimeout(timer);
  }
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

function errorMessage(error: unknown): string {
  if (error instanceof DOMException && error.name === 'AbortError') {
    return 'Request timed out';
  }
  if (error instanceof Error) return error.message;
  return 'Unknown error';
}

export async function getScenarios(): Promise<Sourced<Scenario[]>> {
  if (demoRequested()) {
    await delay(DEMO_LATENCY_MS);
    return { data: DEMO_SCENARIOS, source: 'demo' };
  }
  try {
    const data = await request<Scenario[]>('/scenarios');
    return { data, source: 'live' };
  } catch (error) {
    if (STRICT_API) throw error;
    await delay(DEMO_LATENCY_MS);
    return { data: DEMO_SCENARIOS, source: 'demo', error: errorMessage(error) };
  }
}

export async function getPlan(scenarioId: string): Promise<Sourced<PlanResponse>> {
  if (demoRequested()) {
    await delay(DEMO_LATENCY_MS);
    return { data: getDemoPlan(scenarioId), source: 'demo' };
  }
  try {
    const data = await request<PlanResponse>('/plan', {
      method: 'POST',
      body: JSON.stringify({ scenario_id: scenarioId }),
    });
    return { data, source: 'live' };
  } catch (error) {
    if (STRICT_API) throw error;
    await delay(DEMO_LATENCY_MS);
    return { data: getDemoPlan(scenarioId), source: 'demo', error: errorMessage(error) };
  }
}

export async function getEvaluation(scenarioIds: string[]): Promise<Sourced<EvalResponse>> {
  if (demoRequested()) {
    await delay(DEMO_LATENCY_MS);
    return { data: getDemoEval(scenarioIds), source: 'demo' };
  }
  try {
    const data = await request<EvalResponse>('/evaluate', {
      method: 'POST',
      body: JSON.stringify({ scenario_ids: scenarioIds }),
    });
    return { data, source: 'live' };
  } catch (error) {
    if (STRICT_API) throw error;
    await delay(DEMO_LATENCY_MS);
    return { data: getDemoEval(scenarioIds), source: 'demo', error: errorMessage(error) };
  }
}

export async function getInventory(): Promise<Sourced<InventoryResponse>> {
  if (demoRequested()) {
    await delay(DEMO_LATENCY_MS);
    return { data: getDemoInventory(), source: 'demo' };
  }
  try {
    const data = await request<InventoryResponse>('/inventory');
    return { data, source: 'live' };
  } catch (error) {
    if (STRICT_API) throw error;
    await delay(DEMO_LATENCY_MS);
    return { data: getDemoInventory(), source: 'demo', error: errorMessage(error) };
  }
}

/**
 * Attempt the optional `/explain` endpoint. There is deliberately **no demo
 * fallback**: if the endpoint is not connected we return `available: false` so
 * the UI can present only data already present in the plan response instead of
 * inventing optimizer reasoning.
 */
export async function explain(batchId: string, destinationId: string): Promise<ExplainResult> {
  if (demoRequested()) {
    return { available: false, data: null, error: 'Demo mode — /explain endpoint not connected.' };
  }
  try {
    const data = await request<ExplainResponse>('/explain', {
      method: 'POST',
      body: JSON.stringify({ batch_id: batchId, destination_id: destinationId }),
    });
    return { available: true, data };
  } catch (error) {
    return { available: false, data: null, error: errorMessage(error) };
  }
}

/**
 * Attempt the optional `/replan` endpoint (E3). No demo fallback: the UI runs a
 * clearly-labelled local simulation instead when this is unavailable.
 */
export async function replan(scenarioId: string, event: ReplanEvent): Promise<ReplanResult> {
  if (demoRequested()) {
    return { available: false, data: null, error: 'Demo mode — /replan endpoint not connected.' };
  }
  try {
    const data = await request<ReplanResponse>('/replan', {
      method: 'POST',
      body: JSON.stringify({ scenario_id: scenarioId, event }),
    });
    return { available: true, data };
  } catch (error) {
    return { available: false, data: null, error: errorMessage(error) };
  }
}

export async function getHealth(): Promise<HealthResponse | null> {
  try {
    return await request<HealthResponse>('/health');
  } catch {
    return null;
  }
}
