import { authorize } from "@/lib/access";

export async function POST(request: Request) {
  const body = await request.json().catch(() => null);
  const question = typeof body?.question === "string" ? body.question.trim() : "";
  if (!question || question.length > 500) return Response.json({ error: "ask a question of up to 500 characters" }, { status: 400 });
  const access = await authorize(request, "labs", "ask about her lab values");
  if (access instanceof Response) return access;
  const { insertedId } = await access.db
    .collection("asks")
    .insertOne({ question, member_id: access.member.member_id, status: "pending", at: new Date() });
  return Response.json({ ask_id: insertedId.toHexString() }, { status: 202 });
}
