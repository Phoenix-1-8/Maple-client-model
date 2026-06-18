"use client";

import { useMemo, useState } from "react";
import { PageHeader } from "@/components/Shell";
import { HBarChart, RetentionChart } from "@/components/charts";
import {
  Badge,
  ConfidenceDot,
  ErrorState,
  KpiCard,
  Loading,
  Panel,
  SectionTitle,
} from "@/components/ui";
import { endpoints } from "@/lib/api";
import { inr, pct, signedPct } from "@/lib/format";
import { useApi } from "@/lib/useApi";

function premiumTone(v: number): string {
  if (v > 9) return "text-rose-400";
  if (v < 0) return "text-maple-400";
  return "text-amber-400";
}

const VERDICT_TONE: Record<string, any> = {
  "Premium justified": "maple",
  "At or below market": "sky",
  "Slight premium over justified": "amber",
  "Above justified premium": "rose",
};

export default function MaplePage() {
  const cmp = useApi<any>(endpoints.mapleComparison);
  const ml = useApi<any>(endpoints.mlPricing);
  const [query, setQuery] = useState("");

  const devices: any[] = cmp.data?.devices || [];
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return devices;
    return devices.filter((d) => `${d.model} ${d.storage} ${d.sku}`.toLowerCase().includes(q));
  }, [devices, query]);

  if (cmp.error) return <ErrorState message={cmp.error} />;
  if (cmp.loading || !cmp.data) return <Loading label="Comparing Maple vs the market…" />;

  const head = cmp.data.headline || {};
  const just = cmp.data.premium_justification || {};
  const mlAvail = ml.data?.available;
  const mlModel = ml.data?.model;

  const topPremium = [...devices]
    .filter((d) => d.market_confidence >= 0.4)
    .sort((a, b) => b.premium_vs_fair_pct - a.premium_vs_fair_pct)
    .slice(0, 10)
    .map((d) => ({
      label: `${d.model} ${d.storage}`.replace("iPhone ", ""),
      value: d.premium_vs_fair_pct,
      color: d.premium_vs_fair_pct > (cmp.data.justified_premium_pct || 8) ? "#fb7185" : "#22c55e",
    }));

  return (
    <div>
      <PageHeader
        title="Maple vs Market"
        subtitle="Maple's own prices against the market — and what justifies the premium"
        badge={<Badge tone="maple">{cmp.data.device_count} devices compared</Badge>}
      />

      {/* KPI strip */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <KpiCard
          label="Avg premium vs fair value"
          value={signedPct(head.avg_premium_vs_fair_pct ?? 0, 1)}
          sub="weighted by Maple stock"
          accent={head.avg_premium_vs_fair_pct > (head.justified_premium_pct ?? 8) ? "rose" : "maple"}
        />
        <KpiCard
          label="Justified premium"
          value={pct(cmp.data.justified_premium_pct, 1)}
          sub="certification + warranty + trust"
          accent="sky"
        />
        <KpiCard
          label="SKUs above justified"
          value={`${head.skus_above_justified ?? 0} / ${head.skus_compared ?? 0}`}
          sub="priced above the justified band"
          accent="amber"
        />
        <KpiCard
          label="ML model fit (R²)"
          value={mlAvail ? (mlModel.metrics.r2 * 100).toFixed(1) + "%" : "—"}
          sub={mlAvail ? `MAPE ${mlModel.metrics.mape}%` : "model not trained"}
          accent="maple"
        />
      </div>

      {/* Headline + justification */}
      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Panel className="lg:col-span-2">
          <SectionTitle
            title="The pricing story"
            subtitle="How Maple's shelf price compares to condition-normalized market value"
          />
          <p className="text-sm leading-relaxed text-slate-300">{head.summary}</p>
          <div className="mt-4 grid grid-cols-3 gap-3">
            <div className="rounded-lg border border-panel-line bg-white/[0.02] p-3">
              <div className="text-[11px] uppercase tracking-wider text-slate-500">Brand</div>
              <div className="stat-num mt-1 text-lg text-white">{pct(just.brand_pct, 1)}</div>
            </div>
            <div className="rounded-lg border border-panel-line bg-white/[0.02] p-3">
              <div className="text-[11px] uppercase tracking-wider text-slate-500">Warranty</div>
              <div className="stat-num mt-1 text-lg text-white">{pct(just.warranty_pct, 1)}</div>
            </div>
            <div className="rounded-lg border border-panel-line bg-white/[0.02] p-3">
              <div className="text-[11px] uppercase tracking-wider text-slate-500">Maple trust</div>
              <div className="stat-num mt-1 text-lg text-white">{pct(just.trust_pct, 1)}</div>
            </div>
          </div>
          <p className="mt-3 text-xs text-slate-500">{just.note}</p>
        </Panel>

        <Panel>
          <SectionTitle title="Top premiums vs fair value" subtitle="green = within justified band" />
          {topPremium.length ? (
            <HBarChart data={topPremium} unit="%" height={280} />
          ) : (
            <div className="p-4 text-sm text-slate-500">No high-confidence comparisons yet.</div>
          )}
        </Panel>
      </div>

      {/* ML price intelligence */}
      <Panel className="mt-4">
        <SectionTitle
          title="Price Intelligence (ML)"
          subtitle="A scikit-learn second opinion learned from the live market"
          right={mlAvail ? <Badge tone="sky">{mlModel.kind}</Badge> : <Badge tone="amber">offline</Badge>}
        />
        {mlAvail ? (
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <div className="lg:col-span-2">
              <div className="mb-2 text-xs text-slate-500">
                Learned depreciation curve — % of MSRP retained as a unit ages (Pro · 256GB reference)
              </div>
              <RetentionChart data={ml.data.depreciation_curve || []} />
            </div>
            <div className="space-y-3">
              <KpiCard
                label="Monthly depreciation"
                value={signedPct(ml.data.model.monthly_depreciation_pct, 2)}
                sub="learned market decay"
                accent="rose"
              />
              <KpiCard
                label="Model accuracy"
                value={(mlModel.metrics.r2 * 100).toFixed(1) + "%"}
                sub={`MAE ${inr(mlModel.metrics.mae)} · n=${mlModel.metrics.n_train + mlModel.metrics.n_test}`}
                accent="maple"
              />
              <div className="text-xs text-slate-500">
                Trained on {mlModel.value_platforms?.join(", ")} · as of {mlModel.as_of}
              </div>
            </div>
          </div>
        ) : (
          <div className="p-3 text-sm text-slate-400">
            {ml.data?.reason || "ML model not available. Build it with `python -m app.ml.train`."}
          </div>
        )}
      </Panel>

      {/* Comparison table */}
      <Panel className="mt-4">
        <SectionTitle
          title="Per-device comparison"
          subtitle="Maple price vs market fair value & competitor median (condition-normalized)"
          right={
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search model…"
              className="w-44 rounded-lg border border-panel-line bg-white/[0.02] px-3 py-1.5 text-xs text-slate-200 outline-none focus:border-maple-600/50"
            />
          }
        />
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-panel-line text-left text-[11px] uppercase tracking-wider text-slate-500">
                <th className="py-2 pr-3 font-medium">Device</th>
                <th className="px-3 py-2 text-right font-medium">Maple price</th>
                <th className="px-3 py-2 text-right font-medium">Market fair value</th>
                <th className="px-3 py-2 text-right font-medium">Competitor median</th>
                <th className="px-3 py-2 text-right font-medium">Premium vs fair</th>
                <th className="px-3 py-2 font-medium">Verdict</th>
                <th className="px-3 py-2 text-right font-medium">Market conf.</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((d) => (
                <tr key={d.sku} className="border-b border-panel-line/60 hover:bg-white/[0.02]">
                  <td className="py-2.5 pr-3">
                    <div className="font-medium text-slate-200">{d.model}</div>
                    <div className="text-xs text-slate-500">
                      {d.storage} · {d.maple_units} unit{d.maple_units === 1 ? "" : "s"}
                    </div>
                  </td>
                  <td className="stat-num px-3 py-2.5 text-right text-white">{inr(d.maple_price)}</td>
                  <td className="stat-num px-3 py-2.5 text-right text-slate-300">{inr(d.market_fair_value)}</td>
                  <td className="stat-num px-3 py-2.5 text-right text-slate-400">
                    {d.competitor_median ? inr(d.competitor_median) : "—"}
                  </td>
                  <td className={`stat-num px-3 py-2.5 text-right font-medium ${premiumTone(d.premium_vs_fair_pct)}`}>
                    {signedPct(d.premium_vs_fair_pct, 1)}
                  </td>
                  <td className="px-3 py-2.5">
                    <Badge tone={VERDICT_TONE[d.verdict] || "slate"}>{d.verdict}</Badge>
                  </td>
                  <td className="px-3 py-2.5 text-right">
                    <ConfidenceDot value={d.market_confidence} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}
