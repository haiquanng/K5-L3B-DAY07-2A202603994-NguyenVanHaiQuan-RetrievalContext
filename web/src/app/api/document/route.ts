import { stat } from "node:fs/promises";
import { createReadStream } from "node:fs";
import { Readable } from "node:stream";
import path from "node:path";
export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export async function GET(request: Request) {
  const file = path.resolve(process.cwd(), "../pdf/BCTN_2025_ad403f779b.pdf");
  try {
    const { size } = await stat(file);
    if (new URL(request.url).searchParams.get("meta") === "1")
      return Response.json({
        available: true,
        bytes: size,
        pages: 232,
      });
    const headers: Record<string, string> = {
      "Content-Type": "application/pdf",
      "Content-Disposition": 'inline; filename="FPT-Annual-Report-2025.pdf"',
      "Accept-Ranges": "bytes",
      "Cache-Control": "private, max-age=3600",
    };
    const range = request.headers.get("range");
    let start = 0,
      end = size - 1,
      status = 200;
    if (range) {
      const match = /^bytes=(\d*)-(\d*)$/.exec(range);
      if (!match || (!match[1] && !match[2]))
        return new Response(null, {
          status: 416,
          headers: { "Content-Range": `bytes */${size}` },
        });
      if (!match[1]) start = Math.max(0, size - Number(match[2]));
      else {
        start = Number(match[1]);
        if (match[2]) end = Math.min(Number(match[2]), size - 1);
      }
      if (
        !Number.isSafeInteger(start) ||
        !Number.isSafeInteger(end) ||
        start > end ||
        start >= size
      )
        return new Response(null, {
          status: 416,
          headers: { "Content-Range": `bytes */${size}` },
        });
      status = 206;
      headers["Content-Range"] = `bytes ${start}-${end}/${size}`;
    }
    headers["Content-Length"] = String(end - start + 1);
    const body = Readable.toWeb(
      createReadStream(file, { start, end }),
    ) as ReadableStream;
    return new Response(body, { status, headers });
  } catch {
    return Response.json(
      { error: "Không tìm thấy PDF nguồn trong thư mục pdf/." },
      { status: 404 },
    );
  }
}
