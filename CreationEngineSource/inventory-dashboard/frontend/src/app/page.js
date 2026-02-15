'use client';

/**
 * Main Dashboard Page
 *
 * Orchestrates all dashboard components:
 *   - Analytics stat cards (top row)
 *   - Product inventory table (main area)
 *   - Stock Alert panel (sidebar — turns red on low stock)
 *   - Health gauge with category breakdown (sidebar)
 */

import { useState, useEffect, useCallback } from 'react';
import StockAlert from '@/components/StockAlert';
import ProductTable from '@/components/ProductTable';
import AnalyticsCards from '@/components/AnalyticsCards';
import HealthGauge from '@/components/HealthGauge';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function Dashboard() {
  const [products, setProducts] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [seeding, setSeeding] = useState(false);
  const [error, setError] = useState(null);

  const fetchDashboardData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const [productsRes, analyticsRes] = await Promise.all([
        fetch(`${API_BASE}/products`),
        fetch(`${API_BASE}/analytics`),
      ]);

      if (!productsRes.ok || !analyticsRes.ok) {
        throw new Error('Failed to fetch dashboard data');
      }

      const productsData = await productsRes.json();
      const analyticsData = await analyticsRes.json();

      setProducts(Array.isArray(productsData) ? productsData : []);
      setAnalytics(analyticsData);
    } catch (err) {
      console.error('Dashboard fetch error:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDashboardData();
    // Auto-refresh every 30 seconds
    const interval = setInterval(fetchDashboardData, 30000);
    return () => clearInterval(interval);
  }, [fetchDashboardData]);

  const handleSeed = async () => {
    try {
      setSeeding(true);
      const res = await fetch(`${API_BASE}/seed`, { method: 'POST' });
      if (!res.ok) throw new Error('Seed failed');
      // Refresh all data after seeding
      await fetchDashboardData();
    } catch (err) {
      console.error('Seed error:', err);
    } finally {
      setSeeding(false);
    }
  };

  return (
    <main className="dashboard">
      {/* ── Header ─────────────────────────────────────────── */}
      <header className="dashboard-header">
        <div>
          <h1>📦 Warehouse Inventory</h1>
          <p className="subtitle">
            Real-time stock monitoring &amp; analytics dashboard
          </p>
        </div>
        <div className="header-actions">
          <span className="header-badge badge-live">Live</span>
          <button
            className="seed-button"
            onClick={handleSeed}
            disabled={seeding}
          >
            {seeding ? (
              <>
                <span className="spinner" style={{ width: 14, height: 14, borderWidth: 2 }} />
                Seeding...
              </>
            ) : (
              <>🌱 Seed Demo Data</>
            )}
          </button>
          <button
            className="seed-button"
            onClick={fetchDashboardData}
            style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid var(--border-subtle)' }}
          >
            🔄 Refresh
          </button>
        </div>
      </header>

      {/* ── Error Banner ───────────────────────────────────── */}
      {error && (
        <div className="card" style={{
          marginBottom: 'var(--space-lg)',
          borderColor: 'rgba(239, 68, 68, 0.3)',
          textAlign: 'center',
          padding: 'var(--space-lg)',
        }}>
          <p style={{ color: 'var(--accent-rose)', fontWeight: 600 }}>
            ⚠️ Connection Error
          </p>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem', marginTop: '0.5rem' }}>
            {error}. Make sure the backend is running at <code>{API_BASE}</code>
          </p>
          <button className="seed-button" onClick={fetchDashboardData} style={{ marginTop: '1rem' }}>
            🔄 Retry Connection
          </button>
        </div>
      )}

      {/* ── Analytics Cards (Top Row) ──────────────────────── */}
      <AnalyticsCards analytics={analytics} />

      {/* ── Main Grid: Table + Sidebar ─────────────────────── */}
      <div className="main-grid">
        {/* Left: Product Table */}
        <div>
          <ProductTable products={products} />
        </div>

        {/* Right: Sidebar */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-lg)' }}>
          <StockAlert apiUrl={API_BASE} />
          <HealthGauge
            percentage={analytics?.stock_health_percentage ?? 0}
            categories={analytics?.categories ?? []}
          />
        </div>
      </div>
    </main>
  );
}
