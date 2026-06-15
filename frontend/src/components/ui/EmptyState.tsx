import type { ReactNode } from "react";

interface EmptyStateProps {
  title: string;
  description: string;
  action?: ReactNode;
  icon?: string;
}

export function EmptyState({ title, description, action, icon = "○" }: EmptyStateProps) {
  return (
    <div className="empty-state-pro" role="status">
      <div className="empty-state-pro__icon" aria-hidden="true">{icon}</div>
      <h3>{title}</h3>
      <p>{description}</p>
      {action && <div className="empty-state-pro__action">{action}</div>}
    </div>
  );
}