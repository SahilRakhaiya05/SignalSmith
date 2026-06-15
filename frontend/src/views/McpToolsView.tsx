import { useEffect, useState } from "react";
import { api } from "../api";
import { useSession } from "../context/SessionContext";
import { PageHeader } from "../components/ui/PageHeader";
import { LoadingState } from "../components/ui/LoadingState";

const PRESETS = [
  "Show health check volume by service in the baseline index",
  "Compare event counts between baseline and candidate indexes",
  "Find failed logins and privileged user anomalies",
  "Top 10 services by telemetry volume",
];

const DEFAULT_TOOL = "splunk_get_indexes";

export function McpToolsView() {
  const { integrations } = useSession();
  const [tools, setTools] = useState<Array<{ name: string; description?: string }>>([]);
  const [nlQuery, setNlQuery] = useState(PRESETS[0]);
  const [spl, setSpl] = useState("");
  const [splSource, setSplSource] = useState("");
  const [runResult, setRunResult] = useState("");
  const [loading, setLoading] = useState(false);
  const [toolsLoading, setToolsLoading] = useState(true);
  const [selectedTool, setSelectedTool] = useState(DEFAULT_TOOL);
  const [toolResult, setToolResult] = useState("");

  const mcp = integrations?.mcp;

  useEffect(() => {
    api
      .getMcpTools()
      .then((r) => {
        setTools(r.tools);
        if (r.tools.length) setSelectedTool(r.tools[0].name);
      })
      .catch(() => {})
      .finally(() => setToolsLoading(false));
  }, []);

  const generateSpl = async () => {
    setLoading(true);
    try {
      const r = await api.generateSpl(nlQuery);
      setSpl(r.spl);
      setSplSource(r.source);
    } catch (e) {
      setSpl(`Error: ${e instanceof Error ? e.message : String(e)}`);
      setSplSource("");
    } finally {
      setLoading(false);
    }
  };

  const runSpl = async () => {
    if (!spl) return;
    setLoading(true);
    try {
      const r = await api.runMcpQuery(spl);
      setRunResult(JSON.stringify(r.result, null, 2));
    } catch (e) {
      setRunResult(String(e));
    } finally {
      setLoading(false);
    }
  };

  const callTool = async () => {
    setLoading(true);
    try {
      const baseline = integrations?.splunk?.baseline_index || "signalsmith_baseline";
      const args =
        selectedTool.includes("index_info")
          ? { index_name: baseline, index: baseline }
          : selectedTool.includes("run_query") || selectedTool === "run_splunk_query"
            ? { query: spl || `index=${baseline} | head 5` }
            : selectedTool.includes("knowledge_objects") || selectedTool === "get_saved_searches"
              ? { type: "saved_searches", row_limit: 5 }
              : {};
      const r = await api.callMcpTool(selectedTool, args);
      setToolResult(JSON.stringify(r, null, 2));
    } catch (e) {
      setToolResult(String(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <PageHeader title="Query tools" />

      {toolsLoading && <LoadingState label="Loading tools..." />}

      <section className="panel-pro">
        <h3>Natural language → SPL</h3>
        <textarea className="input-area" rows={3} value={nlQuery} onChange={(e) => setNlQuery(e.target.value)} />
        <div className="preset-row">
          {PRESETS.map((p) => (
            <button key={p} type="button" className="chip" onClick={() => setNlQuery(p)}>
              {p.slice(0, 42)}…
            </button>
          ))}
        </div>
        <div className="btn-row">
          <button type="button" className="btn btn-primary" disabled={loading} onClick={generateSpl}>
            Generate SPL
          </button>
          <button type="button" className="btn btn-secondary" disabled={loading || !spl} onClick={runSpl}>
            Run query
          </button>
        </div>
        {spl && <pre className="code-block">{spl}</pre>}
        {splSource && <p className="muted">Source: {splSource}</p>}
        {runResult && <pre className="code-block result-block">{runResult}</pre>}
      </section>

      <section className="panel-pro">
        <h3>Tool explorer</h3>
        <div className="btn-row">
          <select value={selectedTool} onChange={(e) => setSelectedTool(e.target.value)} className="select-input">
            {(tools.length ? tools : (mcp?.tools || []).map((n) => ({ name: String(n) }))).map((t) => (
              <option key={t.name} value={t.name}>
                {t.name}
              </option>
            ))}
          </select>
          <button type="button" className="btn btn-secondary" disabled={loading} onClick={callTool}>
            Call tool
          </button>
        </div>
        {toolResult && <pre className="code-block result-block">{toolResult}</pre>}
      </section>


    </>
  );
}