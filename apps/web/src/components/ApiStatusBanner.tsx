export type ApiStatus = 'checking' | 'connected' | 'unavailable';

interface ApiStatusBannerProps {
  status: ApiStatus;
  detail?: string;
}

export default function ApiStatusBanner({ status, detail }: ApiStatusBannerProps) {
  if (status === 'checking') {
    return (
      <div className="api-banner api-banner--checking" role="status">
        <span className="api-banner__icon" aria-hidden="true">
          ◍
        </span>
        <span>Checking the FreshRoute API…</span>
      </div>
    );
  }

  if (status === 'connected') {
    return (
      <div className="api-banner api-banner--connected" role="status">
        <span className="api-banner__icon" aria-hidden="true">
          ✓
        </span>
        <span>
          Live API connected{detail ? ` — ${detail}` : ''}. Results below come from the backend.
        </span>
      </div>
    );
  }

  return (
    <div className="api-banner api-banner--unavailable" role="status">
      <span className="api-banner__icon" aria-hidden="true">
        ⚠
      </span>
      <span>
        <strong>Live API not connected.</strong> The backend under <code>apps/api</code> is not
        running, so every value below is clearly-labelled demo data — not a verified result.
        {detail ? ` (${detail})` : ''}
      </span>
    </div>
  );
}
