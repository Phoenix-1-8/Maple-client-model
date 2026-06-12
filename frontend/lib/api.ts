// API client for the Maple AI Department backend.

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000/api";

export async function apiGet<T = any>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`API ${path} failed: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export async function apiPost<T = any>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`API ${path} failed: ${res.status}`);
  return res.json() as Promise<T>;
}

export const endpoints = {
  health: "/health",
  snapshot: "/market/snapshot",
  metrics: "/market/metrics",
  index: "/market/index",
  pricing: "/market/pricing",
  competitor: "/agents/competitor",
  arbitrage: "/agents/arbitrage",
  inventory: "/agents/inventory",
  dubai: "/agents/dubai",
  facets: "/listings/facets",
  refresh: "/scrape/refresh",
  grades: "/normalization/grades",
  config: "/config",
};
