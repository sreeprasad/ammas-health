import { authorize } from "@/lib/access";

export async function POST(request: Request) {
  const access = await authorize(request, "write", "run the watcher");
  if (access instanceof Response) return access;
  const { insertedId } = await access.db
    .collection("watcher_jobs")
    .insertOne({ requested_by: access.member.member_id, at: new Date() });
  return Response.json({ job_id: insertedId.toHexString() }, { status: 202 });
}
