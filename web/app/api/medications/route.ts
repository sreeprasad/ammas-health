import { connection } from "next/server";
import { authorize } from "@/lib/access";

const MEDICATION_WORDS = /\b(start|stop|supplement|supplements|dose|tablet|tablets|medicine|medication)\b/i;

export async function GET(request: Request) {
  await connection();
  const access = await authorize(request, "medications", "see her medications");
  if (access instanceof Response) return access;
  const notes = await access.db.collection("notes").find({}, { projection: { _id: 0, date: 1, department: 1, text: 1 } }).sort({ date: 1 }).toArray();
  const lines = notes.flatMap((n) =>
    String(n.text)
      .split(/(?<=\.)\s+/)
      .filter((sentence) => MEDICATION_WORDS.test(sentence))
      .map((sentence) => ({ date: n.date, department: n.department, line: sentence })),
  );
  return Response.json({ member: access.member.member_id, lines });
}
