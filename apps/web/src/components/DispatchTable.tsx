import { Fragment, useMemo, useState } from 'react';
import type { Dispatch } from '../api/types';
import { EmptyState } from './StateViews';

interface DispatchTableProps {
  dispatches: Dispatch[];
  onExplain?: (dispatch: Dispatch) => void;
}

type SortKey =
  | 'priority_rank'
  | 'batch_id'
  | 'commodity_id'
  | 'destination_id'
  | 'quantity_kg'
  | 'effective_price_per_kg'
  | 'travel_time_hours'
  | 'transport_cost'
  | 'margin'
  | 'urgency_days'
  | 'feasible';

type SortDir = 'asc' | 'desc';
type FeasibilityFilter = 'all' | 'feasible' | 'infeasible';

interface Column {
  key: SortKey;
  label: string;
  numeric: boolean;
  title?: string;
}

const COLUMNS: Column[] = [
  { key: 'priority_rank', label: '#', numeric: true, title: 'Dispatch priority (perishability-first)' },
  { key: 'batch_id', label: 'Batch', numeric: false },
  { key: 'commodity_id', label: 'Commodity', numeric: false },
  { key: 'destination_id', label: 'Destination', numeric: false },
  { key: 'quantity_kg', label: 'Qty (kg)', numeric: true },
  { key: 'effective_price_per_kg', label: 'Eff. price', numeric: true, title: 'Effective price after discount (₹/kg)' },
  { key: 'travel_time_hours', label: 'Transit', numeric: true, title: 'Travel time (hours)' },
  { key: 'transport_cost', label: 'Transport', numeric: true, title: 'Transport cost (₹)' },
  { key: 'margin', label: 'Margin', numeric: true, title: 'Contribution margin (₹)' },
  { key: 'urgency_days', label: 'Urgency', numeric: true, title: 'Remaining shelf life at dispatch (days)' },
  { key: 'feasible', label: 'Feasibility', numeric: false },
];

const inr = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 });
const inr1 = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 1 });

function compare(a: Dispatch, b: Dispatch, key: SortKey): number {
  const av = a[key];
  const bv = b[key];
  if (typeof av === 'number' && typeof bv === 'number') return av - bv;
  if (typeof av === 'boolean' && typeof bv === 'boolean') return Number(av) - Number(bv);
  return String(av).localeCompare(String(bv));
}

