"use client";

import { useState } from "react";
import type { PendingReport, Review } from "@/lib/types";

function PaperView({ row, isoDay, viewer }: { row: Review; isoDay: string; viewer: string }) {
  const [y, m, d] = isoDay.split("-");
  return (
    <div
      className="mono"
      style={{
        flex: "1 1 340px",
        minWidth: 0,
        background: "#FFFFFF",
        border: "1px solid #DCE2DA",
        borderRadius: 6,
        padding: 18,
        boxShadow: "0 16px 36px -24px rgba(19,32,26,0.4)",
        transform: "rotate(-0.5deg)",
        fontSize: 13,
        display: "flex",
        flexDirection: "column",
        gap: 8,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", gap: 8, borderBottom: "2px solid #13201A", paddingBottom: 8 }}>
        <span style={{ fontWeight: 600 }}>ORIGINAL PHOTO</span>
        <span className="muted">
          {d}-{m}-{y} · p.{row.page}
        </span>
      </div>
      {row.fileId ? (
        <div style={{ position: "relative", lineHeight: 0 }}>
          {/* eslint-disable-next-line @next/next/no-img-element -- a GridFS original, served as-is */}
          <img src={`/api/originals/${row.fileId}?as=${encodeURIComponent(viewer)}`} alt={`Page ${row.page} of the uploaded report`} style={{ width: "100%", height: "auto", borderRadius: 4 }} />
          {row.box && (
            <span
              aria-hidden="true"
              style={{
                position: "absolute",
                left: `${row.box[0] * 100 - 1.5}%`,
                top: `${row.box[1] * 100 - 0.6}%`,
                width: `${(row.box[2] - row.box[0]) * 100 + 3}%`,
                height: `${(row.box[3] - row.box[1]) * 100 + 1.2}%`,
                border: `3px solid ${row.needsCheck ? "#B45309" : "#0B6E5F"}`,
                background: "rgba(255, 243, 184, 0.35)",
                borderRadius: 4,
              }}
            />
          )}
        </div>
      ) : (
        <span className="muted">Original not available.</span>
      )}
      <span className="muted" style={{ fontSize: 12 }}>
        {row.printed} · printed range {row.range}
      </span>
    </div>
  );
}

export default function NewReportBanner({
  pending,
  viewer,
  onAnswer,
}: {
  pending: PendingReport;
  viewer: string;
  onAnswer: (valueId: string, value: number) => Promise<void>;
}) {
  const firstWaiting = pending.review.find((r) => r.needsCheck) ?? pending.review[0];
  const [selected, setSelected] = useState(firstWaiting?.valueId);
  const [sending, setSending] = useState<number | null>(null);
  const [other, setOther] = useState("");
  const row = pending.review.find((r) => r.valueId === selected) ?? firstWaiting;

  const answer = async (valueId: string, value: number) => {
    setSending(value);
    try {
      await onAnswer(valueId, value);
    } catch {
      setSending(null);
    }
  };

  return (
    <section aria-labelledby="newrep" style={{ background: "#FFFFFF", border: "2px solid #B45309", borderRadius: 20, padding: 24, display: "flex", flexDirection: "column", gap: 18 }}>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 12, justifyContent: "space-between", alignItems: "flex-start" }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          <span className="mono" style={{ fontSize: 12, fontWeight: 600, letterSpacing: "0.06em", textTransform: "uppercase", color: "#8A3B07" }}>
            New report · {pending.dayLabel} · phone photo
          </span>
          <h2 id="newrep" style={{ margin: 0, fontSize: 24, fontWeight: 800 }}>
            {pending.total} values read. {pending.waiting} needs you before it&apos;s saved.
          </h2>
        </div>
        <div className="mono" style={{ display: "flex", flexWrap: "wrap", gap: 6, fontSize: 12, fontWeight: 600 }}>
          <span style={{ borderRadius: 6, padding: "4px 10px", background: "#E3F1EC", color: "#084F45" }}>✓ Uploaded</span>
          <span style={{ borderRadius: 6, padding: "4px 10px", background: "#E3F1EC", color: "#084F45" }}>✓ Read</span>
          <span style={{ borderRadius: 6, padding: "4px 10px", background: "#FDF0E1", color: "#8A3B07", border: "1px solid #F2C894" }}>Check · {pending.waiting} left</span>
          <span style={{ borderRadius: 6, padding: "4px 10px", background: "#ECEFEB", color: "#4A5951" }}>Remember</span>
        </div>
      </div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 20, alignItems: "flex-start" }}>
        {row && <PaperView row={row} isoDay={pending.isoDay} viewer={viewer} />}
        <div style={{ flex: "1 1 400px", minWidth: 0, display: "flex", flexDirection: "column", gap: 8 }}>
          {pending.review.map((r) => {
            const on = r.valueId === row?.valueId;
            return (
              <div
                key={r.valueId}
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: 6,
                  padding: "8px 14px",
                  borderRadius: 12,
                  background: "#FFFFFF",
                  border: r.needsCheck ? "2px solid #B45309" : on ? "2px solid #0B6E5F" : "1px solid #DCE2DA",
                }}
              >
                <button
                  type="button"
                  aria-pressed={on}
                  onClick={() => setSelected(r.valueId)}
                  style={{ width: "100%", minHeight: 44, display: "flex", alignItems: "center", gap: 12, padding: 0, border: "none", background: "transparent", cursor: "pointer", textAlign: "left", color: "#13201A", fontSize: 15 }}
                >
                  <span style={{ flex: "1 1 auto", minWidth: 0, display: "flex", flexDirection: "column", lineHeight: 1.3 }}>
                    <span style={{ fontWeight: 600 }}>{r.name}</span>
                    <span className="muted" style={{ fontSize: 12 }}>
                      printed as &quot;{r.printed}&quot;
                    </span>
                  </span>
                  <span className="mono" style={{ fontWeight: 600, whiteSpace: "nowrap" }}>
                    {r.valueText} {r.unit}
                  </span>
                  <span className={`chip ${r.needsCheck ? "chip-wait" : "chip-ok"}`}>{r.needsCheck ? "Needs you" : "Verified"}</span>
                </button>
                {r.needsCheck && (
                  <>
                    <span className="muted" style={{ fontSize: 13 }}>
                      {r.note}
                    </span>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "center" }}>
                      {r.candidates.map((value, i) => (
                        <button
                          key={value}
                          type="button"
                          disabled={sending !== null}
                          onClick={() => answer(r.valueId, value)}
                          style={{
                            minHeight: 44,
                            padding: "0 16px",
                            borderRadius: 10,
                            border: i === 0 ? "1px solid #0B6E5F" : "1px solid #C7D0C5",
                            background: i === 0 ? "#0B6E5F" : "#FFFFFF",
                            color: i === 0 ? "#FFFFFF" : "#13201A",
                            fontSize: 14,
                            fontWeight: 600,
                            cursor: sending === null ? "pointer" : "wait",
                          }}
                        >
                          {sending === value ? `Saving ${value}…` : `It says ${value}`}
                        </button>
                      ))}
                      <form
                        onSubmit={(e) => {
                          e.preventDefault();
                          const value = Number(other);
                          if (other.trim() && Number.isFinite(value)) answer(r.valueId, value);
                        }}
                        style={{ display: "flex", gap: 6 }}
                      >
                        <input
                          aria-label={`What ${r.printed} reads on the paper`}
                          inputMode="decimal"
                          placeholder="Something else"
                          value={other}
                          onChange={(e) => setOther(e.target.value)}
                          disabled={sending !== null}
                          style={{ minHeight: 44, width: 150, padding: "0 12px", borderRadius: 10, border: "1px solid #C7D0C5", fontSize: 14 }}
                        />
                      </form>
                    </div>
                  </>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
