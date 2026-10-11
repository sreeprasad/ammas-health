import { connection } from "next/server";
import { getDb } from "@/lib/mongo";

export async function GET() {
  await connection();
  const db = await getDb();
  const members = await db.collection("members").find({}, { projection: { _id: 0, member_id: 1, name: 1, scope: 1 } }).sort({ member_id: -1 }).toArray();
  return Response.json(members);
}