export default function DispatchTable({ dispatches, onExplain }: DispatchTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>('priority_rank');
  const [sortDir, setSortDir] = useState<SortDir>('asc');
  const [query, setQuery] = useState('');
  const [feasibility, setFeasibility] = useState<FeasibilityFilter>('all');
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  const rows = useMemo(() => {
    const needle = query.trim().toLowerCase();
    const filtered = dispatches.filter((d) => {
      if (feasibility === 'feasible' && !d.feasible) return false;
      if (feasibility === 'infeasible' && d.feasible) return false;
      if (!needle) return true;
      return (
        d.batch_id.toLowerCase().includes(needle) ||
        d.commodity_id.toLowerCase().includes(needle) ||
        d.destination_id.toLowerCase().includes(needle) ||
        d.reason.toLowerCase().includes(needle)
      );
    });

    const sorted = [...filtered].sort((a, b) => compare(a, b, sortKey));
    if (sortDir === 'desc') sorted.reverse();
    return sorted;
  }, [dispatches, query, feasibility, sortKey, sortDir]);

  function toggleSort(key: SortKey) {
    if (key === sortKey) {
      setSortDir((dir) => (dir === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('asc');
    }
  }

  function toggleRow(batchId: string) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(batchId)) next.delete(batchId);
      else next.add(batchId);
      return next;
    });
  }

  const feasibleCount = dispatches.filter((d) => d.feasible).length;
  const infeasibleCount = dispatches.length - feasibleCount;

  return (
    <section className="panel" aria-label="Dispatch plan">
      <header className="panel__header">
        <div>
          <h2 className="panel__title">Dispatch plan</h2>
          <p className="panel__subtitle">
            Perishability-first ordering · {feasibleCount} feasible, {infeasibleCount} excluded
          </p>
        </div>
        <div className="panel__tools">
          <input
            type="search"
            className="input"
            placeholder="Filter batch / commodity / destination"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            aria-label="Filter dispatches"
          />
          <select
            className="select select--compact"
            value={feasibility}
            onChange={(event) => setFeasibility(event.target.value as FeasibilityFilter)}
            aria-label="Filter by feasibility"
          >
            <option value="all">All</option>
            <option value="feasible">Feasible only</option>
            <option value="infeasible">Infeasible only</option>
          </select>
        </div>
      </header>

      {dispatches.length === 0 ? (
        <EmptyState
          title="No dispatches"
          message="The optimizer returned no dispatches for this scenario."
          icon="▤"
        />
      ) : rows.length === 0 ? (
        <EmptyState
          title="No matching dispatches"
          message="Adjust the filter or search terms to see dispatch rows."
          icon="⌕"
        />
      ) : (
        <div className="table-scroll">
          <table className="data-table">
            <caption className="sr-only">Optimized dispatch plan with feasibility and reasons</caption>
            <thead>
              <tr>
                <th scope="col" className="col-toggle">
                  <span className="sr-only">Expand</span>
                </th>
                {COLUMNS.map((column) => {
                  const active = sortKey === column.key;
                  const ariaSort = active ? (sortDir === 'asc' ? 'ascending' : 'descending') : 'none';
                  return (
                    <th
                      key={column.key}
                      scope="col"
                      aria-sort={ariaSort}
                      className={column.numeric ? 'is-numeric' : undefined}
                    >
                      <button
                        type="button"
                        className={`th-sort ${active ? 'is-active' : ''}`}
                        title={column.title ?? `Sort by ${column.label}`}
                        onClick={() => toggleSort(column.key)}
                      >
                        {column.label}
                        <span className="th-sort__caret" aria-hidden="true">
                          {active ? (sortDir === 'asc' ? '▲' : '▼') : '↕'}
                        </span>
                      </button>
                    </th>
                  );
                })}
                <th scope="col" className="col-action">
                  Explain
                </th>
              </tr>
            </thead>
            <tbody>
              {rows.map((d) => {
                const isOpen = expanded.has(d.batch_id);
                const impliedDiscount =
                  d.price_per_kg > 0 ? 1 - d.effective_price_per_kg / d.price_per_kg : 0;
                return (
                  <Fragment key={d.batch_id}>
                    <tr className={isOpen ? 'is-expanded' : undefined}>
                      <td className="col-toggle">
                        <button
                          type="button"
                          className="row-toggle"
                          aria-expanded={isOpen}
                          aria-label={`${isOpen ? 'Hide' : 'Show'} reasoning for ${d.batch_id}`}
                          onClick={() => toggleRow(d.batch_id)}
                        >
                          {isOpen ? '▾' : '▸'}
                        </button>
                      </td>
                      <td className="is-numeric">{d.priority_rank}</td>
                      <td className="is-mono">{d.batch_id}</td>
                      <td>{d.commodity_id}</td>
                      <td>{d.destination_id}</td>
                      <td className="is-numeric">{inr.format(d.quantity_kg)}</td>
                      <td className="is-numeric">₹{inr1.format(d.effective_price_per_kg)}</td>
                      <td className="is-numeric">{inr1.format(d.travel_time_hours)} h</td>
                      <td className="is-numeric">₹{inr.format(d.transport_cost)}</td>
                      <td className={`is-numeric ${d.margin < 0 ? 'is-negative' : ''}`}>
                        ₹{inr.format(d.margin)}
                      </td>
                      <td className="is-numeric">{inr1.format(d.urgency_days)} d</td>
                      <td>
                        <span className={`feas-pill ${d.feasible ? 'is-feasible' : 'is-infeasible'}`}>
                          {d.feasible ? 'Feasible' : 'Infeasible'}
                        </span>
                      </td>
                      <td className="col-action">
                        {onExplain ? (
                          <button
                            type="button"
                            className="btn btn--ghost btn--xs"
                            onClick={() => onExplain(d)}
                            aria-label={`Explain dispatch ${d.batch_id} to ${d.destination_id}`}
                          >
                            Explain
                          </button>
                        ) : null}
                      </td>
                    </tr>
                    {isOpen ? (
                      <tr className="detail-row">
                        <td colSpan={COLUMNS.length + 2}>
                          <div className="detail-row__content">
                            <p className="detail-row__reason">
                              <strong>Why:</strong> {d.reason}
                            </p>
                            <dl className="detail-row__facts">
                              <div>
                                <dt>List price</dt>
                                <dd>₹{inr1.format(d.price_per_kg)}/kg</dd>
                              </div>
                              <div>
                                <dt>Effective price</dt>
                                <dd>₹{inr1.format(d.effective_price_per_kg)}/kg</dd>
                              </div>
                              <div>
                                <dt>Implied discount</dt>
                                <dd>{(impliedDiscount * 100).toFixed(0)}%</dd>
                              </div>
                              <div>
                                <dt>Urgency (RSL)</dt>
                                <dd>{inr1.format(d.urgency_days)} days</dd>
                              </div>
                            </dl>
                          </div>
                        </td>
                      </tr>
                    ) : null}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
