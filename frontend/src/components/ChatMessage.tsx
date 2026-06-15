import type { ReactNode } from "react";
import type { IntegrationStatus } from "../types";
import { SplCodeBlock } from "./SplCodeBlock";

interface ChatMessageProps {
  content: string;
  integrations?: IntegrationStatus | null;
}

type Block = { type: "text"; value: string } | { type: "code"; lang: string; value: string };

function splitBlocks(content: string): Block[] {
  const blocks: Block[] = [];
  const re = /```(\w+)?\n?([\s\S]*?)```/g;
  let last = 0;
  let match: RegExpExecArray | null;
  while ((match = re.exec(content)) !== null) {
    if (match.index > last) {
      blocks.push({ type: "text", value: content.slice(last, match.index) });
    }
    blocks.push({ type: "code", lang: match[1] || "text", value: match[2].trim() });
    last = match.index + match[0].length;
  }
  if (last < content.length) {
    blocks.push({ type: "text", value: content.slice(last) });
  }
  return blocks.length ? blocks : [{ type: "text", value: content }];
}

function renderInline(text: string) {
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith("`") && part.endsWith("`")) {
      return (
        <code key={i} className="chat-inline-code">
          {part.slice(1, -1)}
        </code>
      );
    }
    return <span key={i}>{part}</span>;
  });
}

function renderTextBlock(text: string) {
  const lines = text.split("\n");
  const nodes: ReactNode[] = [];
  let listItems: string[] = [];

  const flushList = () => {
    if (!listItems.length) return;
    nodes.push(
      <ul key={`list-${nodes.length}`} className="chat-list">
        {listItems.map((item, idx) => (
          <li key={idx}>{renderInline(item)}</li>
        ))}
      </ul>
    );
    listItems = [];
  };

  lines.forEach((line, idx) => {
    const trimmed = line.trim();
    if (!trimmed) {
      flushList();
      return;
    }
    if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
      listItems.push(trimmed.slice(2));
      return;
    }
    flushList();
    nodes.push(
      <p key={`p-${idx}`} className="chat-paragraph">
        {renderInline(trimmed)}
      </p>
    );
  });
  flushList();
  return nodes;
}

export function ChatMessage({ content, integrations }: ChatMessageProps) {
  const blocks = splitBlocks(content);
  return (
    <div className="chat-message">
      {blocks.map((block, i) => {
        if (block.type === "code") {
          const isSpl = ["splunk", "spl", "sql"].includes(block.lang.toLowerCase()) || block.value.includes("index=");
          if (isSpl) {
            return <SplCodeBlock key={i} code={block.value} integrations={integrations} />;
          }
          return (
            <pre key={i} className="chat-code-block">
              {block.value}
            </pre>
          );
        }
        return <div key={i}>{renderTextBlock(block.value)}</div>;
      })}
    </div>
  );
}