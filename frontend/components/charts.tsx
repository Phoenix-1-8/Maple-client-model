"use client";

import React from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { shortDate } from "@/lib/format";

const AXIS = "#5b6b78";
const GRID = "#1b2730";

function TipBox({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-panel-line bg-[#0c1318] px-3 py-2 text-xs shadow-xl">
      {children}
    </div>
  );
}

export function IndexAreaChart({
  data,
  height = 240,
}: {
  data: { day: string; index: number; movement_pct?: number }[];
  height?: number;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 8, right: 10, left: 6, bottom: 0 }}>
        <defs>
          <linearGradient id="mapleArea" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#34d399" stopOpacity={0.6} />
            <stop offset="100%" stopColor="#22c55e" stopOpacity={0.02} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke={GRID} vertical={false} />
        <XAxis
          dataKey="day"
          tickFormatter={shortDate}
          tick={{ fill: AXIS, fontSize: 11 }}
          tickLine={false}
          axisLine={{ stroke: GRID }}
          minTickGap={28}
        />
        <YAxis
          tick={{ fill: AXIS, fontSize: 11 }}
          tickLine={false}
          axisLine={false}
          domain={[(min: number) => Math.floor(min - 1), (max: number) => Math.ceil(max + 1)]}
          tickFormatter={(v: number) => v.toFixed(0)}
          width={34}
        />
        <Tooltip
          content={({ active, payload, label }) =>
            active && payload && payload.length ? (
              <TipBox>
                <div className="text-slate-400">{shortDate(label as string)}</div>
                <div className="stat-num text-sm text-white">
                  Index {Number(payload[0].value).toFixed(2)}
                </div>
              </TipBox>
            ) : null
          }
        />
        <Area
          type="monotone"
          dataKey="index"
          stroke="#4ade80"
          strokeWidth={2.5}
          fill="url(#mapleArea)"
          activeDot={{ r: 3, fill: "#4ade80" }}
          isAnimationActive={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

export function Sparkline({
  data,
  color = "#22c55e",
  height = 40,
}: {
  data: { day: string; index: number }[];
  color?: string;
  height?: number;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 4, right: 2, left: 2, bottom: 0 }}>
        <Line type="monotone" dataKey="index" stroke={color} strokeWidth={1.6} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}

export function RetentionChart({
  data,
  height = 220,
}: {
  data: { age_months: number; retained_pct: number }[];
  height?: number;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 8, right: 10, left: 6, bottom: 0 }}>
        <defs>
          <linearGradient id="retArea" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#38bdf8" stopOpacity={0.5} />
            <stop offset="100%" stopColor="#38bdf8" stopOpacity={0.02} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke={GRID} vertical={false} />
        <XAxis
          dataKey="age_months"
          tick={{ fill: AXIS, fontSize: 11 }}
          tickLine={false}
          axisLine={{ stroke: GRID }}
          tickFormatter={(v: number) => `${v}m`}
          minTickGap={20}
        />
        <YAxis
          tick={{ fill: AXIS, fontSize: 11 }}
          tickLine={false}
          axisLine={false}
          domain={[0, 1]}
          tickFormatter={(v: number) => `${Math.round(v * 100)}%`}
          width={38}
        />
        <Tooltip
          content={({ active, payload }) =>
            active && payload && payload.length ? (
              <TipBox>
                <div className="text-slate-400">{payload[0].payload.age_months} months old</div>
                <div className="stat-num text-sm text-white">
                  {(Number(payload[0].value) * 100).toFixed(0)}% of MSRP retained
                </div>
              </TipBox>
            ) : null
          }
        />
        <Area
          type="monotone"
          dataKey="retained_pct"
          stroke="#38bdf8"
          strokeWidth={2.5}
          fill="url(#retArea)"
          isAnimationActive={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

export function HBarChart({
  data,
  height = 260,
  unit = "",
}: {
  data: { label: string; value: number; color?: string }[];
  height?: number;
  unit?: string;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart
        data={data}
        layout="vertical"
        margin={{ top: 4, right: 16, left: 8, bottom: 0 }}
      >
        <CartesianGrid stroke={GRID} horizontal={false} />
        <XAxis type="number" tick={{ fill: AXIS, fontSize: 11 }} tickLine={false} axisLine={false} />
        <YAxis
          type="category"
          dataKey="label"
          tick={{ fill: "#aab6c0", fontSize: 12 }}
          tickLine={false}
          axisLine={false}
          width={120}
        />
        <Tooltip
          cursor={{ fill: "rgba(255,255,255,0.03)" }}
          content={({ active, payload }) =>
            active && payload && payload.length ? (
              <TipBox>
                <div className="text-white">{payload[0].payload.label}</div>
                <div className="stat-num text-slate-300">
                  {Number(payload[0].value).toLocaleString("en-IN")}
                  {unit}
                </div>
              </TipBox>
            ) : null
          }
        />
        <Bar dataKey="value" radius={[0, 4, 4, 0]} isAnimationActive={false}>
          {data.map((d, i) => (
            <Cell key={i} fill={d.color || "#22c55e"} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
