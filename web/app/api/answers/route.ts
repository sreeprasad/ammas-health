import { ObjectId } from "mongodb";
import { getDb } from "@/lib/mongo";

export async function POST(request: Request) {
  const body = await request.json().catch(() => null);
  const { run_id, value_id, value, member_id } = body ?? {};

  if (!ObjectId.isValid(run_id) || !ObjectId.isValid(value_id)) {
    return Response.json({ error: "run_id and value_id must be ObjectIds" }, { status: 400 });
  }
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return Response.json({ error: "value must be a number" }, { status: 400 });
  }
  if (typeof member_id !== "string" || !member_id) {
    return Response.json({ error: "member_id is required" }, { status: 400 });
  }

  const db = await getDb();
  const pending = await db
    .collection("values")
    .findOne({ _id: new ObjectId(value_id), run_id: new ObjectId(run_id), status: "needs_person" });
  if (!pending) return Response.json({ error: "no value waiting for an answer" }, { status: 409 });

  const now = new Date();
  const { insertedId } = await db.collection("answers").insertOne({
    run_id: new ObjectId(run_id),
    value_id: new ObjectId(value_id),
    value,
    member_id,
    at: now,
    applied: false,
  });
  await db.collection("audit_log").insertOne({
    at: now,
    event: "ANSWERED",
    actor: member_id,
    what: `${pending.printed_name} confirmed as ${value}`,
    run_id: new ObjectId(run_id),
  });

  return Response.json({ answer_id: insertedId.toHexString() }, { status: 201 });
}
