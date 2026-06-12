"use client";

import { PageHeader } from "@/components/Shell";
import {
  Badge,
  ConfidenceDot,
  ErrorState,
  KpiCard,
  Loading,
  Panel,
  ScoreBar,
  SectionTitle,
} from "@/components/ui";
import { endpoints } from "@/lib/api";
import { inr, pct } from "@/lib/format";
import { useApi } from "@/lib/useApi";

export default function InventoryPage() {
  const res = useApi<any>(endpoints.inventory);

  if (res.error) return <ErrorState message={res.error} />;
  if (res.loading || !res.data) return <Loading />;

  const d = res.data;
  const k = d.kpis || {};

  return (
    <div>
      <PageHeader
        title="Inventory Intelligence"
        subtitle="Demand signals, acquisition targets, oversupply alerts & pricing recommendations"
        badge={<Badge tone="maple">{k.models_tracked}/{k.catalogue_size} models priced</Badge>}
      />

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <KpiCard label="Models Tracked" value={k.models_tracked} sub={<span>of {k.catalogue_size} catalogue</span>} />
        <KpiCard label="Median Listings / Model" value={k.median_listings_per_model} accent="sky" />
        <KpiCard label="Avg Pricing Confidence" value={pct((k.avg_confidence ?? 0) * 100)} accent="maple" />
        <KpiCard
          label="Coverage Gaps"
          value={k.coverage_gaps}
          sub={<span>thin-supply models</span>}
          accent={k.coverage_gaps > 0 ? "amber" : "slate"}
        />
      </div>

      {/* Demand + pricing reco */}
      <Panel className="mt-4">
        <SectionTitle
          title="High-Demand Models — Pricing Recommendations"
          subtitle="What to buy aggressively, and at what price (Superb grade)"
        />
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-panel-line">
                <th className="th">Model</th>
                <th className="th text-right">Listings</th>
                <th className="th text-right">Avg age</th>
                <th className="th">Demand</th>
                <th className="th text-right">Fair value</th>
                <th className="th text-right">Buy @</th>
                <th className="th text-right">Sell @</th>
                <th className="th">Conf.</th>
              </tr>
            </thead>
            <tbody>
              {(d.high_demand || []).map((x: any) => (
                <tr key={x.sku} className="row-hover border-b border-panel-line/50">
                  <td className="td font-medium text-white">
                    {x.model} <span className="text-slate-500">{x.storage}</span>
                  </td>
                  <td className="td stat-num text-right">{x.listings}</td>
                  <td className="td stat-num text-right text-slate-400">{x.avg_listing_age_days}d</td>
                  <td className="td"><ScoreBar value={x.demand_score} /></td>
                  <td className="td stat-num text-right text-slate-300">{inr(x.fair_value)}</td>
                  <td className="td stat-num text-right text-amber-400">{inr(x.recommended_buy)}</td>
                  <td className="td stat-num text-right text-maple-300">{inr(x.recommended_sell)}</td>
                  <td className="td"><ConfidenceDot value={x.confidence} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Panel>
          <SectionTitle title="Underpriced — Buy Signals" subtitle="Cheapest live offer far below fair value" />
          <div className="space-y-2.5">
            {(d.underpriced || []).map((x: any) => (
              <div key={x.sku} className="flex items-center justify-between gap-3 border-b border-panel-line/40 pb-2 last:border-0">
                <div className="min-w-0">
                  <div className="truncate text-sm text-slate-200">
                    {x.model} <span className="text-slate-500">{x.storage}</span>
                  </div>
                  <div className="text-[11px] text-slate-500">
                    best buy {inr(x.best_available_buy)} · fair {inr(x.fair_value)}
                  </div>
                </div>
                <Badge tone="maple">−{pct(x.underpricing_pct)}</Badge>
              </div>
            ))}
          </div>
        </Panel>
        <Panel>
          <SectionTitle title="Oversupplied — Hold / Discount" subtitle="Supply well above catalogue norm" />
          {(d.oversupplied || []).length > 0 ? (
            <div className="space-y-2.5">
              {(d.oversupplied || []).map((x: any) => (
                <div key={x.sku} className="flex items-center justify-between gap-3 border-b border-panel-line/40 pb-2 last:border-0">
                  <div className="min-w-0">
                    <div className="truncate text-sm text-slate-200">
                      {x.model} <span className="text-slate-500">{x.storage}</span>
                    </div>
                    <div className="text-[11px] text-slate-500">{x.listings} listings</div>
                  </div>
                  <Badge tone="amber">{x.supply_ratio}× supply</Badge>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-500">No oversupplied models — supply is balanced.</p>
          )}
        </Panel>
      </div>

      {(d.inventory_gaps || []).length > 0 && (
        <Panel className="mt-4">
          <SectionTitle title="Inventory Gaps" subtitle="Thin supply — hard to source, watch for stockouts" />
          <div className="flex flex-wrap gap-2">
            {(d.inventory_gaps || []).map((g: any) => (
              <span key={g.sku} className="chip">
                {g.model} {g.storage}
                <span className="text-slate-600">· {g.listings}</span>
              </span>
            ))}
          </div>
        </Panel>
      )}
    </div>
  );
}
