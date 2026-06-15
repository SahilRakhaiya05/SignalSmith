export function LoadingState({ label = "Loading..." }: { label?: string }) {
  return (
    <div className="loading-state-pro" role="status" aria-live="polite">
      <div className="loading-state-pro__spinner" aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}