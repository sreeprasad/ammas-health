import type { Db, Document } from "mongodb";
import {
  AREAS,
  GRID_TESTS,
  belowStreak,
  dayLabel,
  fmt,
  ordinal,
  questionsFor,
  statusOf,
  storyFor,
  withUnit,
  type Note,
  type StoryContext,
} from "./areas";
import type { Area, Family, PendingReport, Point, Review, RunState, Series, Source, Visit, WatchItem } from "./types";

const CLINIC = "Amrut Clinic";
const LOOKALIKE: Record<string, string> = { "0": "8", "8": "0", "1": "7", "7": "1", "3": "8", "5": "6", "6": "5", "9": "4", "4": "9", "2": "7" };

const isoDay = (d: Date) => d.toISOString().slice(0, 10);

function decimalsOf(text: string | undefined): number {
  const part = (text ?? "").split(".")[1];
  return part ? part.length : 0;
}

function caption(note: Note | undefined, upload: boolean, titles: string[]): string {
  if (upload) return titles.length > 1 ? "Full panel" : titles[0] ?? "New report";
  const text = note?.text.toLowerCase() ?? "";
  if (text.includes("start vitamin d")) return "Supplements started";
  if (text.includes("recheck hba1c")) return '"Recheck HbA1c in 2 mo"';
  if (text.includes("tiredness")) return "Noted mild tiredness";
  return "Lab only";
}

function candidatesFor(valueText: string, previous: number | null): number[] {
  const at = valueText.indexOf("?");
  if (at < 0 || valueText.indexOf("?", at + 1) >= 0) return [];
  const options = Array.from({ length: 10 }, (_, digit) => Number(valueText.replace("?", String(digit))))
    .filter((v) => Number.isFinite(v));
  if (previous === null) return options.slice(0, 2);
  const best = [...options].sort((a, b) => Math.abs(a - previous) - Math.abs(b - previous) || a - b)[0];
  const digit = String(best).padStart(valueText.length, "0")[at];
  const alternative = Number(valueText.replace("?", LOOKALIKE[digit] ?? digit));
  return alternative === best ? [best] : [best, alternative];
}

function digitPosition(valueText: string): string {
  const at = valueText.indexOf("?");
  if (at === 0) return "first";
  if (at === valueText.length - 1) return "last";
  return "middle";
}

