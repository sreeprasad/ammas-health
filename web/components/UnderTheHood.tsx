"use client";

import { useState } from "react";
import type { Hood } from "@/lib/hood";

const TAG_BG: Record<string, string> = {
  HELD: "#F5B26B",
  RELEASED: "#9FD9C8",
  BLOCKED: "#F2A699",
  DENIED: "#F2A699",
  ALLOWED: "#9FD9C8",
  REJECTED: "#F2A699",
  PROMOTED: "#9FD9C8",
};
const STATE_STYLE = {
  done: { card: "background:#FFFFFF;border:1px solid #DCE2DA", num: { background: "#0B6E5F", color: "#FFFFFF" }, chip: "chip-ok", label: "Done" },
  wait: { card: "background:#FDF0E1;border:2px solid #B45309", num: { background: "#B45309", color: "#FFFFFF" }, chip: "chip-wait", label: "Needs you" },
  todo: { card: "background:#F2F4F1;border:1px dashed #C7D0C5", num: { background: "#E4E9E2", color: "#4A5951" }, chip: "chip-todo", label: "Queued" },
} as const;
const VERDICT_CHIP: Record<string, string> = { Promoted: "chip-ok", Current: "chip-todo", Rejected: "chip-bad", Retired: "chip-todo", "Not promoted": "chip-todo" };

const h2 = { margin: 0, fontSize: 20, fontWeight: 800 } as const;
const sub = { fontSize: 13, color: "#4A5951" } as const;

function css(style: string): React.CSSProperties {
  return Object.fromEntries(style.split(";").filter(Boolean).map((rule) => {
    const [k, v] = rule.split(":");
    return [k.trim().replace(/-([a-z])/g, (_, c) => c.toUpperCase()), v.trim()];
  }));
}

