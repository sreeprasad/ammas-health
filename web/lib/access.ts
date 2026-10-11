import type { Db } from "mongodb";
import { getDb } from "./mongo";

export type Resource = "labs" | "medications" | "write";
export type Member = { member_id: string; name: string; relation: string; scope: "full" | "medications" };

const GRANTS: Record<Member["scope"], Resource[]> = {
  full: ["labs", "medications", "write"],
  medications: ["medications"],
};
const SCOPE_NAME: Record<Member["scope"], string> = { full: "family-full", medications: "medications-only" };
const OWNER = "sreeprasad";
const ALLOWED_LOG_EVERY_MS = 10 * 60 * 1000;

export function memberIdFrom(request: Request, fallback?: string | null): string | null {
  return request.headers.get("x-member-id") ?? new URL(request.url).searchParams.get("as") ?? fallback ?? null;
}

async function audit(db: Db, event: "DENIED" | "ALLOWED", member: Member | null, memberId: string | null, what: string) {
  await db.collection("audit_log").insertOne({
    at: new Date(),
    event,
    actor: member?.member_id ?? memberId ?? "unknown",
    policy: member ? `scope ${SCOPE_NAME[member.scope]}` : "scope unknown-member",
    what,
  });
}

/** Resolve the caller and check the resource against their scope. Denials and non-owner access are logged. */
export async function authorize(
  request: Request,
  resource: Resource,
  what: string,
  fallbackMemberId?: string | null,
): Promise<{ db: Db; member: Member } | Response> {
  const db = await getDb();
  const memberId = memberIdFrom(request, fallbackMemberId);
  const member = memberId ? await db.collection<Member>("members").findOne({ member_id: memberId }, { projection: { _id: 0 } }) : null;

  if (!member || !GRANTS[member.scope].includes(resource)) {
    const who = member?.name ?? memberId ?? "Someone";
    await audit(db, "DENIED", member, memberId, `${who} asked to ${what}`);
    return Response.json(
      { error: "not allowed", member: member?.member_id ?? null, scope: member ? SCOPE_NAME[member.scope] : null, resource },
      { status: member ? 403 : 401 },
    );
  }

  if (member.member_id !== OWNER && resource === "labs") {
    const recent = await db.collection("audit_log").findOne({
      event: "ALLOWED",
      actor: member.member_id,
      at: { $gt: new Date(Date.now() - ALLOWED_LOG_EVERY_MS) },
    });
    if (!recent) await audit(db, "ALLOWED", member, memberId, `${member.name} opened her lab values`);
  }
  return { db, member };
}
