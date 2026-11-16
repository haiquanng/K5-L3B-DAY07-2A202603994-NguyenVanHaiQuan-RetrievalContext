import type { AgentEvent } from "./contracts";

/** Handles split UTF-8 code points, multiple events per chunk and a final line without LF. */
export async function* readAgentEvents(
  body: ReadableStream<Uint8Array>,
): AsyncGenerator<AgentEvent> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    while (true) {
      const { value, done } = await reader.read();
      buffer += done
        ? decoder.decode()
        : decoder.decode(value, { stream: true });
      let boundary: number;
      while ((boundary = buffer.indexOf("\n")) >= 0) {
        const line = buffer.slice(0, boundary).trim();
        buffer = buffer.slice(boundary + 1);
        if (line) yield JSON.parse(line) as AgentEvent;
      }
      if (buffer.length > 2_000_000)
        throw new Error("Phản hồi vượt kích thước cho phép.");
      if (done) {
        if (buffer.trim()) yield JSON.parse(buffer) as AgentEvent;
        break;
      }
    }
  } finally {
    await reader.cancel().catch(() => {});
    reader.releaseLock();
  }
}

export function citationMarkdown(answer: string, citations: string[]): string {
  const allowed = new Set(citations);
  return answer.replace(
    /\[(fpt-ar2025:[a-zA-Z0-9:_-]+)\]/g,
    (literal, id: string) =>
      allowed.has(id)
        ? `[${citations.indexOf(id) + 1}](#source-${encodeURIComponent(id)})`
        : literal,
  );
}
