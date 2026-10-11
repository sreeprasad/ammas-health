import type { Series, Status } from "./types";

export const AREAS = [
  { id: "thyroid", short: "Thyroid", name: "Thyroid", test: "tsh", x: 240, y: 70 },
  { id: "heart", short: "Cholesterol", name: "Cholesterol", test: "ldl", x: 20, y: 140 },
  { id: "sugar", short: "Blood sugar", name: "Blood sugar", test: "hba1c", x: 8, y: 212 },
  { id: "kidneys", short: "Kidneys", name: "Kidneys", test: "creat", x: 280, y: 290 },
  { id: "blood", short: "Blood count", name: "Blood count", test: "hgb", x: 280, y: 180 },
  { id: "vitd", short: "Vitamin D", name: "Bones & Vitamin D", test: "vitd", x: 14, y: 392 },
] as const;

export const GRID_TESTS = ["hba1c", "hgb", "ldl", "vitd", "creat", "tsh"];

export const STATUS_LABEL: Record<Status, string> = {
  rising: "Rising — discuss",
  below: "Low — discuss",
  improving: "Improving",
  steady: "Steady",
};

export type Note = { day: string; label: string; department: string; text: string };

export type StoryContext = {
  notes: Note[];
  pendingLabel: string | null;
  newFindings: { name: string; valueText: string; unit: string; range: string; above: boolean }[];
};

const WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"];

export function fmt(value: number, decimals: number): string {
  return value.toFixed(decimals);
}

export function withUnit(text: string, unit: string): string {
  return unit === "%" ? `${text}%` : `${text} ${unit}`;
}

function known(series: Series) {
  return series.points.filter((p) => p.value !== null) as { day: string; value: number; text: string }[];
}

function outside(series: Series, v: number): number {
  if (v < series.lo) return series.lo - v;
  if (series.hi !== null && v > series.hi) return v - series.hi;
  return 0;
}

function monotonic(values: number[], dir: 1 | -1): boolean {
  return values.length >= 2 && values.every((v, i) => i === 0 || (v - values[i - 1]) * dir > 0);
}

export function statusOf(series: Series): Status {
  const values = known(series).map((p) => p.value);
  if (values.length === 0) return "steady";
  const last = values[values.length - 1];
  if (last < series.lo) return "below";
  if (series.hi !== null && last > series.hi && monotonic(values, 1)) return "rising";
  const gaps = values.map((v) => outside(series, v));
  if (gaps[0] > 0 && gaps.every((g, i) => i === 0 || g <= gaps[i - 1]) && gaps[gaps.length - 1] < gaps[0]) {
    return "improving";
  }
  return "steady";
}

function noteMentioning(ctx: StoryContext, word: string): Note | undefined {
  return ctx.notes.find((n) => n.text.toLowerCase().includes(word.toLowerCase()));
}

export function storyFor(areaId: string, series: Series, ctx: StoryContext): string {
  const points = known(series);
  if (points.length === 0) return `No ${series.name} values on file yet.`;
  const first = points[0];
  const last = points[points.length - 1];
  const d = series.decimals;
  const firstText = fmt(first.value, d);
  const lastText = fmt(last.value, d);
  const pending = series.points.some((p) => p.pending);

  switch (areaId) {
    case "thyroid":
      return `${series.name} has stayed comfortably inside the normal range in all ${WORDS[points.length] ?? points.length} reports.`;
    case "heart": {
      if (pending) {
        return `LDL fell in every report from ${monthOf(first.day)} to ${monthOf(last.day)}. The ${ctx.pendingLabel} value is waiting for your check before it is added.`;
      }
      const limit = series.hi !== null && last.value > series.hi
        ? `now just above the ${fmt(series.hi, d)} limit printed on her reports`
        : "now inside the range printed on her reports";
      return `LDL has come down in every report, from ${firstText} to ${withUnit(lastText, series.unit)}, ${limit}.`;
    }
    case "sugar": {
      let text = `${series.name} has gone up in every report since ${monthName(first.day)}, from ${withUnit(firstText, series.unit)} to ${withUnit(lastText, series.unit)}.`;
      const recheck = noteMentioning(ctx, "recheck hba1c");
      if (recheck) text += ` On ${recheck.label} the doctor asked for a recheck in two months.`;
      const glucose = ctx.newFindings.find((f) => f.name.toLowerCase().includes("glucose") && f.above);
      if (glucose) text += ` Her first fasting glucose, ${withUnit(glucose.valueText, glucose.unit)}, is also above range.`;
      return text;
    }
    case "kidneys": {
      const values = points.map((p) => p.value);
      return `${series.name} has stayed between ${fmt(Math.min(...values), d)} and ${withUnit(fmt(Math.max(...values), d), series.unit)}, inside the normal range every time.`;
    }
    case "blood": {
      const below = points.filter((p) => p.value < series.lo).length;
      let text = `${series.name} has been under the normal range on ${WORDS[below] ?? below} reports and keeps drifting lower, from ${firstText} to ${withUnit(lastText, series.unit)}.`;
      const tired = noteMentioning(ctx, "tiredness");
      if (tired) text += ` The doctor noted mild tiredness on ${tired.label}.`;
      return text;
    }
    case "vitd": {
      const inRange = outside(series, last.value) === 0;
      return `${series.name} has climbed from ${firstText} to ${withUnit(lastText, series.unit)} since supplements started in ${monthName(first.day)}${inRange ? ", and is now inside the normal range" : ""}.`;
    }
    default:
      return `${series.name} went from ${firstText} to ${withUnit(lastText, series.unit)}.`;
  }
}

export function questionsFor(areaId: string, series: Series): string[] {
  const points = known(series);
  if (points.length === 0) return [];
  const d = series.decimals;
  const first = fmt(points[0].value, d);
  const last = fmt(points[points.length - 1].value, d);
  switch (areaId) {
    case "thyroid":
      return ["Is yearly thyroid testing enough now that it has been steady?"];
    case "heart":
      return [`LDL is close to ${series.hi !== null ? fmt(series.hi, d) : "the limit"}. Is that close enough, or should anything change?`];
    case "sugar":
      return [`HbA1c went from ${withUnit(first, series.unit)} to ${withUnit(last, series.unit)} this year. Does her plan need to change?`, "How often should we test from here?"];
    case "kidneys":
      return ["Should kidney tests stay on the same schedule?"];
    case "blood": {
      const below = points.filter((p) => p.value < series.lo).length;
      return [`Hemoglobin has been low ${WORDS[below] ?? below} times. Should we look for the cause?`, "Could this be linked to the tiredness noted in July?"];
    }
    case "vitd":
      return [`Vitamin D is now ${last}. Should she continue the same dose?`];
    default:
      return [];
  }
}

export function belowStreak(series: Series): number {
  let streak = 0;
  for (const p of [...known(series)].reverse()) {
    if (p.value < series.lo) streak += 1;
    else break;
  }
  return streak;
}

export function ordinal(n: number): string {
  const suffix = n % 10 === 1 && n % 100 !== 11 ? "st" : n % 10 === 2 && n % 100 !== 12 ? "nd" : n % 10 === 3 && n % 100 !== 13 ? "rd" : "th";
  return `${n}${suffix}`;
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

export function dayLabel(day: string): string {
  const [, m, d] = day.split("-").map(Number);
  return `${MONTHS[m - 1]} ${d}`;
}

function monthOf(day: string): string {
  return MONTHS[Number(day.split("-")[1]) - 1];
}

function monthName(day: string): string {
  return MONTH_NAMES[Number(day.split("-")[1]) - 1];
}
