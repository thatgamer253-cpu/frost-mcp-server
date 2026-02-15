'use client';

/**
 * HealthGauge — circular gauge showing overall warehouse stock health.
 */

export default function HealthGauge({ percentage = 0, categories = [] }) {
  const radius = 48;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (percentage / 100) * circumference;

  const level = percentage >= 70 ? 'healthy' : percentage >= 40 ? 'warning' : 'critical';
  const color =
    level === 'healthy' ? 'var(--accent-emerald)' :
    level === 'warning' ? 'var(--accent-amber)' :
    'var(--accent-red)';

  return (
    <div className="card animate-in delay-2">
      <div className="card-header">
        <span className="card-title">📊 Warehouse Health</span>
      </div>

      <div className="health-gauge">
        <div className="gauge-ring">
          <svg viewBox="0 0 120 120">
            <circle className="gauge-bg" cx="60" cy="60" r={radius} />
            <circle
              className={`gauge-fill ${level}`}
              cx="60"
              cy="60"
              r={radius}
              strokeDasharray={circumference}
              strokeDashoffset={offset}
            />
          </svg>
          <span className="gauge-value" style={{ color }}>
            {percentage}%
          </span>
        </div>
        <span className="gauge-label">
          Stock Health Score
        </span>
      </div>

      {/* Category Breakdown */}
      {categories && categories.length > 0 && (
        <>
          <div className="card-header" style={{ marginTop: '0.5rem' }}>
            <span className="card-title">Category Breakdown</span>
          </div>
          <ul className="category-list">
            {categories.map((cat) => (
              <li key={cat.id || cat.name} className="category-item">
                <span className="category-name">{cat.name}</span>
                <span className="category-count">{cat.product_count} items</span>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
