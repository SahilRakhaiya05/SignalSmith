import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { Sidebar } from "./components/Sidebar";
import { TopBar } from "./components/layout/TopBar";
import { RouteSkeleton } from "./components/ui/Skeleton";
import { SessionProvider, useSession } from "./context/SessionContext";
import { OverviewView } from "./views/OverviewView";
import { WorkflowView } from "./views/WorkflowView";
import { AnalysisView } from "./views/AnalysisView";
import { ProtectionView } from "./views/ProtectionView";
import { SavedSearchesView } from "./views/SavedSearchesView";
import { RecommendationsView } from "./views/RecommendationsView";
import { ValidationView } from "./views/ValidationView";
import { ResultsView } from "./views/ResultsView";
import { ApprovalView } from "./views/ApprovalView";
import { HistoryView } from "./views/HistoryView";
import { SettingsView } from "./views/SettingsView";
import { AnalyticsView } from "./views/AnalyticsView";
import { AssistantView } from "./views/AssistantView";
import { SplunkDashboardView } from "./views/SplunkDashboardView";
import { DataFlowView } from "./views/DataFlowView";
import { LoginView } from "./views/LoginView";

function AppShell() {
  const location = useLocation();
  const { error, progress, jobProgress, apiOnline, initializing, splunkAuthed } = useSession();
  const isAssistant = location.pathname === "/assistant";

  if (!splunkAuthed) {
    const from = `${location.pathname}${location.search}${location.hash}`;
    return <Navigate to="/login" replace state={{ from }} />;
  }

  return (
    <div className="app">
      <Sidebar />
      <div className="app-main">
        <TopBar />
        <main className={`main${isAssistant ? " main--assistant" : ""}`} id="main-content">
          {!apiOnline && (
            <div className="alert-banner alert-banner--danger" role="alert">
              Backend unreachable. Start the platform with <code>.\scripts\start.ps1</code> then open <code>http://localhost:8080</code>
            </div>
          )}
          {error && (
            <div className="alert-banner alert-banner--danger" role="alert">
              {error}
            </div>
          )}
          {(progress || jobProgress > 0) && (
            <div className="progress-panel progress-panel--global" role="status" aria-live="polite">
              <div className="progress-bar">
                <div
                  className="progress-fill"
                  style={{ width: `${Math.max(jobProgress > 0 ? Math.round(jobProgress * 100) : 8, 8)}%` }}
                />
              </div>
              <p>{progress || "Working…"}</p>
            </div>
          )}
          {initializing ? (
            <RouteSkeleton pathname={location.pathname} />
          ) : (
          <Routes>
            <Route path="/" element={<OverviewView />} />
            <Route path="/data-flow" element={<DataFlowView />} />
            <Route path="/assistant" element={<AssistantView />} />
            <Route path="/analytics" element={<AnalyticsView />} />
            <Route path="/splunk-dashboard" element={<SplunkDashboardView />} />
            <Route path="/workflow" element={<WorkflowView />} />
            <Route path="/analysis" element={<AnalysisView />} />
            <Route path="/protection" element={<ProtectionView />} />
            <Route path="/searches" element={<SavedSearchesView />} />
            <Route path="/recommendations" element={<RecommendationsView />} />
            <Route path="/validation" element={<ValidationView />} />
            <Route path="/results" element={<ResultsView />} />
            <Route path="/approval" element={<ApprovalView />} />
            <Route path="/history" element={<HistoryView />} />
            <Route path="/mcp" element={<Navigate to="/assistant" replace />} />
            <Route path="/settings" element={<SettingsView />} />
            <Route path="/login" element={<Navigate to="/" replace />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
          )}
        </main>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <SessionProvider>
      <Routes>
        <Route path="/login" element={<LoginView />} />
        <Route path="/*" element={<AppShell />} />
      </Routes>
    </SessionProvider>
  );
}