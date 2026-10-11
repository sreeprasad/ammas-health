"use client";

import { useState } from "react";
import FamilyView from "./FamilyView";
import UnderTheHood from "./UnderTheHood";

type View = "family" | "hood";

export default function ScreenSwitch() {
  const [view, setView] = useState<View>("family");

  return (
    <div className="page">
      <div className="shell">
        <div className="topbar">
          <nav aria-label="Screens" className="tabs">
            <button
              type="button"
              className="tab"
              aria-pressed={view === "family"}
              onClick={() => setView("family")}
            >
              Family view
            </button>
            <button
              type="button"
              className="tab"
              aria-pressed={view === "hood"}
              onClick={() => setView("hood")}
            >
              Under the hood
            </button>
          </nav>
          <span className="pill pill-idle">No run yet</span>
        </div>
        {view === "family" ? <FamilyView /> : <UnderTheHood />}
      </div>
    </div>
  );
}
