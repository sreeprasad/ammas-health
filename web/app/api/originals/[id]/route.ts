import { GridFSBucket, ObjectId } from "mongodb";
import { Readable } from "node:stream";
import { connection } from "next/server";
import { getDb } from "@/lib/mongo";

export async function GET(_request: Request, ctx: RouteContext<"/api/originals/[id]">) {
  await connection();
  const { id } = await ctx.params;
  if (!ObjectId.isValid(id)) return Response.json({ error: "not a file id" }, { status: 400 });

  const db = await getDb();
  const file = await db.collection("originals.files").findOne({ _id: new ObjectId(id) });
  if (!file) return Response.json({ error: "no such original" }, { status: 404 });

  const stream = new GridFSBucket(db, { bucketName: "originals" }).openDownloadStream(file._id);
  return new Response(Readable.toWeb(stream) as ReadableStream, {
    headers: {
      "Content-Type": file.metadata?.contentType ?? "application/octet-stream",
      "Cache-Control": "private, max-age=3600, immutable",
    },
  });
}
