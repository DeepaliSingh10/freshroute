import { useRef, useState } from 'react';
import { replan } from '../api/client';
import type { PlanDiffEntry, PlanResponse, ReplanEvent, ReplanEventType } from '../api/types';
import { simulateReplan } from '../utils/simulate';

interface ReplanFeedProps {
  plan: PlanResponse;
}

interface FeedEntry {
  id: number;
  timestamp: string;
  event: ReplanEventType;
  /** Where the diff came from: the live endpoint or the local demo simulation. */
  origin: 'live' | 'simulated';
  summary: string;
  diff: PlanDiffEntry[];
  assumptions: string[];
}

const EVENTS: { type: ReplanEventType; label: string; payload: Record<string, number> }[] = [
  { type: 'traffic_delay', label: 'Traffic delay +6h', payload: { hours: 6 } },
  { type: 'temp_spike', label: 'Temp spike −0.5d', payload: { rsl_penalty_days: 0.5 } },
  { type: 'capacity_change', label: 'Capacity reduced', payload: { factor: 0.8 } },
  { type: 'new_order', label: 'New order', payload: {} },
];

const EVENT_LABEL: Record<ReplanEventType, string> = {
  traffic_delay: 'Traffic delay',
  capacity_change: 'Capacity change',
  new_order: 'New order',
  temp_spike: 'Temperature spike',
};

export default function ReplanFeed({ plan }: ReplanFeedProps) {
  const [entries, setEntries] = useState<FeedEntry[]>([]);
  const counter = useRef(0);

  async function fire(event: ReplanEvent, label: string) {
    const result = await replan(plan.scenario_id, event);

    let entry: FeedEntry;
    if (result.available && result.data) {
      entry = {
        id: ++counter.current,
        timestamp: new Date().toLocaleTimeString(),
        event: event.type,
        origin: 'live',
        summary: `Live /replan returned ${result.data.diff.length} change${result.data.diff.length === 1 ? '' : 's'}.`,
        diff: result.data.diff,
        assumptions: [],
      };
    } else {
      const sim = simulateReplan(plan, event);
      entry = {
        id: ++counter.current,
        timestamp: new Date().toLocaleTimeString(),
        event: event.type,
        origin: 'simulated',
        summary: sim.requiresOptimizer
          ? sim.summary
          : `Simulated replan (${label}) — ${sim.summary}`,
        diff: sim.entries,
        assumptions: sim.assumptions,
      };
    }

    setEntries((prev) => [entry, ...prev]);
  }

  return (
    <section className="panel" aria-label="Replan event feed">
      <header className="panel__header">
        <div>
          <h2 className="panel__title">Replan feed</h2>
          <p className="panel__subtitle">
            Fire a disruption and inspect a plan diff (E3)
          </p>
        </div>
        <span
          className="sim-label"
          title="Live /replan if connected; otherwise a clearly-labelled local simulation"
        >
          E3 · event → diff
        </span>
      </header>

      <div className="replan-buttons">
        {EVENTS.map((item) => (
          <button
            key={item.type}
            type="button"
            className="btn btn--secondary btn--sm"
            onClick={() => void fire({ type: item.type, payload: item.payload }, item.label)}
          >
            {item.label}
          </button>
        ))}
      </div>

      {entries.length === 0 ? (
        <p className="replan-empty">
          No events yet. Fire a disruption to preview how the plan could change. The{' '}
          <code>/replan</code> endpoint is not connected, so diffs are simulated locally and labelled
          as such.
        </p>
      ) : (
        <ol className="replan-feed">
          {entries.map((entry) => (
            <li className="replan-entry" key={entry.id}>
              <div className="replan-entry__head">
                <span className={`replan-entry__badge is-${entry.origin}`}>
                  {entry.origin === 'live' ? 'Live endpoint' : 'Simulated'}
                </span>
                <span className="replan-entry__type">{EVENT_LABEL[entry.event]}</span>
                <time className="replan-entry__time">{entry.timestamp}</time>
              </div>
              <p className="replan-entry__summary">{entry.summary}</p>
              {entry.diff.length > 0 ? (
                <ul className="replan-diff">
                  {entry.diff.map((change) => (
                    <li key={`${change.batch_id}-${change.change}`}>
                      <span className={`diff-tag diff-tag--${change.change}`}>{change.change}</span>
                      <span className="diff-batch">{change.batch_id}</span>
                      {change.destination_id ? (
                        <span className="diff-dest">→ {change.destination_id}</span>
                      ) : null}
                      <span className="diff-reason">{change.reason}</span>
                    </li>
                  ))}
                </ul>
              ) : null}
              {entry.assumptions.length > 0 ? (
                <p className="replan-entry__assumptions">
                  {entry.assumptions.join(' ')} Illustrative only — not optimizer output.
                </p>
              ) : null}
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
