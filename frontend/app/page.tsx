"use client";

import { PageHeader } from "@/components/Shell";
import { IndexAreaChart } from "@/components/charts";
import {
  Badge,
  Delta,
  ErrorState,
  KpiCard,
  Loading,
  Panel,
  ScoreBar,
  SectionTitle,
} from "@/components/ui";
import { endpoints } from "@/lib/api";
import { inr, inrCompact, pct, signedPct } from "@/lib/format";
import { useApi } from "@/lib/useApi";

export default function ExecutivePage() {
  const snap = useApi<any>(endpoints.snapshot);
  const metricsRes = useApi<any>(endpoints.metrics);

  if (snap.error) return <ErrorState message={snap.error} />;
  if (snap.loading || !snap.data) return <Loading />;

  const d = snap.data;
  const m = metricsRes.data?.headline;
  const idx = d.market_index || {};
  const hist = (d.market_index_history || []).map((h: any) => ({ day: h.day, index: h.index }));
  const dev = d.headline_device;

  return (
    <div>
      <PageHeader
        title="Executive Dashboard"
        subtitle="The state of the pre-owned iPhone market, priced by the AI Department"
        badge={
          <div className="flex items-center gap-2">
            <Badge tone="maple">● Live</Badge>
            <span className="text-xs text-slate-500">iPhone 13–17 · India + Dubai</span>
          </div>
        }
      />

      {/* KPI strip */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4 xl:grid-cols-6">
        <KpiCard
          label="Market Index"
          value={idx.index?.toFixed(2) ?? "—"}
          sub={<span>30d</span>}
          delta={idx.change_30d_pct}
        />
        <KpiCard
          label="Gross Margin Lift"
          value={m ? `+${m.gross_margin_lift_pts}pts` : "—"}
          sub={m ? <span>{inrCompact(m.gross_margin_lift_value_monthly)}/mo</span> : undefined}
          accent="maple"
        />
        <KpiCard
          label="Arbitrage Value"
          value={m ? inrCompact(m.arbitrage_opportunity_value_monthly) : "—"}
          sub={<span>monthly, surfaced</span>}
          accent="amber"
        />
        <KpiCard
          label="Pricing Accuracy"
          value={m ? pct(m.pricing_accuracy_after) : "—"}
          sub={m ? <span>was {pct(m.pricing_accuracy_before)}</span> : undefined}
          accent="sky"
        />
        <KpiCard
          label="Inventory Turn"
          value={m ? `+${m.inventory_turn_improvement_pct}%` : "—"}
          sub={<span>vs baseline</span>}
          accent="maple"
        />
        <KpiCard
          label="Market Coverage"
          value={m ? pct(m.market_coverage_pct) : "—"}
          sub={<span>of catalogue priced</span>}
          accent="slate"
        />
      </div>

      {/* Index + recommendation */}
      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Panel className="lg:col-span-2">
          <SectionTitle
            title="Maple Used-iPhone Market Index"
            subtitle="Weighted basket of fair values across the catalogue, base 100"
            right={
              <div className="text-right">
                <div className="stat-num text-2xl font-semibold text-white">
                  {idx.index?.toFixed(2)}
                </div>
                <div className="flex items-center justify-end gap-1.5 text-xs">
                  <Delta value={idx.change_1d_pct ?? 0} /> <span className="text-slate-500">1d</span>
                </div>
              </div>
            }
          />
          <IndexAreaChart data={hist} />
          <div className="mt-3 grid grid-cols-3 gap-3">
            {[
              { label: "1 day", v: idx.change_1d_pct },
              { label: "7 day", v: idx.change_7d_pct },
              { label: "30 day", v: idx.change_30d_pct },
            ].map((x) => (
              <div key={x.label} className="panel-soft px-3 py-2">
                <div className="text-[11px] uppercase tracking-wider text-slate-500">{x.label}</div>
                <div className={`stat-num text-sm font-semibold ${(x.v ?? 0) >= 0 ? "text-maple-400" : "text-rose-400"}`}>
                  {signedPct(x.v ?? 0)}
                </div>
              </div>
            ))}
          </div>
        </Panel>

        {/* Buy / Sell recommendation */}
        <Panel>
          <SectionTitle title="Price Recommendation" subtitle="Top-demand model · Superb grade" />
          {dev ? (
            <div>
              <div className="flex items-baseline justify-between">
                <div className="text-lg font-semibold text-white">{dev.model}</div>
                <Badge tone="slate">{dev.storage}</Badge>
              </div>
              <div className="mt-4 space-y-3">
                <RecoRow label="Recommended Buy" value={inr(dev.recommended_buy)} tone="amber" big />
                <RecoRow label="Recommended Sell" value={inr(dev.recommended_sell)} tone="maple" big />
                <div className="my-2 h-px bg-panel-line" />
                <RecoRow label="Fair Market Value" value={inr(dev.fair_value)} tone="slate" />
                <RecoRow
                  label="Spread / unit"
                  value={inr((dev.recommended_sell || 0) - (dev.recommended_buy || 0))}
                  tone="slate"
                />
              </div>
              <p className="mt-4 text-[11px] leading-relaxed text-slate-500">
                Sell = market median + brand + warranty + Maple trust premiums. Buy = sell − target
                margin − refurb − logistics − warranty reserve.
              </p>
            </div>
          ) : (
            <Loading label="No recommendation" />
          )}
        </Panel>
      </div>

      {/* Arbitrage */}
      <Panel className="mt-4">
        <SectionTitle
          title="Top Arbitrage Opportunities"
          subtitle="Buy-low → sell-high spreads across Indian cities (Superb-adjusted)"
          right={
            <span className="chip">
              Total surfaced: <b className="text-maple-300">{inrCompact(d.arbitrage_total_value)}</b>
            </span>
          }
        />
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-panel-line">
                <th className="th">Model</th>
                <th className="th">Buy in</th>
                <th className="th text-right">Buy</th>
                <th className="th">Sell in</th>
                <th className="th text-right">Sell</th>
                <th className="th text-right">Spread</th>
                <th className="th text-right">Opp. value</th>
              </tr>
            </thead>
            <tbody>
              {(d.top_arbitrage || []).map((o: any) => (
                <tr key={o.sku} className="row-hover border-b border-panel-line/50">
                  <td className="td font-medium text-white">
                    {o.model} <span className="text-slate-500">{o.storage}</span>
                  </td>
                  <td className="td"><Badge tone="sky">{o.buy_city}</Badge></td>
                  <td className="td stat-num text-right">{inr(o.buy_price)}</td>
                  <td className="td"><Badge tone="maple">{o.sell_city}</Badge></td>
                  <td className="td stat-num text-right">{inr(o.sell_price)}</td>
                  <td className="td text-right">
                    <span className="stat-num text-amber-400">+{pct(o.spread_pct)}</span>
                  </td>
                  <td className="td stat-num text-right text-maple-300">{inrCompact(o.opportunity_value)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      {/* Demand + underpriced */}
      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Panel>
          <SectionTitle title="High-Demand Models" subtitle="Liquidity × freshness × recency" />
          <div className="space-y-2.5">
            {(d.top_demand || []).map((x: any) => (
              <div key={x.sku} className="flex items-center justify-between gap-3">
                <div className="min-w-0">
                  <div className="truncate text-sm text-slate-200">
                    {x.model} <span className="text-slate-500">{x.storage}</span>
                  </div>
                  <div className="text-[11px] text-slate-500">{x.listings} listings · fair {inr(x.fair_value)}</div>
                </div>
                <ScoreBar value={x.demand_score} />
              </div>
            ))}
          </div>
        </Panel>
        <Panel>
          <SectionTitle title="Underpriced — Acquisition Targets" subtitle="Cheapest live offer vs fair value" />
          <div className="space-y-2.5">
            {(d.top_underpriced || []).map((x: any) => (
              <div key={x.sku} className="flex items-center justify-between gap-3">
                <div className="min-w-0">
                  <div className="truncate text-sm text-slate-200">
                    {x.model} <span className="text-slate-500">{x.storage}</span>
                  </div>
                  <div className="text-[11px] text-slate-500">
                    buy {inr(x.best_available_buy)} · fair {inr(x.fair_value)}
                  </div>
                </div>
                <Badge tone="amber">−{pct(x.underpricing_pct)}</Badge>
              </div>
            ))}
          </div>
        </Panel>
      </div>
    </div>
  );
}

function RecoRow({
  label,
  value,
  tone,
  big,
}: {
  label: string;
  value: string;
  tone: "maple" | "amber" | "slate";
  big?: boolean;
}) {
  const color =
    tone === "maple" ? "text-maple-300" : tone === "amber" ? "text-amber-400" : "text-slate-300";
  return (
    <div className="flex items-center justify-between">
      <span className="text-sm text-slate-400">{label}</span>
      <span className={`stat-num font-semibold ${color} ${big ? "text-xl" : "text-sm"}`}>{value}</span>
    </div>
  );
}
