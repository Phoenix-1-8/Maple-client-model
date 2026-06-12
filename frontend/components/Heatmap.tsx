import React from "react";

interface Cell {
  series: number;
  index: number | null;
  median_price: number | null;
  n: number;
}
interface Row {
  platform: string;
  platform_name: string;
  cells: Cell[];
}

// index 1.0 == series market median. <1 cheaper (value, green), >1 premium (amber/red).
function cellColor(index: number | null): string {
  if (index === null) return "transparent";
  const d = index - 1; // deviation from market
  if (d <= -0.08) return "rgba(34,197,94,0.42)";
  if (d <= -0.03) return "rgba(34,197,94,0.24)";
  if (d < 0.03) return "rgba(148,163,184,0.12)";
  if (d < 0.08) return "rgba(245,158,11,0.28)";
  return "rgba(244,63,94,0.34)";
}

export function PriceHeatmap({ data }: { data: { series: number[]; rows: Row[] } }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-separate border-spacing-1">
        <thead>
          <tr>
            <th className="th sticky left-0 bg-panel">Platform</th>
            {data.series.map((s) => (
              <th key={s} className="th text-center">
                iPhone {s}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.rows.map((row) => (
            <tr key={row.platform}>
              <td className="td sticky left-0 z-[1] whitespace-nowrap bg-panel font-medium text-slate-200">
                {row.platform_name}
              </td>
              {row.cells.map((c) => (
                <td
                  key={c.series}
                  className="rounded-md text-center"
                  style={{ background: cellColor(c.index) }}
                  title={
                    c.index !== null
                      ? `${row.platform_name} · iPhone ${c.series}\nIndex ${c.index} · ₹${c.median_price?.toLocaleString(
                          "en-IN"
                        )} · n=${c.n}`
                      : "no data"
                  }
                >
                  <div className="px-2 py-2.5">
                    {c.index !== null ? (
                      <>
                        <div className="stat-num text-sm font-semibold text-white">
                          {c.index.toFixed(2)}×
                        </div>
                        <div className="stat-num text-[10px] text-slate-400">
                          ₹{((c.median_price || 0) / 1000).toFixed(0)}k
                        </div>
                      </>
                    ) : (
                      <span className="text-xs text-slate-700">—</span>
                    )}
                  </div>
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      <div className="mt-3 flex items-center gap-3 text-[11px] text-slate-500">
        <span className="flex items-center gap-1">
          <span className="h-3 w-3 rounded" style={{ background: cellColor(0.9) }} /> Value
        </span>
        <span className="flex items-center gap-1">
          <span className="h-3 w-3 rounded" style={{ background: cellColor(1.0) }} /> At market
        </span>
        <span className="flex items-center gap-1">
          <span className="h-3 w-3 rounded" style={{ background: cellColor(1.1) }} /> Premium
        </span>
        <span className="ml-2">Index = platform price ÷ series market median</span>
      </div>
    </div>
  );
}
