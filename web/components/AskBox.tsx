"use client";

import { useState } from "react";
import type { Family } from "@/lib/types";

export default function AskBox({ family }: { family: Family }) {
  const [question, setQuestion] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    if (!question.trim()) return;
    setSending(true);
    setError(null);
    const response = await fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json", "x-member-id": family.viewer },
      body: JSON.stringify({ question }),
    });
    setSending(false);
    if (response.ok) setQuestion("");
    else setError((await response.json()).error ?? "could not send");
  };

  return (
    <section aria-labelledby="ask" className="card" style={{ padding: 24, display: "flex", flexDirection: "column", gap: 14 }}>
      <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
        <h2 id="ask" className="h2">
          Ask about Amma
        </h2>
        <span className="muted" style={{ fontSize: 14 }}>
          Answers come from her record. Every reply is checked live: anything that sounds like treatment advice becomes a question for her doctor.
        </span>
      </div>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
        style={{ display: "flex", gap: 8, flexWrap: "wrap" }}
      >
        <input
          aria-label="Your question about Amma"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="e.g. How has her blood sugar changed this year?"
          disabled={sending}
          style={{ flex: "1 1 320px", minHeight: 44, padding: "0 14px", borderRadius: 10, border: "1px solid var(--line-strong)", fontSize: 15, fontFamily: "inherit" }}
        />
        <button type="submit" className="btn btn-primary" disabled={sending || !question.trim()}>
          {sending ? "Sending…" : "Ask"}
        </button>
      </form>
      {error && <span style={{ color: "#8F1D12", fontSize: 14 }}>{error}</span>}
      {family.asks.map((a) => (
        <div key={a.id} className="fade-in" data-ask-status={a.status} data-ask-blocked={a.blocked} style={{ display: "flex", flexDirection: "column", gap: 6, borderTop: "1px solid var(--line)", paddingTop: 12 }}>
          <span style={{ fontWeight: 600 }}>{a.question}</span>
          {a.status !== "answered" ? (
            <span className="muted mono" style={{ fontSize: 13 }}>
              Drafting a reply and checking it against summarize-never-treat…
            </span>
          ) : (
            <div style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
              {a.blocked && (
                <span className="chip" style={{ background: "#FBE7E4", color: "#8F1D12", border: "1px solid #EDB8B0", flex: "0 0 auto" }}>
                  Advice blocked
                </span>
              )}
              <span>
                {a.blocked ? "Ask her doctor: " : ""}
                {a.reply}
              </span>
            </div>
          )}
        </div>
      ))}
    </section>
  );
}
