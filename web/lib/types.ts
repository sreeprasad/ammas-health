export type Status = "rising" | "below" | "improving" | "steady";

export type Visit = { day: string; label: string; caption: string; isNew: boolean };

export type Point = { day: string; value: number | null; text: string | null; pending: boolean };

export type Series = {
  test: string;
  name: string;
  unit: string;
  lo: number;
  hi: number | null;
  decimals: number;
  points: Point[];
};

export type Source = { label: string; href: string | null };

export type Area = {
  id: string;
  short: string;
  name: string;
  x: number;
  y: number;
  status: Status;
  story: string;
  questions: string[];
  sources: Source[];
  series: Series;
};

export type Review = {
  valueId: string;
  name: string;
  printed: string;
  valueText: string;
  unit: string;
  range: string;
  flag: string;
  needsCheck: boolean;
  note: string;
  candidates: number[];
  page: number;
  fileId: string | null;
  box: number[] | null;
};

export type PendingReport = {
  runId: string;
  dayLabel: string;
  isoDay: string;
  total: number;
  waiting: number;
  review: Review[];
};

export type RunState = { label: string; status: "none" | "running" | "paused" | "complete" | "failed"; text: string };

export type WatchItem = { tag: "RISING" | "LOW" | "NEW" | "GOOD"; text: string };

export type Family = {
  clinic: string;
  viewer: string;
  subtitle: string;
  nextVisit: { department: string; label: string } | null;
  run: RunState;
  visits: Visit[];
  areas: Area[];
  grid: Series[];
  pending: PendingReport | null;
  saved: { dayLabel: string; verified: number; learned: { version: string; regressions: number } | null } | null;
  watch: WatchItem[];
  questions: string[];
  prepDraftedAt: string | null;
  updatedAt: string;
};
