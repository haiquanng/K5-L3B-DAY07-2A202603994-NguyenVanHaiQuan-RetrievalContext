"use client";
import {
  ArrowDownToLine,
  ArrowRight,
  BookOpenCheck,
  Check,
  ChevronDown,
  CircleDashed,
  ClipboardCheck,
  Database,
  FileJson,
  FlaskConical,
  GitBranch,
  Network,
  ShieldCheck,
} from "lucide-react";
import type { View } from "@/lib/types";
import { SOURCE, downloadJson } from "@/lib/demo";
import { Pill } from "./ui";
const SECTIONS = [
  {
    icon: Database,
    title: "Dữ liệu & benchmark",
    points: 13,
    view: "library",
    items: [
      "Nguồn FPT 2025, hash, 232 trang và quy ước số trang.",
      "Kết nối embedding và vector store Day 6; ledger toàn bộ nội dung hữu ích.",
      "240 câu đã chia dev/test; gold tách khỏi dữ liệu gửi agent.",
    ],
    artifacts: [
      "source.json",
      "index_config.json + page_ledger.json",
      "cases.json + queries/*.json",
    ],
    needs: "Xem thống kê index trực tiếp trong Thư viện",
  },
  {
    icon: Network,
    title: "Ba phương pháp retrieval",
    points: 17,
    view: "benchmark",
    items: [
      "Dense trên vector store Day 6; lexical và hybrid là hai phương pháp bổ sung.",
      "Lưu query gốc, rewrite, filter, candidate, rank, score và lỗi.",
      "Dùng cùng corpus/version và cutoff để so sánh.",
    ],
    artifacts: [
      "retrieval_config.json",
      "original_query_ranking + pipeline_ranking",
      "retrieval_traces.json",
    ],
    needs: "Backend hỗ trợ dense, lexical và hybrid",
  },
  {
    icon: GitBranch,
    title: "Agent & context",
    points: 17,
    view: "chat",
    items: [
      "Model thật quyết định gọi retrieval; trace từng tool call và điều kiện dừng.",
      "Context có budget, lựa chọn, dedup, metadata và đủ evidence multi-hop.",
      "Citation có trong context và hỗ trợ câu trả lời; xử lý từ chối, lỗi, timeout.",
    ],
    artifacts: [
      "traces.json",
      "context + citation metadata",
      "model + usage + stop_reason",
    ],
    needs: "Chat đã nối agent; cần kiểm chứng chất lượng",
  },
  {
    icon: ClipboardCheck,
    title: "Đánh giá có kiểm chứng",
    points: 17,
    view: "benchmark",
    items: [
      "Hit@1, Evidence Hit@3, Context Evidence Rate, câu trả lời và context mức 0–2.",
      "Citation hợp lệ; abstention đúng, false abstention, tool use.",
      "Báo n/N, latency, chi phí, lỗi; human review mở đúng trang và vùng nguồn.",
    ],
    artifacts: ["summary.json", "reviews.json", "per-case outcomes"],
    needs: "Cần nhập trace và nhãn kiểm chứng",
  },
  {
    icon: FlaskConical,
    title: "Thử nghiệm & cải thiện",
    points: 13,
    view: "benchmark",
    items: [
      "Ít nhất hai thay đổi có giả thuyết: rerank, neighbor context hoặc cấu hình khác.",
      "Đọc lỗi dev, so trước/sau; chốt cấu hình và tiêu chí chọn trước test.",
      "Chạy baseline và cấu hình chọn trên cùng toàn bộ test; không tuning bằng test.",
    ],
    artifacts: [
      "dev-experiment-01/ + dev-experiment-02/",
      "frozen_run_manifest.json",
      "baseline-test/ + selected-test/",
    ],
    needs: "Cần 2 thí nghiệm dev và test sau freeze",
  },
  {
    icon: FileJson,
    title: "Tái lập & báo cáo",
    points: 8,
    view: "benchmark",
    items: [
      "Code, lệnh chạy, model, tham số, phiên bản dữ liệu/index và chi phí.",
      "Báo cáo phân tích lỗi, đánh đổi, giới hạn; không dùng mock làm kết quả.",
      "Giữ trace và review gắn cùng query ID; xuất artifacts để đối chiếu.",
    ],
    artifacts: [
      "README + requirements + lockfile",
      "run_manifest.json",
      "report/individual/",
    ],
    needs: "Cần gói kết quả thực nghiệm",
  },
  {
    icon: ShieldCheck,
    title: "Advanced · tài liệu đa phương thức",
    points: 15,
    view: "library",
    items: [
      "Index toàn bộ nội dung hữu ích của PDF ≥100 trang, gồm bảng, ảnh và biểu đồ.",
      "Mỗi split 70 câu: 56 có đáp án trong đủ 5 nhóm và 14 thiếu bằng chứng.",
      "Test đạt ≥63/70 không làm tròn; lỗi/timeout/missing vẫn tính fail; audit từng câu.",
    ],
    artifacts: [
      "multimodal index + bbox/crop provenance",
      "advanced.test.json + 70 traces/reviews",
      "summary.json + evidence audit",
    ],
    needs: "Bonus chỉ xác nhận khi đủ mọi điều kiện",
  },
] as const;
export function LabGuide({ onNavigate }: { onNavigate: (v: View) => void }) {
  return (
    <div className="page-scroll">
      <div className="content-page">
        <div className="page-intro">
          <div>
            <span className="eyebrow">FROM DEMO TO EVIDENCE</span>
            <h1>Đối chiếu yêu cầu lab</h1>
            <p>
              Mỗi yêu cầu đều có một nơi để trình bày và một bằng chứng để kiểm
              tra.
            </p>
          </div>
          <button
            className="secondary-button"
            onClick={() =>
              downloadJson("lab07-evidence-checklist.json", {
                status: "ui_scaffold_only",
                source: SOURCE,
                sections: SECTIONS.map((s) => ({
                  requirement: s.title,
                  points: s.points,
                  expected: s.items,
                  artifacts: s.artifacts,
                  status: "pending_real_evidence",
                })),
              })
            }
          >
            <ArrowDownToLine size={15} /> Xuất checklist
          </button>
        </div>
        <div className="lab-summary">
          <div className="lab-summary-icon">
            <BookOpenCheck size={29} />
          </div>
          <div>
            <h2>Sẵn sàng trình diễn. Chưa thay thế bằng chứng chạy thật.</h2>
            <p>
              Khung UI bao phủ 85 điểm cơ bản và 15 điểm advanced. Trạng thái
              bên dưới mô tả phần cần nối và kiểm chứng, không tự đánh dấu hoàn
              thành lab.
            </p>
          </div>
          <div className="lab-points">
            <strong>
              85 <span>+ 15</span>
            </strong>
            <small>theo rubric Lab 07</small>
          </div>
        </div>
        <div className="lab-requirements">
          {SECTIONS.map((s, i) => (
            <details key={s.title} className="requirement-card" open={i === 0}>
              <summary>
                <span className="requirement-icon">
                  <s.icon size={19} />
                </span>
                <span>
                  <strong>{s.title}</strong>
                  <small>{s.needs}</small>
                </span>
                <Pill tone="neutral">{s.points} điểm</Pill>
                <ChevronDown size={17} />
              </summary>
              <div className="requirement-body">
                <ul>
                  {s.items.map((item) => (
                    <li key={item}>
                      <CircleDashed size={14} />
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
                <div className="artifact-list">
                  <span>BẰNG CHỨNG CẦN CÓ</span>
                  {s.artifacts.map((a) => (
                    <code key={a}>{a}</code>
                  ))}
                </div>
                <button
                  className="text-button"
                  onClick={() => onNavigate(s.view)}
                >
                  <ArrowRight size={14} /> Mở màn hình liên quan
                </button>
              </div>
            </details>
          ))}
        </div>
        <div className="demo-tour">
          <h2>Luồng demo gợi ý</h2>
          <div>
            {[
              "Mở thư viện, xác nhận đúng PDF",
              "Hỏi câu mẫu, mở citation và trang gốc",
              "Xem query, context và điều kiện dừng",
              "Thử câu thiếu bằng chứng",
              "Mở benchmark, nhập baseline & selected",
              "Xuất transcript và checklist",
            ].map((s, i) => (
              <span key={s}>
                <i>{i + 1}</i>
                {s}
              </span>
            ))}
          </div>
          <p>
            <Check size={14} /> Đã có khung cho 60 ca kiểm thử hệ thống tại
            benchmark/fpt_2025/SYSTEM_CASEBOOK.md.
          </p>
        </div>
      </div>
    </div>
  );
}