export async function getFamily(db: Db): Promise<Family> {
  const [reports, notesRaw] = await Promise.all([
    db.collection("reports").find({ report_date: { $exists: true } }, { projection: { pages: 1, report_date: 1, source: 1, title: 1, run_id: 1 } }).toArray(),
    db.collection("notes").find({}).toArray(),
  ]);
  const notes: Note[] = notesRaw.map((n) => ({ day: n.date, label: dayLabel(n.date), department: n.department, text: n.text }));

  const latestUpload = await db.collection("reports").find({ source: "upload" }).sort({ uploaded_at: -1 }).limit(1).next();
  const run = latestUpload ? await db.collection("runs").findOne({ report_id: latestUpload._id }) : null;
  const pageTitles: Record<string, string> = run?.outputs?.read?.page_titles ?? {};
  const uploadTitles: string[] = run?.outputs?.read?.titles ?? [];

  const days = [...new Set(reports.map((r) => isoDay(r.report_date)))].sort();
  const uploadDays = new Set(reports.filter((r) => r.source === "upload").map((r) => isoDay(r.report_date)));
  const visits: Visit[] = days.map((day) => ({
    day,
    label: dayLabel(day),
    caption: caption(notes.find((n) => n.day === day && n.department !== "Laboratory"), uploadDays.has(day), uploadTitles),
    isNew: uploadDays.has(day),
  }));

  const reportById = new Map(reports.map((r) => [String(r._id), r]));
  const tests = [...new Set([...AREAS.map((a) => a.test), ...GRID_TESTS])];
  const valueDocs = await db
    .collection("values")
    .find({ test: { $in: tests }, status: { $in: ["verified", "needs_person"] } })
    .sort({ report_date: 1 })
    .toArray();
  const names = new Map<string, string>();
  for (const doc of await db.collection("values").find({ test: { $in: tests }, standard_name: { $exists: true } }, { projection: { test: 1, standard_name: 1 } }).toArray()) {
    names.set(doc.test, doc.standard_name);
  }

  const sourceFor = (doc: Document): Source => {
    const report = reportById.get(String(doc.report_id));
    const page = report?.pages?.find((p: Document) => p.page === doc.page);
    const title = report?.source === "upload" ? pageTitles[String(doc.page)] ?? "Lab report" : report?.title ?? "Lab report";
    return {
      label: `${dayLabel(isoDay(doc.report_date))} · ${title} · p.${doc.page}`,
      href: page ? `/api/originals/${String(page.file_id)}` : null,
    };
  };

  const seriesFor = (test: string): { series: Series; docs: Document[] } => {
    const docs = valueDocs.filter((d) => d.test === test);
    const latestVerified = [...docs].reverse().find((d) => d.status === "verified");
    const points: Point[] = visits.map((v) => {
      const doc = docs.find((d) => isoDay(d.report_date) === v.day);
      if (!doc) return { day: v.day, value: null, text: null, pending: false };
      const pending = doc.status === "needs_person";
      return { day: v.day, value: pending ? null : doc.value, text: doc.value_text, pending };
    });
    return {
      docs,
      series: {
        test,
        name: names.get(test) ?? latestVerified?.printed_name ?? test,
        unit: latestVerified?.unit ?? "",
        lo: latestVerified?.range?.low ?? 0,
        hi: latestVerified?.range?.high ?? null,
        decimals: decimalsOf(latestVerified?.value_text),
        points,
      },
    };
  };

  const pendingDocs = latestUpload
    ? await db.collection("values").find({ report_id: latestUpload._id }).sort({ page: 1, _id: 1 }).toArray()
    : [];
  const pendingLabel = latestUpload?.report_date ? dayLabel(isoDay(latestUpload.report_date)) : null;
  const firstOnFile = async (d: Document) =>
    !d.test || !(await db.collection("values").findOne({ test: d.test, status: "verified", report_date: { $lt: d.report_date } }));
  const firsts = await Promise.all(pendingDocs.map((d) => (d.status === "verified" ? firstOnFile(d) : false)));
  const newFindings = pendingDocs
    .filter((_, i) => firsts[i])
    .map((d) => ({
      name: (d.standard_name as string | undefined)?.toLowerCase() ?? (d.printed_name as string),
      valueText: d.value_text as string,
      unit: d.unit as string,
      range: d.range?.text as string,
      above: d.range?.high != null && d.value > d.range.high,
    }));
  const ctx: StoryContext = { notes, pendingLabel, newFindings };

  const areas: Area[] = AREAS.map((def) => {
    const { series, docs } = seriesFor(def.test);
    const verified = docs.filter((d) => d.status === "verified");
    const sources: Source[] = [];
    if (verified.length) sources.push(sourceFor(verified[verified.length - 1]));
    if (verified.length > 1) sources.push(sourceFor(verified[0]));
    const noteWord = { sugar: "recheck hba1c", blood: "tiredness", vitd: "start vitamin d" }[def.id as string];
    const note = noteWord ? notes.find((n) => n.text.toLowerCase().includes(noteWord)) : undefined;
    if (note) sources.splice(1, 1, { label: `${note.label} · Doctor note · ${note.department}`, href: null });
    return {
      id: def.id,
      short: def.short,
      name: def.name,
      x: def.x,
      y: def.y,
      status: statusOf(series),
      story: storyFor(def.id, series, ctx),
      questions: questionsFor(def.id, series),
      sources,
      series,
    };
  });

  const grid = GRID_TESTS.map((t) => seriesFor(t).series);

  const waitingDocs = pendingDocs.filter((d) => d.status === "needs_person");
  let pending: PendingReport | null = null;
  if (latestUpload && run && waitingDocs.length > 0) {
    const reviewTests = new Set<string>(AREAS.map((a) => a.test));
    const shown = pendingDocs.filter((d) => d.status === "needs_person" || !d.test || reviewTests.has(d.test));
    const review: Review[] = shown.map((d) => {
      const needsCheck = d.status === "needs_person";
      const history = d.test ? valueDocs.filter((v) => v.test === d.test && v.status === "verified" && v.report_date < d.report_date) : [];
      const previous = history.length ? history[history.length - 1].value : null;
      const candidates = needsCheck ? candidatesFor(d.value_text, previous) : [];
      const direction = history.length > 1 && history[history.length - 1].value < history[0].value ? "downward" : "upward";
      const note = needsCheck && candidates.length > 1
        ? `The ${digitPosition(d.value_text)} digit can't be read. ${candidates[1]} would break her steady ${direction} trend, so it asks instead of guessing.`
        : needsCheck
          ? "Part of this value can't be read, so it asks instead of guessing."
          : (d.checks ?? []).join(" · ");
      const page = latestUpload.pages.find((p: Document) => p.page === d.page);
      return {
        valueId: String(d._id),
        name: (d.test && names.get(d.test)) || d.printed_name,
        printed: d.printed_name,
        valueText: d.value_text,
        unit: d.unit,
        range: d.range?.text ?? "",
        flag: d.flag ?? "",
        needsCheck,
        note,
        candidates,
        page: d.page,
        fileId: page ? String(page.file_id) : null,
        box: d.box ?? null,
      };
    });
    pending = {
      runId: String(run._id),
      dayLabel: pendingLabel ?? "New report",
      isoDay: latestUpload.report_date ? isoDay(latestUpload.report_date) : "",
      total: pendingDocs.length,
      waiting: waitingDocs.length,
      review,
    };
  }

  const learned = run ? await db.collection("rules").findOne({ trigger_run_id: run._id, status: "live" }) : null;
  const saved = latestUpload && run?.status === "complete" && waitingDocs.length === 0
    ? {
        dayLabel: pendingLabel ?? "New report",
        verified: pendingDocs.filter((d) => d.status === "verified").length,
        learned: learned ? { version: learned.version, regressions: (learned.regressions ?? []).length } : null,
      }
    : null;

  const watch: WatchItem[] = [];
  for (const area of areas) {
    const known = area.series.points.filter((p) => p.value !== null);
    const last = known[known.length - 1];
    if (!last || last.value === null) continue;
    const valueText = withUnit(fmt(last.value, area.series.decimals), area.series.unit);
    if (area.status === "rising") {
      const recheck = notes.find((n) => n.text.toLowerCase().includes(`recheck ${area.series.name.toLowerCase()}`));
      watch.push({ tag: "RISING", text: `${area.series.name} ${valueText}, up in all ${known.length} reports.${recheck ? ` The doctor asked for a recheck on ${recheck.label}.` : ""}` });
    } else if (area.status === "below") {
      watch.push({ tag: "LOW", text: `${area.series.name} ${valueText}, below range for the ${ordinal(belowStreak(area.series))} report in a row.` });
    } else if (area.status === "improving" && known.length > 1 && last.value >= area.series.lo && (area.series.hi === null || last.value <= area.series.hi)) {
      watch.push({ tag: "GOOD", text: `${area.series.name} ${valueText}, in range for the first time this year.` });
    }
  }
  for (const f of newFindings.filter((f) => f.above)) {
    watch.splice(2, 0, { tag: "NEW", text: `First ${f.name} on file: ${withUnit(f.valueText, f.unit)}, above the printed ${f.range}.` });
  }

  const questions = areas.filter((a) => a.status !== "steady").map((a) => a.questions[0]).filter(Boolean);

  const booked = notes.map((n) => ({ n, m: n.text.match(/review booked for ([A-Z][a-z]{2} \d{1,2})/) })).find((x) => x.m);
  const nextVisit = booked?.m ? { department: booked.n.department, label: booked.m[1] } : null;

  const totalReports = await db.collection("reports").countDocuments({ report_date: { $exists: true } });
  const year = days.length ? days[0].slice(0, 4) : "";
  const span = days.length ? `${dayLabel(days[0]).split(" ")[0]} – ${dayLabel(days[days.length - 1]).split(" ")[0]} ${year}` : "";
  const subtitle = [CLINIC, `${totalReports} reports across ${visits.length} visits`, span, nextVisit ? `next visit ${nextVisit.label}` : null]
    .filter(Boolean)
    .join(" · ");

  return {
    clinic: CLINIC,
    subtitle,
    nextVisit,
    run: runState(run, latestUpload, waitingDocs.length),
    visits,
    areas,
    grid,
    pending,
    saved,
    watch,
    questions,
    updatedAt: new Date().toISOString(),
  };
}

function runState(run: Document | null, report: Document | null, waiting: number): RunState {
  if (!run || !report) return { label: "No run yet", status: "none", text: "No run yet" };
  const day = report.report_date ? isoDay(report.report_date) : isoDay(report.uploaded_at);
  const label = `Run ${day.slice(5, 7)}${day.slice(8, 10)}-A`;
  if (waiting > 0) return { label, status: "paused", text: `${label} · paused, ${waiting} value${waiting > 1 ? "s" : ""} need${waiting > 1 ? "" : "s"} you` };
  if (run.status === "complete") return { label, status: "complete", text: `${label} · complete` };
  if (run.status === "failed") return { label, status: "failed", text: `${label} · failed at ${run.failed_step}` };
  if (run.status === "paused") return { label, status: "running", text: `${label} · saving your answer…` };
  return { label, status: "running", text: `${label} · ${run.current_step ?? "starting"}…` };
}

