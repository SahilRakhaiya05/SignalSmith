import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { ChatMessage } from "../components/ChatMessage";
import { useSession } from "../context/SessionContext";
import { PageLoadGate } from "../components/ui/PageLoadGate";
import { AssistantPageSkeleton } from "../components/ui/Skeleton";
import { clearChatMessages, loadChatMessages, saveChatMessages } from "../utils/chatStorage";

interface ChatMsg {
  role: "user" | "assistant";
  content: string;
}

const STARTERS = [
  "What should I do next in the pipeline?",
  "Top 10 services by event volume",
  "Compare baseline vs candidate indexes",
  "Explain my latest validation results",
  "SPL for health-check noise",
  "Which policies are safe to cut ingest?",
  "SPL for payment outage detection",
  "Walk me through shadow validation",
];

function looksLikeSplRequest(text: string): boolean {
  return /\b(spl|search|query|generate|index|stats|top|show|find|volume|events)\b/i.test(text);
}

function looksLikeExplainRequest(text: string): boolean {
  return /\b(explain|why|how|what|walk|help|validate|validation|pipeline|policy|policies|coverage|detection)\b/i.test(text);
}

export function AssistantView() {
  const { analysis, proposal, validations, integrations, splunkConnection, sessionLoading } = useSession();
  const [messages, setMessages] = useState<ChatMsg[]>(() => loadChatMessages());
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const ai = integrations?.ai;
  const mentorOnline = ai?.available ?? false;

  useEffect(() => {
    saveChatMessages(messages);
  }, [messages]);

  useEffect(() => {
    const el = inputRef.current;
    if (el) {
      el.style.height = "auto";
      el.style.height = `${el.scrollHeight}px`;
    }
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, loading, input]);

  const appendAssistant = (content: string, userMsg: ChatMsg[]) => {
    setMessages([...userMsg, { role: "assistant", content }]);
  };

  const send = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || loading) return;

    setError(null);
    const userMsg: ChatMsg = { role: "user", content: trimmed };
    const nextMessages = [...messages, userMsg];
    setMessages(nextMessages);
    setLoading(true);

    try {
      if (mentorOnline) {
        const history = messages.map((m) => ({ role: m.role, content: m.content }));
        const res = await api.aiChat(trimmed, history);
        appendAssistant(res.reply, nextMessages);
      } else if (looksLikeSplRequest(trimmed)) {
        const res = await api.generateSpl(trimmed);
        appendAssistant(
          `\`\`\`splunk\n${res.spl}\n\`\`\`\n\nUse **Run** on the block to execute in Splunk.`,
          nextMessages
        );
      } else if (looksLikeExplainRequest(trimmed)) {
        try {
          const res = await api.aiExplain(trimmed);
          appendAssistant(res.reply, nextMessages);
        } catch {
          appendAssistant(
            "**SPL mode** — Mentor is offline. Ask for a search (e.g. “top services by volume”) and I'll return runnable SPL from templates.",
            nextMessages
          );
        }
      } else {
        appendAssistant(
          "**SPL mode** — Ask for SPL, pipeline steps, or detection queries. Example: “SPL for credential stuffing”.",
          nextMessages
        );
      }
    } catch (e) {
      if (looksLikeSplRequest(trimmed)) {
        try {
          const res = await api.generateSpl(trimmed);
          appendAssistant(`\`\`\`splunk\n${res.spl}\n\`\`\`\n\nUse **Run** on the block to execute in Splunk.`, nextMessages);
        } catch (splErr) {
          const msg = splErr instanceof Error ? splErr.message : String(splErr);
          setError(msg);
          appendAssistant(`Could not generate SPL: ${msg}`, nextMessages);
        }
      } else if (looksLikeExplainRequest(trimmed)) {
        try {
          const res = await api.generateSpl(trimmed);
          appendAssistant(`\`\`\`splunk\n${res.spl}\n\`\`\`\n\nMentor is offline — here is template SPL for your question.`, nextMessages);
        } catch (splErr) {
          const msg = splErr instanceof Error ? splErr.message : String(e instanceof Error ? e.message : String(e));
          setError(msg);
          appendAssistant(msg, nextMessages);
        }
      } else {
        const msg = e instanceof Error ? e.message : String(e);
        setError(msg);
        appendAssistant(msg, nextMessages);
      }
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  };

  const latestVal = validations[validations.length - 1];
  const pipelineStep = latestVal
    ? latestVal.status === "passed"
      ? "Ready to approve"
      : "Needs revise"
    : proposal
      ? "Apply & validate"
      : analysis
        ? "Review policies"
        : "Run bootstrap";

  return (
    <PageLoadGate loading={sessionLoading} skeleton={<AssistantPageSkeleton />}>
      <div className="assistant-page">
        <div className="assistant-layout">
          <aside className="assistant-sidebar">
            <div className="assistant-sidebar__head">
              <h3>Quick asks</h3>
              {messages.length > 0 && (
                <button
                  type="button"
                  className="btn btn-ghost btn-sm"
                  onClick={() => {
                    setMessages([]);
                    clearChatMessages();
                  }}
                >
                  Clear
                </button>
              )}
            </div>
            <div className="assistant-starters">
              {STARTERS.map((s) => (
                <button key={s} type="button" className="starter-chip" disabled={loading} onClick={() => send(s)}>
                  {s}
                </button>
              ))}
            </div>

            <div className="assistant-context">
              <h4>Your session</h4>
              <ul>
                <li>Next step: <strong>{pipelineStep}</strong></li>
                <li>Baseline: {analysis?.baseline_event_count?.toLocaleString() ?? "—"} events</li>
                <li>Policies: {proposal?.recommendations?.length ?? 0}</li>
                <li>
                  Validation:{" "}
                  {latestVal ? `${latestVal.tests_passed}/${latestVal.tests_total} · ${latestVal.coverage_percent}%` : "—"}
                </li>
                <li>Splunk: {splunkConnection === "splunk_mcp" ? "MCP" : splunkConnection === "offline" ? "Offline" : "Connected"}</li>
                <li>
                  Mentor:{" "}
                  <span className={mentorOnline ? "assistant-status assistant-status--on" : "assistant-status"}>
                    {mentorOnline ? "Online" : "SPL mode"}
                  </span>
                </li>
              </ul>
              <Link to="/workflow" className="btn btn-secondary btn-sm assistant-context__link">
                Open pipeline
              </Link>
            </div>
          </aside>

          <section className="assistant-chat" ref={scrollRef} aria-label="SignalSmith Mentor chat">
            <div className="assistant-messages">
              {messages.length === 0 && (
                <div className="assistant-welcome">
                  <h3>SignalSmith Mentor</h3>
                  <p>
                    Direct guidance on your pipeline, SPL, and validation — grounded in your live session.
                    Ask what to do next, request searches, or drill into coverage results.
                  </p>
                </div>
              )}
              {messages.map((m, i) => (
                <div key={i} className={`chat-bubble chat-bubble--${m.role}`}>
                  <span className="chat-bubble__role">{m.role === "user" ? "You" : "Mentor"}</span>
                  <div className="chat-bubble__body">
                    {m.role === "assistant" ? (
                      <ChatMessage content={m.content} integrations={integrations} />
                    ) : (
                      m.content
                    )}
                  </div>
                </div>
              ))}
              {loading && (
                <div className="chat-bubble chat-bubble--assistant">
                  <span className="chat-bubble__role">Mentor</span>
                  <div className="chat-bubble__body chat-bubble__typing">Thinking…</div>
                </div>
              )}
            </div>

            {error && <p className="assistant-error">{error}</p>}

            <form
              className="assistant-composer"
              onSubmit={(e) => {
                e.preventDefault();
                const text = input;
                setInput("");
                void send(text);
              }}
            >
              <div className="assistant-composer__field">
                <textarea
                  ref={inputRef}
                  className="assistant-composer__input"
                  rows={2}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Ask Mentor: next pipeline step, SPL, validation, policies…"
                  aria-label="Message to SignalSmith Mentor"
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      const text = input;
                      setInput("");
                      void send(text);
                    }
                  }}
                />
                <span className="assistant-composer__hint">Shift+Enter for new line</span>
              </div>
              <button type="submit" className="btn btn-primary" disabled={loading || !input.trim()}>
                Send
              </button>
            </form>
          </section>
        </div>
      </div>
    </PageLoadGate>
  );
}