'use client';

/**
 * ProductTable — sortable product inventory table with stock bars.
 */

import { useState, useMemo } from 'react';

export default function ProductTable({ products = [] }) {
  const [sortField, setSortField] = useState('name');
  const [sortDir, setSortDir] = useState('asc');

  const handleSort = (field) => {
    if (sortField === field) {
      setSortDir(sortDir === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDir('asc');
    }
  };

  const sorted = useMemo(() => {
    if (!Array.isArray(products)) return [];
    return [...products].sort((a, b) => {
      let aVal = a[sortField];
      let bVal = b[sortField];
      if (typeof aVal === 'string') aVal = aVal.toLowerCase();
      if (typeof bVal === 'string') bVal = bVal.toLowerCase();
      if (aVal < bVal) return sortDir === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortDir === 'asc' ? 1 : -1;
      return 0;
    });
  }, [products, sortField, sortDir]);

  const getStockLevel = (pct) => {
    if (pct < 10) return 'critical';
    if (pct < 30) return 'warning';
    return 'healthy';
  };

  const sortIcon = (field) => {
    if (sortField !== field) return ' ↕';
    return sortDir === 'asc' ? ' ↑' : ' ↓';
  };

  if (!products || products.length === 0) {
    return (
      <div className="card animate-in delay-3">
        <div className="card-header">
          <span className="card-title">📦 Product Inventory</span>
        </div>
        <div className="loading-container">
          <span className="loading-text">No products loaded. Seed the database to get started.</span>
        </div>
      </div>
    );
  }

  return (
    <div className="card animate-in delay-3">
      <div className="card-header">
        <span className="card-title">📦 Product Inventory</span>
        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
          {products.length} items
        </span>
      </div>
      <div className="table-wrapper">
        <table className="product-table">
          <thead>
            <tr>
              <th
                onClick={() => handleSort('name')}
                style={{ cursor: 'pointer' }}
              >
                Product{sortIcon('name')}
              </th>
              <th>SKU</th>
              <th
                onClick={() => handleSort('stock_percentage')}
                style={{ cursor: 'pointer' }}
              >
                Stock Level{sortIcon('stock_percentage')}
              </th>
              <th
                onClick={() => handleSort('unit_price')}
                style={{ cursor: 'pointer' }}
              >
                Unit Price{sortIcon('unit_price')}
              </th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((product) => {
              const pct = product.stock_percentage ?? 0;
              const level = getStockLevel(pct);
              return (
                <tr key={product.id}>
                  <td>
                    <span className="alert-item-name">{product.name}</span>
                  </td>
                  <td>
                    <span className="sku-badge">{product.sku}</span>
                  </td>
                  <td>
                    <div className="stock-bar-container">
                      <div className="stock-bar">
                        <div
                          className={`stock-bar-fill ${level}`}
                          style={{ width: `${Math.min(pct, 100)}%` }}
                        />
                      </div>
                      <span className={`stock-pct ${level}`}>
                        {pct}%
                      </span>
                    </div>
                  </td>
                  <td style={{ color: 'var(--text-secondary)' }}>
                    ${product.unit_price?.toFixed(2) ?? '0.00'}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
