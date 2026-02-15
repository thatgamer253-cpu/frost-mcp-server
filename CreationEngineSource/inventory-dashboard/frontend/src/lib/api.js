/**
 * API client for the warehouse backend.
 * Base URL is configurable via NEXT_PUBLIC_API_URL environment variable.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function fetchAPI(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  try {
    const res = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
    if (!res.ok) {
      throw new Error(`API error: ${res.status} ${res.statusText}`);
    }
    return await res.json();
  } catch (error) {
    console.error(`Failed to fetch ${endpoint}:`, error);
    throw error;
  }
}

/** GET /products — all products with stock info */
export async function getProducts() {
  return fetchAPI('/products');
}

/** GET /categories — all categories */
export async function getCategories() {
  return fetchAPI('/categories');
}

/**
 * GET /low-stock — products where current_stock < 0.1 × initial_capacity
 * Returns [] when all items are healthy.
 */
export async function getLowStock() {
  return fetchAPI('/low-stock');
}

/** GET /stock-logs/{id} — stock log history for a product */
export async function getStockLogs(productId) {
  return fetchAPI(`/stock-logs/${productId}`);
}

/** GET /analytics — dashboard summary stats */
export async function getAnalytics() {
  return fetchAPI('/analytics');
}

/** POST /seed — populate demo data */
export async function seedDatabase() {
  return fetchAPI('/seed', { method: 'POST' });
}
