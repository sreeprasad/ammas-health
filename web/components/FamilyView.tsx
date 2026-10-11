"use client";

import { useState } from "react";
import type { Family } from "@/lib/types";
import AreaStory from "./AreaStory";
import BodyMap from "./BodyMap";
import NewReportBanner from "./NewReportBanner";
import ReportGrid from "./ReportGrid";
import VisitPrep from "./VisitPrep";

export default function FamilyView({
  family,
  onAnswer,
  goHood,
}: {
  family: Family | null;
  onAnswer: (runId: string, valueId: string, value: number) => Promise<void>;
  goHood: () => void;
}) {
  const [selected, setSelected] = useState("sugar");
  const area = family?.areas.find((a) => a.id === selected) ?? family?.areas[0];

  return (
    <div className="screen">
      <header className="screen-header">
        <div>
          <span className="eyebrow">Sample data · summaries, not medical advice</span>
          <h1>Amma&apos;s health</h1>
          <p className="lede">{family?.subtitle ?? "Loading her reports…"}</p>
        </div>
        <div className="actions">
          <button type="button" className="btn">
            Share with family
          </button>
          <button type="button" className="btn btn-primary" style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M12 16V4" />
              <path d="M6 10l6-6 6 6" />
              <path d="M4 20h16" />
            </svg>
            Upload report
          </button>
        </div>
      </header>

      {family?.pending && (
        <NewReportBanner
          key={family.pending.runId}
          pending={family.pending}
          onAnswer={(valueId, value) => onAnswer(family.pending!.runId, valueId, value)}
        />
      )}

      {family?.saved && (
        <section className="fade-in" style={{ background: "#E3F1EC", border: "1px solid #A9D6C7", borderRadius: 16, padding: "14px 18px", display: "flex", flexWrap: "wrap", gap: 12, alignItems: "center", justifyContent: "space-between" }}>
          <span style={{ display: "flex", alignItems: "center", gap: 10, color: "#084F45" }}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M20 6L9 17l-5-5" />
            </svg>
            <span>
              <strong>{family.saved.dayLabel} report saved.</strong> {family.saved.verified} values verified.
              {family.saved.learned &&
                ` New reading rule learned and re-tested on her 22 earlier reports: ${family.saved.learned.regressions} broke.`}
            </span>
          </span>
          <button type="button" onClick={goHood} style={{ minHeight: 44, padding: "0 16px", borderRadius: 10, border: "1px solid #0B6E5F", background: "#0B6E5F", color: "#FFFFFF", fontSize: 14, fontWeight: 600, cursor: "pointer" }}>
            See how it learned
          </button>
        </section>
      )}

      {family && area && (
        <section style={{ display: "flex", flexWrap: "wrap", gap: 24, alignItems: "stretch" }}>
          <BodyMap areas={family.areas} selected={area.id} onSelect={setSelected} />
          <AreaStory area={area} visits={family.visits} />
        </section>
      )}

      {family && <ReportGrid grid={family.grid} visits={family.visits} />}
      {family && <VisitPrep family={family} />}

      <section className="card" style={{ borderRadius: 16, padding: "16px 20px", display: "flex", flexWrap: "wrap", gap: 12, alignItems: "center", justifyContent: "space-between" }}>
        <span style={{ display: "flex", flexDirection: "column" }}>
          <span style={{ fontWeight: 700 }}>How can you trust this?</span>
          <span className="muted" style={{ fontSize: 14 }}>
            See which agent did what, how it learned from your answer, and what it isn&apos;t allowed to do.
          </span>
        </span>
        <button type="button" onClick={goHood} style={{ minHeight: 44, padding: "0 18px", borderRadius: 10, border: "1px solid #13201A", background: "#13201A", color: "#FFFFFF", fontSize: 15, fontWeight: 600, cursor: "pointer" }}>
          Under the hood →
        </button>
      </section>
    </div>
  );
}
