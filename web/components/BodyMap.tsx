import type { Area, Status } from "@/lib/types";

export const STATUS_COLOR: Record<Status, string> = {
  rising: "#B45309",
  below: "#2B5CB8",
  improving: "#0B6E5F",
  steady: "#6B7780",
};

const MARKERS: Record<string, { cx: number; cy: number; line: [number, number, number, number] }> = {
  thyroid: { cx: 200, cy: 112, line: [200, 112, 252, 96] },
  heart: { cx: 186, cy: 180, line: [186, 180, 150, 168] },
  sugar: { cx: 190, cy: 246, line: [190, 246, 150, 244] },
  kidneys: { cx: 224, cy: 272, line: [224, 272, 296, 330] },
  blood: { cx: 270, cy: 236, line: [270, 236, 296, 214] },
  vitd: { cx: 178, cy: 440, line: [178, 440, 150, 440] },
};

export default function BodyMap({ areas, selected, onSelect }: { areas: Area[]; selected: string; onSelect: (id: string) => void }) {
  return (
    <div className="card" style={{ flex: "1 1 400px", minWidth: 0, padding: 20, display: "flex", flexDirection: "column", gap: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 8, flexWrap: "wrap" }}>
        <h2 className="h2">Her body, from her reports</h2>
        <span className="muted" style={{ fontSize: 13 }}>
          Tap an area
        </span>
      </div>
      <div style={{ overflowX: "auto" }}>
        <div style={{ position: "relative", width: 400, height: 520, margin: "0 auto" }}>
          <svg width="400" height="520" viewBox="0 0 420 560" role="img" aria-label="Outline of a body with six tracked areas" style={{ position: "absolute", left: 0, top: 0 }}>
            <circle cx="200" cy="60" r="32" fill="#E9EDE7" stroke="#C7D0C5" strokeWidth="2" />
            <rect x="188" y="90" width="24" height="22" rx="8" fill="#E9EDE7" stroke="#C7D0C5" strokeWidth="2" />
            <rect x="150" y="110" width="100" height="200" rx="40" fill="#E9EDE7" stroke="#C7D0C5" strokeWidth="2" />
            <rect x="118" y="122" width="26" height="180" rx="13" fill="#E9EDE7" stroke="#C7D0C5" strokeWidth="2" />
            <rect x="256" y="122" width="26" height="180" rx="13" fill="#E9EDE7" stroke="#C7D0C5" strokeWidth="2" />
            <rect x="158" y="300" width="38" height="230" rx="19" fill="#E9EDE7" stroke="#C7D0C5" strokeWidth="2" />
            <rect x="204" y="300" width="38" height="230" rx="19" fill="#E9EDE7" stroke="#C7D0C5" strokeWidth="2" />
            {areas.map((a) => {
              const m = MARKERS[a.id];
              if (!m) return null;
              const [x1, y1, x2, y2] = m.line;
              const loud = a.status === "rising" || a.status === "below";
              return (
                <g key={a.id}>
                  <line x1={x1} y1={y1} x2={x2} y2={y2} stroke="#AEB8AC" strokeWidth="1.5" />
                  <circle cx={m.cx} cy={m.cy} r={loud ? 9 : 7} fill={STATUS_COLOR[a.status]} stroke="#FFFFFF" strokeWidth="3" />
                </g>
              );
            })}
          </svg>
          {areas.map((a) => {
            const on = a.id === selected;
            return (
              <button
                key={a.id}
                type="button"
                aria-pressed={on}
                onClick={() => onSelect(a.id)}
                style={{
                  position: "absolute",
                  left: a.x,
                  top: a.y,
                  minHeight: 44,
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  padding: "0 16px",
                  borderRadius: 999,
                  fontSize: 14,
                  fontWeight: 600,
                  cursor: "pointer",
                  whiteSpace: "nowrap",
                  color: "#13201A",
                  background: on ? "#E3F1EC" : "#FFFFFF",
                  border: on ? "2px solid #0B6E5F" : "1px solid #C7D0C5",
                  boxShadow: "0 6px 16px -10px rgba(19,32,26,0.5)",
                }}
              >
                <span className="dot" style={{ background: STATUS_COLOR[a.status] }} />
                {a.short}
              </button>
            );
          })}
        </div>
      </div>
      <div className="legend">
        <span>
          <span className="dot" style={{ background: STATUS_COLOR.rising }} />
          Rising — discuss
        </span>
        <span>
          <span className="dot" style={{ background: STATUS_COLOR.below }} />
          Low — discuss
        </span>
        <span>
          <span className="dot" style={{ background: STATUS_COLOR.improving }} />
          Improving
        </span>
        <span>
          <span className="dot" style={{ background: STATUS_COLOR.steady }} />
          Steady
        </span>
      </div>
    </div>
  );
}
