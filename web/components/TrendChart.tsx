import { fmt } from "@/lib/areas";
import type { Series, Visit } from "@/lib/types";

const PT = 12;
const PB = 200;

export default function TrendChart({ series, visits, color }: { series: Series; visits: Visit[]; color: string }) {
  const values = series.points.map((p) => p.value);
  const known = values.filter((v): v is number => v !== null);
  if (known.length === 0) return null;

  const vmin = Math.min(...known);
  const vmax = Math.max(...known);
  let lo = vmin;
  let hi = vmax;
  if (series.lo > vmin * 0.7) lo = Math.min(lo, series.lo);
  if (series.hi !== null && series.hi < vmax * 1.35) hi = Math.max(hi, series.hi);
  const pad = (hi - lo) * 0.18 || 1;
  const y0 = lo - pad;
  const y1 = hi + pad;

  const step = visits.length > 1 ? 520 / (visits.length - 1) : 0;
  const X = (i: number) => 64 + i * step;
  const Y = (v: number) => PB - (PB - PT) * ((v - y0) / (y1 - y0));

  const pts = values.flatMap((v, i) => (v === null ? [] : [[X(i), Y(v)] as const]));
  const line = pts.map(([x, y], i) => `${i === 0 ? "M" : "L"}${x.toFixed(1)} ${y.toFixed(1)}`).join(" ");
  const lastI = values.length - 1;
  const pending = series.points[lastI]?.pending ?? false;
  const lastY = pending ? pts[pts.length - 1][1] : Y(values[lastI] ?? known[known.length - 1]);

  const bandTop = Math.max(PT, Math.min(PB, series.hi === null ? PT : Y(series.hi)));
  const bandBottom = Math.max(PT, Math.min(PB, Y(series.lo)));
  const ticks = [y1 - (y1 - y0) * 0.2, y0 + (y1 - y0) * 0.2];
  const tickText = (v: number) => fmt(v, series.decimals === 0 ? 0 : 1);
  const lastLabel = pending
    ? `${visits[lastI]?.label}: waiting for your check`
    : `${fmt(values[lastI] ?? known[known.length - 1], series.decimals)} ${series.unit}`;
  const labelColor = pending ? "#8A3B07" : color;
  const aria = `${series.name}, ${visits[0]?.label} to ${visits[lastI]?.label}: ${values
    .map((v, i) => (series.points[i].pending ? "pending" : v === null ? "no value" : fmt(v, series.decimals)))
    .join(", ")} ${series.unit}. Normal range ${fmt(series.lo, series.decimals)} to ${series.hi === null ? "no upper limit" : fmt(series.hi, series.decimals)}.`;

  return (
    <svg viewBox="0 0 600 230" width="100%" role="img" aria-label={aria} style={{ display: "block" }}>
      <rect x="44" y={bandTop.toFixed(1)} width="546" height={Math.max(0, bandBottom - bandTop).toFixed(1)} fill="#E3F1EC" />
      <text x="586" y={(bandBottom - bandTop >= 18 ? bandTop + 14 : bandTop - 4).toFixed(1)} textAnchor="end" fontSize="11" fill="#084F45" fontFamily="var(--font-mono)">
        normal range
      </text>
      {ticks.map((t) => (
        <g key={t}>
          <line x1="44" x2="590" y1={Y(t).toFixed(1)} y2={Y(t).toFixed(1)} stroke="#E4E9E2" />
          <text x="36" y={(Y(t) + 4).toFixed(1)} textAnchor="end" fontSize="11" fill="#4A5951" fontFamily="var(--font-mono)">
            {tickText(t)}
          </text>
        </g>
      ))}
      <path d={line} fill="none" stroke={color} strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
      {pts.map(([x, y]) => (
        <circle key={`${x}-${y}`} cx={x} cy={y} r="6" fill="#FFFFFF" stroke={color} strokeWidth="3" />
      ))}
      {pending && <circle cx={X(lastI)} cy={lastY} r="9" fill="#FDF0E1" stroke="#B45309" strokeWidth="2" strokeDasharray="4 3" />}
      <text x={(X(lastI) - 14).toFixed(1)} y={(lastY - 16).toFixed(1)} textAnchor="end" fontSize="14" fontWeight="600" fill={labelColor} fontFamily="var(--font-mono)">
        {lastLabel}
      </text>
      {visits.map((v, i) => (
        <text
          key={v.day}
          x={i === 0 ? 60 : i === lastI ? 586 : X(i)}
          y="224"
          textAnchor={i === 0 ? "start" : i === lastI ? "end" : "middle"}
          fontSize="12"
          fill="#4A5951"
        >
          {v.label}
        </text>
      ))}
    </svg>
  );
}
