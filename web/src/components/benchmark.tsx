"use client";
import { checkRun } from "@/lib/benchmark-results";
import { useEffect, useRef, useState } from "react";
import {
  ArrowDownToLine,
  ArrowRight,
  BarChart3,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  CircleDashed,
  FileJson,
  FlaskConical,
  GitCompareArrows,
  Search,
  Upload,
  XCircle,
} from "lucide-react";
import type { BenchmarkCase, RunSummary, Ratio } from "@/lib/types";
import { CATEGORY_LABELS, downloadJson } from "@/lib/demo";
import { Pill } from "./ui";
const pct = (r?: Ratio) =>
  r && r.N ? `${((r.n / r.N) * 100).toFixed(1)}%` : "—";
const fraction = (r?: Ratio) => (r ? `${r.n}/${r.N} · ${pct(r)}` : "—");
export function Benchmark({ onTry }: { onTry: (text: string) => void }) {
  const [cases, setCases] = useState<BenchmarkCase[]>([]),
    [loading, setLoading] = useState(true),
    [error, setError] = useState("");
  const [suite, setSuite] = useState<"basic" | "advanced">("advanced"),
    [split, setSplit] = useState<"dev" | "test">("dev");
  const [category, setCategory] = useState("all"),
    [search, setSearch] = useState(""),
    [page, setPage] = useState(0),
    [tab, setTab] = useState<"cases" | "compare">("cases");
  const [runs, setRuns] = useState<Record<string, RunSummary>>({}),
    [slot, setSlot] = useState<"baseline" | "selected">("selected"),
    [filename, setFilename] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);
  useEffect(() => {
    let cancelled = false;
    fetch("/api/benchmark")
      .then(async (r) => {
        if (!r.ok) throw Error("Không tải được benchmark.");
        return r.json();
      })
      .then((data) => {
        if (!cancelled) setCases(data.cases);
      })
      .catch((e) => {
        if (!cancelled) setError(String(e.message));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);
  const group = cases.filter((c) => c.suite === suite && c.split === split);
  const filtered = group.filter(
    (c) =>
      (category === "all" || c.category === category) &&
      `${c.id} ${c.question}`.toLowerCase().includes(search.toLowerCase()),
  );
  const runKey = `${suite}.${split}`,
    run = runs[`${runKey}.selected`],
    baseline = runs[`${runKey}.baseline`];
  const shown = filtered.slice(page * 8, page * 8 + 8);
  const countPages = Math.max(1, Math.ceil(filtered.length / 8));
  const changeSuite = (v: "basic" | "advanced") => {
    setSuite(v);
    setPage(0);
    setFilename("");
    setError("");
  };
  const changeSplit = (v: "dev" | "test") => {
    setSplit(v);
    setPage(0);
    setFilename("");
    setError("");
  };
  const importRun = async (file: File) => {
    try {
      if (file.size > 10 * 1024 * 1024)
        throw Error("File kết quả tối đa 10 MB.");
      const data = checkRun(
        JSON.parse(await file.text()),
        group.map((c) => c.id),
      );
      setRuns((prev) => ({ ...prev, [`${runKey}.${slot}`]: data }));
      setFilename(file.name);
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không đọc được file JSON.");
    }
  };
  const metricCards = [
    { label: "Tỷ lệ đạt", value: run?.strict_pass },
    { label: "Hit@1", value: run?.hit_at_1 },
    { label: "Evidence Hit@3", value: run?.evidence_hit_at_3 },
    { label: "Context đủ evidence", value: run?.context_evidence_rate },
  ];
  return (
    <div className="page-scroll">
      <div className="content-page benchmark-page">
        <div className="page-intro">
          <div>
            <span className="eyebrow">MEASURE WHAT MATTERS</span>
            <h1>Phòng thử nghiệm</h1>
            <p>Đánh giá retrieval, ngữ cảnh và chất lượng câu trả lời.</p>
          </div>
          <div className="heading-actions">
            <button
              className="secondary-button"
              disabled={!group.length}
              onClick={() =>
                downloadJson(
                  `fpt-${suite}-${split}-queries.json`,
                  group.map((c) => ({ id: c.id, question: c.question })),
                )
              }
            >
              <ArrowDownToLine size={15} /> Bộ câu hỏi
            </button>
            <button
              className="primary-button"
              disabled={!group.length}
              onClick={() => fileRef.current?.click()}
            >
              <Upload size={15} /> Nhập kết quả
            </button>
            <input
              ref={fileRef}
              type="file"
              accept=".json,application/json"
              hidden
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) void importRun(f);
                e.target.value = "";
              }}
            />
          </div>
        </div>
        <div className="experiment-toolbar">
          <div className="segmented" aria-label="Bộ benchmark">
            <button
              className={suite === "basic" ? "active" : ""}
              onClick={() => changeSuite("basic")}
            >
              Cơ bản <span>100</span>
            </button>
            <button
              className={suite === "advanced" ? "active" : ""}
              onClick={() => changeSuite("advanced")}
            >
              Advanced <span>140</span>
            </button>
          </div>
          <div className="experiment-filters">
            <label>
              Split
              <select
                aria-label="Chọn split benchmark"
                value={split}
                onChange={(e) => changeSplit(e.target.value as "dev" | "test")}
              >
                <option value="dev">Dev</option>
                <option value="test">Test</option>
              </select>
            </label>
            <label>
              Nhập cho
              <select
                aria-label="Cấu hình nhận kết quả"
                value={slot}
                onChange={(e) =>
                  setSlot(e.target.value as "baseline" | "selected")
                }
              >
                <option value="selected">Cấu hình chọn</option>
                <option value="baseline">Baseline</option>
              </select>
            </label>
          </div>
        </div>
        {error && (
          <div role="alert" className="error-banner">
            <XCircle size={17} />
            {error}
          </div>
        )}
        {filename && (
          <div role="status" className="import-note">
            <CheckCircle2 size={15} /> Đã nhập {filename}. Dữ liệu do người dùng
            cung cấp, chưa xác minh độc lập.
          </div>
        )}
        <div className="metrics-grid">
          {metricCards.map((m) => (
            <div className="metric" key={m.label}>
              <span>{m.label}</span>
              <strong>{pct(m.value)}</strong>
              <small>
                {m.value
                  ? `${m.value.n} / ${m.value.N} · kết quả đã nhập`
                  : "Chưa có lượt chạy thật"}
              </small>
            </div>
          ))}
        </div>
        <div className="benchmark-explainer">
          <span className="bench-icon">
            <FlaskConical size={20} />
          </span>
          <div>
            <strong>
              {suite === "advanced"
                ? "Đủ 5 nhóm nội dung. Cùng một chuẩn kiểm chứng."
                : "Từ tìm đúng nguồn đến trả lời có bằng chứng."}
            </strong>
            <p>
              {suite === "advanced"
                ? "Mỗi split: 56 câu có đáp án + 14 câu thiếu bằng chứng. Test cần ít nhất 63/70; lỗi và timeout vẫn nằm trong mẫu số."
                : "Mỗi split: 40 câu có đáp án + 10 câu thiếu bằng chứng. Thử nghiệm và chọn cấu hình trên dev trước khi chạy test."}
            </p>
          </div>
          <Pill tone={split === "test" ? "amber" : "purple"}>
            {split === "test" ? "Không dùng để tuning" : "Dành cho thử nghiệm"}
          </Pill>
        </div>
        <div className="section-tabs">
          <button
            className={tab === "cases" ? "active" : ""}
            onClick={() => setTab("cases")}
          >
            <FileJson size={16} /> Câu hỏi & kết quả<span>{group.length}</span>
          </button>
          <button
            className={tab === "compare" ? "active" : ""}
            onClick={() => setTab("compare")}
          >
            <GitCompareArrows size={16} /> So sánh cấu hình
          </button>
        </div>
        {tab === "cases" ? (
          <>
            <div className="table-toolbar">
              <label className="search-box">
                <Search size={16} />
                <input
                  aria-label="Tìm câu hỏi benchmark"
                  value={search}
                  placeholder="Tìm câu hỏi hoặc mã case…"
                  onChange={(e) => {
                    setSearch(e.target.value);
                    setPage(0);
                  }}
                />
              </label>
              <select
                aria-label="Lọc nhóm câu hỏi"
                value={category}
                onChange={(e) => {
                  setCategory(e.target.value);
                  setPage(0);
                }}
              >
                <option value="all">Tất cả nhóm</option>
                {Object.entries(CATEGORY_LABELS).map(([k, v]) => (
                  <option value={k} key={k}>
                    {v}
                  </option>
                ))}
              </select>
            </div>
            <div className="benchmark-table-wrap">
              <table className="benchmark-table">
                <thead>
                  <tr>
                    <th>CÂU HỎI</th>
                    <th>NHÓM CHÍNH</th>
                    <th>KẾT QUẢ</th>
                    <th>
                      <span className="sr-only">Thao tác</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {loading ? (
                    <tr>
                      <td colSpan={4} className="table-empty">
                        Đang đọc bộ câu hỏi trong repo…
                      </td>
                    </tr>
                  ) : shown.length ? (
                    shown.map((c) => {
                      const detail = run?.details.find(
                        (d) => d.query_id === c.id,
                      );
                      return (
                        <tr key={c.id}>
                          <td>
                            <code>{c.id}</code>
                            <p>{c.question}</p>
                          </td>
                          <td>
                            <Pill tone="neutral">
                              {CATEGORY_LABELS[c.category] ?? c.category}
                            </Pill>
                          </td>
                          <td>
                            <span
                              className={`case-status ${detail ? (detail.passed ? "passed" : "failed") : ""}`}
                            >
                              {detail ? (
                                detail.passed ? (
                                  <CheckCircle2 size={13} />
                                ) : (
                                  <XCircle size={13} />
                                )
                              ) : (
                                <CircleDashed size={13} />
                              )}{" "}
                              {detail
                                ? detail.passed
                                  ? "Đạt"
                                  : "Không đạt"
                                : "Chưa chạy"}
                            </span>
                            {detail && (
                              <small
                                className="review-reason"
                                title={detail.reason}
                              >
                                {detail.reason}
                              </small>
                            )}
                          </td>
                          <td>
                            <button
                              className="icon-button"
                              aria-label={`Thử câu ${c.id} qua agent`}
                              title="Thử qua agent, không tính điểm"
                              onClick={() => onTry(c.question)}
                            >
                              <ArrowRight size={16} />
                            </button>
                          </td>
                        </tr>
                      );
                    })
                  ) : (
                    <tr>
                      <td colSpan={4} className="table-empty">
                        Không có câu hỏi phù hợp bộ lọc.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
            <div className="pagination">
              <span>
                {filtered.length
                  ? `${page * 8 + 1}–${Math.min((page + 1) * 8, filtered.length)} trong ${filtered.length} câu`
                  : "0 câu"}
              </span>
              <div>
                <button
                  className="icon-button"
                  aria-label="Trang trước"
                  disabled={page === 0}
                  onClick={() => setPage((p) => p - 1)}
                >
                  <ChevronLeft size={16} />
                </button>
                <span>
                  {page + 1} / {countPages}
                </span>
                <button
                  className="icon-button"
                  aria-label="Trang sau"
                  disabled={page >= countPages - 1}
                  onClick={() => setPage((p) => p + 1)}
                >
                  <ChevronRight size={16} />
                </button>
              </div>
            </div>
          </>
        ) : (
          <>
            <div className="retrieval-methods">
              {[
                {
                  name: "Lexical",
                  desc: "Từ khóa & số liệu chính xác",
                  badge: "BM25 / TF-IDF",
                },
                {
                  name: "Dense",
                  desc: "Tìm theo ý nghĩa câu hỏi",
                  badge: "Vector store Day 6",
                },
                {
                  name: "Hybrid",
                  desc: "Kết hợp lexical + dense",
                  badge: "Fusion + reranking",
                },
              ].map((m) => (
                <div className="surface-card" key={m.name}>
                  <BarChart3 size={20} />
                  <h3>{m.name}</h3>
                  <p>{m.desc}</p>
                  <Pill tone="neutral">{m.badge}</Pill>
                  <small>Chờ log retrieval thật</small>
                </div>
              ))}
            </div>
            <div className="comparison-table">
              <table>
                <thead>
                  <tr>
                    <th>CHỈ SỐ</th>
                    <th>BASELINE</th>
                    <th>CẤU HÌNH CHỌN</th>
                  </tr>
                </thead>
                <tbody>
                  {[
                    { label: "Tỷ lệ đạt", key: "strict_pass" },
                    { label: "Hit@1", key: "hit_at_1" },
                    { label: "Evidence Hit@3", key: "evidence_hit_at_3" },
                    {
                      label: "Context Evidence Rate",
                      key: "context_evidence_rate",
                    },
                    {
                      label: "Grounded answer / 2",
                      key: "grounded_answer_normalized",
                    },
                    { label: "Citation hợp lệ", key: "valid_citations" },
                    { label: "Abstention đúng", key: "correct_abstention" },
                    { label: "False abstention", key: "false_abstention" },
                    { label: "Tool use", key: "tool_use_successful_runs" },
                  ].map((m) => (
                    <tr key={m.key}>
                      <td>{m.label}</td>
                      <td>
                        {fraction(
                          baseline?.[m.key as keyof RunSummary] as
                            Ratio | undefined,
                        )}
                      </td>
                      <td>
                        {fraction(
                          run?.[m.key as keyof RunSummary] as Ratio | undefined,
                        )}
                      </td>
                    </tr>
                  ))}
                  <tr>
                    <td>Latency median / p95</td>
                    <td>
                      {baseline
                        ? `${baseline.latency_ms_median ?? "—"} / ${baseline.latency_ms_p95_nearest_rank ?? "—"} ms`
                        : "—"}
                    </td>
                    <td>
                      {run
                        ? `${run.latency_ms_median ?? "—"} / ${run.latency_ms_p95_nearest_rank ?? "—"} ms`
                        : "—"}
                    </td>
                  </tr>
                  <tr>
                    <td>Chi phí đã biết</td>
                    <td>
                      {baseline
                        ? `$${baseline.cost_usd_known_subtotal.toFixed(4)} (${baseline.cost_unknown_cases} case thiếu)`
                        : "—"}
                    </td>
                    <td>
                      {run
                        ? `$${run.cost_usd_known_subtotal.toFixed(4)} (${run.cost_unknown_cases} case thiếu)`
                        : "—"}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div className="callout">
              Nhập hai file summary cho cùng suite và split. Tỷ lệ hiển thị n/N
              khi xem thẻ; không suy điểm từ hội thoại chưa qua chấm.
            </div>
          </>
        )}
        <>
          {run && (
            <div className="result-breakdown">
              <h3>Kết quả theo nhóm & trạng thái</h3>
              <div>
                {Object.entries(run.per_category_including_abstention).map(
                  ([key, r]) => (
                    <span key={key}>
                      <strong>{CATEGORY_LABELS[key] ?? key}</strong>
                      {fraction(r)}
                    </span>
                  ),
                )}
              </div>
              <p>
                {Object.entries(run.statuses)
                  .map(([key, n]) => `${key}: ${n}`)
                  .join(" · ")}
              </p>
            </div>
          )}
        </>
        <div className="benchmark-bottom">
          <span>
            <FileJson size={14} /> Nguồn: benchmark/fpt_2025 · chỉ hiển thị câu
            hỏi, không xuất gold cho chat
          </span>
          {run && (
            <button
              className="text-button"
              onClick={() =>
                downloadJson(`fpt-${runKey}-imported-summary.json`, run)
              }
            >
              <ArrowDownToLine size={14} /> Xuất kết quả đã nhập
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
