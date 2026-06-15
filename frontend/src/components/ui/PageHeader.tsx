import type { ReactNode } from "react";

interface PageHeaderProps {
  title: string;
  description?: string;
  actions?: ReactNode;
  badge?: ReactNode;
}

export function PageHeader({ title, description, actions, badge }: PageHeaderProps) {
  return (
    <header className="page-header-ui">
      <div className="page-header-ui__text">
        <div className="page-header-ui__title-row">
          <h1>{title}</h1>
          {badge}
        </div>
        {description && <p>{description}</p>}
      </div>
      {actions && <div className="page-header-ui__actions">{actions}</div>}
    </header>
  );
}