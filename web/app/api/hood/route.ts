import { connection } from "next/server";
import { authorize } from "@/lib/access";
import { getHood } from "@/lib/hood";

export async function GET(request: Request) {
  await connection();
  const access = await authorize(request, "labs", "see how the harness worked");
  if (access instanceof Response) return access;
  return Response.json(await getHood(access.db, access.member.member_id));
}
