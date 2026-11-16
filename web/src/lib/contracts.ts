import type { Config } from "./types";
export type Chunk = {
  chunk_id: string;
  pdf_page: number;
  printed_page: string | null;
  kind: "text" | "table" | "chart" | "photo" | "diagram" | "infographic";
  text: string;
  bbox: number[];
  rank?: number;
  score?: number;
  title?: string;
};
export type TraceEvent = {
  event: string;
  query?: string;
  method?: string;
  elapsed_ms?: number;
  pdf_page?: number;
  chunk_id?: string;
  results?: (Partial<Chunk> | string)[];
  shown_to_model?: string[];
  status?: string;
};
export type AnswerImage = {
  chunk_id: string;
  pdf_page: number;
  printed_page: string | null;
  kind: Exclude<Chunk["kind"], "text">;
  title: string;
  alt: string;
  width: number;
  height: number;
  bbox: number[];
  matched_by: "portrait_name" | "cited_region";
  supporting_chunk_ids: string[];
  identity_source_chunk_ids: string[];
};
export type AgentTrace = {
  run_id: string;
  purpose: "interactive";
  query_id: string;
  question: string;
  status: "answered" | "abstain";
  answer: string;
  citations: string[];
  answer_images?: AnswerImage[];
  source_images?: AnswerImage[];
  image_presentation?: {
    mode: "sidebar" | "inline";
    request_quote: string;
    selected_chunk_ids: string[];
  };
  context_ids: string[];
  context: Chunk[];
  context_chars: number;
  dropped_for_budget: string[];
  events: TraceEvent[];
  original_query_ranking: Partial<Chunk>[];
  search_calls: number;
  model_calls: number;
  elapsed_ms: number;
  cost_usd: number | null;
  rerank_cost_usd: number | null;
  stop_reason: string;
  usage: { input: number; output: number; reasoning: number; cached: number };
  config: {
    model: string;
    method: string;
    budget_chars: number;
    max_steps: number;
    top_k: number;
  };
  ui_config: Config;
};
export type AgentEvent =
  | {
      event: "run_started";
      run_id: string;
      model: string;
      config: Config;
      index_version: string;
    }
  | { event: "loading"; message: string }
  | { event: "search_started"; query: string; method: string }
  | {
      event: "search";
      query: string;
      method: string;
      results: Chunk[];
      elapsed_ms: number;
    }
  | { event: "open_page"; pdf_page: number; results: string[] }
  | { event: "view_image"; chunk_id: string }
  | {
      event: "context";
      chunks: Chunk[];
      context_chars: number;
      budget: number;
      dropped_for_budget: string[];
    }
  | { event: "model_started"; step: number }
  | { event: "complete"; trace: AgentTrace }
  | {
      event: "error";
      code: string;
      message: string;
      retryable: boolean;
      run_id: string;
    };
export type BackendHealth = {
  ready: boolean;
  busy: boolean;
  model: string;
  embedding_loaded: boolean;
  chunks: number;
  embeddings: number;
  pages: number;
  indexed_pages: number;
  chunks_by_kind: Record<string, number>;
  ledger: {
    pdf_page: number;
    status: "indexed" | "skipped";
    chunks: number;
    reason: string | null;
  }[];
};
