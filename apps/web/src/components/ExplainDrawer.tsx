import { useEffect, useRef } from 'react';
import type { ExplainModel } from '../utils/explain';
import Spinner from './Spinner';
import SourceBadge from './SourceBadge';

interface ExplainDrawerProps {
  model: ExplainModel | null;
  onClose: () => void;
  loading?: boolean;
}

function constraintGlyph(status: 'satisfied' | 'violated' | 'unknown'): string {
  if (status === 'satisfied') return '✓';
  if (status === 'violated') return '✕';
  return '—';
}

function constraintStatus(satisfied: boolean, isShelfLife: boolean): 'satisfied' | 'violated' | 'unknown' {
  if (!satisfied) return isShelfLife ? 'violated' : 'unknown';
  return 'satisfied';
}

export default function ExplainDrawer({ model, onClose, loading = false }: ExplainDrawerProps) {
  const closeRef = useRef<HTMLButtonElement>(null);
  const open = Boolean(model) || loading;

  useEffect(() => {
    if (!open) return undefined;
    closeRef.current?.focus();
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') onClose();
    }
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [open, onClose]);

  if (!open) return null;

  if (loading && !model) {
    return (
      <div className="drawer-overlay" onClick={onClose} role="presentation">
        <aside
          className="drawer"
          role="dialog"
          aria-modal="true"
          aria-label="Loading explanation"
          onClick={(event) => event.stopPropagation()}
        >
          <header className="drawer__header">
            <h2 className="drawer__title">Explainability</h2>
            <button
              type="button"
              className="drawer__close"
              aria-label="Close explainability drawer"
              onClick={onClose}
              ref={closeRef}
            >
              ✕
            </button>
          </header>
          <div className="drawer__body drawer__body--loading">
            <Spinner label="Loading explanation" />
            <p>Requesting the /explain endpoint…</p>
          </div>
        </aside>
      </div>
    );
  }

  if (!model) return null;

  const urgency = model.urgencyDays;

  return (
    <div className="drawer-overlay" onClick={onClose} role="presentation">
      <aside
        className="drawer"
        role="dialog"
        aria-modal="true"
        aria-labelledby="explain-drawer-title"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="drawer__header">
          <div>
            <p className="drawer__eyebrow">
              Explainability · {model.kind === 'dispatch' ? 'dispatch' : 'discount'}
            </p>
            <h2 className="drawer__title" id="explain-drawer-title">
              {model.heading}
            </h2>
          </div>
          <div className="drawer__header-actions">
            <SourceBadge source={model.source} size="sm" />
            <button
              type="button"
              className="drawer__close"
              aria-label="Close explainability drawer"
              onClick={onClose}
              ref={closeRef}
            >
              ✕
            </button>
          </div>
        </header>

        <div className="drawer__body">
          <section className="drawer__section">
            <h3 className="drawer__section-title">Recommendation</h3>
            <p className="drawer__recommendation">{model.recommendation}</p>
          </section>

          <section className="drawer__section">
            <h3 className="drawer__section-title">Reason (verbatim from the plan response)</h3>
            <blockquote className="drawer__reason">{model.reason}</blockquote>
          </section>

          {urgency !== undefined ? (
            <section className="drawer__section">
              <h3 className="drawer__section-title">Urgency</h3>
              <p className="drawer__urgency">
                <strong>{urgency.toFixed(1)} days</strong> of remaining shelf life at dispatch.
              </p>
            </section>
          ) : null}

          <section className="drawer__section">
            <h3 className="drawer__section-title">Relevant constraints</h3>
            <ul className="constraint-list">
              {model.constraints.map((constraint) => {
                const isShelfLife = constraint.name.toLowerCase().includes('shelf-life');
                const status = constraintStatus(constraint.satisfied, isShelfLife);
                return (
                  <li key={constraint.name} className={`constraint constraint--${status}`}>
                    <span className="constraint__glyph" aria-hidden="true">
                      {constraintGlyph(status)}
                    </span>
                    <span className="constraint__text">
                      <span className="constraint__name">{constraint.name}</span>
                      {constraint.detail ? (
                        <span className="constraint__detail">{constraint.detail}</span>
                      ) : null}
                    </span>
                  </li>
                );
              })}
            </ul>
          </section>

          <section className="drawer__section">
            <h3 className="drawer__section-title">Supporting data</h3>
            <dl className="fact-list">
              {model.facts.map((fact) => (
                <div className="fact-list__row" key={fact.label}>
                  <dt>{fact.label}</dt>
                  <dd>{fact.value}</dd>
                </div>
              ))}
            </dl>
          </section>

          {model.endpointAvailable && model.serverFactors.length > 0 ? (
            <section className="drawer__section">
              <h3 className="drawer__section-title">Server factor breakdown (/explain)</h3>
              <dl className="fact-list">
                {model.serverFactors.map((factor) => (
                  <div className="fact-list__row" key={factor.factor}>
                    <dt>{factor.factor}</dt>
                    <dd>
                      {factor.value}
                      {factor.note ? <span className="fact-list__note"> · {factor.note}</span> : null}
                    </dd>
                  </div>
                ))}
              </dl>
            </section>
          ) : null}

          <p className={`drawer__endpoint-note ${model.endpointAvailable ? 'is-ok' : 'is-warn'}`} role="note">
            {model.endpointNote}
          </p>

          {model.source === 'demo' ? (
            <p className="drawer__demo-note" role="note">
              Demo data — synthetic and schema-compatible. This panel restates fields from the demo
              plan; it is not an optimizer explanation and not a verified result.
            </p>
          ) : null}
        </div>
      </aside>
    </div>
  );
}
