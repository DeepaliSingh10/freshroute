interface SpinnerProps {
  label?: string;
}

export default function Spinner({ label = 'Loading' }: SpinnerProps) {
  return (
    <span className="spinner-wrap" role="status" aria-live="polite">
      <span className="spinner" aria-hidden="true" />
      <span className="spinner-label">{label}</span>
    </span>
  );
}
