"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { Family } from "@/lib/types";
import FamilyView from "./FamilyView";
import UnderTheHood from "./UnderTheHood";

type View = "family" | "hood";

const PILL = {
  none: "pill-idle",
  running: "pill-paused",
  paused: "pill-paused",
  complete: "pill-complete",
  failed: "pill-paused",
} as const;

export default function ScreenSwitch() {
  const [view, setView] = useState<View>("family");
  const [family, setFamily] = useState<Family | null>(null);
  const pending = useRef<ReturnType<typeof setTimeout> | null>(null);

  const refresh = useCallback(async () => {
    const response = await fetch("/api/family", { cache: "no-store" });
    if (response.ok) setFamily(await response.json());
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- initial load from an external store
    refresh();
    const events = new EventSource("/api/live");
    events.addEventListener("change", () => {
      if (pending.current) clearTimeout(pending.current);
      pending.current = setTimeout(refresh, 120);
    });
    return () => {
      events.close();
      if (pending.current) clearTimeout(pending.current);
    };
  }, [refresh]);

  const answer = useCallback(async (runId: string, valueId: string, value: number) => {
    const response = await fetch("/api/answers", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ run_id: runId, value_id: valueId, value, member_id: "sreeprasad" }),
    });
    if (!response.ok) throw new Error((await response.json()).error ?? "answer rejected");
  }, []);

  const run = family?.run ?? { status: "none" as const, text: "No run yet" };

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
          <span className={`pill ${PILL[run.status]}`} data-run-status={run.status}>
            {run.text}
          </span>
        </div>
        {view === "family" ? <FamilyView family={family} onAnswer={answer} goHood={() => setView("hood")} /> : <UnderTheHood />}
      </div>
    </div>
  );
}
