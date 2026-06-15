import { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { ChevronDown, LogOut, Play, RotateCcw } from "lucide-react";
import { api } from "../api";
import { useSession } from "../context/SessionContext";
import { isSplunkOnline } from "../utils/connectionDisplay";
import { APP_NAV, NAV_SECTIONS } from "../lib/navigation";
import { NavIcon } from "./nav/NavIcon";
import { AppLogo } from "./ui/AppLogo";

export function Sidebar() {
  const {
    splunkConnection,
    loading,
    apiOnline,
    integrations,
    runFullPipeline,
    runStep,
    splunkUser,
    logoutSplunk,
    sessionLoading,
  } = useSession();

  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});
  const navigate = useNavigate();
  const aiReady = integrations?.ai?.available;
  const online = isSplunkOnline(splunkConnection);

  const toggleSection = (id: string) => {
    setCollapsed((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  return (
    <aside className="sidebar-ui" aria-label="Primary navigation">
      <header className="sidebar-ui__brand">
        <div className="sidebar-ui__logo">
          <AppLogo size={28} />
        </div>
        <div className="sidebar-ui__brand-text">
          <h1>SignalSmith</h1>
        </div>
      </header>

      <nav className="sidebar-ui__nav">
        {NAV_SECTIONS.map((section) => {
          const items = APP_NAV.filter((n) => n.section === section.id);
          const isCollapsed = collapsed[section.id];
          return (
            <div key={section.id} className="sidebar-ui__section">
              <button
                type="button"
                className="sidebar-ui__section-btn"
                onClick={() => toggleSection(section.id)}
                aria-expanded={!isCollapsed}
              >
                <span>{section.label}</span>
                <ChevronDown size={12} className={isCollapsed ? "collapsed" : ""} aria-hidden />
              </button>
              {!isCollapsed && (
                <ul className="sidebar-ui__list">
                  {items.map((item) => (
                    <li key={item.to}>
                      <NavLink
                        to={item.to}
                        className={({ isActive }) =>
                          ["sidebar-ui__link", isActive ? "active" : "", item.highlight ? "highlight" : ""]
                            .filter(Boolean)
                            .join(" ")
                        }
                        end={item.to === "/"}
                      >
                        <span className="sidebar-ui__icon-wrap">
                          <NavIcon name={item.icon} size={15} />
                        </span>
                        <span className="sidebar-ui__label">{item.label}</span>
                        {item.highlight && !aiReady && <span className="sidebar-ui__pill">SPL</span>}
                      </NavLink>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          );
        })}
      </nav>

      <div className="sidebar-ui__bottom">
        {splunkUser && !sessionLoading && (
          <div className="sidebar-ui__user">
            <span className="sidebar-ui__user-name">{splunkUser}</span>
            <button
              type="button"
              className="sidebar-ui__user-logout"
              onClick={() => {
                logoutSplunk();
                navigate("/login");
              }}
              title="Sign out"
              aria-label="Sign out"
            >
              <LogOut size={13} aria-hidden />
            </button>
          </div>
        )}

        <footer className="sidebar-ui__footer">
          <button
            type="button"
            className="sidebar-ui__cta"
            disabled={loading || !apiOnline || !online}
            onClick={runFullPipeline}
          >
            <Play size={14} fill="currentColor" aria-hidden />
            Run pipeline
          </button>
          <button
            type="button"
            className="sidebar-ui__reset"
            disabled={loading}
            onClick={() => runStep(async () => { await api.resetSession(); window.location.reload(); }, "Reset")}
          >
            <RotateCcw size={13} aria-hidden />
            Reset
          </button>
        </footer>
      </div>
    </aside>
  );
}