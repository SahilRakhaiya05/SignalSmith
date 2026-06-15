import { useLocation } from "react-router-dom";
import { RefreshCw } from "lucide-react";
import { useSession } from "../../context/SessionContext";
import { PAGE_TITLES } from "../../lib/navigation";
import { isSplunkOnline } from "../../utils/connectionDisplay";
import { GlobalSearch } from "./GlobalSearch";

export function TopBar() {
  const { pathname } = useLocation();
  const { loading, sessionLoading, refreshSession, splunkConnection, validations, comparison } = useSession();
  const busy = loading || sessionLoading;
  const latestVal = validations[validations.length - 1];
  const title = PAGE_TITLES[pathname] || "SignalSmith";
  const online = isSplunkOnline(splunkConnection);

  return (
    <header className="topbar-ui">
      <div className="topbar-ui__left">
        <span className="topbar-ui__crumb">SignalSmith</span>
        <span className="topbar-ui__sep">/</span>
        <span className="topbar-ui__page">{title}</span>
      </div>

      <GlobalSearch />

      <div className="topbar-ui__right">
        {sessionLoading ? (
          <span className="topbar-ui__conn loading">
            <span className="topbar-ui__conn-dot" />
            Syncing
          </span>
        ) : (
          <span className={`topbar-ui__conn ${online ? "on" : "off"}`}>
            <span className="topbar-ui__conn-dot" />
            {splunkConnection === "splunk_mcp" ? "MCP" : online ? "Splunk" : "Offline"}
          </span>
        )}
        {!sessionLoading && latestVal && (
          <span className="topbar-ui__sync">
            {latestVal.tests_passed}/{latestVal.tests_total} · {latestVal.coverage_percent}%
          </span>
        )}
        {!sessionLoading && !latestVal && comparison?.event_reduction_percent != null && (
          <span className="topbar-ui__sync">{comparison.event_reduction_percent}% saved</span>
        )}
        <button
          type="button"
          className="topbar-ui__refresh"
          disabled={busy}
          onClick={() => refreshSession()}
          aria-label="Refresh"
          title="Refresh data"
        >
          <RefreshCw size={15} className={busy ? "spin" : ""} />
        </button>
      </div>
    </header>
  );
}