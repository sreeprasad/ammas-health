import type { Db, Document } from "mongodb";
import { dayLabel } from "./areas";

export type StepCard = { num: number; name: string; state: "done" | "wait" | "todo"; did: string; meta: string };
export type ReadRow = { valueId: string; name: string; printed: string; valueText: string; unit: string; range: string; check: string; needsCheck: boolean };
export type MemoryCard = { kind: string; title: string; detail: string; held: boolean };
export type GateRow = { version: string; by: string; summary: string; correct: number | null; total: number | null; regressions: number | null; verdict: string; regressionNotes: string[] };
export type FollowRow = { said: string; quote: string; summary: string; status: string };
export type LogRow = { event: string; what: string; meta: string; test: boolean };

export type Hood = {
  runLabel: string;
  runId: string | null;
  page: { title: string; dateText: string; pageNo: number; pages: number; fileId: string | null } | null;
  session: { sessionId: string; executionId: string | null; status: string | null } | null;
  steps: StepCard[];
  rows: ReadRow[];
  memory: MemoryCard[];
  memoryTotals: Record<string, number>;
  gate: { status: string; rows: GateRow[]; running: boolean; reports: number };
  watcher: { nextRun: string | null; lastRun: string | null; checked: number; needAttention: number; rows: FollowRow[] };
  log: LogRow[];
};

const isoDay = (d: Date) => d.toISOString().slice(0, 10);
const secs = (ms?: number) => (ms === undefined ? "" : `${(ms / 1000).toFixed(1)} s`);
const time = (d: Date) => d.toLocaleString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit", hour12: false, timeZone: "America/Los_Angeles" });

