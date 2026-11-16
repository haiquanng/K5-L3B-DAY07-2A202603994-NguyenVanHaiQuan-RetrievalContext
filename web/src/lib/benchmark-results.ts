import type { RunSummary } from "./types";

export function checkRun(input: unknown, ids: string[]): RunSummary {
  const d = input as RunSummary;
  if (
    !d ||
    typeof d !== "object" ||
    !Array.isArray(d.details) ||
    !d.strict_pass
  )
    throw Error("File cần là summary.json từ tools.py score.");
  if (
    d.strict_pass.N !== ids.length ||
    d.details.length !== ids.length ||
    new Set(d.details.map((c) => c.query_id)).size !== ids.length ||
    d.details.some((c) => !ids.includes(c.query_id))
  )
    throw Error("Danh sách case không trùng toàn bộ suite/split đang chọn.");
  const fields = [
    "strict_pass",
    "hit_at_1",
    "evidence_hit_at_3",
    "context_evidence_rate",
    "correct_abstention",
    "false_abstention",
    "valid_citations",
    "tool_use_successful_runs",
    "grounded_answer_normalized",
  ] as const;
  for (const f of fields) {
    const r = d[f];
    if (
      !r ||
      !Number.isInteger(r.n) ||
      !Number.isInteger(r.N) ||
      r.n < 0 ||
      r.N < r.n
    )
      throw Error(`Metric ${f} không hợp lệ.`);
  }
  if (
    d.details.some(
      (c) =>
        typeof c.passed !== "boolean" ||
        typeof c.reviewed !== "boolean" ||
        typeof c.reason !== "string",
    ) ||
    d.details.filter((c) => c.passed).length !== d.strict_pass.n
  )
    throw Error("Nhãn từng câu không khớp tổng số đạt.");
  if (!d.statuses || !d.per_category_including_abstention)
    throw Error("Thiếu thống kê trạng thái hoặc nhóm câu.");
  if (
    d.details.some(
      (c) =>
        c.passed &&
        (!c.reviewed || !["answered", "abstain"].includes(c.status)),
    )
  )
    throw Error("Case đạt phải có review và output thành công.");
  if (
    typeof d.cost_usd_known_subtotal !== "number" ||
    !Number.isFinite(d.cost_usd_known_subtotal) ||
    d.cost_usd_known_subtotal < 0 ||
    !Number.isInteger(d.cost_unknown_cases) ||
    d.cost_unknown_cases < 0 ||
    d.cost_unknown_cases > ids.length
  )
    throw Error("Chi phí hoặc số case chưa biết chi phí không hợp lệ.");
  for (const value of [d.latency_ms_median, d.latency_ms_p95_nearest_rank])
    if (
      value !== null &&
      (typeof value !== "number" || !Number.isFinite(value) || value < 0)
    )
      throw Error("Latency phải là số không âm hoặc null.");
  for (const count of Object.values(d.statuses))
    if (!Number.isInteger(count) || count < 0)
      throw Error("Số lượng status không hợp lệ.");
  for (const r of Object.values(d.per_category_including_abstention))
    if (
      !r ||
      !Number.isInteger(r.n) ||
      !Number.isInteger(r.N) ||
      r.n < 0 ||
      r.N < r.n
    )
      throw Error("Tỷ lệ theo nhóm không hợp lệ.");
  return d;
}
