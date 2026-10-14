import type { ReactNode } from 'react';
import Spinner from './Spinner';

interface EmptyStateProps {
  title: string;
  message: string;
  action?: ReactNode;
  icon?: string;
}

export function EmptyState({ title, message, action, icon = '◍' }: EmptyStateProps) {
  return (
    <div className="state-view state-view--empty" role="status">
      <div className="state-view__icon" aria-hidden="true">
        {icon}
      </div>
      <h3 className="state-view__title">{title}</h3>
      <p className="state-view__message">{message}</p>
      {action ? <div className="state-view__action">{action}</div> : null}
    </div>
  );
}

interface LoadingStateProps {
  title?: string;
  message?: string;
}

export function LoadingState({ title = 'Working', message = 'Computing the optimal plan…' }: LoadingStateProps) {
  return (
    <div className="state-view state-view--loading" role="status" aria-live="polite">
      <Spinner label={title} />
      <p className="state-view__message">{message}</p>
    </div>
  );
}

interface ErrorStateProps {
  title?: string;
  message: string;
  onRetry?: () => void;
}

export function ErrorState({ title = 'Something went wrong', message, onRetry }: ErrorStateProps) {
  return (
    <div className="state-view state-view--error" role="alert">
      <div className="state-view__icon" aria-hidden="true">
        ⚠
      </div>
      <h3 className="state-view__title">{title}</h3>
      <p className="state-view__message">{message}</p>
      {onRetry ? (
        <div className="state-view__action">
          <button type="button" className="btn btn--secondary" onClick={onRetry}>
            Try again
          </button>
        </div>
      ) : null}
    </div>
  );
}

export function SkeletonBlock({ lines = 3 }: { lines?: number }) {
  return (
    <div className="skeleton" aria-hidden="true">
      {Array.from({ length: lines }).map((_, index) => (
        <span key={index} className="skeleton__line" />
      ))}
    </div>
  );
}
