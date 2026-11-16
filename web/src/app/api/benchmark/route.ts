import { readFile } from "node:fs/promises";
import path from "node:path";
export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export async function GET() {
  try {
    const folder = path.resolve(process.cwd(), "../benchmark/fpt_2025");
    const cases = JSON.parse(
      await readFile(path.join(folder, "cases.json"), "utf8"),
    ) as {
      id: string;
      question: string;
      suite: string;
      split: string;
      primary_category: string;
    }[];
    // Explicit projection: no answers, evidence, answerability or gold coordinates.
    return Response.json({
      cases: cases.map((c) => ({
        id: c.id,
        question: c.question,
        suite: c.suite,
        split: c.split,
        category: c.primary_category,
      })),
      source: "benchmark/fpt_2025/cases.json",
      systemCaseCount: 60,
    });
  } catch {
    return Response.json(
      {
        error:
          "Không đọc được bộ benchmark trong repo. Kiểm tra thư mục benchmark/fpt_2025.",
      },
      { status: 503 },
    );
  }
}
