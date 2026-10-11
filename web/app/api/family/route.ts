import { connection } from "next/server";
import { getFamily } from "@/lib/family";
import { getDb } from "@/lib/mongo";

export async function GET() {
  await connection();
  return Response.json(await getFamily(await getDb()));
}
