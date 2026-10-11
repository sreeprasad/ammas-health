import { connection } from "next/server";
import { authorize } from "@/lib/access";
import { getFamily } from "@/lib/family";

export async function GET(request: Request) {
  await connection();
  const access = await authorize(request, "labs", "see lab values");
  if (access instanceof Response) return access;
  return Response.json(await getFamily(access.db, access.member.member_id));
}
