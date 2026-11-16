import type { AgentTrace, AnswerImage } from "./contracts";

export function sourceImages(trace?: AgentTrace): AnswerImage[] {
  if (trace?.status !== "answered") return [];
  // Old saved transcripts keep their source images, but no longer insert them in chat.
  return trace.source_images ?? trace.answer_images ?? [];
}

export function inlineImages(trace?: AgentTrace): AnswerImage[] {
  if (
    trace?.status !== "answered" ||
    trace.image_presentation?.mode !== "inline"
  )
    return [];
  const selected = new Set(trace.image_presentation.selected_chunk_ids);
  return (trace.answer_images ?? [])
    .filter((image) => selected.has(image.chunk_id))
    .slice(0, 2);
}
