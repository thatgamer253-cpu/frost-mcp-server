'use client';

/**
 * AnalyticsCards — stat cards showing key warehouse metrics.
 */

export default function AnalyticsCards({ analytics }) {
  if (!analytics) {
    return (
      <div className="stats-grid">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className={`card stat-card animate-in delay-${i}`}>
            <div className="loading-container" style={{ padding: '1rem' }}>
              <div className="spinner" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  const cards = [
    {
      label: 'Total Products',
      value: analytics.total_products,
      color: 'indigo',
      icon: '📦',
    },
    {
      label: 'Categories',
      value: analytics.total_categories,
      color: 'blue',
      icon: '🏷️',
    },
    {
      label: 'Low Stock Items',
      value: analytics.low_stock_count,
      color: analytics.low_stock_count > 0 ? 'amber' : 'emerald',
      icon: analytics.low_stock_count > 0 ? '⚠️' : '✅',
    },
    {
      label: 'Total Stock Value',
      value: `$${analytics.total_stock_value?.toLocaleString(undefined, { minimumFractionDigits: 2 })}`,
      color: 'emerald',
      icon: '💰',
    },
  ];

  return (
    <div className="stats-grid">
      {cards.map((card, i) => (
        <div key={card.label} className={`card stat-card ${card.color} animate-in delay-${i + 1}`}>
          <div className="card-header">
            <span className="card-title">{card.label}</span>
            <span className="card-icon">{card.icon}</span>
          </div>
          <div className="stat-value">{card.value}</div>
        </div>
      ))}
    </div>
  );
}
