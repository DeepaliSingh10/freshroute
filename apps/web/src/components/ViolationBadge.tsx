interface ViolationBadgeProps {
  violations: string[];
  degraded?: boolean;
  size?: 'sm' | 'lg';
}

export default function ViolationBadge({ violations, degraded = false, size = 'sm' }: ViolationBadgeProps) {
  const count = violations.length;
  const ok = count === 0;

  return (
    <div className={`violation-badge violation-badge--${size} ${ok ? 'is-ok' : 'is-bad'}`}>
      <span className="violation-badge__icon" aria-hidden="true">
        {ok ? '✓' : '✕'}
      </span>
      <span className="violation-badge__text">
        {ok ? '0 constraint violations' : `${count} constraint violation${count === 1 ? '' : 's'}`}
      </span>
      {degraded ? (
        <span className="violation-badge__degraded" title="Plan produced under degraded input">
          degraded input
        </span>
      ) : null}
      {!ok ? (
        <ul className="violation-badge__list">
          {violations.map((violation) => (
            <li key={violation}>{violation}</li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
