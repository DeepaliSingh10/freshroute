import type { DataSource, Scenario } from '../api/types';
import SourceBadge from './SourceBadge';

interface ScenarioSelectorProps {
  scenarios: Scenario[];
  selectedId: string | null;
  loading: boolean;
  source: DataSource;
  onSelect: (scenarioId: string) => void;
  onOptimize: () => void;
}

function splitLabel(split: string): string {
  return split.charAt(0).toUpperCase() + split.slice(1);
}

export default function ScenarioSelector({
  scenarios,
  selectedId,
  loading,
  source,
  onSelect,
  onOptimize,
}: ScenarioSelectorProps) {
  const selected = scenarios.find((s) => s.scenario_id === selectedId);

  return (
    <section className="control-bar" aria-label="Scenario controls">
      <div className="control-bar__field">
        <label className="control-bar__label" htmlFor="scenario-select">
          Scenario
        </label>
        <select
          id="scenario-select"
          className="select"
          value={selectedId ?? ''}
          disabled={loading || scenarios.length === 0}
          onChange={(event) => onSelect(event.target.value)}
        >
          {scenarios.length === 0 ? <option value="">No scenarios available</option> : null}
          {scenarios.map((scenario) => (
            <option key={scenario.scenario_id} value={scenario.scenario_id}>
              {scenario.scenario_id}
            </option>
          ))}
        </select>
      </div>

      <div className="control-bar__meta">
        {selected ? (
          <>
            <span className={`pill pill--split pill--split-${selected.split}`}>
              {splitLabel(selected.split)} split
            </span>
            {selected.perturbation_profile && selected.perturbation_profile !== 'none' ? (
              <span className="pill pill--muted" title={selected.perturbation_profile}>
                perturbations
              </span>
            ) : (
              <span className="pill pill--muted">no perturbations</span>
            )}
            {typeof selected.seed === 'number' ? (
              <span className="pill pill--ghost">seed {selected.seed}</span>
            ) : null}
          </>
        ) : (
          <span className="control-bar__hint">Select a scenario to begin.</span>
        )}
      </div>

      <button
        type="button"
        className="btn btn--primary"
        onClick={onOptimize}
        disabled={loading || !selectedId}
      >
        {loading ? 'Optimizing…' : 'Optimize'}
      </button>

      <SourceBadge source={source} />
    </section>
  );
}
