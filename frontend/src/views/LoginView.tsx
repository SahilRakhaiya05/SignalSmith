import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { SplunkAuthGate } from "../components/SplunkAuthGate";
import { LoadingState } from "../components/ui/LoadingState";
import { useSession } from "../context/SessionContext";

export function LoginView() {
  const navigate = useNavigate();
  const location = useLocation();
  const { splunkAuthed, initializing, completeSplunkAuth } = useSession();
  const fromState = (location.state as { from?: string } | null)?.from;
  const redirectTo = fromState && fromState !== "/login" ? fromState : "/";

  if (initializing) {
    return (
      <div className="boot-screen">
        <LoadingState label="Loading…" />
      </div>
    );
  }

  if (splunkAuthed) {
    return <Navigate to={redirectTo} replace />;
  }

  return (
    <SplunkAuthGate
      onAuthenticated={() => {
        completeSplunkAuth();
        navigate(redirectTo, { replace: true });
      }}
    />
  );
}