import { proxyBackend } from "@/lib/backend";
export const runtime = "nodejs";
export async function POST(request: Request) {
  return proxyBackend(request, "/cancel", "POST");
}
