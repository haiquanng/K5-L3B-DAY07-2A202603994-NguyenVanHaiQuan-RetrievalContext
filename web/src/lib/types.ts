import type { AgentTrace } from "./contracts";
export type View = "chat" | "library" | "benchmark" | "lab";
export type Method = "hybrid" | "dense" | "lexical";
export type Config = {
  method: Method;
  mode: "basic" | "advanced";
  topK: number;
  budget: number;
  maxSteps: number;
  rerank: boolean;
  neighbors: boolean;
};
export type Message = {
  id: string;
  role: "user" | "assistant";
  text: string;
  trace?: AgentTrace;
  config?: Config;
  stopped?: boolean;
  error?: boolean;
};
export type Conversation = {
  id: string;
  title: string;
  createdAt: string;
  messages: Message[];
};
export type BenchmarkCase = {
  id: string;
  question: string;
  suite: "basic" | "advanced";
  split: "dev" | "test";
  category: string;
};
export type Ratio = { n: number; N: number; rate: number | null };
export type RunSummary = {
  strict_pass: Ratio;
  hit_at_1: Ratio;
  evidence_hit_at_3: Ratio;
  context_evidence_rate: Ratio;
  correct_abstention: Ratio;
  false_abstention: Ratio;
  valid_citations: Ratio;
  tool_use_successful_runs: Ratio;
  grounded_answer_normalized: Ratio;
  per_category_including_abstention: Record<string, Ratio>;
  statuses: Record<string, number>;
  latency_ms_median: number | null;
  latency_ms_p95_nearest_rank: number | null;
  cost_usd_known_subtotal: number;
  cost_unknown_cases: number;
  details: {
    query_id: string;
    passed: boolean;
    status: string;
    reviewed: boolean;
    reason: string;
  }[];
};