export async function getHood(db: Db, viewer: string): Promise<Hood> {
  const report = await db.collection("reports").find({ source: "upload" }).sort({ uploaded_at: -1 }).limit(1).next();
  const run = report ? await db.collection("runs").findOne({ report_id: report._id }) : null;
  const values = report ? await db.collection("values").find({ report_id: report._id }).sort({ page: 1, _id: 1 }).toArray() : [];
  const waiting = values.filter((v) => v.status === "needs_person");
  const stepOf = (name: string) => (run?.steps ?? []).find((s: Document) => s.name === name);
  const label = report?.report_date ? `Run ${isoDay(report.report_date).slice(5, 7)}${isoDay(report.report_date).slice(8, 10)}-A` : "No run yet";

  const read = stepOf("read");
  const verify = stepOf("verify");
  const remember = stepOf("remember");
  const confirmedByPerson = values.filter((v) => v.source === "person").length;
  const writesThisRun = run ? await db.collection("memory_writes").countDocuments({ run_id: run._id }) : 0;
  const prep = run ? await db.collection("visit_prep").findOne({ run_id: run._id }, { sort: { at: -1 } }) : null;
  const askBlocks = await db.collection("audit_log").countDocuments({ event: "BLOCKED", test: { $ne: true } });
  const watcherState = await db.collection("watcher_state").findOne({ _id: "watcher" as unknown as Document["_id"] });

  const steps: StepCard[] = [
    {
      num: 1, name: "Reader", state: read ? "done" : run ? "wait" : "todo",
      did: read ? `${run?.outputs?.read?.values?.length ?? 0} values from ${report?.pages?.length ?? 0} photographed pages` : "Waiting for a report",
      meta: read ? `${secs(read.duration_ms)} · ${run?.outputs?.read?.gemini_calls ?? 0} Gemini calls, ${run?.outputs?.read?.cache_hits ?? 0} cached` : "",
    },
    {
      num: 2, name: "Verifier", state: !verify ? "todo" : waiting.length ? "wait" : "done",
      did: verify
        ? waiting.length
          ? `${verify.summary} · rule ${run?.outputs?.verify?.rule}`
          : `${values.length} of ${values.length} verified${confirmedByPerson ? ` · ${confirmedByPerson} confirmed by you` : ""}`
        : "Starts after the Reader",
      meta: verify ? (waiting.length ? "checkpointed · resumes on answer" : secs(verify.duration_ms)) : "",
    },
    {
      num: 3, name: "Memory writer", state: !remember ? "todo" : waiting.length ? "wait" : "done",
      did: remember ? `${writesThisRun} writes across memory types${waiting.length ? ` · ${waiting.length} held` : ""}` : "Writes verified values only",
      meta: remember ? `${secs(remember.duration_ms)} · policy no-uncertain-writes` : "",
    },
    {
      num: 4, name: "Watcher", state: watcherState ? "done" : "todo",
      did: watcherState ? `${watcherState.checked} follow-ups checked · ${watcherState.need_attention} need attention` : "Not run yet",
      meta: watcherState ? `weekly · next ${dayLabel(isoDay(watcherState.next_run))}` : "",
    },
    {
      num: 5, name: "Visit prep", state: prep ? "done" : "todo",
      did: prep ? `${(prep.questions ?? []).length} questions drafted · ${askBlocks} draft${askBlocks === 1 ? "" : "s"} blocked so far` : "Starts after memory is updated",
      meta: prep ? "policy summarize-never-treat on every line" : "queued",
    },
  ];

  const focus = waiting[0] ?? values.find((v) => v.source === "person") ?? values[0];
  const pageNo = focus?.page ?? 1;
  const pageDoc = report?.pages?.find((p: Document) => p.page === pageNo);
  const rows: ReadRow[] = values
    .filter((v) => v.page === pageNo)
    .map((v) => ({
      valueId: String(v._id),
      name: v.standard_name ?? v.printed_name,
      printed: v.printed_name,
      valueText: v.value_text,
      unit: v.unit,
      range: v.range?.text ?? "",
      check: (v.checks ?? []).join(" · "),
      needsCheck: v.status === "needs_person",
    }));

  const kinds: [string, string][] = [["semantic", "Facts · semantic"], ["episodic", "Visit · episodic"], ["taxonomic", "Terms · taxonomic"], ["procedural", "Reading rule · procedural"]];
  const memory: MemoryCard[] = [];
  for (const [kind, title] of kinds) {
    const latest = run ? await db.collection("memory_writes").find({ run_id: run._id, kind }).sort({ at: -1 }).toArray() : [];
    if (waiting.length && kind !== "semantic") {
      memory.push({ kind: title, title: "Held", detail: "Waits until every value in the report is verified.", held: true });
    } else if (latest.length) {
      memory.push({ kind: title, title: `${latest.length} written this run`, detail: String(latest[0].summary).slice(0, 140), held: false });
    } else {
      memory.push({ kind: title, title: waiting.length ? "Held" : "Nothing new this run", detail: waiting.length ? "No uncertain value is written." : "", held: waiting.length > 0 });
    }
  }
  const totals: Record<string, number> = {};
  for (const row of await db.collection("memory_writes").aggregate([{ $match: { scope: "local" } }, { $group: { _id: "$kind", n: { $sum: 1 } } }]).toArray()) {
    totals[row._id as string] = row.n as number;
  }

  const rules = await db.collection("rules").find({}).sort({ version: 1 }).toArray();
  const learnedBy = ["family answer", "agent"];
  const baseline = rules.find((r) => r.baseline)?.baseline;
  const gateRows: GateRow[] = rules.map((r) => {
    const isBaseline = baseline && r.version === baseline.version;
    const scores = isBaseline ? baseline : r.scores;
    const regressions = Array.isArray(r.regressions) ? r.regressions.length : null;
    return {
      version: r.version,
      by: r.proposed_by === "agent" ? "proposed by the agent" : r.proposed_by === "family answer" ? "from your answer" : r.status === "live" ? "live" : "earlier rule",
      summary: r.summary,
      correct: scores?.correct ?? null,
      total: scores?.total ?? null,
      regressions: isBaseline ? null : regressions,
      verdict: r.status === "live" ? (learnedBy.includes(r.proposed_by) ? "Promoted" : "Current") : r.status === "retired" ? "Retired" : r.status === "rejected" ? "Rejected" : r.status === "not promoted" ? "Not promoted" : r.status,
      regressionNotes: (r.regressions ?? []).map((g: Document) => `${g.printed_name} ${g.report_key?.slice(0, 10)}: truth ${g.truth}, would record ${g.final}`),
    };
  });
  const promoted = rules.find((r) => r.status === "live" && learnedBy.includes(r.proposed_by));
  const rejected = rules.filter((r) => r.status === "rejected").length;
  const job = run ? await db.collection("learning_jobs").findOne({ run_id: run._id }) : null;
  const running = job?.status === "started";
  const reportsTested = rules.find((r) => r.reports_tested)?.reports_tested ?? (await db.collection("reports").countDocuments({ source: "seed" }));
  const gateStatus = running
    ? `Testing candidates on her ${reportsTested} earlier reports…`
    : promoted
      ? `${promoted.version} promoted · ${(promoted.regressions ?? []).length} regressions${rejected ? ` · ${rejected} rejected` : ""}`
      : waiting.length
        ? "Waiting for your answer"
        : "No candidates yet";

  const follow = await db.collection("followups").find({}).sort({ said_on: 1 }).toArray();
  const watcher = {
    nextRun: watcherState ? dayLabel(isoDay(watcherState.next_run)) : null,
    lastRun: watcherState ? time(watcherState.last_run) : null,
    checked: watcherState?.checked ?? 0,
    needAttention: watcherState?.need_attention ?? 0,
    rows: follow.map((f) => ({ said: dayLabel(f.said_on), quote: f.quote, summary: f.summary ?? "", status: f.status })),
  };

  const events = await db
    .collection("audit_log")
    .find({ event: { $in: ["HELD", "RELEASED", "BLOCKED", "DENIED", "ALLOWED", "REJECTED", "PROMOTED"] } })
    .sort({ at: -1 })
    .limit(14)
    .toArray();
  const log: LogRow[] = events.map((e) => ({
    event: e.event,
    what: e.event === "BLOCKED" && e.rewritten ? `${e.what} → "${e.rewritten}"` : e.what,
    meta: [e.policy, e.actor, time(e.at)].filter(Boolean).join(" · "),
    test: Boolean(e.test),
  }));

  return {
    runLabel: label,
    runId: run ? String(run._id) : null,
    page: report
      ? {
          title: run?.outputs?.read?.page_titles?.[String(pageNo)] ?? "Lab report",
          dateText: report.report_date ? isoDay(report.report_date).split("-").reverse().join("-") : "",
          pageNo,
          pages: report.pages?.length ?? 0,
          fileId: pageDoc ? `${String(pageDoc.file_id)}?as=${encodeURIComponent(viewer)}` : null,
        }
      : null,
    session: run?.agent?.session_id ? { sessionId: run.agent.session_id, executionId: run.agent.execution_id ?? null, status: run.agent.status ?? null } : null,
    steps,
    rows,
    memory,
    memoryTotals: totals,
    gate: { status: gateStatus, rows: gateRows, running, reports: reportsTested },
    watcher,
    log,
  };
}
