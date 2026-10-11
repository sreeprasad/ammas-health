import type { CSSProperties } from "react";
import { fmt } from "@/lib/areas";
import type { Point, Series, Visit } from "@/lib/types";

function rangeText(s: Series): string {
  if (s.hi === null) return `normal > ${fmt(s.lo, s.decimals)} ${s.unit}`;
  if (s.lo === 0) return `normal < ${fmt(s.hi, s.decimals)} ${s.unit}`;
  return `normal ${fmt(s.lo, s.decimals)}–${fmt(s.hi, s.decimals)} ${s.unit}`;
}

function cell(s: Series, p: Point): { text: string; style: CSSProperties } {
  if (p.pending) {
    return { text: "? check", style: { background: "#FDF0E1", color: "#8A3B07", border: "2px dashed #B45309" } };
  }
  if (p.value === null) return { text: "—", style: { background: "#F2F4F1", color: "#4A5951", border: "1px solid #DCE2DA" } };
  const where = p.value < s.lo ? "below" : s.hi !== null && p.value > s.hi ? "above" : "in";
  const bg = where === "below" ? "#2B5CB8" : where === "above" ? "#B45309" : "#FFFFFF";
  return {
    text: fmt(p.value, s.decimals) + (where === "below" ? " ↓" : where === "above" ? " ↑" : ""),
    style: { background: bg, color: where === "in" ? "#13201A" : "#FFFFFF", border: `1px solid ${where === "in" ? "#DCE2DA" : bg}` },
  };
}

export default function ReportGrid({ grid, visits }: { grid: Series[]; visits: Visit[] }) {
  const cols = { "--cols": visits.length } as CSSProperties;
  return (
    <section aria-labelledby="grid" className="card" style={{ padding: 24, display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 12, justifyContent: "space-between", alignItems: "flex-end" }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
          <h2 id="grid" className="h2">
            Every report, side by side
          </h2>
          <span className="muted" style={{ fontSize: 14 }}>
            One square per value. Colour shows where it sits against the range printed on her report.
          </span>
        </div>
        <div className="legend">
          <span>
            <span style={{ width: 16, height: 12, borderRadius: 3, background: "#2B5CB8", display: "inline-block" }} />
            Below ↓
          </span>
          <span>
            <span style={{ width: 16, height: 12, borderRadius: 3, background: "#FFFFFF", border: "1px solid #C7D0C5", display: "inline-block" }} />
            In range
          </span>
          <span>
            <span style={{ width: 16, height: 12, borderRadius: 3, background: "#B45309", display: "inline-block" }} />
            Above ↑
          </span>
        </div>
      </div>
      <div style={{ overflowX: "auto" }}>
        <div style={{ minWidth: 780, display: "flex", flexDirection: "column", gap: 8 }}>
          <div className="grid-row muted" style={{ ...cols, fontSize: 13 }}>
            <span />
            {visits.map((v) => (
              <span key={v.day} style={{ display: "flex", flexDirection: "column" }}>
                <strong style={{ color: "#13201A" }}>
                  {v.label}
                  {v.isNew ? " · new" : ""}
                </strong>
                {v.caption}
              </span>
            ))}
          </div>
          {grid.map((s) => (
            <div key={s.test} className="grid-row" style={cols} data-test={s.test}>
              <span style={{ display: "flex", flexDirection: "column", justifyContent: "center", lineHeight: 1.3 }}>
                <span style={{ fontWeight: 600 }}>{s.name}</span>
                <span className="muted" style={{ fontSize: 12 }}>
                  {rangeText(s)}
                </span>
              </span>
              {s.points.map((p) => {
                const c = cell(s, p);
                return (
                  <span key={p.day} className="cell" style={c.style} data-day={p.day}>
                    {c.text}
                  </span>
                );
              })}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
