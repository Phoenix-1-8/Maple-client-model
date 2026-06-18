"use client";

import { PageHeader } from "@/components/Shell";
import { HBarChart, IndexAreaChart } from "@/components/charts";
import { PriceHeatmap } from "@/components/Heatmap";
import { Badge, ErrorState, KpiCard, Loading, Panel, SectionTitle } from "@/components/ui";
import { endpoints } from "@/lib/api";
import { inr, inrCompact, signedPct } from "@/lib/format";
import { useApi } from "@/lib/useApi";

const ROLE_TONE: Record<string, any> = {
  recommerce: "maple",
  marketplace: "sky",
  tradein: "amber",
};

export default function CompetitorsPage() {
  const comp = useApi<any>(endpoints.competitor);
  const index = useApi<any>(endpoints.index);

  if (comp.error) return <ErrorState message={comp.error} />;
  if (comp.loading || !comp.data) return <Loading />;

  const d = comp.data;
  const rankings = d.competitor_rankings || [];
  const mv = d.price_movement || {};
  const hist = (index.data?.history || []).map((h: any) => ({ day: h.day, index: h.index }));

  const barData = rankings.map((r: any) => ({
    label: r.is_own ? `★ ${r.platform_name}` : r.platform_name,
    value: r.median_price,
    color: r.is_own
      ? "#a855f7"
      : r.price_index >= 1.04
      ? "#f43f5e"
      : r.price_index >= 1.0
      ? "#f59e0b"
      : "#22c55e",
  }));

  return (
    <div>
      <PageHeader
        title="Competitor Intelligence"
        subtitle="Indian platform landscape · normalized to Superb-grade comparable prices"
        badge={<Badge tone="maple">{d.platforms_tracked} platforms tracked</Badge>}
      />

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <KpiCard label="Market Median" value={inr(d.market_median)} sub={<span>Superb-adjusted</span>} />
        <KpiCard label="Market Lowest" value={inr(d.market_lowest)} accent="amber" />
        <KpiCard
          label="Index 7d"
          value={signedPct(mv.change_7d_pct ?? 0)}
          accent={(mv.change_7d_pct ?? 0) >= 0 ? "maple" : "rose"}
        />
        <KpiCard
          label="Index 30d"
          value={signedPct(mv.change_30d_pct ?? 0)}
          accent={(mv.change_30d_pct ?? 0) >= 0 ? "maple" : "rose"}
        />
      </div>

      {/* Rankings */}
      <Panel className="mt-4">
        <SectionTitle
          title="Competitor Rankings"
          subtitle="From aggressive-discount (buy-side) to premium (sell-side) · Maple shown in violet vs the competitor benchmark"
        />
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-panel-line">
                <th className="th">#</th>
                <th className="th">Platform</th>
                <th className="th">Type</th>
                <th className="th text-right">Listings</th>
                <th className="th text-right">Lowest</th>
                <th className="th text-right">Median</th>
                <th className="th">Price index</th>
                <th className="th">Position</th>
              </tr>
            </thead>
            <tbody>
              {rankings.map((r: any, i: number) => (
                <tr
                  key={r.platform}
                  className={`row-hover border-b border-panel-line/50 ${
                    r.is_own ? "bg-violet-500/10 ring-1 ring-inset ring-violet-500/30" : ""
                  }`}
                >
                  <td className="td stat-num text-slate-500">{r.is_own ? "★" : i + 1}</td>
                  <td className={`td font-medium ${r.is_own ? "text-violet-200" : "text-white"}`}>
                    {r.platform_name}
                    {r.is_own && <span className="ml-2 text-[10px] uppercase tracking-wide text-violet-400">your store</span>}
                  </td>
                  <td className="td">
                    <Badge tone={r.is_own ? "violet" : ROLE_TONE[r.role] || "slate"}>{r.role}</Badge>
                  </td>
                  <td className="td stat-num text-right">{r.listings}</td>
                  <td className="td stat-num text-right text-slate-400">{inr(r.lowest_price)}</td>
                  <td className="td stat-num text-right">{inr(r.median_price)}</td>
                  <td className="td">
                    <div className="flex items-center gap-2">
                      <div className="relative h-1.5 w-24 overflow-hidden rounded-full bg-panel-line">
                        <div className="absolute left-1/2 top-0 h-full w-px bg-slate-600" />
                        <div
                          className={`h-full rounded-full ${
                            r.is_own ? "bg-violet-500" : r.price_index >= 1 ? "bg-amber-500" : "bg-maple-500"
                          }`}
                          style={{
                            width: `${Math.min(100, r.price_index * 50)}%`,
                          }}
                        />
                      </div>
                      <span className="stat-num text-xs text-slate-400">{r.price_index.toFixed(2)}×</span>
                    </div>
                  </td>
                  <td className="td text-slate-300">{r.position}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      {/* Heatmap (full width) */}
      <Panel className="mt-4">
        <SectionTitle
          title="Pricing Heatmap"
          subtitle="Platform × series, indexed to each series' market median"
        />
        {d.price_heatmap && <PriceHeatmap data={d.price_heatmap} />}
      </Panel>

      {/* Bars + trend */}
      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Panel>
          <SectionTitle title="Median Price by Platform" subtitle="Superb-adjusted comparable" />
          <HBarChart data={barData} unit="" height={280} />
        </Panel>
        <Panel>
          <SectionTitle title="Market Pricing Trend" subtitle="Maple Used-iPhone Index, last 60 days" />
          {hist.length > 0 ? <IndexAreaChart data={hist} height={280} /> : <Loading label="Loading trend…" />}
        </Panel>
      </div>
    </div>
  );
}
