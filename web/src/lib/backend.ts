// Server-only transport. Credentials stay in Python's existing root .env.
const backend = process.env.LUMINA_BACKEND_URL ?? "http://127.0.0.1:8007";

export async function proxyBackend(
  request: Request,
  endpoint: string,
  method: "GET" | "POST" = "GET",
) {
  if (method === "POST") {
    const origin = request.headers.get("origin");
    if (origin && origin !== new URL(request.url).origin) {
      return Response.json(
        { error: "Yêu cầu khác nguồn bị từ chối." },
        { status: 403 },
      );
    }
    if (
      request.headers.get("content-type")?.split(";")[0] !== "application/json"
    ) {
      return Response.json({ error: "Cần gửi JSON." }, { status: 415 });
    }
  }
  const abort = new AbortController();
  const onAbort = () => abort.abort();
  request.signal.addEventListener("abort", onAbort, { once: true });
  if (request.signal.aborted) abort.abort();
  // Cover cold embedding load and six model steps; cancellation remains available immediately.
  const timeout = setTimeout(
    () => abort.abort(),
    method === "POST" ? 300_000 : 10_000,
  );
  const cleanup = () => {
    clearTimeout(timeout);
    request.signal.removeEventListener("abort", onAbort);
  };
  try {
    const body = method === "POST" ? await request.text() : undefined;
    if (body && Buffer.byteLength(body) > 60_000) {
      cleanup();
      return Response.json({ error: "Yêu cầu quá dài." }, { status: 413 });
    }
    const response = await fetch(`${backend}${endpoint}`, {
      method,
      body,
      cache: "no-store",
      signal: abort.signal,
      headers:
        method === "POST" ? { "Content-Type": "application/json" } : undefined,
    });
    if (!response.body) {
      cleanup();
      return new Response(null, { status: response.status });
    }
    const reader = response.body.getReader();
    const stream = new ReadableStream<Uint8Array>({
      async pull(controller) {
        try {
          const { value, done } = await reader.read();
          if (done) {
            cleanup();
            controller.close();
          } else controller.enqueue(value);
        } catch (error) {
          cleanup();
          controller.error(error);
        }
      },
      async cancel() {
        abort.abort();
        cleanup();
        await reader.cancel().catch(() => {});
      },
    });
    return new Response(stream, {
      status: response.status,
      headers: {
        "Content-Type":
          response.headers.get("content-type") ?? "application/json",
        "Cache-Control": "no-store, no-transform",
        "X-Content-Type-Options": "nosniff",
        "X-Accel-Buffering": "no",
      },
    });
  } catch {
    cleanup();
    return Response.json(
      { error: "Chưa kết nối được agent. Khởi động backend rồi thử lại." },
      { status: 503 },
    );
  }
}
