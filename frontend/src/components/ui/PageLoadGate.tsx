import type { ReactNode } from "react";

interface PageLoadGateProps {
  loading: boolean;
  skeleton: ReactNode;
  children: ReactNode;
}

export function PageLoadGate({ loading, skeleton, children }: PageLoadGateProps) {
  if (loading) return <>{skeleton}</>;
  return <div className="page-content--ready">{children}</div>;
}