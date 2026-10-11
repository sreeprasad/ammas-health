import { GridFSBucket } from "mongodb";
import { Readable } from "node:stream";
import { pipeline } from "node:stream/promises";
import { authorize } from "@/lib/access";

const ALLOWED = new Set(["image/jpeg", "image/png", "image/webp", "application/pdf"]);

export async function POST(request: Request) {
  const form = await request.formData().catch(() => null);
  if (!form) return Response.json({ error: "send the pages as multipart form data" }, { status: 400 });
  const files = form.getAll("files").filter((f): f is File => f instanceof File);
  const memberId = String(form.get("member_id") ?? "");
  const reportKey = form.get("report_key") ? String(form.get("report_key")) : null;

  if (files.length === 0) return Response.json({ error: "attach at least one page as 'files'" }, { status: 400 });
  const rejected = files.find((f) => !ALLOWED.has(f.type));
  if (rejected) return Response.json({ error: `unsupported file type ${rejected.type}` }, { status: 415 });

  const access = await authorize(request, "write", "upload a report", memberId || null);
  if (access instanceof Response) return access;
  const { db, member } = access;
  const bucket = new GridFSBucket(db, { bucketName: "originals" });
  const now = new Date();

  const pages = [];
  for (const [index, file] of files.entries()) {
    const upload = bucket.openUploadStream(file.name, {
      metadata: { report_key: reportKey, page: index + 1, contentType: file.type, uploaded_by: member.member_id },
    });
    await pipeline(Readable.fromWeb(file.stream() as never), upload);
    pages.push({ page: index + 1, file_id: upload.id, content_type: file.type });
  }

  const { insertedId } = await db.collection("reports").insertOne({
    report_key: reportKey,
    status: "uploaded",
    source: "upload",
    pages,
    uploaded_by: member.member_id,
    uploaded_at: now,
  });
  await db.collection("audit_log").insertOne({
    at: now,
    event: "UPLOADED",
    actor: member.member_id,
    what: `${pages.length} page report uploaded`,
    report_id: insertedId,
  });

  return Response.json({ report_id: insertedId.toHexString(), pages: pages.length }, { status: 201 });
}
