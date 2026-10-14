import type { DataSource } from '../api/types';

interface SourceBadgeProps {
  source: DataSource;
  size?: 'sm' | 'md';
}

export default function SourceBadge({ source, size = 'md' }: SourceBadgeProps) {
  const live = source === 'live';
  return (
    <span
      className={`source-badge source-badge--${source} source-badge--${size}`}
      title={
        live
          ? 'Connected to the FreshRoute API.'
          : 'The API is not connected (or demo mode is on); showing synthetic, schema-compatible demo data — not an evaluation result.'
      }
    >
      <span className="source-badge__dot" aria-hidden="true" />
      {live ? 'Live API' : 'Demo data'}
    </span>
  );
}
