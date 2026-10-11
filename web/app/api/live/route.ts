import { connection } from "next/server";
import { authorize } from "@/lib/access";

const WATCHED = ["values", "runs", "reports", "answers"];

export async function GET(request: Request) {
  await connection();
  const access = await authorize(request, "labs", "follow live lab updates");
  if (access instanceof Response) return access;
  const { db } = access;
  const changes = db.watch([{ $match: { "ns.coll": { $in: WATCHED } } }], { fullDocument: "default" });
  const encoder = new TextEncoder();

  const body = new ReadableStream({
    async start(controller) {
      const send = (event: string, data: unknown) =>
        controller.enqueue(encoder.encode(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`));
      const heartbeat = setInterval(() => controller.enqueue(encoder.encode(": keep-alive\n\n")), 15000);
      const close = () => {
        clearInterval(heartbeat);
        changes.close().catch(() => {});
        try {
          controller.close();
        } catch {}
      };
      request.signal.addEventListener("abort", close);
      send("ready", { at: new Date().toISOString() });
      try {
        for await (const change of changes) {
          const ns = "ns" in change ? change.ns : null;
          send("change", { collection: ns && "coll" in ns ? ns.coll : null, at: new Date().toISOString() });
        }
      } catch {
        close();
      }
    },
  });

  return new Response(body, {
    headers: { "Content-Type": "text/event-stream", "Cache-Control": "no-cache, no-transform", Connection: "keep-alive" },
  });
}
