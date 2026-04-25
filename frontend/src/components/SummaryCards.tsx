interface Summary {
  total_miles: number;
  total_co2_kg: number;
  total_trips: number;
  top_mode: string;
}

export default function SummaryCards({ summary }: { summary: Summary }) {
  return (
    <div className="hero-row">
      <div className="stat-card">
        <div className="label">Miles Saved</div>
        <div className="value">{summary.total_miles.toFixed(1)}</div>
      </div>
      <div className="stat-card">
        <div className="label">CO2 Saved</div>
        <div className="value">{summary.total_co2_kg.toFixed(1)}<span style={{ fontSize: '.9rem', color: 'var(--muted)', marginLeft: '.2rem' }}>kg</span></div>
      </div>
      <div className="stat-card">
        <div className="label">Total Trips</div>
        <div className="value">{summary.total_trips}</div>
      </div>
      <div className="stat-card">
        <div className="label">Top Mode</div>
        <div className="value text-val">{summary.top_mode}</div>
      </div>
    </div>
  );
}
