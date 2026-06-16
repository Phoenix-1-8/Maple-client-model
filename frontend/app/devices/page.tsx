"use client";

import { useMemo, useState } from "react";
import { PageHeader } from "@/components/Shell";
import { HBarChart } from "@/components/charts";
import { Badge, ConfidenceDot, ErrorState, KpiCard, Loading, Panel, SectionTitle } from "@/components/ui";
import { endpoints } from "@/lib/api";
import { inr, shortDate } from "@/lib/format";
import { useApi } from "@/lib/useApi";

const ROLE_TONE: Record<string, any> = {
  recommerce: "maple",
  marketplace: "sky",
  tradein: "amber",
};
const ROLE_COLOR: Record<string, string> = {
  recommerce: "#22c55e",
  marketplace: "#38bdf8",
  tradein: "#f59e0b",
};
const FAMILIES = ["iPhone", "iPad", "Mac", "Watch", "AirPods"];

function vsFairClass(v: number): string {
  if (v < -0.05) return "text-maple-400"; // below fair value → buy opportunity
  if (v > 0.05) return "text-rose-400";
  return "text-slate-400";
}

export default function DevicesPage() {
  const overview = useApi<any>(endpoints.devices);
  const [sku, setSku] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [family, setFamily] = useState<string | null>(null);

  const allDevices: any[] = overview.data?.devices || [];

  // Default selection: first device once the catalogue loads.
  const selectedSku = sku ?? allDevices[0]?.sku ?? null;
  const detail = useApi<any>(selectedSku ? endpoints.device(selectedSku) : null);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return allDevices.filter((d) => {
      if (family !== null && (d.family || "iPhone") !== family) return false;
      if (!q) return true;
      return (`${d.model} ${d.storage} ${d.sku}`).toLowerCase().includes(q);
    });
  }, [allDevices, query, family]);

  if (overview.error) return <ErrorState message={overview.error} />;
  if (overview.loading || !overview.data) return <Loading label="Loading device catalogue…" />;

  return (
    <div>
      <PageHeader
        title="Device Pricing"
        subtitle="Per-device price breakdown across every tracked site · India · condition-normalized"
        badge={<Badge tone="maple">{overview.data.device_count} devices priced</Badge>}
      />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[300px,1fr]">
        {/* Device picker */}
        <Panel className="p-3">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search model, storage…"
            className="mb-3 w-full rounded-lg border border-panel-line bg-panel-soft px-3 py-2 text-sm text-slate-200 placeholder:text-slate-600 focus:border-maple-600/50 focus:outline-none"
          />
          <div className="mb-3 flex flex-wrap gap-1">
            <button
              onClick={() => setFamily(null)}
              className={`chip ${family === null ? "border-maple-600/50 text-maple-300" : ""}`}
            >
              All
            </button>
            {FAMILIES.map((f) => (
              <button
                key={f}
                onClick={() => setFamily(f)}
                className={`chip ${family === f ? "border-maple-600/50 text-maple-300" : ""}`}
              >
                {f}
              </button>
            ))}
          </div>
          <div className="max-h-[640px] space-y-1 overflow-y-auto pr-1">
            {filtered.map((d) => {
              const active = d.sku === selectedSku;
              return (
                <button
                  key={d.sku}
                  onClick={() => setSku(d.sku)}
                  className={`w-full rounded-lg border px-3 py-2 text-left transition ${
                    active
                      ? "border-maple-600/50 bg-maple-500/10"
                      : "border-transparent hover:bg-white/[0.03]"
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className={`text-sm font-medium ${active ? "text-maple-200" : "text-slate-200"}`}>
                      {d.model}
                    </span>
                    <span className="text-[11px] text-slate-500">{d.storage}</span>
                  </div>
                  <div className="mt-0.5 flex items-center justify-between text-[11px] text-slate-500">
                    <span className="stat-num">{inr(d.median_price)}</span>
                    <span>{d.listings} listings · {d.platforms} sites</span>
                  </div>
                </button>
              );
            })}
            {filtered.length === 0 && (
              <div className="px-3 py-6 text-center text-xs text-slate-600">No devices match.</div>
            )}
          </div>
        </Panel>

        {/* Detail */}
        <div className="min-w-0">
          {detail.error && <ErrorState message={detail.error} />}
          {(detail.loading || !detail.data) && !detail.error && <Loading label="Loading device…" />}
          {detail.data && <DeviceDetail d={detail.data} />}
        </div>
      </div>
    </div>
  );
}

function DeviceDetail({ d }: { d: any }) {
  const dev = d.device;
  const superb = d.recommendations?.Superb;
  const platformName: Record<string, string> = {};
  for (const p of d.by_platform) platformName[p.platform] = p.platform_name;

  const barData = d.by_platform.map((p: any) => ({
    label: p.platform_name,
    value: p.median_price,
    color: ROLE_COLOR[p.role] || "#64748b",
  }));

  return (
    <div className="space-y-4">
      {/* Title + identity */}
      <Panel>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-xl font-semibold text-white">
              {dev.model} <span className="text-slate-400">· {dev.storage}</span>
            </h2>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <Badge tone="slate">{dev.variant}</Badge>
              <Badge tone="slate">{d.summary.platforms} sites</Badge>
              <Badge tone="slate">{d.summary.total_listings} listings</Badge>
              <Badge tone="slate">{d.summary.cities} cities</Badge>
              {d.valuation && (
                <span className="inline-flex items-center gap-1.5 text-xs text-slate-400">
                  Confidence <ConfidenceDot value={d.valuation.confidence} />
                </span>
              )}
            </div>
          </div>
          <div className="text-right text-xs text-slate-500">
            <div>Launch MSRP <span className="stat-num text-slate-300">{inr(dev.msrp)}</span></div>
            <div>Launched {shortDate(dev.launch_date)} · {dev.age_months}mo old</div>
            <div>Depreciation <span className="text-rose-300">−{dev.depreciation_pct}%</span></div>
          </div>
        </div>
        {dev.colors_seen?.length > 0 && (
          <div className="mt-3 flex flex-wrap items-center gap-1.5 border-t border-panel-line pt-3 text-xs text-slate-500">
            <span className="mr-1">Colours in market:</span>
            {dev.colors_seen.map((c: string) => (
              <span key={c} className="chip">{c}</span>
            ))}
          </div>
        )}
      </Panel>

      {/* KPIs */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-3">
        <KpiCard label="Fair Value (Superb)" value={inr(d.fair_value)} sub={<span>condition-normalized</span>} />
        <KpiCard label="Recommended Sell" value={inr(superb?.recommended_sell)} accent="sky" sub={<span>Superb grade</span>} />
        <KpiCard label="Recommended Buy" value={inr(superb?.recommended_buy)} accent="amber" sub={<span>Superb grade</span>} />
        <KpiCard label="Lowest in market" value={inr(d.summary.lowest_price)} sub={<span>{platformName[d.summary.cheapest_platform] || d.summary.cheapest_platform}</span>} />
        <KpiCard label="Median asking" value={inr(d.summary.median_price)} accent="slate" />
        <KpiCard label="Highest asking" value={inr(d.summary.highest_price)} accent="rose" />
      </div>

      {/* Price by site */}
      <Panel>
        <SectionTitle title="Price by Site" subtitle="Each platform's own price level · sorted cheapest first" />
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-panel-line">
                <th className="th">Site</th>
                <th className="th">Type</th>
                <th className="th text-right">Listings</th>
                <th className="th text-right">Lowest</th>
                <th className="th text-right">Median</th>
                <th className="th text-right">Highest</th>
                <th className="th text-right">vs Fair</th>
                <th className="th text-right">Seller ★</th>
                <th className="th text-right">Verified</th>
              </tr>
            </thead>
            <tbody>
              {d.by_platform.map((p: any) => (
                <tr key={p.platform} className="row-hover border-b border-panel-line/50">
                  <td className="td font-medium text-white">{p.platform_name}</td>
                  <td className="td"><Badge tone={ROLE_TONE[p.role] || "slate"}>{p.role}</Badge></td>
                  <td className="td stat-num text-right">{p.listings}</td>
                  <td className="td stat-num text-right text-slate-400">{inr(p.lowest_price)}</td>
                  <td className="td stat-num text-right text-white">{inr(p.median_price)}</td>
                  <td className="td stat-num text-right text-slate-400">{inr(p.highest_price)}</td>
                  <td className={`td stat-num text-right ${vsFairClass(p.vs_fair_value_pct / 100)}`}>
                    {p.vs_fair_value_pct > 0 ? "+" : ""}{p.vs_fair_value_pct}%
                  </td>
                  <td className="td stat-num text-right text-slate-300">
                    {p.avg_seller_rating != null ? p.avg_seller_rating.toFixed(1) : "—"}
                  </td>
                  <td className="td stat-num text-right text-slate-400">{p.verified_share_pct}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* Median by site */}
        <Panel>
          <SectionTitle title="Median Price by Site" subtitle="Refurbisher · marketplace · trade-in" />
          <HBarChart data={barData} unit="" height={Math.max(180, barData.length * 38)} />
        </Panel>

        {/* By condition */}
        <Panel>
          <SectionTitle title="Buy / Sell by Condition" subtitle="Maple grade · recommended prices" />
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-panel-line">
                  <th className="th">Grade</th>
                  <th className="th text-right">Listings</th>
                  <th className="th text-right">Median</th>
                  <th className="th text-right">Battery</th>
                  <th className="th text-right">Buy</th>
                  <th className="th text-right">Sell</th>
                </tr>
              </thead>
              <tbody>
                {d.by_condition.map((c: any) => (
                  <tr key={c.condition} className="row-hover border-b border-panel-line/50">
                    <td className="td font-medium text-slate-200">{c.condition}</td>
                    <td className="td stat-num text-right">{c.listings}</td>
                    <td className="td stat-num text-right text-slate-400">{inr(c.median_price)}</td>
                    <td className="td stat-num text-right text-slate-400">{c.avg_battery_health}%</td>
                    <td className="td stat-num text-right text-amber-300">{inr(c.recommended_buy)}</td>
                    <td className="td stat-num text-right text-sky-300">{inr(c.recommended_sell)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      </div>

      {/* Full listing feed */}
      <Panel>
        <SectionTitle
          title="All Listings — Scrapable Detail"
          subtitle={`${d.listings.length} live listings · every field captured per source`}
        />
        <div className="overflow-x-auto">
          <table className="w-full whitespace-nowrap">
            <thead>
              <tr className="border-b border-panel-line">
                <th className="th">Site</th>
                <th className="th">Condition</th>
                <th className="th text-right">Battery</th>
                <th className="th">Colour</th>
                <th className="th">City</th>
                <th className="th">Seller</th>
                <th className="th">Warranty</th>
                <th className="th">Accessories</th>
                <th className="th">Lock</th>
                <th className="th text-right">Views</th>
                <th className="th text-right">Price</th>
                <th className="th">Listed</th>
                <th className="th">Link</th>
              </tr>
            </thead>
            <tbody>
              {d.listings.map((l: any, i: number) => (
                <tr key={i} className="row-hover border-b border-panel-line/50">
                  <td className="td font-medium text-slate-200">
                    {platformName[l.platform] || l.platform}
                    {l.verified && <span className="ml-1.5 text-maple-400" title="Verified / inspected">✓</span>}
                  </td>
                  <td className="td">
                    <span className="text-slate-200">{l.condition}</span>
                    <span className="ml-1 text-[11px] text-slate-500">({l.raw_condition})</span>
                  </td>
                  <td className="td stat-num text-right text-slate-400">{l.battery_health}%</td>
                  <td className="td text-slate-300">{l.color}</td>
                  <td className="td text-slate-400">{l.city}</td>
                  <td className="td text-slate-300">
                    {l.seller_name}
                    {l.seller_rating > 0 && (
                      <span className="ml-1 text-[11px] text-slate-500">
                        ★{l.seller_rating}{l.seller_reviews > 0 ? `·${l.seller_reviews}` : ""}
                      </span>
                    )}
                  </td>
                  <td className="td text-slate-400">{l.warranty}</td>
                  <td className="td text-slate-400">{l.accessories}</td>
                  <td className="td text-slate-500">{l.lock_status}</td>
                  <td className="td stat-num text-right text-slate-500">{l.views || "—"}</td>
                  <td className="td stat-num text-right font-medium text-white">{inr(l.asking_price)}</td>
                  <td className="td text-slate-500">{shortDate(l.listing_date)}</td>
                  <td className="td">
                    <a
                      href={l.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-maple-400 hover:text-maple-300"
                    >
                      open ↗
                    </a>
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
