import { proxyBackend } from "@/lib/backend";
export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export async function GET(request: Request) {
  const chunk = new URL(request.url).searchParams.get("chunk") ?? "";
  if (!/^fpt-ar2025:[a-zA-Z0-9:_-]{1,140}$/.test(chunk)) {
    return Response.json({ error: "Nguồn không hợp lệ." }, { status: 400 });
  }
  return proxyBackend(request, `/asset?chunk=${encodeURIComponent(chunk)}`);
}
