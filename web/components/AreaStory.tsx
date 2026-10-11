import { STATUS_LABEL } from "@/lib/areas";
import type { Area, Status, Visit } from "@/lib/types";
import { STATUS_COLOR } from "./BodyMap";
import TrendChart from "./TrendChart";

const BADGE: Record<Status, { bg: string; fg: string }> = {
  rising: { bg: "#FDF0E1", fg: "#8A3B07" },
  below: { bg: "#E8EEFB", fg: "#1E3F82" },
  improving: { bg: "#E3F1EC", fg: "#084F45" },
  steady: { bg: "#ECEFEB", fg: "#3E4A52" },
};

const eyebrow = {
  margin: 0,
  fontFamily: "var(--font-mono)",
  fontSize: 12,
  fontWeight: 600,
  letterSpacing: "0.06em",
  textTransform: "uppercase" as const,
  color: "#4A5951",
};

export default function AreaStory({ area, visits }: { area: Area; visits: Visit[] }) {
  const badge = BADGE[area.status];
  return (
    <article className="card" style={{ flex: "1.35 1 520px", minWidth: 0, padding: 26, display: "flex", flexDirection: "column", gap: 18 }}>
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        <span style={eyebrow}>
          {area.series.name} · {area.series.unit}
        </span>
        <div style={{ display: "flex", flexWrap: "wrap", alignItems: "baseline", gap: 12 }}>
          <h2 style={{ margin: 0, fontSize: 32, fontWeight: 800, letterSpacing: "-0.01em" }}>{area.name}</h2>
          <span style={{ fontSize: 13, fontWeight: 600, borderRadius: 999, padding: "3px 12px", background: badge.bg, color: badge.fg }}>
            {STATUS_LABEL[area.status]}
          </span>
        </div>
        <p style={{ margin: 0, fontSize: 16, color: "#2C3A33", maxWidth: "62ch" }}>{area.story}</p>
      </div>
      <TrendChart series={area.series} visits={visits} color={STATUS_COLOR[area.status]} />
      <div style={{ display: "flex", flexWrap: "wrap", gap: 16 }}>
        <div style={{ flex: "1 1 260px", minWidth: 0, display: "flex", flexDirection: "column", gap: 8 }}>
          <h3 style={eyebrow}>Ask the doctor</h3>
          {area.questions.map((q) => (
            <div key={q} style={{ background: "#F2F4F1", borderRadius: 12, padding: "10px 14px", fontSize: 15 }}>
              {q}
            </div>
          ))}
        </div>
        <div style={{ flex: "1 1 200px", minWidth: 0, display: "flex", flexDirection: "column", gap: 8 }}>
          <h3 style={eyebrow}>Where this comes from</h3>
          {area.sources.map((src) => {
            const icon = (
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#0B6E5F" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" style={{ flex: "0 0 auto" }}>
                <path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z" />
                <path d="M14 3v6h6" />
              </svg>
            );
            return src.href ? (
              <a key={src.label} className="source-link" href={src.href} target="_blank" rel="noreferrer">
                {icon}
                {src.label}
              </a>
            ) : (
              <span key={src.label} className="source-link">
                {icon}
                {src.label}
              </span>
            );
          })}
        </div>
      </div>
    </article>
  );
}
