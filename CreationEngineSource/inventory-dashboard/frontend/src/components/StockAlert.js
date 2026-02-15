'use client';

/**
 * StockAlert Component
 *
 * Fetches /low-stock endpoint and displays alerts.
 * - RED state when low-stock items are found
 * - GREEN "All Clear" state when the list is empty
 * - Handles empty list [] without crashing (validated)
 */

import { useState, useEffect, useCallback } from 'react';

export default function StockAlert({ apiUrl }) {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchLowStock = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const baseUrl = apiUrl || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const res = await fetch(`${baseUrl}/low-stock`);

      if (!res.ok) {
        throw new Error(`API returned ${res.status}`);
      }

      const data = await res.json();

      // ── VALIDATION: Safely handle any response shape ──
      // If data is not an array, default to empty array
      // This prevents crashes when the backend returns null,
      // undefined, or an unexpected shape.
      if (!Array.isArray(data)) {
        console.warn('/low-stock returned non-array:', data);
        setAlerts([]);
      } else {
        setAlerts(data);
      }
    } catch (err) {
      console.error('Failed to fetch low-stock data:', err);
      setError(err.message);
      setAlerts([]); // Default to empty on error — no crash
    } finally {
      setLoading(false);
    }
  }, [apiUrl]);

  useEffect(() => {
    fetchLowStock();

    // Auto-refresh every 30 seconds
    const interval = setInterval(fetchLowStock, 30000);
    return () => clearInterval(interval);
  }, [fetchLowStock]);

  // ── Loading State ──────────────────────────────────────────
  if (loading) {
    return (
      <div className="card stock-alert">
        <div className="loading-container">
          <div className="spinner"></div>
          <span className="loading-text">Checking stock levels...</span>
        </div>
      </div>
    );
  }

  // ── Error State ────────────────────────────────────────────
  if (error) {
    return (
      <div className="card stock-alert danger">
        <div className="alert-header">
          <span className="alert-title danger">⚠️ Stock Alert</span>
        </div>
        <div className="error-container">
          <span>Unable to fetch stock data</span>
          <span style={{ fontSize: '0.75rem', opacity: 0.7 }}>{error}</span>
          <button className="seed-button" onClick={fetchLowStock} style={{ marginTop: '0.5rem' }}>
            🔄 Retry
          </button>
        </div>
      </div>
    );
  }

  // ── Determine state: danger (has items) or safe (empty list) ──
  const hasAlerts = alerts.length > 0;
  const stateClass = hasAlerts ? 'danger' : 'safe';

  return (
    <div className={`card stock-alert ${stateClass} animate-in`}>
      <div className="alert-header">
        <span className={`alert-title ${stateClass}`}>
          {hasAlerts ? '🔴 Low Stock Alert' : '✅ Stock Alert'}
        </span>
        <span className={`alert-count ${stateClass}`}>
          {hasAlerts ? alerts.length : '0'}
        </span>
      </div>

      {/* ── RED STATE: Display low-stock items ──────────────── */}
      {hasAlerts && (
        <ul className="alert-list">
          {alerts.map((item) => (
            <li key={item.id || item.sku} className="alert-item">
              <div className="alert-item-info">
                <span className="alert-item-name">{item.name}</span>
                <span className="alert-item-sku">
                  {item.sku} · {item.category_name}
                </span>
              </div>
              <div className="alert-item-stock">
                <div className="alert-item-pct">
                  {item.stock_percentage != null
                    ? `${item.stock_percentage}%`
                    : `${item.current_stock}/${item.initial_capacity}`
                  }
                </div>
                <div className="alert-item-label">
                  {item.current_stock} / {item.initial_capacity} units
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}

      {/* ── GREEN STATE: Empty list — All Clear ────────────── */}
      {!hasAlerts && (
        <div className="safe-message">
          <span className="safe-icon">🛡️</span>
          <span className="safe-text">All Clear</span>
          <span className="safe-subtext">
            All items are above 10% capacity threshold.
            <br />No restocking needed.
          </span>
        </div>
      )}
    </div>
  );
}
