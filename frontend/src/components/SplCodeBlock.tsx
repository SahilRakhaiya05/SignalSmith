import { useState } from "react";
import { Check, Copy, ExternalLink, Play } from "lucide-react";
import { api } from "../api";
import type { IntegrationStatus } from "../types";
import { splunkSearchUrl } from "../utils/splunkSearchUrl";

interface SplCodeBlockProps {
  code: string;
  integrations?: IntegrationStatus | null;
  runnable?: boolean;
}

export function SplCodeBlock({ code, integrations, runnable = true }: SplCodeBlockProps) {
  const [copied, setCopied] = useState(false);
  const [running, setRunning] = useState(false);
  const [runResult, setRunResult] = useState<string | null>(null);
  const searchUrl = splunkSearchUrl(code, integrations);

  const copy = async () => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const run = async () => {
    setRunning(true);
    setRunResult(null);
    try {
      const res = await api.runMcpQuery(code);
      setRunResult(JSON.stringify(res.result, null, 2));
    } catch (e) {
      setRunResult(e instanceof Error ? e.message : String(e));
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="spl-code-block">
      <div className="spl-code-block__toolbar">
        <span className="spl-code-block__label">SPL</span>
        <div className="spl-code-block__actions">
          <button type="button" className="spl-code-block__btn" onClick={copy}>
            {copied ? <Check size={13} /> : <Copy size={13} />}
            {copied ? "Copied" : "Copy"}
          </button>
          {runnable && (
            <button type="button" className="spl-code-block__btn" onClick={run} disabled={running}>
              <Play size={13} />
              {running ? "Running…" : "Run"}
            </button>
          )}
          {searchUrl && (
            <a href={searchUrl} target="_blank" rel="noreferrer" className="spl-code-block__btn">
              <ExternalLink size={13} />
              Splunk
            </a>
          )}
        </div>
      </div>
      <pre className="spl-code-block__code">{code}</pre>
      {runResult && <pre className="spl-code-block__result">{runResult}</pre>}
    </div>
  );
}