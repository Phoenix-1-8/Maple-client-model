// Indian-rupee + number formatting helpers.

export function inr(value: number | null | undefined, opts?: { decimals?: number }): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  const sign = value < 0 ? "-" : "";
  const n = Math.abs(value).toLocaleString("en-IN", {
    maximumFractionDigits: opts?.decimals ?? 0,
  });
  return `${sign}₹${n}`;
}

// Compact Indian currency: ₹4.8L, ₹1.24Cr
export function inrCompact(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  const n = Math.abs(value);
  const sign = value < 0 ? "-" : "";
  if (n >= 1e7) return `${sign}₹${(n / 1e7).toFixed(2)}Cr`;
  if (n >= 1e5) return `${sign}₹${(n / 1e5).toFixed(1)}L`;
  if (n >= 1e3) return `${sign}₹${(n / 1e3).toFixed(1)}K`;
  return `${sign}₹${Math.round(n)}`;
}

export function pct(value: number | null | undefined, decimals = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return `${value.toFixed(decimals)}%`;
}

export function signedPct(value: number | null | undefined, decimals = 2): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  const s = value > 0 ? "+" : "";
  return `${s}${value.toFixed(decimals)}%`;
}

export function trendClass(value: number | null | undefined): string {
  if (value === null || value === undefined) return "text-slate-400";
  if (value > 0.001) return "text-maple-400";
  if (value < -0.001) return "text-rose-400";
  return "text-slate-400";
}

export function shortDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("en-IN", { day: "2-digit", month: "short" });
}