export default function UnderTheHood({
  hood,
  onReplay,
  onRunWatcher,
  goFamily,
}: {
  hood: Hood | null;
  onReplay: () => Promise<void>;
  onRunWatcher: () => Promise<void>;
  goFamily: () => void;
}) {
  const [busy, setBusy] = useState<string | null>(null);
  const act = async (name: string, fn: () => Promise<void>) => {
    setBusy(name);
    try {
      await fn();
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="screen">
      <header className="screen-header">
        <div>
          <span className="eyebrow">{hood?.runLabel ?? "Run"} · MongoDB Atlas Agent Engine · sample data</span>
          <h1>The harness behind Amma&apos;s health</h1>
          <p className="lede">
            The same Sep 12 report, seen from the inside: which agent did what, what it remembered, how it learned, and what it was not allowed to do.
          </p>
        </div>
        <button type="button" className="btn" disabled={busy !== null} onClick={() => act("replay", onReplay)}>
          {busy === "replay" ? "Replaying…" : "Replay run"}
        </button>
      </header>

      {!hood ? (
        <section className="empty">Loading the harness…</section>
      ) : (
        <>
          <section aria-labelledby="pipe" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8, justifyContent: "space-between", alignItems: "baseline" }}>
              <h2 id="pipe" style={h2}>1 · Agent pipeline</h2>
              <span style={sub}>
                Started by a change stream when the photo was uploaded · every step checkpointed
                {hood.session && (
                  <>
                    {" "}· Agent Engine session <span className="mono">{hood.session.sessionId}</span> ({hood.session.status})
                  </>
                )}
              </span>
            </div>
            <ol style={{ listStyle: "none", margin: 0, padding: 0, display: "flex", flexWrap: "wrap", gap: 10 }}>
              {hood.steps.map((s) => {
                const st = STATE_STYLE[s.state];
                return (
                  <li key={s.num} data-step={s.name} data-state={s.state} style={{ flex: "1 1 220px", minWidth: 0, display: "flex", flexDirection: "column", gap: 6, padding: 14, borderRadius: 14, ...css(st.card) }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}>
                      <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <span className="mono" style={{ width: 24, height: 24, borderRadius: 999, display: "inline-flex", alignItems: "center", justifyContent: "center", fontSize: 12, fontWeight: 600, ...st.num }}>{s.num}</span>
                        <span style={{ fontWeight: 700 }}>{s.name}</span>
                      </span>
                      <span className={`chip ${st.chip}`}>{st.label}</span>
                    </div>
                    <span style={{ fontSize: 14 }}>{s.did}</span>
                    <span className="mono muted" style={{ fontSize: 12 }}>{s.meta}</span>
                  </li>
                );
              })}
            </ol>
          </section>

          <section style={{ display: "flex", flexWrap: "wrap", gap: 20, alignItems: "flex-start" }}>
            <div className="card" style={{ flex: "1 1 300px", minWidth: 0, padding: 20, display: "flex", flexDirection: "column", gap: 10 }}>
              <h2 style={{ ...h2, fontSize: 18 }}>2 · Reader sees</h2>
              {hood.page && (
                <div className="mono" style={{ display: "flex", justifyContent: "space-between", borderBottom: "2px solid #13201A", paddingBottom: 6, fontSize: 12 }}>
                  <span style={{ fontWeight: 600 }}>{hood.page.title.toUpperCase()}</span>
                  <span className="muted">{hood.page.dateText} · page {hood.page.pageNo} of {hood.page.pages}</span>
                </div>
              )}
              {hood.rows.map((r) => (
                <div key={r.valueId} className="mono" style={{ display: "grid", gridTemplateColumns: "minmax(0,1.4fr) minmax(0,0.8fr) minmax(0,0.8fr) minmax(0,0.9fr)", gap: 8, fontSize: 13, padding: "4px 6px", borderRadius: 4, background: r.needsCheck ? "#FFF3B8" : "transparent" }}>
                  <span>{r.printed}</span>
                  <span style={{ fontWeight: 600, filter: r.needsCheck ? "blur(0.6px)" : "none" }}>{r.valueText}</span>
                  <span>{r.unit}</span>
                  <span className="muted">{r.range}</span>
                </div>
              ))}
            </div>

            <div style={{ flex: "1 1 340px", minWidth: 0, display: "flex", flexDirection: "column", gap: 8 }}>
              <h2 style={{ ...h2, fontSize: 18 }}>3 · Verifier checks</h2>
              {hood.rows.map((r) => (
                <div key={r.valueId} style={{ display: "flex", flexDirection: "column", gap: 6, padding: "8px 12px", borderRadius: 12, background: "#FFFFFF", border: r.needsCheck ? "2px solid #B45309" : "1px solid #DCE2DA" }}>
                  <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                    <span style={{ flex: "1 1 auto", minWidth: 0, display: "flex", flexDirection: "column", lineHeight: 1.3 }}>
                      <span style={{ fontWeight: 600 }}>{r.name}</span>
                      <span className="muted" style={{ fontSize: 12 }}>&quot;{r.printed}&quot; · {r.check}</span>
                    </span>
                    <span className="mono" style={{ fontWeight: 600 }}>{r.valueText}</span>
                    <span className={`chip ${r.needsCheck ? "chip-wait" : "chip-ok"}`}>{r.needsCheck ? "Needs you" : "Verified"}</span>
                  </div>
                  {r.needsCheck && (
                    <span style={{ fontSize: 13, color: "#8A3B07" }}>
                      The run is paused durably. It resumes when a family member answers on the Family view.
                    </span>
                  )}
                </div>
              ))}
            </div>

            <div style={{ flex: "1 1 260px", minWidth: 0, display: "flex", flexDirection: "column", gap: 8 }}>
              <h2 style={{ ...h2, fontSize: 18 }}>4 · Memory writes</h2>
              {hood.memory.map((m) => (
                <div key={m.kind} style={{ display: "flex", flexDirection: "column", gap: 2, padding: "12px 14px", borderRadius: 14, background: m.held ? "#FDF0E1" : "#FFFFFF", border: m.held ? "1px dashed #F2C894" : "1px solid #DCE2DA" }}>
                  <span className="mono muted" style={{ fontSize: 11, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em" }}>{m.kind}</span>
                  <span style={{ fontWeight: 700 }}>{m.title}</span>
                  {m.detail && <span className="muted" style={{ fontSize: 13 }}>{m.detail}</span>}
                </div>
              ))}
              <span className="mono muted" style={{ fontSize: 12 }}>
                In her memory: {Object.entries(hood.memoryTotals).map(([k, n]) => `${n} ${k}`).join(" · ")}
              </span>
            </div>
          </section>

          <section aria-labelledby="gate" className="card" style={{ padding: 24, display: "flex", flexDirection: "column", gap: 14 }}>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 12, justifyContent: "space-between", alignItems: "flex-start" }}>
              <div style={{ display: "flex", flexDirection: "column", gap: 4, maxWidth: "70ch" }}>
                <h2 id="gate" style={h2}>5 · Learning check</h2>
                <span style={sub}>
                  A new reading rule goes live only if it reads her {hood.gate.reports} earlier reports at least as well, with zero values that used to be right turning wrong. Correct answers are stored apart and the agents can&apos;t see them.
                </span>
              </div>
              <span className={`chip ${hood.gate.running ? "chip-wait" : "chip-ok"}`} style={{ fontSize: 13, padding: "4px 12px" }} data-gate-status>
                {hood.gate.status}
              </span>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <div className="mono muted" style={{ display: "grid", gridTemplateColumns: "minmax(0,2.6fr) minmax(0,1fr) minmax(0,1.4fr) minmax(0,1fr)", gap: 12, fontSize: 12, padding: "0 14px" }}>
                <span>Rule version</span><span>Read correctly</span><span>Regressions</span><span>Gate</span>
              </div>
              {hood.gate.rows.map((g) => (
                <div key={g.version} data-rule={g.version} style={{ display: "grid", gridTemplateColumns: "minmax(0,2.6fr) minmax(0,1fr) minmax(0,1.4fr) minmax(0,1fr)", gap: 12, alignItems: "center", padding: "12px 14px", borderRadius: 12, background: g.verdict === "Promoted" ? "#E3F1EC" : g.verdict === "Rejected" ? "#FBE7E4" : "#F2F4F1" }}>
                  <span style={{ display: "flex", flexDirection: "column" }}>
                    <span style={{ fontWeight: 700 }}>{g.version} · {g.by}</span>
                    <span className="muted" style={{ fontSize: 13 }}>{g.summary}</span>
                  </span>
                  <span className="mono" data-correct>
                    {g.correct !== null && g.total !== null ? `${g.correct} / ${g.total}` : "—"}
                    {g.correct !== null && g.total ? <span className="muted"> · {((100 * g.correct) / g.total).toFixed(1)}%</span> : null}
                  </span>
                  <span style={{ fontSize: 13 }} data-regressions={g.regressions ?? ""}>
                    {g.regressions === null ? "—" : g.regressions === 0 ? "0" : `${g.regressions} value${g.regressions === 1 ? "" : "s"} that ${hood.gate.rows[0]?.version ?? "v3"} read right turn wrong`}
                    {g.regressionNotes.map((n) => (
                      <span key={n} className="mono muted" style={{ display: "block", fontSize: 11 }}>{n}</span>
                    ))}
                  </span>
                  <span><span className={`chip ${VERDICT_CHIP[g.verdict] ?? "chip-todo"}`}>{g.verdict}</span></span>
                </div>
              ))}
            </div>
          </section>

          <section style={{ display: "flex", flexWrap: "wrap", gap: 20, alignItems: "flex-start" }}>
            <div className="card" style={{ flex: "1 1 420px", minWidth: 0, padding: 24, display: "flex", flexDirection: "column", gap: 10 }}>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 8, alignItems: "flex-start", flexWrap: "wrap" }}>
                <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                  <h2 style={h2}>6 · Watcher, across weeks</h2>
                  <span style={sub}>
                    Follow-ups pulled from the doctor&apos;s notes and tracked until they happen. Wakes weekly
                    {hood.watcher.nextRun ? `; next run ${hood.watcher.nextRun}` : ""}
                    {hood.watcher.lastRun ? ` · last run ${hood.watcher.lastRun}` : ""}.
                  </span>
                </div>
                <button type="button" className="btn" disabled={busy !== null} onClick={() => act("watcher", onRunWatcher)}>
                  {busy === "watcher" ? "Running…" : "Run now"}
                </button>
              </div>
              {hood.watcher.rows.map((f) => (
                <div key={`${f.said}-${f.quote}`} style={{ display: "grid", gridTemplateColumns: "72px minmax(0,1fr)", gap: 14, padding: "10px 0", borderTop: "1px solid #E4E9E2" }}>
                  <span className="mono muted" style={{ fontSize: 13 }}>{f.said}</span>
                  <span style={{ display: "flex", flexDirection: "column" }}>
                    <span>&quot;{f.quote}&quot;</span>
                    <span style={{ fontSize: 14, color: f.status === "done" ? "#084F45" : f.status === "scheduled" ? "#4A5951" : "#8A3B07" }}>
                      {f.status === "done" ? "✓ " : ""}
                      {f.summary}
                    </span>
                  </span>
                </div>
              ))}
            </div>

            <div style={{ flex: "1 1 420px", minWidth: 0, background: "#13201A", color: "#F2F4F1", borderRadius: 20, padding: 24, display: "flex", flexDirection: "column", gap: 10 }}>
              <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                <h2 style={{ ...h2, color: "#FFFFFF" }}>7 · Governance log</h2>
                <span style={{ fontSize: 13, color: "#B7C4BC" }}>Policies the agents can&apos;t switch off. Every event tied to a real identity.</span>
              </div>
              {hood.log.map((l, i) => (
                <div key={`${l.event}-${i}`} data-event={l.event} style={{ display: "grid", gridTemplateColumns: "92px minmax(0,1fr)", gap: 12, padding: "8px 0", borderTop: "1px solid #2C3D34" }}>
                  <span>
                    <span className="mono" style={{ display: "inline-block", fontSize: 11, fontWeight: 600, borderRadius: 6, padding: "2px 8px", color: "#13201A", background: TAG_BG[l.event] ?? "#9FD9C8" }}>{l.event}</span>
                    {l.test && (
                      <span className="mono" style={{ display: "inline-block", marginTop: 4, fontSize: 10, fontWeight: 600, borderRadius: 6, padding: "1px 6px", color: "#13201A", background: "#E4E9E2" }}>TEST</span>
                    )}
                  </span>
                  <span style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                    <span style={{ fontSize: 14 }}>{l.what}</span>
                    <span className="mono" style={{ fontSize: 11, color: "#9FB0A6" }}>{l.meta}</span>
                  </span>
                </div>
              ))}
              <p style={{ margin: 0, fontSize: 13, color: "#B7C4BC", borderTop: "1px solid #2C3D34", paddingTop: 12 }}>
                Doctor-note text is encrypted client-side before it reaches Atlas. Lab values are stored as data the agents can query.
              </p>
            </div>
          </section>

          <section aria-labelledby="atlas" className="card" style={{ padding: 24, display: "flex", flexDirection: "column", gap: 14 }}>
            <h2 id="atlas" style={h2}>What runs on MongoDB Atlas</h2>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
              {[
                ["Agent Engine memory", "Terms, facts, visits and reading rules: all four types"],
                ["Agent Engine runtime", "Durable pause and resume, identity per action"],
                ["Voyage AI retrieval", "Finds matching past values, notes and terms"],
                ["Change streams", "A new upload starts the run; an answer resumes it"],
                ["GridFS", "Original report photos and PDFs, kept as proof"],
                ["Client-side encryption", "Doctor-note text encrypted before it is stored"],
              ].map(([title, text]) => (
                <div key={title} style={{ flex: "1 1 200px", minWidth: 0, border: "1px solid #DCE2DA", borderRadius: 14, padding: 14, display: "flex", flexDirection: "column", gap: 2 }}>
                  <span style={{ fontWeight: 700 }}>{title}</span>
                  <span className="muted" style={{ fontSize: 13 }}>{text}</span>
                </div>
              ))}
            </div>
          </section>

          <section className="card" style={{ borderRadius: 16, padding: "16px 20px", display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
            <span style={{ fontWeight: 700 }}>Back to what the family sees.</span>
            <button type="button" onClick={goFamily} style={{ minHeight: 44, padding: "0 18px", borderRadius: 10, border: "1px solid #13201A", background: "#13201A", color: "#FFFFFF", fontSize: 15, fontWeight: 600, cursor: "pointer" }}>
              ← Family view
            </button>
          </section>
        </>
      )}
    </div>
  );
}
