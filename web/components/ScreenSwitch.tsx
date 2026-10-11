"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { Family } from "@/lib/types";
import FamilyView, { type Denied } from "./FamilyView";
import UnderTheHood from "./UnderTheHood";

type View = "family" | "hood";
type Member = { member_id: string; name: string; scope: string };

const PILL = {
  none: "pill-idle",
  running: "pill-paused",
  paused: "pill-paused",
  complete: "pill-complete",
  failed: "pill-paused",
} as const;

export default function ScreenSwitch() {
  const [view, setView] = useState<View>("family");
  const [members, setMembers] = useState<Member[]>([]);
  const [memberId, setMemberId] = useState("sreeprasad");
  const [family, setFamily] = useState<Family | null>(null);
  const [denied, setDenied] = useState<Denied | null>(null);
  const pending = useRef<ReturnType<typeof setTimeout> | null>(null);

  const refresh = useCallback(async () => {
    const headers = { "x-member-id": memberId };
    const response = await fetch("/api/family", { cache: "no-store", headers });
    if (response.ok) {
      setFamily(await response.json());
      setDenied(null);
      return;
    }
    setFamily(null);
    const meds = await fetch("/api/medications", { cache: "no-store", headers });
    setDenied({ status: response.status, lines: meds.ok ? (await meds.json()).lines : [] });
  }, [memberId]);

  useEffect(() => {
    fetch("/api/members").then(async (r) => r.ok && setMembers(await r.json()));
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- load from an external store when the viewer changes
    refresh();
    const events = new EventSource(`/api/live?as=${encodeURIComponent(memberId)}`);
    events.addEventListener("change", () => {
      if (pending.current) clearTimeout(pending.current);
      pending.current = setTimeout(refresh, 120);
    });
    return () => {
      events.close();
      if (pending.current) clearTimeout(pending.current);
    };
  }, [refresh, memberId]);

  const answer = useCallback(
    async (runId: string, valueId: string, value: number) => {
      const response = await fetch("/api/answers", {
        method: "POST",
        headers: { "Content-Type": "application/json", "x-member-id": memberId },
        body: JSON.stringify({ run_id: runId, value_id: valueId, value }),
      });
      if (!response.ok) throw new Error((await response.json()).error ?? "answer rejected");
    },
    [memberId],
  );

  const run = family?.run ?? { status: "none" as const, text: denied ? "Lab values hidden for this viewer" : "No run yet" };

  return (
    <div className="page">
      <div className="shell">
        <div className="topbar">
          <nav aria-label="Screens" className="tabs">
            <button type="button" className="tab" aria-pressed={view === "family"} onClick={() => setView("family")}>
              Family view
            </button>
            <button type="button" className="tab" aria-pressed={view === "hood"} onClick={() => setView("hood")}>
              Under the hood
            </button>
          </nav>
          <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
            <label className="mono muted" style={{ fontSize: 12, display: "flex", gap: 6, alignItems: "center" }}>
              Viewing as
              <select
                value={memberId}
                onChange={(e) => setMemberId(e.target.value)}
                style={{ minHeight: 36, borderRadius: 8, border: "1px solid var(--line-strong)", padding: "0 8px", fontFamily: "inherit" }}
              >
                {members.map((m) => (
                  <option key={m.member_id} value={m.member_id}>
                    {m.name} ({m.scope})
                  </option>
                ))}
              </select>
            </label>
            <span className={`pill ${PILL[run.status]}`} data-run-status={run.status}>
              {run.text}
            </span>
          </div>
        </div>
        {view === "family" ? (
          <FamilyView family={family} denied={denied} onAnswer={answer} goHood={() => setView("hood")} />
        ) : (
          <UnderTheHood />
        )}
      </div>
    </div>
  );
}
