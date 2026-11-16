import type { Config } from "./types";
export const DEFAULT_CONFIG: Config = {
  method: "hybrid",
  mode: "advanced",
  topK: 5,
  budget: 24000,
  maxSteps: 6,
  rerank: false,
  neighbors: true,
};
export const METHOD_LABELS = {
  hybrid: "Hybrid",
  dense: "Dense",
  lexical: "Lexical",
};
export const SOURCE = {
  title: "Báo cáo thường niên FPT 2025",
  filename: "BCTN_2025_ad403f779b.pdf",
  pages: 232,
  sha256: "9449a7251d126b635988974dbc72c2773c7fff39f4e5e858b5f7d3928b4e0e6c",
  id: "fpt-ar2025-9449a725",
};
// Presentation fixtures, authored from the PDF. Never used as agent or benchmark results.
export const SUGGESTIONS = [
  {
    id: "growth",
    title: "Đọc số liệu",
    prompt: "Doanh thu FPT thay đổi thế nào trong giai đoạn 2021–2025?",
  },
  {
    id: "ownership",
    title: "Kết nối nhiều nguồn",
    prompt:
      "Giới hạn sở hữu nước ngoài và tỷ lệ sở hữu nước ngoài tại FPT năm 2025 là bao nhiêu?",
  },
  {
    id: "organization",
    title: "Khám phá sơ đồ",
    prompt: "Theo sơ đồ tổ chức, những công ty nào thuộc khối đầu tư của FPT?",
  },
  {
    id: "led",
    title: "Đọc bảng ESG",
    prompt: "Tỷ lệ sử dụng đèn LED thực tế của FPT năm 2025 là bao nhiêu?",
  },
  {
    id: "abstention",
    title: "Thiếu bằng chứng",
    prompt: "ROE của FPT cho từng quý năm 2025 là bao nhiêu?",
  },
];
export function downloadJson(name: string, data: unknown) {
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }),
  );
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
export const CATEGORY_LABELS: Record<string, string> = {
  text: "Văn bản",
  table: "Bảng",
  chart: "Biểu đồ",
  image: "Ảnh / sơ đồ",
  multi_hop: "Multi-hop",
};
