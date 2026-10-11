export default function FamilyView() {
  return (
    <div className="screen">
      <header className="screen-header">
        <div>
          <span className="eyebrow">Sample data · summaries, not medical advice</span>
          <h1>Amma&apos;s health</h1>
          <p className="lede">Amrita Hospital · 23 reports across 5 visits · Jan – Sep 2026 · next visit Oct 22</p>
        </div>
        <div className="actions">
          <button type="button" className="btn">Share with family</button>
          <button type="button" className="btn btn-primary">Upload report</button>
        </div>
      </header>
      <section className="empty">Body map, area stories and the report grid arrive in M4.</section>
    </div>
  );
}
