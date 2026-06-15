import { useEffect, useMemo, useRef, useState, type KeyboardEvent } from "react";
import { useNavigate } from "react-router-dom";
import { Search } from "lucide-react";
import { APP_NAV, searchAppNav } from "../../lib/navigation";
import { NavIcon } from "../nav/NavIcon";

export function GlobalSearch() {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const rootRef = useRef<HTMLDivElement>(null);

  const results = useMemo(() => searchAppNav(query).slice(0, 8), [query]);

  useEffect(() => {
    setActiveIndex(0);
  }, [query]);

  useEffect(() => {
    const onDocClick = (e: MouseEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, []);

  const goTo = (to: string) => {
    navigate(to);
    setQuery("");
    setOpen(false);
  };

  const onKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (!open && (e.key === "ArrowDown" || e.key === "Enter")) {
      setOpen(true);
      return;
    }
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIndex((i) => Math.min(i + 1, results.length - 1));
    }
    if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIndex((i) => Math.max(i - 1, 0));
    }
    if (e.key === "Enter" && results[activeIndex]) {
      e.preventDefault();
      goTo(results[activeIndex].to);
    }
    if (e.key === "Escape") {
      setOpen(false);
    }
  };

  return (
    <div className={`global-search ${open ? "open" : ""}`} ref={rootRef}>
      <Search size={15} className="global-search__icon" aria-hidden />
      <input
        type="search"
        className="global-search__input"
        placeholder="Search pages, pipeline, detections…"
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={onKeyDown}
        aria-label="Search workspace"
        aria-expanded={open}
        aria-controls="global-search-results"
        role="combobox"
        autoComplete="off"
      />
      {open && (
        <div id="global-search-results" className="global-search__panel" role="listbox">
          {(query ? results : APP_NAV.slice(0, 8)).map((item, index) => (
            <button
              key={item.to}
              type="button"
              className={`global-search__item ${index === activeIndex ? "active" : ""}`}
              role="option"
              aria-selected={index === activeIndex}
              onMouseEnter={() => setActiveIndex(index)}
              onClick={() => goTo(item.to)}
            >
              <span className="global-search__item-icon">
                <NavIcon name={item.icon} size={14} />
              </span>
              <span className="global-search__item-text">
                <strong>{item.label}</strong>
                <span>{item.section}</span>
              </span>
            </button>
          ))}
          {query && results.length === 0 && (
            <p className="global-search__empty">No pages match “{query}”</p>
          )}
        </div>
      )}
    </div>
  );
}