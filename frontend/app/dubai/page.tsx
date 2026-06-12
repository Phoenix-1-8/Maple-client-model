"use client";

import { PageHeader } from "@/components/Shell";
import { HBarChart } from "@/components/charts";
import { Badge, ErrorState, KpiCard, Loading, Panel, ScoreBar, SectionTitle } from "@/components/ui";
import { endpoints } from "@/lib/api";
import { inr, inrCompact, pct, signedPct } from "@/lib/format";
import { useApi } from "@/lib/useApi";

export default function DubaiPage() {
  const res = useApi<any>(endpoints.dubai);

  if (res.error) return <ErrorState message={res.error} />;
  if (res.loading || !res.data) return <Loading />;

  const d = res.data;
  const opps = d.opportunities || [];
  const spreadBars = opps
    .slice(0, 10)
    .map((o: any) => ({ label: `${o.model} ${o.storage}`, value: o.spread, color: "#22c55e" }));

  return (
    <div>
      <PageHeader
        title="Dubai Expansion"
        subtitle="India ⇄ Dubai price spread, landed-cost margin & export opportunity scoring"
        badge={
          <div className="flex items-center gap-2">
            <Badge tone="sky">AED→INR {d.aed_to_inr}</Badge>
            <Badge tone="amber">Import duty {pct(d.import_duty_pct)}</Badge>
          </div>
        }
      />

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <KpiCard label="Devices Compared" value={d.devices_compared} sub={<span>both markets</span>} />
        <KpiCard
          label="Viable Opportunities"
          value={d.viable_opportunities}
          sub={<span>positive net margin</span>}
          accent="maple"
        />
        <KpiCard
          label="Margin Potential"
          value={inrCompact(d.total_margin_potential)}
          sub={<span>monthly, viable lots</span>}
          accent="amber"
        />
        <KpiCard label="Avg India–Dubai Spread" value={pct(d.avg_spread_pct)} accent="sky" />
      </div>

      <Panel className="mt-4">
        <SectionTitle
          title="Export / Import Opportunities"
          subtitle="Sourcing in the cheaper market, selling in the richer one (Superb-adjusted)"
        />
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-panel-line">
                <th className="th">Model</th>
                <th className="th">Direction</th>
                <th className="th text-right">India value</th>
                <th className="th text-right">Dubai cost</th>
                <th className="th text-right">Spread</th>
                <th className="th text-right">Landed</th>
                <th className="th text-right">Maple sell</th>
                <th className="th text-right">Net margin</th>
                <th className="th">Export score</th>
              </tr>
            </thead>
            <tbody>
              {opps.map((o: any) => (
                <tr key={o.sku} className="row-hover border-b border-panel-line/50">
                  <td className="td font-medium text-white">
                    {o.model} <span className="text-slate-500">{o.storage}</span>
                  </td>
                  <td className="td">
                    <span className="text-[11px] text-slate-400">{o.direction}</span>
                  </td>
                  <td className="td stat-num text-right">{inr(o.india_value)}</td>
                  <td className="td stat-num text-right">
                    {inr(o.dubai_cost)}
                    <span className="ml-1 text-[10px] text-slate-500">AED {o.dubai_cost_aed.toLocaleString("en-IN")}</span>
                  </td>
                  <td className="td stat-num text-right text-amber-400">{signedPct(o.spread_pct, 1)}</td>
                  <td className="td stat-num text-right text-slate-400">{inr(o.landed_cost)}</td>
                  <td className="td stat-num text-right">{inr(o.maple_sell)}</td>
                  <td className={`td stat-num text-right ${o.net_margin >= 0 ? "text-maple-300" : "text-rose-400"}`}>
                    {inr(o.net_margin)}
                  </td>
                  <td className="td">
                    <ScoreBar value={o.export_opportunity_score} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {opps.length === 0 && <Loading label="No cross-border samples yet — hit Refresh market." />}
      </Panel>

      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Panel>
          <SectionTitle title="Largest Price Spreads" subtitle="India value − Dubai cost (₹/unit)" />
          {spreadBars.length > 0 && <HBarChart data={spreadBars} height={300} />}
        </Panel>
        <Panel>
          <SectionTitle title="How the margin is built" subtitle="Worked example per unit" />
          {opps[0] && (
            <DubaiWaterfall
              o={opps[0]}
              duty={d.import_duty_pct}
              logistics={d.cross_border_logistics ?? 1500}
              costs={d.domestic_costs ?? { refurbishment: 1200, logistics: 450, warranty_reserve: 800 }}
            />
          )}
        </Panel>
      </div>
    </div>
  );
}

function DubaiWaterfall({
  o,
  duty,
  logistics,
  costs,
}: {
  o: any;
  duty: number;
  logistics: number;
  costs: { refurbishment: number; logistics: number; warranty_reserve: number };
}) {
  const rows = [
    { label: "Dubai acquisition cost", value: -o.dubai_cost, tone: "text-slate-300" },
    { label: `Import duty + GST (${duty}%)`, value: -(o.landed_cost - o.dubai_cost - logistics), tone: "text-rose-300" },
    { label: "Cross-border logistics", value: -logistics, tone: "text-rose-300" },
    { label: "Landed cost (India)", value: -o.landed_cost, tone: "text-amber-300", rule: true },
    { label: "Refurbishment & certification", value: -costs.refurbishment, tone: "text-rose-300" },
    { label: "Domestic logistics", value: -costs.logistics, tone: "text-rose-300" },
    { label: "Warranty reserve", value: -costs.warranty_reserve, tone: "text-rose-300" },
    { label: "Maple sell price", value: o.maple_sell, tone: "text-maple-300" },
    { label: "Net margin / unit", value: o.net_margin, tone: "text-white", rule: true, bold: true },
  ];
  return (
    <div className="space-y-2">
      <div className="mb-1 text-sm font-medium text-white">
        {o.model} {o.storage}
      </div>
      {rows.map((r, i) => (
        <div key={i} className={`flex items-center justify-between ${r.rule ? "border-t border-panel-line pt-2" : ""}`}>
          <span className="text-sm text-slate-400">{r.label}</span>
          <span className={`stat-num ${r.bold ? "text-base font-semibold" : "text-sm"} ${r.tone}`}>
            {inr(r.value)}
          </span>
        </div>
      ))}
      <p className="pt-1 text-[11px] text-slate-500">
        Margin {pct(o.margin_pct)} · export score {o.export_opportunity_score}/100
      </p>
    </div>
  );
}
