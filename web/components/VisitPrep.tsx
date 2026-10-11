import type { Family, WatchItem } from "@/lib/types";

const TAG: Record<WatchItem["tag"], { label: string; bg: string }> = {
  RISING: { label: "↑ RISING", bg: "#F5B26B" },
  LOW: { label: "↓ LOW", bg: "#8AB4FF" },
  NEW: { label: "NEW", bg: "#F5B26B" },
  GOOD: { label: "GOOD", bg: "#9FD9C8" },
};

export default function VisitPrep({ family }: { family: Family }) {
  const visit = family.nextVisit;
  return (
    <section aria-labelledby="prep" style={{ background: "#13201A", color: "#F2F4F1", borderRadius: 20, padding: 28, display: "flex", flexDirection: "column", gap: 20 }}>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 12, alignItems: "flex-end", justifyContent: "space-between" }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          <span className="mono" style={{ fontSize: 12, fontWeight: 600, letterSpacing: "0.06em", textTransform: "uppercase", color: "#9FD9C8" }}>
            Ready for the visit
          </span>
          <h2 id="prep" style={{ margin: 0, fontSize: 28, fontWeight: 800, color: "#FFFFFF" }}>
            {visit ? `${visit.department} · ${visit.label}` : "Next visit"}
          </h2>
        </div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
          <button type="button" style={{ minHeight: 44, padding: "0 18px", borderRadius: 10, border: "1px solid #3C5247", background: "transparent", color: "#F2F4F1", fontSize: 15, fontWeight: 600, cursor: "pointer" }}>
            Send to sister
          </button>
          <button type="button" onClick={() => window.print()} style={{ minHeight: 44, padding: "0 18px", borderRadius: 10, border: "1px solid #9FD9C8", background: "#9FD9C8", color: "#13201A", fontSize: 15, fontWeight: 700, cursor: "pointer" }}>
            Print one page
          </button>
        </div>
      </div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 24 }}>
        <div style={{ flex: "1 1 340px", minWidth: 0, display: "flex", flexDirection: "column", gap: 12 }}>
          <h3 style={{ margin: 0, fontSize: 15, fontWeight: 600, color: "#9FD9C8" }}>Worth watching</h3>
          {family.watch.map((w) => (
            <div key={w.text} style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
              <span className="mono" style={{ flex: "0 0 auto", fontSize: 12, fontWeight: 600, borderRadius: 6, padding: "2px 8px", background: TAG[w.tag].bg, color: "#13201A" }}>
                {TAG[w.tag].label}
              </span>
              <span>{w.text}</span>
            </div>
          ))}
        </div>
        <div style={{ flex: "1 1 340px", minWidth: 0, display: "flex", flexDirection: "column", gap: 12 }}>
          <h3 style={{ margin: 0, fontSize: 15, fontWeight: 600, color: "#9FD9C8" }}>Questions to ask</h3>
          {family.questions.map((q, i) => (
            <label key={q} style={{ display: "flex", gap: 10, alignItems: "flex-start", cursor: "pointer" }}>
              <input type="checkbox" defaultChecked={i < 2} style={{ width: 20, height: 20, margin: "2px 0 0", accentColor: "#9FD9C8", flex: "0 0 auto" }} />
              {q}
            </label>
          ))}
        </div>
      </div>
      <p style={{ margin: 0, fontSize: 13, color: "#B7C4BC", borderTop: "1px solid #2C3D34", paddingTop: 14 }}>
        Every line links back to the report it came from. Patterns to discuss with her doctor, not a diagnosis.
      </p>
    </section>
  );
}
